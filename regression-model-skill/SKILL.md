---
name: regression-model-skill
description: 以繁體中文協助分析 CSV／Excel 資料的迴歸模型：依樣本量（n/p、殘差自由度、較少類別筆數 n_min）、VIF、資料特性與研究目的推薦 Linear、Polynomial、Logistic、Ridge、Lasso 或懲罰式 Logistic；完成離群候選檢查、經確認的前處理、EDA、假設診斷、必要時的 Box–Cox，並以 AIC 選模，交付 Quarto 原始檔 report.qmd 與 report.pdf，報告末附完整 Python 分析程式碼。
---

# 迴歸模型互動式分析

## 任務與交付範圍

依研究問題、資料特性及使用者同意的方案，完成資料檢查、模型推薦、假設診斷、AIC 選模、估計與結果解讀。

最終只交付兩個檔案：
- `report.qmd`：可獨立渲染的 Quarto 原始檔。完整分析程式直接寫在 qmd 裡，渲染時當場執行並產生全部圖表與表格。
- `report.pdf`：由同一份 `report.qmd` 渲染而成。

`report.qmd` 不得引用任何外部的圖檔、程式檔或其他檔案。唯一的外部輸入是使用者自己的資料檔（CSV／Excel）：只要把 `report.qmd` 和資料檔放在同一個資料夾，執行 `quarto render report.qmd` 就能重新產生 PDF。

報告最後附完整 Python 分析程式碼，與 qmd 開頭隱藏執行的程式完全相同。這份程式只重現數值、表格與圖表，本身不產生 qmd 或 pdf。

不另外交付 Python 檔、模型檔、依賴鎖定檔或 ZIP。執行過程中可使用暫存檔。分析過程中在對話裡展示的圖檔（見「在對話中展示圖表」）是給使用者檢視的證據，必須展示，不算額外交付。

## 參考資料與優先順序

依工作階段查閱下列檔案，只讀取當前需要的部分：

| 檔案 | 用途 | 何時讀 |
|---|---|---|
| [references/decision-tree.md](references/decision-tree.md)（圖：`decision-tree.png`） | 完整互動流程：確認、前處理、診斷、Box–Cox、AIC | 開始分析前 |
| [references/report-spec.md](references/report-spec.md) | 報告章節、圖表、重現合約 | 製作報告前 |
| [references/textbook method.md](<references/textbook method.md>) | 五種方法的符號、前提、模型、VIF 與係數解讀 | 推薦模型、撰寫方法與解讀時 |
| `references/linear_models_math_textbook.qmd`／`.html` | 同一份教材的 Quarto 原始檔與網頁版 | 需要公式原文或排版範例時 |
| [assets/report_template.qmd](assets/report_template.qmd) | 報告範本：跨平台字型 YAML、隱藏分析區塊、圖表輔助函式用法、章節骨架 | 撰寫報告時（必用） |
| `scripts/build_qmd.py` | 把設定好的分析程式填入草稿，產生可獨立渲染的 report.qmd | 撰寫報告後、渲染前 |

參考資料提供方法依據，但不代表使用者已同意執行其中所有程序。

**本檔與參考資料不一致時，以本檔為準。** 具體的覆蓋項目如下：

1. **報告附的程式**：只須重現數值與圖表，不須產生 `report.qmd` 與 `report.pdf`。報告的重現方式是「qmd 渲染時執行同一份程式」。這一項覆蓋 report-spec「重現合約」中的對應要求。
2. **前處理確認方式**：先列出整份方案，使用者有異議的項目再逐項討論。
3. **隨機種子**：固定為 42，記入報告，不詢問使用者。
4. **樣本量與 VIF 的推薦規則**：以本檔「三、模型推薦規則」為準。
5. **依賴版本**：寫在報告附錄中，不另交鎖定檔。

使用者在對話中提出的明確要求，又優先於本檔。

## 工具腳本

`scripts/run_regression.py` 依 `--action` 執行各步驟，結果印成表格，並把 CSV、JSON 與圖檔存到 `--output/<步驟>/`。腳本本身不產生報告。

| action | 用途 | 是否需要使用者確認 |
|---|---|---|
| `inspect` | 資料摘要、缺失比例、前處理建議、二元 Y 類別筆數、資料 SHA-256 | 否 |
| `outliers` | 前處理前的 IQR 離群候選、箱形圖、散布圖 | 否（只標示） |
| `eda` | 套用已確認的前處理，產出描述統計與 EDA 圖 | 須 `--confirm-preprocessing` |
| `recommend` | 推薦規則：n、p、秩、n/p、殘差自由度、n_min/p、VIF、預設搜尋範圍 | 須 `--confirm-preprocessing` |
| `fit` | 擬合指定模型，產出係數、假設診斷或混淆矩陣 | 模型須經使用者同意 |
| `boxcox` | 以剖面概似（含 Jacobian）估計 lambda_BC | 執行與套用都須同意 |
| `aic` | 在相同觀測值上比較候選模型的 AIC | 須 `--confirm-search` |
| `all` | 依已確認的方案一次重現全部數值與圖表 | 報告附程式時使用 |

常用參數：
- 資料與變數：`--data`、`--target`、`--features`、`--id-col`、`--y-type`、`--positive`。
- 前處理：`--drop-features`、`--keep-high-missing`、`--categorical`、`--categorical-missing`、`--drop-missing-y`、`--exclude-rows`。
- 模型：`--model`、`--degree`、`--interaction`、`--lambda-reg`、`--lambda-bc`（`estimate` 或數值）、`--threshold`。
- AIC：`--candidates`、`--degrees`、`--ridge-lambdas`、`--lasso-lambdas`、`--aic-compare-untransformed`。

依賴見 `requirements.txt`，缺少 statsmodels 時先安裝。

腳本遇到下列情況會停止並報錯：路徑或欄位錯誤、前處理未確認、模型無法估計、未收斂、完全分離、秩不足，或完全配適使概似無法計算。遇到這些錯誤時，向使用者說明原因並依推薦規則提出替代方案，**不要自行改資料或改模型繞過**。

## 分析界線

### 可直接執行、不需詢問的檢查

- 原始筆數、有效筆數、缺失筆數、欄位型態、重複列、常數欄位。
- 展開後的參數數 p、設計矩陣秩、n/p、殘差自由度、二元 Y 的 n_min。
- 連續解釋變數之間的相關性，以及 VIF。
- IQR 離群候選值。
- 模型能否估計、是否收斂，以及 Logistic 是否分離。

這些檢查都不改動原始資料。

### 依流程執行的診斷

Linear 與 Polynomial 的假設診斷屬於本 Skill 的標準流程，包括殘差圖、Q–Q 圖、BP／White、DW／BG、Shapiro–Wilk／JB。檢定可呈現統計量與 p-value，以 0.05 作輔助判斷，但須遵守：
- 不把 p≥0.05 當成假設已成立。
- 不把「未偵測到自相關」當成完全獨立。
- DW 與 BG 只在資料順序有意義時解讀。

### 不自動加入的程序

下列程序只有在使用者另行要求時才執行：
- 係數的 p-value、信賴區間、預測區間、t／F 檢定。
- 穩健標準誤、Bootstrap。
- Cook's D、學生化殘差、槓桿值。
- 任何交叉驗證（K-fold、LOOCV、GCV、巢狀 CV）及訓練／測試切分。

不使用「顯著／不顯著」描述係數。不把關聯、非零係數、AIC 較小或配適良好當成因果證據。

## 互動原則

- 使用繁體中文，必要時附英文術語。
- 每則訊息只處理一個待決事項。整份前處理方案、整份 AIC 搜尋範圍各算一個待決事項。收到回答後才進入下一步。
- 使用者已主動提供或已同意的資訊直接沿用，不重複詢問。
- **不詢問的事項**：
  - 隨機種子：固定 42。
  - 分類閾值：預設 0.5，列在模型方案中供使用者修改，不另外發問。
- 可以直接檢查資料並提出推薦，但不得因此自行刪除資料、插補、排除變數、轉換 Y、改模型或擴大搜尋範圍。
- 使用者已要求成果報告時，分析完成後直接製作 qmd 與 pdf，不再為同一項交付另行確認。

## 在對話中展示圖表（必須遵守）

每個步驟產生的圖，都必須在當下顯示在對話中給使用者看，不能只用文字描述。例如不能只說「Q–Q 圖偏離常態」，卻沒有附上圖和對應的檢定數值。

**做法：**

1. 執行腳本時加 `--show-dir /mnt/user-data/outputs/figures`，每張圖會另存一份到該資料夾。腳本結束時會列出「本步驟產生的圖檔」清單。
2. 用 `view` 逐張看過圖，再下判斷。不憑想像或只憑檢定數值描述圖形。
3. 以檔案展示工具（claude.ai 用 `present_files`；Cowork 遠端用 `SendUserFile`）把該步驟清單中的**所有**圖檔一次展示給使用者。沒有檔案展示工具時，列出每張圖的完整路徑，並請使用者開啟查看。
4. 展示之後，再逐張寫出白話解讀。每段解讀都要指明是哪一張圖（檔名或圖標題），並附上支持該判讀的數值，例如 Shapiro–Wilk 統計量與 p-value、偏離 Q–Q 直線的是哪一段（尾端、中段）、大約幾個點。

**各步驟至少要展示的圖：**

| 步驟 | 必須展示的圖 |
|---|---|
| `outliers` | 前處理前的箱形圖、X 與 Y 散布圖（標出離群候選） |
| `eda` | 每個數值變數的直方圖與箱形圖、類別次數圖、X 與 Y 關係圖、連續 X 相關性熱圖 |
| `fit`（Linear／Polynomial） | 殘差 vs 配適值圖、常態 Q–Q 圖 |
| `fit`（Ridge／Lasso） | 殘差 vs 配適值圖 |
| `fit`（Logistic 類） | 混淆矩陣、預測機率分布圖 |
| `boxcox` | 剖面概似圖，以及轉換後重新擬合的殘差圖與 Q–Q 圖（轉換前後並列說明） |
| `aic` | lambda_reg 與 AIC 的關係圖（有正規化候選時） |

**原則：**

- 圖必須先展示，才能用來支持任何結論；沒展示的圖不能拿來當證據。
- 圖與檢定結果不一致時（例如 Q–Q 圖尾端明顯偏離，但 p≥0.05），兩者都如實呈現，並說明可能原因，例如樣本小、檢定力不足。
- 某張圖不適用或無法繪製時，說明原因，不要默默省略。
- 同一步驟的圖一次展示完再解讀，不要一張張穿插在多則訊息中。

## 一、確認研究問題與資料

確認以下事項：
- 資料檔與工作表。
- 背景、觀測單位與研究目的（關聯解釋、預測，或兩者皆有）。
- Y（單選）與 X（多選）。
- 是否有時間順序、群聚或重複測量。
- 二元 Y 的 0／1 對應與正類。

處理原則：
- Y／X 尚未指定時，先執行 `inspect` 列出可用欄位供使用者選擇。
- 不得自行把 ID、日期或會洩漏目標的欄位納入模型。
- 不只依數值型態或不同值的數量判定 Y 的意義，必要時向使用者確認。
- 未知的背景、來源、單位或幣別，在報告中明確標示「未提供」，不自行補寫。

## 二、資料檢查、離群候選與前處理

### 資料摘要與離群候選（前處理前）

執行 `inspect` 與 `outliers`，並依「在對話中展示圖表」展示箱形圖與散布圖後，回報下列資訊：
- 原始列數與欄數、所選 Y／X 的型態與缺失。
- 完整案例筆數、二元 Y 各類別筆數。
- 重複列與常數欄位。
- IQR 離群候選的筆數與識別碼，以及箱形圖、散布圖。

注意事項：
- 資料列數不等於獨立受試者數。重複列不自動刪除。
- 離群值只標示並請使用者查核，不直接判定為錯誤，也不自動刪除。只有經查核且使用者同意後，才以 `--exclude-rows` 排除，並記錄原因。

### 前處理方案：先列整份，有異議再逐項討論

一次列出整份方案，每項都要說明預計處理的筆數與影響。方案依下列規則擬定：

- **缺失比例的計算**：缺失比例 = 缺失筆數 ÷ 原始總筆數。恰好 20% 歸入插補。
- **數值型 X，缺失 >0 且 ≤20%**：建議以中位數插補。
- **X 缺失 >20%**：建議刪除該變數，列出變數名稱、缺失比例與刪除後的影響。必須有使用者明確同意才刪除（`--drop-features`）。若使用者要保留，改以中位數插補（`--keep-high-missing`）或討論補收資料。
- **類別型 X**：不使用中位數插補，請使用者在眾數與「缺失」類別之間選擇。數字編碼的類別變數仍視為類別型（`--categorical`）。
- **Y 的缺失**：不套用 X 的規則，也不插補 Y。另外確認是否排除缺失 Y 的資料列（`--drop-missing-y`）。
- **離群候選**：列出查核結果與建議處理方式，預設保留。

確認流程：
- 使用者整份同意，就照方案執行。
- 使用者對部分項目有異議，只針對那些項目逐一討論，已同意的部分不再重問。
- 須記錄：各欄缺失比例、實際插補筆數與插補值、經同意刪除的變數與排除的資料列。

### EDA（前處理後、判斷 Y 類型與推薦模型之前）

以 `eda` 產出下列內容，所有 EDA 圖都要在對話中展示後再解讀：
- 數值變數：有效筆數、平均數、中位數、標準差、四分位數、範圍、偏態，以及箱形圖與直方圖。
- 類別變數：次數與比例、類別次數圖。
- 前處理前後的缺失概況。
- X 與 Y 的關係圖：連續 Y 用散布圖，二元 Y 用分組箱形圖。
- 連續 X 的相關性熱圖。

**相關係數與熱圖只能使用連續變數。** 類別變數、數字編碼的類別變數、只有兩個值的二元變數（含二元 Y），一律不得納入相關係數的計算、相關矩陣或熱圖，也不得以虛擬變數代入。被排除的變數及原因要在報告中列出；連續 X 少於 2 個時，不計算相關係數，並說明原因。只有使用者另外明確同意時，才可對非連續變數改用其他適合的關聯指標，並清楚標示指標名稱。

每張圖都要標示資料範圍、變數名稱、已知單位，以及是否含插補值。報告中要說明分布、偏態、可能的離群點與變數關係，以及這些觀察對模型推薦的意義。不適用或無法計算的圖表要說明原因。

## 三、模型推薦規則

以 `recommend` 計算下列指標：
- **p**：類別編碼與多項式展開後的參數欄數，不含截距。
- **秩**：設計矩陣（含截距）的秩，用於檢查完全共線性。
- **n**：分析筆數。

選 Polynomial 時，要用展開後的 p 重新判斷一次。

### 連續 Y

| 條件 | 處理建議 |
|---|---|
| p ≥ n | 一般 OLS 無法得到唯一係數解，推薦 Ridge／Lasso；殘差型檢定不可靠，須說明 |
| n/p ≥ 20 或殘差自由度 n−p−1 ≥ 30 | 樣本充足，可推薦 Linear／Polynomial（仍須診斷） |
| 以上皆不符合（p 接近 n） | 殘差自由度不足，估計可能不穩定；建議降低複雜度或改用 Ridge／Lasso，不推薦會再增加參數的 Polynomial |

### 二元 Y（n_min 為較少類別的筆數）

| 條件 | 處理建議 |
|---|---|
| p ≥ n | 推薦懲罰式 Logistic |
| n_min/p ≥ 20 | 可先考慮一般 Logistic，仍須檢查分離與收斂 |
| 10 ≤ n_min/p < 20 | 提醒資訊有限，推薦與懲罰式 Logistic 比較 |
| n_min/p < 10 | 強烈提醒過度擬合風險，建議正規化、依理論減少參數，或增加資料 |

### VIF

| 條件 | 處理建議 |
|---|---|
| 任一 VIF ≥ 5 | 共線性警示，說明係數解讀受限 |
| 任一 VIF ≥ 10 | 推薦 Ridge／Lasso；二元 Y 推薦懲罰式 Logistic |
| 無法計算或為無限大 | 如實說明原因，不捏造有限數值 |

計算方式：
- 推薦用的 VIF 以多項式展開前的 X 計算，含截距，類別變數以虛擬變數編碼。
- 展開後的 VIF 只作為結構性共線性的說明，不作為推薦依據。

### 共同原則

- 設計矩陣秩不足時，須說明未懲罰模型的係數無法唯一識別，不採信套件輸出的係數。
- 推薦規則只是推薦。說明理由與限制後，由使用者確認要採用哪些候選模型；不自行刪除變數，也不為了完整而跑遍所有模型。
- Lasso 的零係數不代表該變數沒有影響；非零係數也不代表通過檢定。
- Y 不是連續或二元結果時，說明本 Skill 的支援邊界，提出替代方向。

## 四、初步擬合與假設診斷

只擬合已同意的模型（`fit`）。殘差圖、Q–Q 圖等診斷圖必須在對話中展示，並和檢定表一起解讀；不得只用文字宣稱「偏離常態」「有異質變異」。

**Linear／Polynomial** 必須呈現：
- 殘差 vs 配適值圖、常態 Q–Q 圖。
- BP 與 White 檢定。White 的輔助迴歸會移除重複欄位，例如虛擬變數的平方項。
- DW 與 BG 檢定。
- Shapiro–Wilk（3≤n≤5000）與 JB 檢定。
- 未計算的項目要說明原因。

**Logistic**：
- 檢查完全分離與收斂。發生完全分離時，一般 Logistic 不適用，改提出懲罰式 Logistic 的建議。
- 不要求誤差常態。

**Ridge／Lasso**：
- 只呈現殘差圖，不套用未懲罰模型的檢定推論。

## 五、Box–Cox 與無法修正時的處理

若異質變異數或常態性有重要問題，依下列順序處理：

1. 先查核資料與模型設定，例如是否遺漏曲線項，或有輸入錯誤。
2. Y 全為正值時，可提出 Box–Cox 建議。使用者同意後，以 `boxcox` 估計 lambda_BC，再以 `--lambda-bc` 重新擬合，並重查三項假設。
   - Y 含 0 或負值時不適用，也不擅自加常數。
   - 必須說明轉換前後的結果、係數所在的尺度，以及預測值回轉時的影響。
   - Box–Cox 參數記為 lambda_BC，正規化強度記為 lambda_reg，兩者分開。
3. 只做一次合理的修改，不反覆轉換直到 p 值達標。Box–Cox 不能修正誤差相依性。

若轉換不適用、使用者不同意，或修改後仍有重要問題：
- 依原因提出替代方向，例如 WLS／GLS、相關誤差模型、混合模型、GEE、穩健迴歸或適當的 GLM，並說明理由。
- 明確標示「此方法不在本 Skill 支援範圍內，本 Skill 不執行其擬合與調參」。
- 停止自動修正，保留已完成的結果與限制。

## 六、AIC 選模（全程不使用交叉驗證）

### 執行前須取得的確認

1. **候選模型**：取自推薦規則，由使用者確認。
2. **搜尋範圍**：列出預設值並請使用者確認（`--confirm-search`）。使用者可修改。
   - Polynomial 次數：預設 2、3。
   - Ridge λ：10⁻³ 至 10³，13 點。
   - Lasso λ：10⁻⁴ 至 10¹，11 點。
   - Ridge Logistic λ：10⁻³ 至 10³，13 點。
   - Lasso Logistic λ：10⁻³ 至 10²，11 點。
3. **比較條件**：候選模型須使用相同的 Y 與觀測值，且概似尺度一致。若異質或相依問題沒有妥善處理，不以獨立同質的 Gaussian 概似強行比較。

### 有效自由度與參數計數 k

| 模型 | 有效自由度 |
|---|---|
| Linear／Polynomial | 參數數（含截距） |
| Ridge | 標準化 X 的 hat matrix 之跡 + 截距 |
| Lasso | 非零係數數 + 截距 |
| Logistic | 參數數 |
| Ridge Logistic | 加權 hat matrix 之跡 tr[H(H+λP)⁻¹]，截距不懲罰 |
| Lasso Logistic | 非零係數數 + 截距 |

連續 Y 的 k 另加 1（變異數參數）。有 Box–Cox 時再加 1（lambda_BC），且對數概似須含 Jacobian。

### lambda_reg 的定義

不要把套件的 alpha 或 C 直接當成教材的 λ：
- Ridge：sklearn 的 alpha，目標函數為 ‖y−Xb‖² + λ‖b‖²。
- Lasso：sklearn 的 alpha，目標函數為 (1/2n)‖y−Xb‖² + λ‖b‖₁。
- 懲罰式 Logistic：λ = 1/C。
- 正規化模型都先將 X 標準化。

### 結果呈現

- 列出每個候選的 AIC、有效自由度、k、與最小 AIC 的差值（ΔAIC），選 AIC 最小者並說明理由。
- AIC 與樣本內誤差不是獨立的預測評估，也不取代殘差診斷。
- 選定模型後，以 `fit` 更新最終診斷。若仍有問題，依支援邊界回報。

## 七、結果解讀

### 係數

- 標明係數的資料範圍（全部分析資料，未切分）、Y 與 X 的尺度，以及類別基準組。
- 係數代表「其他納入變數固定下」的模型關聯。
- Polynomial 依整體曲線解讀，不把單一高次項當成固定斜率。
- Logistic 呈現係數與勝算比（OR）的點估計，不把勝算比寫成機率倍數。
- 正規化係數須說明其收縮性質。

### 配適與分類表現

- 連續 Y：呈現樣本內的 R²、RMSE、MAE。有 Box–Cox 時，要註明這些指標是在轉換後的尺度上計算。
- 二元 Y：呈現混淆矩陣（列為實際、欄為預測）、Accuracy、Precision，並標示 0／1 對應、正類、閾值，以及「樣本內」。
- 指標無法定義時說明原因，不以任意數值代替。
- 沒有做獨立測試，不得宣稱已驗證預測表現。

## 八、成果報告（report.qmd → report.pdf）

章節依 report-spec 的必要順序：
1. 研究問題
2. 重點結果與建議
3. 資料與方法
4. EDA
5. 模型結果與診斷
6. 限制
7. 附錄
8. 完整 Python 程式碼

各章節要求：
- **未採用的程序**：明確標示，不為了填滿章節補做。
- **成本與誤差**：未提供成本或容許誤差時，不宣稱模型可部署。
- **附錄**：本次使用方法的公式、未放進正文的診斷圖與 EDA 圖、套件與 Python 版本、資料 SHA-256、重現指令。
- **程式碼章節**：放在最後，以 `#| eval: false` 展示完整分析程式。內容由 `build_qmd.py` 自動填入，和開頭隱藏執行的程式完全相同。

### 製作 report.qmd 的步驟（必須遵守）

1. **設定分析程式**：把 `scripts/run_regression.py` 複製成 `analysis.py`，只修改開頭「分析設定」：
   - 寫入本次已同意的方案。
   - 設 `ACTION = "all"`。
   - `DATA_PATH` 只寫資料檔名（例如 `r"USJudgeRatings.csv"`），讓它以 qmd 所在資料夾為基準。
   - `OUT_DIR` 用相對路徑（例如 `r"regression_results"`）。這個資料夾在渲染時才產生，不是外部輸入。
2. **撰寫草稿**：複製 `assets/report_template.qmd` 成 `report_draft.qmd`。保留它的 YAML、開頭兩個隱藏區塊、最後的程式碼區塊，以及兩行 `# @@ANALYSIS_CODE@@`，再依報告章節撰寫正文。
3. **產生 report.qmd**：

   ```bash
   python scripts/build_qmd.py --draft report_draft.qmd --code analysis.py --out report.qmd
   ```

   這支腳本會把同一份程式填入兩處，並在草稿引用外部檔案時報錯。
4. **在乾淨資料夾渲染**：新資料夾裡只放 `report.qmd` 和資料檔，執行 `quarto render report.qmd`。這一步證明 qmd 不依賴任何其他檔案。

### 正文如何呈現結果

正文中的圖、表、數值都由渲染當下的執行結果產生，使用分析程式內建的三個輔助函式：

| 用途 | 寫法 | 區塊選項 |
|---|---|---|
| 圖 | `fig("eda/eda_xy.png")` | `#| fig-cap: "圖說"` |
| 表 | `table("fit_final/coefficients.csv", digits=4, columns=[...])` | `#| output: asis` |
| 行內數值 | 先在區塊中 `final = result("fit_final/fit.json")["摘要"]`，正文寫 `` `{python} f"{final['AIC']:.2f}"` `` | — |

使用規則：

- 路徑都是相對於 `OUT_DIR` 的輸出位置，例如 `eda/`、`fit_final/`、`aic/`。圖檔名稱以分析時腳本列出的清單為準：
  - Linear／Polynomial 有 `residual_diagnostics.png` 與 `diagnostics.csv`。
  - Ridge／Lasso 只有 `residual_plot.png`。
  - Logistic 類有 `confusion_matrix.png`、`probability_hist.png`。
- 正文中的數值一律用行內 Python 帶入，不手動抄寫，確保 PDF 數字與程式輸出一致。
- **禁止**以下寫法：`![](路徑)` 圖片連結、`\includegraphics`、`{{< include >}}`、程式區塊的 `file:` 選項、`import run_regression`。
- 隱藏的分析區塊執行失敗時（例如找不到資料檔），渲染會中止並顯示錯誤。不得改成引用事先產生的圖檔來繞過。

### 版面

- PDF 採諮詢簡報風格：醒目結論、大圖、短段落。
- 未指定配色時，可用白底、深色標題、青綠重點，但不得宣稱這是使用者指定的設計。
- 正文只放能回答問題、解釋模型或揭露重要問題的圖。每張圖都要交代樣本範圍、軸標籤、單位與白話解讀；單位未知時明確標示。

### Quarto 渲染

YAML 一律沿用 `assets/report_template.qmd`，不得刪改以下設定：

- **跨平台中文字型**：依序尋找系統內建字型，使用者不需要另外下載或安裝字型。
  - Windows：Microsoft JhengHei、Microsoft YaHei。
  - macOS：PingFang TC、Heiti TC。
  - Linux：Noto Sans CJK TC／JP／SC、Source Han Sans TC、WenQuanYi Zen Hei。
  - 全部找不到時，退回 TeX Live 內建的 FandolHei。
- **`\xeCJKDeclareCharClass`**：讓 ≥、≤、希臘字母改用中文字型，避免等寬字型缺字。不要另外使用 `\newunicodechar`，它需要額外的 LaTeX 套件。
- **`fvextra` 自動換行與比較符號支援**：PDF 中 `code-overflow: wrap` 不會生效，必須保留 `\fvset{breaklines=true,breakanywhere=true}`，讓長程式行自動換行。緊接該行後方加入以下兩行，不得插入空白行，三行的行首縮排必須完全一致，且均位於同一個 YAML literal block（`|`）內：

  ```latex
  \fvset{breaklines=true,breakanywhere=true}
  \catcode`\≥=\active \protected\def≥{\ensuremath{\geq}}
  \catcode`\≤=\active \protected\def≤{\ensuremath{\leq}}
  ```

  修改 `assets/report_template.qmd` 時，沿用原本 `\fvset` 所在行的縮排，不得直接套用此 Markdown 範例的縮排。
- **取消程式碼底色框**（`include-before-body` 中重新定義 `Shaded`）：否則上千行的完整程式碼會讓 LaTeX 報 `Dimension too large`。
- **`jupyter: python3` 與 `execute: echo: false`**：開啟渲染時執行 Python，正文不顯示執行用的程式。

字型與符號的注意事項：

- **不要**另外寫 `CJKmainfont`、`mainfont` 等字型欄位，否則會蓋過跨平台設定，在沒有該字型的電腦上報錯。
- FandolHei 以簡體字為主，部分繁體字（例如「迴、異、別、註」）會缺字，只是保底。
- 分析程式與正文避免使用中文字型也沒有的符號，例如下標數字 ₁、₂；改寫成 `_1`、`_2`。
- 渲染後檢查 log 中有沒有 `Missing character` 與 `falling back to FandolHei`。只要出現任一項，就要告訴使用者 PDF 有缺字，並說明原因，不得宣稱 PDF 完整。

**使用者電腦上的渲染需求**（附錄要寫明，交付時也要告知）：

- Python，以及 `requirements.txt` 中的分析套件與 `jupyter`、`tabulate`：

  ```bash
  pip install numpy pandas scipy scikit-learn statsmodels matplotlib openpyxl jupyter tabulate
  ```

- Quarto，並以 `quarto check jupyter` 確認找得到 Python。
- LaTeX：建議用 `quarto install tinytex`。若 TinyTeX 無法自動補裝套件（例如出現 ``File `fvextra.sty' not found``），Windows 可一次安裝常用套件：

  ```powershell
  & "$env:APPDATA\TinyTeX\bin\windows\tlmgr.bat" update --self
  & "$env:APPDATA\TinyTeX\bin\windows\tlmgr.bat" install fvextra fancyvrb xecjk fontspec unicode-math framed upquote booktabs caption float koma-script microtype bookmark xurl footnotehyper etoolbox
  ```

**容器內的渲染環境**：

若環境沒有 Quarto，先安裝：

```bash
V=$(curl -sI https://github.com/quarto-dev/quarto-cli/releases/latest | grep -i '^location' | sed -E 's#.*/v([0-9.]+).*#\1#' | tr -d '\r')
curl -sL -o /tmp/q.tgz https://github.com/quarto-dev/quarto-cli/releases/download/v$V/quarto-$V-linux-amd64.tar.gz
mkdir -p /opt/quarto && tar -xzf /tmp/q.tgz -C /opt/quarto --strip-components=1
```

缺少 LaTeX 套件時，執行：

```bash
apt-get install -y lmodern texlive-lang-chinese texlive-xetex
```

渲染所需的 Python 套件：

```bash
pip install jupyter tabulate --break-system-packages
```

渲染指令：`/opt/quarto/bin/quarto render report.qmd`。

若渲染失敗，須如實回報錯誤。不得把其他格式改名為 PDF，也不得在只產生部分檔案時宣稱兩者都已完成。

## 分析程式要求

### 內容與行為

- 所有設定集中在程式開頭：資料路徑、Y／X、識別碼、seed、已同意的前處理、模型、lambda_reg、lambda_BC、閾值、AIC 候選與搜尋範圍。
- 以檔案路徑匯入資料，不內嵌原始資料。
- 重跑時使用固定方案，不自行重新選擇分析方法。
- 完整列出必要程式，不使用「其餘省略」或未提供的自訂工具。
- 路徑或欄位錯誤時立即停止。依賴缺少、無法估計或未收斂時明確報錯，不把失敗結果當成有效分析。
- 須說明：重跑需要內容相同的資料（以 SHA-256 核對）；套件、平台與浮點運算可能造成些微差異。

### 終端機與 Jupyter 相容

程式須能直接貼進 Jupyter 單一儲存格執行，也能在終端機以 `python 檔名.py` 執行，兩者結果一致。

- **參數**：命令列參數一律用 `argparse` 的 `parse_known_args()`，以忽略 Jupyter 自動帶入的 `-f kernel.json`。步驟用 `--action` 選項指定，不用位置參數，否則 Jupyter 帶入的 kernel 路徑會被誤判為參數值。
- **路徑**：`DATA_PATH`、`OUT_DIR` 等常數放在程式開頭，作為命令列參數的預設值。附註解說明相對路徑的基準位置、Windows 路徑寫法（`r"C:\..."`），以及如何確認目前資料夾。
- **讀檔**：加註解說明使用的編碼與常見替代編碼（如 `cp950`）。找不到檔案時，印出程式實際尋找的完整路徑。
- **圖表後端**：只有在 `"ipykernel" not in sys.modules` 時才設定 `matplotlib.use("Agg")`。
- **圖表顯示**：每張圖先存檔並印出完整路徑，再於 Jupyter 中以 `IPython.display.display(Image(filename=...))` 顯示，不依賴 `plt.show()`。
- **字型**：設定 `axes.unicode_minus = False`，並依序嘗試 Noto Sans CJK TC、Microsoft JhengHei、PingFang TC 等字型。
- **數值輸出**：整理成與報告各節對應的表格（pandas DataFrame）印出，不得只印原始 JSON；完整數值可另存 JSON。

## 交付前檢查

- 只在實際執行成功後，才聲稱已完成分析；不得捏造數值、圖表或檔案。
- 確認分析過程中每個步驟的圖都已在對話中展示過，且每項圖形判讀都有對應的圖與數值。
- 附在報告中的程式，須以本次設定在終端機與 Jupyter（真實 kernel，例如以 nbclient 執行）兩種環境實際測試，確認圖表會顯示、表格會印出、參數不會報錯。
- `report.qmd` 須在只放 `report.qmd` 與資料檔的乾淨資料夾中渲染成功，證明不依賴任何外部圖檔或程式。
- 確認 qmd 開頭與最後的兩份程式碼完全相同（由 `build_qmd.py` 產生即可保證）。
- 檢查 PDF：
  - 以 `pdffonts` 確認中文字型已嵌入，並確認 log 中沒有 `Missing character` 或 `falling back to FandolHei`。
  - 轉成圖片抽查頁面，確認沒有缺字，圖表、表格與程式碼沒有被截斷或超出版面。
- 確認 qmd 與 pdf 的數值、方法與結論一致，且都與腳本輸出相符。
- qmd 與 pdf 都完成並檢查後，才宣稱兩者皆已成功交付。
