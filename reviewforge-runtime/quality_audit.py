"""Deterministic manuscript depth diagnostics; heuristic flags are not quality verdicts."""
import re
import json
from pathlib import Path

HEADING = re.compile(r'(?m)^\\(section|subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{([^\n]*)\}')
CITE = re.compile(r'\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}')
LATEX = re.compile(r'\\(?:begin|end)\{[^}]+\}|\\[a-zA-Z]+\*?(?:\[[^\]]*\])?')
WORD = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')

def visible_text(text):
    text=re.sub(r'(?m)^%.*$', '', text)
    text=re.sub(r'\\(?:cite[a-zA-Z*]*|ref|eqref|label)\s*(?:\[[^]]*\]\s*)*\{[^}]*\}', ' ', text)
    text=re.sub(r'(?s)\$.*?\$', ' ', text)
    return LATEX.sub(' ',text)

def count_units(text):
    clean=visible_text(text)
    return {'latin_words':len(WORD.findall(clean)),
            'cjk_characters':len(CJK.findall(clean)),
            'paragraphs':sum(1 for p in re.split(r'\n\s*\n',clean)
                             if len(WORD.findall(p))+len(CJK.findall(p))>=35)}

def audit_depth(body,min_words=220):
    matches=list(HEADING.finditer(body))
    sections=[]
    for i,m in enumerate(matches):
        text=body[m.end():matches[i+1].start() if i+1<len(matches) else len(body)]
        units=count_units(text)
        cites=set()
        for group in CITE.findall(text):
            cites.update(k.strip() for k in group.split(',') if k.strip())
        # Combined length indicator is language-neutral enough for flagging, not scoring.
        effective=units['latin_words']+units['cjk_characters']
        findings=[]
        if effective<min_words:
            findings.append('Short treatment: review whether the scientific question is adequately developed')
        if units['paragraphs']<2:
            findings.append('Few developed paragraphs: inspect method explanation, evidence comparison and limitations')
        if not cites:
            findings.append('No detected in-text citations; verify whether this subsection requires evidence')
        sections.append({'heading':m.group(2),'level':m.group(1),**units,
                         'effective_length_indicator':effective,'citekeys':sorted(cites),
                         'diagnostic_flags':findings,'requires_semantic_review':True})
    return {'subsections':sections,
            'flagged_count':sum(bool(x['diagnostic_flags']) for x in sections),
            'method':'Heuristic triage only; length and citation counts do not establish scholarly quality'}

def audit_manuscript(tex):
    matches=list(HEADING.finditer(tex))
    results=[]
    for i,m in enumerate(matches):
        body=tex[m.end():matches[i+1].start() if i+1<len(matches) else len(tex)]
        if m.group(1) not in ('section','subsection'):continue
        metrics=count_units(body)
        keys=set()
        for group in CITE.findall(body):keys.update(x.strip() for x in group.split(',') if x.strip())
        results.append({'heading':m.group(2),'level':m.group(1),**metrics,'unique_citekeys':len(keys)})
    return {'heading_count':len(results),'items':results,
            'flagged_sections':[x for x in results if x['latin_words']+x['cjk_characters']<min_words_default()],
            'note':'Automated triage only; read and assess each flagged section in context.'}

def min_words_default():return 350

def write_depth_report(body,path):
    report=audit_depth(body)
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
