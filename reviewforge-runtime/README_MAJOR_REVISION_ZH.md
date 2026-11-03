# 科学大修流程

本流程处理事实矛盾、横向综合不足和章节重复；旧的 `editorial_refinement.py` 主要做清理与凝练，不能代替这轮大修。

```powershell
cd "D:\拓展和skill\ReviewForge-repo\reviewforge-runtime"
& "C:\Users\10078\AppData\Local\Programs\Python\Python310\python.exe" .\major_revision.py run --workspace .\workspace
```

默认读取当前运行对应的最新英文编辑稿，也可以用 `--source` 指定。仅支持已经审读的13章映射；不匹配时明确停止。原稿、已发表的中英PDF和有效缓存保留。

过程为：共享研究事实提取与复核 → 冲突协调 → 七章重构及独立审查 → 整篇逐句核查及同一研究的跨章比对 → 必要的有限修复 → 已有中英翻译、双栏排版与导出。没有九小时总截止；单次请求、格式重试和修复轮数仍有限制。证据不足时会保留待修问题，不无限循环。只使用本机已配置的TokenHarbor免费模型，不启用APIMaster。

提取前会检查Crossref记录的公开出版商PDF链接，核对PDF中的DOI并缓存取得的全文。不能取得的来源只记录访问状态，不写成“原文未报告”。这一步不绕过付费墙，也不能保证所有文献都能取得全文。

只想预检时用 `prepare`，它不调用模型；`facts` 只做共享研究记录。`run` 才执行大修与导出。重跑同一指令复用已经通过的源卡、章节和审查；最终审查指出问题的章节可继续修复。

事实卡会先保存模型原回复，再做格式校验。明确的状态别名及分类值误填会记录纠正；不能机械纠正的字段只补修该字段，保留其余有效内容。每项事实保留所需的互补原文片段，不按固定数量截断；所有片段仍须核对原始ID并接受独立复核。异常报告包含当前阶段、文献、校验原因和代码位置，避免只有泛化的 `ValueError`。

内部记录位于当前运行的 `study_registry.json`、`reports/study_evidence_matrix.json`、`reports/study_comparison_wide.csv`、`major_revision/<版本>/progress.json`、`status.json` 和 `delivery_report.json`。最终成功导出的中英PDF仍通过原来的保留机制发布到 `workspace/成果`。

`PREPARED_ONLY` 仅表示计划已准备；`PROVISIONAL_MODEL_PASS` 仅表示本次模型审查通过；`NEEDS_REVISION` 表示还有问题。它们都不代表专家认可或达到投稿标准。当前已核实的三项核心案例不等于全部参考文献都核实完成。

每节审稿还会逐段登记职责、主要意思、新增内容和去向。若某段应改写、合并或移至证据表/补充材料，该节会继续修订，不会仅凭高层检查通过就接受。后续章节会看到前文已确认的段落意思，以检查重复。移走请求的原文保存在内部 `paragraph_relocations.json`；它不是正式补充材料，不能据此在论文中声称已提供某个补充说明。

正文生成后会先保存 `pending_review` 检查点。若审稿请求断网，下次从原候选稿继续审稿，不重新生成整节。审稿漏填段落映射时只补审稿；真正内容问题才交回写作修复。

## 存储保留

本机 `workspace/retention_policy.json` 启用 `require_improvement_before_replacement` 后，生成时间更晚不会自动替换旧成稿。新中英PDF、翻译对应关系、引用与视觉检查及当前科学审查通过后，程序会对照完整新旧英文稿作一次质量比较并缓存结果。比较须确认必要科学内容保留、无新增重大问题、综合性、重复和可读性改善；不确定或未通过时，保留上一份完整PDF及可编辑源码包，新候选仍留在工作目录。模型比较不是专家认可或投稿承诺。

通过比较后，成果目录只保留最新中英PDF和源码包；旧PDF被阅读器占用时延后删除，不影响新版本发布。原始文献和续跑缓存保留。旧 `workspace_backup_时间戳` 工作区可用 `python storage_cleanup.py --execute` 去重归档到一个 `historical-workspaces.zip`，逐对象核对后再删除展开副本。默认只清理明确可再生成、未被TEX引用的排版文件和预览图，不删除论文配图或主文献。开启 `compact_historical_workspaces` 后，后续成功发布会继续处理历史备份和此前被占用的文件。


### Original scientific-figure contract

Use original local drawing code, not Vivid code, templates or assets (its license
requires separate permission for adaptation). Borrow only general workflow ideas:
choose the scientific question and route first, use distinct a-d panel roles,
semantic colors and explicitly authored connections. Conceptual diagrams must not
invent empirical data; numerical plots retain datum-level source IDs and compatible
units/protocols. Do not add an illustration merely to increase figure count.

Generated publication plans default to one-column inclusion. Render native 89 x
68 mm diagrams, wrap/shorten labels rather than shrink fonts, and retain PDF, editable
SVG and authored spec in the manifest. Do not emit PNG copies on every export.
`figure_contract.py` checks declared inclusion width, page-area fraction (<=1/8),
vector text size and page clipping. Mathematical scripts are distinguished by
relative size and baseline displacement; small ordinary labels must still fail.
Oversized legacy overviews require re-layout, not blind scaling.

These are standalone checks at declared width, not measurements of final manuscript
placement or proof of nonoverlap/semantic correctness. Manifests keep visual status
PENDING and final_manuscript_placement_verified=false. Final compiled manuscript
visual QA remains required; technical PASS never implies scientific approval.
