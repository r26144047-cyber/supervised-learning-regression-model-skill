#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把設定好的分析程式填入 report.qmd 草稿，產生可獨立渲染的 report.qmd。

草稿中須有兩行 `# @@ANALYSIS_CODE@@`：
  1. 開頭的隱藏區塊（#| include: false）：渲染時執行分析，產生全部圖表與表格。
  2. 最後的「完整 Python 程式碼」區塊（#| eval: false）：只展示，不重複執行。
兩處會填入完全相同的程式碼。也會檢查草稿沒有引用外部圖檔或外部程式。

用法：
    python build_qmd.py --draft report_draft.qmd --code analysis.py --out report.qmd
"""
import argparse
import re
import sys
from pathlib import Path

MARK = "# @@ANALYSIS_CODE@@"
FORBIDDEN = [
    (r"!\[[^\]]*\]\((?!data:)[^)]+\)", "Markdown 圖片連結（請改用 fig(...) 在渲染時產生）"),
    (r"\\includegraphics", "LaTeX \\includegraphics"),
    (r"\\input\{|\\include\{", "LaTeX \\input／\\include"),
    (r"\{\{<\s*(include|embed)", "Quarto include／embed"),
    (r"^#\|\s*file\s*:", "程式區塊的 file: 選項"),
    (r"^\s*(import|from)\s+run_regression\b", "import 外部的 run_regression 模組"),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--draft", required=True)
    p.add_argument("--code", required=True)
    p.add_argument("--out", default="report.qmd")
    a, _ = p.parse_known_args()
    draft = Path(a.draft).read_text(encoding="utf-8")
    code = Path(a.code).read_text(encoding="utf-8").rstrip("\n")
    errors = []
    if draft.count(MARK) != 2:
        errors.append(f"草稿中 {MARK} 應出現 2 次，實際 {draft.count(MARK)} 次")
    if not re.search(r'^ACTION\s*=\s*"all"', code, re.M):
        errors.append('分析程式開頭須設定 ACTION = "all"')
    if "```" in code:
        errors.append("分析程式中不可含 ``` ，會破壞 qmd 程式區塊")
    for pat, name in FORBIDDEN:
        if re.search(pat, draft, re.M):
            errors.append(f"草稿引用了外部檔案：{name}")
    if errors:
        sys.exit("建立失敗：\n- " + "\n- ".join(errors))
    out = draft.replace(MARK, code)
    blocks = re.findall(r"```\{python\}\n(.*?)```", out, re.S)
    full = [b for b in blocks if code in b]
    if len(full) != 2:
        sys.exit("建立失敗：填入後找不到兩個含完整程式碼的 {python} 區塊")
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"已建立：{Path(a.out).resolve()}（程式碼 {code.count(chr(10)) + 1} 行，填入 2 處）")


if __name__ == "__main__":
    main()
