"""Timeboxed reading-copy delivery from a verified complete editorial baseline.

This restores the old delivery scope, not scientific approval of rejected revisions.
"""
import json,time,math,os,sys
from pathlib import Path
from reviewforge import atomic_json


def completed_baseline(run):
    from editorial_refinement import sha
    editorial=(Path(run)/'editorial').resolve()
    for path in sorted(editorial.glob('*/status.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('status')!='COMPLETE':continue
        entry=record.get('versions',{}).get('condense',{});source=Path(entry.get('path','')).resolve()
        if not source.is_relative_to(editorial) or not source.is_file():continue
        if sha(source.read_text(encoding='utf-8'))!=entry.get('sha256'):raise ValueError('Completed baseline hash mismatch')
        return source,record
    raise ValueError('No verified complete editorial baseline; refusing to substitute an incomplete chapter')


def run_stable(workspace,hours=4):
    if not math.isfinite(hours) or not 1<=hours<=8:raise ValueError('Delivery budget must be between one and eight hours')
    ws=Path(workspace).resolve();active=json.loads((ws/'autonomous_active.json').read_text(encoding='utf-8'))
    run=(ws/active['run_directory']).resolve()
    if not run.is_relative_to(ws):raise ValueError('Run outside workspace')
    source,baseline=completed_baseline(run)
    from continuous_revision import claim_worker
    worker_lock=claim_worker(run)
    try:
        return _run_stable_job(ws,run,source,baseline,hours)
    except Exception as exc:
        route=run/'workflow_route.json'
        if route.exists():
            state=json.loads(route.read_text(encoding='utf-8'))
            if state.get('process_id')==os.getpid():
                state.update(status='NEEDS_ATTENTION',reason=type(exc).__name__+': '+str(exc)[:300],finished_epoch=time.time())
                atomic_json(route,state)
        raise
    finally:worker_lock.close()


def _run_stable_job(ws,run,source,baseline,hours):
    started=time.time();deadline=started+hours*3600
    job=run/'editorial'/('reading_'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_'+str(os.getpid()))
    job.mkdir(parents=True,exist_ok=False)
    # Never reuse an old PDF or an incomplete reconstructed manuscript.
    snapshot=job/'refined.tex';snapshot.write_bytes(source.read_bytes())
    from editorial_refinement import sha,resilient_request
    result={'status':'COMPLETE','source_sha256':baseline.get('source_sha256'),'expert_verified':False,
            'submission_ready':False,'delivery_scope':'Reading copies of the last complete editorial manuscript; scientific major revision remains unresolved',
            'versions':{'condense':{'path':str(snapshot),'sha256':sha(snapshot.read_text(encoding='utf-8'))}},
            'citation_audit':baseline.get('citation_audit',{}),'run_started_epoch':started}
    known=[]
    for p in (run/'major_revision').glob('*/[1-7]_*.json'):
        r=json.loads(p.read_text(encoding='utf-8'))
        if not r.get('accepted') and r.get('review'):known.append({'checkpoint':str(p),'review':r['review']})
    atomic_json(job/'unresolved_scientific_reviews.json',{'records':known,'scientific_approval':False})
    route=run/'workflow_route.json'
    state={'kind':'stable_delivery','status':'RUNNING','process_id':os.getpid(),'started_epoch':started,
           'deadline_epoch':deadline,'source':str(source),'job':str(job),'output':str(job/'short/output/output'),
           'expert_verified':False,'submission_ready':False}
    atomic_json(route,state)
    from reviewforge import CompatibleAPI,load_env
    from account_cycles import is_tokenharbor_free
    from freeai_provider import allowed_freeai
    from beatapi_provider import allowed_beatapi
    from major_revision import provider_request
    load_env(Path(__file__).parent/'.env');api=CompatibleAPI()
    if not all(is_tokenharbor_free(api.base,m) for m in (api.model,api.reviewer_model,api.fallback_model)):
        raise ValueError('Stable route requires configured free TokenHarbor primary models')
    api.providers=[p for p in api.providers if all(is_tokenharbor_free(p.base,m) for m in (p.model,p.reviewer_model,p.fallback_model)) or allowed_freeai(p) or allowed_beatapi(p)]
    api.execution_root=job/'model_requests';api.thinking_mode='disabled'
    def chat(system,payload,role):
        bound=min(deadline,payload.get('_delivery_deadline',deadline))
        payload={k:v for k,v in payload.items() if k!='_delivery_deadline'}
        if time.time()>=bound:raise TimeoutError('Reading-copy delivery budget exhausted')
        def retry(request,request_deadline):
            api.deadline=min(api.deadline,bound)
            return resilient_request(request,min(request_deadline,bound))
        print('[stable-delivery] '+role+' request; bounded translation/export only',flush=True)
        return provider_request(api,system,payload,None,role,retry=retry)
    try:
        from editorial_export import finalize_versions
        print('[stable-delivery] verified complete baseline; skipping seven-section reconstruction and repeated editorial passes',flush=True)
        result=finalize_versions(run,result,deadline,chat=chat)
        atomic_json(job/'result.json',result)
        export=result.get('exports',{}).get('condense',{})
        report=export.get('report',{})
        built=all(report.get(k,{}).get('status')=='PASS' for k in ('review_en_build','review_zh_build'))
        built=built and all((Path(state['output'])/name).is_file() and (Path(state['output'])/name).stat().st_size>0 for name in ('review_en.pdf','review_zh.pdf'))
        state.update(status='READING_COPIES_BUILT' if built else 'NEEDS_ATTENTION',export_status=export.get('status'),
                     report=str(job/'result.json'),finished_epoch=time.time())
    except Exception as exc:
        state.update(status='NEEDS_ATTENTION',reason=type(exc).__name__+': '+str(exc)[:300],finished_epoch=time.time())
        atomic_json(route,state);raise
    atomic_json(route,state);print(json.dumps(state,ensure_ascii=True));return state
