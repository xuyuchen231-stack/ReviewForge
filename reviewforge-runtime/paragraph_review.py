"""Paragraph-bound review decisions. Relocation and deletion require revision, never automatic cuts."""
from collections import Counter
import hashlib
import re
from pathlib import Path
from manuscript_integrity import citekeys
from prose_quality import plain

POLICY='paragraph-function-and-placement-v1'
CONTRACT='''In the SAME review response return paragraph_review, with exactly one row for every supplied paragraph_options ID:
{"paragraph_id":ID,"function":"context|definition|evidence|comparison|analysis|implication|qualification|proposal","message":str,"adds":str,"decision":"keep|revise|merge|move|delete","destination":"main|evidence_matrix|supplement","reason":str}.
State the paragraph's actual message and what it adds to the section or previously established claims, using one short sentence each rather than copying the paragraph. Keep means the current paragraph belongs in main text and is necessary. If removing it would lose no evidence, reasoning or material qualification, choose merge/delete. Access bookkeeping and noncentral extended reconciliation may move to the evidence matrix/supplement. Never move contradictory or conclusion-changing evidence out of sight. Do not demand every paragraph contain every rhetorical function.
Check repeated claims against previous_paragraph_messages. A later occurrence can legitimately introduce, demonstrate, interpret or synthesize an established claim, but its reason must identify the changed function or new consequence. Quote the offending original wording in reason when requesting a change. A relocation request and its internal audit log are not a published supplementary note; do not claim such a note exists. Do not confuse a physical loss rate with a training penalty, or a rate law's limiting behavior with estimator convergence. These are provisional reviewer judgments, not expert approval.'''


def paragraph_records(text):
    counts=Counter();result=[]
    for block in re.split(r'\n\s*\n',text):
        body=re.sub(r'\\(?:section|subsection|subsubsection)\*?\{[^{}]*\}',' ',block)
        visible=re.sub(r'\s+',' ',plain(body)).strip()
        if not re.search(r'[A-Za-z]{2,}|[\u3400-\u9fff]{2,}',visible):continue
        counts[block]+=1;identifier=hashlib.sha256((str(counts[block])+'\0'+block).encode()).hexdigest()[:18]
        result.append({'id':identifier,'text':block,'start_anchor':block.strip()[:90],'end_anchor':block.strip()[-65:],'citekeys':sorted(citekeys(block))})
    return result


def paragraph_options(text):return [{k:v for k,v in row.items() if k!='text'} for row in paragraph_records(text)]

def paragraph_unit_owners(text,units):
    starts=[];cursor=0
    for unit in units:
        marker='\\subsection{'+unit['heading']+'}\n';start=text.find(marker,cursor)
        if start<0:raise ValueError('Unit heading missing from assembled paragraph map')
        starts.append((start,unit['id']));cursor=start+len(marker)
    if not starts:raise ValueError('Unit ownership requires a nonempty outline')
    result={};cursor=0
    for paragraph in paragraph_records(text):
        start=text.find(paragraph['text'],cursor)
        if start<0:raise ValueError('Paragraph missing from exact assembled text')
        cursor=start+len(paragraph['text'])
        result[paragraph['id']]=next((uid for offset,uid in reversed(starts) if offset<=start),starts[0][1])
    return result


def preserve_relocations(directory,text,changes):
    import json
    from reviewforge import atomic_json
    path=Path(directory)/'paragraph_relocations.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'records':{},'scope':'Internal source-preservation and placement-request log, not independent evidence or a submission-ready supplement.','expert_verified':False}
    lookup={row['id']:row for row in paragraph_records(text)}
    sha=hashlib.sha256(text.encode()).hexdigest()
    for row in changes:
        if row['decision']!='move':continue
        original=lookup[row['paragraph_id']]
        data['records'][sha+':'+row['paragraph_id']]={'candidate_sha256':sha,'original_paragraph':original['text'],'citekeys':original['citekeys'],'review_request':row,'status':'relocation_requested; subsequent revision must be checked'}
    if data['records']:atomic_json(path,data)


def validate_paragraph_review(text,review):
    return validate_options_review(paragraph_options(text),review)

def validate_options_review(options,review):
    rows=review.get('paragraph_review')
    if not options or not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):raise ValueError('Paragraph review mapping required')
    if any(not isinstance(r.get('paragraph_id'),str) for r in rows) or Counter(r['paragraph_id'] for r in rows)!=Counter(p['id'] for p in options):raise ValueError('Paragraph review must cover each current paragraph exactly once')
    issues=[]
    for row in rows:
        if row.get('function') not in ('context','definition','evidence','comparison','analysis','implication','qualification','proposal') or row.get('decision') not in ('keep','revise','merge','move','delete') or row.get('destination') not in ('main','evidence_matrix','supplement'):
            raise ValueError('Invalid paragraph function or placement decision')
        if any(not isinstance(row.get(k),str) or not row[k].strip() for k in ('message','adds','reason')):raise ValueError('Paragraph review needs actual message, contribution and rationale')
        severity=row.get('severity','major')
        if severity not in ('critical','major','minor','observation'):raise ValueError('Invalid paragraph issue severity')
        category=row.get('category','scientific_reasoning')
        if category not in ('factual','mathematical','evidence_scope','scientific_reasoning','style','placement'):raise ValueError('Invalid paragraph issue category')
        optional=severity in ('minor','observation') and category=='style'
        if (row['decision']!='keep' or row['destination']!='main') and not optional:issues.append(row)
    return issues
