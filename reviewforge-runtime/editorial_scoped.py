"""Exact claim-scoped source fields. Selection is navigation, never source approval."""
import copy,re,json,hashlib
from manuscript_integrity import CITES,citekeys
from study_registry import FIELDS

BASE={'domain','study_type','prediction_task','mechanistic_structure','learned_component',
      'validation_split','prediction_information','uncertainty','failure_modes'}
RULES=[
 (r'hybrid|model|learn|predict',set()),
 (r'conserv|constraint|balance|physical|non.?negative|boundar|stoichi|yield',{'constraints','constraint_enforcement'}),
 (r'observ|sensor|measur|signal|initializ|online|off.?line|capacit|spectr|biomass|input|feed|induc',{'observations','conditioning_inputs','update_policy'}),
 (r'train|optim|sensitivity|adjoint|gradient|loss|identif|pretrain',{'training_objective','update_policy','baseline_tuning'}),
 (r'scale|transfer|reactor|pilot|industrial|operating|batch|cultivat',{'system_scale','operating_changes','conditioning_inputs'}),
 (r'error|rmse|mape|accuracy|percent|outperform|improv|baseline|compar|r\^?2|\d',{'quantitative_results','sample_size','baseline_tuning'}),
 (r'cpu|gpu|runtime|latency|computation|seconds?|minutes?|software|hardware',{'hardware','software','computation_time','online_latency'}),
 (r'organism|species|strain|bacter|yeast|fung|pichia|penicill|coli',{'organism','product'})]

def claim_text(text,key):
    # Citation ownership stops at another study or the authors' own scope.
    # Keep uncited follow-on results; never route by a whole mixed paragraph.
    selected=[];active=False;uncited_paragraphs=0
    for paragraph in re.split(r'\n\s*\n',text):
        if re.search(r'\\(?:section|subsection|subsubsection|begin)\{',paragraph):
            active=False
        owned=False
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z\\])',paragraph):
            if re.match(r'\s*(?:This review|Our review|We |The present review)',sentence,re.I):
                active=False
            keys=citekeys(sentence)
            if keys:
                active=key in keys
                if active:uncited_paragraphs=0;owned=True
            if active:selected.append(sentence)
        if not owned and active:
            uncited_paragraphs+=1
            if uncited_paragraphs>=2:active=False
    raw=CITES.sub('', ' '.join(selected))
    return re.sub(r'\\(?:ref|eqref|label|autoref|cref)\{[^}]+\}','',raw)

def scope_studies(studies,text):
    result=[]
    for study in studies:
        key=study['citekey'];claim=claim_text(text,key)
        hits=[fields for pattern,fields in RULES if re.search(pattern,claim,re.I)]
        full=not hits
        fields=set(study.get('facts',{})) if full else BASE.union(*hits)
        # Conflicted facts are never hidden by a lexical routing decision.
        fields.update(f for f,c in study.get('facts',{}).items() if c.get('status')=='conflict')
        facts={f:copy.deepcopy(c) for f,c in study.get('facts',{}).items() if f in fields}
        unknown=[f for f in FIELDS if f not in study.get('facts',{}) or study['facts'][f].get('status') in ('not_reported','unknown')]
        available=[f for f,c in study.get('facts',{}).items() if f not in facts and c.get('status') not in ('not_reported','unknown')]
        source_access=study.get('source_access') or [{k:s.get(k) for k in ('source_id','source_sha256','document_access','inspection_coverage') if k in s} for s in study.get('sources',[])]
        result.append({'citekey':key,'status':study.get('status','RECORDED'),'facts':facts,
          'source_access':copy.deepcopy(source_access),'conflicts':copy.deepcopy(study.get('conflicts',[])),
          'unknown_fields':unknown,'available_unselected_fields':available,
          'selection_basis':'full_unclassified_fallback' if full else 'claim_field_routes',
          'claim_sha256':hashlib.sha256(claim.encode()).hexdigest()})
    return result

def scoped_context(workspace,text,index=None):
    from editorial_quality import citation_context
    from study_registry import load_registry,facts_for_studies
    context=citation_context(workspace,text,index=index)
    full=facts_for_studies(load_registry(workspace),context['selected_citekeys'])
    context['canonical_studies']=scope_studies(full,text)
    context['field_selection_policy']='Exact complete selected fact cells, qualifications and primary anchors are supplied. Available unselected fields are known locally, not missing evidence. Request any specific needed fields; an unresolved evidence request cannot pass. No selected fact is newly approved by this packet.'
    # Avoid sending the same studies nested and at top level; wire encoder pools anchors.
    return context


def source_packet(studies,text):
    """Render exact values/qualifications plus relevant primary spans on demand.

    Complete original cells remain in the immutable registry; never infer that an
    unexpanded field or anchor is absent. Unresolved evidence requests block review.
    """
    rendered=[]
    for study in studies:
        claim=claim_text(text,study['citekey']);terms=set(re.findall(r'[a-z]{4,}',claim.lower()))
        anchors={};refs={}
        for field,cell in study['facts'].items():
            if cell.get('status')=='conflict':
                raise ValueError('Conflicted source field requires resolution before automatic editing')
            for a in cell.get('anchors',[]):
                key=hashlib.sha256(json.dumps(a,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                anchors[key]=a;refs.setdefault(field,[]).append(key)
        numbers=set(re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',claim))
        scored=sorted(anchors,key=lambda k:(sum(n in anchors[k].get('excerpt','') for n in numbers),sum(t in anchors[k].get('excerpt','').lower() for t in terms)),reverse=True)
        selected=scored[:2]
        # Preserve every source span containing a specifically claimed decimal or
        # percentage, rather than imposing a blind excerpt-count cap.
        material={n for n in numbers if '.' in n or re.search(re.escape(n)+r'\s*(?:percent|\\%|%)',claim,re.I)}
        for number in sorted(material):
            if any(number in anchors[k].get('excerpt','') for k in selected):continue
            hit=next((k for k in scored if number in anchors[k].get('excerpt','')),None)
            if hit is not None:selected.append(hit)
        cells={}
        for field,cell in study['facts'].items():
            view={k:copy.deepcopy(cell[k]) for k in ('id','status','value','context','semantic_status','source_sha256','context_values') if k in cell}
            note=cell.get('semantic_review',{}).get('reason')
            if note:view['source_check_note']=note
            view['expanded_primary_ids']=[selected.index(k)+1 for k in refs.get(field,[]) if k in selected]
            view['unexpanded_anchor_count']=sum(k not in selected for k in refs.get(field,[]))
            cells[field]=view
            assert view.get('value')==cell.get('value')
            assert view.get('source_check_note','')==cell.get('semantic_review',{}).get('reason','')
        rendered.append({**{k:copy.deepcopy(v) for k,v in study.items() if k!='facts'},'facts':cells,
            'primary_spans':{str(i+1):copy.deepcopy(anchors[k]) for i,k in enumerate(selected)},
            'unexpanded_anchor_count':len(set(anchors)-set(selected)),
            'evidence_contract':'Every value, context and source_check_note is exact. A qualified note limits its value. Primary spans supplied here are a relevant subset; all remaining original anchors are retrievable by citekey/field. Do not declare unexpanded evidence absent. Return evidence_requests and do not accept if any required support is unresolved.'})
    return rendered
