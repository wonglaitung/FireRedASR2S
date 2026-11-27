# Progress

Last updated: 2026-11-27

## 当前状态
- 正式方案 v1.3：默认 FireRedASR2-AED；LLM 仅作为后续精度升级路径，当前不接入。
- **单引擎 AED**：已删除 CTC（配置、下载、Adapter 分支、对比脚本、文档），避免误用；不引入 FunASR。
- **POC MVP 已跑通**：WAV + WebSocket 两条链路，真实 FireRedASR2-AED。
- **桌面录音器已实现并打包**：PyQt6 + QtWebSocket 客户端；Windows exe 已由 GitHub Actions 产出。
- **验证集已准备**：`eval/yue/` 20 条粤语、`eval/en/` 20 条英文、`eval/yue_en/` 20 条粤英混说。
- **Dockerfile 已改为 AED-only**；本地镜像重建尚未完成（上次构建超时）。

## 已验证基线（AED，本机 CPU，sherpa int8 + greedy）
- 粤语 CER：**11.5%**（`eval/yue`，20 条）
- 英文 WER：**1.1%**（`eval/en`，20 条）
- 粤英混说英文词召回：**104/119 = 87.4%**（`eval/yue_en`，20 条）
- 汇总：`eval/baseline_aed.json`

## 已完成
- `README.md` v1.8：项目概览、快速开始、录音器/Windows exe、验证集。
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先方案。
- `docs/POC.md` v1.7：AED-only POC、接口、配置、实测与运行方式。
- `docs/RECORDER.md` v1.6：录音器设计、跨机器、Windows exe、打包。
- `docs/DOCKER.md` v1.3：AED-only 镜像、端口、模型挂载。
- **删除 CTC**：`configs/app_ctc.yaml`、`scripts/compare_backends.py`、sherpa CTC 分支、CTC 下载逻辑均移除。
- 验证集：
  - `eval/yue/`：words.hk，CC BY 4.0，20 条纯粤语。
  - `eval/en/`：LibriSpeech validation.clean，CC BY 4.0，20 条英文。
  - `eval/yue_en/`：MCE，研究用途，20 条粤英混说。
  - `scripts/eval_suite.py`：一次跑三套，输出 CER/WER/英文召回。
- 后端：`src/firered_poc/`（Silero VAD、segmenter+merge、AED Adapter、postprocess、CLI、WS server）。
- 录音器：`src/firered_recorder/`（PyQt6 + QtMultimedia + WebSocket）。
- 打包：`scripts/build_recorder.py`、`.github/workflows/build-recorder.yml`；Windows exe 已产出。
- Docker：`Dockerfile`（AED-only）、`Dockerfile.local`（只复制 AED/Silero/标点）、`scripts/build_docker_local.sh`。
- 质量门禁：`ruff check .` PASS；`pytest` 39 passed。
- 报告：`/tmp/opencode/reports/`。

## 待办
- [x] 删除 CTC，统一 AED。
- [x] 准备粤语/英文/粤英混说三套验证集与基线。
- [ ] 将 POC 从 sherpa int8 greedy 切到官方 AED PyTorch（FP16/BF16 + beam/n-best + 外部 LM）。
- [ ] 用 `eval_suite.py` 对比官方 AED 与当前基线，重点看粤语 CER、英文 WER、英文召回。
- [ ] 重建 Docker 镜像（AED-only）并复测。
- [ ] 真实 Windows 双击冒烟、真机麦克风冒烟。
- [ ] 补自發粤英对话验证集。
- [ ] 工程化：server 重试/超时、并发压测、生产部署。

## 风险 / 阻塞
- 当前 AED 仍是 sherpa int8 + greedy，不是精度上限。
- MCE 仅限研究，商用需授权；全部来自 train split，不是官方测试集。
- 验证集偏朗讀/半自發，不能完全代表真实港式粤英对话。
- `eval/en` 是 native English，不是香港口音英文。
- AED CPU 推理较慢；官方 beam/LM 需要 GPU 更合适。
- Docker 本地镜像重建超时；当前本地旧镜像可能仍含 CTC 文件（代码已不会使用）。
- 录音器包只含客户端，不含后端与模型。
- 当前容器无真实麦克风；录音器麦克风链路仅做设备枚举/格式转换/offscreen GUI 验证。
- 未做代码签名；Windows SmartScreen 可能拦截。
- 上报的 pytest 基线（44 passed, 8 skipped）与本仓库无关；本仓库现为 39 passed。
