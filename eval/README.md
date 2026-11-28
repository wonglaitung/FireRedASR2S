# 验证集套件

> 版本：v1.5
> 用途：AED-only 优化前后对比；不是官方 benchmark，也不代表生产分布。

## 1. 四个子集

| 子集 | 数量 | 总时长 | 内容 | 来源 | 授权 |
| --- | --- | --- | --- | --- | --- |
| `eval/yue/` | 20 | 81.64s | 纯粤语（词典例句/短句） | `AlienKevin/wordshk_cantonese_speech` | CC BY 4.0 |
| `eval/en/` | 20 | 153.94s | 纯英文（朗读，7 位说话人） | `openslr/librispeech_asr` validation.clean | CC BY 4.0 |
| `eval/yue_en/` | 100 | 785.58s | 粤英混说（日常主题，含英文词/短语） | MCE / `AlienKevin/mixed_cantonese_and_english_speech` | 仅研究，商用需授权 |
| `eval/yue_en_spont/` | 153 | 971.76s | 自發/多领域粤英混说 | WSYue-ASR-eval Short / `ASLP-lab/WSYue-ASR-eval` | CC BY-NC 4.0 |

所有音频已转为 **16kHz / 16bit / mono WAV**。

## 2. 基线对比

| 引擎 | 环境 | `yue` CER | `en` WER | `yue_en` F1 | `yue_en` 混合 CER |
| --- | --- | --- | --- | --- | --- |
| sherpa int8 greedy | CPU | 11.5% | 1.1% | 84.3% | 7.2% |
| 官方 AED PyTorch | RTX 4090，BF16，beam10 | **4.7%** | **0.9%** | **87.4%**（P 88.7 / R 86.1） | **6.5%** |
| 官方 AED + n-best LM | RTX 4090，BF16，beam10 | **4.7%** | **0.9%** | **88.4%**（P 90.1 / R 86.9） | **6.0%** |

逐条结果：`eval/baseline_aed.json`（sherpa）、`eval/baseline_official_aed.json`（官方 1-best）、`eval/baseline_official_lm.json`（官方 + LM）。

> 官方 AED 使用 `configs/app_official.yaml`；模型/代码缓存见 `scripts/setup_official_aed.sh`。混说 LM 由 `scripts/build_mce_lm.py` 构建，训练时排除 100 条评估集。
>
> 原 20 条子集不是独立测试集，且偏容易；用 20 条会得到偏乐观的 95.4%，请以 100 条结果为准。

### 自發 WSYue 153 条

| 引擎 | 英文词 F1 | 混合 CER |
| --- | --- | --- |
| 官方 AED 1-best | **71.5%**（P 72.4 / R 70.6） | **10.1%** |
| 官方 AED + MCE LM | 70.5%（P 72.9 / R 68.2） | 10.2% |

结论：MCE LM 在自發域**退化**，当前不应默认套用；LM 需要域内数据或按场景开关。

## 3. 指标定义

- **CER**：粤语参考/输出先转简体、只保留汉字，再算字符级编辑距离。
- **WER**：英文转小写、去标点、按空格分词，再算词级编辑距离。
- **英文词 P/R/F1**：按 token 边界匹配，参考/输出英文词（长度 ≥2 且含字母）逐个计数；不再用 substring。
- **混合 CER**：中文按字、英文按词作为单位，计算整句编辑距离。

## 4. 运行

```bash
PYTHONPATH=src python3 scripts/eval_suite.py \
  --config configs/app.yaml \
  --output eval/baseline_aed.json
```

跑自發集（不套 MCE LM，用 1-best 配置）：

```bash
PYTHONPATH=src python3 scripts/eval_suite.py \
  --config configs/app_official_1best.yaml \
  --sets yue_en_spont \
  --output eval/baseline_official_spont_1best.json
```

只跑粤英混说：

```bash
PYTHONPATH=src python3 scripts/eval_suite.py \
  --config configs/app.yaml \
  --sets yue_en \
  --output eval/baseline_mce100.json
```

## 5. 目录

```text
eval/
├── README.md
├── baseline_aed.json
├── yue/             # 纯粤语
├── en/              # 纯英文
├── yue_en/          # MCE 粤英混说（100）
└── yue_en_spont/    # WSYue 自發粤英混说（153）
```

每个子集都有 `manifest.tsv` / `manifest.json` 与 `audio/`。

## 6. 限制

- `yue`/`en`/`yue_en` 是朗读/半自發；`yue_en_spont` 是真实自發/多领域。
- `en` 是 native English（LibriSpeech），不是「香港口音英文」；不能单独代表港式英文。
- `yue` 来自词典例句，部分句子偏书面/释义。
- `yue_en` 来自 MCE train split，不是官方 held-out；仅内部回归。
- `yue_en_spont` 是 WSYue-ASR-eval Short 的 code-switch 子集，CC BY-NC 4.0，仅非商业用途。
- MCE 仅限研究；商用需先确认授权。
- 指标只覆盖 CER/WER/英文词 P/R/F1、混合 CER，不含语义、语序、幻觉率。
