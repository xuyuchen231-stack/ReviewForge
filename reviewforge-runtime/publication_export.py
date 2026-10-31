"""Export-only reference identity and physical PDF reading-order checks."""
import re,time,shutil,uuid,zipfile
from pathlib import Path
from bibliography_delivery import active_text,citation_order,order_inline_bibliography,numeric_order_enabled
from manuscript_integrity import CITES

ITEM=re.compile(r'\\bibitem(?:\[[^]]*\])?\{([^{}]+)\}')

def canonicalize_references(tex):
    """Merge explicit identical DOIs, never title/surname guesses. Originals stay local."""
    active=active_text(tex);end=active.find(r'\end{thebibliography}')
    if end<0:return tex,{}
    start=active.find(r'\begin{thebibliography}')
    matches=[m for m in ITEM.finditer(active) if start<m.start()<end]
    if len({m.group(1) for m in matches})!=len(matches):raise ValueError('Duplicate bibliography keys must be resolved before canonicalization')
    rank={key:i for i,key in enumerate(citation_order(tex))};groups={};blocks={}
    for i,m in enumerate(matches):
        stop=matches[i+1].start() if i+1<len(matches) else end
        body=active_text(tex[m.end():stop]);blocks[m.group(1)]=(m.start(),stop)
        identifiers=re.findall(r'\\url\{(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^{}\s]+)\}',body,re.I)
        identifiers+=re.findall(r'\bDOI:\s*(?:https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^\s{}]+)',body,re.I)
        identifiers={doi.rstrip('.,;').lower() for doi in identifiers}
        if len(identifiers)==1:groups.setdefault(next(iter(identifiers)),[]).append(m.group(1))
    aliases={}
    for keys in groups.values():
        chosen=min(keys,key=lambda k:rank.get(k,len(rank)+list(blocks).index(k)))
        aliases.update({key:chosen for key in keys if key!=chosen})
    for begin,stop in sorted((blocks[key] for key in aliases),reverse=True):tex=tex[:begin]+tex[stop:]
    for m in reversed(list(CITES.finditer(active_text(tex)))):
        keys=list(dict.fromkeys(aliases.get(k.strip(),k.strip()) for k in m.group(1).split(',')))
        tex=tex[:m.start(1)]+','.join(keys)+tex[m.end(1):]
    return tex,aliases

def ordered_citation_links(links,width,spanning_bands,two_column=True):
    bands=[]
    for top,bottom in sorted(spanning_bands):
        if bands and top<=bands[-1][1]+1:bands[-1]=(bands[-1][0],max(bottom,bands[-1][1]))
        else:bands.append((top,bottom))
    def position(link):
        y=(link['y']+link.get('y1',link['y']))/2;x=link['x'];segment=0;wide=False
        for top,bottom in bands:
            if y<top:break
            segment+=1
            if y<=bottom:wide=True;break
            segment+=1
        column=0 if wide or not two_column or x<width/2 else 1
        return segment,column,round(y/2),x
    return list(dict.fromkeys(item['key'] for item in sorted(links,key=position)))

def mark_wide_material(tex):
    pattern=re.compile(r'\\begin\{(figure\*|table\*|strip)\}(?:\[[^]]*\])?[\s\S]*?\\end\{\1\}')
    matches=[m for m in pattern.finditer(active_text(tex)) if not re.search(r'rf-wide-\d+-start',tex[m.start():m.end()])]
    first=max([int(x) for x in re.findall(r'rf-wide-(\d+)-start',tex)]+[-1])+1
    for i,m in reversed(list(enumerate(matches,first))):
        raw=tex[m.start():m.end()];opening=re.match(r'\\begin\{[^}]+\}(?:\[[^]]*\])?',raw).end();closing=raw.rfind(r'\end{')
        raw=raw[:closing]+'\n\\hypertarget{rf-wide-%04d-end}{}\n'%i+raw[closing:]
        raw=raw[:opening]+'\n\\hypertarget{rf-wide-%04d-start}{}\n'%i+raw[opening:]
        tex=tex[:m.start()]+raw+tex[m.end():]
    if matches and not re.search(r'\\usepackage(?:\[[^]]*\])?\{[^}]*\bhyperref\b',active_text(tex)):
        tex=tex.replace(r'\begin{document}',r'\usepackage{hyperref}'+'\n'+r'\begin{document}',1)
    return tex

def portable_text_symbols(tex):
    """Use mathematical glyphs for Greek prose, leaving math and identifiers intact."""
    active=active_text(tex)
    if not any(char in active for char in ('\u03b2','\u03b1','\u03bc')):return tex
    protected=list(re.finditer(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}[\s\S]*?\\end\{\1\}|\\\[[\s\S]*?\\\]|(?<!\\)\$\$[\s\S]*?\$\$|(?<!\\)\$(?:\\[\s\S]|[^\\$])*?(?<!\\)\$|\\(?:url|path|href|label|ref|eqref|pageref|includegraphics|cite\w*)(?:\[[^]]*\])*\{[^{}]*\}',active))
    names={'\u03b2':'beta','\u03b1':'alpha','\u03bc':'mu'}
    for m in reversed(list(re.finditer('[\u03b2\u03b1\u03bc]',active))):
        if any(p.start()<=m.start()<p.end() for p in protected):continue
        tex=tex[:m.start()]+'\\ensuremath{\\'+names[m.group()]+'}'+tex[m.end():]
    return tex

def prepare_two_column_export(tex,force=False):
    """Keep requested columns; give figures/tables full width instead of shrinking type."""
    if not force and not re.search(r'\\documentclass\[[^]]*\btwocolumn\b',active_text(tex)):return tex
    if force:
        tex=re.sub(r'(?m)^\\onecolumn\s*\n','',tex)
    tex=tex.replace(r'\setmainfont{Liberation Serif}',r'\setmainfont{Latin Modern Roman}')
    # The portable Latin Modern text face lacks Greek prose glyphs. Math fonts
    # supply these symbols without changing the symbol or requiring a private font.
    tex=portable_text_symbols(tex)
    for m in reversed(list(re.finditer(r'\\begin\{(figure|table)\}(?:\[[^]]*\])?[\s\S]*?\\end\{\1\}',active_text(tex)))):
        body=tex[m.start():m.end()];kind=m.group(1)
        body=body.replace('\\begin{'+kind+'}','\\begin{'+kind+'*}',1)
        stop=body.rfind('\\end{'+kind+'}')
        body=body[:stop]+body[stop:].replace('\\end{'+kind+'}','\\end{'+kind+'*}',1)
        body=body.replace(r'\columnwidth',r'\textwidth')
        tex=tex[:m.start()]+body+tex[m.end():]
    # Standard two-column LaTeX cannot place starred floats at the bottom;
    # retaining [b] can block the entire figure queue until the bibliography.
    tex=re.sub(r'\\begin\{(figure\*|table\*)\}(?:\[[^]]*\])?',lambda m:'\\begin{'+m.group(1)+'}[!tp]',tex)
    return tex

def reflow_wide_displays(tex,layout):
    """Wrap only reported overwide displays; keep their complete math source unchanged."""
    lines=[d.get('start_line') for d in layout.get('overflow_details',[]) if d.get('kind')=='hbox' and isinstance(d.get('start_line'),int)]
    pattern=re.compile(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}[\s\S]*?\\end\{\1\}|\\\[[\s\S]*?\\\]')
    spans=list(re.finditer(r'\\begin\{strip\}[\s\S]*?\\end\{strip\}',active_text(tex)));selected=[]
    for m in pattern.finditer(active_text(tex)):
        if any(s.start()<=m.start()<s.end() for s in spans):continue
        start=tex.count('\n',0,m.start())+1;end=tex.count('\n',0,m.end())+1
        if any(start<=line<=end+1 for line in lines):selected.append(m)
    for m in reversed(selected):tex=tex[:m.start()]+'\n\\begin{strip}\n\\small\n'+tex[m.start():m.end()]+'\n\\end{strip}\n'+tex[m.end():]
    if selected and not re.search(r'\\usepackage(?:\[[^]]*\])?\{cuted\}',active_text(tex)):
        tex=tex.replace(r'\begin{document}',r'\usepackage{cuted}'+'\n'+r'\setlength{\stripsep}{6pt plus 2pt minus 2pt}'+'\n'+r'\begin{document}',1)
    return tex,len(selected)

class ReferenceCoverageError(ValueError):pass

def numeric_citation_records(raw,links,number_keys):
    """Expand link-anchored printed ranges, including their non-linked middle keys."""
    result=[];covered=set()
    def intersects(a,b):return a[0]<b['x1'] and a[2]>b['x'] and a[1]<b['y1'] and a[3]>b['y']
    for block in raw.get('blocks',[]):
        characters=[];positions=[]
        for line in block.get('lines',[]):
            for span in line.get('spans',[]):
                for char in span.get('chars',[]):characters.append(char['c']);positions.append(char['bbox'])
            characters.append('\n');positions.append(None)
        text=''.join(characters)
        for match in re.finditer(r'\[(\s*\d+(?:\s*[,;–—-]\s*\d+)*\s*)\]',text):
            boxes=[b for b in positions[match.start():match.end()] if b is not None]
            consumed={i for i,link in enumerate(links) if any(intersects(b,link) for b in boxes)}
            if not boxes or not consumed:continue
            numbers=[]
            for token in re.split(r'[,;]',match.group(1)):
                pair=re.split(r'[–—-]',token.strip())
                if len(pair)==2:
                    first,last=map(int,pair)
                    if first>last or last-first>len(number_keys):numbers=[];break
                    numbers.extend(range(first,last+1))
                else:numbers.append(int(pair[0]))
            if not numbers or any(n not in number_keys for n in numbers):continue
            anchor=boxes[0]
            for i,number in enumerate(numbers):
                key=number_keys[number]
                result.append({'key':key,'x':anchor[0]+i*.001,'x1':anchor[2],'y':anchor[1],'y1':anchor[3]})
            covered.update(consumed)
    # Retain every unconsumed link, including an earlier author-only citation
    # to an identity that is also cited numerically later on the same page.
    result.extend(link for i,link in enumerate(links) if i not in covered)
    return result

def validate_wide_markers(destinations,expected):
    missing=set(expected)-set(destinations)
    if missing:raise ReferenceCoverageError('Missing wide-material markers: '+','.join(sorted(missing)))
    for name,point in destinations.items():
        if not name.startswith('rf-wide-') or not name.endswith('-start'):continue
        last=destinations.get(name[:-5]+'end')
        if not last or any(not isinstance(p,dict) or type(p.get('page')) is not int or p['page']<0 or not isinstance(p.get('to'),(tuple,list)) or len(p['to'])<2 for p in (point,last)):
            raise ReferenceCoverageError('Incomplete wide-material marker pair: '+name)
        if last['page']<point['page'] or (last['page']==point['page'] and last['to'][1]<point['to'][1]-2):raise ReferenceCoverageError('Reversed wide-material marker pair: '+name)

def pdf_citation_order(pdf,two_column=True,expected_markers=()):
    import fitz
    order=[]
    aux=Path(pdf).with_suffix('.aux');number_keys={}
    if aux.exists():
        text=aux.read_text(encoding='utf-8',errors='replace')
        number_keys={int(number):key for key,number in re.findall(r'\\bibcite\{([^}]+)\}\{\{?(\d+)',text)}
    if not number_keys:raise ReferenceCoverageError('Current PDF citation numbering map is unavailable')
    with fitz.open(pdf) as document:
        destinations=document.resolve_names();bands={}
        # Named destinations use PDF bottom-left coordinates; link rectangles
        # already use top-left coordinates. Compare them in one coordinate space.
        destinations={name:{**point,'to':list(fitz.Point(point['to'])*document[point['page']].transformation_matrix)}
                      if type(point.get('page')) is int and 0<=point['page']<len(document) and 'to' in point else point
                      for name,point in destinations.items()}
        validate_wide_markers(destinations,expected_markers)
        for name,point in destinations.items():
            if not name.startswith('rf-wide-') or not name.endswith('-start'):continue
            last=destinations.get(name[:-5]+'end')
            if not last or 'page' not in point or 'page' not in last:continue
            for page in range(point['page'],last['page']+1):
                top=point['to'][1]-2 if page==point['page'] else 0
                bottom=last['to'][1]+2 if page==last['page'] else document[page].rect.height
                bands.setdefault(page,[]).append((top,bottom))
        for index,page in enumerate(document):
            links=[]
            for link in page.get_links():
                name=link.get('nameddest','')
                if name.startswith('cite.'):
                    box=link['from'];links.append({'key':name[5:],'x':box.x0,'y':box.y0,'x1':box.x1,'y1':box.y1})
            if number_keys:links=numeric_citation_records(page.get_text('rawdict'),links,number_keys)
            order.extend(ordered_citation_links(links,page.rect.width,bands.get(index,[]),two_column))
    return list(dict.fromkeys(order))

def reconcile_pdf_references(directory,tex,build,compile_again,max_passes=3,deadline=None):
    """Reorder against visible PDF links; fail visibly on missing coverage/cycles."""
    folder=Path(directory);passes=0
    if not numeric_order_enabled(tex):return tex,build,{'status':'NOT_APPLICABLE','reason':'Author-year ordering retained','passes':0}
    try:
        while build.get('status')=='PASS':
            pdf=folder/build['pdf']
            if not pdf.resolve().is_relative_to(folder.resolve()):raise ReferenceCoverageError('PDF is outside the export directory')
            markers=re.findall(r'\\hypertarget\{(rf-wide-\d+-(?:start|end))\}',active_text(tex))
            keys=pdf_citation_order(pdf,two_column=bool(re.search(r'\\documentclass\[[^]]*\btwocolumn\b',tex)),expected_markers=markers)
            missing=set(citation_order(tex))-set(keys)
            if missing:return tex,build,{'status':'UNVERIFIED','missing_pdf_citation_links':sorted(missing),'passes':passes}
            entries=ITEM.findall(active_text(tex));cited=[key for key in entries if key in keys]
            if cited==keys:return tex,build,{'status':'PASS','cited_references':len(keys),'passes':passes,'basis':'PDF hyperlink positions in column/float reading order'}
            if passes>=max_passes:return tex,build,{'status':'UNRESOLVED','reason':'Reference layout did not stabilize','passes':passes}
            if deadline is not None and deadline-time.time()<=30:return tex,build,{'status':'UNVERIFIED','reason':'Insufficient remaining reference-build budget; successful output retained','passes':passes}
            old_tex=tex;old_build=build;old_pdf=pdf.read_bytes();old_source=(folder/'review_en.tex').read_bytes()
            aux=pdf.with_suffix('.aux');old_aux=aux.read_bytes() if aux.exists() else None
            report_path=folder/'reports/review_en_build.json';old_report=report_path.read_bytes() if report_path.exists() else None
            tex=order_inline_bibliography(tex,keys)
            try:
                (folder/'review_en.tex').write_bytes(tex.encode('utf-8'))
                new_build=compile_again();passes+=1
                if new_build.get('status')!='PASS' or (old_build.get('layout_status')=='PASS' and new_build.get('layout_status')=='FAILED'):raise RuntimeError('Reference recompile failed; restored last successful output')
                build=new_build
            except Exception as exc:
                (folder/'review_en.tex').write_bytes(old_source);pdf.write_bytes(old_pdf)
                if old_aux is not None:aux.write_bytes(old_aux)
                elif aux.exists():aux.unlink()
                if old_report is not None:report_path.write_bytes(old_report)
                return old_tex,old_build,{'status':'UNVERIFIED','reason':type(exc).__name__+': '+str(exc)[:180],'passes':passes}
    except ReferenceCoverageError as exc:
        return tex,build,{'status':'UNVERIFIED','reason':str(exc)[:200],'passes':passes}
    except (ImportError,OSError,ValueError,KeyError,RuntimeError) as exc:
        return tex,build,{'status':'UNAVAILABLE','reason':type(exc).__name__+': '+str(exc)[:180],'passes':passes}
    return tex,build,{'status':'UNAVAILABLE','reason':'No successful current PDF build','passes':passes}

def make_overleaf_project(directory):
    """Create a source-only project; never include credentials, reports or other drafts."""
    from autonomous_delivery import copy_project_assets
    folder=Path(directory).resolve();project=folder/'overleaf_project'
    if project.exists():project=folder/('overleaf_project_'+uuid.uuid4().hex[:8])
    project.mkdir()
    source=(folder/'review_en.tex').read_bytes();(project/'main.tex').write_bytes(source)
    assets=copy_project_assets(folder,project,source.decode('utf-8'))
    if assets['missing']:raise ValueError('Overleaf source assets missing: '+','.join(assets['missing']))
    # A locally bundled standard package retains its original source and notices.
    support=folder/'tex_support'
    if (project/'cuted.sty').exists() and support.exists():
        for name in ('cuted.dtx','sttools.ins','README.md'):
            if (support/name).is_file():
                (project/'tex_support').mkdir(exist_ok=True);shutil.copyfile(support/name,project/'tex_support'/name)
    (project/'README.txt').write_text('Main file: main.tex\nCompiler: XeLaTeX\nReferences are embedded in main.tex; no BibTeX step is required.\nUpload the ZIP as an Overleaf project. The figures directory contains the vector assets.\nThe source package preserves the current research draft; compilation does not grant scientific approval.\n',encoding='utf-8')
    archive=folder/(project.name+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(project.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(project).as_posix())
    return {'status':'CREATED','main':str(project/'main.tex'),'directory':str(project),'zip':str(archive),'assets':assets,'compiler':'XeLaTeX'}
