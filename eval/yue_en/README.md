# 粵英混說驗證集（20 條）

> 版本：v1.2
> 用途：本項目內部的**粵英混說回歸驗證集**，不是官方 benchmark，也不代表生產分佈。

---

## 1. 內容

```text
eval/yue_en/
├── README.md
├── manifest.tsv          # 人可讀清單
├── manifest.json         # 評測腳本使用
├── baseline.tsv          # AED 基線輸出
├── baseline.json
└── audio/
    ├── yue_en_001.wav
    └── ... yue_en_020.wav
```

- 20 條音頻，總時長約 **166.95 秒**
- 16kHz / 16bit / mono WAV
- 主題：天氣、食物、旅遊、娛樂、體育、本地時事、購物、學習、工作
- 每條都包含粵語語法 + 英文詞/短語（句首、句中、句尾、英文標題、多詞英文段）

`manifest.tsv` 欄位：

| 欄位 | 說明 |
| --- | --- |
| `id` | 001~020 |
| `source` | 資料集名稱 |
| `source_index` | 原始資料集 row index |
| `topic` | 主題 |
| `duration_s` | 時長 |
| `sample_rate` | 採樣率 |
| `audio` | 相對路徑 |
| `transcript` | 參考轉寫（英文保留拉丁） |
| `english_terms` | 英文詞列表 |

---

## 2. 來源與授權

- 來源：HuggingFace [`AlienKevin/mixed_cantonese_and_english_speech`](https://huggingface.co/datasets/AlienKevin/mixed_cantonese_and_english_speech)
- 上游：MCE（Mixed Cantonese and English）資料集 / [`Shelton1013/Whisper_MCE`](https://github.com/Shelton1013/Whisper_MCE)
- 本驗證集從該資料集抽取 20 條，保留原始 row index，方便回溯。

> **MCE 標註僅限研究用途，商用需取得作者授權。**  
> 本目錄音頻僅供本項目內部研究與回歸測試；若倉庫需要公開分發或商用，請先確認授權，或刪除 `audio/` 只保留 manifest 與下載腳本。

---

## 3. 基線結果（本機 CPU）

| 指標 | 結果 |
| --- | --- |
| AED（`configs/app.yaml`） | **F1 87.8%**（P 88.1% / R 87.4%） |
| 混合 CER | **6.8%** |

- 英文詞 P/R/F1：按 token 邊界匹配，長度 ≥2 且含字母；不再用 substring。
- 混合 CER：中文按字、英文按詞計編輯距離。
- P/R/F1 與混合 CER 一起看，避免「多吐英文」推高召回。
- 詳細輸出：`baseline.tsv` / `baseline.json`。

觀察：

- AED 在多數句子能保留英文；錯誤多為英文拼錯或替換，例如：
  - `clothes` → `CLOSER`
  - `countdown` → `COUNT STYLE`
  - `boutique` → `补贴`
  - `croissant` → `CROSSING`

> 這批資料偏**朗讀/半自發**，且全部來自原資料集的 train split。  
> 它適合做內部回歸，不適合宣稱「官方測試集」或直接外推生產準確率。

---

## 4. 如何跑

```bash
PYTHONPATH=src python3 scripts/eval_yue_en.py \
  --config configs/app.yaml \
  --output eval/yue_en/baseline.json
```

腳本會逐條輸出英文詞命中，最後打印總召回。完整三套驗證集見 [`eval/README.md`](../README.md)。

---

## 5. 限制

- 不是自發對話；口音、語速、停頓與真實港式粵英仍有差距。
- 沒有官方 held-out split；所有樣本來自 train split。
- 只衡量英文詞是否保留，不衡量粵語 CER、語序、語義。
- 英文借詞（如 `bus` → `巴士`）不應強行算錯；本集已尽量選擇需要保留拉丁的詞。
- 若用於正式評測，建議再補 SpiCE / 自錄自發粵英對話，並人工校對轉寫。
