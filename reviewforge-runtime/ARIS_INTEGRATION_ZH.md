# ARIS 方法整合记录

核对日期：2026-11-04，Pacific/Auckland。上游：
https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep

核对快照：`2927b40b2ea37774de53763338c5e8f91a7601e6`，MIT License。
审阅了24个相关 skill 的关键流程，以及4份共享合同；没有安装全部87个模块。

## 时间与相似性

GitHub API 的仓库创建时间为2026-03-10 07:31:45 UTC；最早提交为同日
07:31:41 UTC，标题为 Initial release: research-review and auto-review-loop skills。
独立 ARIS-Code CLI 的 v0.1.0 release 发布于2026-04-02 05:12:45 UTC。
创建/提交时间不能单独证明首次转为公开的时刻，不能把这几个日期混为一谈。

它与 ReviewForge 都采用自动执行、独立评审、反馈修订和持久化结果的循环。
这说明高层方法相近，不足以证明代码或实现相同。ARIS主要面向机器学习研究，
ReviewForge主要面向真实文献证据、综述综合、中文翻译和双栏交付。

## 已整合进 skill 的方法

| 上游模块 | ReviewForge采用或补强的部分 |
|---|---|
| research-pipeline | 分阶段完成标准、断点续跑、监控不能替代质量审查 |
| research-lit | 优先复用本地证据，多源去重，针对缺口逐级获取原文 |
| novelty-check | 与最接近的既有综述比较，明确真正新增的综合坐标 |
| research-review | 保留原始评审，独立评价具体论断，分离格式修复和科学判断 |
| auto-review-loop | 记录实际进展，停止无收益的重复调用，具体问题具体修复 |
| paper-plan | 论点—证据—章节—图表共同规划 |
| paper-write | 逐单元写作、统一符号、反向提纲、避免固定段落模板 |
| paper-writing | 写之前明确可检验的完成标准，区分写作、审查和交付 |
| auto-paper-improvement-loop | 保留原稿，有限编辑轮次，局部修改后独立复核 |
| result-to-claim | 区分已报告结果、可支持的推论、未验证提议 |
| paper-claim-audit | 数字、比较和范围主张回溯到真实来源 |
| citation-audit | 引文存在、字段正确、支持当前论点三个层次分开 |
| citation-crosscheck | 对有争议条目独立重建元数据，不以疑似错误字段作答案 |
| kill-argument | 全文阶段检验最强反对理由，避免局部全对、总论点夸大 |
| formula-derivation | 固定推导目标与假设，区分定义、恒等式和条件性命题 |
| paper-figure | 每张图有论证任务，真实数据与分析示意分开 |
| figure-spec | 从可编辑规格重新出图，检查真实尺寸和连接语义 |
| paper-compile | 编译、版面、来源和旧文件检测分别报告 |
| research-wiki | 复用现有研究登记簿和问题记录，防止模型总结反复成为“证据” |
| meta-optimize | 根据日志指出当前单一瓶颈，用固定样例评估改动 |
| meta-apply | 修改与评估分离，实际差异经复核后落地，不自改标准求通过 |
| experiment-plan | 仅借鉴“主张需要什么证据”的规划方法，不强制综述做新实验 |
| analyze-results | 在可比条件内解释数据，保留失败、负面和不确定结果 |
| system-profile | 区分接口等待、格式失败、科学返工和版面瓶颈 |

共享参考中的完成约束、证据溯源、审查记录和精炼写作方法也纳入指南。
完整逐项来源和文件摘要保存在 skill 的 `references/aris-source-map.json`。

## 具体落地点与实际边界

- `reviewforge/SKILL.md`：新增按需路由，修正旧的默认九小时截止、60条引文目标、
  以及可能重复要求已有授权的规则。保留单次调用、修复轮次和预算上限。
- `reviewforge/references/autonomous-research-adaptation.md`：计划、证据、审稿、
  精简、数学、图表、无进展处理和工作流改进的完整适配指南。
- `reviewforge/scripts/campaign_state.py`：无需API的离线建议工具；识别未关闭重大
  问题、旧版本审查、冷却等待和真正完成审查后的无进展状态。它不读取原文或PDF，
  不是科学验收引擎，也不会自动发送邮件或关机。
- `reviewforge/THIRD_PARTY_NOTICES.md`：上游署名和完整MIT通知。

当前固定运行脚本已具备断点、局部修订、有限恢复和科学门槛。此次没有把所有新
指南自动注入当前API提示词，也没有改变当前缓存键、清除限流或宣称完整接入ARIS。
新指南会指导后续agent工作；离线建议工具由agent按需使用，不是每次请求的依赖。

不照搬：昂贵模型/推理档位、GPU租用、强制实验数量、分数达标即完成、最低页数、
固定段落模板或“投稿就绪”承诺。已有TokenHarbor免费限制和当前邮件关机授权保留。
