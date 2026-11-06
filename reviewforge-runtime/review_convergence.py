"""Persistent exact issue tracking; repeated rejection stops work, never approves it."""
import re
from paragraph_review import paragraph_records,blocking_change
from study_registry import signature


def block_repair(budget,candidate,reason):
    budget['convergence_block']={'candidate_sha256':signature(candidate),'reason':reason,
                               'fingerprint':budget.get('review_convergence',{}).get('last_fingerprint')}


def repair_blocked(budget,candidate,diagnosis=None):
    block=budget.get('convergence_block')
    if not block:return False
    changed=block['candidate_sha256']!=signature(candidate)
    if diagnosis:
        if (not isinstance(diagnosis,dict) or diagnosis.get('block_sha256')!=signature(block)
            or any(not isinstance(diagnosis.get(k),str) or not diagnosis[k].strip() for k in ('reason','action'))):
            raise ValueError('Repair diagnosis must name the current block and concrete reason/action')
        receipt=signature(diagnosis)
        if receipt==budget.get('last_diagnosis_receipt'):return True
        budget.setdefault('repair_diagnoses',[]).append(diagnosis)
        budget['last_diagnosis_receipt']=receipt
        changed=True
    if changed:
        budget.setdefault('convergence_block_history',[]).append(block)
        budget.pop('convergence_block')
        state=budget.get('review_convergence',{})
        state.update(streak=0,stalled=False)
        return False
    return True


def track_review(budget,report,body):
    state=budget.setdefault('review_convergence',{'issues':{},'rounds':[],'streak':0})
    paragraphs=paragraph_records(body);locations={p['id']:(i,p) for i,p in enumerate(paragraphs)}
    active=[]
    for row in report.get('paragraph_review',[]):
        if not blocking_change(row):continue
        index,paragraph=locations.get(row.get('paragraph_id'),(-1,{}))
        reason=row.get('reason','');category=row.get('category','scientific_reasoning')
        key=signature([index,category,row.get('decision'),row.get('destination'),re.sub(r'\s+',' ',reason).strip()])
        item=state['issues'].setdefault(key,{'requirement':reason,'category':category,'resolved':False,'occurrences':0})
        item.update(paragraph_id=row.get('paragraph_id'),paragraph_anchor=paragraph.get('start_anchor',''),
                    citekeys=paragraph.get('citekeys',[]),occurrences=item['occurrences']+1,resolved=False)
        active.append(key)
    failed=sorted(k for k,v in report.get('checks',{}).items() if v is not True)
    # Unbound/global objections still block; do not discard them just because a
    # paragraph map was absent or every mapped paragraph said keep.
    unresolved={'issue_ids':sorted(set(active)),'failed_checks':failed,
                'issues':sorted(set(str(i).strip() for i in report.get('issues',[]))),
                'scientific_conflicts':report.get('scientific_conflicts',[]),
                'evidence_requests':report.get('evidence_requests',[]),
                'accepted':report.get('accepted')}
    fingerprint=signature(unresolved)
    state['streak']=state.get('streak',0)+1 if state.get('last_fingerprint')==fingerprint else 1
    state.update(last_fingerprint=fingerprint,active_issue_ids=sorted(set(active)))
    state['rounds'].append({'candidate_sha256':signature(body),'fingerprint':fingerprint,**unresolved})
    state['stalled']=state['streak']>=3
    return state['stalled']
