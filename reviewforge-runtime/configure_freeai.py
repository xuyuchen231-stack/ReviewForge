"""Add two existing Free.ai keys locally and test without exposing credentials."""
import argparse,getpass,json,os,time
from pathlib import Path
from reviewforge import CompatibleAPI,atomic_json

def profile(keys):
    if not keys or len(set(keys))!=len(keys) or any(not k.startswith('sk-free-') or any(c.isspace() or c in ',\"\'' for c in k) for k in keys):
        raise ValueError('Distinct existing sk-free- keys are required')
    return {'name':'freeai','enabled':True,'RF_BASE_URL':'https://api.free.ai/v1','RF_API_KEYS':','.join(keys),'RF_WRITER_MODEL':'qwen7b','RF_REVIEWER_MODEL':'qwen7b','RF_FALLBACK_MODEL':'qwen7b','RF_FREEAI_SELF_HOSTED_ONLY':'1','RF_FREEAI_MAX_INPUT_CHARS':'60000'}

def save_profile(path,keys):
    path=Path(path)
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'providers':[]}
    row=profile(keys)
    rows=[r for r in data.get('providers',[]) if r.get('name')!='freeai']
    rows.append(row);data['providers']=rows
    atomic_json(path,data)

def test_keys(keys):
    results=[]
    for i,key in enumerate(keys,1):
        api=CompatibleAPI(profile([key]));api.max_tokens=128;api.call_timeout=30;api.request_timeout=25
        try:
            result=api.chat('Return JSON only.','Return exactly {"ok":true}.','writer')
            from reviewforge import extract_json
            passed=extract_json(result)=={'ok':True}
            results.append({'slot':i,'suffix':key[-4:],'status':'PASS' if passed else 'RESPONSE_SCHEMA_FAILED','model':api.last_model,'usage':api.last_free_ai_usage})
        except Exception as exc:
            results.append({'slot':i,'suffix':key[-4:],'status':'FAILED','error_type':type(exc).__name__})
        print(json.dumps(results[-1],ensure_ascii=True),flush=True)
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--restart',action='store_true');parser.add_argument('--test-saved',action='store_true');args=parser.parse_args()
    target=Path(os.environ.get('RF_PROVIDER_FILE',str(Path.home()/'.reviewforge/providers.json')))
    if args.test_saved:
        data=json.loads(target.read_text(encoding='utf-8'));rows=[r for r in data['providers'] if r.get('name')=='freeai']
        if len(rows)!=1:raise ValueError('No saved Free.ai profile')
        keys=rows[0]['RF_API_KEYS'].split(',')
    else:
        keys=[getpass.getpass('Paste existing Free.ai API key '+str(i)+' (hidden), then Enter: ').strip() for i in (1,2)]
    profile(keys)
    results=test_keys(keys)
    runtime=Path(__file__).resolve().parent
    atomic_json(runtime/'workspace/reports/freeai_connection_test.json',{'observed_at_epoch':time.time(),'accounts':results,'scientific_quality_verified':False})
    if not all(r['status']=='PASS' for r in results):
        print('One or more tests failed; configuration unchanged, no restart.');return 1
    if not args.test_saved:save_profile(target,keys)
    print('Both Free.ai keys tested and configured. Self-hosted qwen7b only; requests above 60000 characters are skipped intact. TokenHarbor remains primary; APIMaster unchanged.')
    if args.restart:
        from prioritize_account import restart_runner
        print('Resumed process ID '+str(restart_runner(runtime)))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,EOFError,KeyboardInterrupt) as exc:
        print('Free.ai setup stopped ('+type(exc).__name__+'); secrets not printed.');raise SystemExit(1)
