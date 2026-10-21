"""ReviewForge minimal autonomous writing engine (standard library)."""
from __future__ import annotations
import datetime as dt
import hashlib
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


class CompatibleAPI:
    def __init__(self):
        raw_keys = os.environ.get('RF_API_KEYS', '')
        self.keys = [x.strip() for x in raw_keys.split(',') if x.strip() and x.strip() != 'replace_me']
        if not self.keys:
            self.keys = [os.environ.get('RF_API_KEY', '')]
        self.key = self.keys[0]
        self.key_index = 0
        self.base = os.environ.get('RF_BASE_URL','').rstrip('/')
        self.model = os.environ.get('RF_WRITER_MODEL',os.environ.get('RF_MODEL','mimo-v2.6-flash:free'))
        self.reviewer_model = os.environ.get('RF_REVIEWER_MODEL','deepseek-v4.1-flash:free')
        self.fallback_model = os.environ.get('RF_FALLBACK_MODEL','deepseek-v4.1-flash:free')
        if not self.key or self.key == 'replace_me' or not self.base.startswith('https://') or not self.model:
            raise ValueError('Configure RF_API_KEY, HTTPS RF_BASE_URL, RF_MODEL in .env')
        self.max_tokens = int(os.environ.get('RF_MAX_OUTPUT_TOKENS','2500'))

    def chat(self, system, user, role='writer'):
        preferred = self.reviewer_model if role == 'reviewer' else self.model
        models = [preferred] + ([self.fallback_model] if self.fallback_model != preferred else [])
        failures = []
        for model in models:
            body = json.dumps({'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], 'temperature': 0.2, 'max_tokens': self.max_tokens}).encode()
            for key_index in range(self.key_index, len(self.keys)):
                key = self.keys[key_index]
                req = urllib.request.Request(self.base + '/chat/completions', data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
                try:
                    with urllib.request.urlopen(req, timeout=150) as resp:
                        data = json.load(resp)
                    result = data['choices'][0]['message']['content']
                    if not isinstance(result, str) or not result.strip():
                        raise ValueError('Empty API response')
                    self.key_index = key_index
                    return result
                except urllib.error.HTTPError as exc:
                    # Never rotate keys to evade provider rate limits.
                    if exc.code == 429:
                        retry = exc.headers.get('Retry-After', '')
                        raise RuntimeError('Provider rate limit (429); respect Retry-After: ' + retry) from None
                    # Explicitly opt-in only for independently authorized,
                    # separately billed accounts. 402 is payment required.
                    if exc.code == 402 and os.environ.get('RF_ALLOW_BILLING_FAILOVER') == '1':
                        failures.append('HTTP 402 (key slot ' + str(key_index + 1) + ')')
                        continue
                    failures.append(model + ': HTTP ' + str(exc.code))
                    break
                except Exception as exc:
                    failures.append(model + ': ' + type(exc).__name__)
                    break
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
