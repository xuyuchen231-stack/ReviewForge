"""Offline workflow advice from declared review records; never an expert verdict."""
import argparse
import json
import time
from pathlib import Path


def assess(snapshot,now=None):
    """Call only after real events; a heartbeat/cooldown is not a review round."""
    now=time.time() if now is None else now
    stale=0
    seen=set()
    unidentified=0
    for event in snapshot.get('history',[]):
        if event.get('kind')!='completed_review':
            continue
        review_id=event.get('review_id')
        if not isinstance(review_id,str) or not review_id.strip():
            unidentified+=1
            continue
        if review_id in seen:
            continue
        if any(snapshot.get(field) is not None and event.get(field)!=snapshot[field]
               for field in ('task_id','evidence_scope')):
            continue
        seen.add(review_id)
        if event.get('new_findings') or event.get('closed_issue_ids'):
            stale=0
        else:
            stale+=1
    unresolved=[]
    for issue in snapshot.get('issues',[]):
        severity=str(issue.get('severity','UNKNOWN')).strip().upper()
        if severity not in ('CRITICAL','MAJOR','MINOR','OBSERVATION','UNKNOWN'):
            severity='UNKNOWN'
        issue={**issue,'severity':severity}
        closed=(str(issue.get('status','OPEN')).strip().upper()=='CLOSED'
                and bool(issue.get('resolution_evidence'))
                and issue.get('independently_reviewed') is True)
        if not closed and severity!='OBSERVATION':
            unresolved.append(issue)
    blocking=[issue['id'] for issue in unresolved
              if issue['severity'] in ('CRITICAL','MAJOR','UNKNOWN')]
    required=[issue['id'] for issue in unresolved if issue.get('required',True)]
    checks=snapshot.get('checks',{})
    missing=[name for name,status in checks.items() if status!='PASS']
    current=(bool(snapshot.get('revision')) and snapshot.get('revision')==snapshot.get('reviewed_revision'))
    if blocking:
        status,action='BLOCKED','REPAIR_BLOCKING_ISSUES'
    elif not checks or missing or not current:
        status,action='INCOMPLETE','VERIFY_CURRENT_CONTRACT'
    elif required:
        status,action='NEEDS_REVISION','LOCAL_PATCH_THEN_REVIEW'
    else:
        status,action='PROVISIONAL_MODEL_PASS','REVIEW_DELIVERY_REQUIREMENTS'
    wait=max(0,int(snapshot.get('wait_until_epoch',0)-now))
    if wait:
        action='WAIT_PROVIDER'
    elif status!='PROVISIONAL_MODEL_PASS' and stale>=4:
        action='REPORT_PERSISTENT_BLOCKER'
    elif status!='PROVISIONAL_MODEL_PASS' and stale>=2:
        action='CHANGE_REPAIR_STRATEGY'
    return {'status':status,'next_action':action,'stale_completed_reviews':stale,
            'ignored_unidentified_reviews':unidentified,
            'blocking_issue_ids':blocking,'required_open_issue_ids':required,
            'unverified_checks':missing,'review_matches_current_revision':bool(current),
            'retry_after_seconds':wait,'score_used_for_acceptance':False,
            'basis':'Caller-supplied records; offline workflow advice, not source or PDF verification.',
            'expert_verified':False,'author_approved':False,'submission_ready':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    report=assess(json.loads(args.input.read_text(encoding='utf-8-sig')))
    text=json.dumps(report,ensure_ascii=True,indent=2)
    if args.output:
        if args.output.resolve()==args.input.resolve():
            raise ValueError('Keep the original campaign record unchanged')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+'\n',encoding='utf-8')
    print(text)


if __name__=='__main__':
    main()
