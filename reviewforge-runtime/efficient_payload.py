"""Bounded model views of independently verified facts; originals remain local."""
import copy,json
from manuscript_integrity import citekeys

POLICY='verified-fact-wire-v1'
EVIDENCE_POLICY=('Canonical facts were independently checked against immutable primary-source anchors upstream. '
 'Exact values, contexts, qualifications, source access and source hashes are retained here; each immutable fact ID resolves to its full anchors and primary quotation text in the local registry. '
 'A qualified fact is not approval of every subclaim in its value: its qualification limits what may be asserted. Do not repeat a specifically unsupported detail, or say a split is unreported when the checked validation_split supplies it. '
 'Review against these verified records, not an assumed abstract-only source. If a specific claim needs original wording, return evidence_requests with its fact IDs and do not pass that unresolved claim. '
 'Do not treat discourse summaries as additional evidence.')

class InputBudgetExceeded(ValueError):pass

def encoded_size(value):return len(json.dumps(value,ensure_ascii=False,separators=(',',':')))

def fact_card(study):
    result={k:copy.deepcopy(v) for k,v in study.items() if k not in ('facts','sources')}
    if 'sources' in study:
        result['sources']=[{k:copy.deepcopy(s[k]) for k in ('source_id','source_sha256','document_access','inspection_coverage') if k in s} for s in study['sources']]
    result['facts']={}
    sources={}
    for field,cell in study.get('facts',{}).items():
        item={k:copy.deepcopy(v) for k,v in cell.items() if k not in ('anchors','semantic_review')}
        if cell.get('semantic_status')=='qualified' and 'qualification' not in item:
            item['qualification']=copy.deepcopy(cell.get('semantic_review',{}).get('reason',''))
        if 'anchors' in cell:
            refs=[]
            for anchor in cell['anchors']:
                sha=anchor.get('source_sha256')
                if sha not in sources:sources[sha]='doc'+str(len(sources)+1)
                refs.append(sources[sha])
            item['source_refs']=list(dict.fromkeys(refs))
        result['facts'][field]=item
    if sources:result['primary_sources']={ref:sha for sha,ref in sources.items()}
    return result

def discourse(rows):
    return [row.get('finding',row) if isinstance(row,dict) else row for row in rows]

def project_payload(payload):
    if not isinstance(payload,dict):return payload
    result=copy.deepcopy(payload);changed=False
    if 'canonical_studies' in result:
        result['canonical_studies']=[fact_card(s) for s in result['canonical_studies']];changed=True
    if 'canonical_study' in result:
        result['canonical_study']=fact_card(result['canonical_study']);changed=True
    if changed:result['canonical_evidence_policy']=EVIDENCE_POLICY
    if not changed and isinstance(result.get('facts'),list):
        # Upstream semantic fact verification still gets EVERY exact quotation.
        # Only identical anchor objects are shared, never replaced by fact values.
        pool={};lookup={}
        for fact in result['facts']:
            if not isinstance(fact,dict) or 'anchors' not in fact:continue
            refs=[]
            for anchor in fact.pop('anchors'):
                key=json.dumps(anchor,ensure_ascii=False,sort_keys=True,separators=(',',':'))
                if key not in lookup:lookup[key]='q'+str(len(pool)+1);pool[lookup[key]]=anchor
                refs.append(lookup[key])
            fact['anchor_refs']=refs
        if pool:
            result['primary_quote_pool']=pool
            result['primary_quote_policy']='These facts are being verified now, not already approved. Resolve every anchor_refs ID to the exact primary anchor in primary_quote_pool. All referenced quotes remain present; verify every value and qualification.'
    if 'completed_unit_findings' in result:
        result['completed_unit_findings']=[discourse(rows) for rows in result['completed_unit_findings']]
    if 'previous_section_summaries' in result:
        result['previous_section_summaries']=[{**row,'findings':discourse(row.get('findings',[]))} for row in result['previous_section_summaries']]
    if 'previous_paragraph_messages' in result:
        grouped={}
        for row in result['previous_paragraph_messages']:
            grouped.setdefault(row.get('section',''),[]).append(row.get('message',''))
        result['previous_paragraph_messages']=[{'section':section,'messages':messages} for section,messages in grouped.items()]
    return result

def partition_fact_review(system,payload,limit):
    groups=[];group=[]
    for fact in payload['facts']:
        trial=group+[fact]
        if group and len(system)+encoded_size(project_payload({**payload,'facts':trial}))+500>limit:
            groups.append(group);group=[fact]
        else:group=trial
        if len(system)+encoded_size(project_payload({**payload,'facts':group}))+500>limit:
            raise InputBudgetExceeded('One source fact and its complete primary anchors exceed the input budget')
    if group:groups.append(group)
    return [{**payload,'facts':group} for group in groups]

def scoped_payload(payload,material):
    local=copy.deepcopy(payload);keys=citekeys(material)
    local['original_material']=material
    local['canonical_studies']=[s for s in payload.get('canonical_studies',[]) if s.get('citekey') in keys]
    local['known_citekeys']=sorted(keys)
    return local

def partition_writing(system,payload,limit):
    from bounded_writing import source_blocks
    blocks=source_blocks(payload.get('original_material',''));groups=[];group=[]
    for block in blocks:
        trial=group+[block['text']];local=scoped_payload(payload,'\n\n'.join(trial))
        if group and len(system)+encoded_size(project_payload(local))+1000>limit:
            groups.append(group);group=[block['text']]
        else:group=trial
        check=scoped_payload(payload,'\n\n'.join(group))
        if len(system)+encoded_size(project_payload(check))+1000>limit:
            raise InputBudgetExceeded('One intact writing block exceeds the input budget; no text or evidence was truncated')
    if group:groups.append(group)
    if not groups:raise InputBudgetExceeded('Oversize writing input cannot be partitioned without source material')
    result=[]
    for index,group in enumerate(groups,1):
        local=scoped_payload(payload,'\n\n'.join(group))
        local['execution_partition']={'part':index,'total':len(groups),'instruction':'Develop only this intact source-material portion. Other portions are written separately and independently reviewed after assembly. No headings or document wrapper. No repeated introductory or closing summary.'}
        local['word_budget']=max(100,int(payload.get('word_budget',1000)/len(groups)))
        if len(system)+encoded_size(project_payload(local))>limit:raise InputBudgetExceeded('Partition metadata exceeds input budget')
        result.append(local)
    return result
