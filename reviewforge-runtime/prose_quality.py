"""Lightweight prose diagnostics; hints require contextual review, never blind deletion."""
from collections import defaultdict
import re

PROSE_CONTRACT='''Write concise, ordinary academic prose. Name the actual model, input, measurement, comparison and result rather than replacing them with newly coined abstract labels. Keep established scientific terminology and define genuinely necessary new terms.
Give each paragraph a useful job: report a supported finding, compare studies, explain a mechanism or inference, introduce a needed definition, or state a concrete proposal. Use the jobs that the argument needs; do not repeat an identical claim-evidence-caveat-summary template in every paragraph. A paragraph can end when its point is made.
State each central distinction once in its proper section. A later mention must add a new condition, result or consequence; otherwise merge it or refer back briefly. Consolidate shared access limitations in the matrix or methods rather than adding a disclaimer for each citation.
Delete a sentence when removing it loses no scientific information or necessary reasoning. Preserve findings, comparisons, quantities, meaningful uncertainty and counterevidence. Add neither invented details nor stronger claims to sound concrete. A shorter complete explanation is preferable to filling a minimum length. Prefer direct subjects and verbs; remove ceremonial introductions, synonym chains and abstract slogans. Do not mechanically ban a word, colloquialize scientific prose or claim to detect AI authorship.'''
PROSE_REVIEW='''Assess information gain, not word count or polished tone. Identify repeated propositions across paragraphs/previous section findings and distinguish genuine new evidence or conditions. Reject filler that merely rephrases a conclusion, unnecessary invented terminology and repeatedly stapled-on caveats. Quote the actual problematic sentence and say what is redundant or undefined. Keep necessary limitations and standard technical terms. Automated similarity/phrase hints are advisory; do not delete different numerical results, analytical steps or distinct claims because wording is similar. Never require every paragraph to follow the same rhetorical template.'''


def plain(text):
    text=re.sub(r'(?m)(?<!\\)%[^\n]*','',text)
    text=re.sub(r'\\begin\{(equation\*?|align\*?|gather\*?|figure\*?|table\*?|tikzpicture)\}[\s\S]*?\\end\{\1\}',' ',text)
    text=re.sub(r'\$\$[\s\S]*?\$\$|\$[^$]*\$|\\\[[\s\S]*?\\\]',' ',text)
    text=re.sub(r'\\(?:cite[a-zA-Z]*|label|ref|eqref)\*?(?:\[[^\]]*\])*\{[^}]*\}',' ',text)
    text=re.sub(r'\\[a-zA-Z@]+\*?(?:\[[^\]]*\])?',' ',text)
    return text.replace('{',' ').replace('}',' ')


def prose_diagnostics(text):
    cleaned=plain(text)
    paragraphs=[re.sub(r'\s+',' ',p).strip() for p in re.split(r'\n\s*\n',cleaned) if p.strip()]
    groups=defaultdict(list);tokens=[]
    for n,p in enumerate(paragraphs):
        for s in re.split(r'(?<=[.!?\u3002\uff01\uff1f])\s*',p):
            key=' '.join(re.findall(r'[a-z0-9]+|[\u3400-\u9fff]',s.lower()))
            if len(key.split())>=12:groups[key].append({'paragraph':n+1,'text':s.strip()})
        words=set(re.findall(r'[a-z]{3,}|[\u3400-\u9fff]',p.lower()))
        tokens.append((words,tuple(re.findall(r'\d+(?:\.\d+)?',p))))
    repeated=[{'occurrences':rows} for rows in groups.values() if len(rows)>1]
    similar=[]
    for i,(a,numbers) in enumerate(tokens):
        if len(a)<20:continue
        for j in range(i):
            b,other=tokens[j]
            if numbers==other and len(b)>=20 and a!=b and len(a&b)/len(a|b)>=.82:
                similar.append({'paragraphs':[j+1,i+1],'passages':[paragraphs[j],paragraphs[i]],'reason':'Similar prose with unchanged numerical context; inspect information gain.'})
                if len(similar)>=30:break
        if len(similar)>=30:break
    meta={phrase:cleaned.lower().count(phrase) for phrase in ('accessible abstract','does not establish','absence of evidence','supports only the narrow','证据边界','并不意味着','不能证明')}
    return {'status':'REVIEW_HINTS_ONLY','repeated_sentences':repeated,'similar_paragraphs':similar,
            'repeated_meta_phrases':{p:n for p,n in meta.items() if n>=3},'automatic_deletion_allowed':False}
