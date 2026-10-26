"""Bounded source batches with exact-context, independently validated disk cards."""
import hashlib,json,os
from pathlib import Path
from reviewforge import atomic_json

POLICY='located-source-cards-v1'

def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def namespaced_source(source):
    prefix=signature(source['citekey'])[:12]+':'
    return {**source,'evidence_spans':[{**span,'id':prefix+span['id']} for span in source['evidence_spans']]}

def bounded_batches(sources,max_sources=3,max_bytes=36000):
    if not 1<=max_sources<=4 or max_bytes<1000:raise ValueError('Invalid extraction batch bounds')
    result=[];current=[]
    for source in sources:
        if len(json.dumps([source],ensure_ascii=False).encode('utf-8'))>max_bytes:raise ValueError('Source packet exceeds batch budget; curate source locations explicitly, do not silently truncate.')
        if current and (len(current)>=max_sources or len(json.dumps(current+[source],ensure_ascii=False).encode('utf-8'))>max_bytes):result.append(current);current=[]
        current.append(source)
    if current:result.append(current)
    return result

def extract_sources(run,unit_id,question,axes,packets,ask,index_source,normalize,materialize,validate,batch_size=None,seed_rows=()):
    run=Path(run);folder=run/'source_cache';folder.mkdir(exist_ok=True)
    indexed={p['citekey']:index_source(p) for p in packets};original={p['citekey']:p for p in packets}
    if len(original)!=len(packets):raise ValueError('Duplicate source packets')
    requests={key:{'schema_version':3,'question':question,'comparison_axes':axes,'sources':[source]} for key,source in indexed.items()}
    fingerprints={key:signature({'policy':POLICY,'request':request}) for key,request in requests.items()}
    results={};stats={'cache_hits':0,'legacy_hits':0,'requested_sources':0,'requests':0,'local_repairs':0}
    def save(key,row):
        atomic_json(folder/(fingerprints[key]+'.json'),{'policy':POLICY,'request_sha256':signature(requests[key]),'row':row})
        # Keep the old per-unit format usable by earlier local versions.
        atomic_json(run/'planning_cache'/unit_id/('study_'+signature(requests[key])+'.json'),row)
        results[key]=row
    for seed in seed_rows:
        try:
            key=seed['citekey']
            if key not in original:continue
            row=normalize(seed,axes)
            if validate(row,axes,original[key]) is not False:save(key,row)
        except (ValueError,TypeError,KeyError,AttributeError):continue
    for key,request in requests.items():
        if key in results:continue
        cached=folder/(fingerprints[key]+'.json');legacy=run/'planning_cache'/unit_id/('study_'+signature(request)+'.json')
        old_request={**request,'schema_version':2,'sources':[original[key]]}
        older=[run/'planning_cache'/unit_id/('study_'+signature(candidate)+'.json') for candidate in (old_request,{k:v for k,v in old_request.items() if k!='schema_version'})]
        for path in (cached,legacy,*older):
            if not path.exists():continue
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                if path==cached:
                    if data.get('policy')!=POLICY or data.get('request_sha256')!=signature(request):raise ValueError('Stale evidence cache')
                    data=data['row']
                row=normalize(data,axes)
                if row.get('citekey')!=key or validate(row,axes,original[key]) is False:raise ValueError('Invalid cached source card')
                save(key,row);stats['cache_hits' if path==cached else 'legacy_hits']+=1;break
            except (OSError,ValueError,TypeError,KeyError,AttributeError):continue
    def request_group(sources):
        stats['requests']+=1;stats['requested_sources']+=len(sources)
        response=ask(sources);rows=response.get('studies',[]) if isinstance(response,dict) else []
        wanted={p['citekey']:p for p in sources};bykey={}
        for row in rows if isinstance(rows,list) else []:
            if isinstance(row,dict) and row.get('citekey') in wanted:bykey.setdefault(row['citekey'],[]).append(row)
        failed=[]
        for key,source in wanted.items():
            try:
                if len(bykey.get(key,[]))!=1:raise ValueError('Missing or duplicate source card')
                row=materialize(normalize(bykey[key][0],axes),source)
                if validate(row,axes,original[key]) is False:raise ValueError('Invalid source card')
                save(key,row)
            except (ValueError,TypeError,KeyError,AttributeError):failed.append(source)
        return failed
    pending=[namespaced_source(source) for key,source in indexed.items() if key not in results]
    size=int(os.environ.get('RF_EVIDENCE_BATCH_SIZE','3')) if batch_size is None else batch_size
    try:
        for group in bounded_batches(pending,max_sources=size):
            failed=request_group(group)
            for source in failed:
                stats['local_repairs']+=1
                if request_group([source]):raise ValueError('Evidence record blocked after local repair: '+source['citekey'])
        return results
    finally:atomic_json(run/'reports'/(unit_id+'_extraction_stats.json'),stats)
