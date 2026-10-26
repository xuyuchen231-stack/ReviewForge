# 科研技能取舍与本次落地（2026-10-27）

核查范围是项目 README 与适合综述写作的具体指令文件，不是逐行审计全部软件，也不把截图星数当质量证据。可核查的仓库、文件、树版本和许可证元数据见 [来源记录](skill-source-audit-2026-10-27.json)。以下是独立表述的方法取舍，没有整包安装、执行远端脚本或复制第三方实现。

## 第一组：截图提供链接的十个项目

| 项目 | 对 ReviewForge 有用的部分 | 处理与边界 |
|---|---|---|
| [claude-scholar](https://github.com/Galaxy-Dawn/claude-scholar) | 写句子之前建立论证；Related Work 按问题综合；来源记录与可提升为正文的主张分开 | 保留原有证据台账，增加段落逆向提纲检查；不接入它的安装钩子、Obsidian 或多套代理 |
| [codex-claude-academic-skills](https://github.com/zLanqing/codex-claude-academic-skills) | 每段推动章节目的，定量结论写清比较条件，中文与英文术语和公式保护 | 纳入段落贡献与可比性检查。截图用户名辨识有误，已核实为 zLanqing；Office 和光学计算模块不属于这次综述运行 |
| [chatgpt-prompts-for-academic-writing](https://github.com/ahmetbersoz/chatgpt-prompts-for-academic-writing) | 比较理论、反驳主张、把论点前置、检查重复表达等小任务 | 把这些问题合并进现有写作和审稿调用；不照搬“给一个主题就生成引用”的提示，也不采用固定字数扩写。未检测到许可证，不复制提示词文本 |
| [WritingAIPaper](https://github.com/hzwer/WritingAIPaper) | 围绕读者能获得的新认识组织文章，主张与证据对应，区分重要贡献和过程记录 | 综述的贡献体现为条件性综合判断，不强套实验论文的性能优胜故事；未检测到许可证，不复制手册文字 |
| [anti-defensive-writing-Skill](https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill) | 去掉自我辩解、过程汇报和空泛退让，主张强度与证据一致 | 采纳清晰、直接的论证。明确拒绝“永不说输”、隐藏相关不利结果或为叙事更换有利指标；综述必须保留相关反证 |
| [FAROS](https://github.com/OpenNSWM-Lab/FAROS) | 阶段对象契约、上下文交接、审查反馈和修订记录 | 与现有来源/候选/契约哈希、检查点机制相符，保持单一运行链；不移植完整前后端、实验执行或额外长期服务 |
| [AcademicForge](https://github.com/HughYau/AcademicForge) | 按任务选配技能；paper-narrative 从主张和图表审查论证顺序 | 采用“每个图表承担什么科学判断”的编辑原则，缺少数据的图不生成结果；不把聚合集合视为统一许可证或全部启用 |
| [academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer) | 改善精确表达，保留事实、数值、引文和有依据的不确定性，按作者样本校准风格 | 与内容修订合并，不另开昂贵润色循环；不承诺绕过检测，不照搬所有文体禁令 |
| [medical-research-skills](https://github.com/aipoch/medical-research-skills) | 方法导向阅读、矛盾结果解释、主张强度校准、证据缺口与验证设计衔接 | 采用评价思路，发酵工程按任务/工况/分割/尺度评估；不把临床证据等级、CONSORT 或临床统计模板直接套给工程论文。当前只核查目录与相关能力说明，未审计其数百个实现 |
| [claude-prism](https://github.com/delibae/claude-prism) | 本地文件、编译、版本快照和逐项修改比较；明确本地存储与远端推理的区别 | 保留本机快照和独立导出验证。正确仓库用户为 delibae；不替换编辑器，不把本地运行误说成内容不会发送给配置的模型服务 |

## 第二组：截图中的其他九个不同项目

| 项目 | 适合吸收的部分 | 处理与边界 |
|---|---|---|
| [academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | 主张与来源可追溯、材料状态区分、审稿意见与修订对应 | 保持模型审稿为暂定判断；不把多个代理一致意见当专家证明，不复制许可证未确认的指令 |
| [scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 主题综合、检索覆盖、报告与研究去重、来源实质支持核查 | 保留检索记录与研究身份，DOI 注册不等于支持论述；叙述综述不伪称系统综述，不增加强制图表生成 |
| [AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs) | 科学叙事聚焦、引用验证、符合目标读者的解释层级 | 采用明确主张和证据连接；LLM 训练、微调、GPU 编排与本任务无关，不引入其整套依赖 |
| [local-deep-research](https://github.com/LearningCircuit/local-deep-research) | 问题拆解、来源累积复用、根据缺口补充检索 | 复用已有证据卡、只对具体缺口补证；不额外安装搜索服务，不把网页事实问答基准当综述质量证明 |
| [academic-research-skills-codex](https://github.com/Imbad0202/academic-research-skills-codex) | 来源/主张/审稿状态区分、缓存、验证范围和适配边界 | 与 Claude 版一起去重，保留单一路由；不照搬其逐阶段确认要求来阻断用户已授权的夜间任务，也不引入额外付费模型 |
| [Research-Paper-Writing-Skills](https://github.com/Master-cai/Research-Paper-Writing-Skills) | 逆向提纲：段落主题句→章节主张、证据→段落主题句 | 已加入写作提示、审稿提示和深度契约；不强求每段固定句式 |
| [Supervisor-Skills](https://github.com/HKUSTDial/Supervisor-Skills) | 审稿前检查主张、论证链和支撑证据，按文章类型评价 | 合并到原五项审稿标准，给具体可修意见；不把某表编号、禁词次数或排版印象当科学有效性门槛 |
| [claude-scientific-writer](https://github.com/K-Dense-AI/claude-scientific-writer) | 先证据提纲再正文、源记录、数值和引用一致性、本地检查 | 与 scientific-agent-skills 重叠内容去重；证据标识留在台账，不泄漏到期刊正文；不采用所有文献必须有卷页的硬要求 |
| [nature-skills](https://github.com/Yuan1z0825/nature-skills) | 写作/润色/审稿职责区分，讨论中的条件判断、文献定位和具体研究缺口 | 写作与审稿中增加论证推进检查；不把 Nature 文体当正式期刊要求，不复制带独立许可的模板/资源 |

## 本机已安装技能的分工

- scientific-brainstorming：把模糊未来展望变为可区分解释的研究问题；不捏造未开展实验。
- nature-academic-search、paper-lookup、literature-review：补充具体缺口、记录检索范围并核对来源；元数据与正文支持分开。
- academic-research-suite：来源、主张、修订轨迹与缓存；与现有运行时去重。
- nature-statistics：比较样本单位、验证分割、基线和不确定性，不把不同数据集的误差直接排名。
- scientific-visualization、nature-figure：图表有明确证据来源和比较范围；不编造缺失数据。
- nature-writing：问题驱动的章节和段落；nature-polishing：最后改善表达，不抹去限制。
- nature-reviewer：给出具体证据和问题定位；nature-response：返修阶段才使用，不每轮生成回复信。
- nature-data：需要交付数据/代码可用性说明时才加载；nature-paper2ppt：需要汇报时才使用。

截图中不完整的“arxi/xpread/RPBS/nature apa ieee”没有足够身份信息，未把猜测当已研究项目，也没有据此安装新软件。

## 这次实际改变与验证范围

1. 数字制手工参考文献按正文首次有效引用排序；引用键不变，同组引用按首次遇到的键顺序，未引用条目稳定放在后面，重复键阻止交付。注释中的引用不参与排序，作者—年份样式保留原顺序。当前实现用于已经展开的单文件手工 bibliography，不宣称支持任意 TeX 宏执行或 BibTeX 工程。
2. 深度契约新增段落逆向提纲、反证、可比性和具体缺口检查；合并到原写作/审稿调用，不增加一轮润色或多代理评审。仍允许真正的过渡段短写，不以凑字数通过审稿。
3. 更换深度策略版本，使旧稿不会自动沿用旧标准下的通过结论；已保存来源卡继续复用。正在运行的旧进程不会热加载这些修改。
4. TokenHarbor 首次成功观察与周期起点分别记录，按账号顺序使用，免费周期耗尽后到期可重试；普通瞬时限流不等于永久用尽。1 号按用户后台剩余 2 天 2 小时再加 1 小时安全余量保存固定恢复时间，不随程序重启往后推。

软件测试只能验证上述行为，不能证明修订后的整篇文章已达到作者要求。实际论文需要完成新标准下的写作和审稿，缺乏来源时仍会留下可见问题。
