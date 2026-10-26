"""Interactive local APIMaster backup setup. Never prints or puts keys in arguments."""
import getpass,json,os,urllib.request,urllib.error
from pathlib import Path
from reviewforge import atomic_json

BASE='https://apimaster.ai/v1'

def fetch_models(key):
    request=urllib.request.Request(BASE+'/models',headers={'Authorization':'Bearer '+key})
    with urllib.request.urlopen(request,timeout=30) as response:data=json.load(response)
    models=sorted({row['id'] for row in data.get('data',[]) if isinstance(row,dict) and isinstance(row.get('id'),str) and row['id']})
    if not models:raise ValueError('No accessible model IDs returned; no configuration saved.')
    return models

def choose(models,prompt,default=None):
    while True:
        value=input(prompt).strip()
        if not value and default:return default
        if value.isdigit() and 1<=int(value)<=len(models):return models[int(value)-1]
        if value in models:return value
        print('请输入列表中的编号或完整模型 ID。')

def save_profile(path,key,writer,reviewer):
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'providers':[]}
    if not isinstance(data,dict) or not isinstance(data.get('providers'),list):raise ValueError('Existing provider configuration is invalid; original preserved.')
    profile={'name':'apimaster','enabled':True,'RF_BASE_URL':BASE,'RF_API_KEY':key,'RF_WRITER_MODEL':writer,'RF_REVIEWER_MODEL':reviewer,'RF_FALLBACK_MODEL':reviewer}
    data['providers']=[row for row in data['providers'] if row.get('name')!='apimaster']+[profile]
    atomic_json(path,data)
    if os.name!='nt':path.chmod(0o600)

def main():
    print('添加 APIMaster 备用服务，保留原有账号。')
    print('模型调用使用你在 APIMaster 的额度和价格；本次只读取模型列表，不发送生成请求。')
    key=getpass.getpass('粘贴 APIMaster API Key（输入不显示）：').strip()
    if not key or any(ch.isspace() for ch in key):raise ValueError('Invalid empty/whitespace key; no configuration saved.')
    models=fetch_models(key)
    for index,model in enumerate(models,1):print(str(index)+'. '+model)
    print('请选择支持 chat/completions 的文本模型；不要选择图片、语音或 embedding 模型。')
    writer=choose(models,'写作模型编号或 ID：')
    reviewer=choose(models,'审稿模型编号或 ID（直接回车使用同一模型）：',writer)
    path=Path(os.environ.get('RF_PROVIDER_FILE',str(Path.home()/'.reviewforge/providers.json')))
    save_profile(path,key,writer,reviewer)
    print('APIMaster 备用配置已保存在本机，密钥不显示。下次启动 ReviewForge 时生效。')
    print('配置位置：'+str(path))

if __name__=='__main__':
    try:main()
    except (KeyboardInterrupt,EOFError):print('\n已取消，未更新配置。')
    except urllib.error.HTTPError as exc:print('读取模型列表失败：HTTP '+str(exc.code)+'。原配置保留。');raise SystemExit(1)
    except Exception as exc:print('配置失败（'+type(exc).__name__+'）。原配置保留。');raise SystemExit(1)
