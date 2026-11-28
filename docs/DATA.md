# 对话数据采集与标注规范

> 版本：v1.0
> 目标：为**个人语言输入**与**会议全文转写**建立可复现、可评测、无说话人区分的内部数据规范。

---

## 1. 范围

本项目只做句子级、非流式、句尾出字；不做 `partial`，不做说话人区分，不做会议摘要/待办。

| 场景 | 输入 | 输出 | 说话人 |
| --- | --- | --- | --- |
| 个人语言输入 | 单人、近场、句尾 | 单句文本 + 标点/ITN | 单人 |
| 会议全文 | 多人、远场、整场 | 全文转写 | 不区分 |

> 公开集（MCE、WSYue、SpiCE）只做代理/回归，不作为验收集。

---

## 2. 通用录音要求

- 格式：**16kHz / 16bit / mono PCM WAV**
- 电平：峰值不超过 `-1 dBFS`，避免削波；底噪稳定
- 句首/句尾各留 200ms 静音；不要人为剪掉换气/填充词
- 录音环境需记录：`quiet`（安静）或 `office`（办公室）
- 设备需记录：`headset`（耳麦）、`phone`（手机/话机）、`far_field`（会议远场）
- 每个文件只含一个场景、一个 session 或一条 utterance
- 文件命名只使用 ASCII：`[a-z0-9_]+\.wav`

---

## 3. 个人语言输入

### 3.1 规模

- 10 位说话人，每人 20–30 条，共 **200–300 条**
- 每条 3–15s，避免过长
- 任务分布：
  - `email`：写邮件/消息
  - `notes`：记笔记/待办
  - `chat`：聊天/回复
  - `schedule`：日程/预约
- 环境：`quiet` 与 `office` 各半；`headset` 与 `phone` 各半

### 3.2 内容要求

- 必须包含粤语/普通话/英文混说，英文保留拉丁
- 覆盖：人名、日期、时间、金额、地址、产品/项目名、缩写
- 转写为**逐字文本**，保留英文、数字、标点；不要改写语法
- 每条至少 1 个英文词；不要整句纯英文或纯中文

### 3.3 目录与 manifest

```text
dictation/
├── manifest.json
└── audio/
    ├── dict_0001.wav
    └── ...
```

`manifest.json` 是数组：

```json
[
  {
    "id": "dict_0001",
    "audio": "audio/dict_0001.wav",
    "duration_s": 6.24,
    "sample_rate": 16000,
    "speaker_id": "spk01",
    "environment": "quiet",
    "device": "headset",
    "task": "email",
    "transcript": "聽日下晝三點同Alice開會，記得帶laptop。",
    "english_terms": ["Alice", "laptop"],
    "split": "train"
  }
]
```

字段约束：

| 字段 | 约束 |
| --- | --- |
| `id` | 全局唯一 |
| `speaker_id` | 同一人跨 split 不得复用 |
| `split` | `train` / `dev` / `test` |
| `duration_s` | 与实际音频误差 ≤ 0.05s |
| `english_terms` | 可选；用于错误分析，不参与训练 |

### 3.4 划分

- 按 **speaker** 划分，禁止同一说话人跨 split
- 建议 7 人 train、1 人 dev、2 人 test
- 每个 split 覆盖所有任务/环境/设备，避免偏差

---

## 4. 会议全文转写

### 4.1 规模

- 5–10 场，每场 20–30 分钟
- 3–5 人，允许自然重叠
- 录音：单麦远场为主，另加 1–2 场耳麦会议作为对照
- 不标 speaker，不做 diarization

### 4.2 内容要求

- 真实会议或角色扮演会议；需参会人授权
- 主题覆盖：项目进度、需求评审、排期、复盘、销售/客户会议
- 转写按**句段**切分，保留时间戳；允许一个句段跨说话人切换
- 重叠段必须标记 `overlap: true`
- 噪声/笑声标记 `noise: true` / `laugh: true`
- 不要求区分谁说的；不要把不同说话人强行拆成多个 speaker 字段

### 4.3 目录与 manifest

```text
meeting/
├── manifest.json
├── audio/
│   └── mtg_001.wav
└── transcripts/
    └── mtg_001.jsonl
```

`manifest.json` 是数组：

```json
[
  {
    "session_id": "mtg_001",
    "audio": "audio/mtg_001.wav",
    "transcript": "transcripts/mtg_001.jsonl",
    "duration_s": 1500.0,
    "sample_rate": 16000,
    "participants": 4,
    "environment": "office",
    "device": "far_field",
    "split": "test"
  }
]
```

`transcripts/*.jsonl` 每行一个句段：

```json
{"session_id":"mtg_001","segment_id":"s0001","start_ms":1200,"end_ms":5400,"text":"我哋下個sprint會focus喺payment同login。","english_terms":["sprint","focus","payment","login"],"overlap":false,"noise":false}
```

字段约束：

| 字段 | 约束 |
| --- | --- |
| `session_id` | 全局唯一 |
| `segment_id` | session 内唯一 |
| `start_ms` / `end_ms` | 单调、在音频时长内、`start < end` |
| `text` | 非空；英文保留拉丁 |
| `overlap` | 多人同时说话时为 `true` |
| `split` | 按 session 划分，禁止同场跨 split |

### 4.4 划分

- 按 **session** 划分，禁止同一会议跨 split
- 至少 2 场 test、1 场 dev；train 仅在需要域内 LM 时使用

---

## 5. 评测口径

### 5.1 个人听写

- 单句混合 CER：中文按字、英文按词
- 英文词 P/R/F1（token 边界）
- 标点/ITN 抽检
- 句尾延迟、空结果率
- 按 `task` / `environment` / `device` 分桶

### 5.2 会议全文

- 全文混合 CER、英文词 F1（拼接所有句段）
- 漏句/重复率（按参考句段时间对齐）
- 切分错误：一句切两段、多句并一段
- 重叠段单独统计；噪声段单独统计
- 长音频端到端延迟/超时

> 不做 speaker-attributed WER，不做摘要/待办评测。

---

## 6. 隐私与授权

- 个人听写：使用自录或明确授权的样本；避免真实密码、身份证号、完整住址
- 会议：参会人书面/电子授权；可脱敏人名/客户名，但需保持可读
- 数据入库前做重复检测；test 集不得出现在任何训练/LM 语料中
- 公开集授权：MCE 仅研究；WSYue CC BY-NC 4.0；SpiCE CC BY 4.0

---

## 7. 校验

```bash
python3 scripts/validate_eval_data.py --kind dictation --root data/dictation
python3 scripts/validate_eval_data.py --kind meeting --root data/meeting
```

校验内容：

- WAV 是否为 16kHz/16bit/mono
- 音频/转写文件是否存在
- ID、时间戳、split 是否合法
- speaker（个人）/session（会议）是否跨 split 泄漏
- 时长与 manifest 是否一致

---

## 8. 优先级

1. 个人听写 pilot：100–200 条，先验证近场混说与句尾出字。
2. 会议 pilot：3 场，先看远场、重叠、长音频退化。
3. 数据稳定后再考虑域内 LM；热词等业务词表确定后再做。
