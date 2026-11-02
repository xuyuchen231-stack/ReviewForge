"""One source-versioned study record shared by every manuscript consumer."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
from reviewforge import atomic_json

POLICY='canonical-study-facts-v2'
FIELDS=('domain','study_type','organism','product','system_scale','prediction_task','mechanistic_structure','learned_component',
        'conditioning_inputs','observations','prediction_information','update_policy','training_objective',
        'constraints','constraint_enforcement','sample_size','validation_split','baseline_tuning',
        'quantitative_results','operating_changes','uncertainty','failure_modes','hardware','software','computation_time','online_latency')
ACCESS={'anchor_only':0,'abstract_only':1,'publisher_excerpt':2,'full_text_excerpt':2,'full_text':3}


def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def empty_registry():return {'policy':POLICY,'studies':{},'expert_verified':False}
def load_registry(run):
    root=Path(run).resolve();path=root/'study_registry.json'
    active=root/'autonomous_active.json'
    if not path.exists() and active.exists():
        target=(root/json.loads(active.read_text(encoding='utf-8'))['run_directory']).resolve()
        if not target.is_relative_to(root):raise ValueError('Active study registry outside workspace')
        path=target/'study_registry.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else empty_registry()


def ingest_card(registry,packet,card):
    registry['policy']=POLICY
    key=packet['citekey'];sha=packet.get('source_sha256')
    if not sha:raise ValueError('Canonical source needs a content hash')
    if card.get('citekey',key)!=key:raise ValueError('Wrong canonical study identity')
    row=registry['studies'].setdefault(key,{'citekey':key,'sources':{},'observations':{},'reviews':{}})
    access=packet.get('document_access',packet.get('access','anchor_only'))
    source={'source_sha256':sha,'document_access':access,'source_type':packet.get('source_type','unknown'),
            'inspection_coverage':packet.get('inspection_coverage','selected_excerpt'),'source_text_file':packet.get('source_text_file',''),
            'source_id':packet.get('source_id') or packet.get('claim_anchor',{}).get('doi','')}
    row['sources'][sha]=source
    spans={s['id']:s for s in packet.get('evidence_spans',[])}
    for field,original in card.get('fields',{}).items():
        if field not in FIELDS:raise ValueError('Unknown canonical field: '+field)
        status=original.get('status');value=original.get('value')
        if status not in ('reported','unknown','not_in_inspected_material','not_reported','not_applicable'):raise ValueError('Invalid canonical fact status: '+field)
        anchors=[]
        if status=='reported':
            ids=original.get('evidence_ids',[])
            if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in spans for i in ids) or len(set(ids))!=len(ids) or value is None or value=='':raise ValueError('Unanchored canonical fact: '+field)
            anchors=[{'span_id':i,'excerpt':spans[i]['text'],'locator':spans[i]['locator'],'source_sha256':sha} for i in ids]
            if isinstance(value,(int,float)) and not isinstance(value,bool):
                if not re.search(r'(?<![\d.])'+re.escape(str(value))+r'(?![\d.])',' '.join(a['excerpt'] for a in anchors)):
                    raise ValueError('Numeric fact absent from supporting quotation: '+field)
        if status=='not_reported':
            inspection=original.get('inspection',{})
            if access!='full_text' or source['inspection_coverage']!='complete_document' or not inspection.get('sections_checked') or not inspection.get('search_terms'):
                raise ValueError('Selective or abstract access cannot establish not reported')
        fact={'field':field,'context':original.get('context','study'),'status':status,'value':value,'anchors':anchors,
              'source_sha256':sha,'inspection':original.get('inspection',{}),'quote_verified':bool(anchors),'semantic_verified':False}
        fact['id']=signature(fact)
        row['observations'].setdefault(field,{})[fact['id']]=fact
    return row


def study_view(registry,key):
    row=registry.get('studies',{}).get(key)
    if row is None:return {'citekey':key,'status':'NOT_EXTRACTED','facts':{},'sources':[],'conflicts':[]}
    cells={};conflicts=[]
    for field,observations in row['observations'].items():
        excluded=set(row.get('resolutions',{}).get(field,{}).get('superseded_fact_ids',[]))
        facts=[f for f in observations.values() if f['id'] not in excluded];positive=[f for f in facts if f['status']=='reported'];negative=[f for f in facts if f['status']=='not_reported']
        contexts={}
        for fact in positive:contexts.setdefault(fact['context'],{}).setdefault(signature(fact['value']),[]).append(fact)
        conflict=any(len(values)>1 for values in contexts.values()) or bool(positive and negative)
        if conflict:
            cells[field]={'status':'conflict','value':None,'fact_ids':[f['id'] for f in positive+negative],'alternatives':positive+negative};conflicts.append(field);continue
        selected=positive or negative or facts
        best=max(selected,key=lambda f:(f['status']=='reported',row.get('reviews',{}).get(f['id'],{}).get('status') in ('pass','qualified'),ACCESS.get(row['sources'][f['source_sha256']]['document_access'],0)))
        cells[field]={**best,'fact_ids':[f['id'] for f in selected],
                      'semantic_status':row.get('reviews',{}).get(best['id'],{}).get('status','not_reviewed'),
                      'semantic_review':row.get('reviews',{}).get(best['id'],{})}
        if len(contexts)>1:cells[field]['context_values']={c:next(iter(values.values()))[0]['value'] for c,values in contexts.items()}
    sources=sorted(row['sources'].values(),key=lambda s:(ACCESS.get(s['document_access'],0),s['source_sha256']),reverse=True)
    return {'citekey':key,'status':'CONFLICT' if conflicts else 'RECORDED','facts':cells,'sources':sources,'conflicts':conflicts,'expert_verified':False}


def facts_for_studies(registry,keys):return [study_view(registry,key) for key in sorted(set(keys))]
def registry_digest(registry,keys):return signature(facts_for_studies(registry,keys))


def eligible_facts(registry):
    return {cell['id']:(key,cell) for key in registry['studies'] for cell in study_view(registry,key)['facts'].values()
            if cell['status']=='reported' and cell.get('semantic_status') in ('pass','qualified')}


def resolve_conflict(registry,key,field,selected_id,reason):
    """Explicit, logged adjudication; retains rejected observations and their quotations."""
    row=registry['studies'][key];observations=row['observations'][field]
    if selected_id not in observations or observations[selected_id]['status']!='reported' or len(reason.strip())<30:raise ValueError('Resolution needs a supported observation and substantive rationale')
    if row.get('reviews',{}).get(selected_id,{}).get('status') not in ('pass','qualified'):raise ValueError('Resolution cannot select an unreviewed fact')
    row.setdefault('resolutions',{})[field]={'selected_fact_id':selected_id,'superseded_fact_ids':[i for i in observations if i!=selected_id],
                                           'reason':reason,'expert_verified':False}


def compact_facts(registry,keys):
    result=[]
    for view in facts_for_studies(registry,keys):
        if view['status']=='NOT_EXTRACTED':continue
        result.append({'citekey':view['citekey'],'status':view['status'],'conflicts':view['conflicts'],
                       'source_access':[{'source_sha256':s['source_sha256'],'document_access':s['document_access'],'inspection_coverage':s['inspection_coverage']} for s in view['sources']],
                       'facts':{field:{name:cell.get(name) for name in ('id','status','value','semantic_status','semantic_review','fact_ids')} for field,cell in view['facts'].items() if cell['status'] in ('reported','conflict','not_reported')}})
    return result


def record_fact_review(registry,key,report,source_sha256=None,fact_ids=None):
    row=registry['studies'][key];facts={f['id']:f for values in row['observations'].values() for f in values.values() if f['status']=='reported' and (source_sha256 is None or f['source_sha256']==source_sha256) and (fact_ids is None or f['id'] in fact_ids)}
    if fact_ids is not None and set(facts)!=set(fact_ids):raise ValueError('Review refers to unknown current card facts')
    verdicts=report.get('facts',[])
    if Counter(v.get('fact_id') for v in verdicts)!=Counter(facts.keys()):raise ValueError('Fact review must cover each reported fact exactly once')
    for verdict in verdicts:
        if verdict.get('status') not in ('pass','fail','qualified') or not verdict.get('reason'):raise ValueError('Invalid fact semantic review')
        row['reviews'][verdict['fact_id']]={**verdict,'review_kind':'provisional_model_or_assistant_review','expert_verified':False}


def overlay_matrix(matrix,registry):
    result=json.loads(json.dumps(matrix))
    for row in result.get('studies',[]):
        key=row['citekey'];view=study_view(registry,key)
        if view['status']=='NOT_EXTRACTED':continue
        row['canonical_study']=view;row['registry_digest']=registry_digest(registry,{key})
        row['fact_precedence']='Current canonical facts override legacy chapter-specific descriptions; access limitations are audit metadata, not findings.'
        for legacy in row.get('fields',{}).values():
            if legacy.get('status') in ('not_accessible','not_reported'):
                legacy.update(status='not_accessible',value='',legacy_access_inference_removed=True)
        if view['sources']:
            row['source_type']=view['sources'][0]['source_type']
            row['source_text_file']=view['sources'][0].get('source_text_file',row.get('source_text_file',''))
        for field,cell in view['facts'].items():
            if cell['status']=='reported' and cell.get('semantic_status') in ('pass','qualified'):
                anchor=cell['anchors'][0];row.setdefault('fields',{})[field]={'status':'supported','value':cell['value'],'excerpt':anchor['excerpt'],'locator':anchor['locator'],'canonical_fact_id':cell['id']}
            elif cell['status'] in ('conflict','reported'):row.setdefault('fields',{})[field]={'status':'not_accessible','value':'','canonical_conflict':cell['status']=='conflict','canonical_semantic_status':cell.get('semantic_status','not_reviewed')}
    return result


def evidence_rows(registry):
    rows=[]
    for key in sorted(registry['studies']):
        view=study_view(registry,key)
        for field,cell in view['facts'].items():
            if cell['status']!='reported' or cell.get('semantic_status') not in ('pass','qualified'):continue
            source=registry['studies'][key]['sources'][cell['source_sha256']]
            for anchor in cell['anchors']:
                rows.append({'citekey':key,'claim':field+': '+json.dumps(cell['value'],ensure_ascii=False),'excerpt':anchor['excerpt'],'locator':anchor['locator'],
                             'source_id':source.get('source_id') or cell['source_sha256'],'source_type':source['source_type'],'source_sha256':cell['source_sha256'],
                             'verification_status':'quote_checked; semantic_'+cell.get('semantic_status','not_reviewed'),'canonical_fact_id':cell['id'],'canonical_field':field,
                             'limitations':'Source-bound canonical study fact; provisional semantic review, not expert verification.'})
    return rows


def export_matrix(run,registry):
    folder=Path(run)/'reports';folder.mkdir(exist_ok=True)
    records=[]
    for key in sorted(registry['studies']):
        view=study_view(registry,key)
        for field in FIELDS:
            cell=view['facts'].get(field,{'status':'unknown','value':None});anchors=cell.get('anchors',[])
            records.append({'citekey':key,'field':field,'status':cell['status'],'value':json.dumps(cell.get('value'),ensure_ascii=False),
                            'fact_ids':';'.join(cell.get('fact_ids',[])),'source_sha256':cell.get('source_sha256',''),
                            'locators':' | '.join(a['locator'] for a in anchors),'quotations':' | '.join(a['excerpt'] for a in anchors),
                            'semantic_status':cell.get('semantic_status','not_reviewed')})
    target=folder/'study_evidence_matrix.csv'
    # Python 3.10's CSV writer treats NUL as its unset escape character.
    # Show PDF extraction control glyphs visibly in CSV; keep exact originals in JSON.
    display=lambda rows:({k:v.replace('\x00','\u2400') if isinstance(v,str) else v for k,v in row.items()} for row in rows)
    with target.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]) if records else ['citekey','field','status']);writer.writeheader();writer.writerows(display(records))
    atomic_json(folder/'study_evidence_matrix.json',{'policy':POLICY,'studies':facts_for_studies(registry,registry['studies']),'expert_verified':False,'csv_display_note':'NUL glyphs are displayed as U+2400 in CSV only; exact original quotations and source hashes remain in this JSON.'})
    # One row per study for actual horizontal comparison; long-form remains the provenance ledger.
    wide=[]
    for key in sorted(registry['studies']):
        view=study_view(registry,key);facts=view['facts']
        domain=facts.get('domain',{}).get('value','unknown');kind=facts.get('study_type',{}).get('value','unknown')
        cohort='microbial_'+str(kind) if domain=='microbial_fermentation' else 'adjacent_or_background'
        wide.append({'citekey':key,'cohort':cohort,**{f:json.dumps(facts[f]['value'],ensure_ascii=False) if f in facts and facts[f]['status']=='reported' else 'UNKNOWN' for f in FIELDS},
                     'source_access':'; '.join(sorted({s['document_access'] for s in view['sources']})),
                     'conflicts':'; '.join(view['conflicts'])})
    with (folder/'study_comparison_wide.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['citekey','cohort',*FIELDS,'source_access','conflicts']);writer.writeheader();writer.writerows(display(wide))
    return {'path':str(target),'studies':len(registry['studies']),'rows':len(records),'expert_verified':False}
