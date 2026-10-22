"""Traceable source-evidence ledger. A source anchor is not semantic proof."""
import argparse,json,re
from pathlib import Path
CITE=re.compile(r'\\(?:cite|citep|citet|autocite|parencite|textcite)\*?(?:\[[^]]*\])*\{([^{}]+)\}')
def citekeys(text):
 return {k.strip() for group in CITE.findall(text) for k in group.split(',') if k.strip()}
def check_entry(entry):
 required=('claim','citekey','source_id','locator','excerpt')
 missing=[k for k in required if not isinstance(entry.get(k),str) or not entry[k].strip()]
 status=entry.get('verification_status','unverified')
 if status not in ('unverified','source_located','expert_verified','contradicted'):missing.append('verification_status')
 return {'traceable':not missing,'missing':missing,'status':status,'expert_verified':not missing and status=='expert_verified'}
def evaluate_ledger(manuscript,ledger):
 keys=citekeys(manuscript);entries=ledger.get('entries',[])
 if not isinstance(entries,list):raise ValueError('entries must be a list')
 audited=[]
 for entry in entries:
  if not isinstance(entry,dict):raise ValueError('ledger entry must be an object')
  result=check_entry(entry)
  result.update({'claim':entry.get('claim',''),'citekey':entry.get('citekey',''),'citation_in_manuscript':entry.get('citekey') in keys})
  audited.append(result)
 covered={e['citekey'] for e in audited if e['traceable'] and e['citation_in_manuscript']}
 return {'citations_without_source_anchor':sorted(keys-covered),
  'traceable_claims':sum(e['traceable'] for e in audited),
  'expert_verified_claims':sum(e['expert_verified'] and e['citation_in_manuscript'] for e in audited),
  'unresolved_claims':[e for e in audited if not e['expert_verified'] or not e['citation_in_manuscript']],
  'complete_expert_verification':False,
  'verification_scope':'CITATION_ANCHORS_ONLY; manuscript-wide claim completeness cannot be inferred',
  'note':'Even expert-reviewed ledger entries do not establish that every manuscript claim was inventoried. Manuscript-wide verification is not certified.'}
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--manuscript',required=True);p.add_argument('--ledger',required=True);p.add_argument('--output',required=True)
 a=p.parse_args()
 report=evaluate_ledger(Path(a.manuscript).read_text(encoding='utf-8'),json.loads(Path(a.ledger).read_text(encoding='utf-8')))
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'expert_verified_claims':report['expert_verified_claims'],'unresolved_claims':len(report['unresolved_claims']),'output':str(dest)}))
if __name__=='__main__':main()
