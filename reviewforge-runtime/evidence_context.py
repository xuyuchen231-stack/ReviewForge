"""Read source anchors for both writer and reviewer; never certify entailment."""
import hashlib
import json
from pathlib import Path
from manuscript_integrity import citekeys


def load_context(workspace, text, heading=''):
    ws = Path(workspace)
    path = ws/'evidence_ledger.json'
    result = {'entries': [], 'status': 'MISSING', 'semantic_verification': False,
              'unanchored_citekeys': sorted(citekeys(text))}
    if not path.exists(): return result
    raw = path.read_bytes()
    result['ledger_sha256'] = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw)
        entries = data.get('entries', []) if isinstance(data, dict) else data
        if not isinstance(entries, list): raise ValueError('Expected list of evidence entries')
        for row in entries:
            if not isinstance(row, dict): raise ValueError('Invalid evidence entry')
            key = row.get('citekey', '')
            if key not in citekeys(text) and row.get('section') != heading: continue
            item = {'citekey': key, 'claim': row.get('claim') or row.get('supported_claim', ''),
                    'source_id': row.get('source_id') or row.get('doi', ''),
                    'locator': row.get('locator') or row.get('evidence_location', ''),
                    'excerpt': row.get('excerpt') or row.get('quote', ''),
                    'limitations': row.get('limitations', ''),
                    'verification_status': row.get('verification_status', 'unverified')}
            # Legacy ledgers may point at a local UTF-8 source excerpt.
            source = row.get('source_file')
            if source and not item['excerpt']:
                local = (ws/str(source)).resolve()
                if local.is_relative_to(ws.resolve()) and local.is_file() and local.stat().st_size <= 100000:
                    item['excerpt'] = local.read_text(encoding='utf-8')
            if not all(isinstance(item[x], str) and item[x].strip() for x in ('claim','source_id','locator','excerpt')):
                continue
            result['entries'].append(item)
        result['status'] = 'SOURCE_ANCHORS' if result['entries'] else 'NO_MATCHING_ANCHORS'
        result['unanchored_citekeys'] = sorted(citekeys(text)-{x['citekey'] for x in result['entries']})
    except (ValueError, TypeError, OSError, UnicodeError):
        result.update(status='INVALID', entries=[])
    return result


def context_digest(context):
    return hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def candidate_evidence_gate(before, after, workspace, heading):
    from evidence_gate import provenance_audit
    report = provenance_audit(before, after, workspace)
    if not report['hard_pass']:
        return False, 'Removed original citations or introduced unregistered citations'
    supplied = load_context(workspace, before, heading)
    anchored = {entry['citekey'] for entry in supplied['entries']}
    missing = (citekeys(after)-citekeys(before))-anchored
    if missing:
        return False, 'New citations lack source excerpts supplied to writer: '+', '.join(sorted(missing))
    return True, ''
