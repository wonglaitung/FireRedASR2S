# FireRedASR2S POC 设计与 MVP 范围

> 版本：v1.6
> 目标：用最小闭环验证 **音频 → 句级文字**，并明确 MVP 要实现的功能、技术选型与验收标准。
> 状态：**POC MVP 已实现并跑通**（WAV + WebSocket，真实 FireRedASR2）；默认 AED，CTC 作为快速备选；已接入 Silero VAD、句段合并、标点/ITN/繁简后处理。

---

## 1. POC 目标

POC（Proof of Concept，概念验证）只回答一个问题：**用 FireRedASR2 能否把粤语、普通话、英文及混说的整句音频稳定转成文字。**

验证范围：

1. **WAV 文件转写**：一条命令输入音频，输出整句文本。
2. **WebSocket 流式转写**：客户端推 PCM，句尾返回整句文本。
3. **真实模型**：使用 FireRedASR2 权重，不用 Mock。
4. **三语覆盖**：粤语（香港/广东）、普通话、英文，含句内混说（code-switching，语码混用）。

---

## 2. MVP 功能清单

| 编号 | 功能 | 说明 |
| --- | --- | --- |
| F1 | WAV 文件转写 | 读 16kHz/16bit/mono；非 16kHz 自动重采样 |
| F2 | WebSocket 串流 | 接收 20ms PCM（Pulse Code Modulation，脉冲编码调制）帧，句尾回 `final` |
| F3 | 句级切分 | pre-roll（句首回看）300ms、post-roll（句尾保留）300ms、静音 450ms、最短 250ms、最长 15s；支持相邻句段按 gap 合并 |
| F4 | 非流式 ASR（Automatic Speech Recognition，自动语音识别） | 整句送入 FireRedASR2，返回 `text` 与 `start_ms/end_ms`；含标点、ITN、繁简 |
| F5 | 单引擎失败处理 | 重试一次；仍失败返回明确 `error`，不跨引擎降级 |
| F6 | 配置化 | 模型路径、VAD（Voice Activity Detection，语音活动检测）参数、线程数走 YAML |
| F7 | CLI + WS 服务 | 一条命令转档；一个 WS 端点；`/health` 健康检查 |
| F8 | 基础测试 | 切分器、VAD、会话状态机、后处理与 WS 的测试 |

---

## 3. 非目标（POC 不做）

- 不接 FireRedASR2-LLM（8B+）与低置信重解码。
- 不做 LID（Language Identification，语种识别）与 Prompt/热词注入。
- 不做动态批处理、多卡、队列削峰、生产级监控。
- 不用 FireRedVAD；POC 用 Silero VAD 代替。
- 不做说话人分离、离线批量转写。

---

## 4. 技术选型

### 4.1 推荐路径：sherpa-onnx + FireRedASR2-AED（CTC 快速备选）

| 项 | 选择 | 理由 |
| --- | --- | --- |
| 推理运行时 | sherpa-onnx | 纯 ONNX（Open Neural Network Exchange，开放神经网络交换格式）、CPU 可跑、安装简单 |
| 默认模型 | **FireRedASR2-AED ONNX（约 838MB）** | 精度优先；中英混说明显优于 CTC；与正式方案默认 AED 一致 |
| 快速备选 | FireRedASR2-CTC-int8（约 520MB） | CPU 更快；单语场景可接受，混说/英文较弱 |
| VAD | Silero VAD（约 0.6MB） | 比能量 VAD 稳，CPU 运行 |
| 句段合并 | `merge_gap_ms` | 减少自然停顿造成的碎句，文件模式默认开启 |
| 后处理 | CT-Transformer 标点 + cn2an ITN + OpenCC | 标点、日期/金额/百分比、繁简归一 |
| 正式生产 | 官方 FireRedASR2S PyTorch + AED/LLM + CUDA | POC 只验证可行性，不替代生产方案 |

> AED 比 CTC 慢约 1.5~2 倍，但 10s 音频 CPU 仍在 3s 内出字，且中英混说准确率明显更好，故 POC 默认 AED。Adapter（适配器）隔离后端，`configs/app_ctc.yaml` 可切回 CTC。

### 4.2 关键指标参考

- 官方文档中 CTC 单句 RTF（Real Time Factor，实时率）约 0.17；POC 实测 AED 约 0.25~0.33（CPU）。
- POC 目标：10s 音频单句延迟可接受；WS 端到端 CTC 约 2s、AED 实测约 2.2s；不承诺生产延迟。

---

## 5. 系统架构

```mermaid
flowchart LR
    IN["输入<br/>WAV 文件 / WebSocket PCM"] --> SEG["Segmenter<br/>VAD + pre/post roll"]
    SEG --> ASR["ASR Adapter<br/>FireRedASR2-AED（默认）/ CTC"]
    ASR --> OUT["结果<br/>text + start_ms/end_ms"]
    OUT --> CLI["CLI stdout"]
    OUT --> WS["WS final"]
```

WebSocket 时序：

```mermaid
sequenceDiagram
    participant C as 客户端
    participant S as Server
    participant V as Segmenter
    participant A as ASR Adapter
    C->>S: start
    C->>S: audio（20ms）× N
    S->>V: 推入 PCM
    V->>V: VAD 端点判定
    V-->>S: 完整句段
    S->>A: transcribe（PCM）
    A-->>S: text + 时间戳
    S-->>C: final
    C->>S: stop
```

---

## 6. 模块与代码结构（已实现）

```text
src/firered_poc/
├── audio.py          # WAV 读取 / 重采样
├── vad.py            # Silero VAD / 能量 VAD
├── segmenter.py      # RingBuffer / 端点 / 软硬切分 / 句段合并
├── asr/
│   ├── base.py       # ASRAdapter 接口
│   └── sherpa.py     # FireRedASR2 CTC/AED 实现
├── postprocess.py    # 标点 / ITN / 繁简
├── session.py        # 会话状态机
├── server.py         # WebSocket 服务
└── cli.py            # 文件转写命令
configs/app.yaml
tests/unit/
tests/integration/
```

核心接口：

```python
class ASRAdapter(Protocol):
    def transcribe(self, pcm: bytes, sample_rate: int = 16000) -> ASRResult: ...

@dataclass
class ASRResult:
    text: str
    start_ms: int
    end_ms: int
```

---

## 7. 接口协议

**客户端 → 服务端**

| 类型 | 载荷 |
| --- | --- |
| `start` | `{"type":"start","sample_rate":16000,"format":"pcm_s16le"}` |
| `audio` | 二进制 PCM（20ms = 640B） |
| `stop` | `{"type":"stop"}` |

**服务端 → 客户端**

| 类型 | 载荷 |
| --- | --- |
| `ready` | `{"type":"ready","session_id":"..."}` |
| `final` | `{"type":"final","segment_id":1,"text":"...","start_ms":0,"end_ms":3200}` |
| `error` | `{"type":"error","code":"ASR_FAILED","message":"..."}` |

CLI：

```bash
python -m firered_poc.cli transcribe --audio test.wav
```

---

## 8. 配置示例

```yaml
server:
  host: 0.0.0.0
  port: 8000

audio:
  sample_rate: 16000
  frame_ms: 20

vad:
  backend: silero            # silero | energy
  energy_threshold: 0.02
  silero_model: models/silero_vad.onnx
  silero_threshold: 0.5
  silero_min_silence_ms: 500
  silero_min_speech_ms: 250
  silero_max_speech_ms: 20000
  silero_window_size: 512
  pre_roll_ms: 300
  post_roll_ms: 300
  max_end_silence_ms: 450
  min_speech_ms: 250
  hard_max_segment_ms: 15000
  merge_gap_ms: 1200        # 相邻句段间隔 ≤ 此值时合并（仅文件模式）

postprocess:
  punctuation: true
  punctuation_model: models/sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8/model.int8.onnx
  itn: true
  output_script: simplified  # as-is | simplified | traditional

asr:
  backend: firered_aed       # firered_aed（默认）| firered_ctc（快速）
  model: ""
  tokens: models/sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26/tokens.txt
  encoder: models/sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26/encoder.int8.onnx
  decoder: models/sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26/decoder.int8.onnx
  num_threads: 2
  provider: cpu
```

---

## 9. 验收标准

1. **真实转写**：用模型自带 `test_wavs` 的中文、粤语、英文样例，实际输出非空且与参考文本接近。
2. **端到端**：WAV CLI 与 WS 两条链路都能返回 `final` 文本。
3. **延迟记录**：记录 10s 音频的单句推理耗时与 WS 端到端耗时（POC 目标 < 2s）。
4. **质量门禁**：`ruff check .` 与 `pytest` 实际通过；报告存本机临时目录，不入库。
5. **可复现**：README/POC 文档给出一条可复制的转写命令与输出样例。

### 9.1 实测结果（本地 CPU，2026-11-26）

| 样例 | 内容 | 结果 | 耗时 |
| --- | --- | --- | --- |
| `test_wavs/0.wav`（中英混说） | 整段 | `昨天是MONDAY TODAY IS礼拜二，THE DAY AFTER TOMORROW是星期三。` | 2.8s |
| `test_wavs/0.wav`（VAD + merge） | 1 段 | `昨天是MONDAY TODAY IS礼拜二，THE DAY AFTER TOMORROW是星期三。` | 2.8s |
| `test_wavs/1.wav`（普通话） | 整段 | `这是第一种。第二种叫呃与ALWAYS ALWAYS什么意思啊？` | 1.35s |
| `test_wavs/3-sichuan.wav`（四川话） | 整段 | `自己就是在那个在那个就是在情节里面，就是感觉戏演的特别好，就是好像很真实一样，你知道吧？` | 2.57s |
| `yue.wav`（粤语） | 整段 | `呢几个字都表达唔到我想讲嘅意思。` | 1.30s |
| `hello_en.wav`（英文） | 整段 | `HELLO SPEECH.` | 0.55s |
| `test_wavs/0.wav`（WS 流式） | 2 段 | 2 条 `final`：`昨天是MONDAY。` / `TODAY IS礼拜二。THE DAY AFTER TOMORROW是星期三。` | 2.24s |

> 质量门禁：`ruff check .` PASS；`pytest` 28 passed（含真实模型、Silero VAD、后处理与 WebSocket 冒烟测试）。
> 结论：AED 默认下三语与混说均可出字；Silero VAD + 句段合并减少碎句；标点/ITN/繁简显著提升可读性。

### 9.2 AED vs CTC 同集对比

| 音频 | CTC（1.75 / 0.87 / 1.34 / 0.90 / 0.41s） | AED（2.76 / 1.35 / 2.57 / 1.30 / 0.55s） | 结论 |
| --- | --- | --- | --- |
| `0.wav` 中英混说 | `MOAY TOAY ... 礼拜八二 ... THE DAYAY` | `MONDAY TODAY ... 礼拜二 ... THE DAY AFTER` | **AED 明显更好** |
| `1.wav` 普通话 | `ALWAYSISE ALWAYS` | `ALWAYS ALWAYS` | AED 更好 |
| `3-sichuan.wav` 四川话 | `是演的特别好` | `戏演的特别好` | 接近，AED 更自然 |
| `yue.wav` 粤语 | `呢几个字都表达唔到我想讲嘅意思。` | 同左 | 持平 |
| `hello_en.wav` 英文 | `HELLO SPEECH.` | 同左 | 持平 |

> 决策：**POC 默认切到 AED**（精度优先）；CTC 保留为 `configs/app_ctc.yaml` 快速模式。AED 在 CPU 上仍快于实时（RTF ≈ 0.25~0.33）。

---

## 10. 里程碑

| 阶段 | 内容 | 预估 |
| --- | --- | --- |
| P0 | 安装 sherpa-onnx、下载模型、CLI 单档转写跑通 | 0.5 天 |
| P1 | Segmenter + WebSocket + 单元测试 | 1 天 |
| P2 | 演示样例、检查报告、进度同步 | 0.5 天 |

---

## 11. 风险与限制

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| CPU 推理慢 | 延迟高于生产 | POC 只验证可行性；生产换 GPU + AED/LLM |
| ITN 策略保守 | 仅转换日期/金额/百分比 | 未匹配的数字保持原文，避免误改 |
| 标点模型 73MB | 首次启动与内存开销 | 可关闭 `postprocess.punctuation` |
| 能量 VAD 对噪声不稳 | 切分不准 | 默认已切 Silero VAD，保留能量 VAD 兜底 |
| 自然停顿被切成多句 | 上下文丢失、文本碎片化 | `merge_gap_ms`（默认 1200ms，文件模式） |
| 模型下载约 600MB | 首次启动慢 | `download_model.sh` 预下载到 `models/`，已 gitignore |
| 粤语/英语样例覆盖不全 | 三语验证不足 | 确认 `test_wavs` 覆盖，必要时补样例 |
| CTC 与正式 AED 有差异 | 精度结论不能直接外推 | POC 已默认 AED；CTC 仅作快速备选 |

---

## 12. 默认决策

1. POC 默认后端：**sherpa-onnx FireRedASR2-AED-int8**；`configs/app_ctc.yaml` 为快速模式。
2. 入口顺序：**先 WAV CLI，再 WebSocket**。
3. VAD：**Silero VAD 默认**，能量 VAD 保留兜底；文件模式合并 ≤1200ms 的相邻句段。
4. 后处理：**标点 + 保守 ITN + OpenCC 繁简**，默认输出简体。
5. 失败策略：**单引擎重试一次 → error**，不引入 FunASR。

---

## 13. 运行方式（已验证）

安装依赖并下载模型（AED + CTC + Silero VAD + 标点，约 1.3GB）：

```bash
python3 -m pip install --user -r requirements.txt
./scripts/download_model.sh
```

WAV 文件转写（默认 AED）：

```bash
PYTHONPATH=src python3 -m firered_poc.cli transcribe \
  --audio models/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25/test_wavs/0.wav \
  --config configs/app.yaml --json
```

快速 CTC 模式：

```bash
PYTHONPATH=src python3 -m firered_poc.cli transcribe \
  --audio models/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25/test_wavs/0.wav \
  --config configs/app_ctc.yaml --json
```

需要按句切分时加 `--vad`（默认合并 ≤1200ms 的相邻句段）：

```bash
PYTHONPATH=src python3 -m firered_poc.cli transcribe \
  --audio /path/to/long.wav --config configs/app.yaml --vad --json
```

如需关闭合并或调整阈值：

```bash
PYTHONPATH=src python3 -m firered_poc.cli transcribe \
  --audio /path/to/long.wav --config configs/app.yaml --vad --merge-gap-ms -1
```

启动 WebSocket 服务：

```bash
PYTHONPATH=src python3 -m firered_poc.server --config configs/app.yaml
```

启动横幅会打印本机与 LAN 的 WebSocket/健康检查地址；前后端不同机时，录音器填横幅中的 LAN 地址。
桌面录音器的源码运行、Windows exe、跨机器部署见 [`docs/RECORDER.md`](RECORDER.md) 与 [`README.md`](../README.md)。

健康检查：`GET /health`；串流端点：`ws://127.0.0.1:8000/ws`。
发送 `start` → 二进制 20ms PCM → `stop`，接收 `final`。

AED vs CTC 对比：

```bash
PYTHONPATH=src python3 scripts/compare_backends.py \
  --wavs models/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25/test_wavs/0.wav
```

质量门禁：

```bash
ruff check .
python3 -m pytest
```
