# 全文清理、精炼与可复现实验

本流程处理已组装的论文，不重跑文献抽取，也不改变科学审稿通过数量。

先生成独立审计记录与文献证据表（不调用模型）：

```powershell
python .\editorial_refinement.py audit --run .\workspace\autonomous_runs\你的运行目录
```

运行两阶段精炼，最多使用指定小时数，沿用本地已配置的写作与审稿API：

```powershell
python .\editorial_refinement.py refine --run .\workspace\autonomous_runs\你的运行目录 --hours 2
```

也可以自动定位当前任务，避免手动填写运行目录：

```powershell
python .\editorial_refinement.py refine --workspace .\workspace --hours 2
```

第一阶段完整清理重复的防御性表达，保存 `full_cleaned.tex`；第二阶段从该版本精炼，保存
`refined.tex`。两份文件位于 `editorial/<版本指纹>/`；以 `editorial/latest.json` 中的完整
版本路径为准。`current.json` 指向本次任务，`raw/` 是内部原始快照。若第二阶段中断，已
完成的完整清理版仍保存在自己的版本目录中，不会与另一个来源的精炼版混用。

相同来源、提示词和片段的已审稿结果会复用。调用失败或内容保护检查不通过时暂停，
再次运行同一命令续跑。检查包含原始数值、数学表达、图表、引用和交叉引用；模型再核对
前后论证、必要不确定性和反面证据。模型审核仍不是专家核实。不得把尚未完成的片段
称为完成稿。25–30页是精炼目标，需要编译后确认，程序不会缩小字号硬凑页数。

如需九小时流程在交付前自动尝试此步骤，在本地 `.env` 中设置：

```text
RF_MANUSCRIPT_REFINEMENT=1
```

它使用剩余交付时间并保留编译预算；预算不足则保存断点。未设置时，原有交付不增加
精炼模型调用。单独命令只生成版本候选，不覆盖原稿或原PDF，需经过正常编译检查后导出。

`literature_evidence_ledger.csv` 保存各单位的文献、比较维度、可达性、记录状态和定位。
“不可访问”不能改写成“作者未做”。符号检查提供角色规范与待核对段落，不盲目替换
`x/X`、`e/u`。现有公式标签的前向引用不等于公式缺失。

额外图使用 `editorial_diagrams.proposed_diagrams` 生成方案，经 `publication_figures` 输出
矢量图，区分学习接口、测试锁定流程和M0–M4修正阶梯；都是概念综合图。

独立的H1–H4合成示例可以实际运行，不消耗API：

```powershell
python -m pip install -r .\requirements-research.txt
python .\synthetic_benchmark.py --output .\workspace\synthetic_benchmark
```

它固定训练、验证、测试批次，训练拟合、验证选参、锁定后测试，输出原始采样数据、预测、
误差CSV、曲线、参数和程序副本。测试数据改变不会影响模型拟合或选择。参数为演示值，
不是特定菌株实测结果，也不是PenSim复现。缺少独立参考测定时H1/H2可能混淆。此工具不
自动往论文写入新实验结论；真正添加实验章节还需审核协议、适用范围和实际结果。
