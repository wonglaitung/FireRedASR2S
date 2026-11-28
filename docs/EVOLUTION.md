# 技术演化：从第一版 POC 到场景化验证

> 版本：v1.0
> 目的：用“问题 → 改动 → 结果 → 经验”的方式，解释第一版 POC 之后发生了什么，便于没有语音背景的读者理解。

---

## 0. 一句话总结

第一版 POC 解决“**能不能把一句话转成字**”；后续解决“**测得准不准、模型选得对不对、数据是否可信、是否匹配真实场景**”。

```mermaid
flowchart LR
    A["第一版 POC<br/>跑通闭环"] --> B["删 CTC<br/>修评测"]
    B --> C["官方 AED<br/>GPU + beam"]
    C --> D["n-best + LM<br/>候选重打分"]
    D --> E["扩验证集<br/>20 → 100 → 153"]
    E --> F["场景数据规范<br/>个人听写 / 会议"]
```

---

## 1. 第一版 POC：先跑通闭环

第一版的目标不是最高精度，而是验证一条最小链路：

```text
麦克风 / WAV → WebSocket → VAD 切句 → ASR → 标点/ITN/繁简 → 文本
```

当时包含：

- `sherpa-onnx` 推理，支持 CTC 和 AED 两条路径
- Silero VAD（Voice Activity Detection，语音活动检测）
- 句段合并：把相邻短句合并，减少碎句
- CT-Transformer 标点、保守 ITN（Inverse Text Normalization，文本规范化）、OpenCC 繁简
- WAV CLI + WebSocket 后端
- PyQt6 桌面录音器
- Docker 单容器

这一版验证了：整句、非流式 ASR 可以在真实音频上稳定出字。

但也留下三个问题：

1. CTC 和 AED 两条路径让配置、模型、文档复杂。
2. 评测只看“英文有没有出现”，不可靠。
3. 用的是 sherpa int8 + greedy，精度不是上限。

---

## 2. 从“能跑”到“可比较”：删 CTC，修评测

### 2.1 为什么删 CTC

- CTC（Connectionist Temporal Classification）速度快，但精度通常低于 AED。
- 项目定位是精度优先、单引擎，不应保留两套后端。
- 保留 CTC 会让配置、下载脚本、Docker、文档都出现分叉。

所以直接删除 CTC：

- 删除 `configs/app_ctc.yaml`
- 删除 CTC 下载逻辑
- 删除 Adapter 里的 CTC 分支
- 删除后端对比脚本
- 文档只保留 AED

### 2.2 为什么先修评测

旧评测用 substring 判断英文词：

```text
IT 可能命中 with
app 可能命中 happy
```

这会高估召回率。于是改成：

- 英文按 token 边界匹配
- 增加 Precision / Recall / F1
- 增加混合 CER（Chinese Character Error Rate，混合字符错误率）：中文按字、英文按词一起算编辑距离
- 同时记录 raw ASR 和 postprocess 后文本

**经验：指标定义错了，优化方向就会错。先修尺子，再改模型。**

---

## 3. 从“可比较”到“更准”：官方 AED + GPU + beam

### 3.1 原路径的局限

原路径是：

- `sherpa-onnx` int8：8 位量化，快，但精度有损失
- greedy search：每步只选一个最可能的 token，不保留多条候选

### 3.2 改了什么

新增官方 `FireRedASR2-AED` PyTorch Adapter：

- BF16（16 位脑浮点，精度和显存折中）
- beam search（束搜索，同时保留多条候选路径）
- n-best（保留前 K 条完整候选）
- RTX 4090 GPU

同时保留 sherpa 路径，作为 CPU/轻量回归。

### 3.3 结果

| 引擎 | 粤语 CER | 英文 WER | 粤英 F1 | 混合 CER |
|---|---:|---:|---:|---:|
| sherpa int8 greedy | 11.5% | 1.1% | 87.8% | 6.8% |
| 官方 AED BF16 beam10 | **4.7%** | **0.9%** | **87.4%** | **6.5%** |

端到端：

- 8.78s 粤英混说音频约 **2.4s** 返回
- GPU 服务进程约 **3GB**
- 显存足够，但 Docker 还未切到官方 AED

**经验：音频模型不是“换个更大的模型”就完事；精度格式、解码方式、GPU/CPU 路径都会影响结果。**

---

## 4. 从“更准”到“选对候选”：n-best + LM

### 4.1 问题

官方 AED 的 1-best 仍会漏英文词，例如：

- `clothes → closer`
- `croissant → crescent`
- `food court → footcock`
- `sunscreen → screen`

但分析发现：正确词经常在 n-best 候选里，只是没被选为第 1 名。

### 4.2 改了什么

- 输出 n-best 候选
- 用 MCE train 文本训练轻量混说 n-gram LM（Language Model，语言模型）
- 训练时排除评估句，避免泄漏
- 用 `LM 分数 + 候选排名` 重新打分

### 4.3 结果

MCE 100 条：

| 方案 | 英文词 F1 | 混合 CER |
|---|---:|---:|
| 1-best | 87.4% | 6.5% |
| + n-best LM | **88.4%** | **6.0%** |

但关键问题是**域偏移**：

- 原 20 条子集：LM 能到 95.4%
- MCE 100 条：LM 88.4%
- WSYue 自發 153 条：LM 反而退化到 70.5%
- SwitchLingua 听写代理 100 条：LM 退化到 83.2%

**经验：LM 很强，但非常依赖训练域。MCE 上有效的 LM，不能默认套到真实对话/听写。**

---

## 5. 从“小集”到“可信数据”：扩验证集

最初 20 条混说集太容易，导致指标偏乐观。后来逐步增加：

| 数据 | 数量 | 性质 | 用途 |
|---|---:|---|---|
| 粤语 | 20 | 词典朗读 | 粤语回归 |
| 英文 | 20 | LibriSpeech | 英文回归 |
| MCE | 100 | 生成/半自發 | 混说回归 |
| WSYue | 153 | 真实自發短视频/访谈 | 自發压力测试 |
| SwitchLingua | 100 | 生成/朗读 | 个人听写代理 |

当前结果：

| 数据 | 官方 AED 1-best | MCE LM |
|---|---:|---:|
| MCE 100 | 87.4% / 6.5% | **88.4% / 6.0%** |
| WSYue 153 | **71.5% / 10.1%** | 70.5% / 10.2% |
| SwitchLingua 100 | **88.5% / 6.6%** | 83.2% / 9.4% |

**经验：数据域比模型参数更决定结果。朗读、自發、对话、听写是不同分布，不能混着宣称“准确率”。**

---

## 6. 为两个真实场景做准备

确认的场景是：

1. **个人语言输入**：单人、近场、句尾出字
2. **会议全文**：多人、远场、只出全文，不区分说话人

因此当前明确不做：

- 不做 partial（边说边出字）
- 不做 diarization（说话人分离）
- 不做摘要/待办
- 不做 LLM rerank、微调
- 热词等有业务词表后再做

为此新增 `docs/DATA.md` 和 `scripts/validate_eval_data.py`：

- 个人听写：10 人、200–300 条、任务/环境/设备
- 会议：5–10 场、3–5 人、单麦远场、全文转写
- 录音格式、manifest、split 防泄漏、隐私授权、校验规则

---

## 7. 当前系统状态

| 项目 | 状态 |
|---|---|
| CTC | 已删除，只保留 AED |
| 官方 AED | 已接入，BF16 + beam10 |
| n-best LM | 已接入，但只适合 MCE 域 |
| sherpa | 保留为 CPU/轻量路径 |
| server/recorder | 端到端跑通 |
| Docker | 仍是 sherpa 路径 |
| 真实个人听写 | 尚未采集 |
| 真实会议 | 尚未采集 |
| 热词 | 未做 |
| LLM/微调 | 按需求不做 |
| 质量门禁 | `ruff` PASS，`pytest` 53 passed |

---

## 8. 想读代码，建议顺序

1. `src/firered_poc/server.py`：WebSocket 后端入口
2. `src/firered_poc/cli.py`：WAV 文件入口
3. `src/firered_poc/vad.py` / `segmenter.py`：切句
4. `src/firered_poc/asr/sherpa.py`：CPU/ONNX 路径
5. `src/firered_poc/asr/official.py`：官方 AED + n-best
6. `src/firered_poc/lm.py`：混说 LM
7. `src/firered_poc/postprocess.py`：标点/ITN/繁简
8. `scripts/eval_suite.py`：三/多套验证集评测
9. `docs/DATA.md`：个人听写/会议数据规范

---

## 9. 下一步

真正的分水岭不是再换模型，而是**采到真实的个人听写数据**：

1. 自录 100–200 条个人听写
2. 跑 `validate_eval_data.py`
3. 用官方 AED 1-best 跑基线
4. 会议按计划之后再做

---

## 10. 核心经验

1. **先修评测，再改模型。**
2. **数据域比模型大小更决定结果。**
3. **n-best 只有在有合适 LM/上下文时才有用。**
4. **端到端延迟和显存要单独测，不能只看 CER。**
5. **不要用 20 条小集下结论。**
6. **场景没定之前，不做热词；没有真实数据之前，不承诺生产准确率。**
