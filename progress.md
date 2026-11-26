# Progress

Last updated: 2026-11-26

## 当前状态
- 正式方案 v1.3：初步设计使用 FireRedASR2-AED（均衡/高并发）作为默认后端，LLM 作为精度升级与低置信重解码路径。
- **单引擎策略**：只维护 FireRedASR2，不引入 FunASR；失败重试一次，仍失败返回明确 `error`。
- **POC MVP 已实现并跑通**：WAV + WebSocket 两条链路，使用真实 FireRedASR2-CTC（sherpa-onnx，CPU）。

## 已完成
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先的完整方案。
- `docs/POC.md` v1.1：POC 范围、选型、架构、接口、配置、验收、实测结果与运行方式。
- POC 代码：`src/firered_poc/`（audio、VAD、segmenter、session、ASR Adapter、CLI、WebSocket server）。
- 配置与脚本：`configs/app.yaml`、`scripts/download_model.sh`、`pyproject.toml`、`requirements.txt`、`.gitignore`。
- 实测（CPU）：普通话、中英混说、四川话、粤语、英文均能出字；WebSocket 流式返回 5 条 `final`。
- 质量门禁：`ruff check .` PASS；`pytest` 14 passed（含 1 个真实模型冒烟测试）。
- 报告：`/tmp/opencode/reports/`（ruff、pytest、POC demo、文档检查），不入库。

## 待办
- [x] P0：安装 sherpa-onnx、下载模型、CLI 单档转写跑通。
- [x] P1：Segmenter + WebSocket + 单元测试。
- [x] P2：演示样例、检查报告、进度同步。
- [ ] 改进 VAD：能量 VAD 会把自然停顿切成多段，评估 Silero VAD 或 FireRedVAD。
- [ ] 精度增强：标点/ITN、繁简归一、AED/LLM 对比、低置信重解码。
- [ ] 工程化：打包、并发压测、错误码与超时策略、生产部署。
- [ ] 补充粤语/英语内部评测集，校准 CER/WER。

## 风险 / 阻塞
- 能量 VAD 对停顿敏感，实测 10s 音频被切成 5 段；需后续替换。
- CTC 在英文与数字上仍有错字（如 `MONDAY TODAY` → `MOAY TOAY`），POC 可接受。
- CPU 仅适合单路/少路 POC；多路并发与生产延迟需 GPU + AED/LLM。
- 模型约 740MB，未入库（`models/` 已 gitignore）；需运行下载脚本。
- 环境 `torch` 为 CPU 版，但 POC 使用 onnxruntime，不受影响。
- 正式方案 AED/LLM 的精度仍需内部三语/混说评测集验证。
- 上报的 pytest 基线（44 passed, 8 skipped）与本仓库无关；本仓库现为 14 passed。
