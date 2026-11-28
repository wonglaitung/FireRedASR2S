# Progress

Last updated: 2026-11-27

## 当前状态
- 正式方案 v1.3：默认 FireRedASR2-AED；LLM 仅作为后续精度升级路径，当前不接入。
- **单引擎 AED**：已删除 CTC（配置、下载、Adapter 分支、对比脚本、文档），避免误用；不引入 FunASR。
- **POC MVP 已跑通**：WAV + WebSocket 两条链路，真实 FireRedASR2-AED。
- **桌面录音器已实现并打包**：PyQt6 + QtWebSocket 客户端；Windows exe 已由 GitHub Actions 产出。
- **验证集已准备**：`eval/yue/` 20 条粤语、`eval/en/` 20 条英文、`eval/yue_en/` 100 条 MCE、`eval/yue_en_spont/` 153 条 WSYue 自發、`eval/yue_en_dictation/` 100 条 SwitchLingua 听写代理。
- **Dockerfile 已改为 AED-only**；本地镜像重建尚未完成（上次构建超时）。
- **官方 AED PyTorch Adapter 已接入**：BF16 + beam5，三套验证集全部优于 sherpa int8。
- **官方 AED 端到端已跑通**：server + Silero VAD；beam10 + LM 下 8.78s 混说音频 2.42s 返回，服务进程 GPU 约 2.8GB。

## 已验证基线
### sherpa int8 + greedy（CPU）
- 粤语 CER：**11.5%**（`eval/yue`，20 条）
- 英文 WER：**1.1%**（`eval/en`，20 条）
- 粤英混说（100 条）：英文词 F1 **84.3%**、混合 CER **7.2%**（sherpa）
- 汇总：`eval/baseline_aed.json`

### 官方 AED PyTorch（RTX 4090，BF16，beam5）
- 粤语 CER：**4.7%**
- 英文 WER：**0.9%**
- 粤英混说（100 条）：英文词 F1 **87.4%**（P 88.7% / R 86.1%）、混合 CER **6.5%**
- 汇总：`eval/baseline_official_aed.json`
- 原 20 条子集的 n-best 上界：F1 **95.4%**、混合 CER **3.9%**；扩到 100 条后 LM 为 88.4% / 6.0%。
- WSYue 自發 153 条：官方 AED 1-best **71.5% / 10.1%**；MCE LM 退化到 **70.5% / 10.2%**。
- SwitchLingua 个人听写代理 100 条：官方 AED 1-best **88.5% / 6.6%**；MCE LM 退化到 **83.2% / 9.4%**。
- 轻量 n-best 重打分（confidence + 词频）失败：F1 88.6%~88.8%、混合 CER 6.9%，低于 1-best。
- **n-best + 混说 n-gram LM 成功**：100 条混说上 F1 **88.4%**、混合 CER **6.0%**；粤语 CER/英文 WER 保持 4.7% / 0.9%。原 20 条子集 F1 95.4%，说明小集偏乐观；LM 用 2400 条 MCE train 文本训练，排除 100 条评估集。
- held-out 20 条更长混说 sanity check：F1 45.4% → 46.0%，混合 CER 17.3% → 16.7%，正向但绝对值受长句影响。
- 简单 OOV 词表纠错收益有限：F1 90.3% → 90.8%。

## 已完成
- `README.md` v2.6：项目概览、快速开始、录音器/Windows exe、MCE/WSYue/听写代理验证集、数据规范与技术演化。
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先方案。
- `docs/POC.md` v2.6：AED-only POC、官方 AED 对照、端到端、MCE/WSYue/听写代理验证与 n-best LM。
- `docs/EVOLUTION.md` v1.0：从第一版 POC 到当前阶段的完整技术演化。
- `docs/DATA.md` v1.0：个人听写/会议全文的采集、标注、划分与校验规范。
- `docs/RECORDER.md` v1.7：录音器设计、跨机器、Windows exe、打包。
- `docs/DOCKER.md` v1.3：AED-only 镜像、端口、模型挂载。
- **删除 CTC**：`configs/app_ctc.yaml`、`scripts/compare_backends.py`、sherpa CTC 分支、CTC 下载逻辑均移除。
- 验证集：
  - `eval/yue/`：words.hk，CC BY 4.0，20 条纯粤语。
  - `eval/en/`：LibriSpeech validation.clean，CC BY 4.0，20 条英文。
  - `eval/yue_en/`：MCE，研究用途，100 条粤英混说。
  - `scripts/eval_suite.py`：一次跑三套，输出 CER/WER/英文 P/R/F1、混合 CER；英文按 token 边界匹配。
- 官方 AED：`src/firered_poc/asr/official.py`、`configs/app_official.yaml`、`scripts/setup_official_aed.sh`；模型/代码缓存于 `models/`。
- 后端：`src/firered_poc/`（Silero VAD、segmenter+merge、AED Adapter、postprocess、CLI、WS server）。
- 录音器：`src/firered_recorder/`（PyQt6 + QtMultimedia + WebSocket）。
- 打包：`scripts/build_recorder.py`、`.github/workflows/build-recorder.yml`；Windows exe 已产出。
- Docker：`Dockerfile`（AED-only）、`Dockerfile.local`（只复制 AED/Silero/标点）、`scripts/build_docker_local.sh`。
- 质量门禁：`ruff check .` PASS；`pytest` 53 passed。
- 报告：`/tmp/opencode/reports/`。

## 待办
- [x] 删除 CTC，统一 AED。
- [x] 准备粤语/英文/粤英混说三套验证集与基线。
- [x] 将 POC 从 sherpa int8 greedy 切到官方 AED PyTorch（BF16 + beam5）。
- [x] n-best + 混说 n-gram LM 重打分（100 条 F1 88.4%；原 20 条子集 95.4%）。
- [x] 扩到 100 条同分布混说验证集，确认 20 条明显偏乐观。
- [x] 补 WSYue 自發混说 153 条。
- [ ] 为自發域单独训练/选择 LM，或按场景开关 LM。
- [x] 个人听写/会议全文数据采集、标注、划分与校验规范（`docs/DATA.md`）。
- [x] 接 SwitchLingua 个人听写公开代理 100 条（非真实听写）。
- [ ] 采集个人听写 pilot 100–200 条，并用单句 harness 跑基线。
- [ ] 采集会议 pilot 3 场，并用全文/切分 harness 跑基线。
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
- 本仓库当前 pytest 为 53 passed（新增严格评测指标、LM、官方 AED 配置、数据校验测试）。
