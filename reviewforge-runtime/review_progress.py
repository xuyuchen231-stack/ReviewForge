"""Read-only progress viewer for the active local editorial export."""
import json,time,sys
from pathlib import Path

def progress(runtime):
 ws=Path(runtime)/'workspace'
 active=json.loads((ws/'autonomous_active.json').read_text(encoding='utf-8'))
 run=(ws/active['run_directory']).resolve()
 if not run.is_relative_to(ws.resolve()):raise ValueError('Active run outside workspace')
 current=json.loads((run/'editorial/current.json').read_text(encoding='utf-8'))
 root=Path(current['version_directory'])
 if not root.resolve().is_relative_to(run):raise ValueError('Version outside active run')
 out=root/'short/output'
 f=out/'reports/translation_progress.json'
 units=json.loads(f.read_text(encoding='utf-8')) if f.exists() else []
 log=run/'editorial/resume_delivery.log'
 lines=log.read_text(encoding='utf-8',errors='replace').splitlines() if log.exists() else []
 final=None
 for line in reversed(lines):
  try:
   value=json.loads(line)
   if isinstance(value,dict) and 'translation' in value:final=value;break
  except ValueError:pass
 state='未确认运行状态'
 if final:state='已暂停' if final.get('translation')!='generated' else '导出流程已结束，请查看PDF检查结果'
 elif lines:state='任务已启动，尚未记录结束状态'
 passed=sum(x.get('status')=='PASS' for x in units)
 reason=final.get('translation_error','') if final else ''
 return {'state':state,'passed':passed,'recorded':len(units),'reason':reason,'english':(out/'output/review_en.pdf').is_file(),'chinese':(out/'output/review_zh.pdf').is_file(),'output':str(out/'output')}

def main():
 last=None
 while True:
  try:
   d=progress(Path(__file__).resolve().parent)
   if d!=last:
    print('状态：'+d['state']+'\n中文翻译：已通过 '+str(d['passed'])+' 个单元（总数尚未统计，不显示百分比）\n英文PDF：'+('已生成' if d['english'] else '未生成')+'；中文PDF：'+('已生成' if d['chinese'] else '未生成')+'\n'+('暂停原因：'+d['reason']+'\n' if d['reason'] else '')+'文件位置：'+d['output'],flush=True)
    last=d
  except (OSError,ValueError,KeyError) as exc:print('暂时无法读取进度：'+type(exc).__name__,flush=True)
  if '--watch' not in sys.argv:break
  time.sleep(10)

if __name__=='__main__':main()
