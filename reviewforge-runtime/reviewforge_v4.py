"""ReviewForge v4: section-level evidence-aware bilingual review workflow.
All data is local except optional OpenAlex/Crossref/compatible-chat API calls.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from reviewforge import CompatibleAPI, load_env, atomic_json

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
 ws=Path(ws); entries=[]
 for p in papers:
  if not p.get('doi') or not p.get('key'):continue
  fields={'title':p.get('title',''),'author':' and '.join(p.get('authors',[])),'year':p.get('year',''),
          'journal':p.get('venue',''),'doi':p['doi'],'url':'https://doi.org/'+p['doi']}
  lines=[f'  {key} = {{{bib_clean(val)}}}' for key,val in fields.items() if val]
  entries.append('@article{'+p['key']+',\n'+',\n'.join(lines)+'\n}')
 (ws/'references.bib').write_text('\n\n'.join(entries)+'\n',encoding='utf-8')

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
 if after.count(r'\begin{')!=after.count(r'\end{'):return False,'Unbalanced environments'
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
 sysmsg='''You are a senior reviewer-author in biochemical engineering. Rewrite ONLY the provided LaTeX section body.\nReturn plain LaTeX body without fences or the \\section header, preamble or bibliography. Preserve ALL figures, tables, TikZ, equations, labels, user citation commands and technical accuracy.\nCite supplied keys only when actually relevant from title/metadata; do NOT attribute findings, numerical results or detailed methods based on titles alone.\nMake synthesis deep, arguments coherent, terms precise. Avoid defensive self-justifying prose. Do not replace equations with generic prose.\nIf evidence is insufficient, preserve existing supported statements and avoid inventing new ones. No full document output.\n'''
 return client_chat(api,sysmsg,{'brief':BRIEF,'section':section_head,'body':section_body,'reference_catalogue':sources,'reviewer_feedback':feedback})

def analyze_structure(text):
 return {'sections':[s[0] for s in extract_sections(text)],'citekeys':sorted(cite_keys(text)),
         'figures':text.count(r'\begin{figure'),'tables':text.count(r'\begin{table')}

def review_section(api,head,old,new):
 raw=client_chat(api,'You are a skeptical scientific reviewer. Give a concise JSON object only: {"accept": true/false, "issues": [string], "reason": string}. Reject missing equations/figures/citations, unsupported scientific specificity, loss of meaningful coverage, defensive prose, and incoherent method comparisons.',{'section':head,'before':old[:18000],'after':new[:18000]},role='reviewer')
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
  """Deterministic offline build; never invokes a language-model API."""
  ws=Path(ws).resolve()
  cmd=shutil.which('latexmk')
  engine=shutil.which('xelatex')
  if not cmd or not engine:
   return {'status':'UNAVAILABLE','reason':'latexmk or xelatex not installed','pdf':None}
  texfile=ws/(basename+'.tex')
  if not texfile.is_file():
   return {'status':'FAILED','reason':'missing source','pdf':None}
  output=ws/'output'
  output.mkdir(parents=True,exist_ok=True)
  pdf=output/(basename+'.pdf')
  # An existing PDF must never be mistaken for a successful new build.
  old_pdf_mtime=pdf.stat().st_mtime_ns if pdf.exists() else None
  args=[cmd,'-gg','-xelatex','-interaction=nonstopmode','-halt-on-error',
        '-file-line-error','-outdir=output',texfile.name]
  try:
   p=subprocess.run(args,cwd=ws,capture_output=True,text=True,errors='replace',timeout=600)
   combined=(p.stdout or '')+'\n'+(p.stderr or '')
   logpath=output/(basename+'.log')
   if logpath.exists():
    combined+='\n'+logpath.read_text(encoding='utf-8',errors='replace')[-20000:]
   errors=re.findall(r'(?m)^! .+|^.+?:\\d+: .+|^Latexmk: .+',combined)
   missing=sorted(set(re.findall(r"(?:File [`']|! LaTeX Error: File [`'])([^'`]+\\.(?:sty|cls|bib))",combined)))
   fresh=pdf.exists() and (old_pdf_mtime is None or pdf.stat().st_mtime_ns!=old_pdf_mtime)
   status='PASS' if p.returncode==0 and pdf.exists() and fresh else 'FAILED'
   report={'status':status,'exit_code':p.returncode,'pdf':str(pdf.relative_to(ws)) if status=='PASS' else None,
           'pdf_exists':pdf.exists(),'fresh_pdf':fresh,'missing_packages':missing,
           'errors':errors[-30:],'log_tail':combined[-6000:],
           'command':args,'api_calls':0}
  except subprocess.TimeoutExpired as e:
   report={'status':'FAILED','reason':'latexmk timed out after 600 seconds','pdf':None,'api_calls':0}
  except OSError as e:
   report={'status':'FAILED','reason':str(e),'pdf':None,'api_calls':0}
  atomic_json(ws/'reports'/(basename+'_build.json'),report)
  return report


def bib_keys(text):
  """Extract BibTeX entry identifiers without relying on generated literature.json."""
  return set(re.findall(r'(?m)^\\s*@[A-Za-z]+\\s*[{(]\\s*([^,\\s]+)\\s*,',text))


def audit(ws,minimum=60):
  ws=Path(ws)
  papers=json.loads((ws/'literature.json').read_text(encoding='utf-8')) if (ws/'literature.json').exists() else []
  registered={p['key'] for p in papers if p.get('key')}
  bibfile=ws/'references.bib'
  bib=bib_keys(bibfile.read_text(encoding='utf-8',errors='replace')) if bibfile.exists() else set()
  en=(ws/'review_en.tex').read_text(encoding='utf-8') if (ws/'review_en.tex').exists() else ''
  zh=(ws/'review_zh.tex').read_text(encoding='utf-8') if (ws/'review_zh.tex').exists() else ''
  enkeys=cite_keys(en); zhkeys=cite_keys(zh)
  # A citation key present in a catalogue is not necessarily present in the compiled bibliography.
  missing_en=sorted(enkeys-bib)
  missing_zh=sorted(zhkeys-bib)
  complete=bool(bib) and not missing_en and not missing_zh
  return {'minimum':minimum,'registered_references':len(registered),'bib_entries':len(bib),
          'english_used_references':len(enkeys),'chinese_used_references':len(zhkeys),
          'english_unknown_keys':sorted(enkeys-registered),
          'chinese_unknown_keys':sorted(zhkeys-registered),
          'english_missing_bib_keys':missing_en,'chinese_missing_bib_keys':missing_zh,
          'english_only_keys':sorted(enkeys-zhkeys),'chinese_only_keys':sorted(zhkeys-enkeys),
          'bib_integrity_pass':complete,
          'minimum_pass':complete and len(enkeys)>=minimum and len(zhkeys)>=minimum,
          'semantic_source_support':'NOT_VERIFIED',
          'metadata_verification':'CATALOGUE_ONLY_NOT_INDEPENDENTLY_RECHECKED',
          'submission_ready':False,
          'citation_warning':'Matching BibTeX keys and DOI metadata do not establish scientific support. Verify primary texts and claim-level evidence.'}

def run_v4(ws=WORK,hours=9,resume=False,minimum=60,skip_search=False,skip_translation=False):
 ws=Path(ws).resolve(); (ws/'reports').mkdir(parents=True,exist_ok=True); (ws/'revisions').mkdir(exist_ok=True);(ws/'output').mkdir(exist_ok=True)
 state_path=ws/'v4_state.json'
 if resume:
  if not state_path.exists():raise GateError('No v4 checkpoint to resume')
  state=json.loads(state_path.read_text(encoding='utf-8'))
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
  sections=extract_sections(tex)
  if not sections:raise GateError('No \\section blocks detected')
  for index in range(state['section'],len(sections)):
   if time.time()>=state['deadline']:break
   head,start,end=sections[index];chunk=tex[start:end];body=chunk[len(head):]
   if len(body)>30000:
    state['history'].append({'section':index,'status':'SKIPPED_TOO_LONG','characters':len(body)});state['section']=index+1;atomic_json(state_path,state);continue
   try:
    candidate=write_section(api,tex,head,body,papers).strip();state['calls']+=1
    ok,why=protect_tex(body,candidate)
    # user citations and labels cannot be lost, including all existing citekeys in section
    if ok and not cite_keys(body).issubset(cite_keys(candidate)):ok=False;why='Existing citekeys removed'
    verdict=review_section(api,head,body,candidate) if ok else {'accept':False,'issues':[why],'reason':'Structural gate'}
    if ok:state['calls']+=1
    accepted=ok and verdict.get('accept') is True
    if accepted:
     tex=tex[:start]+head+'\n'+candidate+'\n'+tex[end:]
     (ws/'revisions'/f'section_{index+1:02}.tex').write_text(candidate,encoding='utf-8')
    state['history'].append({'section':index,'accepted':accepted,'review':verdict})
   except Exception as e:
    state['history'].append({'section':index,'accepted':False,'error':type(e).__name__+': '+str(e)[:300]})
   (ws/'review_en.tex').write_text(tex,encoding='utf-8')
   state['section']=index+1;atomic_json(state_path,state)
   sections=extract_sections(tex)
  if state['section']>=len(sections):state['stage']='translation';atomic_json(state_path,state)
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
  state['stage']='finished';atomic_json(state_path,state)
 return state

def main():
 parser=argparse.ArgumentParser(description='ReviewForge v4 academic review automation')
 parser.add_argument('action',choices=['discover','audit','compile','run','resume','preflight'])
 parser.add_argument('--workspace',default=str(WORK));parser.add_argument('--hours',type=float,default=9)
 parser.add_argument('--minimum',type=int,default=60);parser.add_argument('--skip-search',action='store_true')
 parser.add_argument('--skip-translation',action='store_true');args=parser.parse_args()
 load_env(ROOT/'.env');ws=Path(args.workspace);(ws/'reports').mkdir(parents=True,exist_ok=True)
 if args.action=='discover':print('registered metadata records:',len(collect_literature(ws,args.minimum)));return
 if args.action=='preflight':
  print(json.dumps({'original_tex_exists':(ws/'original.tex').exists(),'latexmk':bool(shutil.which('latexmk')),
  'xelatex':bool(shutil.which('xelatex')),'bibtex':bool(shutil.which('bibtex')),
  'key_configured':bool(os.environ.get('RF_API_KEY')),'workspace':str(ws)},indent=2));return
 if args.action=='audit':print(json.dumps(audit(ws,args.minimum),ensure_ascii=False,indent=2));return
 if args.action=='compile':
  for name in ('review_en','review_zh'):
   if (ws/(name+'.tex')).exists():print(name,compile_tex(ws,name))
  return
 state=run_v4(ws,args.hours,args.action=='resume',args.minimum,args.skip_search,args.skip_translation)
 print(json.dumps({'stage':state['stage'],'sections_processed':state['section'],'calls':state['calls'],'reports':str(ws/'reports')},ensure_ascii=False))

if __name__=='__main__':
 try:main()
 except (GateError,FileNotFoundError,ValueError) as e:print('ERROR:',str(e));sys.exit(2)
