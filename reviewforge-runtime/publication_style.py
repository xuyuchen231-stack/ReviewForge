"""Export-only prose presentation; no scientific rewriting or master-file mutation."""
import re
from manuscript_integrity import CITES, citekeys, tex_integrity
from bibliography_delivery import active_text,numeric_order_enabled


def prose_lists(tex):
    from editorial_refinement import split_document,_scientific_inventory,protected_spans,NUMBERS
    active=active_text(tex);stack=[];spans=[]
    lists={'itemize','enumerate','description'};narrative={'document','abstract','quote','quotation'}
    for match in re.finditer(r'\\(begin|end)\{([^{}]+)\}',active):
        action,name=match.groups()
        if action=='begin':
            eligible=name in lists and not any(env not in narrative for env,_ in stack)
            stack.append((name,match.start() if eligible else None))
        elif stack and stack[-1][0]==name:
            _,start=stack.pop()
            if start is not None:spans.append((start,match.end(),name))
    result=tex;retained=[];converted=0
    for start,end,name in reversed(spans):
        block=tex[start:end]
        masked=re.sub(r'\\(?:begin|end)\{(?:itemize|enumerate|description)\}',lambda m:' '*len(m.group(0)),active_text(block))
        protected=protected_spans(masked)
        item_labels=[m for m in re.finditer(r'\\label\{',active_text(block)) if not any(a<=m.start()<b for a,b in protected)]
        if item_labels:
            retained.append({'environment':name,'offset':start,'reason':'Referenced list labels need explicit prose revision'});continue
        block=re.sub(r'\\(?:begin|end)\{(?:itemize|enumerate|description)\}(?:\[[^]\n]*\])?','\n\n',block)
        block=re.sub(r'\\item(?![A-Za-z])(?:\[([^]\n]*)\])?',lambda m:'\n\n'+(r'\textbf{'+m.group(1)+'} ' if m.group(1) else ''),block)
        result=result[:start]+block+result[end:];converted+=1
    result=re.sub(r'(?m)^[ \t]*(?:\u2022|\\textbullet(?:\{\})?)[ \t]+','',result)
    before=''.join(split_document(tex)[1]);after=''.join(split_document(result)[1])
    safe=(citekeys(tex)==citekeys(result) and set(NUMBERS.findall(active_text(tex)))==set(NUMBERS.findall(active_text(result)))
          and _scientific_inventory(before)==_scientific_inventory(after) and tex_integrity(active_text(tex))==tex_integrity(active_text(result)))
    if not safe:return tex,{'status':'FAILED','reason':'Presentation edit failed scientific-content preservation','converted_lists':0,'retained_referenced_lists':retained}
    return result,{'status':'PASS' if not retained else 'NEEDS_REVIEW','converted_lists':converted,'retained_referenced_lists':retained}


def sorted_citation_groups(tex):
    if not numeric_order_enabled(tex):return tex
    entries=re.findall(r'\\bibitem(?:\[[^]]*\])?\{([^{}]+)\}',active_text(tex))
    rank={key:i for i,key in enumerate(entries)}
    if not rank:return tex
    for match in reversed(list(CITES.finditer(active_text(tex)))):
        command=re.match(r'\\([A-Za-z]+)',match.group(0)).group(1)
        if command not in {'cite','citep','parencite','autocite','footcite','supercite','citenum'}:continue
        keys=list(dict.fromkeys(k.strip() for k in match.group(1).split(',')))
        if len(keys)<2 or any(k not in rank for k in keys):continue
        keys.sort(key=rank.get)
        tex=tex[:match.start(1)]+','.join(keys)+tex[match.end(1):]
    return tex
