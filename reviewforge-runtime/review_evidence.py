"""Explicit, bounded retrieval of requested original anchors; never silent approval."""
import copy

def add_requested_evidence(payload,requests,studies):
    if not isinstance(requests,list) or not requests:raise ValueError('Invalid primary evidence request')
    facts={cell.get('id'):(study['citekey'],field,cell) for study in studies for field,cell in study.get('facts',{}).items() if cell.get('id')}
    bykey={study['citekey']:study for study in studies};selected={}
    for request in requests:
        if isinstance(request,str):
            if request not in facts:raise ValueError('Unknown primary evidence fact ID')
            selected[request]=facts[request]
        elif isinstance(request,dict):
            study=bykey.get(request.get('citekey'));fields=request.get('fields')
            if study is None or not isinstance(fields,list) or not fields:raise ValueError('Unknown primary evidence study/fields')
            for field in fields:
                if not isinstance(field,str) or field not in study.get('facts',{}):raise ValueError('Unknown primary evidence field')
                cell=study['facts'][field]
                if not cell.get('id'):raise ValueError('Requested field has no source-bound fact')
                selected[cell['id']]=(study['citekey'],field,cell)
        else:raise ValueError('Malformed primary evidence request')
    quotes=[]
    for key,field,cell in selected.values():
        if not cell.get('anchors'):raise ValueError('Requested fact has no inspectable primary anchors')
        quotes.append({'citekey':key,'field':field,'fact':copy.deepcopy(cell)})
    return {**payload,'requested_primary_evidence':quotes,'evidence_feedback':'The specifically requested original anchors are now supplied. Resolve these requests explicitly; do not pass any unresolved claim.'}

def ask_with_evidence(ask,system,payload,required,role='reviewer'):
    report=ask(system,payload,required,role)
    if isinstance(report,dict) and report.get('evidence_requests'):
        studies=payload.get('canonical_studies') or ([payload['canonical_study']] if payload.get('canonical_study') else [])
        expanded=add_requested_evidence(payload,report['evidence_requests'],studies)
        report=ask(system,expanded,required,role)
        if report.get('evidence_requests'):raise ValueError('Primary evidence remains unresolved after bounded retrieval')
    return report
