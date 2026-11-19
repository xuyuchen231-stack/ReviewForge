"""Offline recorded-usage audit. No prompts, secrets, API calls or manuscript edits."""
import argparse,collections,json
from pathlib import Path

def audit(run):
    reports=[]
    for path in sorted(run.rglob('requests.jsonl')):
        rows=[]; malformed=0
        for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
            try: rows.append(json.loads(line))
            except ValueError: malformed+=1
        if not rows:continue
        physical_bindings={r.get('binding') for r in rows if r.get('scope')=='transport'}
        physical=[r for r in rows if r.get('status') not in ('STARTED','CACHE_HIT') and
            (r.get('scope')=='transport' or r.get('binding') not in physical_bindings)]
        roles=collections.defaultdict(lambda: {'sends':0,'known_input':0,'known_output':0,'recorded_seconds':0})
        stages=collections.defaultdict(lambda: {'sends':0,'known_input':0,'known_output':0,'recorded_seconds':0})
        kinds={}
        for cache in (path.parent/'responses').glob('*.json'):
            data=json.loads(cache.read_text(encoding='utf-8')); response=data.get('response')
            if isinstance(response,dict):
                kind=next((label for field,label in [('facts','primary_fact_review'),('examined_unit_ids','cross_unit_review'),('accepted','paragraph_or_assembly_review'),('latex','writing'),('replacements','paragraph_repair'),('fields','source_extraction')] if field in response),'other_structured_response')
            else:kind='plain_text'
            kinds[data.get('binding')]=kind
        repeated=collections.Counter();unknown=0
        for row in physical:
            usage=row.get('usage',{});binding=row.get('binding')
            if binding:repeated[binding]+=1
            if not usage:unknown+=1
            for counter in (roles[row.get('role','unknown')], stages[kinds.get(binding,row.get('stage','unclassified'))]):
                counter['sends']+=1
                counter['known_input']+=usage.get('prompt_tokens',usage.get('input_tokens',0))
                counter['known_output']+=usage.get('completion_tokens',usage.get('output_tokens',0))
                counter['recorded_seconds']+=row.get('elapsed_seconds',0)
        reports.append({'journal':str(path.relative_to(run)),'roles':dict(roles),'response_kinds':dict(stages),
            'recorded_sends':len(physical),'extra_sends_under_same_binding':sum(n-1 for n in repeated.values()),
            'usage_missing_sends':unknown,'cache_hits':sum(r.get('status')=='CACHE_HIT' for r in rows),'malformed_lines':malformed,
            'identity_coverage':'Historical journals without logical_binding cannot establish cross-binding duplicate prompts. Repeated binding includes legitimate failed-send recovery; not automatically waste.'})
    return {'scope':'Recorded journals only; no extrapolation to unrecorded history. Physical sends suppress their duplicate logical journal entries. Durations are API-call time, not end-to-end elapsed time.',
        'new_provider_requests':0,'journals':reports}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=audit(a.run);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'journals':len(report['journals']),'new_provider_requests':0}))
