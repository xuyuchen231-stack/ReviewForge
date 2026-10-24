"""ReviewForge minimal autonomous writing engine (standard library)."""
from __future__ import annotations
import datetime as dt
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import urllib.error


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def load_env(path):
    """Load local overrides, then persistent per-user configuration.

    Explicit process environment variables take priority. The project-local
    .env is supported for backward compatibility; the per-user config survives
    cloning, upgrading, or moving the repository.
    """
    paths = [Path(path), Path.home() / '.reviewforge' / 'credentials.env']
    for p in paths:
        if not p.is_file():
            continue
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if k.strip().startswith('RF_'):
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def validate_ledger(ledger, sources):
    """Verify quotation provenance, not semantic truth."""
    if not isinstance(ledger, list) or not ledger: return False, ['Missing claim ledger']
    index = {x['id']: x for x in sources if isinstance(x, dict) and 'id' in x}
    errors = []
    for n, claim in enumerate(ledger):
        if not isinstance(claim, dict): errors.append(f'{n}: invalid record'); continue
        sid = claim.get('source_id'); loc = claim.get('locator'); quote = claim.get('quote')
        if not claim.get('claim') or claim.get('status') != 'supported':
            errors.append(f'{n}: unresolved claim'); continue
        if not isinstance(quote, str) or len(quote.strip()) < 12:
            errors.append(f'{n}: missing meaningful quote'); continue
        src = index.get(sid)
        if not src or not any(e.get('locator') == loc and quote in e.get('text','') for e in src.get('excerpts',[]) if isinstance(e,dict)):
            errors.append(f'{n}: quote not anchored to source/locator')
    return not errors, errors


def extract_json(content):
    content = content.strip()
    if content.startswith('```'):
        lines = content.splitlines()
        if lines[-1].strip() == '```': content = '\n'.join(lines[1:-1])
    return json.loads(content)


def read_response_body(response,deadline,timeout):
    """Read chunks so gateway keepalive bytes cannot reset an overall request budget."""
    chunks=[]
    while True:
        remaining=deadline-time.time()
        if remaining<=0:raise TimeoutError('API response time budget reached')
        sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
        if sock is not None:sock.settimeout(max(.1,min(timeout,remaining)))
        reader=getattr(response,'read1',None) or response.read
        chunk=reader(65536)
        if not chunk:break
        chunks.append(chunk)
    return b''.join(chunks)

class CompatibleAPI:
    def __init__(self):
        raw_keys = os.environ.get('RF_API_KEYS', '')
        self.keys = [x.strip() for x in raw_keys.split(',') if x.strip() and x.strip() != 'replace_me']
        if not self.keys:
            self.keys = [os.environ.get('RF_API_KEY', '')]
        self.key = self.keys[0]
        self.key_index = 0
        self.key_cooldowns = {}
        self.base = os.environ.get('RF_BASE_URL','').rstrip('/')
        self.health_path = Path(os.environ.get('RF_ACCOUNT_HEALTH_FILE',str(Path.home()/'.reviewforge'/'account_health.json')))
        self.cooldown_seconds = max(60,int(os.environ.get('RF_ACCOUNT_COOLDOWN_SECONDS','36000')))
        try:
            health=json.loads(self.health_path.read_text(encoding='utf-8'))
        except FileNotFoundError:health={}
        for i,key in enumerate(self.keys):
            slot=hashlib.sha256((self.base+'\0'+key).encode()).hexdigest()
            until=health.get(slot,{}).get('retry_after_epoch',0)
            if until>time.time():self.key_cooldowns[i]=until
        self.model = os.environ.get('RF_WRITER_MODEL',os.environ.get('RF_MODEL','mimo-v2.6-flash:free'))
        self.reviewer_model = os.environ.get('RF_REVIEWER_MODEL','deepseek-v4.1-flash:free')
        self.fallback_model = os.environ.get('RF_FALLBACK_MODEL','deepseek-v4.1-flash:free')
        if not self.key or self.key == 'replace_me' or not self.base.startswith('https://') or not self.model:
            raise ValueError('Configure RF_API_KEY, HTTPS RF_BASE_URL, RF_MODEL in .env')
        self.max_tokens = int(os.environ.get('RF_MAX_OUTPUT_TOKENS','2500'))

    def chat(self, system, user, role='writer'):
        preferred = self.reviewer_model if role == 'reviewer' else self.model
        models = [preferred] + ([self.fallback_model] if self.fallback_model != preferred else [])
        if role=='reviewer' and self.model not in models:models.append(self.model)
        failures = []
        call_deadline=min(getattr(self,'deadline',float('inf')),time.time()+max(1,min(1800,getattr(self,'call_timeout',180))))
        for model in models:
            body = json.dumps({'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], 'temperature': 0.2, 'max_tokens': self.max_tokens}).encode()
            # Explicit user opt-in to independently authorized accounts.
            allow_rate_failover = os.environ.get('RF_ALLOW_RATE_LIMIT_FAILOVER') == '1'
            key_order = list(range(self.key_index, len(self.keys))) + list(range(0, self.key_index))
            for key_index in key_order:
                if time.time()>=call_deadline:raise TimeoutError('API time budget reached')
                if self.key_cooldowns.get(key_index, 0) > time.time():
                    continue
                key = self.keys[key_index]
                req = urllib.request.Request(self.base + '/chat/completions', data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
                try:
                    attempt_deadline=min(call_deadline,time.time()+getattr(self,'request_timeout',150)) if getattr(self,'call_timeout',180)>180 else call_deadline
                    with urllib.request.urlopen(req, timeout=max(.1,min(getattr(self,'request_timeout',150),call_deadline-time.time()))) as resp:
                        raw = read_response_body(resp,attempt_deadline,getattr(self,'request_timeout',150))
                        if not raw.strip():raise ValueError('Empty upstream body; bytes='+str(len(raw)))
                        try:data=json.loads(raw)
                        except json.JSONDecodeError as error:raise ValueError('Invalid upstream JSON; bytes='+str(len(raw))+'; position='+str(error.pos)) from None
                    result = data['choices'][0]['message']['content']
                    if not isinstance(result, str) or not result.strip():
                        choice=data['choices'][0];message=choice.get('message',{})
                        raise ValueError('Empty API response; finish_reason='+str(choice.get('finish_reason','unknown'))+'; reasoning_chars='+str(len(message.get('reasoning_content') or message.get('reasoning') or '')))
                    self.key_index = key_index
                    self.last_finish_reason=data['choices'][0].get('finish_reason')
                    self.last_model=model
                    self.last_key_slot=key_index+1
                    return result
                except urllib.error.HTTPError as exc:
                    if exc.code == 429:
                        retry = exc.headers.get('Retry-After', '')
                        if allow_rate_failover and len(self.keys) > 1:
                            # A 429 is temporary unavailability, not token exhaustion.
                            try:
                                delay = max(self.cooldown_seconds, int(float(retry)))
                            except (TypeError, ValueError):
                                delay = self.cooldown_seconds
                            self.key_cooldowns[key_index] = time.time() + delay
                            try:
                                health=json.loads(self.health_path.read_text(encoding='utf-8'))
                            except FileNotFoundError:health={}
                            slot=hashlib.sha256((self.base+'\0'+key).encode()).hexdigest()
                            health[slot]={'status':'temporary_rate_limit','retry_after_epoch':self.key_cooldowns[key_index]}
                            atomic_json(self.health_path,health)
                            print('API account slot '+str(key_index+1)+' temporarily rate-limited; trying another available account.',flush=True)
                            failures.append('HTTP 429 (key slot ' + str(key_index + 1) + ')')
                            continue
                        raise RuntimeError('Provider rate limit (429); respect Retry-After: ' + retry) from None
                    # Explicitly opt-in only for independently authorized,
                    # separately billed accounts. 402 is payment required.
                    if exc.code == 402 and os.environ.get('RF_ALLOW_BILLING_FAILOVER') == '1':
                        failures.append('HTTP 402 (key slot ' + str(key_index + 1) + ')')
                        continue
                    failures.append(model + ': HTTP ' + str(exc.code))
                    break
                except Exception as exc:
                    network_error=isinstance(exc,(TimeoutError,ConnectionError,urllib.error.URLError,http.client.HTTPException))
                    if network_error and len(self.keys)>1:
                        self.key_index=(key_index+1)%len(self.keys)
                        print('API network failure on account slot '+str(key_index+1)+'; next route uses another account.',flush=True)
                    detail=('; '+str(exc)) if isinstance(exc,ValueError) and str(exc).startswith(('Empty API response;','Empty upstream body;','Invalid upstream JSON;')) else ''
                    failures.append(model + ': ' + type(exc).__name__+detail)
                    # An exhausted model output budget is not an account outage.
                    # Preserve time for another model instead of repeating it per key.
                    if detail.startswith('; Empty API response; finish_reason=length;'):break
                    if detail:continue
                    break
        if (failures and all('HTTP 429' in f for f in failures)) or (not failures and self.key_cooldowns and all(self.key_cooldowns.get(i,0)>time.time() for i in range(len(self.keys)))):
            active_cooldowns=[until for until in self.key_cooldowns.values() if until>time.time()]
            delay = max(60, int(min(active_cooldowns) - time.time())+1) if active_cooldowns else 60
            raise RuntimeError('Provider rate limit (429); respect Retry-After: ' + str(delay))
        raise RuntimeError('API attempts failed: ' + '; '.join(failures))


def git_commit(workspace, message):
    try:
        if not (workspace/'.git').exists():
            subprocess.run(['git','init'], cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
        subprocess.run(['git','add','revisions','reports'], cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
        subprocess.run(['git','-c','user.name=ReviewForge','-c','user.email=reviewforge@localhost','commit','-m',message], cwd=workspace, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def run(workspace, hours=9, minutes=None, resume=False, dry_run=False):
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    state_file = workspace/'state.json'
    source_file = workspace/'sources.json'
    manuscript_file = workspace/'manuscript.md'
    if not manuscript_file.exists() or not source_file.exists(): raise FileNotFoundError('Provide manuscript.md and sources.json')
    sources = json.loads(source_file.read_text(encoding='utf-8'))
    if not isinstance(sources,list): raise ValueError('sources.json must be an array')
    if not dry_run and not sources: raise ValueError('Real run requires nonempty evidence sources.json')
    original = manuscript_file.read_text(encoding='utf-8')
    original_hash = hashlib.sha256(original.encode()).hexdigest()
    duration = (minutes/60 if minutes is not None else hours)*3600
    if resume:
        if not state_file.exists(): raise FileNotFoundError('No checkpoint to resume')
        state = json.loads(state_file.read_text(encoding='utf-8'))
        if state['original_sha256'] != original_hash: raise ValueError('Original changed; refuse unsafe resume')
    else:
        if state_file.exists(): raise FileExistsError('Existing run; use --resume or move workspace/state.json')
        state = {'started':time.time(),'deadline':time.time()+duration,'original_sha256':original_hash,'iteration':0,'calls':0,'no_improve':0,'best_file':'manuscript.md','history':[]}
        atomic_json(state_file,state)
    (workspace/'revisions').mkdir(exist_ok=True)
    (workspace/'reports').mkdir(exist_ok=True)
    if dry_run:
        atomic_json(workspace/'reports/dry_run.json', {'valid':True,'deadline':state['deadline'],'sources':len(sources)})
        return state
    api = CompatibleAPI()
    max_calls = int(os.environ.get('RF_MAX_CALLS','120'))
    while time.time() < state['deadline'] and state['calls']+2 <= max_calls and state['no_improve'] < 3:
        current = (workspace/state['best_file']).read_text(encoding='utf-8')
        i = state['iteration'] + 1
        evidence = json.dumps(sources, ensure_ascii=False)
        instructions = ('You are an academic review author. Return ONLY JSON with keys manuscript (complete Markdown), '
                        'ledger (nonempty array of objects with claim,source_id,locator,quote,status), '
                        'change_summary. Only use the supplied source excerpts; quote EXACT verbatim substrings. '
                        'Every modified/new empirical claim must appear in ledger. Preserve unsupported existing '
                        'claims unchanged rather than invent evidence. Improve critical synthesis and substantive argument. '
                        'Do not add any new citations outside the provided source IDs. Keep the entire manuscript.')
        review_sys = ('You are a strict independent scientific reviewer. Return ONLY JSON: '
                      '{"accept": boolean, "major_issues": [strings], "rationale": string}. '
                      'Reject if citation/claim mismatches, unsupported extrapolation, regressions, '
                      'or no substantive improvement. Review excerpt-grounded claims critically.')
        try:
            proposal = extract_json(api.chat(instructions, json.dumps({'manuscript':current,'sources':sources,'task':'Deep writing: solve one substantive synthesis weakness.'},ensure_ascii=False), role='writer'))
            state['calls'] += 1
            draft = proposal['manuscript']; ledger = proposal['ledger']
            if not isinstance(draft,str) or len(draft.strip()) < 30: raise ValueError('Invalid manuscript')
            ok, errors = validate_ledger(ledger,sources)
            if not ok:
                verdict = {'accept':False,'major_issues':errors,'rationale':'Deterministic evidence gate rejected revision'}
            else:
                verdict = extract_json(api.chat(review_sys, json.dumps({'before':current,'after':draft,'ledger':ledger,'sources':sources},ensure_ascii=False), role='reviewer'))
                state['calls'] += 1
            accepted = bool(ok and verdict.get('accept') is True and draft != current)
            report = {'iteration':i,'accepted':accepted,'summary':proposal.get('change_summary',''),'evidence_errors':errors,'review':verdict,'ledger':ledger}
            atomic_json(workspace/f'reports/iteration_{i:04}.json',report)
            if accepted:
                relative = f'revisions/revision_{i:04}.md'
                (workspace/relative).write_text(draft,encoding='utf-8')
                state['best_file'] = relative
                state['no_improve'] = 0
            else:
                state['no_improve'] += 1
            state['history'].append({'iteration':i,'accepted':accepted,'file':state['best_file']})
        except Exception as e:
            state['no_improve'] += 1
            atomic_json(workspace/f'reports/error_{i:04}.json',{'error':str(e),'type':type(e).__name__})
            state['history'].append({'iteration':i,'accepted':False,'error':type(e).__name__})
        state['iteration'] = i
        atomic_json(state_file,state)
        git_commit(workspace,f'ReviewForge iteration {i}')
    atomic_json(workspace/'reports/final.json',{'best_file':state['best_file'],'iterations':state['iteration'],'calls':state['calls'],'finished':dt.datetime.now(dt.timezone.utc).isoformat(),'remaining_unverified':'Requires human audit of all claims and source text'})
    return state
