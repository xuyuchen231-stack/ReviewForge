"""Bounded public publisher-PDF acquisition; never convert access failures into findings."""
import datetime as dt
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
from reviewforge import atomic_json

POLICY='public-primary-pdf-v1'
MAX_BYTES=15*1024*1024


def download(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Public HTTPS source required')
    host=parsed.hostname.lower()
    if host in ('localhost','localhost.localdomain') or host.endswith(('.local','.internal')):raise ValueError('Local source URL rejected')
    try:
        if not ipaddress.ip_address(host).is_global:raise ValueError('Non-public source URL rejected')
    except ValueError as exc:
        if 'rejected' in str(exc):raise
    request=urllib.request.Request(url,headers={'User-Agent':'ReviewForge/1.0 (primary literature acquisition)','Accept':'application/pdf, application/json'})
    with urllib.request.urlopen(request,timeout=25) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('Primary source exceeds acquisition byte limit')
    return data


def acquire(workspace,entry,fetch=download,now=None):
    ws=Path(workspace).resolve();folder=(ws/entry.get('source_directory','__missing__')).resolve()
    if not folder.is_relative_to(ws) or not folder.is_dir():return {'status':'NO_SOURCE_DIRECTORY'}
    full=folder/'fulltext';meta=full/'source.json'
    if (full/'source.pdf').exists() and (full/'source.txt').exists() and meta.exists():
        saved=json.loads(meta.read_text(encoding='utf-8'))
        if saved.get('kind')=='pdf' and saved.get('sha256')==hashlib.sha256((full/'source.pdf').read_bytes()).hexdigest():return {'status':'CACHED_FULL_TEXT'}
    if (folder/'source.pdf').exists() and (folder/'source.txt').exists():return {'status':'CACHED_FULL_TEXT'}
    doi=str(entry.get('doi','')).strip()
    if not doi:doi=str(entry.get('source_id','')).removeprefix('https://doi.org/')
    if not re.fullmatch(r'10\.\d{4,9}/\S+',doi,re.I):return {'status':'NO_VERIFIED_DOI'}
    now=now or dt.datetime.now(dt.timezone.utc);stamp=now.isoformat();log=folder/'fulltext_acquisition.json'
    if log.exists():
        previous=json.loads(log.read_text(encoding='utf-8'))
        try:recent=(now-dt.datetime.fromisoformat(previous['checked_at'])).total_seconds()<7*86400
        except (ValueError,KeyError,TypeError):recent=False
        if recent and previous.get('policy')==POLICY and previous.get('doi')==doi and previous.get('status')=='NO_PUBLIC_FULL_TEXT':return previous
    result={'policy':POLICY,'doi':doi,'checked_at':stamp,'status':'NO_PUBLIC_FULL_TEXT','attempts':[],'interpretation':'Access bookkeeping only; not evidence that the paper omitted a method or result.'}
    try:
        crossref=json.loads(fetch('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')))['message']
        if str(crossref.get('DOI','')).lower()!=doi.lower():raise ValueError('Crossref source identity mismatch')
        urls=[r['URL'] for r in crossref.get('link',[]) if r.get('URL') and (r.get('content-type')=='application/pdf' or '.pdf' in r['URL'].lower())]
        for url in list(dict.fromkeys(urls))[:3]:
            try:
                blob=fetch(url)
                if not blob.startswith(b'%PDF'):raise ValueError('Publisher returned no PDF')
                import fitz
                with fitz.open(stream=blob,filetype='pdf') as pdf:pages=[p.get_text() for p in pdf]
                text='\n\n'.join(pages)
                if len(text)<1000 or doi.lower() not in re.sub(r'\s+','',text).lower():raise ValueError('PDF identity/text could not be verified')
                full.mkdir(exist_ok=True)
                # Preserve previously inspected publisher excerpts, if present.
                if (full/'source.txt').exists():
                    old=(full/'source.txt').read_bytes();archive=full/('excerpt_'+hashlib.sha256(old).hexdigest()+'.txt')
                    if not archive.exists():archive.write_bytes(old)
                (full/'source.pdf').write_bytes(blob);(full/'source.txt').write_bytes(text.encode('utf-8'))
                atomic_json(full/'pages.json',pages)
                atomic_json(meta,{'doi':doi,'url':url,'kind':'pdf','retrieved_at':stamp,'sha256':hashlib.sha256(blob).hexdigest(),'retrieval_method':'public_crossref_publisher_link'})
                result.update(status='ACQUIRED_PUBLIC_FULL_TEXT',pages=len(pages),source_pdf_sha256=hashlib.sha256(blob).hexdigest());break
            except Exception as exc:result['attempts'].append({'error_type':type(exc).__name__})
    except Exception as exc:result['attempts'].append({'error_type':type(exc).__name__})
    atomic_json(log,result);return result
