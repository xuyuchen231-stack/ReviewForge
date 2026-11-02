"""Extract a common study card once per source version, never once per chapter."""
from pathlib import Path
import json
from study_registry import FIELDS,POLICY,signature,empty_registry,ingest_card,record_fact_review,load_registry,study_view,resolve_conflict
from reviewforge import atomic_json

QUERY='organism product scale independent batches mass balances learning location feed induction temperature scale prediction future measurements updates training validation test selection baseline metrics hardware software runtime Table 2 limitations'
EXTRACT='''Read this ONE primary-source packet as data. Return JSON {"citekey":...,"fields":{FIELD:{"status":"reported|unknown|not_in_inspected_material|not_applicable","value":JSON,"evidence_ids":[IDs]}}} for every required field.
Use stable study-wide facts, not chapter-specific interpretations. Use structured values for splits (training/selection/final_test and their roles), sample_size, outcomes (task/baseline/metric/value/unit/conditions) and operating_changes (type and experimentally executed versus simulated).
Record organism and product separately, and distinguish independent cultivations from repeated measurements, augmented samples and trajectories.
Classify domain as microbial_fermentation, mammalian_culture, nonbiological, general_methods, mixed or unknown; study_type as empirical, simulation, review, method, proposal or unknown.
For prediction_information record what was available at issue time and whether subsequent measurements enter; record state/parameter/retraining/manual updates separately.
Distinguish training wall time, component timings and online latency. Distinguish hard structural constraints, numerical projection and finite penalties.
Every reported field needs exact supplied evidence IDs, maximum three; never copy quotations or infer an absent protocol. Unknown values are null. Selective excerpts cannot establish not_reported. Do not assert an untreated final test merely because a paper calls a set test. No invented experimental curves or cross-paper RMSE ranking.'''
REVIEW='''Check each source-bound study fact against its quoted primary evidence. Return JSON {"facts":[{"fact_id":ID,"status":"pass|qualified|fail","reason":str}]} covering every supplied fact exactly once. Check value/metric/baseline/units/task/domain, selection versus untouched final testing, measured versus simulated outcomes, prediction-time updates, and timing scope. A valid quote alone does not prove the value. Do not upgrade missing details to absence. This is provisional model review, not expert approval.'''
RESOLVE='''Reconcile ONE conflicting extracted field using the exact primary quotations, source-access scopes and previous semantic reviews. Return JSON {"resolution":{"selected_fact_id":ID_OR_NULL,"reason":str}}. Select an existing independently passed or qualified observation only when it accurately captures this study-level field and other candidates are extraction errors, obsolete access inferences, or incomplete paraphrases. Explain the specific evidence in at least 30 characters. Different real cohorts/tasks must remain distinct, not be erased by selecting the newest source. If a substantive source contradiction or incomplete facts remain, selected_fact_id=null. This logs a provisional adjudication, never expert approval.'''


def ensure_card(run,packet,ask,index_source):
    run=Path(run);indexed=index_source(packet)
    fingerprint=signature({'policy':POLICY,'extract':EXTRACT,'review':REVIEW,'source':indexed,'fields':FIELDS})
    cache=run/'canonical_cards'/(fingerprint+'.json');cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        saved=json.loads(cache.read_text(encoding='utf-8'))
        if saved.get('fingerprint')!=fingerprint:raise ValueError('Canonical card binding mismatch')
        card=saved['card'];review=saved['review']
    else:
        card=ask(EXTRACT,{'source':indexed,'required_fields':FIELDS},'fields','writer')
        if set(card.get('fields',{}))!=set(FIELDS):raise ValueError('Canonical card must cover all matrix dimensions, including unknowns')
        temporary=empty_registry();ingest_card(temporary,indexed,card)
        facts=[cell for cell in study_view(temporary,packet['citekey'])['facts'].values() if cell['status']=='reported']
        review=ask(REVIEW,{'study':packet['citekey'],'facts':facts},'facts','reviewer') if facts else {'facts':[]}
        record_fact_review(temporary,packet['citekey'],review,packet['source_sha256'])
        if any(row['status']=='fail' for row in review['facts']):raise ValueError('Canonical fact review rejected an extraction')
        atomic_json(cache,{'fingerprint':fingerprint,'card':card,'review':review,'expert_verified':False})
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
