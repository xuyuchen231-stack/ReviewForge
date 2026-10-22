"""Evidence provenance checks for scholarly review revisions.

Deterministic bibliographic identity checks, not semantic entailment.
Unknown or changed scientific claims require source-level expert verification.
"""
import json
import re
from pathlib import Path

CITES=re.compile(r'\\(?:cite|citep|citet|autocite|parencite|textcite)\*?(?:\[[^\]]*\])*\{([^{}]+)\}')
BIB=re.compile(r'@\w+\s*\{\s*([^,\s]+)\s*,',re.I)
DOI=re.compile(r'\b10\.\d{4,9}/[^\s,;}]+',re.I)
NUMBER=re.compile(r'(?<![\w\\])\d+(?:\.\d+)?(?:\s*%|\s*(?:mg/L|g/L|h|hours|fold))?',re.I)

def citation_keys(text):
    return {key.strip() for group in CITES.findall(text) for key in group.split(',') if key.strip()}

def registered_keys(workspace):
    ws=Path(workspace)
    keys=set()
    for path in ws.glob('*.bib'):
        keys.update(BIB.findall(path.read_text(encoding='utf-8',errors='replace')))
    for path in (ws/'literature.json',):
        if path.exists():
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                if isinstance(data,list):
                    keys.update(p['key'] for p in data if isinstance(p,dict) and isinstance(p.get('key'),str))
            except (ValueError,OSError):pass
    return keys

def provenance_audit(before,after,workspace):
    old,new=citation_keys(before),citation_keys(after)
    known=registered_keys(workspace)
    oldnums=set(NUMBER.findall(before))
    newnums=set(NUMBER.findall(after))
    new_dois=set(DOI.findall(after))-set(DOI.findall(before))
    report={
      'existing_citations_removed':sorted(old-new),
      'new_citations':sorted(new-old),
      'new_citations_unregistered':sorted((new-old)-known),
      'new_numeric_expressions':sorted(newnums-oldnums),
      'new_dois':sorted(new_dois),
      'bibliographic_keys_available':len(known),
      'semantic_claims_verified':False,
      'warning':'A registered citekey or DOI proves identity only; primary-source content must substantiate the claim.'
    }
    report['hard_pass']=not(report['existing_citations_removed'] or report['new_citations_unregistered'])
    report['needs_evidence_review']=bool(report['new_citations'] or report['new_numeric_expressions'] or report['new_dois'])
    return report

def evidence_gate(before,after,workspace):
    report=provenance_audit(before,after,workspace)
    if not report['hard_pass']:
        return False,'Missing original citations or unregistered new citations',report
    if report['needs_evidence_review']:
        return False,'New evidence-bearing content requires source verification',report
    return True,'',report
