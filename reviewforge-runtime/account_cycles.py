"""Local TokenHarbor free-period observations, keyed by credential fingerprints."""
import argparse,contextlib,datetime,hashlib,json,math,os,time,uuid
from pathlib import Path
from urllib.parse import urlsplit

WEEK=7*24*3600

def is_tokenharbor_free(base,model):
    url=urlsplit(base)
    return url.scheme=='https' and url.hostname in ('tokenharbor.ai','api.tokenharbor.ai') and isinstance(model,str) and model.endswith(':free')

def is_weekly_quota(status,data):
    if status==402:return True
    error=data.get('error',{}) if isinstance(data,dict) else {}
    text=' '.join(str(error.get(key,'')) for key in ('code','type','message')).lower() if isinstance(error,dict) else str(error).lower()
    return status in (403,429) and ('free' in text or 'weekly' in text) and any(word in text for word in ('quota','allowance','period')) and any(word in text for word in ('exhaust','exceed','used up','deplet'))

def fingerprint(base,key):return hashlib.sha256((base.rstrip('/')+'\0'+key).encode()).hexdigest()

class WeeklyAccounts:
    def __init__(self,path=None):self.path=Path(path or os.environ.get('RF_TOKENHARBOR_CYCLES_FILE',str(Path.home()/'.reviewforge/tokenharbor_cycles.json')))
    def _load(self):
        if not self.path.exists():return {'version':1,'accounts':{}}
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or not isinstance(data.get('accounts'),dict):raise ValueError('Invalid account-cycle ledger; original file preserved')
        return data
    @contextlib.contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.with_suffix('.lock').open('a+b') as handle:
            if handle.tell()==0:handle.write(b'0');handle.flush()
            handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
            try:yield
            finally:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
    def _update(self,base,key,change):
        with self._locked():
            data=self._load();row=data['accounts'].setdefault(fingerprint(base,key),{'base_url':base.rstrip('/')})
            result=change(row)
            temporary=self.path.with_name(self.path.name+'.'+uuid.uuid4().hex+'.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(self.path)
            return result
    def entry(self,base,key):return self._load()['accounts'].get(fingerprint(base,key),{}).copy()
    def set_reset_deadline(self,base,key,reset_at,safety_seconds=3600):
        reset=float(reset_at)
        if not math.isfinite(reset) or safety_seconds<0:raise ValueError('Invalid reset time or safety interval')
        def change(row):
            row.update(window_started_at=reset-WEEK,start_basis='user_dashboard_reset_countdown; cycle start inferred, not first-ever use',user_reported_reset_at=reset,reset_safety_seconds=safety_seconds,exhausted_until=reset+safety_seconds,status='weekly_free_quota_exhausted',server_window_confirmed=False)
        self._update(base,key,change)
    def success(self,base,key,started_at,basis='first_local_success',source=None):
        timestamp=float(started_at)
        if not math.isfinite(timestamp) or timestamp<0:raise ValueError('Invalid successful request time')
        def change(row):
            previous=row.get('first_success_observed_at');row['first_success_observed_at']=min(previous,timestamp) if previous is not None else timestamp
            window=row.get('window_started_at')
            if window is None or timestamp>=window+WEEK:
                row.update(window_started_at=timestamp,start_basis=basis,exhausted_until=0,status='observed_active_window')
            elif timestamp<window and previous==window and timestamp+WEEK>max(window,row.get('exhausted_at',0)):
                row.update(window_started_at=timestamp,start_basis=basis)
                if row.get('exhausted_until',0)>0:row['exhausted_until']=max(timestamp+WEEK,row.get('exhausted_at',0))
            row['last_success_observed_at']=max(timestamp,row.get('last_success_observed_at',0))
            row['server_window_confirmed']=False
            if source:row['historical_source']=str(source)
        self._update(base,key,change)
    def exhausted(self,base,key,at=None):
        now=time.time() if at is None else float(at)
        def change(row):
            window=row.get('window_started_at');until=(window+WEEK if window is not None and window+WEEK>now else now+WEEK)+row.get('reset_safety_seconds',0)
            row.update(exhausted_at=now,exhausted_until=until,status='weekly_free_quota_exhausted')
            if window is None:row['start_basis']='unknown; conservative retry upper bound'
            return until
        return self._update(base,key,change)
    def blocked(self,base,key,at=None):return self.entry(base,key).get('exhausted_until',0)>(time.time() if at is None else at)
    def report(self,base,keys,at=None):
        now=time.time() if at is None else at;result=[]
        def stamp(value):return datetime.datetime.fromtimestamp(value,datetime.timezone.utc).isoformat() if value is not None else None
        for index,key in enumerate(keys,1):
            row=self.entry(base,key);blocked=row.get('exhausted_until',0)>now;start=row.get('window_started_at')
            result.append({'account_slot':index,'first_success_observed_utc':stamp(row.get('first_success_observed_at')),'window_start_observed_utc':stamp(start),'next_window_check_utc':stamp(start+WEEK if start is not None else None),'quota_retry_utc':stamp(row.get('exhausted_until')) if row.get('exhausted_until') else None,'status':'weekly_exhausted' if blocked else ('eligible_to_retry' if row.get('exhausted_until') else ('observed_used' if start is not None else 'first_use_unknown')),'start_basis':row.get('start_basis'),'server_window_confirmed':False})
        return result

def backfill(workspace,ledger,base,keys):
    earliest={}
    for path in Path(workspace).rglob('*state.json'):
        try:data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        for row in data.get('model_routes',[]) if isinstance(data,dict) else []:
            slot=row.get('account_slot');stamp=row.get('utc');model=row.get('model','')
            if type(slot) is int and 1<=slot<=len(keys) and stamp and model.endswith(':free') and row.get('provider') in (None,'primary'):
                when=datetime.datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp()
                if slot not in earliest or when<earliest[slot][0]:earliest[slot]=(when,path)
    for slot,(when,path) in earliest.items():ledger.success(base,keys[slot-1],when,basis='historical_log; earliest available observation, not proven first-ever use',source=path)
    return len(earliest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',default='workspace');parser.add_argument('--backfill',action='store_true');parser.add_argument('--initialize',action='store_true');args=parser.parse_args()
    from reviewforge import load_env,CompatibleAPI
    load_env(Path(__file__).parent/'.env');api=CompatibleAPI();ledger=WeeklyAccounts()
    if not is_tokenharbor_free(api.base,api.model):raise SystemExit('Configured primary must be a TokenHarbor :free route; no request sent.')
    if args.backfill:backfill(args.workspace,ledger,api.base,api.keys)
    if args.initialize:api.prime_free_accounts(deadline=time.time()+60)
    report=ledger.report(api.base,api.keys);target=ledger.path.with_name('tokenharbor_accounts_report.json');target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'accounts':report,'report':str(target)},ensure_ascii=True))
