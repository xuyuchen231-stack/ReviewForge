"""Topic-independent review planning from imperfect LaTeX drafts.

This module creates an inspectable planning brief; it does not invent references,
rewrite protected TeX, or assume a fixed number of chapters.
"""
import argparse
import json
import re
from pathlib import Path

SECTION = re.compile(r'(?m)^\\section\*?(?:\[[^\]]*\])?\{([^}\n]+)\}')
SUBSECTION = re.compile(r'(?m)^\\subsection\*?(?:\[[^\]]*\])?\{([^}\n]+)\}')
WORD = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
CITE = re.compile(r'\\cite\w*(?:\[[^]]*\])*\{([^}]+)\}')

def inspect_draft(tex):
    matches=list(SECTION.finditer(tex))
    chapters=[]
    for i,m in enumerate(matches):
        body=tex[m.end():matches[i+1].start() if i+1<len(matches) else len(tex)]
        subs=SUBSECTION.findall(body)
        keys=set()
        for group in CITE.findall(body):
            keys.update(x.strip() for x in group.split(',') if x.strip())
        words=len(WORD.findall(re.sub(r'\\[A-Za-z]+\*?(?:\[[^\]]*\])?', ' ', body)))
        chapters.append({'heading':m.group(1),'subsections':subs,'approx_words':words,
                         'citation_keys':len(keys),'thin_draft_flag':words<350})
    return {'section_count':len(chapters),'sections':chapters,
            'draft_quality_indicators_only':True}

def planning_contract(topic, draft_tex=''):
    inspection=inspect_draft(draft_tex)
    return {
      'topic':topic,'draft_inventory':inspection,
      'instructions':[
        'Treat the draft as evidence and material, not a mandatory table of contents.',
        'Choose the number and sequence of chapters from the review question, literature landscape, and argument; never assume three or thirteen chapters.',
        'Propose a concise central research question and distinguish the review contribution from existing reviews.',
        'Build a chapter argument map: purpose, key scientific questions, evidence required, comparisons, counterevidence, limitations, and transition.',
        'Identify underdeveloped and redundant material. Merge, split, rename or reorder chapters when justified.',
        'Preserve all original figures, tables, equations, labels, citations, numerical claims and source files until an independently reviewed replacement is accepted.',
        'For weak drafts, explicitly plan missing background, methods, primary-study evidence, comparative synthesis, and future research questions.',
        'Do not infer study results from titles or bibliographic metadata. Mark unsupported claims for evidence retrieval.',
        'Do not equate long prose, citation count or a high model-generated score with scholarly quality.'
      ],
      'output_schema':{
        'review_question':'string','proposed_title':'string','contribution':'string',
        'chapters':[{'title':'string','purpose':'string','questions':['string'],
                     'required_evidence':['string'],'comparisons':['string'],
                     'limitations':['string'],'draft_material_to_reuse':['string']}],
        'draft_gaps':['string'],'evidence_to_verify':['string'],
        'reorganization_rationale':'string'
      },
      'status':'PLANNING_INPUT_ONLY',
      'note':'This contract is not an LLM-generated outline; independent literature-grounded planning is required.'
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--topic',required=True)
    p.add_argument('--draft',default='')
    p.add_argument('--output',default='workspace/reports/review_plan_input.json')
    a=p.parse_args()
    draft=Path(a.draft).read_text(encoding='utf-8') if a.draft else ''
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(planning_contract(a.topic,draft),ensure_ascii=False,indent=2),encoding='utf-8')
    print(out)
if __name__=='__main__':main()
