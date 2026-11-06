"""Complete paragraph coverage with bounded evidence packets, never truncated prose."""
import copy
from efficient_payload import project_payload,encoded_size,InputBudgetExceeded
from manuscript_integrity import citekeys
from paragraph_review import paragraph_records,paragraph_options
from bounded_writing import source_blocks

POLICY='bounded-fact-card-review-v1'
CLARIFICATIONS=('Evaluate material scientific and editorial defects, not an ideal alternative wording. '
 'Use severity critical/major for wrong facts, unsupported scientific conclusions, lost reasoning or material qualifications; minor/observation for optional wording. '
 'A minor suggestion alone does not require rejection or a failed check. Each row may include severity critical|major|minor|observation and category factual|mathematical|evidence_scope|scientific_reasoning|style|placement. Only minor/observation rows explicitly categorized style are optional. '
 'Consistent notation and symbolic references do not require adding equations to an equation-free passage. '
 'A ban on cross-paper RMSE league tables is not a ban on grounded comparisons of validation designs. '
 'Canonical current source_access overrides older claims about abstract-only access. Canonical checked facts may correct legacy prose. '
 'A source citation and an accurate checked fact are sufficient attribution: do not require fact IDs or quotations inside manuscript prose. A clearly identified analytical inference can follow checked premises without appearing verbatim in the source; verify the reasoning rather than rejecting it merely for being new. '
 'Retain material limitations; do not alternately demand and remove the same qualifier without explaining the factual or argumentative reason. '
 'Multiple study citations and combined evidence, comparison and inference in one paragraph are normal scientific synthesis; do not require homogeneous citekeys or one rhetorical function per paragraph. A sliced packet is not the complete unit: do not fail a local paragraph merely because another batch develops the remaining cases. Source-access policy does not make all studies full text: an abstract_only record remains abstract-only. '
 'Mark reviewer uncertainty rather than inventing a requirement. Verify the supplied revision response independently; it cannot approve its own text. '
 'Return concise issues and one short sentence per paragraph message/adds/reason. For disputed primary wording return evidence_requests: [{citekey,fields:[field names]}] or [fact IDs]; do not pass a claim with unresolved evidence requests.')

def review_batches(system,payload,candidate,limit=90000,max_paragraphs=10,followup_reserve=0):
    body=candidate['latex'];records=paragraph_records(body)
    if not records:return [{**payload,'candidate':candidate,'paragraph_options':paragraph_options(body),'review_criteria':CLARIFICATIONS}]
    pieces=[];cursor=0
    for i,row in enumerate(records):
        start=body.find(row['text'],cursor)
        if start<0:raise ValueError('Review paragraph no longer matches candidate')
        end=body.find(records[i+1]['text'],start+len(row['text'])) if i+1<len(records) else len(body)
        pieces.append({'text':body[cursor:end],'options':[p for p in paragraph_options(body) if p['id']==row['id']],'original':[]})
        cursor=end
    originals=source_blocks(payload.get('original_material',''))
    for block in originals:
        refs=citekeys(block['text'])
        index=max(range(len(pieces)),key=lambda i:(len(refs&citekeys(pieces[i]['text'])),-sum(len(b['text']) for b in pieces[i]['original']),-i))
        pieces[index]['original'].append(block)
    def packet(group):
        text=''.join(p['text'] for p in group);refs=citekeys(text)
        findings=[f for f in candidate.get('evidence_synthesis',[]) if set(f.get('citekeys',[])) and set(f.get('citekeys',[]))<=refs]
        local=copy.deepcopy(payload)
        candidate_view={k:copy.deepcopy(candidate[k]) for k in ('retained_analytical_examples','revision_response') if k in candidate}
        candidate_view.update(latex=text,evidence_synthesis=findings)
        local.update(candidate=candidate_view,
                     original_material='\n\n'.join(b['text'] for p in group for b in p['original']),
                     original_block_ids=[b['id'] for p in group for b in p['original']],
                     paragraph_options=[o for p in group for o in p['options']],review_criteria=CLARIFICATIONS,
                     review_scope='Review exactly the supplied paragraph IDs. Other candidate paragraphs are covered in other batches. Original manuscript is historical input, not authoritative evidence. Do not assert unsupported legacy claims as facts.')
        local['canonical_studies']=[s for s in payload.get('canonical_studies',[]) if s.get('citekey') in refs]
        omitted=[s for s in payload.get('canonical_studies',[]) if s.get('citekey') not in refs]
        local['available_studies']=[s['citekey'] for s in omitted]
        local['available_fact_fields']=sorted({field for s in omitted for field in s.get('facts',{})})
        # Exact neighbouring text remains context for repetition and cross-paragraph logic.
        # This is bounded by the unit; large chapters use compact paragraph anchors instead.
        local['whole_unit_context']=[{'id':r['id'],'opening':r['start_anchor']} for r in records]
        return local
    # Leave room for requested primary quotes and schema diagnostics. One
    # indivisible paragraph may still use the hard limit; it is never truncated.
    group_limit=limit-min(max(0,followup_reserve),limit//4)
    groups=[];group=[]
    for piece in pieces:
        trial=group+[piece]
        if group and (len(trial)>max_paragraphs or len(system)+encoded_size(project_payload(packet(trial)))>group_limit):
            groups.append(group);group=[piece]
        else:group=trial
        if len(system)+encoded_size(project_payload(packet(group)))>limit:
            view=project_payload(packet(group))
            sizes=sorted(((key,encoded_size(value)) for key,value in view.items()),key=lambda x:-x[1])[:5]
            raise InputBudgetExceeded('An intact review paragraph and its required facts exceed the request budget; no evidence truncated. Largest fields: '+str(sizes))
    if group:groups.append(group)
    return [packet(g) for g in groups]

def combine_reviews(reports,checks):
    return {'accepted':all(r.get('accepted') is True for r in reports),
            'checks':{c:all(r.get('checks',{}).get(c) is True for r in reports) for c in checks},
            'issues':list(dict.fromkeys(str(i) for r in reports for i in r.get('issues',[]))),
            'paragraph_review':[p for r in reports for p in r.get('paragraph_review',[])],
            'review_policy':POLICY,'batches':len(reports)}
