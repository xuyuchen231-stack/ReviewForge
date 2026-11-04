"""Test and save one existing BeatAPI key locally; exact free models only."""
import argparse,getpass,json,os,time
from pathlib import Path
from reviewforge import CompatibleAPI,atomic_json,extract_json

def profile(key):
    if len(key)<16 or any(c.isspace() or c in ',\"\'' for c in key):raise ValueError('A complete API key is required')
    return {'name':'beatapi','enabled':True,'RF_BASE_URL':'https://api.beatapi.io/v1','RF_API_KEY':key,'RF_WRITER_MODEL':'deepseek-v4.1-flash-free','RF_REVIEWER_MODEL':'deepseek-v4.1-flash-free','RF_FALLBACK_MODEL':'glm-5.3-flash-free','RF_BEATAPI_FREE_ONLY':'1','RF_BEATAPI_MAX_INPUT_CHARS':'120000'}

def save_profile(path,key):
    path=Path(path);data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'providers':[]}
    rows=[r for r in data.get('providers',[]) if r.get('name')!='beatapi'];rows.append(profile(key));data['providers']=rows
    atomic_json(path,data)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--restart',action='store_true');parser.add_argument('--test-saved',action='store_true');args=parser.parse_args()
    target=Path(os.environ.get('RF_PROVIDER_FILE',str(Path.home()/'.reviewforge/providers.json')))
    if args.test_saved:
        rows=[r for r in json.loads(target.read_text(encoding='utf-8'))['providers'] if r.get('name')=='beatapi']
        if len(rows)!=1:raise ValueError('No saved BeatAPI profile')
        key=rows[0]['RF_API_KEY']
    else:key=getpass.getpass('Paste existing BeatAPI API key (hidden), then Enter: ').strip()
    api=CompatibleAPI(profile(key));api.max_tokens=512;api.call_timeout=90;api.request_timeout=45;api.thinking_mode='disabled'
    row={'suffix':key[-4:],'status':'FAILED','observed_at_epoch':time.time(),'scientific_quality_verified':False}
    try:
        result=api.chat('Return JSON only.','Return exactly {"ok":true}.','writer')
        row.update(status='PASS' if extract_json(result)=={'ok':True} else 'RESPONSE_SCHEMA_FAILED',model=api.last_model,usage=api.last_usage)
    except Exception as exc:row['error_type']=type(exc).__name__
    runtime=Path(__file__).resolve().parent;atomic_json(runtime/'workspace/reports/beatapi_connection_test.json',row);print(json.dumps(row,ensure_ascii=True))
    if row['status']!='PASS':print('Test failed; configuration unchanged; no restart.');return 1
    if not args.test_saved:save_profile(target,key)
    print('BeatAPI configured: exact -free models only, 61-second free request spacing, no paid fallback. TokenHarbor and Free.ai retained; APIMaster unchanged.')
    if args.restart:
        from prioritize_account import restart_runner
        print('Resumed process ID '+str(restart_runner(runtime)))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,EOFError,KeyboardInterrupt) as exc:
        print('BeatAPI setup stopped ('+type(exc).__name__+'); secrets not printed.');raise SystemExit(1)
