# TokenHarbor 刷新时间优先

新增账号仍使用 `add_tokenharbor_account.py --suffix <末4位> --restart`。保存一个此前未配置的密钥后，仅对它发送一次小型免费请求（最多32输出token），记录首次成功时间；重复添加已有密钥不会再发激活请求。

没有找到独立的公开周期查询接口。成功响应未必包含刷新时间，因此首次成功时间加7天仅标为估算，不冒充服务端确认。若平台额度错误明确返回“next rolling 7-day period starts on … UTC”或“comes back on … UTC”，程序解析并保存服务端日期，保留1小时安全余量。普通 Retry-After 是临时冷却，不是周期刷新。

每次真实调用按下一次刷新时间从早到晚选择**可用**账号；耗尽/冷却账号跳过，时间未知的排最后，相同时间保持原顺序。已确认周期不因较晚发起下一次请求而向后漂移。周期规则只适用 TokenHarbor，Free.ai 和 BeatAPI 不受影响，仍不启用付费回退。

官方周期说明：https://tokenharbor.ai/faq
