"""ReviewForge v4: section-level evidence-aware bilingual review workflow.
All data is local except optional OpenAlex/Crossref/compatible-chat API calls.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from reviewforge import CompatibleAPI, load_env, atomic_json
from research_quality import evaluate as evaluate_quality, scaffold as scaffold_quality
from manuscript_integrity import analyze as analyze_manuscript, write_report as write_integrity, bibkeys as parse_bibkeys

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'workspace'
DEFAULT_QUERIES=[
 'hybrid modeling microbial fermentation bioreactor',
 'hybrid mechanistic machine learning fed batch fermentation',
 'hybrid model Pichia pastoris Escherichia coli fermentation',
 'gray box modeling bioprocess fermentation kinetics',
 'hybrid digital twin microbial bioreactor substrate biomass product',
 'hybrid modeling bioprocess neural networks dynamic prediction',
]
BRIEF='''Hybrid Modeling of Microbial Fermentation: Dynamic Prediction under Changing Operating Conditions.
Write a substantial Q1-oriented academic review on microbial bioreactor-scale mechanistic–data-driven hybrids.
Core: changed feed/induction trajectories; biomass, substrate and product balances; kinetics/parameter/rate/residual learning;
measurement and PAT, extrapolation, uncertainty, independent validation, identifiability, industrial deployment.
Prefer precise, evidence-calibrated academic prose. Remove defensive/self-justifying statements; discuss scientific limitations objectively.
Preserve TeX mathematics, figures, tables, captions, and user citations unless correcting an identified error.
Never fabricate DOI, experiments, numerical findings, or article-specific conclusions.
'''

class GateError(Exception): pass

def http_json(url, timeout=35):
 req=urllib.request.Request(url,headers={'User-Agent':'ReviewForge/4.0 (academic metadata discovery)','Accept':'application/json'})
 with urllib.request.urlopen(req, timeout=timeout) as r:return json.load(r)

def discover(query, limit=40):
 url='https://api.openalex.org/works?'+urllib.parse.urlencode({'search':query,'per-page':min(limit,100),'filter':'type:article','select':'id,doi,title,publication_year,authorships,primary_location,abstract_inverted_index'})
 return http_json(url).get('results',[])

def doi_normalize(doi):
 if not doi:return ''
 d=re.sub(r'^https?://(?:dx\.)?doi\.org/','',str(doi).strip(),flags=re.I)
 return d.lower().strip()

def crossref(doi):
 return http_json('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='/'))['message']

def bib_clean(s):return re.sub(r'[{}\\]','',str(s or '')).replace('\n',' ').strip()

def short_author(work):
 a=work.get('authorships') or []
 return (a[0].get('author') or {}).get('display_name','Anon').split()[-1] if a else 'Anon'

def collect_literature(workspace, target=60, max_queries=6):
 workspace=Path(workspace); workspace.mkdir(parents=True,exist_ok=True)
 existing=workspace/'literature.json'; papers=[]
 if existing.exists():
  try: papers=json.loads(existing.read_text(encoding='utf-8'))
  except (ValueError,OSError):papers=[]
 seen={doi_normalize(x.get('doi')) for x in papers if isinstance(x,dict)}
 log=[]
 for q in DEFAULT_QUERIES[:max_queries]:
  try:
   results=discover(q,70); log.append({'query':q,'status':'OK','hits':len(results)})
  except Exception as e:
   log.append({'query':q,'status':'UNAVAILABLE','error':type(e).__name__}); continue
  for w in results:
   doi=doi_normalize(w.get('doi'))
   if not doi or doi in seen:continue
   yr=w.get('publication_year'); title=w.get('title') or ''
   if not title or not isinstance(yr,int):continue
   try:
    meta=crossref(doi)
    registry_title=(meta.get('title') or [''])[0]
    if not registry_title:continue
    authors=[f"{a.get('given','')} {a.get('family','')}".strip() for a in meta.get('author',[])][:15]
    record={'doi':doi,'title':registry_title,'year':yr,'authors':authors,'venue':(meta.get('container-title') or [''])[0],
            'source':'OpenAlex+Crossref','metadata_status':'REGISTERED_METADATA','evidence_status':'ABSTRACT_OR_METADATA_ONLY',
            'key':None,'openalex_id':w.get('id'),'retrieval_query':q}
   except urllib.error.HTTPError as e:
    log.append({'doi':doi,'status':'CROSSREF_HTTP_'+str(e.code)});continue
   except Exception as e:
    log.append({'doi':doi,'status':'CROSSREF_UNAVAILABLE','error':type(e).__name__});continue
   papers.append(record);seen.add(doi)
  atomic_json(existing,papers);atomic_json(workspace/'reports/search_log.json',log)
  if len(papers)>=target+20:break
 keys=set()
 for x in papers:
  if not x.get('key'):
   stem=re.sub('[^A-Za-z0-9]','',short_author({'authorships':[{'author':{'display_name':(x.get('authors') or ['Anon'])[0]}}]}))
   base=(stem or 'Ref')+str(x.get('year','0000'))+hashlib.sha256(x['doi'].encode()).hexdigest()[:6]
   x['key']=base
  if x['key'] in keys:x['key']+=hashlib.sha1(x['doi'].encode()).hexdigest()[:4]
  keys.add(x['key'])
 atomic_json(existing,papers)
 make_bib(workspace,papers)
 atomic_json(workspace/'reports/literature_gate.json',{'target':target,'unique_registered_records':len(papers),
  'passed':len(papers)>=target,'metadata_only_not_semantically_verified':len(papers),'search_log':log})
 return papers

def make_bib(ws,papers):
 """Merge new registered records without overwriting the author's bibliography."""
 ws=Path(ws); bib=ws/'references.bib'
 existing=bib.read_text(encoding='utf-8',errors='replace') if bib.exists() else ''
 keys=parse_bibkeys(existing)
 entries=[]
 for p in papers:
  if not p.get('doi') or not p.get('key') or p['key'] in keys:continue
  fields={'title':p.get('title',''),'author':' and '.join(p.get('authors',[])),'year':p.get('year',''),
          'journal':p.get('venue',''),'doi':p['doi'],'url':'https://doi.org/'+p['doi']}
  lines=[f'  {key} = {{{bib_clean(val)}}}' for key,val in fields.items() if val]
  entries.append('@article{'+p['key']+',\n'+',\n'.join(lines)+'\n}')
 if entries:
  with bib.open('a',encoding='utf-8') as handle:
   if existing.strip():handle.write('\n\n')
   handle.write('\n\n'.join(entries)+'\n')


def extract_sections(tex):
 """Only replace top-level section bodies; preserve preamble, environments, math and bibliography tail."""
 matches=list(re.finditer(r'(?m)^\\section(?:\[[^\]]*\])?\{[^\n]*\}',tex))
 if not matches:return []
 tail=re.search(r'(?m)^\\(?:bibliography\{|printbibliography|end\{document\})',tex)
 return [(m.group(0),m.start(),(matches[i+1].start() if i+1<len(matches) else (tail.start() if tail and tail.start()>m.start() else len(tex)))) for i,m in enumerate(matches)]

def protect_tex(before,after):
 """Conservative structural gate; caller should inspect rejected reports."""
 tokens=[r'\\begin\{(?:figure\*?|table\*?|tikzpicture|equation\*?|align\*?)\}',r'\\label\{[^{}]+\}',r'\\includegraphics(?:\[[^]]+\])?\{[^}]+\}']
 for pattern in tokens:
  old=re.findall(pattern,before);new=re.findall(pattern,after)
  if any(new.count(x)<old.count(x) for x in set(old)):return False,'TeX structure or labels were removed: '+pattern
 # Equation and graphical source must remain byte-identical across AI edits.
 for env in ('equation','equation*','align','align*','gather','gather*','tikzpicture'):
  pattern=r'\\begin\{'+re.escape(env)+r'\}.*?\\end\{'+re.escape(env)+r'\}'
  if re.findall(pattern,before,re.S)!=re.findall(pattern,after,re.S):
   return False,'Protected scientific/graphical environment changed: '+env
 if after.count(r'\\begin{')!=after.count(r'\\end{'):return False,'Unbalanced environments'
 if after.count('$')%2:return False,'Odd number of inline math delimiters'
 if '\\documentclass' in after or '\\begin{document}' in after:return False,'Section edit attempted document reset'
 return True,''

def citations_used(tex):return set(re.findall(r'\\cite\w*(?:\[[^]]*\])*\{([^{}]+)\}',tex))

def cite_keys(tex):
 out=set()
 for group in citations_used(tex):out.update(z.strip() for z in group.split(','))
 return out

def client_chat(api,system,payload,role='writer'):
 return api.chat(system,json.dumps(payload,ensure_ascii=False),role=role)

def write_section(api,whole,section_head,section_body,papers,feedback=''):
 sources=[{'key':p['key'],'title':p['title'],'year':p['year'],'doi':p['doi'],'metadata_status':p['metadata_status']} for p in papers[:180]]
 sysmsg='''You are a senior reviewer-author in biochemical engineering. Rewrite ONLY the provided LaTeX section body.\nReturn plain LaTeX body without fences or the \\section header, preamble or bibliography. Preserve ALL figures, tables, TikZ, equations, labels, user citation commands and technical accuracy. Keep existing cross-reference targets (\\ref, \\eqref, \\autoref, \\cref) valid; you may move their mentions with reorganized prose, but do not invent or remove targets.\nCite supplied keys only when actually relevant from title/metadata; do NOT attribute findings, numerical results or detailed methods based on titles alone.\nYou may rename subsection, subsubsection and paragraph headings to improve clarity, brevity and scholarly organization. You may merge, split, or reorganize subheadings within this block when justified, but never omit substantive content, citations, figures, equations, tables, or labels. Make synthesis deep, arguments coherent, terms precise. Avoid defensive self-justifying prose. Do not replace equations with generic prose.\nIf evidence is insufficient, preserve existing supported statements and avoid inventing new ones. No full document output.\n'''
 return client_chat(api,sysmsg,{'brief':BRIEF,'section':section_head,'body':section_body,'reference_catalogue':sources,'reviewer_feedback':feedback})

def split_safe_blocks(body, limit=3200):
 """Split at headings and blank lines, never within LaTeX environments."""
 headings=list(re.finditer(r'(?m)^\\(?:subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{[^\n]*\}',body))
 boundaries=sorted(set([0,len(body)]+[m.start() for m in headings]))
 units=[]
 for a,b in zip(boundaries,boundaries[1:]):
  section=body[a:b]
  # Avoid splitting within a protected environment; accumulate paragraphs with environment depth.
  parts=re.split(r'(\n[ \t]*\n)',section)
  current=''
  for part in parts:
   if current and len(current)+len(part)>limit and current.count(r'\begin{')==current.count(r'\end{'):
    units.append(current);current=''
   current+=part
  if current:units.append(current)
 return [x for x in units if x]


def heading_inventory(text):
 """Track heading hierarchy independently of editable heading wording."""
 pattern=r'\\(subsection|subsubsection|paragraph)(\*?)(?:\[[^\]]*\])?\{[^\n]*\}'
 return [(m.group(1),m.group(2)) for m in re.finditer(pattern,text)]


def heading_change_log(old,new):
 pattern=r'\\(?:subsection|subsubsection|paragraph)\*?(?:\[[^\]]*\])?\{[^\n]*\}'
 before=re.findall(pattern,old)
 after=re.findall(pattern,new)
 return [{'before':a,'after':b} for a,b in zip(before,after) if a!=b]


def gate_block(old,new):
 if not new.strip() or len(new)<max(80,int(len(old)*.72)):
  return False,'Output empty or likely truncated'
 if cite_keys(old)-cite_keys(new):return False,'Existing citations removed'
 if heading_inventory(old)!=heading_inventory(new):
  # Structural reorganization is allowed only after independent scientific review.
  # All protected LaTeX, citations, labels and cross-references are still gated below.
  if len(heading_inventory(new))>max(20,3*max(1,len(heading_inventory(old)))):
   return False,'Excessive new headings; possible model-generated outline instead of revision'
 old_refs=set(re.findall(r'\\(?:ref|eqref|autoref|cref|Cref)\{([^}]+)\}',old))
 new_refs=set(re.findall(r'\\(?:ref|eqref|autoref|cref|Cref)\{([^}]+)\}',new))
 if old_refs-new_refs:
  return False,'Existing cross-reference targets removed: '+', '.join(sorted(old_refs-new_refs))
 if new_refs-old_refs:
  return False,'New cross-reference targets require whole-document validation: '+', '.join(sorted(new_refs-old_refs))
 for env in ('figure','figure*','table','table*','equation','equation*','align','align*','gather','gather*','tikzpicture'):
  p=r'\\begin\{'+re.escape(env)+r'\}.*?\\end\{'+re.escape(env)+r'\}'
  if re.findall(p,old,re.S)!=re.findall(p,new,re.S):return False,'Protected environment changed: '+env
 return protect_tex(old,new)


def review_blocks(api,tex,head,body,papers,ws,index,state,state_path):
 """Persist each accepted, independently reviewed block before moving on."""
 blocks=split_safe_blocks(body)
 directory=ws/'revisions'/('section_%02d_blocks'%(index+1))
 directory.mkdir(parents=True,exist_ok=True)
 output=[]
 for number,original in enumerate(blocks,1):
  fingerprint=hashlib.sha256(original.encode('utf-8')).hexdigest()
  record_path=directory/('block_%03d.json'%number)
  if record_path.exists():
   try:
    saved=json.loads(record_path.read_text(encoding='utf-8'))
    if saved.get('source_sha256')==fingerprint and saved.get('accepted') and gate_block(original,saved.get('candidate',''))[0]:
     output.append(saved['candidate'])
     state['active_block']=number
     atomic_json(state_path,state)
     continue
   except (OSError,ValueError,TypeError):pass
  if time.time()>=state['deadline']:
   state['status']='paused_deadline';atomic_json(state_path,state)
   return None
  # Never send a block containing structural environments for destructive rewriting.
  if re.search(r'\\begin\{(?:figure|table|equation|align|gather|tikzpicture)\*?\}|\\includegraphics',original):
   atomic_json(record_path,{'source_sha256':fingerprint,'accepted':True,'candidate':original,'mode':'protected_original'})
   output.append(original)
   continue
  feedback=''
  accepted=False
  attempt=1
  rate_count=0
  while attempt<=3 and time.time()<state['deadline']:
   state.update({'active_section':index+1,'active_block':number,'total_blocks':len(blocks),'active_attempt':attempt,'status':'requesting','heartbeat_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
   atomic_json(state_path,state)
   try:
    candidate=write_section(api,tex,head,original,papers,feedback=feedback).strip()
    state['calls']+=1
    ok,why=gate_block(original,candidate)
    verdict=review_section(api,head,original,candidate) if ok else {'accept':False,'issues':[why],'reason':'Structural gate'}
    if ok:state['calls']+=1
    if ok and verdict.get('accept') is True:
     atomic_json(record_path,{'source_sha256':fingerprint,'accepted':True,'candidate':candidate,'review':verdict,'attempt':attempt,'heading_changes':heading_change_log(original,candidate),'heading_structure_before':heading_inventory(original),'heading_structure_after':heading_inventory(candidate)})
     output.append(candidate);accepted=True
     state['heartbeat_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
     atomic_json(state_path,state)
     print(f'Accepted section {index+1} block {number}/{len(blocks)}; API calls {state["calls"]}',flush=True)
     break
    feedback='Correct the following review findings without deleting evidence or TeX: '+json.dumps(verdict.get('issues',[]),ensure_ascii=False)
    atomic_json(record_path,{'source_sha256':fingerprint,'accepted':False,'last_review':verdict,'attempt':attempt})
    attempt+=1
   except Exception as e:
    message=type(e).__name__+': '+str(e)[:300]
    if '429' in str(e):
     rate_count+=1
     delay=min(1800,60*2**min(rate_count-1,4))
     if time.time()+delay>=state['deadline']:
      state['status']='paused_rate_limit';state['last_error']=message;atomic_json(state_path,state)
      return None
     state['status']='rate_limited';state['last_error']=message;atomic_json(state_path,state)
     until=time.time()+delay
     while time.time()<until:
      time.sleep(min(30,max(.1,until-time.time())))
      state['heartbeat_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
      atomic_json(state_path,state)
     continue
    atomic_json(record_path,{'source_sha256':fingerprint,'accepted':False,'last_error':message,'attempt':attempt})
    attempt+=1
  if not accepted:
   state['status']='blocked_block';state['last_error']=f'Section {index+1}, block {number} failed; accepted earlier blocks retained'
   atomic_json(ws/'reports/blocked_block.json',{'section':index+1,'block':number,'total_blocks':len(blocks),'reason':state['last_error']})
   atomic_json(state_path,state)
   return None
 return ''.join(output)


def analyze_structure(text):
 return {'sections':[s[0] for s in extract_sections(text)],'citekeys':sorted(cite_keys(text)),
         'figures':text.count(r'\begin{figure'),'tables':text.count(r'\begin{table')}

def review_section(api,head,old,new):
 today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
 raw=client_chat(api,'Current UTC date: '+today+'. Treat this as the authoritative current date, not your training cutoff. Do not reject dates earlier than this date merely for being in the future; distinguish provenance verification from calendar consistency. You are a skeptical scientific reviewer. Give a concise JSON object only: {"accept": true/false, "issues": [string], "reason": string}. Reject missing equations/figures/citations, unsupported scientific specificity, loss of meaningful coverage, defensive prose, and incoherent method comparisons.',{'section':head,'before':old[:18000],'after':new[:18000],'current_date_utc':today},role='reviewer')
 try:return json.loads(raw.removeprefix('```json').removesuffix('```').strip())
 except ValueError:return {'accept':False,'issues':['Non-JSON review response'],'reason':'Parse failed'}

def generate_chinese_body(api,tex,papers,workspace):
 """Translate section bodies one at a time; preserve LaTeX. Expects XeLaTeX+ctex."""
 sections=extract_sections(tex)
 if not sections:raise GateError('No sections in TeX')
 result=tex; reports=[]
 for head,start,end in reversed(sections):
  original=tex[start:end]
  body=original[len(head):]
  sysmsg='Translate the supplied academic LaTeX section body into formal Chinese, preserving all LaTeX math, \u005c\u005ccite keys, figures, tables, captions, labels, environments, and data. Return ONLY translated LaTeX body; no markdown. Use objective academic style without defensive wording. Do not hallucinate findings.'
  proposed=client_chat(api,sysmsg,{'body':body,'research_topic':BRIEF},role='writer').strip()
  ok,why=protect_tex(body,proposed)
  if not ok:proposed=body
  reports.append({'section':head,'accepted':ok,'reason':why})
  result=result[:start]+head+'\n'+proposed+result[end:]
 # Translate front-matter abstract independently, keeping its LaTeX container.
 match=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',result,re.S)
 if match:
  try:
   old=match.group(1)
   chinese=client_chat(api,'Translate this research review abstract to rigorous scientific Chinese. Preserve LaTeX math and citekeys, return only translation, no commentary.',{'abstract':old},role='writer').strip()
   if protect_tex(old,chinese)[0] and cite_keys(old).issubset(cite_keys(chinese)):
    result=result[:match.start(1)]+chinese+result[match.end(1):]
  except Exception as e:reports.append({'abstract':'FAILED','reason':type(e).__name__})
 # Translate section headings using a single batch request; retain exact LaTeX syntax.
 english_heads=[m.group(1) for m in re.finditer(r'\\section\{([^{}]+)\}',result)]
 if english_heads:
  try:
   response=client_chat(api,'Translate these academic section heading strings into concise scientific Chinese. Return a JSON array of translated strings in the same order, no fences.',{'headings':english_heads},role='writer')
   translations=json.loads(response)
   if isinstance(translations,list) and len(translations)==len(english_heads) and all(isinstance(x,str) and x.strip() and not any(z in x for z in '{}\\') for x in translations):
    ii=iter(translations)
    result=re.sub(r'\\section\{([^{}]+)\}',lambda m:r'\section{'+next(ii)+'}',result)
  except Exception as e:reports.append({'headings':'FAILED','reason':type(e).__name__})
 # Replace English title with known Chinese scientific title.
 result=re.sub(r'\\title\{[^{}]*\}',r'\title{微生物发酵混合建模：变化操作条件下的动态预测}',result,count=1)
 atomic_json(workspace/'reports/translation_gate.json',reports)
 # Replace English document preamble only with explicit ctex and twocolumn settings.
 if r'\documentclass' in result and r'\usepackage{ctex}' not in result:
  pos=result.find(r'\begin{document}')
  result=result[:pos]+r'\usepackage[UTF8]{ctex}'+'\n'+result[pos:]
 result=re.sub(r'(\\documentclass)(\[[^\]]*\])?(\{[^}]+\})',lambda m:m.group(1)+'[twocolumn]'+m.group(3),result,count=1)
 return result

def compile_tex(ws,basename):
 """Compile without any LLM calls; fail closed on stale outputs or LaTeX errors."""
 ws=Path(ws).resolve()
 output=ws/'output';output.mkdir(parents=True,exist_ok=True)
 reports=ws/'reports';reports.mkdir(parents=True,exist_ok=True)
 tex=ws/(basename+'.tex')
 pdf=output/(basename+'.pdf')
 cmd=shutil.which('latexmk')
 engine=shutil.which('xelatex')
 report={'status':'FAILED','pdf':None,'api_calls':0,'engine':'xelatex',
         'source_sha256':hashlib.sha256(tex.read_bytes()).hexdigest() if tex.exists() else None}
 if not tex.exists():
  report['reason']='Missing TeX source'
 elif not cmd or not engine:
  report['status']='UNAVAILABLE'
  report['reason']='latexmk or xelatex not installed'
 else:
  # Delete only the generated PDF: old outputs cannot be reported as new.
  if pdf.exists():pdf.unlink()
  args=[cmd,'-gg','-xelatex','-interaction=nonstopmode','-halt-on-error',
        '-file-line-error','-outdir=output',tex.name]
  report['command']=args
  try:
   p=subprocess.run(args,cwd=ws,capture_output=True,text=True,errors='replace',timeout=600)
   log=(p.stdout or '')+'\n'+(p.stderr or '')
   logpath=output/(basename+'.log')
   if logpath.exists():log+='\n'+logpath.read_text(encoding='utf-8',errors='replace')[-20000:]
   report['exit_code']=p.returncode
   report['errors']=re.findall(r'(?m)^! .+|^.+?:\d+: .+|^Latexmk: .+',log)[-30:]
   report['missing_packages']=sorted(set(re.findall(r"File [`']([^'`]+\.(?:sty|cls|bib))",log)))
   report['log_tail']=log[-7000:]
   report['status']='PASS' if p.returncode==0 and pdf.is_file() and pdf.stat().st_size>0 else 'FAILED'
   if report['status']=='PASS':report['pdf']=str(pdf.relative_to(ws))
  except subprocess.TimeoutExpired:
   report['reason']='latexmk timed out after 600 seconds'
  except OSError as e:
   report['reason']=str(e)
 atomic_json(reports/(basename+'_build.json'),report)
 return report



def bib_keys(text):
 return parse_bibkeys(text)


def audit(ws,minimum=60):
 ws=Path(ws)
 integrity=write_integrity(ws)
 languages=integrity['languages']
 citation_pass=all(languages[lang]['cited_count']>=minimum and
                   not languages[lang]['missing_bibliography_keys'] for lang in ('en','zh'))
 return {'minimum':minimum,'integrity':integrity,'citation_gate_pass':citation_pass,
         'semantic_source_support':'NOT_VERIFIED',
         'submission_ready':False}



def run_v4(ws=WORK,hours=9,resume=False,minimum=60,skip_search=False,skip_translation=False):
 ws=Path(ws).resolve(); (ws/'reports').mkdir(parents=True,exist_ok=True); (ws/'revisions').mkdir(exist_ok=True);(ws/'output').mkdir(exist_ok=True)
 state_path=ws/'v4_state.json'
 if resume:
  if not state_path.exists():raise GateError('No v4 checkpoint to resume')
  state=json.loads(state_path.read_text(encoding='utf-8'))
  # Legacy checkpoints could advance past rejected sections and enter translation.
  failed=[h['section'] for h in state.get('history',[]) if isinstance(h.get('section'),int) and not h.get('accepted',False)]
  if failed and state.get('stage') in ('writing','translation','compile','finished'):
   first=min(failed)
   state['section']=first
   state['stage']='writing'
   state['history']=[h for h in state['history'] if not isinstance(h.get('section'),int) or h['section']<first]
  if time.time()>=state.get('deadline',0):
   state['deadline']=time.time()+hours*3600
  atomic_json(state_path,state)
 else:
  if state_path.exists():raise GateError('Existing checkpoint: choose --resume or archive it')
  start=time.time(); state={'started':start,'deadline':start+hours*3600,'stage':'literature','section':0,'calls':0,'history':[]}
  atomic_json(state_path,state)
 source=ws/'original.tex'
 if not source.exists():raise GateError('Put your complete English LaTeX source at workspace/original.tex')
 raw=source.read_text(encoding='utf-8')
 if '\\begin{document}' not in raw:raise GateError('Original is not a complete LaTeX document')
 src_hash=hashlib.sha256(raw.encode()).hexdigest()
 if state.get('source_sha256') and state['source_sha256']!=src_hash:raise GateError('Original modified after checkpoint')
 state['source_sha256']=src_hash;atomic_json(state_path,state)
 if state['stage']=='literature':
  if not skip_search:collect_literature(ws,target=minimum)
  elif not (ws/'literature.json').exists():raise GateError('--skip-search requires literature.json')
  papers=json.loads((ws/'literature.json').read_text(encoding='utf-8'))
  make_bib(ws,papers)
  state['stage']='writing';atomic_json(state_path,state)
 else:papers=json.loads((ws/'literature.json').read_text(encoding='utf-8'))
 if len(papers)<minimum:
  atomic_json(ws/'reports/blockers.json',{'stage':'literature','required':minimum,'found':len(papers),'reason':'Metadata search insufficient; cannot claim >=60 references'})
  return state
 api=CompatibleAPI()
 tex=raw if not (ws/'review_en.tex').exists() else (ws/'review_en.tex').read_text(encoding='utf-8')
 if state['stage']=='writing':
  expected=[h for h,_,_ in extract_sections(raw)]
  actual=[h for h,_,_ in extract_sections(tex)]
  if actual!=expected:
   atomic_json(ws/'reports/section_integrity_error.json',{'original_count':len(expected),'current_count':len(actual),'original_headings':expected,'current_headings':actual,'action':'Restore from original and audit accepted revisions before resuming'})
   raise GateError('Section inventory differs from original; resume blocked to prevent manuscript loss. See reports/section_integrity_error.json')
  sections=extract_sections(tex)
  if not sections:raise GateError('No \\section blocks detected')
  while state['section']<len(sections):
   if time.time()>=state['deadline']:break
   index=state['section']
   head,start,end=sections[index]
   body=tex[start+len(head):end]
   candidate=review_blocks(api,tex,head,body,papers,ws,index,state,state_path)
   if candidate is None:
    print(f'Section {index+1} paused; accepted blocks saved for resume',flush=True)
    break
   ok,why=gate_block(body,candidate)
   if not ok:
    state['status']='blocked_section';state['last_error']=why;atomic_json(state_path,state)
    break
   proposed=tex[:start]+head+candidate+tex[end:]
   if [h for h,_,_ in extract_sections(proposed)]!=expected:
    state['status']='blocked_section';state['last_error']='Section inventory changed';atomic_json(state_path,state)
    break
   # Check both the complete section and all protected structural material.
   if not cite_keys(body).issubset(cite_keys(candidate)):
    state['status']='blocked_section';state['last_error']='Section citations removed';atomic_json(state_path,state)
    break
   from quality_audit import write_depth_report
   write_depth_report(candidate,ws/'reports'/f'section_{index+1:02}_depth.json')
   (ws/'revisions'/f'section_{index+1:02}.tex').write_text(candidate,encoding='utf-8')
   tex=proposed
   (ws/'review_en.tex').write_text(tex,encoding='utf-8')
   state['section']=index+1
   state['status']='section_complete'
   state['history']=[h for h in state.get('history',[]) if h.get('section')!=index or h.get('accepted')]
   state['history'].append({'section':index,'accepted':True,'blocks':len(split_safe_blocks(body))})
   atomic_json(state_path,state)
   print(f'Accepted section {index+1}/{len(sections)}; API calls {state["calls"]}',flush=True)
   sections=extract_sections(tex)
  if state['section']>=len(sections):
   state['stage']='consistency';atomic_json(state_path,state)
 if state['stage']=='consistency':
  report={'sections':len(extract_sections(tex)),'expected_sections':len(extract_sections(raw)),'missing_original_citations':sorted(cite_keys(raw)-cite_keys(tex)),'figure_count_original':raw.count(r'\begin{figure'),'figure_count_current':tex.count(r'\begin{figure'),'table_count_original':raw.count(r'\begin{table'),'table_count_current':tex.count(r'\begin{table'),'duplicate_section_titles':len(set(h for h,_,_ in extract_sections(tex)))!=len(extract_sections(tex)),'scientific_claim_verification':'REQUIRES_PRIMARY_SOURCE_REVIEW'}
  report['passed']=report['sections']==report['expected_sections'] and not report['missing_original_citations'] and report['figure_count_current']>=report['figure_count_original'] and report['table_count_current']>=report['table_count_original'] and not report['duplicate_section_titles']
  atomic_json(ws/'reports/full_manuscript_consistency.json',report)
  state['stage']='translation' if report['passed'] else 'consistency_blocked';atomic_json(state_path,state)
 if state['stage']=='translation' and not skip_translation and time.time()<state['deadline']:
  # Avoid creating a misleading partial Chinese file: translate when API and time budget permit.
  try:
   zh=generate_chinese_body(api,tex,papers,ws)
   (ws/'review_zh.tex').write_text(zh,encoding='utf-8')
   state['stage']='compile';atomic_json(state_path,state)
  except Exception as e:atomic_json(ws/'reports/translation_error.json',{'error':str(e)})
 elif state['stage']=='translation' and skip_translation:state['stage']='compile';atomic_json(state_path,state)
 if state['stage']=='compile':
  for name in ('review_en','review_zh'):
   if (ws/(name+'.tex')).exists():
    report=compile_tex(ws,name)
    atomic_json(ws/'reports'/(name+'_build.json'),report)
  result=audit(ws,minimum=minimum)
  atomic_json(ws/'reports/final_audit.json',result)
  evaluate_quality(ws,minimum)
  state['stage']='finished';atomic_json(state_path,state)
 return state

def main():
 parser=argparse.ArgumentParser(description='ReviewForge v4 academic review automation')
 parser.add_argument('action',choices=['discover','audit','compile','quality','quality-init','plan','improve','run','resume','preflight'])
 parser.add_argument('--workspace',default=str(WORK));parser.add_argument('--hours',type=float,default=9)
 parser.add_argument('--minimum',type=int,default=60);parser.add_argument('--skip-search',action='store_true')
 parser.add_argument('--skip-translation',action='store_true');args=parser.parse_args()
 load_env(ROOT/'.env');ws=Path(args.workspace);(ws/'reports').mkdir(parents=True,exist_ok=True)
 if args.action=='plan':
  from review_planner import planning_contract
  source=ws/'original.tex'
  if not source.exists():raise GateError('Planning requires workspace/original.tex; original is never modified')
  draft=source.read_text(encoding='utf-8')
  topic_file=ws/'review_topic.txt'
  topic=topic_file.read_text(encoding='utf-8').strip() if topic_file.exists() else ''
  if not topic:
   match=re.search(r'\\\\title\\{([^{}]+)\\}',draft)
   topic=match.group(1) if match else 'Academic literature review (topic to be confirmed)'
  contract=planning_contract(topic,draft)
  atomic_json(ws/'reports/review_plan_input.json',contract)
  api=CompatibleAPI()
  instructions=('You are a scholarly review architect. Return ONLY a JSON object matching output_schema. '
   'Propose the chapter count and hierarchy based on the scientific question, not the existing chapter count. '
   'Diagnose weak draft coverage, compare alternative structures, and explain each chapter\'s argument and evidence needs. '
   'Do not invent primary-study findings or references. Use the original only as source material. '
   'Mark claims requiring primary-source verification. This is a proposed outline, not a completed evidence audit.')
  raw_plan=client_chat(api,instructions,{'planning_contract':contract,'draft_excerpt':draft[:45000]},role='writer')
  try:
   plan=json.loads(raw_plan.removeprefix('```json').removeprefix('```').removesuffix('```').strip())
   if not isinstance(plan,dict) or not isinstance(plan.get('chapters'),list) or len(plan['chapters'])<2:
    raise ValueError('Missing chapters')
  except ValueError:
   atomic_json(ws/'reports/review_plan_unparsed.json',{'raw':raw_plan})
   raise GateError('Planning output not valid JSON; inspect reports/review_plan_unparsed.json')
  atomic_json(ws/'reports/review_plan_proposed.json',plan)
  print(json.dumps({'proposed_chapters':len(plan['chapters']),'plan':str(ws/'reports/review_plan_proposed.json'),'original_unchanged':True},ensure_ascii=False))
  return
 if args.action=='improve':
  from quality_loop import improve,save
  source=ws/'review_en.tex'
  if not source.exists():raise GateError('Run improve after review_en.tex exists')
  tex=source.read_text(encoding='utf-8')
  sections=extract_sections(tex)
  if not sections:raise GateError('No sections for improvement')
  api=CompatibleAPI()
  def ask(prompt,payload):
   return client_chat(api,prompt,payload,role='reviewer' if 'Independent scholarly reviewer' in prompt else 'writer')
  from evidence_gate import evidence_gate,provenance_audit
  report=[]
  for index,(heading,start,end) in enumerate(sections,1):
   body=tex[start+len(heading):end]
   def combined_gate(before,after):
    ok,why=gate_block(before,after)
    if not ok:return ok,why
    safe,reason,_=evidence_gate(before,after,ws)
    return safe,reason
   result=improve(ask,combined_gate,heading,body,max_rounds=3)
   result['evidence_audit']=provenance_audit(body,result['text'],ws)
   if result['status']=='provisional_pass':
    result['status']='model_review_pass_evidence_unverified'
   save(result,ws/'quality_revisions',f'section_{index:02d}')
   report.append({'section':index,'heading':heading,'score':result['review']['total'],'status':result['status']})
  atomic_json(ws/'reports/quality_improvement_summary.json',report)
  print(json.dumps({'reviewed_sections':len(report),'outputs':str(ws/'quality_revisions'),'master_unchanged':True},ensure_ascii=False))
  return
 if args.action=='discover':print('registered metadata records:',len(collect_literature(ws,args.minimum)));return
 if args.action=='preflight':
  print(json.dumps({'original_tex_exists':(ws/'original.tex').exists(),'latexmk':bool(shutil.which('latexmk')),
  'xelatex':bool(shutil.which('xelatex')),'bibtex':bool(shutil.which('bibtex')),
  'key_configured':bool(os.environ.get('RF_API_KEY')),'workspace':str(ws)},indent=2));return
 if args.action=='audit':print(json.dumps(audit(ws,args.minimum),ensure_ascii=False,indent=2));return
 if args.action=='quality-init':print(json.dumps({'created':scaffold_quality(ws)},ensure_ascii=False,indent=2));return
 if args.action=='quality':print(json.dumps(evaluate_quality(ws,args.minimum),ensure_ascii=False,indent=2));return
 if args.action=='compile':
  for name in ('review_en','review_zh'):
   if (ws/(name+'.tex')).exists():print(name,compile_tex(ws,name))
  return
 state=run_v4(ws,args.hours,args.action=='resume',args.minimum,args.skip_search,args.skip_translation)
 print(json.dumps({'stage':state['stage'],'sections_processed':state['section'],'calls':state['calls'],'reports':str(ws/'reports')},ensure_ascii=False))

if __name__=='__main__':
 try:main()
 except (GateError,FileNotFoundError,ValueError) as e:print('ERROR:',str(e));sys.exit(2)
