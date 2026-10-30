#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""迴歸模型 Skill 工具腳本。

流程：資料檢查 → 離群候選 → 經確認的前處理與 EDA → 模型推薦（樣本量、VIF）
→ 假設診斷 → 必要時 Box–Cox → AIC 選模（全程不使用交叉驗證）→ 最終擬合。
本腳本只產生數值、表格與圖表，不產生報告。

終端機：
    python run_regression.py --action inspect --data data.csv --target y --features x1 x2
Jupyter：
    修改下方「分析設定」後，將整份程式貼進單一儲存格執行；Jupyter 自動帶入的
    -f kernel.json 參數會被 parse_known_args() 忽略。
"""

# =====================================================================
# 分析設定（終端機未提供參數時使用這些預設值；報告附程式時在此寫入已同意的方案）
# =====================================================================
ACTION = "inspect"          # inspect / outliers / eda / recommend / boxcox / aic / fit / all
# 資料路徑：相對路徑以「目前工作資料夾」為基準（可用 import os; print(os.getcwd()) 確認）。
# Windows 請寫成 r"C:\資料夾\data.csv"，避免反斜線被當成跳脫字元。
DATA_PATH = r"data.csv"
SHEET = None                # Excel 工作表名稱；None 表示第一張
ENCODING = "utf-8-sig"      # CSV 編碼；若出現亂碼或 UnicodeDecodeError，常見替代為 "cp950"
OUT_DIR = r"regression_results"
TARGET = "y"                # 結果變數 Y（單選）
FEATURES = ["x1", "x2"]     # 解釋變數 X（多選）
ID_COL = None               # 識別碼欄位（只用於標示，不納入模型）
Y_TYPE = None               # None 自動判斷；或 "continuous"／"binary"（依使用者確認的 Y 意義）
POSITIVE = None             # 二元 Y 的正類（記為 1）；None 表示排序後第二個類別
SEED = 42                   # 固定隨機種子（只影響 saga 等含隨機性的演算法）

# 前處理（須先由使用者確認整份方案）
CONFIRM_PREPROCESSING = False
DROP_FEATURES = []          # 缺失 >20% 且使用者同意刪除的 X
KEEP_HIGH_MISSING = []      # 缺失 >20% 但使用者同意保留並以中位數插補的數值 X
CATEGORICAL = []            # 數字編碼但屬類別的 X
CATEGORICAL_MISSING = "error"   # 類別 X 缺失：error / most_frequent（眾數）/ missing（「缺失」類別）
DROP_MISSING_Y = False      # 使用者同意排除缺失 Y 的資料列
EXCLUDE_ROWS = []           # 經查核且使用者同意排除的資料列（ID_COL 的值；未設 ID_COL 時為列索引）

# 模型與選模
MODEL = "linear"            # linear / polynomial / ridge / lasso / logistic / ridge_logistic / lasso_logistic
DEGREE = 1                  # 最終模型的多項式次數（polynomial 須 ≥2；ridge/lasso 可搭配展開）
INTERACTION = False         # 多項式是否含交互作用項
LAMBDA_REG = None           # 最終正規化強度 lambda_reg（定義見 lambda_definition()）
LAMBDA_BC = None            # Box–Cox：None 不轉換；"estimate" 估計；或數值
THRESHOLD = 0.5             # 二元分類閾值（混淆矩陣用）
CANDIDATES = []             # AIC 比較的候選模型（使用者已確認）
DEGREES = [2, 3]            # Polynomial 候選次數
RIDGE_LAMBDAS = None        # None 使用預設搜尋範圍；或數值清單
LASSO_LAMBDAS = None
CONFIRM_SEARCH = False      # 使用者已確認 AIC 搜尋範圍
AIC_COMPARE_UNTRANSFORMED = False  # Box–Cox 時一併比較未轉換的候選（含 Jacobian）
BG_LAGS = 1                 # Breusch–Godfrey 落後期數
ALPHA_LEVEL = 0.05          # 檢定的輔助判斷水準（不把 p≥0.05 當成假設成立）

# =====================================================================
import argparse
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 120)


class AnalysisError(Exception):
    """分析無法依已確認方案進行時拋出；不改用其他資料或模型。"""


def in_jupyter():
    return "ipykernel" in sys.modules


# ----------------------------- 共用工具 -----------------------------
def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, pd.DataFrame):
        return clean(o.to_dict(orient="records"))
    if isinstance(o, pd.Series):
        return clean(o.to_dict())
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, Path):
        return str(o)
    return o


def save_json(obj, path):
    Path(path).write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2), encoding="utf-8")


def show(title, obj):
    print(f"\n=== {title} ===")
    if isinstance(obj, (pd.DataFrame, pd.Series)):
        print(obj.to_string())
    elif isinstance(obj, dict):
        print(pd.Series({k: v for k, v in obj.items()}, dtype=object).to_string())
    else:
        print(obj)


def outdir(args, sub):
    p = Path(args.output) / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_PLT = None


def plotting():
    """終端機使用非互動後端；Jupyter 不更動後端，圖檔存好後以 display(Image) 顯示。"""
    global _PLT
    if _PLT is not None:
        return _PLT
    import matplotlib
    if not in_jupyter():
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    names = {f.name for f in font_manager.fontManager.ttflist}
    prefs = ["Noto Sans CJK TC", "Microsoft JhengHei", "PingFang TC",
             "Noto Sans CJK JP", "Noto Sans CJK SC", "Heiti TC"]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = [f for f in prefs if f in names] + ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False   # 避免 U+2212 缺字
    _PLT = plt
    return plt


FIGURES = []        # 本次執行產生的圖檔，結束時列出，供在對話中展示給使用者
SHOW_DIR = None     # 設定後，每張圖另複製一份到此資料夾（例如 /mnt/user-data/outputs/figures）


def save_plot(fig, path):
    plt = plotting()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    path = Path(path).resolve()
    if SHOW_DIR:
        import shutil
        dest = Path(SHOW_DIR) / f"{path.parent.name}__{path.name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        path_show = dest
    else:
        path_show = path
    FIGURES.append(str(path_show))
    print(f"圖檔：{path_show}")
    if in_jupyter():
        from IPython.display import Image, display
        display(Image(filename=str(path)))


# ----------------------------- 資料讀取 -----------------------------
def load(args):
    p = Path(args.data).expanduser().resolve()
    if not p.exists():
        raise AnalysisError(f"找不到資料檔。程式實際尋找的完整路徑：{p}\n目前工作資料夾：{Path.cwd()}")
    suf = p.suffix.lower()
    if suf == ".csv":
        # 預設 utf-8-sig（可處理含 BOM 的 UTF-8）；Big5 系統匯出的檔案常需改用 cp950
        try:
            df = pd.read_csv(p, encoding=args.encoding)
        except UnicodeDecodeError as e:
            raise AnalysisError(f"以 {args.encoding} 讀取失敗，可改用 --encoding cp950：{e}")
    elif suf in (".xlsx", ".xls"):
        df = pd.read_excel(p, sheet_name=args.sheet if args.sheet is not None else 0)
    else:
        raise AnalysisError("僅支援 CSV、XLSX、XLS")
    cols = [args.target] + list(args.features)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise AnalysisError(f"欄位不存在：{missing}；可用欄位：{list(df.columns)}")
    if args.target in args.features or len(set(args.features)) != len(args.features):
        raise AnalysisError("Y 不可同時為 X，X 欄位不可重複")
    if args.id_col:
        if args.id_col not in df.columns:
            raise AnalysisError(f"識別碼欄位不存在：{args.id_col}")
        if args.id_col in cols:
            raise AnalysisError("識別碼欄位不可作為 Y 或 X")
    args._path = p
    return df


def row_ids(df, args):
    if args.id_col:
        return df[args.id_col].astype(str)
    return pd.Series(df.index.astype(str), index=df.index)


def y_kind(y, override=None):
    if override:
        return override
    u = y.dropna().unique()
    if len(u) == 2:
        return "binary"
    if pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y) and len(u) > 2:
        return "continuous"
    return "unsupported"


def encode_binary(y, positive):
    vals = sorted(y.dropna().unique(), key=lambda v: str(v))
    if len(vals) != 2:
        raise AnalysisError(f"二元 Y 須恰有兩個類別，實際為 {vals}")
    if positive is None:
        pos = vals[1]
    else:
        match = [v for v in vals if str(v) == str(positive)]
        if not match:
            raise AnalysisError(f"正類 {positive} 不在 Y 的類別 {vals} 中")
        pos = match[0]
    neg = [v for v in vals if str(v) != str(pos)][0]
    return (y.map(str) == str(pos)).astype(int), {"0": str(neg), "1": str(pos)}


def is_categorical(df, c, args):
    s = df[c]
    return c in args.categorical or not pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s)


# ----------------------------- 前處理 -----------------------------
def prepare(df, args):
    """只套用使用者已確認的處理；缺失比例 = 缺失筆數 ÷ 原始總筆數，恰好 20% 歸入插補。"""
    if not args.confirm_preprocessing:
        raise AnalysisError("請先列出整份前處理方案並取得使用者確認；確認後加 --confirm-preprocessing")
    feats = list(args.features)
    unknown = set(args.drop_features + args.categorical + args.keep_high_missing) - set(feats)
    if unknown:
        raise AnalysisError(f"非所選 X 欄位：{sorted(unknown)}")
    if set(args.drop_features) & set(args.keep_high_missing):
        raise AnalysisError("同一變數不可同時刪除與保留")
    n_raw = len(df)
    ratios = df[feats].isna().mean()
    high = [c for c in feats if ratios[c] > 0.20]
    undecided = [c for c in high if c not in args.drop_features and c not in args.keep_high_missing]
    if undecided:
        raise AnalysisError(f"缺失比例 >20% 的 X：{undecided}；須由使用者決定刪除（--drop-features）"
                            "或保留插補（--keep-high-missing），不自動處理")
    feats = [c for c in feats if c not in args.drop_features]
    if not feats:
        raise AnalysisError("刪除後沒有可用的 X")
    d = df.copy()
    excluded = []
    if args.exclude_rows:
        key = row_ids(d, args)
        wanted = [str(v) for v in args.exclude_rows]
        mask = key.isin(wanted)
        notfound = sorted(set(wanted) - set(key[mask]))
        if notfound:
            raise AnalysisError(f"找不到要排除的資料列：{notfound}")
        excluded = list(key[mask])
        d = d.loc[~mask]
    y_missing = int(d[args.target].isna().sum())
    if y_missing and not args.drop_missing_y:
        raise AnalysisError(f"Y 有 {y_missing} 筆缺失；使用者同意排除後加 --drop-missing-y（不插補 Y）")
    d = d.loc[d[args.target].notna()]
    categorical = [c for c in feats if is_categorical(df, c, args)]
    numeric = [c for c in feats if c not in categorical]
    cat_missing = [c for c in categorical if d[c].isna().any()]
    if cat_missing and args.categorical_missing == "error":
        raise AnalysisError(f"類別 X 有缺失：{cat_missing}；須確認以眾數（most_frequent）或「缺失」類別（missing）處理")
    X = d[feats].copy()
    records = []
    for c in numeric:
        X[c] = pd.to_numeric(X[c], errors="raise").astype(float)
        if not np.isfinite(X[c].dropna().to_numpy()).all():
            raise AnalysisError(f"數值 X {c} 含無限值，須另確認處理方案")
        k = int(X[c].isna().sum())
        if k:
            med = X[c].median()
            if pd.isna(med):
                raise AnalysisError(f"{c} 無可估計的中位數")
            X[c] = X[c].fillna(med)
            records.append({"變數": c, "型態": "數值", "原始缺失比例": ratios[c], "方法": "中位數插補",
                            "實際插補筆數": k, "插補值": med})
    for c in categorical:
        s = X[c].map(lambda v: str(v) if pd.notna(v) else np.nan)
        k = int(s.isna().sum())
        if k:
            if args.categorical_missing == "missing":
                fill, method = "缺失", "「缺失」類別"
            else:
                mode = s.mode()
                if mode.empty:
                    raise AnalysisError(f"{c} 無可估計的眾數")
                fill, method = mode.iloc[0], "眾數"
            s = s.fillna(fill)
            records.append({"變數": c, "型態": "類別", "原始缺失比例": ratios[c], "方法": method,
                            "實際插補筆數": k, "插補值": fill})
        X[c] = s
    y_raw = d[args.target]
    kind = y_kind(y_raw, args.y_type)
    if kind == "unsupported":
        raise AnalysisError("Y 不是連續或二元結果，本 Skill 不支援；請說明支援邊界並提出替代方向")
    mapping = None
    if kind == "binary":
        y, mapping = encode_binary(y_raw, args.positive)
    else:
        y = pd.to_numeric(y_raw, errors="raise").astype(float)
    if len(X) < 3:
        raise AnalysisError("可用資料少於 3 筆，無法分析")
    base = {c: sorted(X[c].unique())[0] for c in categorical}
    log = {"原始筆數": n_raw, "原始變數數_所選Y與X": 1 + len(args.features),
           "分析筆數": len(X), "分析X數": len(feats),
           "經確認排除的資料列": excluded, "排除缺失Y筆數": y_missing if args.drop_missing_y else 0,
           "缺失比例_原始": ratios.to_dict(), "Y缺失比例_原始": float(df[args.target].isna().mean()),
           "經確認刪除的變數": list(args.drop_features), "保留插補的高缺失變數": list(args.keep_high_missing),
           "插補紀錄": records, "類別基準組": base, "數值X": numeric, "類別X": categorical,
           "Y類型": kind, "二元對應": mapping}
    return {"X": X, "y": y, "kind": kind, "numeric": numeric, "categorical": categorical,
            "features": feats, "mapping": mapping, "log": log, "ids": row_ids(d, args)}


def design(P, degree=1, interaction=False):
    """設計矩陣（不含截距）。數值 X 依次數展開，類別 X 以第一個類別為基準做虛擬變數。"""
    X, num, cat = P["X"], P["numeric"], P["categorical"]
    parts = []
    if num:
        N = X[num].astype(float)
        if degree <= 1:
            parts.append(N)
        elif interaction:
            from sklearn.preprocessing import PolynomialFeatures
            pf = PolynomialFeatures(degree, include_bias=False)
            arr = pf.fit_transform(N)
            parts.append(pd.DataFrame(arr, index=X.index,
                                      columns=[n.replace(" ", "*") for n in pf.get_feature_names_out(num)]))
        else:
            cols = {}
            for c in num:
                for k in range(1, degree + 1):
                    cols[c if k == 1 else f"{c}^{k}"] = N[c] ** k
            parts.append(pd.DataFrame(cols, index=X.index))
    elif degree > 1:
        raise AnalysisError("多項式展開需要至少一個數值型 X")
    if cat:
        parts.append(pd.get_dummies(X[cat], drop_first=True, dtype=float, prefix_sep="="))
    Z = pd.concat(parts, axis=1).astype(float) if parts else pd.DataFrame(index=X.index)
    if Z.shape[1] == 0:
        raise AnalysisError("設計矩陣沒有任何欄位（類別變數可能只有一個類別）")
    return Z


def with_const(Z):
    return np.column_stack([np.ones(len(Z)), Z.to_numpy(float)])


# ----------------------------- 推薦規則 -----------------------------
def size_rules(n, p, rank, kind, n_min=None):
    """p 為展開後參數欄數（不含截距）；秩另用於檢查完全共線性。"""
    full = rank == p + 1
    out = {"n": n, "p（展開後、不含截距）": p, "設計矩陣秩（含截距）": rank, "滿秩": full,
           "殘差自由度 n-p-1": n - p - 1, "n/p": n / p}
    if kind == "binary":
        out["n_min（較少類別筆數）"] = n_min
        out["n_min/p"] = n_min / p
    if p >= n:
        level = "p≥n"
        rec = ("一般 OLS 無法得到唯一係數解；推薦 Ridge／Lasso" if kind == "continuous"
               else "一般 Logistic 無法得到唯一係數解；推薦懲罰式 Logistic")
    elif kind == "continuous":
        if n / p >= 20 or n - p - 1 >= 30:
            level, rec = "樣本充足", "可推薦 Linear／Polynomial（仍須做假設診斷）"
        else:
            level, rec = "p 接近 n", "殘差自由度不足，估計可能不穩定；建議降低模型複雜度或改用 Ridge／Lasso"
    else:
        r = n_min / p
        if r >= 20:
            level, rec = "n_min/p≥20", "可先考慮一般 Logistic，仍須檢查分離與收斂"
        elif r >= 10:
            level, rec = "10≤n_min/p<20", "資訊有限；推薦與懲罰式 Logistic 比較"
        else:
            level, rec = "n_min/p<10", "過度擬合風險高；考慮正規化、依理論減少參數或增加資料"
    if not full and p < n:
        rec += "；設計矩陣秩不足（完全共線性），未懲罰模型的係數無法唯一識別"
    out["分級"], out["建議"] = level, rec
    return out


def vif_table(Z, structural=False):
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    A = with_const(Z)
    if len(Z) <= A.shape[1]:
        return None, "樣本數不大於參數數（含截距），無法計算 VIF"
    if Z.shape[1] == 1:
        return pd.DataFrame([{"特徵": Z.columns[0], "VIF": 1.0, "判讀": "只有一個特徵，VIF=1"}]), None
    rows = []
    with np.errstate(divide="ignore", invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for j, c in enumerate(Z.columns, 1):
            v = float(variance_inflation_factor(A, j))
            if not np.isfinite(v) or v > 1e12:
                rows.append({"特徵": c, "VIF": np.inf, "判讀": "完全共線性，VIF 無限大"})
            else:
                if structural:
                    note = "高（多項式結構性共線性，不作推薦依據）" if v >= 10 else ""
                else:
                    note = "≥10：推薦正規化" if v >= 10 else ("≥5：共線性警示" if v >= 5 else "")
                rows.append({"特徵": c, "VIF": v, "判讀": note})
    return pd.DataFrame(rows), None


def default_lambdas(model, kind):
    if model in ("ridge", "ridge_logistic"):
        return list(np.round(np.logspace(-3, 3, 13), 6))
    if model == "lasso":
        return list(np.round(np.logspace(-4, 1, 11), 6))
    return list(np.round(np.logspace(-3, 2, 11), 6))


def lambda_definition(model):
    return {"ridge": "lambda_reg = sklearn Ridge 的 alpha；目標函數 ||y-Xb||² + lambda_reg·||b||²（X 已標準化，截距不懲罰）",
            "lasso": "lambda_reg = sklearn Lasso 的 alpha；目標函數 (1/2n)||y-Xb||² + lambda_reg·||b||_1（X 已標準化）",
            "ridge_logistic": "lambda_reg = 1/C；目標函數 -logL + (lambda_reg/2)||b||²（X 已標準化，截距不懲罰）",
            "lasso_logistic": "lambda_reg = 1/C；目標函數 -logL + lambda_reg·||b||_1（X 已標準化，截距不懲罰）"}.get(model, "")


# ----------------------------- 模型核心 -----------------------------
def standardize(Z):
    X = Z.to_numpy(float)
    mu, sd = X.mean(0), X.std(0, ddof=0)
    if (sd == 0).any():
        raise AnalysisError(f"常數欄位無法標準化：{list(Z.columns[sd == 0])}")
    return (X - mu) / sd, mu, sd


def fit_gaussian(Z, y, model, lam=None):
    """回傳配適值、殘差、Gaussian 對數概似、有效自由度（不含變異數參數）與係數。"""
    from sklearn.exceptions import ConvergenceWarning
    n, yv = len(y), np.asarray(y, float)
    if model in ("linear", "polynomial"):
        A = with_const(Z)
        if np.linalg.matrix_rank(A) < A.shape[1]:
            raise AnalysisError("設計矩陣秩不足（p≥n 或完全共線性），一般 OLS 係數無法唯一識別；"
                                "請依推薦規則改用 Ridge／Lasso 或降低模型複雜度")
        beta = np.linalg.lstsq(A, yv, rcond=None)[0]
        fitted, df = A @ beta, float(A.shape[1])
        coef = pd.DataFrame({"特徵": ["截距"] + list(Z.columns), "係數（原尺度）": beta})
    else:
        if lam is None or lam <= 0:
            raise AnalysisError("正規化模型需要正的 lambda_reg")
        Xs, mu, sd = standardize(Z)
        if model == "ridge":
            from sklearn.linear_model import Ridge
            m = Ridge(alpha=lam).fit(Xs, yv)
            s = np.linalg.svd(Xs, compute_uv=False)
            df = float(np.sum(s ** 2 / (s ** 2 + lam))) + 1.0     # hat matrix 的跡 + 截距
        elif model == "lasso":
            from sklearn.linear_model import Lasso
            m = Lasso(alpha=lam, max_iter=200000, tol=1e-8)
            with warnings.catch_warnings():
                warnings.simplefilter("error", ConvergenceWarning)
                try:
                    m.fit(Xs, yv)
                except ConvergenceWarning as e:
                    raise AnalysisError(f"Lasso（lambda_reg={lam}）未收斂：{e}")
            df = float(np.sum(np.abs(m.coef_) > 1e-10)) + 1.0     # 非零係數數 + 截距
        else:
            raise AnalysisError(f"連續 Y 不支援模型 {model}")
        fitted = m.predict(Xs)
        b = m.coef_ / sd
        coef = pd.DataFrame({"特徵": ["截距"] + list(Z.columns),
                             "係數（標準化X）": np.r_[m.intercept_, m.coef_],
                             "係數（換回原尺度）": np.r_[m.intercept_ - np.sum(m.coef_ * mu / sd), b]})
    resid = yv - fitted
    rss = float(resid @ resid)
    if rss <= 1e-12 * max(1.0, float(yv @ yv)):
        raise AnalysisError("殘差平方和約為 0（完全配適，常見於 p 接近或超過 n），無法計算 Gaussian 概似")
    ll = -n / 2 * (np.log(2 * np.pi) + np.log(rss / n) + 1)
    return {"fitted": fitted, "resid": resid, "rss": rss, "ll": float(ll), "df": df, "coef": coef}


def separated(Z, y):
    """嚴格線性可分（完全分離）偵測：以線性規劃檢查是否存在 margin≥1 的超平面。"""
    from scipy.optimize import linprog
    signs = np.where(np.asarray(y) == 1, 1.0, -1.0)
    A = with_const(Z)
    r = linprog(np.zeros(A.shape[1]), A_ub=-signs[:, None] * A, b_ub=-np.ones(len(A)),
                bounds=[(None, None)] * A.shape[1], method="highs")
    return bool(r.success)


def _logreg(model, C, seed):
    import sklearn
    from sklearn.linear_model import LogisticRegression
    try:
        ver = tuple(int(x) for x in sklearn.__version__.split(".")[:2])
    except ValueError:
        ver = (1, 8)
    if model == "ridge_logistic":
        return LogisticRegression(C=C, solver="lbfgs", max_iter=100000, tol=1e-8)
    if ver >= (1, 8):
        return LogisticRegression(C=C, l1_ratio=1.0, solver="saga", max_iter=200000, tol=1e-8, random_state=seed)
    return LogisticRegression(C=C, penalty="l1", solver="saga", max_iter=200000, tol=1e-8, random_state=seed)


def fit_logistic(Z, y, model, lam=None, seed=42):
    from sklearn.exceptions import ConvergenceWarning
    yv, notes = np.asarray(y, int), []
    if model == "logistic":
        import statsmodels.api as sm
        A = with_const(Z)
        if np.linalg.matrix_rank(A) < A.shape[1]:
            raise AnalysisError("設計矩陣秩不足（p≥n 或完全共線性），一般 Logistic 係數無法唯一識別；建議懲罰式 Logistic")
        if separated(Z, yv):
            raise AnalysisError("偵測到完全分離，一般 Logistic 的最大概似估計不存在；建議懲罰式 Logistic 或依理論調整變數")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                r = sm.Logit(yv, A).fit(disp=0, maxiter=500, method="newton")
            except Exception as e:
                raise AnalysisError(f"Logistic 無法估計：{e}")
        if not r.mle_retvals.get("converged", False):
            raise AnalysisError("Logistic 未收斂；不將未收斂結果當成有效分析")
        notes += [str(x.message) for x in w if "converge" in str(x.message).lower() or "separation" in str(x.message).lower()]
        prob, df = np.asarray(r.predict(A)), float(A.shape[1])
        coef = pd.DataFrame({"特徵": ["截距"] + list(Z.columns), "係數（log-odds，原尺度）": r.params,
                             "勝算比 OR（點估計）": np.exp(r.params)})
    else:
        if lam is None or lam <= 0:
            raise AnalysisError("懲罰式 Logistic 需要正的 lambda_reg")
        Xs, mu, sd = standardize(Z)
        m = _logreg(model, 1.0 / lam, seed)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            warnings.simplefilter("ignore", FutureWarning)
            try:
                m.fit(Xs, yv)
            except ConvergenceWarning as e:
                raise AnalysisError(f"{model}（lambda_reg={lam}）未收斂：{e}")
        prob = m.predict_proba(Xs)[:, 1]
        b = m.coef_.ravel()
        if model == "ridge_logistic":
            At = np.column_stack([np.ones(len(Xs)), Xs])
            W = prob * (1 - prob)
            H = At.T @ (At * W[:, None])
            Pm = np.diag([0.0] + [lam] * Xs.shape[1])
            df = float(np.trace(np.linalg.solve(H + Pm, H)))   # 加權 hat matrix 的跡（含截距）
        else:
            df = float(np.sum(np.abs(b) > 1e-8)) + 1.0
        coef = pd.DataFrame({"特徵": ["截距"] + list(Z.columns),
                             "係數（標準化X）": np.r_[m.intercept_[0], b],
                             "係數（換回原尺度）": np.r_[m.intercept_[0] - np.sum(b * mu / sd), b / sd],
                             "每 1 SD 的勝算比（收縮後）": np.r_[np.nan, np.exp(b)]})
    p = np.clip(prob, 1e-15, 1 - 1e-15)
    ll = float(np.sum(yv * np.log(p) + (1 - yv) * np.log(1 - p)))
    return {"prob": prob, "ll": ll, "df": df, "coef": coef, "notes": notes}


def bc(y, lam):
    y = np.asarray(y, float)
    return np.log(y) if abs(lam) < 1e-12 else (y ** lam - 1) / lam


def estimate_boxcox(P, args):
    from scipy.optimize import minimize_scalar
    y = P["y"].to_numpy(float)
    if (y <= 0).any():
        raise AnalysisError("Y 含 0 或負值，Box–Cox 不適用；不擅自加常數")
    deg = args.degree if args.model == "polynomial" else 1
    A = with_const(design(P, deg, args.interaction))
    if np.linalg.matrix_rank(A) < A.shape[1]:
        raise AnalysisError("設計矩陣秩不足，無法估計 Box–Cox 參數")
    n, sly = len(y), float(np.sum(np.log(y)))

    def nll(lam):
        yt = bc(y, lam)
        r = yt - A @ np.linalg.lstsq(A, yt, rcond=None)[0]
        return n / 2 * np.log(float(r @ r) / n) - (lam - 1) * sly   # 含 Jacobian

    grid = np.linspace(-3, 3, 121)
    vals = np.array([nll(g) for g in grid])
    g0 = grid[int(np.argmin(vals))]
    res = minimize_scalar(nll, bounds=(max(-3, g0 - 0.1), min(3, g0 + 0.1)), method="bounded")
    return float(res.x), grid, vals, deg


def resolve_lambda_bc(args, P):
    v = args.lambda_bc
    if v in (None, "", "none", "None"):
        return None
    if P["kind"] != "continuous":
        raise AnalysisError("Box–Cox 只適用於連續 Y")
    if (P["y"] <= 0).any():
        raise AnalysisError("Y 含 0 或負值，Box–Cox 不適用；不擅自加常數")
    if str(v) == "estimate":
        return estimate_boxcox(P, args)[0]
    return float(v)


# ----------------------------- 各步驟 -----------------------------
def act_inspect(args, df):
    od = outdir(args, "inspect")
    sub = df[[args.target] + list(args.features)]
    n = len(df)
    rows = []
    for c in sub.columns:
        miss = int(sub[c].isna().sum())
        ratio = miss / n
        cat = c != args.target and is_categorical(df, c, args)
        if c == args.target:
            plan = "無缺失" if miss == 0 else "建議排除缺失 Y 的資料列（須確認，不插補 Y）"
        elif miss == 0:
            plan = "無缺失，不需處理"
        elif ratio > 0.20:
            plan = "缺失 >20%：建議刪除變數（須使用者明確同意）"
        elif cat:
            plan = "類別型：以眾數或「缺失」類別處理（須選擇）"
        else:
            plan = "數值型、缺失 ≤20%：建議中位數插補"
        rows.append({"欄位": c, "角色": "Y" if c == args.target else "X", "型態": str(sub[c].dtype),
                     "視為類別": cat, "唯一值數": int(sub[c].nunique()), "缺失筆數": miss,
                     "缺失比例": ratio, "建議處理": plan})
    plan = pd.DataFrame(rows)
    const = [c for c in sub.columns if sub[c].nunique(dropna=True) <= 1]
    kind = y_kind(df[args.target], args.y_type)
    summary = {"資料檔": str(args._path), "SHA-256": sha256(args._path),
               "原始資料列數": n, "原始欄位數": df.shape[1], "Y 初步類型": kind,
               "Y 非缺失筆數": int(df[args.target].notna().sum()),
               "完整案例筆數": int(len(sub.dropna())), "重複資料列數（所選欄位）": int(sub.duplicated().sum()),
               "常數欄位": const,
               "提醒": "資料列數不等於獨立受試者數；重複列不自動刪除。數字編碼的類別 X 須以 --categorical 指定。"}
    show("資料摘要", summary)
    show("缺失概況與前處理建議（缺失比例 = 缺失筆數 ÷ 原始總筆數）", plan)
    if kind == "binary":
        vc = df[args.target].value_counts(dropna=True)
        show("二元 Y 各類別筆數", vc)
        summary["二元Y各類別筆數"] = vc.to_dict()
    plan.to_csv(od / "missing_plan.csv", index=False, encoding="utf-8-sig")
    save_json({"摘要": summary, "前處理建議": plan}, od / "inspect.json")
    return summary


def act_outliers(args, df):
    plt = plotting()
    od = outdir(args, "outliers")
    ids = row_ids(df, args)
    cols = [c for c in [args.target] + list(args.features)
            if not (c != args.target and is_categorical(df, c, args))
            and pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 2]
    if not cols:
        print("沒有適用 IQR 檢查的數值變數。")
        return {}
    summary, flagged = [], []
    for c in cols:
        s = df[c].dropna().astype(float)
        q1, q3 = s.quantile(.25), s.quantile(.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (df[c] < lo) | (df[c] > hi)
        summary.append({"變數": c, "Q1": q1, "Q3": q3, "IQR": iqr, "下界": lo, "上界": hi, "候選筆數": int(mask.sum())})
        for i in df.index[mask]:
            flagged.append({"變數": c, "識別碼": ids[i], "值": df.at[i, c], "方向": "低於下界" if df.at[i, c] < lo else "高於上界"})
    tab, fl = pd.DataFrame(summary), pd.DataFrame(flagged)
    show("離群候選值（IQR 1.5 倍規則；僅標示，不自動刪除）", tab)
    if len(fl):
        show("候選資料列", fl)
    k = len(cols)
    ncol = min(4, k)
    nrow = int(np.ceil(k / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.2 * ncol, 3.2 * nrow), squeeze=False)
    for ax, c in zip(axes.ravel(), cols):
        ax.boxplot(df[c].dropna().astype(float), whis=1.5)
        ax.set_title(c)
        ax.set_xticks([])
    for ax in axes.ravel()[k:]:
        ax.axis("off")
    fig.suptitle(f"前處理前的箱形圖（原始資料，n={len(df)}，單位未提供則未標示）")
    save_plot(fig, od / "outlier_boxplots.png")
    if args.target in cols:
        xs = [c for c in cols if c != args.target]
        if xs:
            k = len(xs)
            ncol = min(3, k)
            nrow = int(np.ceil(k / ncol))
            fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3.4 * nrow), squeeze=False)
            ymask = df.index.isin([i for i in df.index if ids[i] in set(fl["識別碼"])]) if len(fl) else np.zeros(len(df), bool)
            for ax, c in zip(axes.ravel(), xs):
                ax.scatter(df[c], df[args.target], s=14, alpha=.6, label="一般")
                if ymask.any():
                    ax.scatter(df.loc[ymask, c], df.loc[ymask, args.target], s=22, color="crimson", label="離群候選")
                ax.set_xlabel(c)
                ax.set_ylabel(args.target)
            for ax in axes.ravel()[k:]:
                ax.axis("off")
            axes.ravel()[0].legend(fontsize=8)
            fig.suptitle("X 與 Y 散布圖（原始資料；紅點為任一變數的離群候選列）")
            save_plot(fig, od / "outlier_scatter.png")
    tab.to_csv(od / "outlier_summary.csv", index=False, encoding="utf-8-sig")
    fl.to_csv(od / "outlier_rows.csv", index=False, encoding="utf-8-sig")
    save_json({"摘要": tab, "候選資料列": fl}, od / "outliers.json")
    return {"摘要": tab, "候選資料列": fl}


def act_eda(args, df, P=None):
    P = P or prepare(df, args)
    plt = plotting()
    od = outdir(args, "eda")
    X, y, num, cat = P["X"], P["y"], P["numeric"], P["categorical"]
    yname = args.target
    shown = X.copy()
    shown[yname] = y if P["kind"] == "continuous" else y.map(lambda v: P["mapping"][str(v)])
    imputed = {r["變數"] for r in P["log"]["插補紀錄"]}
    show("前處理紀錄", {k: v for k, v in P["log"].items() if k not in ("插補紀錄", "缺失比例_原始")})
    if P["log"]["插補紀錄"]:
        show("插補紀錄", pd.DataFrame(P["log"]["插補紀錄"]))
    num_cols = num + ([yname] if P["kind"] == "continuous" else [])
    if num_cols:
        s = shown[num_cols].astype(float)
        desc = pd.DataFrame({"有效筆數": s.count(), "平均數": s.mean(), "中位數": s.median(), "標準差": s.std(),
                             "Q1": s.quantile(.25), "Q3": s.quantile(.75), "最小值": s.min(), "最大值": s.max(),
                             "偏態": s.skew()})
        show("數值變數描述統計（前處理後）", desc)
        desc.to_csv(od / "descriptive_numeric.csv", encoding="utf-8-sig")
    else:
        desc = pd.DataFrame()
    freq = []
    for c in cat + ([yname] if P["kind"] == "binary" else []):
        vc = shown[c].value_counts()
        for k, v in vc.items():
            freq.append({"變數": c, "類別": k, "次數": int(v), "比例": v / len(shown)})
    freq = pd.DataFrame(freq)
    if len(freq):
        show("類別變數次數與比例（前處理後）", freq)
        freq.to_csv(od / "frequency.csv", index=False, encoding="utf-8-sig")
    raw = df[[args.target] + list(args.features)]
    miss = pd.DataFrame({"前處理前缺失筆數": raw.isna().sum(), "前處理前缺失比例": raw.isna().mean()})
    miss["前處理後缺失筆數"] = [int(shown[c].isna().sum()) if c in shown else None for c in miss.index]
    miss["處理"] = ["已刪除變數" if c in P["log"]["經確認刪除的變數"] else ("已插補" if c in imputed else "") for c in miss.index]
    show("前處理前後缺失概況", miss)
    miss.to_csv(od / "missing_before_after.csv", encoding="utf-8-sig")
    for i, c in enumerate(num_cols):
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
        axes[0].hist(shown[c].astype(float), bins="auto", color="#14b8a6", edgecolor="white")
        axes[0].set_xlabel(c)
        axes[0].set_ylabel("次數")
        axes[1].boxplot(shown[c].astype(float))
        axes[1].set_ylabel(c)
        axes[1].set_xticks([])
        tag = "；含中位數插補值" if c in imputed else ""
        fig.suptitle(f"{c}：直方圖與箱形圖（前處理後 n={len(shown)}{tag}；單位未提供）")
        save_plot(fig, od / f"eda_dist_{i:02d}.png")
    for i, c in enumerate(cat + ([yname] if P["kind"] == "binary" else [])):
        vc = shown[c].value_counts()
        fig, ax = plt.subplots(figsize=(6, 3.4))
        ax.bar([str(v) for v in vc.index], vc.values, color="#0f766e")
        ax.set_ylabel("次數")
        ax.set_xlabel(c)
        ax.set_title(f"{c} 類別次數（前處理後 n={len(shown)}）")
        save_plot(fig, od / f"eda_counts_{i:02d}.png")
    if num:
        k = len(num)
        ncol = min(3, k)
        nrow = int(np.ceil(k / ncol))
        fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3.4 * nrow), squeeze=False)
        for ax, c in zip(axes.ravel(), num):
            if P["kind"] == "continuous":
                ax.scatter(shown[c], y, s=14, alpha=.6, color="#0f766e")
                ax.set_ylabel(yname)
            else:
                groups = [shown.loc[y == g, c].astype(float) for g in (0, 1)]
                ax.boxplot(groups)
                ax.set_xticks([1, 2], [f"0={P['mapping']['0']}", f"1={P['mapping']['1']}"])
                ax.set_ylabel(c)
            ax.set_xlabel(c if P["kind"] == "continuous" else yname)
        for ax in axes.ravel()[k:]:
            ax.axis("off")
        fig.suptitle("X 與 Y 的關係（前處理後；觀察趨勢用，不證明模型形式）")
        save_plot(fig, od / "eda_xy.png")
    # 相關係數與熱圖只納入連續變數：排除類別 X（含以 --categorical 指定的數字編碼類別）
    # 與只有兩個值的二元變數；二元 Y 也不納入。
    cont = [c for c in num if shown[c].nunique() > 2]
    corr_excluded = [{"變數": c, "排除原因": "類別變數"} for c in cat] + \
                    [{"變數": c, "排除原因": "二元變數（只有兩個值）"} for c in num if c not in cont]
    if corr_excluded:
        show("未納入相關係數與熱圖的非連續變數", pd.DataFrame(corr_excluded))
    corr = None
    if len(cont) > 1:
        corr = shown[cont].astype(float).corr()
        show("連續 X 相關係數", corr)
        corr.to_csv(od / "correlation.csv", encoding="utf-8-sig")
        fig, ax = plt.subplots(figsize=(1.1 * len(cont) + 3, 1.0 * len(cont) + 2.5))
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
        ax.set_xticks(range(len(cont)), cont, rotation=45, ha="right")
        ax.set_yticks(range(len(cont)), cont)
        for a in range(len(cont)):
            for b in range(len(cont)):
                ax.text(b, a, f"{corr.iat[a, b]:.2f}", ha="center", va="center", fontsize=8)
        fig.colorbar(im, ax=ax)
        ax.set_title("連續 X 相關性熱圖（前處理後；不含類別與二元變數）")
        save_plot(fig, od / "eda_correlation.png")
    else:
        print(f"連續 X 少於 2 個（{cont}），不計算相關係數、不繪製熱圖。")
    save_json({"前處理": P["log"], "描述統計": desc.reset_index().rename(columns={"index": "變數"}),
               "次數": freq, "缺失": miss.reset_index().rename(columns={"index": "欄位"}),
               "相關係數_連續X": corr, "相關係數排除的變數": corr_excluded}, od / "eda.json")
    return P


def act_recommend(args, df, P=None):
    P = P or prepare(df, args)
    od = outdir(args, "recommend")
    kind, y = P["kind"], P["y"]
    n = len(y)
    n_min = int(y.value_counts().min()) if kind == "binary" else None
    rules = []
    specs = [("基本模型（未展開）", 1)] + [(f"Polynomial 次數 {d}", d) for d in sorted(set(args.degrees)) if d > 1 and P["numeric"]]
    for label, deg in specs:
        Z = design(P, deg, args.interaction)
        r = size_rules(n, Z.shape[1], int(np.linalg.matrix_rank(with_const(Z))), kind, n_min)
        rules.append({"設定": label, **r})
    rules = pd.DataFrame(rules)
    show("樣本量與可估計性（推薦規則）", rules)
    Z1 = design(P, 1)
    vif, msg = vif_table(Z1)
    if vif is not None:
        show("VIF（多項式展開前的 X；≥5 警示、≥10 推薦正規化）", vif)
        mx = float(vif["VIF"].max())
        vif_rec = ("推薦 Ridge／Lasso" if kind == "continuous" else "推薦懲罰式 Logistic") if mx >= 10 else \
                  ("共線性警示：係數解讀受限" if mx >= 5 else "未見明顯共線性")
    else:
        print(f"VIF：{msg}")
        vif_rec = msg
    structural = None
    if len(specs) > 1:
        Zd = design(P, specs[-1][1], args.interaction)
        structural, smsg = vif_table(Zd, structural=True)
        if structural is not None:
            show(f"展開後 VIF（{specs[-1][0]}；結構性共線性，只作說明，不作推薦依據）", structural)
    base_level = rules.iloc[0]["分級"]
    cands = []
    if kind == "continuous":
        if base_level == "p≥n":
            cands = ["ridge", "lasso"]
        else:
            if base_level == "p 接近 n":
                cands = ["linear", "ridge", "lasso"]   # 不推薦會再增加參數的 Polynomial
            else:
                cands = ["linear", "polynomial"] if P["numeric"] else ["linear"]
                if vif is not None and vif["VIF"].max() >= 10:
                    cands += ["ridge", "lasso"]
    else:
        if base_level == "p≥n":
            cands = ["ridge_logistic", "lasso_logistic"]
        else:
            cands = ["logistic"]
            if base_level != "n_min/p≥20" or (vif is not None and vif["VIF"].max() >= 10):
                cands += ["ridge_logistic", "lasso_logistic"]
    search = {"Polynomial 候選次數": sorted(set(args.degrees))} if "polynomial" in cands else {}
    for m in cands:
        if m in ("ridge", "lasso", "ridge_logistic", "lasso_logistic"):
            search[f"{m} lambda_reg"] = default_lambdas(m, kind)
            search[f"{m} 定義"] = lambda_definition(m)
    rec = {"Y 類型": kind, "樣本量建議": rules.iloc[0]["建議"], "VIF 建議": vif_rec,
           "規則推薦的候選模型": cands, "預設 AIC 搜尋範圍（須使用者確認）": search,
           "提醒": "以上為推薦，實際採用的模型由使用者確認；不自動刪除變數或改變模型。"}
    show("推薦摘要", rec)
    rules.to_csv(od / "size_rules.csv", index=False, encoding="utf-8-sig")
    save_json({"規則": rules, "VIF": vif if vif is not None else msg, "展開後VIF": structural, "推薦": rec}, od / "recommend.json")
    return rec


def white_test(e, Z):
    """White 檢定：殘差平方對 X、X 平方與兩兩交乘迴歸；以 QR 移除線性相依欄位後計算自由度。"""
    from scipy import stats
    X = Z.to_numpy(float)
    cols = [np.ones(len(X))] + [X[:, j] for j in range(X.shape[1])]
    for i in range(X.shape[1]):
        for j in range(i, X.shape[1]):
            cols.append(X[:, i] * X[:, j])
    M = np.column_stack(cols)
    M = M / np.where(np.abs(M).max(0) > 0, np.abs(M).max(0), 1)
    keep = []
    for j in range(M.shape[1]):
        if np.linalg.matrix_rank(M[:, keep + [j]]) == len(keep) + 1:
            keep.append(j)
    M = M[:, keep]
    if len(e) <= M.shape[1] + 1:
        raise ValueError("樣本數不足以估計 White 輔助迴歸")
    u = e ** 2
    fit = M @ np.linalg.lstsq(M, u, rcond=None)[0]
    r2 = 1 - np.sum((u - fit) ** 2) / np.sum((u - u.mean()) ** 2)
    df = M.shape[1] - 1
    lm = len(e) * r2
    return float(lm), float(stats.chi2.sf(lm, df)), df


def ols_diagnostics(Z, y, args, od, tag):
    import statsmodels.api as sm
    from scipy import stats
    from statsmodels.stats.diagnostic import acorr_breusch_godfrey, het_breuschpagan
    from statsmodels.stats.stattools import durbin_watson, jarque_bera
    plt = plotting()
    A = with_const(Z)
    res = sm.OLS(np.asarray(y, float), A).fit()
    e, n = res.resid, len(y)
    rows = []

    def add(name, aspect, stat, p, note=""):
        flag = "" if p is None else ("p<{:.2f}：顯示可能問題".format(args.alpha_level) if p < args.alpha_level
                                     else "p≥{:.2f}：未偵測到明顯問題（不等於假設成立）".format(args.alpha_level))
        rows.append({"檢查": name, "面向": aspect, "統計量": stat, "p-value": p, "輔助判讀": flag, "說明": note})

    bp = het_breuschpagan(e, A)
    add("Breusch–Pagan", "異質變異數", bp[0], bp[1])
    try:
        w_stat, w_p, w_df = white_test(e, Z)
        add("White", "異質變異數", w_stat, w_p, f"輔助迴歸自由度 {w_df}（已移除虛擬變數平方等重複欄位）")
    except Exception as ex:
        add("White", "異質變異數", None, None, f"未計算：{ex}")
    add("Durbin–Watson", "獨立性（一階自相關）", float(durbin_watson(e)), None,
        "接近 2 表示一階自相關不明顯；只在資料順序有意義時解讀")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            bg = acorr_breusch_godfrey(res, nlags=args.bg_lags)
        add(f"Breusch–Godfrey（{args.bg_lags} 期）", "獨立性", bg[0], bg[1], "只在資料順序有意義時解讀")
    except Exception as ex:
        add("Breusch–Godfrey", "獨立性", None, None, f"未計算：{ex}")
    if 3 <= n <= 5000:
        sw = stats.shapiro(e)
        add("Shapiro–Wilk", "常態性", sw.statistic, sw.pvalue)
    else:
        add("Shapiro–Wilk", "常態性", None, None, "樣本數超出 3–5000，未計算")
    jb = jarque_bera(e)
    add("Jarque–Bera", "常態性", jb[0], jb[1], "小樣本時近似較差")
    tab = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].scatter(res.fittedvalues, e, s=14, alpha=.65, color="#0f766e")
    axes[0].axhline(0, ls="--", color="gray")
    axes[0].set_xlabel("配適值")
    axes[0].set_ylabel("殘差")
    axes[0].set_title("殘差 vs 配適值（線性設定、異質變異數）")
    (osm, osr), (sl, ic, _) = stats.probplot(e, dist="norm")
    axes[1].scatter(osm, osr, s=14, alpha=.65, color="#0f766e")
    axes[1].plot(osm, sl * osm + ic, color="gray", ls="--")
    axes[1].set_xlabel("理論常態分位數")
    axes[1].set_ylabel("殘差分位數")
    axes[1].set_title("常態 Q-Q 圖")
    fig.suptitle(f"{tag}：建模資料 n={n}")
    save_plot(fig, od / "residual_diagnostics.png")
    return tab


def act_boxcox(args, df, P=None):
    P = P or prepare(df, args)
    if P["kind"] != "continuous":
        raise AnalysisError("Box–Cox 只適用於連續 Y")
    plt = plotting()
    od = outdir(args, "boxcox")
    lam, grid, vals, deg = estimate_boxcox(P, args)
    n = len(P["y"])
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(grid, -vals, color="#0f766e")
    ax.axvline(lam, ls="--", color="crimson")
    ax.set_xlabel("lambda_BC")
    ax.set_ylabel("剖面對數概似（含 Jacobian，差一常數）")
    ax.set_title(f"Box–Cox 剖面概似（模型次數 {deg}，n={n}）")
    save_plot(fig, od / "boxcox_profile.png")
    out = {"lambda_BC": lam, "估計所用模型次數": deg, "建模資料筆數": n,
           "說明": "lambda_BC 以最大剖面概似估計（含 Jacobian）；使用者同意後以 --lambda-bc 重新擬合並重查假設。"
                   "Box–Cox 不能修正誤差相依性；不反覆轉換直到 p 值達標。"}
    show("Box–Cox 估計", out)
    save_json(out, od / "boxcox.json")
    return out


def act_aic(args, df, P=None):
    P = P or prepare(df, args)
    od = outdir(args, "aic")
    kind, y = P["kind"], P["y"]
    if not args.candidates:
        raise AnalysisError("請以 --candidates 列出使用者確認的候選模型")
    if not args.confirm_search:
        raise AnalysisError("AIC 搜尋範圍（次數、lambda_reg）須先列給使用者確認；確認後加 --confirm-search")
    lam_bc = resolve_lambda_bc(args, P)
    cont_models, bin_models = {"linear", "polynomial", "ridge", "lasso"}, {"logistic", "ridge_logistic", "lasso_logistic"}
    for m in args.candidates:
        if m not in (cont_models if kind == "continuous" else bin_models):
            raise AnalysisError(f"候選模型 {m} 與 Y 類型（{kind}）不相容")
    transforms = [lam_bc] if lam_bc is None or not args.aic_compare_untransformed else [None, lam_bc]
    rows = []
    for lbc in transforms:
        yt = bc(y, lbc) if lbc is not None else y
        jac = (lbc - 1) * float(np.sum(np.log(y))) if lbc is not None else 0.0
        for m in args.candidates:
            if m == "linear" or m == "logistic":
                degs = [1]
            elif m == "polynomial":
                degs = sorted(set(d for d in args.degrees if d > 1))
            else:
                degs = [args.degree]
            if m in ("ridge", "ridge_logistic"):
                lams = args.ridge_lambdas or default_lambdas(m, kind)
            elif m in ("lasso", "lasso_logistic"):
                lams = args.lasso_lambdas or default_lambdas(m, kind)
            else:
                lams = [None]
            for d in degs:
                Z = design(P, d, args.interaction)
                for lam in lams:
                    row = {"模型": m, "次數": d, "lambda_reg": lam, "lambda_BC": lbc}
                    try:
                        if kind == "continuous":
                            r = fit_gaussian(Z, yt, m, lam)
                            ll = r["ll"] + jac
                            k = r["df"] + 1 + (1 if lbc is not None else 0)   # +σ²，+lambda_BC
                        else:
                            r = fit_logistic(Z, y, m, lam, args.seed)
                            ll, k = r["ll"], r["df"]
                        row.update({"有效自由度": r["df"], "參數計數k": k, "logLik": ll, "AIC": -2 * ll + 2 * k, "狀態": "可用"})
                    except AnalysisError as e:
                        row.update({"有效自由度": np.nan, "參數計數k": np.nan, "logLik": np.nan, "AIC": np.nan, "狀態": str(e)})
                    rows.append(row)
    tab = pd.DataFrame(rows)
    if tab["AIC"].notna().sum() == 0:
        show("AIC 候選結果", tab)
        raise AnalysisError("所有候選模型皆無法估計，無法以 AIC 選模")
    tab["ΔAIC"] = tab["AIC"] - tab["AIC"].min()
    best = tab.loc[tab["AIC"].idxmin()].to_dict()
    show("AIC 比較（相同觀測值、相同 Y；k 含變異數參數與 Box–Cox 參數）", tab)
    show("AIC 最小的候選", best)
    plt = plotting()
    pen = tab[tab["lambda_reg"].notna() & tab["AIC"].notna()]
    if len(pen):
        fig, ax = plt.subplots(figsize=(6.5, 3.8))
        for (m, d, lbc), g in pen.groupby(["模型", "次數", tab["lambda_BC"].fillna(-999)]):
            ax.plot(np.log10(g["lambda_reg"].astype(float)), g["AIC"], marker="o", label=f"{m}（次數 {d}）")
        ax.set_xlabel("log10(lambda_reg)")
        ax.set_ylabel("AIC")
        ax.legend(fontsize=8)
        ax.set_title(f"正規化強度與 AIC（n={len(y)}）")
        save_plot(fig, od / "aic_lambda.png")
    tab.to_csv(od / "aic_table.csv", index=False, encoding="utf-8-sig")
    save_json({"AIC表": tab, "選定": best, "lambda_reg定義": {m: lambda_definition(m) for m in args.candidates},
               "提醒": "AIC 不是獨立測試成績，也不取代殘差診斷。"}, od / "aic.json")
    return best


def act_fit(args, df, P=None, sub="fit"):
    P = P or prepare(df, args)
    plt = plotting()
    od = outdir(args, sub)
    kind, y, m = P["kind"], P["y"], args.model
    if (kind == "continuous") != (m in ("linear", "polynomial", "ridge", "lasso")):
        raise AnalysisError(f"模型 {m} 與 Y 類型（{kind}）不相容")
    if m == "polynomial" and args.degree < 2:
        raise AnalysisError("Polynomial 需要 --degree ≥ 2")
    deg = 1 if m in ("linear", "logistic") else args.degree
    Z = design(P, deg, args.interaction)
    n = len(y)
    info = {"模型": m, "次數": deg, "交互作用": bool(args.interaction and deg > 1), "建模筆數": n,
            "lambda_reg": args.lambda_reg, "lambda_reg 定義": lambda_definition(m),
            "類別基準組": P["log"]["類別基準組"], "資料範圍": "全部分析資料（未切分；以下指標皆為樣本內配適，不是獨立預測評估）"}
    if kind == "continuous":
        lam_bc = resolve_lambda_bc(args, P)
        yt = bc(y, lam_bc) if lam_bc is not None else y
        r = fit_gaussian(Z, yt, m, args.lambda_reg)
        jac = (lam_bc - 1) * float(np.sum(np.log(y))) if lam_bc is not None else 0.0
        k = r["df"] + 1 + (1 if lam_bc is not None else 0)
        yv = np.asarray(yt, float)
        info.update({"lambda_BC": lam_bc, "係數尺度": "Box–Cox 轉換後的 Y" if lam_bc is not None else "原始 Y",
                     "有效自由度": r["df"], "logLik（含 Jacobian）": r["ll"] + jac, "AIC": -2 * (r["ll"] + jac) + 2 * k,
                     "R²（樣本內）": 1 - r["rss"] / float(np.sum((yv - yv.mean()) ** 2)),
                     "RMSE（樣本內，建模尺度）": float(np.sqrt(r["rss"] / n)),
                     "MAE（樣本內，建模尺度）": float(np.mean(np.abs(r["resid"])))})
        coef = r["coef"]
        tag = f"{m}{'（Box–Cox lambda_BC=%.3f）' % lam_bc if lam_bc is not None else ''}"
        if m in ("linear", "polynomial"):
            diag = ols_diagnostics(Z, yt, args, od, tag)
            show("假設診斷（p-value 僅作輔助判斷）", diag)
            diag.to_csv(od / "diagnostics.csv", index=False, encoding="utf-8-sig")
        else:
            diag = None
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.scatter(r["fitted"], r["resid"], s=14, alpha=.65, color="#0f766e")
            ax.axhline(0, ls="--", color="gray")
            ax.set_xlabel("配適值")
            ax.set_ylabel("殘差")
            ax.set_title(f"{tag} 殘差 vs 配適值（n={n}）")
            save_plot(fig, od / "residual_plot.png")
    else:
        if m == "logistic" and separated(Z, y):
            raise AnalysisError("偵測到完全分離；一般 Logistic 不適用，建議懲罰式 Logistic")
        r = fit_logistic(Z, y, m, args.lambda_reg, args.seed)
        coef, diag = r["coef"], None
        prob = r["prob"]
        pred = (prob >= args.threshold).astype(int)
        yv = np.asarray(y, int)
        cm = np.array([[np.sum((yv == a) & (pred == b)) for b in (0, 1)] for a in (0, 1)])
        tp, fp = cm[1, 1], cm[0, 1]
        info.update({"0／1 對應": P["mapping"], "正類": f"1 = {P['mapping']['1']}", "分類閾值": args.threshold,
                     "有效自由度": r["df"], "logLik": r["ll"], "AIC": -2 * r["ll"] + 2 * r["df"],
                     "Accuracy（樣本內）": float((pred == yv).mean()),
                     "Precision（樣本內）": float(tp / (tp + fp)) if tp + fp > 0 else "無法定義（沒有預測為正類的觀測值）",
                     "擬合警告": r["notes"]})
        cmdf = pd.DataFrame(cm, index=[f"實際 0（{P['mapping']['0']}）", f"實際 1（{P['mapping']['1']}）"],
                            columns=[f"預測 0", f"預測 1"])
        show(f"混淆矩陣（列為實際、欄為預測；閾值 {args.threshold}；樣本內）", cmdf)
        cmdf.to_csv(od / "confusion_matrix.csv", encoding="utf-8-sig")
        fig, ax = plt.subplots(figsize=(4.8, 4.2))
        ax.imshow(cm, cmap="Greens")
        for a in range(2):
            for b in range(2):
                ax.text(b, a, str(cm[a, b]), ha="center", va="center", fontsize=14)
        ax.set_xticks([0, 1], ["預測 0", "預測 1"])
        ax.set_yticks([0, 1], [f"實際 0\n{P['mapping']['0']}", f"實際 1\n{P['mapping']['1']}"])
        ax.set_title(f"混淆矩陣（樣本內 n={n}，閾值 {args.threshold}）")
        save_plot(fig, od / "confusion_matrix.png")
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.hist([prob[yv == 0], prob[yv == 1]], bins=15, label=[f"實際 0", f"實際 1"], color=["#94a3b8", "#0f766e"])
        ax.axvline(args.threshold, ls="--", color="crimson")
        ax.set_xlabel("預測正類機率")
        ax.set_ylabel("次數")
        ax.legend()
        ax.set_title("預測機率分布（樣本內）")
        save_plot(fig, od / "probability_hist.png")
    show("模型摘要", info)
    show("係數（正規化係數為收縮估計，不套用未懲罰模型的推論）", coef)
    coef.to_csv(od / "coefficients.csv", index=False, encoding="utf-8-sig")
    save_json({"摘要": info, "係數": coef, "診斷": diag}, od / "fit.json")
    return info


def act_all(args, df):
    """依已確認的方案一次重現全部數值與圖表（不產生報告）。"""
    import copy
    act_inspect(args, df)
    act_outliers(args, df)
    P = prepare(df, args)
    act_eda(args, df, P)
    act_recommend(args, df, P)
    if args.lambda_bc not in (None, "", "none", "None"):
        a0 = copy.copy(args)
        a0.lambda_bc = None
        act_fit(a0, df, P, sub="fit_before_boxcox")
        act_boxcox(args, df, P)
    if args.candidates:
        act_aic(args, df, P)
    return act_fit(args, df, P, sub="fit_final")


# ----------------------------- Quarto 報告輔助 -----------------------------
# report.qmd 先在隱藏的程式區塊執行本程式（ACTION = "all"），所有圖表與表格在
# 渲染當下產生；正文再用下列函式取出結果，不引用任何事先存在的外部圖檔。
_LAST_OUTPUT = None


def _out(rel):
    p = Path(_LAST_OUTPUT or OUT_DIR) / rel
    if not p.exists():
        raise AnalysisError(f"找不到分析輸出：{p.resolve()}；請確認前面的分析區塊已執行成功")
    return p


def fig(rel):
    """顯示本次執行產生的圖，例如 fig("fit_final/residual_diagnostics.png")。"""
    from IPython.display import Image, display
    display(Image(filename=str(_out(rel))))


def table(obj, digits=3, index=False, columns=None, rename=None):
    """輸出 Markdown 表格；obj 可為輸出資料夾下的 CSV 相對路徑或 DataFrame。程式區塊須設 #| output: asis。"""
    df = pd.read_csv(_out(obj), encoding="utf-8-sig") if isinstance(obj, (str, Path)) else obj
    if columns:
        df = df[columns]
    if rename:
        df = df.rename(columns=rename)
    try:
        print(df.round(digits).to_markdown(index=index))
    except ImportError:
        raise AnalysisError("輸出表格需要 tabulate 套件：pip install tabulate")
    print()


def result(rel):
    """讀取本次執行輸出的 JSON，例如 result("fit_final/fit.json")["摘要"]["AIC"]。"""
    return json.loads(_out(rel).read_text(encoding="utf-8"))


ACTIONS = {"inspect": act_inspect, "outliers": act_outliers, "eda": act_eda, "recommend": act_recommend,
           "boxcox": act_boxcox, "aic": act_aic, "fit": act_fit, "all": act_all}


def build_parser():
    p = argparse.ArgumentParser(description="迴歸模型 Skill 工具腳本（AIC 選模、不使用交叉驗證）")
    a = p.add_argument
    a("--action", choices=list(ACTIONS), default=ACTION)
    a("--data", default=DATA_PATH)
    a("--sheet", default=SHEET)
    a("--encoding", default=ENCODING)
    a("--target", default=TARGET)
    a("--features", nargs="+", default=FEATURES)
    a("--output", default=OUT_DIR)
    a("--id-col", default=ID_COL)
    a("--y-type", choices=["continuous", "binary"], default=Y_TYPE)
    a("--positive", default=POSITIVE)
    a("--seed", type=int, default=SEED)
    a("--confirm-preprocessing", action="store_true", default=CONFIRM_PREPROCESSING)
    a("--drop-features", nargs="*", default=list(DROP_FEATURES))
    a("--keep-high-missing", nargs="*", default=list(KEEP_HIGH_MISSING))
    a("--categorical", nargs="*", default=list(CATEGORICAL))
    a("--categorical-missing", choices=["error", "most_frequent", "missing"], default=CATEGORICAL_MISSING)
    a("--drop-missing-y", action="store_true", default=DROP_MISSING_Y)
    a("--exclude-rows", nargs="*", default=list(EXCLUDE_ROWS))
    a("--model", choices=["linear", "polynomial", "ridge", "lasso", "logistic", "ridge_logistic", "lasso_logistic"], default=MODEL)
    a("--degree", type=int, default=DEGREE)
    a("--interaction", action="store_true", default=INTERACTION)
    a("--lambda-reg", type=float, default=LAMBDA_REG)
    a("--lambda-bc", default=LAMBDA_BC)
    a("--threshold", type=float, default=THRESHOLD)
    a("--candidates", nargs="*", default=list(CANDIDATES))
    a("--degrees", nargs="*", type=int, default=list(DEGREES))
    a("--ridge-lambdas", nargs="*", type=float, default=RIDGE_LAMBDAS)
    a("--lasso-lambdas", nargs="*", type=float, default=LASSO_LAMBDAS)
    a("--confirm-search", action="store_true", default=CONFIRM_SEARCH)
    a("--aic-compare-untransformed", action="store_true", default=AIC_COMPARE_UNTRANSFORMED)
    a("--bg-lags", type=int, default=BG_LAGS)
    a("--alpha-level", type=float, default=ALPHA_LEVEL)
    a("--show-dir", default=None, help="每張圖另複製到此資料夾，方便在對話中展示")
    return p


def main(argv=None):
    # parse_known_args：忽略 Jupyter 自動帶入的 -f kernel.json 等參數
    args, _unknown = build_parser().parse_known_args(argv)
    np.random.seed(args.seed)
    global SHOW_DIR, _LAST_OUTPUT
    SHOW_DIR = args.show_dir
    _LAST_OUTPUT = args.output
    FIGURES.clear()
    try:
        df = load(args)
        result = ACTIONS[args.action](args, df)
        if FIGURES:
            print("\n=== 本步驟產生的圖檔（須全部在對話中展示給使用者，再依圖解讀） ===")
            for f in FIGURES:
                print(f)
        return result
    except AnalysisError as e:
        print(f"分析失敗：{e}", file=sys.stderr)
        if in_jupyter():
            raise
        sys.exit(2)


if __name__ == "__main__":
    main()
