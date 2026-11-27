# Progress

Last updated: 2026-11-27

## 当前状态
- 正式方案 v1.3：初步设计使用 FireRedASR2-AED（均衡/高并发）作为默认后端，LLM 作为精度升级与低置信重解码路径。
- **单引擎策略**：只维护 FireRedASR2，不引入 FunASR；失败重试一次，仍失败返回明确 `error`。
- **POC MVP 已实现并跑通**：WAV + WebSocket 两条链路，真实 FireRedASR2-AED（默认）/ CTC（快速）。
- **独立桌面录音器 MVP 已实现**：PyQt6 窗口，麦克风 → WebSocket → 后端逐句转写；不依赖 `/data/opencode`。
- **录音器打包脚本与 Windows CI 已就绪**：PyInstaller 构建脚本已在本机 Linux 验证；Windows exe 需在 Windows 或 GitHub Actions 构建。

## 已完成
- `README.md` v1.0：项目概览、快速开始、录音器/Windows exe 使用与环境说明。
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先的完整方案。
- `docs/POC.md` v1.5：POC 范围、选型、架构、接口、配置、验收、AED/CTC 对比与运行方式。
- `docs/RECORDER.md` v1.4：独立录音器设计、协议、跨机器部署、Windows exe 使用与打包。
- POC 后端：`src/firered_poc/`（audio、Silero/能量 VAD、segmenter+merge、session、ASR Adapter、postprocess、CLI、WebSocket server）。
- 默认后端：**AED**（`configs/app.yaml`）；**CTC 快速模式**（`configs/app_ctc.yaml`）。
- 后处理：CT-Transformer 标点 + 保守 ITN（日期/金额/百分比）+ OpenCC 繁简。
- 录音器：`src/firered_recorder/`（PyQt6 + QtMultimedia + WebSocket；GUI 与 `--file` 无窗口模式）。
- 打包：`scripts/build_recorder.py`、`.github/workflows/build-recorder.yml`；GitHub Actions run `45915057637` 成功。
- Windows 产物：`dist/FireRedRecorder-windows.zip`（约 102MB，sha256 `fcd389b4…`），解压后 `FireRedRecorder/FireRedRecorder.exe` + `_internal`。
- 脚本：`scripts/download_model.sh`（AED + CTC + Silero + 标点）、`scripts/compare_backends.py`。
- 实测（CPU）：
  - 中英混说：CTC `MOAY TOAY ... 礼拜八二` → AED `MONDAY TODAY ... 礼拜二`（AED 明显更好）。
  - AED 时延：10.05s 音频约 2.76s（RTF ≈ 0.27）；CTC 约 1.75s（RTF ≈ 0.17）。
  - WebSocket（AED + Silero VAD）：10.05s 音频返回 2 条 `final`，端到端 2.24s。
  - 录音器文件模式：真实后端返回 2 条 `final`，文本与后端一致。
  - PyInstaller Linux 构建：`dist/FireRedRecorder`（约 370MB），`--help` 与文件模式 E2E 均通过。
- 质量门禁：`ruff check .` PASS；`pytest` 39 passed（真实模型、Silero VAD、后处理、WS、录音器协议/GUI/文件 E2E）。
- 报告与截图：`/tmp/opencode/reports/`、`/tmp/opencode/recorder-window.png`。

## 待办
- [x] P0 #1：AED vs CTC 同集对比，默认切 AED。
- [x] P0 #2：标点 + ITN + 繁简。
- [x] P0 #3：Silero VAD + 句段合并。
- [x] 独立桌面录音器 MVP（窗口 + 文件模式）。
- [x] 后端启动横幅：打印监听地址、健康检查、WebSocket（含 LAN IP）与录音器示例命令。
- [x] 录音器跨机器：先连 WebSocket，收到 `ready` 后才开麦；地址可指向 `ws://<局域网IP>:8000/ws`。
- [x] 录音器打包脚本 + GitHub Actions（Windows 构建入口）。
- [x] 在 GitHub Actions 实际产出 `FireRedRecorder.exe`。
- [ ] 在真实 Windows 上双击冒烟（本机 Wine 6 无法运行该 exe，报 UCRT `fetestexcept` 缺失）。
- [ ] 真机麦克风冒烟（Windows/Linux 桌面），验证设备热插拔与长时录音。
- [ ] 后端打包（Python + 依赖 + 模型）或保留独立服务部署。
- [ ] 托盘/快捷键、代码签名、安装包。
- [ ] 后端 `partial` 事件，实现逐字/草稿显示。
- [ ] 录音器断线重连、自动拉起本地后端（sidecar）。
- [ ] 建立内部三语/混说评测集，量化 CER/WER 与幻觉率。
- [ ] 精度增强：LLM 低置信重解码、热词/Prompt。
- [ ] 工程化：server 重试/超时、并发压测、生产部署。

## 风险 / 阻塞
- PyInstaller 不能跨平台：本机只产出 Linux 二进制（约 370MB）；Windows exe 已由 GitHub Actions 产出，但尚未在真实 Windows 运行验证。
- GitHub Actions artifact 为双层 zip；本机已整理为 `dist/FireRedRecorder-windows.zip`。
- 录音器包只含客户端，不含后端与模型；后端仍需单独运行。
- 当前容器无真实麦克风语音输入；录音器麦克风链路仅做设备枚举、格式转换与 offscreen GUI 验证。
- Linux QtMultimedia 依赖 PipeWire/GStreamer；容器内会打印缺失警告，但 offscreen UI 正常。
- 未做代码签名；Windows SmartScreen 可能拦截。
- 录音器只做客户端，后端需先运行；未做 sidecar 自动启动。
- 后端是句级非流式，文字按句出现，不是逐字。
- AED 在 CPU 上比 CTC 慢约 1.5~2 倍；生产需 GPU。
- 标点模型 73MB、AED 约 1.2GB；首次启动与内存开销增加。
- 句段合并只在文件模式生效；WebSocket 仍按实时句段返回。
- 模型共约 1.3GB，未入库（`models/` 已 gitignore）；需运行下载脚本。
- 上报的 pytest 基线（44 passed, 8 skipped）与本仓库无关；本仓库现为 39 passed。
