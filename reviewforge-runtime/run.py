import argparse
from pathlib import Path
from reviewforge import load_env, run

if __name__ == '__main__':
    p=argparse.ArgumentParser(description='ReviewForge local unattended writer')
    p.add_argument('--hours',type=float,default=9)
    p.add_argument('--minutes',type=float)
    p.add_argument('--resume',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--workspace',default='workspace')
    args=p.parse_args()
    load_env(Path(__file__).resolve().parent/'.env')
    result=run(args.workspace,hours=args.hours,minutes=args.minutes,resume=args.resume,dry_run=args.dry_run)
    print('Completed; best draft:',result['best_file'],'iterations:',result['iteration'])
