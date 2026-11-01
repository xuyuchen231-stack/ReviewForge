"""Compact bilingual results and verified cleanup of explicitly generated validation folders."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import time
import uuid
import zipfile
from contextlib import contextmanager
from reviewforge import atomic_json

VALIDATION_NAMES={'layout_route_validation','reference_order_validation','comprehensive_validation',
                  'release_route_validation','gpt_workflow_validation','delivery_route_validation'}
RUN_VALIDATION_NAMES={'publication_revision','publication_automatic_validation','editorial_validation','editorial_readiness_validation'}
DERIVED_SUFFIXES={'.aux','.xdv','.fls','.fdb_latexmk','.toc','.synctex'}


def _sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def _new_zip(path):
    try:
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as archive:yield archive
    except BaseException:
        if path.exists():path.unlink()
        raise


def _workspace(run):
    return next((p.parent for p in (run,*run.parents) if p.name=='autonomous_runs'),run.parent)


def _safe(path,root):
    root=Path(root).resolve();path=Path(path).absolute()
    if not path.resolve().is_relative_to(root):raise ValueError('Cleanup target outside workspace')
    for part in (path,*path.parents):
        if part.exists():
            flags=getattr(part.lstat(),'st_file_attributes',0)
            if part.is_symlink() or flags&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):raise ValueError('Links and junctions are not cleanup targets')
        if part==root:break
    return path.resolve()


def _time_name(epoch):return dt.datetime.fromtimestamp(epoch).astimezone().strftime('%Y%m%d_%H%M%S')


def publish_latest(run,report,output=None,started=None,finished=None):
    """Publish both fresh languages together; previous complete pair survives any failure."""
    run=Path(run).resolve();out=Path(output or run/'output').resolve()
    scope=Path(report.get('retention_run',run)).resolve()
    if not run.is_relative_to(scope):raise ValueError('Retention scope must contain publication run')
    if report.get('publication_acceptance',{}).get('technical_ready') is False:return {'status':'WAITING_FOR_VALIDATION'}
    if report.get('citation_order',{}).get('status') not in (None,'PASS','NOT_APPLICABLE'):return {'status':'WAITING_FOR_VALIDATION'}
    if report.get('chinese_citation_order',{}).get('status') not in (None,'PASS','NOT_APPLICABLE') or report.get('chinese_prose_presentation',{}).get('status') in ('FAILED','NEEDS_REVIEW'):return {'status':'WAITING_FOR_VALIDATION'}
    results=_workspace(scope)/'成果';internal=results/'内部资料'
    for language,key in (('en','review_en_build'),('zh','review_zh_build')):
        build=report.get(key,{})
        if build.get('status')!='PASS' or build.get('layout_status')!='PASS' or build.get('visual_status')=='FAILED':return {'status':'WAITING_FOR_CHINESE' if language=='zh' else 'WAITING_FOR_ENGLISH'}
        pdf=_safe(out/build.get('pdf','output/review_'+language+'.pdf'),out)
        source=out/('review_'+language+'.tex')
        if not pdf.is_file() or not source.is_file():return {'status':'WAITING_FOR_CHINESE' if language=='zh' else 'WAITING_FOR_ENGLISH'}
        if not build.get('source_sha256') or not build.get('pdf_sha256'):return {'status':'WAITING_FOR_VALIDATION'}
        if build['source_sha256']!=_sha(source) or build['pdf_sha256']!=_sha(pdf):return {'status':'WAITING_FOR_CHINESE' if language=='zh' else 'WAITING_FOR_ENGLISH'}
    provenance=out/'translation_provenance.json'
    if not provenance.exists():return {'status':'WAITING_FOR_CHINESE'}
    translated=json.loads(provenance.read_text(encoding='utf-8'))
    if translated.get('english_sha256')!=_sha(out/'review_en.tex') or translated.get('chinese_sha256')!=_sha(out/'review_zh.tex'):return {'status':'WAITING_FOR_CHINESE'}
    finished=finished or time.time();basis='recorded session'
    if started is None:
        started=report.get('run_started_epoch')
        requests=scope/'editorial/requests.jsonl'
        if started is None and requests.exists():
            starts=[r.get('started_epoch') for line in requests.read_text(encoding='utf-8').splitlines() if (r:=json.loads(line)).get('started_epoch')]
            if starts:started=min(starts);basis='earliest recorded request (legacy run)'
    if started is None:started=finished;basis='start unknown; publication time used'
    internal.mkdir(parents=True,exist_ok=True)
    latest=internal/'latest.json';previous=json.loads(latest.read_text(encoding='utf-8')) if latest.exists() else {}
    names={lang:'ReviewForge_开始'+_time_name(started)+'_结束'+_time_name(finished)+'_'+label+'.pdf' for lang,label in (('en','英文'),('zh','中文'))}
    archive=internal/'latest-source.zip';temporary=internal/(uuid.uuid4().hex+'.tmp')
    with _new_zip(temporary) as z:
        for language in ('en','zh'):z.write(out/('review_'+language+'.tex'),'review_'+language+'.tex')
        reference=report.get('source_versions',report.get('editorial',{}).get('versions',{})).get('clean',{}).get('path')
        if reference:
            reference=_safe(reference,scope)
            if reference.name=='full_cleaned.tex' and reference.is_file():z.write(reference,'full_cleaned.tex')
        from autonomous_delivery import copy_project_assets
        with tempfile.TemporaryDirectory(prefix='rf_source_assets_') as folder:
            assets=Path(folder)
            copied=copy_project_assets(out,assets,(out/'review_en.tex').read_text(encoding='utf-8')+'\n'+(out/'review_zh.tex').read_text(encoding='utf-8'))
            if copied['missing']:raise ValueError('Editable source archive assets missing')
            for path in sorted(assets.rglob('*')):
                if path.is_file():z.write(path,'overleaf/'+path.relative_to(assets).as_posix())
        for name in ('cuted.dtx','sttools.ins','README.md'):
            path=out/'tex_support'/name
            if path.is_file():z.write(_safe(path,out),'overleaf/tex_support/'+name)
        z.write(out/'review_en.tex','overleaf/main.tex')
        z.write(out/'review_zh.tex','overleaf/review_zh.tex')
        z.writestr('run.json',json.dumps({'started_at':dt.datetime.fromtimestamp(started).astimezone().isoformat(),'finished_at':dt.datetime.fromtimestamp(finished).astimezone().isoformat(),'start_time_basis':basis,'source_sha256':{lang:report['review_'+lang+'_build']['source_sha256'] for lang in ('en','zh')},'expert_verified':False},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(temporary) as z:
        if z.testzip() is not None:raise ValueError('Source archive failed verification')
    staged_files={}
    try:
        for language in ('en','zh'):
            source=out/report['review_'+language+'_build'].get('pdf','output/review_'+language+'.pdf')
            staged=internal/(names[language]+'.tmp');staged_files[language]=staged
            shutil.copyfile(source,staged)
            if _sha(staged)!=report['review_'+language+'_build']['pdf_sha256']:raise ValueError('Published PDF copy mismatch')
        for language in ('en','zh'):
            if _sha(out/('review_'+language+'.tex'))!=report['review_'+language+'_build']['source_sha256']:raise ValueError('Publication source changed during staging')
    except Exception:
        for path in staged_files.values():
            if path.exists():path.unlink()
        if temporary.exists():temporary.unlink()
        raise
    for language,path in staged_files.items():path.replace(results/names[language])
    temporary.replace(archive)
    obsolete=set(previous.get('files',{}).values())|set(previous.get('obsolete_files',[]))
    obsolete-=set(names.values())
    manifest={'status':'PUBLISHED','files':names,'started_at':dt.datetime.fromtimestamp(started).astimezone().isoformat(),
              'finished_at':dt.datetime.fromtimestamp(finished).astimezone().isoformat(),'start_time_basis':basis,
              'directory':str(results),'source_archive':str(archive),'obsolete_files':sorted(obsolete),
              'visual_status':{lang:report['review_'+lang+'_build'].get('visual_status','PENDING') for lang in ('en','zh')},'expert_verified':False}
    atomic_json(latest,manifest)
    for name in obsolete:
        if Path(name).name!=name or not name.startswith('ReviewForge_') or not name.endswith('.pdf'):continue
        path=_safe(results/name,results)
        if path.exists():path.unlink()
    return manifest


def _derived(path):
    page=bool(re.fullmatch(r'page-\d+\.png',path.name)) and (path.parent.name=='preview' or path.parent.name.endswith('_preview'))
    return path.suffix.lower() in DERIVED_SUFFIXES or path.name.endswith('.synctex.gz') or page or bool(re.fullmatch(r'new-figure-page-\d+\.png',path.name))


def prune_build_artifacts(output,remove_page_images=True):
    root=Path(output).resolve();removed=0;size=0
    for path in list(root.rglob('*')):
        if path.is_file() and _derived(path) and (remove_page_images or path.suffix.lower()!='.png'):
            path=_safe(path,root);size+=path.stat().st_size;path.unlink();removed+=1
    return {'files_removed':removed,'bytes_reclaimed':size}


def cleanup_validation(workspace,execute=False):
    """Explicit historical validation allowlist only. Never touch active scientific state."""
    ws=Path(workspace).resolve();targets=[ws/name for name in sorted(VALIDATION_NAMES) if (ws/name).is_dir()]
    if (ws/'autonomous_runs').is_dir():
        for run in (ws/'autonomous_runs').iterdir():
            if run.is_dir() and not run.is_symlink():targets += [run/name for name in sorted(RUN_VALIDATION_NAMES) if (run/name).is_dir()]
    if not targets:return {'targets':[],'files':0,'bytes_before':0,'executed':False}
    # A historical-looking directory can still supply an asset to a retained
    # manuscript. Follow local input dependencies before treating it as disposable.
    queue=[]
    for folder,dirs,files in os.walk(ws,followlinks=False):
        safe_dirs=[]
        for name in dirs:
            directory=_safe(Path(folder)/name,ws)
            if not any(directory.is_relative_to(t.resolve()) for t in targets):safe_dirs.append(name)
        dirs[:]=safe_dirs
        queue.extend(Path(folder)/name for name in files if Path(name).suffix=='.tex')
    references=[];visited=set();ambiguous=[];total_text=0
    pattern=re.compile(r'\\(input|include|includegraphics|bibliography|usepackage|documentclass|RequirePackage(?:WithOptions)?|LoadClass(?:WithOptions)?)\*?(?:\s*\[[^]]*\])?\s*\{([^{}]+)\}')
    while queue:
        source=_safe(queue.pop(),ws)
        if source in visited or not source.is_file():continue
        visited.add(source)
        total_text+=source.stat().st_size
        if source.stat().st_size>2*1024*1024 or total_text>100*1024*1024 or len(visited)>2000:
            return {'targets':[],'files':0,'bytes_before':0,'executed':False,'reason':'Large retained manuscript requires explicit dependency audit'}
        from editorial_refinement import active_tex
        text=active_tex(source.read_text(encoding='utf-8'))
        # Be conservative with primitive/unbraced loads and custom wrappers:
        # mentioning a candidate directory in retained code is enough to keep it.
        references.extend(t.resolve() for t in targets if t.name in text)
        matched_starts={match.start() for match in pattern.finditer(text)}
        for loader in re.finditer(r'\\(?:input|include|includegraphics|bibliography|usepackage|documentclass|RequirePackage(?:WithOptions)?|LoadClass(?:WithOptions)?)(?![A-Za-z])',text):
            if loader.start() not in matched_starts:ambiguous.append(str(source))
        graphic_dirs=[]
        graphic_blocks=re.findall(r'\\graphicspath\s*\{((?:\{[^{}]*\})+)\}',text)
        if '\\graphicspath' in text and not graphic_blocks:ambiguous.append(str(source))
        for block in graphic_blocks:
            for name in re.findall(r'\{([^{}]*)\}',block):
                if '\\' in name:ambiguous.append(str(source));continue
                graphic_dirs.append((source.parent/name).resolve())
        references.extend(graphic_dirs)
        for command,names in pattern.findall(text):
            for name in names.split(','):
                if '\\' in name:
                    ambiguous.append(str(source))
                    continue
                candidate=(source.parent/name).resolve();references.append(candidate)
                if command=='includegraphics':references.extend((directory/name).resolve() for directory in graphic_dirs)
                if command in ('input','include','usepackage','documentclass','RequirePackage','RequirePackageWithOptions','LoadClass','LoadClassWithOptions'):
                    extension='.sty' if command in ('usepackage','RequirePackage','RequirePackageWithOptions') else '.cls' if command in ('documentclass','LoadClass','LoadClassWithOptions') else '.tex'
                    included=candidate if candidate.suffix else candidate.with_suffix(extension)
                    if included.is_relative_to(ws) and included.is_file():queue.append(included)
    if ambiguous:return {'targets':[],'files':0,'bytes_before':0,'executed':False,'reason':'Unresolved dynamic manuscript asset paths; no cleanup performed','ambiguous_sources':sorted(set(ambiguous))}
    skipped=[str(t) for t in targets if any(p.is_relative_to(t.resolve()) for p in references)]
    targets=[t for t in targets if str(t) not in skipped]
    snapshots={};total=0
    for target in targets:
        _safe(target,ws)
        for path in target.rglob('*'):
            _safe(path,ws)
            if path.is_file():
                data=path.stat();snapshots[path.relative_to(ws).as_posix()]={'sha256':_sha(path),'size':data.st_size,'mtime_ns':data.st_mtime_ns};total+=data.st_size
    result={'targets':[str(p) for p in targets],'files':len(snapshots),'bytes_before':total,'executed':False,'referenced_targets_preserved':skipped}
    if not execute or not targets:return result
    internal=ws/'成果/内部资料';internal.mkdir(parents=True,exist_ok=True)
    archive=internal/('historical-validation-'+_time_name(time.time())+'-'+uuid.uuid4().hex[:6]+'.zip')
    objects=set();manifest={}
    with _new_zip(archive) as z:
        for relative,info in snapshots.items():
            path=_safe(ws/relative,ws)
            if _derived(path):manifest[relative]={**info,'regenerable':True};continue
            obj='objects/'+info['sha256']+path.suffix
            manifest[relative]={**info,'object':obj}
            if obj not in objects:z.write(path,obj);objects.add(obj)
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('Historical archive CRC failed')
        for row in manifest.values():
            if row.get('object') and hashlib.sha256(z.read(row['object'])).hexdigest()!=row['sha256']:raise ValueError('Historical archive digest failed')
    current={p.relative_to(ws).as_posix() for target in targets for p in target.rglob('*') if p.is_file()}
    if current!=set(snapshots):raise RuntimeError('Validation files changed; no deletion performed')
    for relative,row in snapshots.items():
        path=_safe(ws/relative,ws)
        if path.stat().st_mtime_ns!=row['mtime_ns'] or _sha(path)!=row['sha256']:raise RuntimeError('Validation files changed; no deletion performed')
    for target in targets:shutil.rmtree(_safe(target,ws))
    result.update(executed=True,archive=str(archive),bytes_reclaimed=total-archive.stat().st_size)
    atomic_json(internal/'last_cleanup.json',result);return result
