#!/usr/bin/env python3
"""互動式迴歸 Skill 的唯讀資料檢查、診斷與經授權的模型擬合。"""
import argparse
import json
import warnings
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.stats import jarque_bera
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Lasso, LogisticRegression, Ridge, LinearRegression
from sklearn.metrics import (accuracy_score, f1_score, log_loss, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, KFold, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def load(args):
    p = Path(args.data).resolve()
    if not p.exists():
        raise ValueError(f'找不到資料檔：{p}')
    if p.suffix.lower() == '.csv':
        df = pd.read_csv(p)
    elif p.suffix.lower() in ('.xlsx', '.xls'):
        df = pd.read_excel(p)
    else:
        raise ValueError('僅支援 CSV、XLSX、XLS')
    cols = [args.target] + args.features
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f'欄位不存在：{missing}')
    if args.target in args.features or len(set(args.features)) != len(args.features):
        raise ValueError('Y 不可同時為 X，X 欄位不可重複')
    return df


def kind(y):
    u = y.dropna().unique()
    if len(u) == 2:
        return 'binary'
    if pd.api.types.is_numeric_dtype(y) and len(u) > 2:
        return 'continuous'
    return 'unsupported'


def complete(df, args):
    sub = df[[args.target] + args.features].dropna()
    if len(sub) < 8:
        raise ValueError('完整案例不足 8 筆，無法執行目前的示範分析')
    return sub


def inspect(df, args):
    sub = df[[args.target] + args.features]
    result = {
        '樣本數': len(df), '觀測值總數': int(df.shape[0]), '變數總數': int(df.shape[1]), '欄位': list(sub.columns), 'Y類型': kind(df[args.target]),
        '缺失數': sub.isna().sum().to_dict(),
        '缺失比例': sub.isna().mean().to_dict(),
        '建議刪除X_需確認': [c for c in args.features if sub[c].isna().mean()>.20],
        '預設方案': '數值X缺失≤20%：中位數插補；>20%：確認後刪變數；類別X及缺失Y另確認',
        '欄位型態': {c: str(sub[c].dtype) for c in sub.columns},
        '唯一值數': sub.nunique(dropna=True).to_dict(),
        '重複資料列數': int(sub.duplicated().sum()),
        '完整案例數': int(len(sub.dropna())),
        '因Y或X缺失而排除的列數': int(len(sub) - len(sub.dropna())),
        'Y非缺失觀測數': int(df[args.target].notna().sum()),
        '各欄位非缺失觀測數': sub.notna().sum().astype(int).to_dict(),
        'Y各類別觀測數': {str(k): int(v) for k, v in df[args.target].value_counts(dropna=False).items()} if kind(df[args.target]) == 'binary' else None,
        '執行門檻_非統計充分性保證': {'診斷完整案例最低': 8, '擬合完整案例最低': 25, '預設交叉驗證折數': 5, '二元訓練集每類別至少': 5},
        '提醒': '僅進行檢查，尚未進行刪除、插補或模型擬合。'
    }
    return result


def matrix(df, features):
    x = pd.get_dummies(df[features], drop_first=True, dtype=float)
    x = x.astype(float)
    return x


def separation(x, y):
    # strict margin 1 is feasible iff strictly linearly separable (scaling argument)
    yy = np.asarray(y).astype(int)
    signs = np.where(yy == 1, 1., -1.)
    z = np.column_stack([np.ones(len(x)), np.asarray(x, dtype=float)])
    a = -signs[:, None] * z
    r = linprog(np.zeros(z.shape[1]), A_ub=a, b_ub=-np.ones(len(x)),
                bounds=[(None, None)] * z.shape[1], method='highs')
    return bool(r.success)


def diagnose(df, args):
    import statsmodels.api as sm
    from statsmodels.stats.diagnostic import het_breuschpagan
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    from statsmodels.stats.stattools import durbin_watson

    d, features, cat, num, log = prepare(df, args)
    if d[features].isna().any().any():
        raise ValueError("有缺失X時請先用 eda 或 fit；diagnose 不自行刪列或插補")
    x = matrix(d, features)
    y = d[args.target]
    z = sm.add_constant(x, has_constant='add').astype(float)
    rank = int(np.linalg.matrix_rank(z.to_numpy()))
    result = {'完整案例數': len(d), '設計矩陣欄數': z.shape[1], '秩': rank,
              '滿列秩': rank == z.shape[1], 'Y類型': kind(y),
              '殘差自由度_n減rank': int(len(d)-rank), '樣本數與參數比_n除rank': float(len(d)/rank) if rank else None,
              '警告': ['診斷使用完整案例，實際刪除資料前應先徵求使用者同意。']}
    if rank == z.shape[1] and len(d) > z.shape[1]:
        result['VIF'] = {c: float(variance_inflation_factor(z.to_numpy(), j))
                         for j, c in enumerate(z.columns) if c != 'const'}
    else:
        result['VIF'] = '設計矩陣秩不足或自由度不足，無法可靠計算 VIF'
    if kind(y) == 'continuous' and args.extra_diagnostics:
        if rank == z.shape[1] and len(d) > z.shape[1] + 1:
            fit = sm.OLS(y.astype(float), z).fit()
            residuals = fit.resid
            bp = het_breuschpagan(residuals, z)
            result['Breusch_Pagan_p'] = float(bp[1])
            result['Jarque_Bera_p'] = float(jarque_bera(residuals).pvalue)
            result['Durbin_Watson'] = float(durbin_watson(residuals))
            result['最大_Cooks_D'] = float(np.nanmax(fit.get_influence().cooks_distance[0]))
            result['OLS_R2'] = float(fit.rsquared)
        else:
            result['警告'].append('OLS 診斷需滿秩且有足夠殘差自由度')
    elif kind(y) == 'binary':
        codes = pd.Categorical(y).codes
        result['類別數量'] = {str(k): int(v) for k, v in y.value_counts().items()}
        result['偵測到嚴格完全分離'] = separation(x, codes)
        result['警告'].append('嚴格分離偵測不等於已排除準完全分離；請同時檢查 Logistic 擬合警告。')
    return result



def prepare(df, args):
    """Apply only explicitly confirmed choices; keep missing X for fold-local imputation."""
    if not args.confirm_preprocessing:
        raise ValueError('請先檢視 inspect 的方案；同意後加 --confirm-preprocessing')
    features = list(args.features)
    unknown = set(args.drop_features + args.categorical) - set(features)
    if unknown:
        raise ValueError(f'非所選 X 欄位：{sorted(unknown)}')
    ratios = df[features].isna().mean()
    high = list(ratios[ratios > .20].index)
    if set(args.drop_features) != set(high):
        raise ValueError(f'缺失 >20% 的變數為 {high}；同意刪除時以 --drop-features 明列全部欄位，否則停止並討論替代方案')
    features = [c for c in features if c not in args.drop_features]
    if not features:
        raise ValueError('刪除後沒有可用 X')
    categorical = [c for c in features if c in args.categorical or not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])]
    missing_cat = [c for c in categorical if df[c].isna().any()]
    if missing_cat and args.categorical_missing == 'error':
        raise ValueError(f'類別缺失需另確認：{missing_cat}；選擇 --categorical-missing most_frequent 或 missing')
    if df[args.target].isna().any() and not args.drop_missing_y:
        raise ValueError('Y 有缺失；同意排除時加 --drop-missing-y，不插補 Y')
    d = df.loc[df[args.target].notna(), [args.target] + features].copy()
    if len(d) < 8:
        raise ValueError('可用資料不足 8 筆，無法執行目前示範流程')
    for c in categorical:
        d[c] = d[c].map(lambda v: str(v) if pd.notna(v) else np.nan)
    numeric = [c for c in features if c not in categorical]
    if numeric and not np.isfinite(d[numeric].to_numpy(dtype=float)[~d[numeric].isna().to_numpy()]).all():
        raise ValueError('數值 X 含無限值，請另確認處理方案')
    log = {'原始筆數': len(df), '分析筆數': len(d), '排除缺失Y筆數': len(df)-len(d),
           '缺失比例': df[[args.target]+args.features].isna().mean().to_dict(),
           '刪除變數_已確認': args.drop_features, '類別處理': args.categorical_missing,
           '數值處理': '中位數；只在訓練資料及各CV折內估計'}
    return d, features, categorical, numeric, log


def plotting():
    import sys
    import matplotlib
    if 'ipykernel' not in sys.modules:
        matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Noto Sans CJK TC', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def save_plot(plt, path):
    import sys
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f'圖檔：{path.resolve()}')
    if 'ipykernel' in sys.modules:
        from IPython.display import display, Image
        display(Image(filename=str(path)))


def eda_tables(raw, x, y, out, categorical, numeric, log):
    """Exploration uses the training subset only; imputed copies never feed model CV."""
    plt = plotting()
    out.mkdir(parents=True, exist_ok=True)
    shown = x.copy()
    records = []
    for c in numeric:
        median = x[c].median()
        if pd.isna(median):
            raise ValueError(f'訓練資料 {c} 無可估計的中位數')
        records.append({'變數': c, '訓練缺失筆數': int(x[c].isna().sum()), '測試缺失筆數': log.get('測試缺失筆數', {}).get(c, 0), '訓練中位數': median})
        shown[c] = x[c].fillna(median)
    for c in categorical:
        fill = '__MISSING__' if log['類別處理'] == 'missing' else (x[c].mode().iloc[0] if not x[c].mode().empty else None)
        if x[c].isna().any() and fill is None:
            raise ValueError(f'類別 {c} 無可估計的眾數')
        shown[c] = x[c].fillna(fill) if fill is not None else x[c]
    shown[y.name] = y
    stats = shown.describe(include='all').T
    stats.to_csv(out/'descriptive_statistics.csv', encoding='utf-8-sig')
    pd.DataFrame(records).to_csv(out/'imputation.csv', index=False, encoding='utf-8-sig')
    missing = pd.DataFrame({'原始缺失筆數': raw.isna().sum(), '原始缺失比例': raw.isna().mean(),
                            'EDA訓練缺失_處理前': pd.concat([x,y],axis=1).isna().sum(), 'EDA訓練缺失_處理後': shown.isna().sum()})
    missing.to_csv(out/'missing_summary.csv', encoding='utf-8-sig')
    print('描述統計（訓練資料；數值X已按訓練中位數插補；單位未提供）')
    print(stats.to_string())
    print(missing.to_string())
    plots=[]
    def finish(name):
        save_plot(plt, out/name)
        plots.append(name)
    for i,c in enumerate(shown.columns):
        if c not in categorical and pd.api.types.is_numeric_dtype(shown[c]) and shown[c].nunique()>2:
            fig, axes=plt.subplots(1,2,figsize=(9,3))
            axes[0].hist(shown[c].dropna(),bins='auto'); axes[0].set_ylabel('Count')
            axes[1].boxplot(shown[c].dropna()); axes[1].set_ylabel(c)
            for ax in axes: ax.set_xlabel(c)
            fig.suptitle(f'Training EDA: {c}; X median imputed; n={len(shown)}; units unspecified')
            finish(f'eda_{i:03d}_distribution.png')
        else:
            counts=shown[c].value_counts(dropna=False)
            counts.rename_axis(c).to_csv(out/f'frequency_{i:03d}.csv',encoding='utf-8-sig')
            plt.figure(figsize=(7,4)); counts.plot.bar(); plt.ylabel('Count'); plt.title(f'Training: {c}; n={len(shown)}')
            finish(f'eda_{i:03d}_counts.png')
    if pd.api.types.is_numeric_dtype(y):
        for i,c in enumerate(numeric):
            plt.figure(figsize=(5,4)); plt.scatter(shown[c],y,alpha=.6); plt.xlabel(c); plt.ylabel(y.name)
            plt.title('Training; X median imputed; units unspecified')
            finish(f'eda_scatter_{i:03d}.png')
    if len(numeric)>1:
        corr=shown[numeric].corr(); corr.to_csv(out/'correlation.csv',encoding='utf-8-sig')
        fig,ax=plt.subplots(figsize=(6,5)); im=ax.imshow(corr,vmin=-1,vmax=1,cmap='coolwarm')
        ax.set_xticks(range(len(numeric)),numeric,rotation=45); ax.set_yticks(range(len(numeric)),numeric)
        fig.colorbar(im,ax=ax); ax.set_title('Training correlation; median imputed')
        finish('eda_correlation.png')
    return stats, records, plots


def explore(df,args):
    d,features,cat,num,log=prepare(df,args)
    # Standalone EDA reserves the same random holdout as fit; target semantics remain user-defined.
    tr,te=train_test_split(d,test_size=.2,random_state=args.seed)
    log['測試缺失筆數']=te[features].isna().sum().to_dict()
    out=Path(args.output)
    _,records,plots=eda_tables(df[[args.target]+args.features],tr[features],tr[args.target],out,cat,num,log)
    log['訓練插補紀錄']=records
    (out/'preprocessing.json').write_text(json.dumps(clean(log),ensure_ascii=False,indent=2),encoding='utf-8')
    return {'輸出資料夾':str(out),'前處理':log,'EDA圖':plots}


def estimator(model, categorical, numeric, categorical_missing="most_frequent"):
    pre = ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median')),
                          ('scale', StandardScaler())]), numeric),
        ('cat', Pipeline([('imputer', SimpleImputer(strategy='constant', fill_value='__MISSING__') if categorical_missing == 'missing' else SimpleImputer(strategy='most_frequent')),
                          ('onehot', OneHotEncoder(handle_unknown='ignore'))]), categorical),
    ])
    if model == 'linear':
        reg, params = LinearRegression(), {}
    elif model == 'polynomial':
        # polynomial expands the processed feature space, including dummy columns
        reg, params = LinearRegression(), {'poly__degree': [2, 3]}
    elif model == 'ridge':
        reg, params = Ridge(), {'model__alpha': [0.01, 0.1, 1, 10, 100]}
    elif model == 'lasso':
        reg, params = Lasso(max_iter=20000), {'model__alpha': [0.001, 0.01, 0.1, 1, 10]}
    elif model in ('logistic', 'ridge_logistic', 'lasso_logistic'):
        penalty = 'l1' if model == 'lasso_logistic' else 'l2'
        c = 1e6 if model == 'logistic' else 1.0
        reg = LogisticRegression(penalty=penalty, solver='liblinear', C=c, max_iter=10000)
        params = {} if model == 'logistic' else {'model__C': [0.01, 0.1, 1, 10, 100]}
    else:
        raise ValueError('不支援的模型')
    steps = [('pre', pre)]
    if model == 'polynomial':
        steps.append(('poly', PolynomialFeatures(include_bias=False)))
    steps.append(('model', reg))
    return Pipeline(steps), params


def fit(df, args):
    plt = plotting()
    d, features, cat, num, prep_log = prepare(df, args)
    target_kind = kind(d[args.target])
    is_class = args.model in ('logistic', 'ridge_logistic', 'lasso_logistic')
    if target_kind != ('binary' if is_class else 'continuous'):
        raise ValueError('模型與 Y 類型不相容')
    x, y = d[features], d[args.target]
    if is_class:
        y = pd.Series(pd.Categorical(y).codes, index=y.index)
    if is_class and y.value_counts().min() < 5:
        raise ValueError('某類別少於 5 筆，無法使用預設分層 5-fold 交叉驗證')
    if len(d) < 25:
        raise ValueError('目前示範腳本需要至少 25 筆完整案例以執行切分與 CV')
    xtr, xte, ytr, yte = train_test_split(x, y, test_size=0.2, random_state=args.seed,
                                           stratify=y if is_class else None)
    out = Path(args.output)
    prep_log['測試缺失筆數'] = xte.isna().sum().to_dict()
    stats, imputation, eda_plots = eda_tables(df[[args.target]+args.features], xtr, d.loc[xtr.index,args.target], out, cat, num, prep_log)
    prep_log['訓練插補紀錄'] = imputation
    (out/'preprocessing.json').write_text(json.dumps(clean(prep_log),ensure_ascii=False,indent=2),encoding='utf-8')
    pipe, grid = estimator(args.model, cat, num, args.categorical_missing)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed) if is_class else KFold(n_splits=5, shuffle=True, random_state=args.seed)
    if is_class and ytr.value_counts().min() < 5:
        raise ValueError('訓練集某類別不足 5 筆，無法進行 5-fold 分層交叉驗證')
    if grid and not args.confirm_tuning:
        raise ValueError("此模型包含參數搜尋；同意預設搜尋範圍後加 --confirm-tuning")
    if grid:
        search = GridSearchCV(pipe, grid, scoring='neg_log_loss' if is_class else 'neg_root_mean_squared_error', cv=cv, n_jobs=1)
        search.fit(xtr, ytr)
        pipe = search.best_estimator_
        best = search.best_params_
        cv_score = float(search.best_score_)
    else:
        pipe.fit(xtr, ytr)
        best, cv_score = {}, None
    # Audit fold-specific medians using the exact selected pipeline and CV partitions.
    if grid:
        from sklearn.base import clone
        fold_records=[]
        for fold,(train_idx,valid_idx) in enumerate(cv.split(xtr,ytr),1):
            fold_pipe=clone(pipe).fit(xtr.iloc[train_idx],ytr.iloc[train_idx])
            medians=fold_pipe.named_steps['pre'].named_transformers_['num'].named_steps['imputer'].statistics_ if num else []
            fold_records.append({'fold':fold,'訓練筆數':len(train_idx),'驗證筆數':len(valid_idx),'中位數':dict(zip(num,medians))})
        prep_log['CV每折插補']=fold_records
        (out/'preprocessing.json').write_text(json.dumps(clean(prep_log),ensure_ascii=False,indent=2),encoding='utf-8')
    pred = pipe.predict(xte)
    metrics = {'模型': args.model, '原始觀測值數': len(df), '樣本數_已確認前處理': len(d), '因缺失排除筆數': len(df)-len(d), '訓練筆數': len(xtr),
               '測試筆數': len(xte), '參數': best, '交叉驗證分數_負值損失': cv_score,
               '注意': '測試集只做最終評估；示範採隨機切分，不適用時間或群聚資料。'}
    if is_class:
        proba = pipe.predict_proba(xte)[:, 1]
        metrics.update({'Accuracy': accuracy_score(yte, pred), 'Precision': precision_score(yte, pred, zero_division=0),
                        'Recall': recall_score(yte, pred, zero_division=0), 'F1': f1_score(yte, pred, zero_division=0),
                        'Log_Loss': log_loss(yte, proba, labels=[0, 1])})
        metrics['ROC_AUC'] = roc_auc_score(yte, proba) if len(np.unique(yte)) == 2 else None
    else:
        proba = None
        metrics.update({'MAE': mean_absolute_error(yte, pred),
                        'RMSE': np.sqrt(mean_squared_error(yte, pred)), 'R2': r2_score(yte, pred)})
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'metrics.json').write_text(json.dumps(clean(metrics), ensure_ascii=False, indent=2), encoding='utf-8')
    preds = pd.DataFrame({'實際值': yte.to_numpy(), '預測值': pred}, index=yte.index)
    if is_class:
        preds['預測機率_正類'] = proba
    preds.to_csv(out / 'predictions.csv', index_label='原始列索引', encoding='utf-8-sig')
    try:
        names = pipe[:-1].get_feature_names_out()
    except Exception:
        names = [f'feature_{i}' for i in range(len(pipe.named_steps['model'].coef_.ravel()))]
    coefs = np.asarray(pipe.named_steps['model'].coef_).ravel()
    pd.DataFrame({'特徵': names, '係數': coefs}).to_csv(out / 'coefficients.csv', index=False, encoding='utf-8-sig')
    if is_class:
        from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
        cm=confusion_matrix(yte,pred,labels=[0,1])
        metrics['混淆矩陣_列實際欄預測']=cm.tolist()
        metrics['類別對應']={str(i):str(v) for i,v in enumerate(pd.Categorical(d[args.target]).categories)}
        metrics['正類']=1
        metrics['分類閾值']=.5
        (out/'metrics.json').write_text(json.dumps(clean(metrics),ensure_ascii=False,indent=2),encoding='utf-8')
        ConfusionMatrixDisplay(cm,display_labels=[0,1]).plot()
        save_plot(plt,out/'confusion_matrix.png')
        plt.figure(figsize=(6, 4))
        plt.hist(proba, bins=15)
        plt.xlabel('Predicted probability')
        plt.ylabel('Count')
        plt.title('Predicted probabilities')
    else:
        plt.figure(figsize=(6, 4))
        plt.scatter(pred, yte.to_numpy() - pred, alpha=.7)
        plt.axhline(0, linestyle='--')
        plt.xlabel('Fitted')
        plt.ylabel('Residual')
        plt.title('Residuals vs fitted')
    plt.tight_layout()
    plt.savefig(out / 'diagnostic_plot.png', dpi=160)
    plt.close()
    diagnosis = {'說明': '未自動執行額外推論檢定；EDA使用訓練資料，見EDA圖表。'}
    (out / 'diagnostics.json').write_text(json.dumps(clean(diagnosis), ensure_ascii=False, indent=2), encoding='utf-8')
    report = ['# 迴歸模型分析報告', '', f'- 模型：{args.model}', f'- 目標變數：{args.target}',
              f'- 解釋變數：{", ".join(args.features)}', f'- 分析筆數：{len(d)}',
              '- 前處理：經確認刪除高缺失X與缺失Y；保留X在Pipeline內插補、標準化及編碼',
              f'- 切分：80% 訓練／20% 測試，隨機種子 {args.seed}',
              '- 若模型需要調參：5-fold CV 僅在訓練資料進行', '', '## 評估結果', '']
    report.extend(f'- {k}: {v}' for k, v in clean(metrics).items())
    report.extend(['', '## 限制', '- 本報告不代表因果推論。',
                   '- 插補可能改變變異及變數關係；缺失機制未確認。',
                   '- 正則化係數不可直接套用 OLS 的 p-value 推論。',
                   '- 請檢視 diagnostics.json 與 diagnostic_plot.png。'])
    import base64
    report.extend(['', '## 缺失處理紀錄', '```json', json.dumps(clean(prep_log),ensure_ascii=False,indent=2), '```',
                   '', '## EDA（訓練資料）', '數值X使用訓練中位數插補；離群點不自動刪除。', '```text', stats.to_string(), '```'])
    for filename in eda_plots:
        encoded=base64.b64encode((out/filename).read_bytes()).decode('ascii')
        report.append(f'![{filename}](data:image/png;base64,{encoded})')
    eda_start=report.index('## 缺失處理紀錄')-1
    eda_section=report[eda_start:]
    report=report[:eda_start]
    insert_at=report.index('## 評估結果')-1
    report[insert_at:insert_at]=eda_section
    # 將實際執行指令與完整分析腳本嵌入 Markdown，方便在相同資料和套件環境重現。
    import shlex
    import importlib.metadata as metadata
    command = ['python', 'run_regression.py', 'fit', '--data', str(Path(args.data).resolve()),
               '--target', args.target, '--features', *args.features, '--model', args.model,
               '--output', str(out.resolve()), '--seed', str(args.seed)]
    command += ['--confirm-preprocessing']
    if args.drop_features: command += ['--drop-features', *args.drop_features]
    if args.categorical: command += ['--categorical', *args.categorical]
    command += ['--categorical-missing', args.categorical_missing]
    if args.drop_missing_y: command += ['--drop-missing-y']
    if args.confirm_tuning: command += ['--confirm-tuning']
    versions = {}
    for pkg in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'statsmodels', 'matplotlib', 'openpyxl']:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            versions[pkg] = '未安裝'
    source = Path(__file__).read_text(encoding='utf-8')
    report.extend(['', '## 可重現性與執行環境',
                   '- 需保留原始資料；報告不會內嵌原始 CSV/Excel。',
                   '- 重現需相同資料內容、Python 及套件版本；不同作業系統或數值函式庫可能造成微小差異。',
                   '- 使用以下指令前，請將 `run_regression.py` 儲存為同名檔案，並確認資料路徑正確。',
                   '', '### 套件版本', '```json', json.dumps(versions, ensure_ascii=False, indent=2), '```',
                   '', '### 安裝依賴', '```bash',
                   'python -m pip install numpy pandas scipy scikit-learn statsmodels matplotlib openpyxl',
                   '```', '', '### 重現指令', '```bash', shlex.join(command), '```',
                   '', '### 完整 Python 分析程式碼', '```python', source, '```'])
    (out / 'report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    return {'輸出資料夾': str(out), '評估結果': metrics}


def main():
    p = argparse.ArgumentParser(description='迴歸模型 Skill 分析腳本')
    p.add_argument('action', choices=['inspect', 'diagnose', 'eda', 'fit'])
    p.add_argument('--data', required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--features', nargs='+', required=True)
    p.add_argument('--model', choices=['linear', 'polynomial', 'logistic', 'ridge', 'lasso',
                                       'ridge_logistic', 'lasso_logistic'], default='linear')
    p.add_argument('--output', default='regression_results')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--extra-diagnostics', action='store_true', help='明確同意BP/JB/DW/Cooks額外診斷')
    p.add_argument('--confirm-preprocessing', action='store_true', help='確認前處理、80/20隨機切分與既有編碼標準化方案')
    p.add_argument('--drop-features', nargs='*', default=[], help='明確同意刪除的 >20%% 缺失 X')
    p.add_argument('--drop-missing-y', action='store_true')
    p.add_argument('--categorical', nargs='*', default=[], help='數字編碼的類別X也須列入')
    p.add_argument('--categorical-missing', choices=['error','most_frequent','missing'], default='error')
    p.add_argument('--confirm-tuning', action='store_true', help='同意腳本所列5折CV與參數搜尋範圍')
    args, _ = p.parse_known_args()
    try:
        df = load(args)
        if args.action == 'inspect':
            result = inspect(df, args)
        elif args.action == 'eda':
            result = explore(df,args)
        elif args.action == 'diagnose':
            result = diagnose(df, args)
        else:
            result = fit(df, args)
        print(json.dumps(clean(result), ensure_ascii=False, indent=2))
    except Exception as exc:
        p.exit(2, f'分析失敗：{exc}\n')


if __name__ == '__main__':
    main()
