"""Append-only local usage journal. Never contains prompts or credentials."""
import json,os,time,uuid
from pathlib import Path

def known_refusal(row):
    return row.get('status')=='REFUSED' and row.get('error_type') in {'HTTP '+str(n) for n in (400,401,402,403,404,409,429)}


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
            'unknown_charge_attempts':sum(bool(r.get('charge_unknown')) and not known_refusal(r) for r in charged)+len(unfinished),
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
        self.append({**token,'status':status,'usage':clean,'charge_unknown':False if status=='CACHE_HIT' or known_refusal({'status':status,'error_type':error_type}) else (status!='RETURNED' or not clean),
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
        using_recovery=False
        if state['total']>=24:
            raise InputBudgetExceeded('Physical total-send budget exhausted; no further HTTP send made')
        if state['chargeable_or_unknown']>=3:
            grant_name='network_recovery' if state['chargeable_or_unknown']==3 else 'model_recovery' if state['chargeable_or_unknown']==4 else ''
            grant=state.get(grant_name,{})
            proof={k:v for k,v in grant.items() if k not in ('receipt_sha256','used')}
            import hashlib
            expected=hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest()
            if (not grant or grant.get('receipt_sha256')!=expected or grant.get('binding')!=self.binding
                    or grant.get('max_additional_sends')!=1 or grant.get('used')!=0
                    or state['chargeable_or_unknown']!=grant.get('baseline_chargeable')
                    or state['total']<grant.get('baseline_total',0)):
                raise InputBudgetExceeded('Physical request budget exhausted; no further HTTP send made')
            if grant.get('allowed_models') and model not in grant['allowed_models']:
                raise InputBudgetExceeded('Diagnosed model recovery is bound to its proven configured fallback')
            if [provider,slot] in grant['excluded_provider_slots']:
                raise InputBudgetExceeded('Diagnosed recovery must not resend to the proven failed account')
            grant['used']=1
            using_recovery=True

        state['total']+=1;state['chargeable_or_unknown']+=1;atomic_json(self.budget_path,state)
        token=self.journal.start(self.binding,self.role,self.input_chars,self.input_chars,scope='transport')
        token.update(model=model,account_slot=slot,provider=provider)
        if using_recovery:
            token['network_recovery_receipt']=grant['receipt_sha256']
            token['recovery_grant_name']=grant_name
        return token
    def finish(self,token,status,usage=None,http_status=None,error_type=None):
        from reviewforge import atomic_json
        if token.get('_finished'):return
        # HTTP refusals occur before a completion. Count them in total attempts
        # but do not spend the chargeable/unknown-response retry allowance.
        if http_status in (400,401,402,403,404,409,429):
            state=self.state();state['chargeable_or_unknown']-=1
            name=token.get('recovery_grant_name','network_recovery')
            if token.get('network_recovery_receipt')==state.get(name,{}).get('receipt_sha256') and token.get('network_recovery_receipt'):
                state[name]['used']=0
            atomic_json(self.budget_path,state)
        public={k:v for k,v in token.items() if not k.startswith('_')}
        self.journal.finish(public,status,usage or {},model=token['model'],slot=token['account_slot'],provider=token['provider'],error_type=error_type or ('HTTP '+str(http_status) if http_status else None))
        token['_finished']=True


def authorize_network_recovery(root,binding,fix_commit,diagnosis):
    """Operator-invoked one-potential-charge receipt after a documented network-routing fix.

    Never called by a provider response or automatic retry loop. Retains every old counter and journal
    row; successful responses/scientific refusals cannot justify this allowance.
    """
    import hashlib,re
    from reviewforge import atomic_json
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',binding):raise ValueError('Invalid request binding')
    if not re.fullmatch(r'[a-f0-9]{40}',fix_commit) or not isinstance(diagnosis,str) or not isinstance(diagnosis,str) or not diagnosis.strip():
        raise ValueError('Concrete diagnosis and fixed commit are required')
    tracker=TransportTracker(root,binding,'writer',0);state=tracker.state()
    existing=state.get('network_recovery')
    if existing:
        proof={k:v for k,v in existing.items() if k not in ('receipt_sha256','used')}
        if existing.get('binding')!=binding or existing.get('receipt_sha256')!=hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest():
            raise ValueError('Recovery receipt hash mismatch; retained state must be investigated')
        if existing.get('fix_commit')!=fix_commit or existing.get('diagnosis')!=diagnosis:
            raise ValueError('One diagnosed recovery already exists; no additional allowance')
        # Replay a previously written known-refusal receipt from before this
        # accounting fix. Do not decrement counters or grant another unknown send.
        rows=[json.loads(line) for line in tracker.journal.path.read_text(encoding='utf-8').splitlines() if line.strip()]
        extras=[r for r in rows if r.get('binding')==binding and r.get('scope')=='transport' and r.get('request_id') not in existing['prior_request_ids']]
        finished={r['request_id'] for r in extras if r.get('status')!='STARTED'}
        terminals=[r for r in extras if r.get('status')!='STARTED']
        if (existing.get('used')==1 and state.get('chargeable_or_unknown')==existing['baseline_chargeable']
                and terminals and all(known_refusal(r) for r in terminals)
                and all(r['request_id'] in finished for r in extras)):
            existing['used']=0;atomic_json(tracker.budget_path,state)
            tracker.journal.append({'scope':'budget','status':'RECOVERY_REFUSAL_RECONCILED','binding':binding,
                                    'receipt_sha256':existing['receipt_sha256'],'usage':{},'charge_unknown':False})
        return existing
    if state.get('chargeable_or_unknown')!=3 or state.get('total')!=3:
        raise ValueError('Recovery requires exactly the retained three failed sends')
    rows=[json.loads(line) for line in tracker.journal.path.read_text(encoding='utf-8').splitlines() if line.strip()]
    failures=[r for r in rows if r.get('binding')==binding and r.get('scope')=='transport' and r.get('status')!='STARTED']
    allowed={'TimeoutError','RemoteDisconnected','IncompleteRead','ConnectionResetError','ConnectionError'}
    if (len(failures)!=3 or any(r.get('status')!='FAILED' or r.get('error_type') not in allowed or r.get('usage') for r in failures)
            or len({(r.get('provider'),r.get('account_slot')) for r in failures})!=1):
        raise ValueError('Journal does not prove repeated network failures on one account')
    proof={'binding':binding,'fix_commit':fix_commit,'diagnosis':diagnosis.strip(),
           'max_additional_sends':1,'baseline_total':state['total'],'baseline_chargeable':state['chargeable_or_unknown'],
           'excluded_provider_slots':[[failures[0]['provider'],failures[0]['account_slot']]],
           'prior_request_ids':[r['request_id'] for r in failures],'created_epoch':time.time()}
    receipt={**proof,'receipt_sha256':hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest(),'used':0}
    state['network_recovery']=receipt;atomic_json(tracker.budget_path,state)
    tracker.journal.append({'scope':'budget','status':'DIAGNOSED_NETWORK_RECOVERY_GRANTED','binding':binding,
                            'receipt_sha256':receipt['receipt_sha256'],'max_additional_sends':1,'usage':{},'charge_unknown':False})
    return receipt


def authorize_model_recovery(root,binding,target_model,diagnosis):
    """One final route-specific send, with all previous sends still counted."""
    import hashlib,re
    from reviewforge import atomic_json
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',binding) or not isinstance(target_model,str) or not target_model.endswith(':free') or not isinstance(diagnosis,str) or not diagnosis.strip():
        raise ValueError('Exact free fallback route and concrete diagnosis required')
    tracker=TransportTracker(root,binding,'writer',0);state=tracker.state()
    existing=state.get('model_recovery')
    if existing:
        proof={k:v for k,v in existing.items() if k not in ('receipt_sha256','used')}
        if existing.get('binding')!=binding or existing.get('receipt_sha256')!=hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest():
            raise ValueError('Recovery receipt hash mismatch; retained state must be investigated')
        if existing.get('allowed_models')!=[target_model] or existing.get('diagnosis')!=diagnosis:
            raise ValueError('Final model recovery already exists; no further allowance')
        # Narrow a model-health diagnosis to the model. A failed preferred
        # model is not evidence that its account cannot serve the proven fallback.
        # Correct only an UNUSED receipt, retaining its original hash/history.
        if existing.get('used')==0 and existing.get('excluded_provider_slots') and state.get('chargeable_or_unknown')==existing['baseline_chargeable']:
            state.setdefault('model_recovery_history',[]).append(dict(existing))
            proof={k:v for k,v in existing.items() if k not in ('receipt_sha256','used')}
            proof.update(excluded_provider_slots=[],route_correction_reason='Preferred-model failures do not exclude accounts from an independently proven fallback route; same unspent allowance retained')
            existing={**proof,'receipt_sha256':hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest(),'used':0}
            state['model_recovery']=existing;atomic_json(tracker.budget_path,state)
            tracker.journal.append({'scope':'budget','status':'RECOVERY_ROUTE_SCOPE_CORRECTED','binding':binding,'receipt_sha256':existing['receipt_sha256'],'usage':{},'charge_unknown':False})
        return existing
    if state.get('chargeable_or_unknown')!=4 or state.get('network_recovery',{}).get('used')!=1:
        raise ValueError('Retain the exhausted network recovery before changing route')
    rows=[json.loads(line) for line in tracker.journal.path.read_text(encoding='utf-8').splitlines() if line.strip()]
    failures=[r for r in rows if r.get('binding')==binding and r.get('scope')=='transport' and r.get('status')=='FAILED' and r.get('error_type') in ('TimeoutError','RemoteDisconnected','IncompleteRead','ConnectionResetError')]
    preferred=[r for r in failures if r.get('model')!=target_model]
    success=[r for r in rows if r.get('scope')=='transport' and r.get('status')=='RETURNED' and r.get('role')=='writer' and r.get('model')==target_model and r.get('usage')]
    if len({(r.get('provider'),r.get('account_slot')) for r in preferred})<2 or not success:
        raise ValueError('Need failed preferred route on two accounts and a proven successful writer fallback')
    proof={'binding':binding,'diagnosis':diagnosis,'allowed_models':[target_model],
           'max_additional_sends':1,'baseline_total':state['total'],'baseline_chargeable':state['chargeable_or_unknown'],
           'excluded_provider_slots':[],
           'failed_request_ids':[r['request_id'] for r in preferred],
           'successful_route_request_id':success[-1]['request_id'],'created_epoch':time.time()}
    receipt={**proof,'receipt_sha256':hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest(),'used':0}
    state['model_recovery']=receipt;atomic_json(tracker.budget_path,state)
    tracker.journal.append({'scope':'budget','status':'DIAGNOSED_MODEL_RECOVERY_GRANTED','binding':binding,'receipt_sha256':receipt['receipt_sha256'],'max_additional_sends':1,'usage':{},'charge_unknown':False})
    return receipt
