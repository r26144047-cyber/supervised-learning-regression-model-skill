# Regression Model Skill

一個以繁體中文互動的迴歸分析 skill，協助使用者從 CSV／Excel 原始資料，走到資料檢查、模型選擇、結果解讀與可重現報告。

先確認研究問題與 Y／X，再檢查資料與離群候選值，確認前處理方案後完成 EDA，接著推薦模型。模型、Box–Cox 轉換與 AIC 搜尋範圍經使用者確認後才執行，不自行刪除變數、排除資料、改模型或擴大搜尋。

**主要流程：資料確認 → 資料檢查與離群候選檢查 → 確認前處理 → EDA → 判斷 Y 類型 → 推薦並確認模型 → 擬合與診斷 → 必要時確認修正 → 確認 AIC 搜尋方案與選模 → 成果報告。**


## 涵蓋的模型

| 方法 | 適用情境 |
|---|---|
| Linear regression | 連續 Y，作為線性關係的基準模型 |
| Polynomial regression | 連續 Y，且資料呈現平滑曲線趨勢 |
| Logistic regression | 二元 Y，估計正類事件機率 |
| Ridge regression | 連續 Y，需收縮係數或改善共線性下的穩定性 |
| Lasso regression | 連續 Y，需收縮係數並精簡變數 |
| Ridge Logistic | 二元 Y，採 L2 懲罰的 Logistic |
| Lasso Logistic | 二元 Y，採 L1 懲罰的 Logistic |

其他 Y 型態會先說明支援範圍，不直接套用上述模型。

## 適用資料

適合以 CSV／Excel 儲存，具有明確結果變數 Y 與解釋變數 X 的表格資料。

| 資料情境 | 可考慮的方法 |
|---|---|
| 連續 Y，例如價格、評分 | Linear、Polynomial、Ridge、Lasso |
| 二元 Y，例如是否通過 | Logistic、懲罰式 Logistic |
| X 之間高度相關 | Ridge、Lasso |
| 高維度：參數數量接近或超過樣本數（p ≥ n） | Ridge、Lasso、懲罰式 Logistic；須確認運算與選模條件 |
| X 與連續 Y 呈平滑曲線關係 | Polynomial；須確認展開後的參數數量 |

`n` 為分析筆數，`p` 為編碼與展開後的參數數量，不含截距。模型須經資料檢查與使用者確認後採用。

多類別、序位、計數、存活及具相依結構的資料，需另行評估適用模型。

## 模型選擇決策樹

```mermaid
%%{init: {'theme': 'base', 'flowchart': {'curve': 'linear', 'nodeSpacing': 25, 'rankSpacing': 45}, 'themeVariables': {'darkMode': true, 'background': '#0d1117', 'fontSize': '16px', 'primaryColor': '#172554', 'primaryTextColor': '#f1f5f9', 'primaryBorderColor': '#60a5fa', 'secondaryColor': '#292015', 'tertiaryColor': '#1e293b', 'lineColor': '#cbd5e1', 'textColor': '#f1f5f9', 'edgeLabelBackground': '#1e293b'}}}%%
flowchart TB
 START([開始：上傳 CSV／Excel])
 START --> A["① 使用者勾選欄位<br/>Y 單選、X 多選<br/>確認時間順序、群組與重複測量結構"]
 A --> B["② 資料品質檢查<br/>缺失比例、型態、重複、常數欄位、秩與樣本數<br/>離群候選值：箱形圖、IQR、散佈圖<br/>"]
 B --> C["③ 提出完整前處理方案<br/>數值 X 缺失 ≤20%：建議中位數插補<br/>X 缺失 >20%：提出刪除建議，須明確同意<br/>類別 X、缺失 Y、離群值另議處理方式"]
 C --> D{"使用者確認 Y／X<br/>及完整前處理方案？"}
 D -- 是 --> E["④ 執行已確認的處理並進行 EDA<br/>描述統計、箱形圖、直方圖、類別次數圖<br/>散佈圖與相關性熱圖"]
 D -- 否 --> D0["暫停執行<br/>依意見修改欄位或方案<br/>取得確認後再從④繼續"]

 E --> F{"⑤ Y 的類型？"}
 F -- 連續 --> F1["連續 Y：推薦候選模型<br/>Linear／Polynomial／Ridge／Lasso"]
 F -- 二元 --> F2["二元 Y：推薦候選模型<br/>Logistic；必要時評估懲罰式 Logistic"]
 F -- 其他 --> F3(["說明本 Skill 不支援<br/>提出替代方向並輸出建議"])
 F1 --> G{"候選模型受支援<br/>且使用者已確認？"}
 F2 --> G
 G -- 是 --> H["⑥ 初步擬合與診斷<br/>連續線性模型：線性設定、異質變異數、獨立性、常態性<br/>"]
 G -- 否 --> G0["暫停擬合<br/>調整候選模型並取得確認<br/>超出範圍則說明不支援，輸出建議"]

 H --> I{"診斷是否顯示<br/>重要假設或模型問題？"}
 I -- 否 --> J["⑦ 確認可比較的模型與概似<br/>相同 Y、相同觀測值、一致概似尺度<br/>確認使用者同意 AIC 選模與調參"]
 I -- 是 --> I0["提出修改建議<br/>異質變異數／常態性異常且 Y>0：評估 Box–Cox<br/>先查核資料與模型設定，取得同意後才轉換<br/>獨立性異常：Box–Cox 無法直接修正相依"]
 I0 --> I1{"Box–Cox 適用<br/>且使用者同意？"}
 I1 -- 是 --> I2["估計轉換參數並重新擬合<br/>重查異質變異數、獨立性與常態性<br/>"]
 I1 -- 否 --> I4["提出適當替代方向並說明限制<br/>相依：AR 模型、混合模型或 GEE<br/>明確說明本 Skill 不支援"]
 I2 --> I3{"重新診斷後<br/>仍有重要問題？"}
 I3 -- 是 --> I4
 I3 -- 否 --> J
 I4 --> I5(["停止自動修正<br/>輸出現有診斷、限制與下一步建議"])

 J --> K{"概似與自由度定義<br/>適用且已獲確認？"}
 K -- 是 --> L["⑧ 使用 AIC 選模<br/>Linear：比較候選設定<br/>Polynomial：選多項式次數<br/>Ridge／Lasso：以有效自由度的近似 AIC 選 λ<br/>懲罰式 Logistic：須有適用的有效自由度實作"]
 K -- 否 --> K0(["停止不適用的 AIC 比較<br/>說明原因、支援限制並輸出現有結果"])
 L --> M["⑨ 呈現並確認選模結果<br/>候選 AIC、與最小值的差值、有效自由度及選定參數<br/>Box–Cox"]
 M --> N{"最終模型診斷<br/>仍有重要問題？"}
 N -- 否 --> O["⑩ 輸出完整分析報告與可重現程式碼<br/>Y／X、處理紀錄、EDA、診斷及修改前後結果<br/>AIC 定義、比較表、選定模型、限制與套件版本"]
 N -- 是 --> N0(["提出 Skill 外替代方法與理由<br/>明確說明不支援其擬合與調參<br/>輸出已完成結果，停止自動修正"])
 O --> END([完成])

 classDef terminal fill:#155e75,color:#ffffff,stroke:#67e8f9,stroke-width:3px;
 classDef main fill:#172554,color:#eff6ff,stroke:#60a5fa,stroke-width:1.5px;
 classDef decision fill:#36270f,color:#fef3c7,stroke:#fbbf24,stroke-width:2px;
 classDef note fill:#1e293b,color:#e2e8f0,stroke:#94a3b8,stroke-width:1.5px;

 class START,END terminal;
 class A,B,C,E,F1,F2,H,J,L,M,O main;
 class D,F,G,I,I1,I3,K,N decision;
 class D0,F3,G0,I0,I2,I4,I5,K0,N0 note;

 linkStyle default stroke:#cbd5e1,stroke-width:1.5px;
```



## 模型推薦的判斷方式

模型推薦綜合考慮研究目的、樣本數、參數數量、設計矩陣秩、共線性與關係形狀。以下門檻是本 Skill 採用的操作性推薦規則，不代表統計上的充分條件，也不保證模型穩定或預測良好。

### 指標定義

| 指標 | 定義與用途 |
|---|---|
| `n` | 套用已確認前處理後，本次分析使用的資料筆數；不一定等於獨立受試者數 |
| `p` | 類別編碼與多項式展開後的解釋變數欄數，不含截距 |
| `n/p` | 每個解釋變數參數對應的觀測筆數，用於評估模型複雜度 |
| `n−p−1` | 含截距且設計矩陣滿秩時，Linear／Polynomial 的殘差自由度 |
| `n_min` | 二元 Y 中，觀測筆數較少的類別筆數 |
| `n_min/p` | 較少類別的筆數相對於參數數量的比例，用於二元模型的資訊量警示 |
| 設計矩陣秩 | 檢查參數是否能唯一識別；含截距時，滿秩須達 `p+1` |
| VIF | 變異數膨脹因子，用於檢查解釋變數間的共線性 |

例如，四個類別的 X 在含截距的模型中，通常展開為三個虛擬變數，因此計入 `p` 的是三個參數，不是一個原始欄位。

Polynomial 須依實際使用的次數、交互作用與展開方式，重新計算 `p`，不能沿用原始 X 的欄位數。

`n/p` 與 `n_min/p` 的規則適用於 `p>0`；若沒有解釋變數，須另行說明截距模型的用途。

### 連續 Y：n/p 與殘差自由度

依下列順序判斷：

| 條件 | 處理建議 |
|---|---|
| `p ≥ n` | 含截距的一般 OLS 無法得到唯一係數解，推薦 Ridge／Lasso；說明殘差型檢定的限制 |
| `p < n`，且 `n/p ≥ 20` **或** `n−p−1 ≥ 30` | 依本 Skill 規則可考慮 Linear／Polynomial，仍須檢查秩、VIF、關係形狀與模型假設 |
| `p < n`，但上述兩個樣本量條件皆未達到 | 提醒估計可能不穩定，建議降低複雜度或採 Ridge／Lasso，不推薦再增加參數的 Polynomial |

即使符合樣本量門檻，設計矩陣仍可能因完全共線性而秩不足，不能只看 `n/p` 就判定模型可用。

若設計矩陣秩不足，一般線性模型的殘差自由度應依 `n−rank(X_design)` 計算，不能直接套用 `n−p−1`；未懲罰模型的係數也無法唯一識別。

### 二元 Y：n_min/p

先確認 Y 的兩個類別、0／1 對應與正類，再依下列規則推薦：

| 條件 | 處理建議 |
|---|---|
| `p ≥ n` | 推薦懲罰式 Logistic |
| `p < n`，且 `n_min/p ≥ 20` | 可先考慮一般 Logistic，仍須檢查分離與收斂 |
| `p < n`，且 `10 ≤ n_min/p < 20` | 提醒資訊有限，推薦與懲罰式 Logistic 比較 |
| `p < n`，且 `n_min/p < 10` | 強烈提醒過度擬合風險，建議正則化、依理論減少參數或增加資料 |

比例達標不保證不存在完全分離或準完全分離，也不保證模型收斂。遇到這些問題時，須說明原因並提出替代方案，不自行改模型。

### 共線性：VIF 與設計矩陣秩

| 條件 | 處理建議 |
|---|---|
| 任一 `VIF ≥ 5` | 提出共線性警示，說明係數解讀可能不穩定 |
| 任一 `VIF ≥ 10` | 推薦 Ridge／Lasso；二元 Y 推薦懲罰式 Logistic |
| VIF 無法計算或為無限大 | 如實說明原因，不捏造有限數值 |
| 含截距的設計矩陣秩小於 `p+1` | 說明未懲罰模型的係數無法唯一識別，不採信其個別係數解讀 |

推薦用的 VIF 以多項式展開前的 X 計算，包含截距，類別變數以虛擬變數編碼。多項式展開後的 VIF 僅作結構性共線性的補充說明，不作推薦依據。

VIF 的 `5` 與 `10` 是本 Skill 的警示門檻，不代表必須刪除變數；是否調整變數或模型，仍由使用者確認。

## 資料檢查與缺失值處理

先檢查欄位型態、缺失、重複列、常數欄位與離群候選值。

離群候選只標示與說明，預設保留；須經查核及使用者同意後才排除，並記錄原因。重複列也不自動刪除。

缺失比例以各欄位的「缺失筆數 ÷ 原始資料總筆數」計算。

| 情況 | 預設建議與確認方式 |
|---|---|
| 數值型 X 有缺失且比例 ≤20% | 建議中位數插補，納入完整前處理方案，確認後執行；恰好 20% 歸此類 |
| X 缺失比例 >20% | 列出變數、缺失比例與影響，經使用者明確同意後才刪除變數 |
| 類別型 X 有缺失 | 提出眾數或「缺失」類別等方案供確認；數字編碼的類別也不使用中位數 |
| Y 有缺失 | 另行確認是否排除缺失 Y 的資料列或補收資料，不預設插補 Y |

## AIC 選模

候選模型及搜尋範圍經使用者確認後，才執行比較。

| 項目 | 預設搜尋範圍 |
|---|---|
| Polynomial 次數 | 2、3 |
| Ridge λ | 10⁻³ 至 10³，共 13 點 |
| Lasso λ | 10⁻⁴ 至 10¹，共 11 點 |
| Ridge Logistic λ | 10⁻³ 至 10³，共 13 點 |
| Lasso Logistic λ | 10⁻³ 至 10²，共 11 點 |


## Skill 資料夾結構

```text
regression-model-skill/
├── README.md
├── SKILL.md                              分析流程、互動原則與交付要求
├── requirements.txt                      基礎 Python 套件需求
├── assets/
│   └── report_template.qmd               Quarto 報告範本與跨平台字型設定
├── references/
│   ├── decision-tree.md                  完整互動流程與模型選擇決策樹
│   ├── decision-tree.png                 決策樹圖片
│   ├── textbook method.md                方法、公式與係數解讀
│   ├── linear_models_math_textbook.qmd   教材 Quarto 原始檔
│   ├── linear_models_math_textbook.html  教材網頁版
│   └── report-spec.md                    成果報告規格
├── scripts/
    ├── run_regression.py                 資料檢查、EDA、診斷與模型分析
    └── build_qmd.py                      將完整分析程式填入報告草稿
```

## 環境準備與使用（Claude）

可在 Claude 支援 Skills 與程式執行的環境使用。須啟用程式執行與檔案建立；Team／Enterprise 也可能受組織設定限制。

操作依據：[Claude 官方 Skills 使用說明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。

### 1. 上傳並啟用 Skill

1. 下載本專案的 Skill ZIP，保留 ZIP 格式。
2. 前往 **Customize → Skills**，點選 **＋ → Create skill → Upload a skill**。
3. 上傳 ZIP，確認 `regression-model-skill` 出現在清單並已啟用。

選單名稱依介面語言與版本可能不同，以官方說明為準。

### 2. 上傳資料並輸入指令

建立新對話，上傳 CSV 或 Excel，並輸入：

```text
請分析我上傳的csv
```

建議同時提供研究背景、觀測單位、Excel 工作表與分析目的，並說明是否有時間順序、群聚或重複測量。

二元 Y 須提供 0／1 意義與正類；數字編碼的類別 X 也須指出。

分析在 Claude 的執行環境進行，須先確認套件、Quarto、LaTeX 與檔案輸出能力。僅在對話中操作不需自行安裝 Python；若要在自己的電腦重新渲染報告，則需準備下述環境。

## 示範資料：美國法官評分資料

### 資料來源與內容

`USJudgeRatings` 是 **R 內建 `datasets` 套件**的資料集，記錄律師對美國高等法院州法官的評價。

R 官方文件列有 **43 位法官、12 個數值變數**。原始來源為 *New Haven Register*，1977 年 1 月 14 日，由 John Hartigan 提供。

詳見 [R 官方資料說明](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/USJudgeRatings.html)。

本專案提供的 `examples/USJudgeRatings.csv` 有 **43 筆資料、13 個欄位，無缺失值**：12 個原始數值變數，加上由 R 列名保留的 `judge` 法官姓名識別欄。

| 欄位 | 說明 |
|---|---|
| `judge` | 法官姓名，識別欄位 |
| `CONT` | 律師與法官的接觸次數指標 |
| `INTG` | 司法廉正 |
| `DMNR` | 儀態與待人態度 |
| `DILG` | 勤勉程度 |
| `CFMG` | 案件流程管理 |
| `DECI` | 裁決及時性 |
| `PREP` | 審判準備程度 |
| `FAMI` | 法律熟悉程度 |
| `ORAL` | 口頭裁決的妥適性 |
| `WRIT` | 書面裁決的妥適性 |
| `PHYS` | 身體能力 |
| `RTEN` | 值得留任的程度 |

`judge` 用於識別資料，不直接當成 X。

### 取得與下載方式

**從 R 內建資料匯出。**

不需另外安裝資料套件，在 R 或 RStudio 執行：

```r
data("USJudgeRatings", package = "datasets")

# 原資料的法官姓名存於列名；匯出為明確的 judge 欄位。
judge_data <- data.frame(
  judge = rownames(USJudgeRatings),
  USJudgeRatings,
  row.names = NULL,
  check.names = FALSE
)

write.csv(
  judge_data,
  file = "USJudgeRatings.csv",
  row.names = FALSE,
  fileEncoding = "UTF-8"
)

getwd()  # 查看 CSV 儲存的資料夾
```

## 成果報告

最終交付 **`report.qmd` 與 `report.pdf`**，由同一份 Quarto 原始檔產生，內容保持一致。

1. 研究問題。
2. 重點結果與建議。
3. 資料與方法：資料範圍、缺失處理、實際插補值與筆數、經確認的刪除紀錄、模型推薦指標與 AIC 搜尋方案。
4. EDA：描述統計、圖表與白話解讀。
5. 模型結果與診斷：區分關聯解釋、樣本內配適與獨立預測評估。
6. 限制。
7. 附錄：必要公式、補充圖表、來源、套件版本與重現指令。
8. 完整 Python 程式碼：包含本次實際採用的前處理、EDA、模型估計、診斷與選模程序。

模型推薦須列明本次實際使用的 `n`、`p`、設計矩陣秩、`n/p`、適用的殘差自由度、二元 Y 的 `n_min/p` 與 VIF，並說明如何形成推薦。

PDF 採醒目結論、大圖與短段落的諮詢報告風格。每張圖標示資料範圍、軸標籤、已知單位與是否含插補值；二元結果標示正類、分類閾值與混淆矩陣。

`report.qmd` 內含完整分析程式，渲染時執行並產生表格與圖；報告最後展示相同程式。唯一外部輸入為原始資料檔，不需額外提供圖檔或分析程式檔。

### 在自己的電腦重現報告

先安裝 Python、[Quarto](https://quarto.org/) 與必要套件：

```bash
pip install numpy pandas scipy scikit-learn statsmodels matplotlib openpyxl jupyter tabulate
quarto check jupyter
quarto install tinytex
```

將 `report.qmd` 與內容相同的資料檔放在同一個資料夾，於該資料夾執行：

```bash
quarto render report.qmd
```

## 開發協助

- ChatGPT：協助修改 skill 與開發。
- Claude：協助測試與驗證。

## 參考資料

- James, G., Witten, D., Hastie, T., Tibshirani, R., & Taylor, J. (2023). *An Introduction to Statistical Learning: with Applications in Python*. Springer. [https://doi.org/10.1007/978-3-031-38747-0](https://doi.org/10.1007/978-3-031-38747-0).
- [教科書官方網站](https://www.statlearning.com/)。
- R `datasets` 套件：[USJudgeRatings 官方資料說明](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/USJudgeRatings.html)。原始資料來源：*New Haven Register*, January 14, 1977（由 John Hartigan 提供）。
- [Claude 官方 Skills 使用說明](https://support.claude.com/en/articles/12512180-use-skills-in-claude)。

上述樣本量與 VIF 門檻是本 Skill 的操作性推薦規則，不宣稱全部直接出自上述教科書。

