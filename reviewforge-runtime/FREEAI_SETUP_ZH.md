# Free.ai 接入

原配置没有 Free.ai。新增通道使用官方 `https://api.free.ai/v1/chat/`，仅请求自托管模型 `qwen7b`；不调用 GPT、Claude 或其他外部付费模型。TokenHarbor 保持主通道，APIMaster 的禁用状态不变。

在 PowerShell 运行：

```powershell
& "C:\Users\10078\AppData\Local\Programs\Python\Python310\python.exe" "D:\拓展和skill\ReviewForge-repo\reviewforge-runtime\configure_freeai.py" --restart
```

按提示在本机隐藏输入两个**现有**完整密钥，不要发到聊天。工具对每个账号发出一次极小 JSON 请求；两者都返回正确结果后才保存到用户目录 `.reviewforge/providers.json`，并从缓存续跑。任何一个失败均不修改配置、不重启。测试日志只记录末4位、模型、用量和结果，保存在 `workspace/reports/freeai_connection_test.json`。

网页历史密钥只显示前缀，不能从遮蔽文本还原完整密钥。若没有保存完整密钥，需要用户在平台自行取得可用密钥。

为避免当前大请求立即耗尽每日额度或超出未知上下文限制，Free.ai 暂只接收系统和用户输入合计不超过60000字符的请求；超限整条跳过，不裁剪证据。此阈值是本地保守预算，不是平台公布的上下文上限。Free.ai 不套用 TokenHarbor 的七天周期。402/429 按服务端 Retry-After 冷却，缺失时暂等一小时。

请求成功仅证明连通和 JSON 格式可用，不证明科研写作质量与原模型等同。原有科学审查和完成门槛保留。官方文档：https://free.ai/api/
