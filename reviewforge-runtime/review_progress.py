"""Read-only progress viewer for scientific revision and legacy editorial export."""
import json,time,sys
from datetime import datetime,timezone
from pathlib import Path

def read_json(path,default=None):
 return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def local_stamp(epoch):
 try:
  from zoneinfo import ZoneInfo
  zone=ZoneInfo('Pacific/Auckland')
 except Exception:zone=timezone.utc
 return datetime.fromtimestamp(epoch,zone).strftime('%Y-%m-%d %H:%M:%S %Z')

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
  if status=='PAUSED':
   state='已暂停';reason=final.get('reason') or final.get('error_type','未知原因')
   category=final.get('request_failure',{}).get('category')
   if category=='scientific_revision_required':reason='科学审查仍需修订；已通过内容保留。'+str(final.get('reason',''))
   if category in ('rate_limit','weekly_allowance_exhausted'):
    reason='接口限流，等待账号冷却' if category=='rate_limit' else '账号周额度耗尽，等待刷新'
    deadline=read_json(root/'monitor_wait.json',{}).get('retry_not_before_epoch',0)
    if deadline>time.time():
     try:
      from zoneinfo import ZoneInfo
      zone=ZoneInfo('Pacific/Auckland')
     except Exception:
      zone=timezone.utc
     stamp=datetime.fromtimestamp(deadline,zone)
     reason+='；最早重试时间 '+stamp.strftime('%Y-%m-%d %H:%M %Z')+' (Pacific/Auckland)' if str(zone)!='UTC' else '；最早重试时间 '+stamp.strftime('%Y-%m-%d %H:%M UTC')+' (Pacific/Auckland 时区数据不可用)'
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
 unit_files=list((root/'argument_units').glob('*/progress.json'))
 unit_progress=read_json(max(unit_files,key=lambda p:p.stat().st_mtime),{}) if unit_files else {}
 log_updated=local_stamp(log.stat().st_mtime) if log.exists() else ''
 from request_accounting import usage_summary
 return {'kind':'major_revision','state':state,'stage':phase,'completed':completed,'total':total,'study':(final or {}).get('study') or info.get('study',''),
         'argument_units':unit_progress,'log_updated_at':log_updated,'usage':usage_summary(root/'model_requests/requests.jsonl'),
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
     if d.get('log_updated_at'):print('日志更新时间：'+d['log_updated_at'],flush=True)
     units=d.get('argument_units',{})
     if units:print('最近章节单元记录：'+str(units.get('completed',0))+'/'+str(units.get('total',0))+'；待修订：'+(', '.join(units.get('unresolved_units',[])) or '按当前审查结果继续'),flush=True)
     usage=d.get('usage',{})
     if usage:print('新日志已记录Token：输入 '+str(usage.get('prompt_tokens',0))+'；输出 '+str(usage.get('completion_tokens',0))+'；缓存复用 '+str(usage.get('cache_hits',0))+' 次；用量未确认请求 '+str(usage.get('unknown_charge_attempts',0))+' 次（不含历史未记录用量）',flush=True)
    else:
     print('状态：'+d['state']+'\n中文翻译：已通过 '+str(d['passed'])+' 个单元（总数尚未统计，不显示百分比）\n英文PDF：'+('已生成' if d['english'] else '未生成')+'；中文PDF：'+('已生成' if d['chinese'] else '未生成')+'\n'+('暂停原因：'+d['reason']+'\n' if d['reason'] else '')+'文件位置：'+d['output'],flush=True)
    last=d
  except (OSError,ValueError,KeyError) as exc:print('暂时无法读取进度：'+type(exc).__name__,flush=True)
  if '--watch' not in sys.argv:break
  time.sleep(10)

if __name__=='__main__':main()
