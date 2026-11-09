"""Lossless shared evidence spans for the model wire payload, not cache identity."""
import copy,json

def compact_evidence(payload):
    if not isinstance(payload,dict) or not payload.get('canonical_studies'):
        return payload
    if '_shared_evidence' in payload:
        raise ValueError('Evidence transport namespace already present')
    result=copy.deepcopy(payload)
    table={};indices={}
    for study in result['canonical_studies']:
        for fact in study.get('facts',{}).values():
            if 'anchors' not in fact:continue
            refs=[]
            for anchor in fact.pop('anchors'):
                binding=json.dumps(anchor,ensure_ascii=False,sort_keys=True,separators=(',',':'))
                if binding not in indices:
                    identifier='e'+str(len(table)+1)
                    indices[binding]=identifier;table[identifier]=anchor
                refs.append(indices[binding])
            fact['anchor_refs']=refs
    result['_shared_evidence']={'instruction':'Each fact anchor_refs entry resolves to the exact source anchor in spans. Apply every referenced excerpt and qualification when checking the fact; references do not establish independent support.','spans':table}
    return result

def expand_evidence(payload):
    result=copy.deepcopy(payload)
    table=result.pop('_shared_evidence')['spans']
    for study in result['canonical_studies']:
        for fact in study.get('facts',{}).values():
            if 'anchor_refs' in fact:
                fact['anchors']=[copy.deepcopy(table[ref]) for ref in fact.pop('anchor_refs')]
    return result


def encode_context_payload(payload):
    """Share exact repeated excerpts across v4 evidence entries and facts."""
    def encode(value):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

    original = encode(payload)
    context = payload.get('evidence_context')
    if not isinstance(context, dict) or 'shared_excerpts' in context:
        return original
    counts = {}
    for field in ('entries', 'canonical_facts'):
        for row in context.get(field, []):
            excerpt = row.get('excerpt')
            if isinstance(excerpt, str) and excerpt:
                counts[excerpt] = counts.get(excerpt, 0) + 1
    ids = {excerpt: str(i) for i, excerpt in enumerate(
        (excerpt for excerpt, count in counts.items() if count > 1), 1)}
    if not ids:
        return original
    view = {**context, 'shared_excerpts': {ref: excerpt for excerpt, ref in ids.items()},
            'shared_excerpt_instruction': 'Resolve every excerpt_ref to its exact source text in shared_excerpts. Retain each row’s source, locator and limitations.'}
    for field in ('entries', 'canonical_facts'):
        if field not in context:
            continue
        view[field] = []
        for row in context[field]:
            ref = ids.get(row.get('excerpt'))
            if ref is not None and 'excerpt_ref' not in row:
                row = {k: v for k, v in row.items() if k != 'excerpt'}
                row['excerpt_ref'] = ref
            view[field].append(row)
    compact = encode({**payload, 'evidence_context': view})
    return compact if len(compact) < len(original) else original
