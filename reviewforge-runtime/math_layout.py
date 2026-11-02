"""Measured-width equation packing: use the fewest scientifically coherent rows."""
from pathlib import Path
import re
import shutil
import tempfile
import time

LAYOUT_TAG='% RF_MEASURED_MATH'

DISPLAY=re.compile(r'\\begin\{(equation\*?)\}([\s\S]*?)\\end\{\1\}|\\\[([\s\S]*?)\\\]')


def unfold_continuation(body,*,exporter_owned=False):
    if not exporter_owned:return body
    match=re.fullmatch(r'\s*\\begin\{aligned\}([\s\S]*?)\\end\{aligned\}\s*',body)
    if not match:return body
    rows=match.group(1).replace(r'\\',' ')
    return re.sub(r'(?<!\\)&','',rows).strip()


def breakpoints(core):
    cuts={};depth=paren=left=escaped=0;relations=0;i=0
    while i<len(core):
        command=re.match(r'\\[A-Za-z]+|\\.',core[i:])
        if command:
            token=command.group()
            if token==r'\left':left+=1
            elif token==r'\right':left=max(0,left-1)
            elif token==r'\{':escaped+=1
            elif token==r'\}':escaped=max(0,escaped-1)
            if token in (r'\qquad',r'\quad') and depth==paren==left==0:
                cuts[i]=0;relations=0
            i+=len(token);continue
        c=core[i]
        if c=='{':depth+=1
        elif c=='}':depth-=1
        elif depth==0:
            if c in '([':paren+=1
            elif c in ')]':paren=max(0,paren-1)
            elif left==escaped==0:
                if c=='=' and paren==0:
                    cuts[i]=0 if relations else 4
                    relations+=1
                elif c=='+' and paren==0:cuts[i]=2
                elif c=='-' and paren==0 and core[:i].rstrip() and core[:i].rstrip()[-1] not in '^_({[=,+-':cuts[i]=2
                elif c in ',;' and paren==0:
                    cuts[i+1]=0;relations=0
                elif c==',' and paren==1:cuts[i+1]=1
        i+=1
    return {i:cost for i,cost in cuts.items() if core[:i].strip() and core[i:].strip()}


def pack_rows(core,cuts,widths,limit):
    positions=sorted({0,len(core),*cuts});best={0:(0,[])}
    for stop in positions[1:]:
        for start in positions:
            if start>=stop or start not in best:continue
            width=widths.get((start,stop),float('inf'))
            if width>limit:continue
            cost=best[start][0]+1000000+1000*cuts.get(stop,0)+(limit-width)**2*.001
            if stop not in best or cost<best[stop][0]:best[stop]=(cost,best[start][1]+[core[start:stop].strip()])
    return best.get(len(core),(None,None))[1]


def tex_widths(expressions,preamble,directory,deadline=None):
    """Use the manuscript's own TeX fonts and column geometry, not source length."""
    from bounded_process import run_process_tree
    engine=shutil.which('xelatex')
    if not engine:raise RuntimeError('XeLaTeX required for measured equation layout')
    with tempfile.TemporaryDirectory(prefix='rf_math_') as temp:
        folder=Path(temp);source=folder/'measure.tex'
        rows=[preamble,r'\begin{document}',r'\typeout{RFCOLUMN:\the\columnwidth}']
        for index,expression in enumerate(expressions):
            rows.extend([r'\setbox0=\hbox{$\displaystyle '+expression+r'$}',r'\typeout{RFWIDTH:'+str(index)+r':\the\wd0}'])
        rows.append(r'\end{document}');source.write_bytes('\n'.join(rows).encode('utf-8'))
        remaining=float('inf') if deadline is None else deadline-time.time()
        if remaining<5:raise TimeoutError('Equation measurement budget ended; source retained')
        process=run_process_tree([engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-output-directory='+str(folder),str(source)],cwd=str(Path(directory).resolve()),timeout=min(90,remaining-2))
        log=(folder/'measure.log').read_text(encoding='utf-8',errors='replace') if (folder/'measure.log').exists() else ''
        values={int(i):float(w) for i,w in re.findall(r'RFWIDTH:(\d+):([\d.]+)pt',log)}
        column=re.search(r'RFCOLUMN:([\d.]+)pt',log)
        if process.returncode or len(values)!=len(expressions) or not column:raise RuntimeError('Equation width measurement failed; original source retained')
        return [values[i] for i in range(len(expressions))],float(column.group(1))


def row_text(text):
    return re.sub(r'^(?:(?:\\qquad|\\quad)\s*)+','',text.strip())


def aligned_rows(rows):
    result=[]
    for row in rows:
        row=row_text(row)
        equal=next((i for i in breakpoints(row) if row[i:i+1]=='='),None)
        if re.match(r'^\s*[+=-]',row):equal=None
        if equal is None:result.append('&'+row)
        else:result.append(row[:equal]+'&'+row[equal:])
    return r'\begin{aligned}'+'\n'+('\\\\\n'.join(result))+r'\end{aligned}'


def balanced_math(tex,directory,deadline=None):
    records=[];expressions=[];ids={}
    def expression_id(value):
        value=row_text(value)
        if value not in ids:ids[value]=len(expressions);expressions.append(value)
        return ids[value]
    for match in DISPLAY.finditer(tex):
        body=match.group(2) if match.group(1) else match.group(3)
        labels=re.findall(r'\\label\{[^{}]+\}',body)
        authored=re.sub(r'\\label\{[^{}]+\}','',body)
        if LAYOUT_TAG in authored:
            authored=authored.replace(LAYOUT_TAG,'',1)
            authored=unfold_continuation(authored,exporter_owned=True)
        core=authored.strip()
        if re.search(r'\\begin\{|\\\\|&|\\tag\b',core) or len(core)<40:continue
        cuts=breakpoints(core);positions=sorted({0,len(core),*cuts});intervals={}
        for i,start in enumerate(positions[:-1]):
            for stop in positions[i+1:]:intervals[start,stop]=expression_id(core[start:stop])
        records.append({'match':match,'core':core,'labels':labels,'cuts':cuts,'intervals':intervals})
    if not records:return tex,0
    preamble=tex[:tex.index(r'\begin{document}')]
    measured,column=tex_widths(expressions,preamble,directory,deadline)
    for record in records:
        widths={key:measured[index] for key,index in record['intervals'].items()}
        limit=column-(25 if record['match'].group(1) and not record['match'].group(1).endswith('*') else 4)
        rows=pack_rows(record['core'],record['cuts'],widths,limit)
        if rows is None:record['replacement']=None;continue
        record['limit']=limit;record['widths']=widths;record['rows']=rows
        record['layout']=row_text(rows[0]) if len(rows)==1 else aligned_rows(rows)
    # Alignment columns can be wider than individual rows. Verify the final box,
    # then repack only overwide results using a slightly tighter row budget.
    for iteration in range(4):
        active=[r for r in records if 'layout' in r]
        checks,_=tex_widths([r['layout'] for r in active],preamble,directory,deadline)
        pending=False
        for record,width in zip(active,checks):
            if width<=record['limit']+.1:continue
            budget=record['limit']*(.88**(iteration+1))
            rows=pack_rows(record['core'],record['cuts'],record['widths'],budget)
            if rows is None:raise RuntimeError('Equation cannot fit safely within its column')
            record['rows']=rows;record['layout']=row_text(rows[0]) if len(rows)==1 else aligned_rows(rows);pending=True
        if not pending:break
    else:raise RuntimeError('Equation alignment remains overwide')
    count=0
    for record in reversed(records):
        if 'layout' not in record:continue
        match=record['match'];body=LAYOUT_TAG+'\n'+record['layout']+''.join(record['labels'])
        replacement=(r'\begin{'+match.group(1)+'}'+body+r'\end{'+match.group(1)+'}') if match.group(1) else r'\['+body+r'\]'
        if replacement!=match.group():count+=1
        tex=tex[:match.start()]+replacement+tex[match.end():]
    return tex,count
