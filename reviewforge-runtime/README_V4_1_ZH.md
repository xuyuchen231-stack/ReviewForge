# ReviewForge v4.1：证据传递与交付验收

本次保留 v4 的入口、工作区和模型配置。更新代码前结束旧进程，随后使用原有
`resume_review_v4.bat` 或 `python reviewforge_v4.py resume`。不覆盖作者原稿，不上传工作区。

## 已修改

1. 中文按有长度上限的文本单元翻译，保护 LaTeX、数字、公式和引用标识。
   标题、摘要、正文、图注和表格文字参与翻译；失败会重试并尝试更小分块。
   成功单元保存在 `reports/translation_units/`，续跑复用相同输入和配置的结果。
   任一单元失败则 `translation_gate.json` 为 FAILED，不生成冒充完整译文的新文件。
   不再把标题强制替换为发酵主题，也不强制双栏。可在 `translation_glossary.json`
   提供术语映射，例如 `{"hybrid model":"混合模型"}`。
2. 写作、独立审稿和质量改进均接收原文证据包。支持 `evidence_ledger.json` 的
   `{"entries":[...]}` 和旧列表形式。证据变化后重新审阅缓存块。
3. 编译报告分别记录 `status`、`layout_status`、`visual_status`。
   只检查最终 LaTeX 轮次的未解析引用、越界和缺字，避免首轮引用警告误报。
   只有生成 PDF 才有编译 PASS；这不等于版面合格。
4. 安装可选的 `PyMuPDF` 后，成功编译会生成所有页面的 PNG 和 manifest：
   `output/review_en_preview/`、`output/review_zh_preview/`。
   未安装时明确显示预览不可用，不能自动通过视觉验收。
5. `audit` 和 `quality_pipeline.py prepare` 生成问题覆盖报告与逐图设计检查单。
   模型改稿必须减少已记录问题，不能仅凭评分上涨接受。

## 原文证据格式

```json
{"entries":[{
  "claim":"需要支撑的具体论断",
  "citekey":"Smith2024",
  "source_id":"DOI 或稳定来源标识",
  "locator":"第 4 页，表 2",
  "excerpt":"实际读取到的原文摘录",
  "limitations":"适用工况与未验证条件",
  "verification_status":"source_located",
  "section":"\\section{Methods}"
}]}
```

`section` 可选，用于向该节提供尚未引用的候选证据。既有列表字段
`supported_claim`、`doi`、`evidence_location`、`quote` 也可读取。
没有摘录时可使用位于工作区内的 UTF-8 `source_file`（不超过 100 KB）。
传入摘录不表示程序已验证语义蕴含，需检查原文是否实际支持论断。

## 问题覆盖矩阵

在工作区创建 `coverage_matrix.json`：

```json
{"questions":[{
  "id":"q1",
  "question":"模型在未见过的操作条件下是否有效？",
  "supporting_keys":["Smith2024"],
  "counterevidence_keys":[],
  "counterevidence_search":"数据库、日期、检索式和筛选范围",
  "no_counterevidence_reason":"在上述范围内未找到符合条件的反例",
  "unresolved":"尚缺独立外部验证"
}]}
```

不能把未找到反例写成不存在反例。报告显示未覆盖问题，数量门槛仍由 `--minimum`
控制。报告不会自动补文献、认证全文，也不会替你重画论文图。

## 视觉验收与续跑

检查 preview 目录全部页面，修复越界、图表不可读等问题后，创建
`reports/review_en_visual_review.json`（中文同理）：

```json
{
  "pdf_sha256":"从对应 preview/manifest.json 复制",
  "reviewed_pages":[1,2,3],
  "reviewer":"实际检查者标识",
  "approved":true
}
```

`reviewed_pages` 必须完整匹配实际 PDF 页码。只有实际检查后才能填写批准。
`resume` 会复用输入和 PDF 哈希均未改变的编译结果，保留已完成的视觉验收；
源文件、编译记录中的本地图/样式依赖或工作区 `.bib` 改变后重新编译。
显式 `compile` 命令仍强制重编译，之后需要重新验收 PDF。

```powershell
python -m pip install PyMuPDF  # 可选，仅用于本地页面预览
python reviewforge_v4.py compile --workspace workspace
python reviewforge_v4.py audit --workspace workspace
python reviewforge_v4.py resume --workspace workspace
```

缺少译文、视觉验收或版面检查失败时，运行状态为 `delivery_blocked`。
`finished_with_unresolved_reviews` 表示仍有待修复段落：使用同一个 `resume`
入口会从修复队列、失败章节和检查点中收集未解决章节，重试这些章节。
整节替换通过检查后才更新修复队列；已解决记录会清除，仍失败的记录继续保留。
空白文本块会直接保留，不占模型调用。不要删除检查点或将状态手工改成 `finished`。
若待改写正文引用缺少原文摘录/定位，续跑在模型调用前暂停，状态为
`blocked_evidence`，具体引用键见 `reports/evidence_preflight.json`。
补齐 `evidence_ledger.json` 中真实读取的原文证据后再续跑；不要把示例文件改名
或把 DOI 元数据当作原文证据。失败块保留最后一次审稿意见/接口错误，便于诊断。
有未修复原文回填的章节会打印 `Saved section ... with ... unresolved blocks`，
避免被误读为整节科学审稿通过。
最终审计中的 `submission_ready` 继续为 false：技术验收不代替科学审稿。
检查失败的译文时，以当前 `translation_gate.json` 为准；旧版文件可能仍被保留。

## 已知边界

保护区域内的数学文字、TikZ 标签和外部图中文字不会自动翻译，需单独编辑图源。
正文使用 `\input` 或 `\include` 引入外部章节时会明确拒绝翻译；先合并为完整正文，
避免把未处理的外部英文段落算作已翻译内容。
自定义宏和复杂 TeX 应先用小样验证；检查器是保守的，可能拒绝合法的复杂翻译。
结构重写仍通过 `plan` 生成候选方案后另行执行，默认 `run` 保留顶层章节。
本次验证使用离线模型替身和真实 XeLaTeX 小样，没有运行收费 API 或重新生成作者论文。

## 回归验证

```powershell
python -m unittest discover -s tests -v
python -m unittest test_quality_system -v
```
