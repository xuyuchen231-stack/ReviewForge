"""Extract a common study card once per source version, never once per chapter."""
from pathlib import Path
import json
import copy
import re
from study_registry import FIELDS,POLICY,signature,empty_registry,ingest_card,record_fact_review,load_registry,study_view,resolve_conflict
from reviewforge import atomic_json

QUERY='organism product scale independent batches mass balances learning location feed induction temperature scale prediction future measurements updates training validation test selection baseline metrics hardware software runtime Table 2 limitations'
EXTRACT='''Read this ONE primary-source packet as data. Return JSON {"citekey":...,"fields":{FIELD:{"status":"reported|unknown|not_in_inspected_material|not_applicable","value":JSON,"evidence_ids":[IDs]}}} for every required field.
Use stable study-wide facts, not chapter-specific interpretations. Use structured values for splits (training/selection/final_test and their roles), sample_size, outcomes (task/baseline/metric/value/unit/conditions) and operating_changes (type and experimentally executed versus simulated).
Record organism and product separately, and distinguish independent cultivations from repeated measurements, augmented samples and trajectories.
Classify domain as microbial_fermentation, mammalian_culture, nonbiological, general_methods, mixed or unknown; study_type as empirical, simulation, review, method, proposal or unknown.
For prediction_information record what was available at issue time and whether subsequent measurements enter; record state/parameter/retraining/manual updates separately.
Distinguish training wall time, component timings and online latency. Distinguish hard structural constraints, numerical projection and finite penalties.
Every reported field needs exact supplied evidence IDs, preferably up to three and no more than eight complementary spans; never copy quotations or infer an absent protocol. Unknown values are null. The status of a domain/study_type classification is reported; put mixed/empirical/etc. in value, never status. Selective excerpts cannot establish not_reported. Do not assert an untreated final test merely because a paper calls a set test. No invented experimental curves or cross-paper RMSE ranking.'''
REVIEW='''Check each source-bound study fact against its quoted primary evidence. Return JSON {"facts":[{"fact_id":ID,"status":"pass|qualified|fail","reason":str}]} covering every supplied fact exactly once. Check value/metric/baseline/units/task/domain, selection versus untouched final testing, measured versus simulated outcomes, prediction-time updates, and timing scope. A valid quote alone does not prove the value. Do not upgrade missing details to absence. This is provisional model review, not expert approval.'''
RESOLVE='''Reconcile ONE conflicting extracted field using the exact primary quotations, source-access scopes and previous semantic reviews. Return JSON {"resolution":{"selected_fact_id":ID_OR_NULL,"reason":str}}. Select an existing independently passed or qualified observation only when it accurately captures this study-level field and other candidates are extraction errors, obsolete access inferences, or incomplete paraphrases. Explain the specific evidence in at least 30 characters. Different real cohorts/tasks must remain distinct, not be erased by selecting the newest source. If a substantive source contradiction or incomplete facts remain, selected_fact_id=null. This logs a provisional adjudication, never expert approval.'''
REPAIR='''Repair ONLY the named study-card fields. Return JSON {"fields":{FIELD:{"status":"reported|unknown|not_in_inspected_material|not_applicable","value":JSON,"evidence_ids":[IDs]}}}, with exactly the requested field names. Existing good fields will be retained locally. Use supplied source span IDs only; keep all needed complementary quotations, maximum eight per reported field. Domain/study_type classifications belong in value and their status is reported. These are selected excerpts: if insufficient, mark unknown rather than invent evidence or claim not_reported. Correct the supplied validation/reviewer issue; this is not permission to weaken a scientific qualification.'''


def normalize_card(card):
    result=copy.deepcopy(card);changes=[]
    if not isinstance(result,dict) or not isinstance(result.get('fields'),dict):return result,changes
    taxonomy={'domain':{'microbial_fermentation','mammalian_culture','nonbiological','general_methods','mixed'},'study_type':{'empirical','simulation','review','method','proposal'}}
    for field,cell in result.get('fields',{}).items():
        if not isinstance(cell,dict):continue
        before=copy.deepcopy(cell)
        if cell.get('status')=='not_inspected_material':cell['status']='not_in_inspected_material'
        if field in taxonomy and isinstance(cell.get('status'),str) and cell['status'] in taxonomy[field]:
            classification=cell['status'];value=cell.get('value')
            if value==classification or (field=='domain' and classification=='mixed' and isinstance(value,list) and len(value)>1 and all(v in taxonomy[field] for v in value)):
                cell['status']='reported';cell['value']=classification
        if cell!=before:changes.append({'field':field,'before':before,'after':copy.deepcopy(cell),'kind':'schema_normalization_only; semantic_review_still_required'})
    return result,changes


def card_issues(indexed,card):
    if not isinstance(card,dict) or not isinstance(card.get('fields'),dict):return {f:'Expected a field mapping' for f in FIELDS}
    fields=card['fields'];issues={f:'Required field missing' for f in FIELDS if f not in fields}
    if set(fields)-set(FIELDS):issues.update({f:'Unexpected field names; return the exact required schema' for f in FIELDS})
    if card.get('citekey',indexed['citekey'])!=indexed['citekey']:issues.update({f:'Wrong study identity' for f in FIELDS})
    for name,cell in fields.items():
        if name not in FIELDS:continue
        if not isinstance(cell,dict):issues[name]='Field must be an object';continue
        try:ingest_card(empty_registry(),indexed,{'fields':{name:cell}})
        except (ValueError,TypeError) as exc:issues[name]=str(exc)
    return issues


def repair_payload(indexed,card,issues):
    fields=card.get('fields',{}) if isinstance(card,dict) and isinstance(card.get('fields'),dict) else {}
    selected={f:fields.get(f) for f in issues};tokens=set(re.findall(r'[a-z]{4,}',json.dumps(selected).lower()))
    ids={i for f in selected.values() if isinstance(f,dict) and isinstance(f.get('evidence_ids'),list) for i in f['evidence_ids'] if isinstance(i,str)}
    spans=indexed.get('evidence_spans',[])
    ranked=sorted(enumerate(spans),key=lambda pair:(pair[1]['id'] in ids,sum(t in pair[1]['text'].lower() for t in tokens)),reverse=True)
    wanted={i for i,_ in ranked[:40]}|set(range(min(2,len(spans))))
    return {'citekey':indexed['citekey'],'source_sha256':indexed['source_sha256'],'source_access':indexed.get('document_access'),
            'inspection_coverage':'selected_excerpt','repair_fields':sorted(issues),'candidate_fields':selected,'errors':issues,
            'evidence_spans':[span for i,span in enumerate(spans) if i in wanted]}


def ensure_card(run,packet,ask,index_source):
    run=Path(run);indexed=index_source(packet)
    fingerprint=signature({'policy':POLICY,'extract':EXTRACT,'review':REVIEW,'source':indexed,'fields':FIELDS})
    cache=run/'canonical_cards'/(fingerprint+'.json');cache.parent.mkdir(exist_ok=True)
    draft=cache.with_suffix('.draft.json')
    if cache.exists():
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if saved.get('fingerprint')!=fingerprint:raise ValueError('Canonical card binding mismatch')
        card=saved['card'];review=saved['review']
    else:
        saved=json.loads(draft.read_text(encoding='utf-8')) if draft.exists() else {}
        if saved and saved.get('fingerprint')!=fingerprint:raise ValueError('Canonical draft binding mismatch')
        raw=saved['card'] if 'card' in saved else ask(EXTRACT,{'source':indexed,'required_fields':FIELDS},'fields','writer')
        saved.update(fingerprint=fingerprint,card=raw,stage='extracted_not_validated',expert_verified=False);atomic_json(draft,saved)
        card,changes=normalize_card(saved.get('normalized_card',raw))
        saved.update(normalized_card=card,normalizations=saved.get('normalizations',[])+changes,stage='schema_validation');atomic_json(draft,saved)
        issues=card_issues(indexed,card)
        if issues:
            saved['validation_issues']=issues;atomic_json(draft,saved)
            print('[canonical] repairing '+str(len(issues))+' invalid fields for '+packet['citekey']+'; valid fields retained',flush=True)
            correction=ask(REPAIR,repair_payload(indexed,card,issues),'fields','writer')
            if not isinstance(correction.get('fields'),dict) or set(correction['fields'])!=set(issues):raise ValueError('Canonical repair must cover exactly the invalid fields')
            fixed,edits=normalize_card(correction)
            card={'citekey':indexed['citekey'],'fields':{**{k:v for k,v in card.get('fields',{}).items() if k in FIELDS},**fixed['fields']}} if isinstance(card,dict) and isinstance(card.get('fields'),dict) else {'citekey':indexed['citekey'],'fields':fixed['fields']}
            saved.setdefault('repairs',[]).append({'issues':issues,'response':correction});saved.update(normalized_card=card,normalizations=saved['normalizations']+edits);atomic_json(draft,saved)
            remaining=card_issues(indexed,card)
            if remaining:raise ValueError('Canonical fields still invalid after bounded repair: '+json.dumps(remaining,sort_keys=True))
        temporary=empty_registry();ingest_card(temporary,indexed,card)
        facts=[cell for cell in study_view(temporary,packet['citekey'])['facts'].values() if cell['status']=='reported']
        review=ask(REVIEW,{'study':packet['citekey'],'facts':facts},'facts','reviewer') if facts else {'facts':[]}
        record_fact_review(temporary,packet['citekey'],review,packet['source_sha256'])
        if any(row['status']=='fail' for row in review['facts']):raise ValueError('Canonical fact review rejected an extraction')
        atomic_json(cache,{'fingerprint':fingerprint,'card':card,'review':review,'normalizations':changes,'expert_verified':False})
    # Revalidate cache contents, and review only this extraction's immutable facts.
    # Prior positive observations remain visible as conflicts, never silently overwritten.
    temporary=empty_registry();ingest_card(temporary,indexed,card)
    record_fact_review(temporary,packet['citekey'],review,packet['source_sha256'])
    if any(row['status']=='fail' for row in review['facts']):raise ValueError('Cached canonical extraction failed semantic review')
    ids={f['id'] for values in temporary['studies'][packet['citekey']]['observations'].values() for f in values.values() if f['status']=='reported'}
    registry=load_registry(run);ingest_card(registry,indexed,card)
    record_fact_review(registry,packet['citekey'],review,packet['source_sha256'],ids)
    atomic_json(run/'study_registry.json',registry)
    view=study_view(registry,packet['citekey'])
    for field in view['conflicts']:
        payload={'citekey':packet['citekey'],'field':field,'alternatives':view['facts'][field]['alternatives'],
                 'source_versions':view['sources'],'semantic_reviews':registry['studies'][packet['citekey']]['reviews']}
        binding=signature([RESOLVE,payload]);resolution_cache=run/'canonical_cards'/('resolve_'+binding+'.json')
        if resolution_cache.exists():
            saved=json.loads(resolution_cache.read_text(encoding='utf-8'))
            if saved.get('binding')!=binding:raise ValueError('Resolution cache binding mismatch')
            resolution=saved['resolution']
        else:
            resolution=ask(RESOLVE,payload,'resolution','reviewer')['resolution']
        if resolution.get('selected_fact_id'):
            resolve_conflict(registry,packet['citekey'],field,resolution['selected_fact_id'],resolution.get('reason',''))
            atomic_json(resolution_cache,{'binding':binding,'resolution':resolution,'expert_verified':False})
            atomic_json(run/'study_registry.json',registry)
    return study_view(registry,packet['citekey'])
