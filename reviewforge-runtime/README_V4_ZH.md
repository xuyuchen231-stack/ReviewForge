# ReviewForge v4 — 微生物发酵混合建模综述自动化

本目录是 v3 的增量升级，原有 `setup_secret.bat`、`check_connection.bat` 和 `start_9h.bat` 均保留。**本次使用新入口 `start_review_v4_9h.bat`。**

## Windows 快速使用

1. 安装 Python 3.10+、Git；推荐安装 [MiKTeX](https://miktex.org/download)，确保命令行 `latexmk` 和 `xelatex` 可调用（安装时允许按需安装 LaTeX 包）。
2. **首次配置一次即可**：执行 `setup_secret.bat`，密钥保存至用户目录 `%USERPROFILE%\\.reviewforge\\credentials.env`，后续克隆、更新或移动项目都会自动读取。若旧目录存在 `.env`，脚本可选择导入而无需重新输入。然后执行 `check_connection.bat` 检查 MiMo / DeepSeek。配置 MiMo `mimo-v2.6-flash:free` 写作，DeepSeek `deepseek-v4.1-flash:free` 审稿。
3. 将**完整英文 LaTeX 源文件**放在 `workspace/original.tex`，原论文的图片、`.bib`、`.sty` 等文件保持原相对路径也复制到 `workspace/`。从现有项目导入可运行：

```powershell
py import_project.py "C:\path\to\my-paper\main.tex"
```

4. 双击 `check_review_v4.bat` 看环境预检；双击 `start_review_v4_9h.bat` 开始，关闭/中断后使用 `resume_review_v4.bat` 续跑。
5. 查看 `workspace/reports/literature_gate.json`、`workspace/reports/final_audit.json`、`workspace/reports/review_en_build.json` 与 `review_zh_build.json`。正常编译的 PDF 在 `workspace/output/review_en.pdf` 和 `review_zh.pdf`。

## 实际流水线

- OpenAlex 的多检索式结果经 Crossref DOI 元数据核对，形成去重的 `literature.json`、`references.bib` 和检索日志。**元数据核验不等于阅读全文或论断真实性验证。** 如果不足 60 条 DOI 登记文献，流程在检索门停止而不是编造文献。
- 以 `original.tex` 为只读输入，按 `\\section` 逐节向 MiMo 请求编辑；结构门保护图表、标签、旧引用，然后由 DeepSeek 提交 JSON 审稿意见。接受的改动写入 `review_en.tex` 和 `revisions/`，检查点记录到 `v4_state.json`。
- 逐节中文翻译，保留 LaTeX 数学/图表命令；再调用本地 `latexmk -xelatex` 编译两份 PDF。
- `final_audit.json` 审核英中引用键一致性，以及论文实际引用文献数量是否达到 60；只有**实际使用的独立引用键**才计入，而非仅 `.bib` 收录数量。
- 到达 9 小时上限后保留进度；其间如果已完成，则正常结束，不人为持续浪费调用。

## 手动命令

```powershell
py reviewforge_v4.py preflight
py reviewforge_v4.py discover --minimum 60
py reviewforge_v4.py run --hours 9 --minimum 60
py reviewforge_v4.py resume --minimum 60
py reviewforge_v4.py audit --minimum 60
py reviewforge_v4.py compile
py -m unittest discover -s tests -v
```

## 科研质量说明

当前 v4 可以跨平台地组织 DOI 元数据检索、逐节修改、两模型审阅、编译和检查点，但不自动获取被墙或受版权限制的全文，不具备 DOI 所代表论文对每条科学论断的自动实质核验；也不会将 60 条下载到的元数据直接冒充 60 条正文引用。低质量候选文献应在 `literature.json` 经作者筛选后再进入正式引文集。若英语原稿本身不足 60 条引用，v4 会明确将 `minimum_pass` 标记为 `false`，而不是为了数量强行把无关论文塞进正文。

**注意**：编译失败、工具未安装或科研证据不足时，报告会记为 FAILED/UNAVAILABLE；生成 PDF 也不意味着达到投稿质量。源论文、图和引用需要人工复核。不要把 `workspace/` 中包含未发表论文的内容推送到公开 GitHub。

## Light-skills 整合

借鉴 MIT 许可开源仓库 <https://github.com/Light0305/Light-skills> 的 `light-literature-search`, `light-citation`, `light-paper-writing`, `light-consistency`, `light-typesetting`, `light-figure`, `light-orchestrator`, `light-memory-pm`, `light-file-reading`, `light-review-rebuttal`, `light-research-ethics`, `light-venue-matching` 工作流设计。这里是**自主实现的轻量集成**，并未复制其 23 个技能的全部脚本，也不声称原项目的正式集成或官方兼容。请见 `LIGHT_INTEGRATION.md`。

## 从 v3 升级说明

本 ZIP 已包含 v3 的所有文件。不要把它直接覆盖到旧目录里；建议解压到**新的目录**，避免原稿、旧 `state.json`、密钥配置与新版 `v4_state.json` 混淆。旧 v3 的 `start_9h.bat` 仍运行 Markdown 引擎；新 v4 的入口是 `start_review_v4_9h.bat`。

**持久化配置（更新）**：现在 API 配置保存在 `%USERPROFILE%\\.reviewforge\\credentials.env`，不是 Git 仓库中。第一次设置后，升级或新克隆项目不需要再次输入。旧版目录中的 `.env` 可通过 `setup_secret.bat` 导入一次。不要将配置文件提交到 GitHub。

可在 `.env` 中将 `RF_MAX_OUTPUT_TOKENS` 设为 `12000` 或供应商支持的更高数值，以降低长章节返回被截断的风险；过长的章节会保留原文并在报告中标记待拆分。


## 多 API Key（同平台）

在**当前任务结束后**更新代码：

```powershell
cd "D:\\拓展和skill\\ReviewForge-repo"
git pull origin main
cd reviewforge-runtime
.\\setup_secret.bat
```

如果提示已有持久配置，选择 `n` 重新配置；逐个输入获授权的 Token Harbor Key，最后直接回车结束。密钥只保存在 `%USERPROFILE%\\.reviewforge\\credentials.env`，不提交到 GitHub。旧单 Key 配置继续可用。

多 Key 功能默认**不会**切换以规避限流。仅当服务商允许多个独立计费账户间进行故障切换时，才可以在 `credentials.env` 中单独增加：

```ini
RF_ALLOW_BILLING_FAILOVER=1
```

该模式仅在服务端明确返回 HTTP 402（需要付费/余额不足）时尝试下一个 Key；HTTP 429 不轮换，401/403 也不会自动换 Key。部分平台的余额不足错误并非 HTTP 402，因此不能保证覆盖所有额度耗尽情形。配置更改不会影响已经运行中的进程。可用 `.\\check_connection.bat` 验证连接，随后再启动或恢复任务。
