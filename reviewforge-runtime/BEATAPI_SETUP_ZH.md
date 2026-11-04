# BeatAPI 免费文本备用通道

官方资料核查日期：2026-11-05。文档：https://docs.beatapi.io/free-models

仅使用 `deepseek-v4.1-flash-free` 和 `glm-5.3-flash-free`。不去掉 `-free`，不切换付费模型。API：`https://api.beatapi.io/v1/chat/completions`。

PowerShell 执行下列命令，在本机隐藏输入一个现有完整密钥：

```powershell
& "C:\Users\10078\AppData\Local\Programs\Python\Python310\python.exe" "D:\拓展和skill\ReviewForge-repo\reviewforge-runtime\configure_beatapi.py" --restart
```

先进行一次极小 JSON 连通测试，成功后保存用户目录 `.reviewforge/providers.json` 并从缓存续跑；失败不修改配置、不重启。不会打印完整密钥。测试验证的是实际响应模型的连通与格式，不等同于科研质量验证，也不声称备用模型已实测。

TokenHarbor 仍是主通道，保留已配置的 Free.ai，APIMaster 禁用状态不变。BeatAPI 免费模型不套用 TokenHarbor 周额度。未充值账户官方限制每分钟1次成功请求，本地成功后间隔61秒；429遵守 Retry-After。

官方没有承诺免费ID的上下文、输出或每日额度。为避免无界请求，本地目前仅向 BeatAPI 发送合计不超过120000字符的系统和用户输入；超过则整条跳过，不截断正文/证据。这是本地保守阈值，不是平台公开上限。免费模型不可用时保留稿件缓存和科学审查门槛。
