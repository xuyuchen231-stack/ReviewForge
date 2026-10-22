"""ReviewForge quality-first orchestration.

Separate review planning, evidence inventory and staged candidate improvements.
Does not silently overwrite the master or claim primary-source verification.
"""
import argparse
import hashlib
import json
from pathlib import Path

from review_planner import planning_contract, inspect_draft
from quality_audit import audit_depth, audit_manuscript
from source_evidence import evaluate_ledger
from quality_loop import improve
from evidence_gate import evidence_gate

def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')
    temp.replace(path)

def prepare(workspace):
    ws=Path(workspace)
    original=ws/'original.tex'
    if not original.is_file():raise FileNotFoundError(original)
    text=original.read_text(encoding='utf-8')
    if r'\begin{document}' not in text:raise ValueError('Expected complete LaTeX document')
    topicfile=ws/'review_topic.txt'
    topic=topicfile.read_text(encoding='utf-8').strip() if topicfile.exists() else ''
    if not topic:
        import re
        m=re.search(r'\\title\{([^{}]+)\}',text)
        topic=m.group(1) if m else 'Topic requires clarification from draft and literature'
    reportdir=ws/'reports'
    write_json(reportdir/'review_plan_input.json',planning_contract(topic,text))
    write_json(reportdir/'draft_depth.json',audit_depth(text))
    write_json(reportdir/'manuscript_structure_and_depth.json',audit_manuscript(text))
    ledgerfile=ws/'evidence_ledger.json'
    ledger=json.loads(ledgerfile.read_text(encoding='utf-8')) if ledgerfile.exists() else {'entries':[]}
    write_json(reportdir/'source_evidence_report.json',evaluate_ledger(text,ledger))
    return {'topic':topic,'sections':inspect_draft(text)['section_count'],
            'original_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
            'plan_input':str(reportdir/'review_plan_input.json'),
            'depth_report':str(reportdir/'draft_depth.json'),
            'evidence_report':str(reportdir/'source_evidence_report.json'),
            'next':'Review literature and approve a topic-adaptive outline before structural rewriting.'}

def revise_sections(workspace,chat,structure_gate,max_rounds=3):
    """Generate separately reviewed candidates, never alter review_en.tex or original.tex."""
    from reviewforge_v4 import extract_sections
    ws=Path(workspace)
    source=ws/'review_en.tex'
    if not source.is_file():raise FileNotFoundError(source)
    text=source.read_text(encoding='utf-8')
    sections=extract_sections(text)
    if not sections:raise ValueError('No sections detected')
    out=ws/'quality_revisions';out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for i,(heading,start,end) in enumerate(sections,1):
        body=text[start+len(heading):end]
        def gate(before,after):
            ok,reason=structure_gate(before,after)
            if not ok:return ok,reason
            ok,reason,_=evidence_gate(before,after,ws)
            return ok,reason
        result=improve(chat,gate,heading,body,max_rounds=max_rounds)
        stem='section_%02d'%i
        (out/(stem+'.tex')).write_text(result['text'],encoding='utf-8')
        write_json(out/(stem+'.json'),{k:v for k,v in result.items() if k!='text'})
        summary.append({'section':i,'heading':heading,'score':result['review']['total'],
                        'status':result['status'],'rounds':len(result['history'])-1})
        write_json(ws/'reports'/'quality_improvement_summary.json',summary)
    return summary

def main():
    p=argparse.ArgumentParser(description='ReviewForge evidence-aware planning and diagnostic pipeline')
    p.add_argument('action',choices=['prepare'])
    p.add_argument('--workspace',default='workspace')
    args=p.parse_args()
    if args.action=='prepare':print(json.dumps(prepare(args.workspace),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
