# EuroSCORE II Automation (NCKUH)

成大醫院心臟內科導管病人 EuroSCORE II 自動化評估工具。

## 功能

- 使用 Nashef 2012 EJCTS 原文 Table 6 完整係數計算 EuroSCORE II
- 從 NCKUH Web EMR 自動抓取病人 demographics / Cr / 體重 / 心超 / 用藥
- 用 LLM (gemini) 解析 EMR 文字，主 agent 判讀共病
- 對照 MDCalc 表單樣式輸出分層 cheatsheet
- 寫回 Excel 工作表（每位病人獨立評估區塊）

## 架構

```
fetch_patient.py        Python requests 從 EMR 抓 docs（不用瀏覽器）
                            ↓
gemini CLI + gemini_prompt.md
                            ↓ (gemini 解析 demographics/Cr/order)
人工判讀 AD/DC（共病、critical preop、recent MI）
                            ↓
_emr_raw/<chart>.yaml   每位病人輸入
                            ↓
euroscore_ii.py + cheatsheet.py
                            ↓ (Nashef 2012 公式 + MDCalc 樣式)
write_to_excel.py       寫回主工作簿
```

## 檔案

| 檔案 | 用途 |
|---|---|
| `euroscore_ii.py` | Nashef 2012 完整係數 + Cockcroft-Gault + renal_category |
| `cheatsheet.py` | YAML → MDCalc 分層 cheatsheet + diff vs manual |
| `fetch_patient.py` | Python requests 抓 EMR docs |
| `generate_euroscore_sheet.py` | 建立 Excel 評估表（含 21 input 欄）|
| `write_to_excel.py` | 把分數寫回主表 + block |
| `_emr_raw/gemini_prompt.md` | gemini 解析 schema |

## 安裝

```bash
pip install -r requirements.txt
```

需要：
- Python 3.10+
- gemini CLI (`npm install -g @google/gemini-cli`) — 雜活解析用
- 院內 EMR session (URL 含 session ID，數小時過期)

## 使用流程

對每位病人：

1. **Browser 切換 chart**（Chrome / 任何能登 EMR 的瀏覽器）
2. **找 medicalsn**：leftFrame `Discharge Note(*)` anchor 中的 `medicalsn=I...`
3. **Python 抓 docs**：
   ```bash
   python fetch_patient.py <SESSION_ID> <CHART_NO> <SN>
   ```
4. **gemini 解析**：
   ```bash
   cat _emr_raw/gemini_prompt.md _emr_raw/<CHART>_raw.txt > _emr_raw/_gemini_input.txt
   gemini -p "Extract YAML per schema. Use age = 入院年度 - 出生年度." < _emr_raw/_gemini_input.txt
   ```
5. **人工讀 AD/DC** 判讀共病（critical preop / ECA / previous cardiac surgery / recent MI）
6. **寫 YAML** 到 `_emr_raw/<CHART>.yaml`
7. **算分**：
   ```bash
   python cheatsheet.py _emr_raw/<CHART>.yaml
   ```
8. **批次寫回 Excel**：
   ```bash
   python write_to_excel.py
   ```

## EuroSCORE II 規則

詳細係數見 `euroscore_ii.py`，重點規則：

1. **Age**: 入院年度 − 出生年度（calendar year subtraction）
2. **NYHA**: default I (β=0)
3. **Poor mobility**: default N. AD "independent" → N
4. **CCS class 4**: default N. 只有當 PI 明確「無法做任何活動」才 Y
5. **Renal**: HD/ESRD/dialysis → dialysis；否則 Cockcroft-Gault：
   - CC > 85 → normal
   - CC 50-85 → moderate
   - CC ≤ 50 → severe
   - eGFR 僅供參考，不用於分級
6. **No echo**: LV=good, PHT=none
7. **Operation defaults** (cath 病人)：urgency=elective, weight=isolated_cabg, thoracic_aorta=N
8. **Critical preop**: 自己讀 AD+DC 判讀。Y if IABP/ECMO/shock/acute resp failure/decomp HF/preop inotropes/VT-VF/preop ventilation/acute renal failure
9. **ECA**: strict 定義 — 光是 absent pulse 或 bruit 不算
10. **Previous cardiac surgery**: 任何開心包的手術都算（含主動脈根部/弓部置換）

## 隱私

- `.gitignore` 排除所有 `*.xlsx`、`_emr_raw/`、`HANDOFF.md`
- 病人資料**永不**進入 git
- EMR URL 為院內網址，外部無法存取

## 參考

Nashef SAM, Roques F, Sharples LD, et al. EuroSCORE II. Eur J Cardiothorac Surg 2012;41:734-745. doi:10.1093/ejcts/ezs043
