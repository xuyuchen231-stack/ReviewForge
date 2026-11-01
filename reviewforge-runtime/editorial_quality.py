"""Bounded publication diagnostics; model judgments never grant scientific approval."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from manuscript_integrity import CITES, citekeys, tex_integrity

POLICY='anchored-editorial-quality-v1'
ROLES={'state_vector':r'state vector|reactor state', 'biomass_scalar':r'biomass(?: concentration)?',
       'control_input':r'control inputs?|manipulated inputs?|operating inputs?|externally specified operations',
       'environmental_disturbance':r'environmental disturbances?|external disturbances?'}


def notation_audit(text):
    from editorial_refinement import active_tex
    active=active_tex(text);definitions=[]
    symbol=r'\$([^$\n]{1,65})\$'
    for role,words in ROLES.items():
        patterns=[r'\b(?:'+words+r')(?:\s+(?:is|are|denoted|represented|by|the|as|with)){0,5}\s*'+symbol,
                  r'\bby\s*'+symbol+r'\s+(?:the\s+|a\s+|an\s+)?(?:'+words+r')\b',
                  symbol+r'\s+(?:denotes|represents|is)\s+(?:the\s+|a\s+|an\s+)?(?:'+words+r')\b']
        for pattern in patterns:
            for match in re.finditer(pattern,active,re.I):
                displayed=match.group(1).strip();base=re.sub(r'\((?:t|k)\)$','',displayed)
                definitions.append({'role':role,'symbol':base,'displayed_symbol':displayed,'offset':match.start(),
                                    'line':active.count('\n',0,match.start())+1,'declaration':text[match.start():match.end()]})
    conflicts=[]
    for item in sorted({d['symbol'] for d in definitions}):
        rows=[d for d in definitions if d['symbol']==item]
        roles=sorted({r['role'] for r in rows})
        if len(roles)>1:conflicts.append({'symbol':item,'roles':roles,'definitions':rows,'action':'Check local scope and clarify definitions; no global rename.'})
    expansions=[]
    for match in re.finditer(r'\b([A-Za-z][A-Za-z-]*(?:[ \t]+[A-Za-z][A-Za-z-]*){1,9})[ \t]*\(([A-Z][A-Z0-9]{1,7})\)',active):
        words=match.group(1).split();acronym=match.group(2)
        for count in range(2,len(words)+1):
            tail=words[-count:]
            initials=''.join(w[0] for w in tail if w.lower() not in ('of','and','the','for')).upper()
            if initials==acronym:
                expansions.append({'acronym':acronym,'expansion':' '.join(tail),'offset':match.end()-len(match.group(0))+match.group(0).find(' '.join(tail))});break
    late=[];acronym_conflicts=[]
    for acronym in sorted({x['acronym'] for x in expansions}):
        rows=[x for x in expansions if x['acronym']==acronym]
        first=re.search(r'\b'+re.escape(acronym)+r'\b',active)
        if first and first.start()<min(x['offset'] for x in rows):late.append({'acronym':acronym,'first_use_offset':first.start(),'definition_offset':min(x['offset'] for x in rows)})
        if len({x['expansion'].lower() for x in rows})>1:acronym_conflicts.append({'acronym':acronym,'definitions':rows})
    return {'source_modified':False,'definitions':definitions,'conflicts':conflicts,
            'acronym_definitions':expansions,'late_definitions':late,'acronym_conflicts':acronym_conflicts,
            'scope':'Explicit adjacent declarations only; local mathematical examples may legitimately reuse symbols.'}


def evidence_index(workspace):
    """Read once. Original quotation provenance is retained; no fuzzy author matching."""
    path=Path(workspace)/'evidence_ledger.json'
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding='utf-8'))
    rows=data.get('entries',[]) if isinstance(data,dict) else data
    if not isinstance(rows,list):raise ValueError('Invalid evidence ledger')
    index={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('citekey'),str):continue
        index.setdefault(row['citekey'],[]).append(row)
    return index


def citation_context(workspace,text,budget=7000,index=None,max_keys=8):
    index=evidence_index(workspace) if index is None else index
    scores=Counter();positions={}
    for match in CITES.finditer(text):
        window=text[max(0,match.start()-350):match.end()+120]
        score=1+3*bool(re.search(r'control|transfer|outperform|improv|prospective|independent|causal',window,re.I))+bool(re.search(r'\d',window))
        for key in match.group(1).split(','):
            key=key.strip();scores[key]+=score;positions.setdefault(key,match.start())
    selected=sorted(scores,key=lambda k:(-scores[k],positions[k]))[:max_keys]
    anchors=[];missing=[];deferred=[]
    for key in selected:
        found=False
        for row in index.get(key,[]):
            quote=row.get('excerpt') or row.get('quote','')
            locator=row.get('locator') or row.get('evidence_location','')
            source_id=row.get('source_id') or row.get('doi','')
            if not all(isinstance(x,str) and x.strip() for x in (quote,locator,source_id)):continue
            excerpt=quote;offset=0
            if len(excerpt)>1000:
                sentences=list(re.finditer(r'[^.!?]+[.!?](?:\s|$)',quote))
                sentence=next((m for m in sentences if 50<=len(m.group(0))<=1000),None)
                if sentence is None:continue
                excerpt=sentence.group(0);offset=sentence.start()
            anchor={'citekey':key,'source_id':source_id,'locator':locator,'excerpt':excerpt,
                    'excerpt_offset_in_record':offset,'source_type':row.get('source_type','unknown'),
                    'verification_status':row.get('verification_status','unverified'),
                    'limitations':row.get('limitations','')}
            if len(json.dumps(anchors+[anchor],ensure_ascii=False))>budget:
                deferred.append(key);found=True;break
            anchors.append(anchor);found=True;break
        if not found:missing.append(key)
    selected=[k for k in selected if k not in deferred]
    return {'policy':POLICY,'selected_citekeys':selected,'anchors':anchors,'missing_citekeys':missing,
            'deferred_citekeys':sorted(set(scores)-set(selected)),
            'claim_offsets':{k:positions[k] for k in selected},'semantic_verification':False,
            'scope':'Bounded critical-citation sample in this chunk; not a full-source or whole-bibliography audit.'}


def context_digest(context):
    return hashlib.sha256(json.dumps(context,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def citation_passage_options(candidate,keys):
    options=[];counts=Counter()
    for match in CITES.finditer(candidate):
        for key in match.group(1).split(','):
            key=key.strip()
            if key not in keys or counts[key]>=3:continue
            start=max(0,match.start()-220);end=min(len(candidate),match.end()+100)
            passage=candidate[start:end].strip()
            identity=hashlib.sha256((key+'\0'+str(start)+'\0'+passage).encode()).hexdigest()[:16]
            options.append({'id':identity,'citekey':key,'start_anchor':passage[:65],'end_anchor':passage[-45:],'passage':passage})
            counts[key]+=1
    return options


def review_citations(review,context,candidate=None):
    rows=review.get('citation_checks',[])
    if isinstance(rows,list):
        lookup={r['id']:r for r in citation_passage_options(candidate or '',context['selected_citekeys'])}
        rows=[dict(r) if isinstance(r,dict) else r for r in rows]
        for row in rows:
            if isinstance(row,dict) and 'passage_id' in row:
                option=lookup.get(row['passage_id'])
                row['passage']=option['passage'] if option and option['citekey']==row.get('citekey') else ''
    expected=set(context['selected_citekeys']);anchored={r['citekey'] for r in context['anchors']}
    valid=isinstance(rows,list) and all(isinstance(r,dict) and r.get('status') in ('supported','qualified','unsupported','uncertain') and isinstance(r.get('reason'),str) and r['reason'].strip() for r in rows)
    complete=valid and Counter(r.get('citekey') for r in rows)==Counter(expected)
    if complete and any(r['status'] in ('supported','qualified') and r['citekey'] not in anchored for r in rows):complete=False
    if complete and candidate is not None and any(not isinstance(r.get('passage'),str) or len(r['passage'].strip())<12 or r['passage'] not in candidate for r in rows):complete=False
    return {'complete':bool(complete),'checks':rows if valid else [],
            'unsupported': [r['citekey'] for r in rows if isinstance(r,dict) and r.get('status')=='unsupported'] if valid else [],
            'uncertain':[r['citekey'] for r in rows if isinstance(r,dict) and r.get('status')=='uncertain'] if valid else [],
            'expert_verified':False}


def acceptance_report(text,build,citation_order,pages=None,citation_audit=None):
    from editorial_refinement import active_tex
    active=active_tex(text);integrity=tex_integrity(active)
    two_column=bool(re.search(r'\\documentclass\s*\[[^]]*\btwocolumn\b[^]]*\]',active))
    visual=build.get('visual_status','PENDING')
    technical=build.get('status')=='PASS' and build.get('layout_status')=='PASS' and visual!='FAILED' and citation_order.get('status') in ('PASS','NOT_APPLICABLE') and not integrity and two_column
    return {'policy':POLICY,'technical_ready':technical,'delivery_ready':technical and visual=='PASS','visual_status':visual,'two_column':two_column,
            'pages':pages,'target_pages':[25,30],'page_target_met':25<=pages<=30 if isinstance(pages,int) else None,
            'figure_count':len(re.findall(r'\\begin\{figure\*?\}',active)),
            'citation_order':citation_order.get('status','NOT_CHECKED'),'integrity_findings':integrity,
            'notation':notation_audit(text),'citation_audit':citation_audit or {'status':'NOT_RUN'},
            'expert_verified':False,'submission_ready':False,
            'scope':'Technical readiness is separate from page goal, evidence completeness and expert approval.'}
