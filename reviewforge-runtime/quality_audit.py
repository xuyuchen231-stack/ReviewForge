"""Deterministic depth diagnostics for ReviewForge. No API calls, no invented grades."""
import re
import json
from pathlib import Path

HEADING = re.compile(r'(?m)^\\(subsection|subsubsection|paragraph)\\*?(?:\\[[^\\]]*\\])?\\{([^\\n]*)\\}')
CITE = re.compile(r'\\\\cite[a-zA-Z*]*\\s*(?:\\[[^\\]]*\\]\\s*)*\\{([^}]+)\\}')
LATEX = re.compile(r'\\\\(?:begin|end)\\{[^}]+\\}|\\\\[a-zA-Z]+\\*?(?:\\[[^\\]]*\\])?')
WORD = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")

def audit_depth(body, min_words=220):
    matches=list(HEADING.finditer(body))
    sections=[]
    for i,m in enumerate(matches):
        text=body[m.end():matches[i+1].start() if i+1<len(matches) else len(body)]
        clean=LATEX.sub(' ',re.sub(r'(?m)^%.*$', '', text))
        words=len(WORD.findall(clean))
        cites=set()
        for group in CITE.findall(text):
            cites.update(k.strip() for k in group.split(',') if k.strip())
        paragraphs=[p for p in re.split(r'\\n\\s*\\n',clean) if len(WORD.findall(p))>=25]
        findings=[]
        if words<min_words: findings.append('Short treatment: inspect whether this subsection adequately develops its scientific argument')
        if len(paragraphs)<2: findings.append('Limited paragraph-level development; consider evidence, comparison, and limitations')
        if not cites: findings.append('No in-text citations in subsection; verify whether evidence is required')
        sections.append({'heading':m.group(2),'level':m.group(1),'words_approx':words,'paragraphs_approx':len(paragraphs),'citekeys':sorted(cites),'diagnostic_flags':findings,'requires_semantic_review':True})
    return {'subsections':sections,'flagged_count':sum(bool(x['diagnostic_flags']) for x in sections),
            'method':'Heuristic diagnostic only; not a publication score or proof of evidence quality'}

def write_depth_report(body,path):
    report=audit_depth(body)
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
