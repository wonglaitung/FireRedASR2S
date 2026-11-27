# 验证集套件

> 版本：v1.0
> 用途：AED-only 优化前后对比；不是官方 benchmark，也不代表生产分布。

## 1. 三个子集

| 子集 | 数量 | 总时长 | 内容 | 来源 | 授权 |
| --- | --- | --- | --- | --- | --- |
| `eval/yue/` | 20 | 81.64s | 纯粤语（词典例句/短句） | `AlienKevin/wordshk_cantonese_speech` | CC BY 4.0 |
| `eval/en/` | 20 | 153.94s | 纯英文（朗读，7 位说话人） | `openslr/librispeech_asr` validation.clean | CC BY 4.0 |
| `eval/yue_en/` | 20 | 166.95s | 粤英混说（日常主题，含英文词/短语） | MCE / `AlienKevin/mixed_cantonese_and_english_speech` | 仅研究，商用需授权 |

所有音频已转为 **16kHz / 16bit / mono WAV**。

## 2. 基线（AED，本机 CPU）

| 子集 | 指标 | 结果 |
| --- | --- | --- |
| `yue` | CER（字符错误率） | **11.5%** |
| `en` | WER（词错误率） | **1.1%** |
| `yue_en` | 英文词召回 | **104 / 119 = 87.4%** |

详细逐条结果：`eval/baseline_aed.json`。

> 这是 `sherpa-onnx int8 + greedy` 的基线；换官方 AED + beam/LM 后应重新跑。

## 3. 指标定义

- **CER**：粤语参考/输出先转简体、只保留汉字，再算字符级编辑距离。
- **WER**：英文转小写、去标点、按空格分词，再算词级编辑距离。
- **英文词召回**：参考中的英文词（长度 ≥2）有多少在输出中以拉丁字符串出现。

## 4. 运行

```bash
PYTHONPATH=src python3 scripts/eval_suite.py \
  --config configs/app.yaml \
  --output eval/baseline_aed.json
```

只跑粤英混说：

```bash
PYTHONPATH=src python3 scripts/eval_yue_en.py \
  --config configs/app.yaml \
  --output eval/yue_en/baseline.json
```

## 5. 目录

```text
eval/
├── README.md
├── baseline_aed.json
├── yue/        # 纯粤语
├── en/         # 纯英文
└── yue_en/     # 粤英混说
```

每个子集都有 `manifest.tsv` / `manifest.json` 与 `audio/`。

## 6. 限制

- 三个子集都是**朗读/半自發**，不是自發港式對話。
- `en` 是 native English（LibriSpeech），不是「香港口音英文」；不能单独代表港式英文。
- `yue` 来自词典例句，部分句子偏书面/释义。
- `yue_en` 来自 MCE train split，不是官方 held-out；仅内部回归。
- MCE 仅限研究；商用需先确认授权。
- 指标只覆盖 CER/WER/英文召回，不含语义、语序、幻觉率。
