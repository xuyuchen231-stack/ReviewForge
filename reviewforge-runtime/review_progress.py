"""Read-only progress viewer for scientific revision and legacy editorial export."""
import json,time,sys
from pathlib import Path

def read_json(path,default=None):
 return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def major_progress(run):
 folder=run/'major_revision';log=folder/'running.log'
 roots=[p.parent for p in folder.glob('*/plan.json')]
 if not roots:return None
 lines=log.read_text(encoding='utf-8',errors='replace').splitlines() if log.exists() else []
 final=None
 for line in reversed(lines):
  try:
   value=json.loads(line)
   if isinstance(value,dict) and 'status' in value:final=value;break
  except ValueError:pass
 root=None
 if final:
  target=final.get('details') or (str(Path(final['candidate']).parent) if final.get('candidate') else None)
  if target:
   target=Path(target).resolve()
   if not target.is_relative_to(folder.resolve()):raise ValueError('Major revision outside active run')
   root=target
 if root is None:
  roots.sort(key=lambda p:(p/'progress.json').stat().st_mtime if (p/'progress.json').exists() else 0,reverse=True)
  root=roots[0]
 info=read_json(root/'progress.json',{})
 # A newer log activity supersedes an older terminal line (append-mode log support).
 if final and lines:
  terminal_line=next((i for i in range(len(lines)-1,-1,-1) if lines[i].lstrip().startswith('{') and '"status"' in lines[i]),-1)
  if any(line.startswith('[major-revision]') for line in lines[terminal_line+1:]):final=None
 phase=info.get('stage','prepared')
 state='运行中（按最近日志）' if lines else '已准备，尚未确认启动'
 reason=''
 if final:
  status=final.get('status')
  if status=='PAUSED':state='已暂停';reason=final.get('reason') or final.get('error_type','未知原因')
  elif status=='NEEDS_REVISION':state='等待修复科学审查问题'
  elif status=='FACTS_RECORDED':state='文献事实整理已结束，尚未重构正文'
  elif status=='PROVISIONAL_MODEL_PASS':
   exports=final.get('exports',{})
   state='流程已完成，稿件仍需审阅' if exports.get('english')=='PASS' and exports.get('chinese')=='PASS' else '正文模型审查通过，双语导出尚未完成'
   phase='export'
 if phase=='facts':completed,total=info.get('studies_processed',0),info.get('studies_total',0)
 else:completed,total=info.get('sections_completed',0),info.get('sections_total',0)
 out=root/'delivery/output';translation=read_json(out/'reports/translation_progress.json',[])
 if isinstance(translation,dict):translation=translation.get('units',[])
 activity=next((line for line in reversed(lines) if line.startswith('[major-revision]') or line.startswith('[canonical]')),'')
 return {'kind':'major_revision','state':state,'stage':phase,'completed':completed,'total':total,'study':(final or {}).get('study') or info.get('study',''),
         'passed':sum(u.get('status')=='PASS' for u in translation),'recorded':len(translation),'reason':reason,'activity':activity,
         'english':(out/'output/review_en.pdf').is_file(),'chinese':(out/'output/review_zh.pdf').is_file(),'output':str(out/'output')}

def progress(runtime):
 ws=Path(runtime)/'workspace'
 active=json.loads((ws/'autonomous_active.json').read_text(encoding='utf-8'))
 run=(ws/active['run_directory']).resolve()
 if not run.is_relative_to(ws.resolve()):raise ValueError('Active run outside workspace')
 major=major_progress(run)
 if major is not None:return major
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
    if d.get('kind')=='major_revision':
     phases={'facts':'文献事实整理与复核','reconstruction':'七章正文重构','prepared':'大修准备','export':'审查与双语导出'}
     label='文献' if d['stage']=='facts' else '章节'
     print('状态：'+d['state']+'\n当前阶段：'+phases.get(d['stage'],d['stage'])+'\n本阶段进度：'+str(d['completed'])+'/'+str(d['total'])+' '+label+'（不是全流程百分比）'+('\n当前文献：'+d['study'] if d['study'] else '')+'\n最近活动：'+d['activity']+'\n本轮英文PDF：'+('已生成' if d['english'] else '未生成')+'；本轮中文PDF：'+('已生成' if d['chinese'] else '未生成')+'\n'+('暂停原因：'+d['reason']+'\n' if d['reason'] else '')+'文件位置：'+d['output'],flush=True)
    else:
     print('状态：'+d['state']+'\n中文翻译：已通过 '+str(d['passed'])+' 个单元（总数尚未统计，不显示百分比）\n英文PDF：'+('已生成' if d['english'] else '未生成')+'；中文PDF：'+('已生成' if d['chinese'] else '未生成')+'\n'+('暂停原因：'+d['reason']+'\n' if d['reason'] else '')+'文件位置：'+d['output'],flush=True)
    last=d
  except (OSError,ValueError,KeyError) as exc:print('暂时无法读取进度：'+type(exc).__name__,flush=True)
  if '--watch' not in sys.argv:break
  time.sleep(10)

if __name__=='__main__':main()
