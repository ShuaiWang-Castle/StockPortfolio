# GPT 早期研究原包归档

2026-11-19，Shuai 提供了两份从早期研究交付中保留的 ZIP，并确认可向本公开仓库原样归档。11/13 的冻结价格和 11/9 的会计估值资料都能从这里取得。两包共 281 个文件成员均通过 ZIP CRC 校验；11/9 包所列 133 项 SHA-256 和字节数全部相符。下表整包 SHA-256 为接收后计算的指纹，供后续下载者逐字节比对。没有随件提供的历史整包指纹可供独立对照。[逐项核验汇总](out/summary.json) · [本次归档清单](manifest.json)

| 原始交付 | 研究截点 | 包内文件数 | 字节 | 收件时 SHA-256 |
|---|---|---:|---:|---|
| [组合复核数据与代码 ZIP](ai_portfolio_review_20261113_data_code.zip) | 2026-11-13 美股收盘 | 146 | 7,200,406 | `63e5a106b91124b1d798dcfc24082b7a595c6b3f251b4c6e07211fe4c1dad695` |
| [会计估值数据与代码 ZIP](ai_portfolio_valuation_data_and_code.zip) | 模型 2026-11-09，价格截至 11-06 收盘 | 135 | 9,776,730 | `5961db76cdb0163c3a015254fe45a6b6f4f757b1b7841a40038d6a83ccbbce30` |

## 历史数据如何接上已入库的 GPT 复核

| 检验对象 | 实测结果 |
|---|---|
| 11/13 的 `market_data/`、`market_data_extended/` | 按两个目录各自的来源记录核对每个原始响应，SHA-256 与字节数分别通过 32/32、39/39。扩充价格表引用的两份基础 CSV 指纹也相符。 |
| 既有 `gpt_review_20261113/data_audit/` | 先按 GPT 原清单核验旧包的来源文件及 16 份原始价格响应，再与新到包交叉比对。旧包的 39 标的 provenance 与新到扩充价格表的 provenance 逐字节一致，旧包记录的扩充版复权价格 CSV 指纹相符，16/16 个共同标的的原始文件逐字节一致。原包补齐另外 23 个标的的来源文件。旧包另外四个标的是当时另行抓取的 BTAL、XLP、BIL、SMH。 |
| 11/13 的两份独立审计与工作簿验证记录 | 两份审计对输入模型和价格文件的四处指纹，以及工作簿验证记录对模型的一处指纹，全部相符。两处 BRK 研究记录列出的三份 PDF 指纹相同，文件本身未收进这两包。 |
| 11/9 的 `MANIFEST.json` | 133/133 项 SHA-256 和字节数相符。包中另有原清单自身与 `README.txt`。价格来源记录另核对 15、3、8 份原始响应，合计 26/26。 |
| 共用模型 | 两包的 `valuation_research/consolidated_model.json` 逐字节相同。 |

这些检查使用原件的 ZIP 成员和既有 Git 文件，未执行外部交付中的脚本，也未重算这些旧研究的估值、配置或工作簿。当前采纳方案见仓库根目录。[已采纳方案](../current_plan.json)

## 根 README 所指原件的恢复范围

表中“包内”路径从对应 ZIP 根部开始。仓库保留压缩容器和归档入口，原目录结构在 ZIP 内可浏览。原根目录中依然失效的链接可按下表定位。[11/13 包](ai_portfolio_review_20261113_data_code.zip) · [11/9 包](ai_portfolio_valuation_data_and_code.zip)

| 根 README 的旧路径 | 可取得的原件 |
|---|---|
| `portfolio_refresh_20261113/` | 11/13 包内有 145 份文件，包括直接引用的 `analysis/portfolio_conviction_review.json` 和整个已交付的 `market_data_extended/`。 |
| `valuation_research/` | 11/9 包内 86 份文件，覆盖会计输入、来源缓存、DCF 模型及脚本。11/13 包另含其中的合并模型。 |
| `ai_expansion_analysis/`、`investment_plan_analysis/`、`market_data/` | 11/9 包内分别有 16、9、22 份文件。旧索引另列的 `market_analysis/` 缺件。 |
| `outputs/ai_portfolio_20261113/ai_portfolio_review_20261113_data_code.zip`、`outputs/ai_valuation/ai_portfolio_valuation_data_and_code.zip` | 对应上表两份原始 ZIP。 |
| `docs/` | 两包均缺 `RESEARCH_REPORT_ZH.md`、`EXPECTED_RETURN_ZH.md`、`DECISIONS_AND_ASSUMPTIONS.md`、`REPRODUCIBILITY.md`、`AGENT_COLLABORATION.md`。 |
| 其余 `outputs/` 链接 | 缺 `ai_portfolio_20261113/ai_portfolio_review_20261113.xlsx`、`ai_portfolio_20261113/ai_portfolio_review_20261113.png`、`ai_valuation/ai_portfolio_valuation.xlsx`、`ai_valuation/portfolio_risk_review.png`、`portfolio_review/portfolio_analysis.xlsx`、`portfolio_review/portfolio_data_and_code.zip`。 |
| `tools/`、根 `manifest.json` | 仍缺。11/9 包的大写 `MANIFEST.json` 的覆盖范围为该包的 133 项。 |

11/13 的两处 BRK 记录还引用 `3rdqtr26.pdf`、`nov0726.pdf`、`feb2826.pdf`。补这三份原件时，可先对照保留下来的 SHA-256。Claude 11/13 使用的 52 资产原始浏览器数组也仍待取得。此处归档的两个日期、两套选择范围和获取方式均与该数组不同。[缺件指纹](out/summary.json)

## 离线复核

从仓库根运行。核验脚本只使用 Python 标准库，读取本目录的两个原包和已有 GPT 复核文件，将结果写入 `out/summary.json`。输入文件的逐个 SHA-256 保存在该输出中。clean export 对照值见归档清单。

```sh
python3 -I gpt_archive_20261113/verify_import.py .
```
