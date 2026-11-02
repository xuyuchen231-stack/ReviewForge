"""Set a TokenHarbor account first using a masked local prompt, never chat input."""
import argparse
import base64
import getpass
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from account_cycles import WeeklyAccounts,WEEK,is_tokenharbor_free
from reviewforge import load_env,CompatibleAPI


def apply_priority(path,key,keys,base,ledger,hours,now=None):
    if not key or any(c in key for c in ',\r\n\t \"\'') or not math.isfinite(hours) or hours<=0:raise ValueError('Invalid key or refresh interval; configuration unchanged')
    now=time.time() if now is None else now;reset=now+hours*3600
    order=[key]+[k for k in keys if k!=key];path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    original=path.read_text(encoding='utf-8-sig') if path.exists() else ''
    lines=original.splitlines();updated=[];found=False
    for line in lines:
        if line.strip().startswith('RF_API_KEYS='):
            if not found:updated.append('RF_API_KEYS='+','.join(order));found=True
        else:updated.append(line)
    if not found:updated.append('RF_API_KEYS='+','.join(order))
    if original:path.with_name(path.name+'.before_priority.bak').write_text(original,encoding='utf-8')
    fd,name=tempfile.mkstemp(prefix='.rf-priority-',suffix='.tmp',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:stream.write('\n'.join(updated)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if Path(name).exists():Path(name).unlink()
    def change(row):
        blocked=row.get('exhausted_until',0)>now
        row.update(window_started_at=reset-WEEK,user_reported_reset_at=reset,reset_safety_seconds=3600,
                   start_basis='user_reported_remaining_hours; not proven first-ever use',server_window_confirmed=False,priority_set_at=now)
        if blocked:row['exhausted_until']=reset+3600
    ledger._update(base,key,change)
    return order


def restart_runner(runtime):
    if os.name!='nt':raise ValueError('Automatic restart requires Windows')
    runtime=Path(runtime).resolve();ws=runtime/'workspace';program=runtime/'major_revision.py'
    literal=lambda s:"'"+str(s).replace("'","''")+"'"
    script="$targets=Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains("+literal(program)+") -and $_.CommandLine.Contains("+literal(ws)+") }; $targets | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop }"
    encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    subprocess.run(['powershell.exe','-NoProfile','-EncodedCommand',encoded],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    import json
    active=json.loads((ws/'autonomous_active.json').read_text(encoding='utf-8'));run=(ws/active['run_directory']).resolve()
    if not run.is_relative_to(ws):raise ValueError('Active run outside workspace')
    folder=run/'major_revision';folder.mkdir(exist_ok=True)
    with (folder/'running.log').open('w',encoding='utf-8') as stdout,(folder/'running_error.log').open('w',encoding='utf-8') as stderr:
        process=subprocess.Popen([sys.executable,'-u',str(program),'run','--workspace',str(ws)],cwd=str(runtime),stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
    return process.pid


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--suffix',required=True);parser.add_argument('--reset-hours',type=float,required=True);parser.add_argument('--restart',action='store_true');args=parser.parse_args()
    runtime=Path(__file__).resolve().parent;load_env(runtime/'.env');api=CompatibleAPI()
    if not all(is_tokenharbor_free(api.base,m) for m in (api.model,api.reviewer_model,api.fallback_model)):raise SystemExit('Only the TokenHarbor free route is supported; nothing changed.')
    existing=[k for k in api.keys if k.endswith(args.suffix)]
    key=existing[0] if len(existing)==1 else getpass.getpass('Paste the full TokenHarbor key locally (hidden input): ').strip()
    if len(key)<16 or not key.endswith(args.suffix):raise SystemExit('A complete key with the requested suffix is required; nothing changed.')
    paths=[runtime/'.env',Path.home()/'.reviewforge/credentials.env']
    path=next((p for p in paths if p.exists() and any(line.strip().startswith('RF_API_KEYS=') for line in p.read_text(encoding='utf-8-sig').splitlines())),paths[0])
    order=apply_priority(path,key,api.keys,api.base,WeeklyAccounts(),args.reset_hours)
    os.environ['RF_API_KEYS']=','.join(order)
    print('Priority saved for account ending '+args.suffix+'. Free-only routing and quota failover retained.')
    if args.restart:print('Resumed from saved caches; process ID '+str(restart_runner(runtime))+'.')


if __name__=='__main__':main()
