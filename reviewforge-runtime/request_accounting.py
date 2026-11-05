"""Append-only local usage journal. Never contains prompts or credentials."""
import json,os,time,uuid
from pathlib import Path

def usage_summary(path):
    """Known provider usage only; unknown failures remain explicitly unknown."""
    rows=[]
    if Path(path).exists():
        for line in Path(path).read_text(encoding='utf-8',errors='replace').splitlines():
            try:rows.append(json.loads(line))
            except ValueError:continue # May observe an unfinished append while monitoring.
    physical={r.get('binding') for r in rows if r.get('scope')=='transport'}
    charged=[r for r in rows if r.get('status')!='STARTED' and (r.get('scope')=='transport' or r.get('binding') not in physical)]
    finished={r.get('request_id') for r in rows if r.get('status')!='STARTED'}
    unfinished=[r for r in rows if r.get('status')=='STARTED' and r.get('request_id') not in finished and (r.get('scope')=='transport' or r.get('binding') not in physical)]
    return {'prompt_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in charged),
            'completion_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in charged),
            'cache_hits':sum(r.get('status')=='CACHE_HIT' for r in rows),
            'unknown_charge_attempts':sum(bool(r.get('charge_unknown')) for r in charged)+len(unfinished),
            'scope':'new append-only journal only; excludes unrecorded historical usage'}

class RequestJournal:
    def __init__(self,path):self.path=Path(path)
    def append(self,row):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(row,ensure_ascii=True,separators=(',',':'))+'\n');stream.flush();os.fsync(stream.fileno())
    def start(self,binding,role,input_chars,before_chars,scope='logical'):
        token={'request_id':uuid.uuid4().hex,'binding':binding,'role':role,'started_epoch':time.time(),'scope':scope}
        self.append({**token,'status':'STARTED','input_chars':input_chars,'input_chars_before':before_chars})
        return token
    def finish(self,token,status,usage,model=None,slot=None,provider=None,error_type=None):
        clean={k:v for k,v in (usage or {}).items() if k in ('prompt_tokens','completion_tokens','total_tokens') and type(v) is int and v>=0}
        self.append({**token,'status':status,'usage':clean,'charge_unknown':False if status=='CACHE_HIT' else (status!='RETURNED' or not clean),
                     'elapsed_seconds':round(time.time()-token['started_epoch'],3),'model':model,'account_slot':slot,'provider':provider,'error_type':error_type})

class TransportTracker:
    """Reserve and journal each actual HTTP send, including nested fallbacks."""
    def __init__(self,root,binding,role,input_chars):
        self.root=Path(root);self.binding=binding;self.role=role;self.input_chars=input_chars
        self.journal=RequestJournal(self.root/'requests.jsonl')
        self.budget_path=self.root/'transport_attempts'/(binding+'.json')
    def state(self):
        return json.loads(self.budget_path.read_text(encoding='utf-8')) if self.budget_path.exists() else {'total':0,'chargeable_or_unknown':0}
    def reserve(self,model,slot,provider):
        from reviewforge import atomic_json
        from efficient_payload import InputBudgetExceeded
        state=self.state()
        if state['chargeable_or_unknown']>=3 or state['total']>=24:
            raise InputBudgetExceeded('Physical request budget exhausted; no further HTTP send made')
        state['total']+=1;state['chargeable_or_unknown']+=1;atomic_json(self.budget_path,state)
        token=self.journal.start(self.binding,self.role,self.input_chars,self.input_chars,scope='transport')
        token.update(model=model,account_slot=slot,provider=provider)
        return token
    def finish(self,token,status,usage=None,http_status=None,error_type=None):
        from reviewforge import atomic_json
        if token.get('_finished'):return
        # HTTP refusals occur before a completion. Count them in total attempts
        # but do not spend the chargeable/unknown-response retry allowance.
        if http_status in (400,401,402,403,404,409,429):
            state=self.state();state['chargeable_or_unknown']-=1;atomic_json(self.budget_path,state)
        public={k:v for k,v in token.items() if not k.startswith('_')}
        self.journal.finish(public,status,usage or {},model=token['model'],slot=token['account_slot'],provider=token['provider'],error_type=error_type or ('HTTP '+str(http_status) if http_status else None))
        token['_finished']=True
