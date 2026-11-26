# Progress

Last updated: 2026-11-26

## 当前状态
- 方案 v1.3 完成；**初步设计使用 FireRedASR2-AED（均衡/高并发）作为默认后端**，LLM 作为精度升级与低置信重解码路径。
- **单引擎策略**：只维护 FireRedASR2，不引入 FunASR；失败重试一次，仍失败返回明确 `error`。
- POC 方案已定（`docs/POC.md` v1.0），**尚未开始编码**。

## 已完成
- `docs/ARCHITECTURE.md` v1.3：三语（粤/普/英 + 混说）、精度优先的完整方案；架构/流程使用 Mermaid；补充术语解释。
- `docs/POC.md` v1.0：MVP 功能、技术选型（sherpa-onnx + FireRedASR2-CTC）、架构、接口、配置、验收标准与里程碑。
- 决策：初步默认 AED；`balanced` 为默认模式，`accuracy`（LLM）后续接入；取消 FunASR 降级链，改为单引擎重试/报错。
- `AGENTS.md`：仓库现状、锁定决策、进度更新要求、验证要求与文档规范。
- 文档检查：PASS（`ARCHITECTURE.md` 16 围栏/8 对/5 Mermaid；`POC.md` 12 围栏/6 对/2 Mermaid）；报告不入库。

## 待办
- [ ] P0：安装 sherpa-onnx、下载模型、CLI 单档转写跑通。
- [ ] P1：Segmenter + WebSocket + 单元测试。
- [ ] P2：演示样例、检查报告、进度同步。
- [ ] M1 骨架：WS Gateway + Session 状态机 + RingBuffer + VAD + Mock ASR，打通端到端延迟测量。
- [ ] M2 真模型：FireRedASR2-AED Adapter（初步默认），粤/普/英三语验证。
- [ ] M3 精度增强：热词/LID/前后填充；低置信句 LLM 重解码（可选）。
- [ ] M4 压测：并发、显存、延迟分位与容量报告。
- [ ] M5 上线：监控、灰度、回归门禁。

## 风险 / 阻塞
- 环境 `torch` 为 CPU 版，4090 暂不可用于推理，需安装 CUDA 版。
- FireRedASR2S 权重未下载；需确认下载渠道与许可。FunASR 不在维护范围（单引擎策略）。
- 初步 AED 的精度需用三语/混说内部集验证；LLM 升级路径待评测后决定是否切换默认。
- 生产硬件规格与并发目标未定（AED 可跑 24GB；LLM 建议 A100/H20）。
- 三语/混说评测集尚未建立，验收指标待基线校准。
- 上报的 pytest 基线（44 passed, 8 skipped）在本仓库无法复现——当前 `main` 无测试文件。
