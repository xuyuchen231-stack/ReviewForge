"""Verified compaction of named old workspaces and regenerable publication debris."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid
import zipfile
from result_retention import _safe,_sha,_new_zip
from reviewforge import atomic_json

BACKUP=re.compile(r'workspace[_-]backup[_-]\d{8}[_-]\d{6}$')


def verify_archive(path):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Historical archive CRC failure')
        manifest=json.loads(z.read('manifest.json'))
        for info in manifest['files'].values():
            digest=hashlib.sha256()
            with z.open(info['object']) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
            if digest.hexdigest()!=info['sha256']:raise ValueError('Historical archive content mismatch')
    return manifest


def compact_storage(runtime,execute=False,include_derived=True):
    root=Path(runtime).resolve();ws=_safe(root/'workspace',root)
    if not ws.is_dir():raise ValueError('Runtime workspace is required')
    backups=[];snapshots={};protected=[]
    # Refuse links/junctions before traversing explicitly named historical folders.
    texts=[]
    for p in ws.rglob('*.tex'):
        p=_safe(p,ws)
        if p.stat().st_size<3*1024*1024:texts.append(p.read_text(encoding='utf-8',errors='replace'))
    references='\n'.join(texts).replace('\\_','_').lower()
    loads=list(re.finditer(r'\\includegraphics\*?(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}',references))
    ambiguous_graphics=any('\\' in m.group(1) for m in loads) or len(loads)!=len(re.findall(r'\\includegraphics(?![a-zA-Z])',references))
    for old in root.iterdir():
        if not BACKUP.fullmatch(old.name) or not old.is_dir():continue
        old=_safe(old,root)
        if old.name.lower() in references:protected.append(str(old));continue
        files=[]
        for p in old.rglob('*'):
            p=_safe(p,root)
            if p.is_file():files.append(p)
        if any(p.name in ('.env','credentials.env','providers.json') for p in files):protected.append(str(old));continue
        backups.append(old)
        for p in files:snapshots[p.relative_to(root).as_posix()]={'sha256':_sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
    derived=[]
    runs=ws/'autonomous_runs'
    for p in runs.rglob('*') if include_derived and runs.exists() else []:
        p=_safe(p,ws)
        if not p.is_file():continue
        page=bool(re.fullmatch(r'(?:new-figure-)?page-\d+\.png',p.name)) and any(part=='preview' or part.endswith('_preview') for part in p.parts)
        generated=p.suffix.lower() in ('.xdv','.fls','.fdb_latexmk') or p.name.endswith('.synctex.gz') or page
        referenced=p.name.lower() in references
        if page:referenced=referenced or p.stem.lower() in references or ambiguous_graphics or any(part.lower() in references for part in p.parts if part=='preview' or part.endswith('_preview'))
        if generated and not referenced:derived.append((p,p.stat().st_size,p.stat().st_mtime_ns))
    result={'executed':False,'backup_folders':[str(p) for p in backups],'backup_files':len(snapshots),'backup_bytes':sum(v['size'] for v in snapshots.values()),'derived_files':len(derived),'derived_bytes':sum(n for _,n,_ in derived),'protected_folders':protected}
    if not execute:return result
    reclaimed=0;removed=0;deferred=[]
    if snapshots:
        internal=ws/'成果/内部资料';internal.mkdir(parents=True,exist_ok=True)
        archive=_safe(internal/'historical-workspaces.zip',ws);temporary=internal/(uuid.uuid4().hex+'.tmp')
        previous=verify_archive(archive) if archive.exists() else {'files':{}}
        old_size=archive.stat().st_size if archive.exists() else 0
        batch=hashlib.sha256(json.dumps(snapshots,sort_keys=True).encode()).hexdigest()[:16]
        manifest={'files':dict(previous['files']),'scope':'Exact original bytes from retired workspace folders. Active manuscript, evidence and checkpoints were excluded.'}
        objects=set()
        with _new_zip(temporary) as z:
            if archive.exists():
                with zipfile.ZipFile(archive) as old:
                    for name in old.namelist():
                        if name=='manifest.json':continue
                        with old.open(name) as source,z.open(name,'w') as target:shutil.copyfileobj(source,target)
                        objects.add(name)
            for relative,info in snapshots.items():
                source=_safe(root/relative,root);obj='objects/'+info['sha256']
                if obj not in objects:z.write(source,obj);objects.add(obj)
                manifest['files'][batch+'/'+relative]={**info,'original_path':relative,'object':obj}
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        verify_archive(temporary)
        # Recheck every source and membership before replacing the archive or removing anything.
        current={p.relative_to(root).as_posix() for old in backups for p in old.rglob('*') if _safe(p,root).is_file()}
        if current!=set(snapshots):raise ValueError('Historical workspace changed during compaction')
        for relative,info in snapshots.items():
            p=_safe(root/relative,root)
            if p.stat().st_mtime_ns!=info['mtime_ns'] or _sha(p)!=info['sha256']:raise ValueError('Historical file changed during compaction')
        temporary.replace(archive);result['archive']=str(archive)
        for relative,info in snapshots.items():
            source=_safe(root/relative,root)
            try:source.unlink();reclaimed+=info['size'];removed+=1
            except PermissionError:deferred.append(str(source))
        for old in backups:
            old=_safe(old,root)
            for directory in sorted((p for p in old.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
                directory=_safe(directory,root)
                try:directory.rmdir()
                except OSError:pass
            try:old.rmdir()
            except OSError:deferred.append(str(old))
        reclaimed-=archive.stat().st_size-old_size
    for p,size,mtime in derived:
        p=_safe(p,ws)
        if not p.exists() or p.stat().st_size!=size or p.stat().st_mtime_ns!=mtime:continue
        try:p.unlink();reclaimed+=size;removed+=1
        except PermissionError:deferred.append(str(p))
    result.update(executed=True,bytes_reclaimed=reclaimed,files_removed=removed,deferred=deferred)
    log=ws/'reports/storage_cleanup.json';log.parent.mkdir(exist_ok=True);atomic_json(log,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    print(json.dumps(compact_storage(Path(__file__).parent,args.execute),ensure_ascii=True))
