"""Advisory coverage checks and source-verified, explicit citation repairs."""
import hashlib
import json
from pathlib import Path
import re
from manuscript_integrity import CITES,bibkeys


def intro_span(text):
    first=re.search(r'\\section\*?\{(?:Introduction|引言)\}',text,re.I)
    if not first:return None
    next_section=re.search(r'\\section\*?\{',text[first.end():])
    return first.end(),first.end()+next_section.start() if next_section else len(text)


def intro_citation_audit(text):
    from bibliography_delivery import active_text
    text=active_text(text)
    span=intro_span(text)
    if span is None:return {'status':'NOT_APPLICABLE','scope':'Introduction opening only'}
    intro=text[slice(*span)]
    intro=re.sub(r'\\begin\{(figure\*?|table\*?)\}[\s\S]*?\\end\{\1\}',' ',intro)
    first=re.compile(CITES.pattern,re.I).search(intro);prefix=intro[:first.start()] if first else intro
    prefix=re.sub(r'\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}[\s\S]*?\\end\{\1\}|\\\[[\s\S]*?\\\]|\$[^$]*\$',' ',prefix)
    prefix=re.sub(r'(?m)(?<!\\)%[^\n]*','',prefix)
    words=len(re.findall(r'\b[A-Za-z]{2,}\b',prefix));chinese=len(re.findall(r'[\u3400-\u9fff]',prefix))
    review=first is None or words>250 or chinese>700
    return {'status':'REVIEW' if review else 'PASS','english_words_before_first_citation':words,'chinese_characters_before_first_citation':chinese,
            'first_citekeys':first.group(1).split(',') if first else [],'scope':'Opening coverage indicator only; neither claim entailment nor whole-paper citation approval.',
            'action':'Inspect uncited background and mechanistic claims; add only source-supported citations.' if review else 'No unusually long uncited opening detected.'}


def apply_verified_patches(text,plan,workspace):
    span=intro_span(text)
    if span is None:return text,{'applied':0,'status':'NOT_APPLICABLE'}
    root=Path(workspace).resolve();intro=text[slice(*span)];known=bibkeys(text);applied=[]
    for patch in plan.get('patches',[]):
        if patch['before'] not in intro:continue
        if intro.count(patch['before'])!=1:raise ValueError('Ambiguous citation-repair anchor')
        if patch['citekey'] not in known:raise ValueError('Citation identity absent from manuscript bibliography')
        paths=[]
        for field,hash_field in (('source_text_file','source_text_sha256'),('identity_file','identity_sha256')):
            path=(root/patch[field]).resolve()
            if not path.is_relative_to((root/'primary_sources').resolve()):raise ValueError('Evidence path outside primary-source cache')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=patch[hash_field]:raise ValueError('Evidence identity changed')
            paths.append(path)
        metadata=paths[1].parent/'source.json'
        if paths[0].parent!=paths[1].parent or not metadata.is_file():raise ValueError('Text and identity must share a primary-source provenance record')
        record=json.loads(metadata.read_text(encoding='utf-8'))
        if record.get('sha256')!=patch['identity_sha256']:raise ValueError('Source metadata identity mismatch')
        doi=re.sub(r'^https?://(?:dx\.)?doi\.org/','',str(record.get('doi') or '').strip().lower())
        entry=re.search(r'\\bibitem(?:\[[^]]*\])?\{'+re.escape(patch['citekey'])+r'\}([\s\S]*?)(?=\\bibitem|\\end\{thebibliography\})',text)
        entry_dois=set(re.findall(r'10\.\d{4,9}/[^\s\\{}<>]+',entry.group(1).lower())) if entry else set()
        entry_dois={value.rstrip('.,;') for value in entry_dois}
        if not doi or doi not in entry_dois:raise ValueError('Evidence DOI does not match the cited bibliography entry')
        if paths[0].suffix=='.json':
            pages=json.loads(paths[0].read_text(encoding='utf-8'));evidence=' '.join(page.get('text','') if isinstance(page,dict) else str(page) for page in pages)
        else:evidence=paths[0].read_text(encoding='utf-8')
        normalize=lambda value:' '.join(value.split())
        if len(normalize(patch['quote']))<12 or normalize(patch['quote']) not in normalize(evidence):raise ValueError('Citation quote not found in source or too short')
        if '\\' in CITES.sub('',patch['after']):raise ValueError('Repair may add prose and citation commands only')
        if not any(patch['citekey'] in group.split(',') for group in CITES.findall(patch['after'])):raise ValueError('Expected supporting citation absent')
        if any(key.strip() not in known for group in CITES.findall(patch['after']) for key in group.split(',')):raise ValueError('Replacement introduces an unknown citation')
        intro=intro.replace(patch['before'],patch['after'],1)
        applied.append({'citekey':patch['citekey'],'source_text_file':patch['source_text_file'],'quote':patch['quote'],'source_sha256':patch['identity_sha256']})
    return text[:span[0]]+intro+text[span[1]:],{'applied':len(applied),'status':'APPLIED' if applied else 'UNCHANGED','anchors':applied,'expert_verified':False}
