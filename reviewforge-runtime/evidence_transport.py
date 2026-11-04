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
