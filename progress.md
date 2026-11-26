# Progress

Last updated: 2026-11-27

## 当前状态
- 正式方案 v1.3：初步设计使用 FireRedASR2-AED（均衡/高并发）作为默认后端，LLM 作为精度升级与低置信重解码路径。
- **单引擎策略**：只维护 FireRedASR2，不引入 FunASR；失败重试一次，仍失败返回明确 `error`。
- **POC MVP 已实现并跑通**：WAV + WebSocket 两条链路，真实 FireRedASR2-AED（默认）/ CTC（快速）。
- P0 #1~#3 已完成：AED vs CTC 对比、标点/ITN/繁简、Silero VAD + 句段合并。

## 已完成
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先的完整方案。
- `docs/POC.md` v1.4：POC 范围、选型、架构、接口、配置、验收、AED/CTC 对比与运行方式。
- POC 代码：`src/firered_poc/`（audio、Silero/能量 VAD、segmenter+merge、session、ASR Adapter、postprocess、CLI、WebSocket server）。
- 默认后端：**AED**（`configs/app.yaml`）；**CTC 快速模式**（`configs/app_ctc.yaml`）。
- 后处理：CT-Transformer 标点 + 保守 ITN（日期/金额/百分比）+ OpenCC 繁简。
- 脚本：`scripts/download_model.sh`（AED + CTC + Silero + 标点）、`scripts/compare_backends.py`。
- 实测（CPU）：
  - 中英混说：CTC `MOAY TOAY ... 礼拜八二` → AED `MONDAY TODAY ... 礼拜二`（AED 明显更好）。
  - 四川话、粤语、英文：两后端接近；AED 略慢。
  - AED 时延：10.05s 音频约 2.76s（RTF ≈ 0.27）；CTC 约 1.75s（RTF ≈ 0.17）。
  - WebSocket（AED + Silero VAD）：10.05s 音频返回 2 条 `final`，端到端 2.24s。
- 质量门禁：`ruff check .` PASS；`pytest` 28 passed（真实模型、Silero VAD、后处理、WebSocket）。
- 报告：`/tmp/opencode/reports/`（ruff、pytest、AED vs CTC、POC demo、文档检查），不入库。

## 待办
- [x] P0 #1：AED vs CTC 同集对比，默认切 AED。
- [x] P0 #2：标点 + ITN + 繁简。
- [x] P0 #3：Silero VAD + 句段合并。
- [ ] 建立内部三语/混说评测集，量化 CER/WER 与幻觉率。
- [ ] 精度增强：LLM 低置信重解码、热词/Prompt、繁简策略细化。
- [ ] 工程化：server 重试/超时、并发压测、打包、生产部署。
- [ ] 长音频与噪声/音乐场景验证。

## 风险 / 阻塞
- AED 在 CPU 上比 CTC 慢约 1.5~2 倍；生产需 GPU。
- 标点模型 73MB、AED 约 1.2GB；首次启动与内存开销增加。
- ITN 策略保守，仅处理日期/金额/百分比，未覆盖所有数字表达。
- 句段合并只在文件模式生效；WebSocket 仍按实时句段返回。
- 粤语/英语样例覆盖仍有限；缺内部 CER/WER 评测集。
- 模型共约 1.3GB，未入库（`models/` 已 gitignore）；需运行下载脚本。
- 上报的 pytest 基线（44 passed, 8 skipped）与本仓库无关；本仓库现为 28 passed。
