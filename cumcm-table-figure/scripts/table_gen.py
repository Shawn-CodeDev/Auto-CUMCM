"""国赛三线表生成器：从数据文件生成可直接 \\input 的 LaTeX 表格源码。

解决的问题（每个写论文的队伍都会踩）：
  1. 手敲表格数字 → 与结果文件不一致（论文与程序结果不符，属于可能取消评奖资格的硬伤）
  2. 最优值忘了加粗 / 加粗了但摘要没同步改
  3. 缺失值留空 → 评委分不清"漏了"还是"为零"
  4. 同一列小数位不齐 → 小数点对不齐，读者没法纵向扫读
  5. 单位写在格子里的数字后面 → 表头拥挤、单位重复 20 遍
  6. 忘记写表注（数据来源 / 单位 / 空值含义 / 显著性定义）

用法一（推荐，写完 spec 后反复重跑）：
    python table_gen.py --input results/E04/sensitivity.csv \\
                        --spec  results/E04/table_spec.json \\
                        --out   paper/tables/tab_sensitivity.tex

用法二（先让脚本猜一个 spec，再人工改）：
    python table_gen.py --input results/E04/sensitivity.csv --emit-spec results/E04/table_spec.json

用法三（自检，不需要任何输入文件）：
    python table_gen.py

spec 的最小形态（完整字段见 _build_default_spec 与 --emit-spec 的输出）：
    {
      "caption": "关键参数 ±10% 扰动下的最优遮蔽时长（数据来源：E05）",
      "label": "tab:sensitivity",
      "align": "right",                      // right（默认，稳）| decimal（siunitx S 列）
      "notes": ["弹性系数 =(ΔT/T)/(Δp/p)。"],
      "midrule_before": [4],                 // 在第 4 行数据前插一条 \\midrule（如"合计"行）
      "bold_rows": [4],                      // 整行加粗（如"合计"行）
      "columns": [
        {"key": "参数", "header": "参数", "kind": "text"},
        {"key": "T_lo", "header": "下限 $T^{-}$", "unit": "s", "decimals": 2, "best": "min"},
        {"key": "T_hi", "header": "上限 $T^{+}$", "unit": "s", "decimals": 2, "best": "max"},
        {"key": "弹性系数", "header": "弹性系数", "decimals": 2}
      ]
    }

设计取舍（重要）：
  * 默认 align="right"：同列定长小数 + 右对齐 ⇒ 小数点自然对齐，且 \\textbf 加粗绝对安全，
    任何 TeX 发行版都能编译。这是推荐的默认档。
  * align="decimal" 用 siunitx 的 S 列（模板 cumcm2026.sty 已加载 siunitx），能处理 ± 、范围、
    千分位；空值用 \\multicolumn{1}{c}{—} 逃逸，加粗用 \\bfseries（siunitx 会保留该字体命令）。
    若你的 siunitx 版本报 "Invalid number"，把该单元格改成 \\multicolumn 逃逸，或直接用
    align="right"。
  * 生成物只负责"表体 + 表题 + 表注"，不含 \\cmidrule 分组线等手工精修——
    精修请在生成物基础上改，但**不要改数字**：数字永远来自数据源。
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

MISSING_TOKEN = "—"          # 空值/缺测的统一符号（不是短横线 "-"，短横线像负号）
MISSING_RAW = {"", "-", "--", "—", "nan", "none", "null", "na", "n/a", "/"}


# --------------------------------------------------------------------------- #
# 数据读取：先转成纯 Python 结构，后续逻辑不依赖 pandas
# --------------------------------------------------------------------------- #
@dataclass
class Table:
    headers: list[str]                 # 原始列名
    rows: list[dict[str, Any]]         # 每行 {列名: 原始值}


def read_table(path: str) -> Table:
    """读 CSV/TSV/Excel。Excel 需要 pandas + openpyxl；CSV 有标准库兜底。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        return _read_excel(path)
    return _read_delimited(path)


def _read_delimited(path: str) -> Table:
    """读 CSV/TSV。编码按 utf-8-sig → gbk 依次尝试（Excel 导出的中文 CSV 常见 GBK）。"""
    try:
        import pandas as pd  # noqa: PLC0415
        last_err: Exception | None = None
        for enc in ("utf-8-sig", "gbk", "utf-8"):
            try:
                df = pd.read_csv(path, sep=None, engine="python", dtype=object, encoding=enc)
                break
            except UnicodeDecodeError as exc:      # 换下一个编码再试
                last_err = exc
        else:
            raise SystemExit(f"无法识别 {path} 的编码（试过 utf-8-sig / gbk / utf-8）：{last_err}")
        df = df.where(df.notna(), None)
        df.columns = [_clean_key(c) for c in df.columns]   # 去掉 BOM 与首尾空白
        return Table(headers=[str(c) for c in df.columns],
                     rows=[{_clean_key(k): v for k, v in rec.items()}
                           for rec in df.to_dict(orient="records")])
    except ImportError:
        pass
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.DictReader(fh, dialect=dialect)
        headers = [_clean_key(h) for h in (reader.fieldnames or []) if h is not None]
        rows = [{_clean_key(k): v for k, v in rec.items() if k is not None} for rec in reader]
    return Table(headers=headers, rows=rows)


def _clean_key(key: Any) -> str:
    """列名清洗：去 BOM（\\ufeff）、去首尾空白。BOM 不清理会让 spec 里的列名对不上数据。"""
    return str(key).replace("\ufeff", "").strip()


def _read_excel(path: str) -> Table:
    try:
        import pandas as pd  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            f"读取 {path} 需要 pandas 与 openpyxl（当前环境未安装 pandas）。\n"
            f"替代方案：在 Excel 里另存为 CSV，再用本脚本读 CSV。"
        ) from exc
    df = pd.read_excel(path, dtype=object)
    df = df.where(df.notna(), None)
    df.columns = [_clean_key(c) for c in df.columns]
    return Table(headers=[str(c) for c in df.columns],
                 rows=[{_clean_key(k): v for k, v in rec.items()}
                       for rec in df.to_dict(orient="records")])


# --------------------------------------------------------------------------- #
# 数值解析与格式化
# --------------------------------------------------------------------------- #
def parse_number(value: Any) -> float | None:
    """把单元格解析成 float；解析不出来（缺测、文字、"-"）返回 None。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return None if (isinstance(value, float) and math.isnan(value)) else float(value)
    text = str(value).strip()
    if text.lower() in MISSING_RAW:
        return None
    text = text.replace(",", "").replace("\\,", "").replace("%", "")
    text = text.replace("−", "-").replace("±", "")   # 全角减号 / 去 ± 前缀
    try:
        return float(text)
    except ValueError:
        return None


def is_number(value: Any) -> bool:
    return parse_number(value) is not None


def format_number(value: float, decimals: int, *, signed: bool = False,
                  thin_space: bool = True, escape: bool = True) -> str:
    """定长小数格式化。同列 decimals 相同 ⇒ 右对齐即小数点对齐。"""
    if abs(value) < 0.5 * 10 ** (-decimals):     # 消除 -0.00
        value = 0.0
    text = f"{value:,.{decimals}f}" if thin_space else f"{value:.{decimals}f}"
    if thin_space:
        text = text.replace(",", "\\,")          # 千分位用 LaTeX 细空格，避免与列分隔符混淆
    if signed and value > 0 and not text.startswith("+"):
        text = "+" + text
    return text


def latex_escape(text: str) -> str:
    """转义正文里的特殊字符，但不动数学模式 $...$、已有命令（\\% / \\textbf）与换行。

    逐字符扫描而不是批量 replace，是为了避免把已经转义好的 \\% 二次转义成 \\\\%。
    """
    parts = str(text).split("$")
    for i in range(0, len(parts), 2):            # 偶数段 = 数学模式之外
        seg = parts[i]
        out: list[str] = []
        j = 0
        while j < len(seg):
            ch = seg[j]
            if ch == "\\" and j + 1 < len(seg):   # 已有命令/转义序列原样保留
                out.append(seg[j:j + 2])
                j += 2
                continue
            out.append("\\" + ch if ch in "&%#_" else ch)
            j += 1
        parts[i] = "".join(out)
    return "$".join(parts)


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in MISSING_RAW


def _terminate(text: str) -> str:
    """给表注补齐句末标点：多条注连排时不加空格（中文排版习惯），靠标点断句。"""
    text = str(text).strip()
    return text if text.endswith(("。", "；", "！", "？", ".", ";", ":")) else text + "。"


# --------------------------------------------------------------------------- #
# 列规格
# --------------------------------------------------------------------------- #
@dataclass
class Column:
    key: str
    header: str
    unit: str | None = None
    decimals: int | None = None
    kind: str = "auto"          # auto | number | text
    best: str | None = None     # None | "min" | "max"
    bold_best: bool = True
    signed: bool = False
    thin_space: bool = True
    decimals_from_data: bool = False

    def resolved_kind(self) -> str:
        return "number" if self.kind == "auto" and self.decimals is not None else (
            self.kind if self.kind != "auto" else "text")

    def display_header(self) -> str:
        head = self.header if not self.unit else f"{self.header} ({self.unit})"
        return latex_escape(head)


def infer_decimals(values: Iterable[Any], cap: int = 6) -> int:
    """从数据推断小数位：取出现次数最多的位数（看不出就用 2 位）。"""
    counts: dict[int, int] = {}
    for v in values:
        if not is_number(v):
            continue
        text = str(v).strip().replace(",", "").replace("%", "")
        if "e" in text.lower():
            continue
        if "." in text:
            counts[len(text.split(".")[1])] = counts.get(len(text.split(".")[1]), 0) + 1
        else:
            counts[0] = counts.get(0, 0) + 1
    if not counts:
        return 2
    best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return min(best, cap)


def build_columns(spec: dict, table: Table) -> list[Column]:
    cols: list[Column] = []
    for raw in spec.get("columns", []):
        col = Column(
            key=str(raw.get("key", raw.get("name", ""))),
            header=str(raw.get("header", raw.get("name", raw.get("key", "")))),
            unit=raw.get("unit"),
            decimals=raw.get("decimals"),
            kind=str(raw.get("kind", raw.get("type", "auto"))),
            best=raw.get("best"),
            bold_best=bool(raw.get("bold_best", True)),
            signed=bool(raw.get("signed", False)),
            thin_space=bool(raw.get("thin_space", True)),
        )
        if col.key not in table.headers:
            raise SystemExit(f"spec 里的列 {col.key!r} 不在数据文件里；"
                             f"可用列：{table.headers}")
        if col.kind == "auto":
            numeric = all(is_missing(r.get(col.key)) or is_number(r.get(col.key))
                          for r in table.rows)
            col.kind = "number" if numeric else "text"
        if col.kind == "number" and col.decimals is None:
            col.decimals = infer_decimals(r.get(col.key) for r in table.rows)
            col.decimals_from_data = True
        cols.append(col)
    if not cols:
        raise SystemExit("spec 里没有任何列（columns 为空）。")
    return cols


_CJK_UNITS = ("元", "万元", "亿元", "件", "人", "次", "小时", "天", "月", "年", "台", "个",
              "米", "千米", "公里", "吨", "千克", "克", "秒", "分", "度", "摄氏度", "点", "户")
_UNIT_TAIL = re.compile(r"^[A-Za-z%℃°μ/·\s0-9^.\\{}$\-\u00b2\u00b3]+$")


def _split_unit(header: str) -> tuple[str, str | None]:
    """把 "日成本(元)" 拆成 ("日成本", "元")；拆不出来就原样返回。

    只在括号内容**像单位**时才拆（纯拉丁/符号单位，或常见中文量词），
    避免把 "问题一(最优)" 这种括号说明误当单位。
    """
    m = re.match(r"^(.*?)\s*[（(]\s*([^（()）]{1,8})\s*[)）]\s*$", header)
    if not m:
        return header, None
    name, inner = m.group(1).strip(), m.group(2).strip()
    if not name:
        return header, None
    if inner in _CJK_UNITS or _UNIT_TAIL.match(inner):
        return name, inner
    return header, None


def default_spec(table: Table, *, caption: str = "（请填写表题）",
                 label: str = "tab:result") -> dict:
    """没有 spec 时按数据猜一个：全数字列 2 位小数，第一列当文字列，不做最优值加粗。"""
    columns = []
    for i, head in enumerate(table.headers):
        numeric = all(is_missing(r.get(head)) or is_number(r.get(head)) for r in table.rows)
        name, unit = _split_unit(head)
        col: dict[str, Any] = {"key": head, "header": name if unit else head}
        if unit:
            col["unit"] = unit
        if numeric and i > 0:
            col["kind"] = "number"
            col["decimals"] = infer_decimals(r.get(head) for r in table.rows)
        else:
            col["kind"] = "text"
        columns.append(col)
    return {"caption": caption, "label": label, "align": "right",
            "columns": columns, "notes": [],
            "_提示": "这份 spec 是脚本猜的，请人工核对：单位、有效位数、最优值加粗方向（best）"}


# --------------------------------------------------------------------------- #
# 最优值定位
# --------------------------------------------------------------------------- #
def find_best_indices(table: Table, col: Column) -> set[int]:
    if col.best not in ("min", "max"):
        return set()
    vals = [(i, parse_number(r.get(col.key))) for i, r in enumerate(table.rows)]
    vals = [(i, v) for i, v in vals if v is not None]
    if not vals:
        return set()
    target = min(v for _, v in vals) if col.best == "min" else max(v for _, v in vals)
    return {i for i, v in vals if abs(v - target) <= 1e-12}


# --------------------------------------------------------------------------- #
# LaTeX 生成
# --------------------------------------------------------------------------- #
@dataclass
class GenOptions:
    align: str = "right"                 # right | decimal
    size: str = "small"                  # \small = 比正文小一号
    placement: str = "htbp"
    missing: str = MISSING_TOKEN
    escape_text: bool = True
    header_center: bool = True           # 数字列的表头居中（右对齐列里的长表头很难看）
    note_lines: list[str] = field(default_factory=list)


def _table_format(table: Table, col: Column) -> str:
    """siunitx S 列的 table-format：整数位取该列最大位数，小数位取配置值。

    siunitx 以小数点为锚点对齐，符号（+/-）只向左侧突出、不会破坏对齐；
    但如果 table-format 的整数位不够，siunitx 会对每个超宽单元格发警告。
    因此这里对可能出现符号或负数的列多留一位整数位，宁可列宽一点也不要警告。
    """
    ints = 1
    has_sign = col.signed
    for row in table.rows:
        v = parse_number(row.get(col.key))
        if v is None:
            continue
        ints = max(ints, len(str(int(abs(v)))))
        if v < 0:
            has_sign = True
    return f"{ints + (1 if has_sign else 0)}.{col.decimals}"


def generate_table(table: Table, columns: Sequence[Column], *,
                   caption: str, label: str, opt: GenOptions | None = None,
                   midrule_before: Sequence[int] = (),
                   bold_rows: Sequence[int] = (),
                   source: str | None = None) -> str:
    """生成完整的 table 环境源码（表题在表上方、三线表、含表注）。"""
    opt = opt or GenOptions()
    if opt.align not in ("right", "decimal"):
        raise SystemExit(f"align 只能是 'right' 或 'decimal'，收到 {opt.align!r}")

    # ---- 1) 列格式 ----
    specs: list[str] = []
    for c in columns:
        if c.kind == "number" and opt.align == "decimal":
            specs.append(f"S[table-format={_table_format(table, c)}]")
        elif c.kind == "number":
            specs.append("r")
        else:
            specs.append("l")
    colspec = "@{}" + " ".join(specs) + "@{}"

    # ---- 2) 最优值 ----
    best_idx = {c.key: find_best_indices(table, c) for c in columns if c.best in ("min", "max")}

    # ---- 3) 表头 ----
    heads = []
    for c in columns:
        head = c.display_header()
        if c.kind == "number" and opt.align == "decimal":
            heads.append("{" + head + "}")                      # siunitx 要求表头加花括号
        elif c.kind == "number" and opt.header_center:
            heads.append(r"\multicolumn{1}{c}{" + head + "}")    # 数字列表头居中
        else:
            heads.append(head)
    lines = ["    " + " & ".join(heads) + r" \\"]

    # ---- 4) 表体 ----
    bold_row_set = {int(i) for i in bold_rows}
    mid_set = {int(i) for i in midrule_before}
    body: list[str] = []
    for i, row in enumerate(table.rows):
        if i in mid_set:
            body.append(r"    \midrule")
        cells: list[str] = []
        for c in columns:
            raw = row.get(c.key)
            if is_missing(raw):
                cells.append((r"\multicolumn{1}{c}{" + opt.missing + "}")
                             if (c.kind == "number" and opt.align == "decimal")
                             else opt.missing)
                continue
            if c.kind == "number":
                num = parse_number(raw)
                if num is None:                      # 列里混进了文字 → 原样输出并提示
                    cells.append(latex_escape(str(raw)) if opt.escape_text else str(raw))
                    continue
                text = format_number(num, c.decimals or 0, signed=c.signed,
                                     thin_space=c.thin_space and opt.align == "right",
                                     escape=opt.escape_text)
                want_bold = (i in bold_row_set) or (
                    c.bold_best and c.best in ("min", "max") and i in best_idx.get(c.key, set()))
                if want_bold:
                    text = (r"\bfseries " + text) if opt.align == "decimal" else r"\textbf{" + text + "}"
            else:
                text = latex_escape(str(raw)) if opt.escape_text else str(raw)
                if i in bold_row_set:
                    text = r"\textbf{" + text + "}"
            cells.append(text)
        body.append("    " + " & ".join(cells) + r" \\")

    # ---- 5) 表注 ----
    notes = list(opt.note_lines)
    if any(c.best in ("min", "max") and c.bold_best for c in columns):
        notes.append("加粗为该列最优值。")
    if any(is_missing(r.get(c.key)) for r in table.rows for c in columns):
        notes.append(f"``{opt.missing}'' 表示该指标缺测或不适用。")
    units = [f"{c.header}（{c.unit}）" for c in columns if c.unit]
    if units:
        notes.append("单位：" + "、".join(units) + "。")
    if source:
        notes.append(f"数据来源：{source}。")
    notes = [latex_escape(_terminate(n)) if opt.escape_text else _terminate(n) for n in notes]

    # ---- 6) 拼装 ----
    out: list[str] = [
        "% 由 skills/cumcm-table-figure/scripts/table_gen.py 生成",
        "% 重新生成：修改数据源或 spec 后重跑脚本；请勿手改数字。",
        f"\\begin{{table}}[{opt.placement}]",
        r"  \centering",
        f"  \\caption{{{caption}}}",
        f"  \\label{{{label}}}",
        f"  \\{opt.size}",
        f"  \\begin{{tabular}}{{{colspec}}}",
        r"    \toprule",
    ]
    out += lines
    out.append(r"    \midrule")
    out += body
    out.append(r"    \bottomrule")
    out.append(r"  \end{tabular}")
    if notes:
        out.append("")
        out.append(r"  \vspace{2pt}")
        out.append(r"  {\footnotesize 注：" + "".join(notes) + "}")
    out.append(r"\end{table}")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# 静态自检：不装 TeX 也能查出的低级错误
# --------------------------------------------------------------------------- #
def _expand_colspec(spec: str) -> str:
    spec = re.sub(r"[@!]\{[^{}]*\}", "", spec)
    spec = re.sub(r"\*\{(\d+)\}\{([^{}]*)\}", lambda m: m.group(2) * int(m.group(1)), spec)
    spec = re.sub(r"[pmb]\{[^{}]*\}", "X", spec)
    spec = re.sub(r"S\[[^\]]*\]", "S", spec)
    spec = re.sub(r"[><]\{[^{}]*\}", "", spec)
    return re.sub(r"\s+", "", spec)


def validate_tex(tex: str) -> list[str]:
    """返回问题清单（空列表 = 通过）。检查项见 SKILL.md 第 4 步。"""
    issues: list[str] = []
    lines = tex.splitlines()
    code = [ln for ln in lines if not ln.lstrip().startswith("%")]

    # (1) 环境配对
    stack: list[str] = []
    for ln in code:
        for m in re.finditer(r"\\(begin|end)\{([^}]+)\}", ln):
            kind, name = m.group(1), m.group(2)
            if kind == "begin":
                stack.append(name)
            elif not stack:
                issues.append(f"多出一个 \\end{{{name}}}（没有对应的 \\begin）")
            elif stack[-1] != name:
                issues.append(f"环境嵌套错误：期望 \\end{{{stack[-1]}}}，实际 \\end{{{name}}}")
                stack.pop()
            else:
                stack.pop()
    if stack:
        issues.append("未闭合的环境：" + "、".join(stack))

    # (2) 花括号配对（忽略 \{ \}）
    clean = re.sub(r"\\[{}]", "", "\n".join(code))
    if clean.count("{") != clean.count("}"):
        issues.append(f"花括号不配对：{{ {clean.count('{')} 个，}} {clean.count('}')} 个")

    # (3) 三线表合规
    if re.search(r"\\hline", "\n".join(code)):
        issues.append("出现 \\hline：三线表不允许（用 \\toprule/\\midrule/\\bottomrule）")
    for m in re.finditer(r"\\begin\{(?:tabular|tabularx|longtable)\}\{([^{}]*)\}", "\n".join(code)):
        raw = m.group(1)
        body = raw.lstrip("{[")
        if re.search(r"(?<!@)(?<!\\)\|", body) or body.strip().startswith("|"):
            issues.append(f"列格式里有竖线：{raw!r}（三线表严禁竖线）")
    if re.search(r"\\resizebox", "\n".join(code)):
        issues.append("出现 \\resizebox：会把表内字号一起缩小，改用删列/\\small/拆表")

    # (4) 列数一致性（tabular 与 tabularx 都查）
    joined = "\n".join(code)
    colspec_re = (r"\\begin\{tabular\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
                  r"|\\begin\{tabularx\}\{[^{}]*\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
    m = re.search(colspec_re, joined)
    if m:
        ncol = len(_expand_colspec(m.group(1) or m.group(2)))
        in_body = False
        for ln in code:
            s = ln.strip()
            if s.startswith(r"\toprule") or s.startswith(r"\midrule"):
                in_body = True
                continue
            if s.startswith(r"\bottomrule"):
                in_body = False
                continue
            if not in_body or r"\\" not in s:
                continue
            core = s.rstrip()
            core = re.sub(r"\\\\\s*(\[[^\]]*\])?$", "", core).strip()
            if not core or core.startswith("%"):
                continue
            cells = core.count("&") + 1
            for mm in re.finditer(r"\\multicolumn\{(\d+)\}", core):
                cells += int(mm.group(1)) - 1
            if cells != ncol:
                issues.append(f"列数不一致：表体 {cells} 列 vs 列格式 {ncol} 列 → {s[:48]}...")

    # (5) 表题在表体之前
    pos_cap = tex.find(r"\caption")
    pos_tab = tex.find(r"\begin{tabular}")
    if pos_cap == -1:
        if r"\begin{table}" in tex or r"\begin{longtable}" in tex:
            issues.append("没有 \\caption（表题必须写）")
    elif pos_tab != -1 and pos_cap > pos_tab:
        issues.append("\\caption 出现在 tabular 之后：表题必须在表体上方")

    # (6) 占位符 / 未格式化残留
    for token in ("nan", "NaN", "None", "TODO", "???"):
        if re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", tex):
            issues.append(f"残留占位符 {token!r}：检查数据源与表注是否写全")
    return issues


def describe(table: Table, columns: Sequence[Column], tex: str) -> str:
    n_missing = sum(1 for r in table.rows for c in columns if is_missing(r.get(c.key)))
    n_bold = tex.count(r"\textbf{") + len(re.findall(r"\\bfseries ", tex))
    return (f"{len(table.rows)} 行 × {len(columns)} 列；空值 {n_missing} 个；"
            f"加粗单元格 {n_bold} 个；源码 {len(tex.splitlines())} 行 / {len(tex)} 字符")


def run(input_path: str, out_path: str, spec_path: str | None, *, align: str | None = None,
        source: str | None = None, caption: str | None = None,
        label: str | None = None, quiet: bool = False) -> dict:
    """完整流程：读数据 → 建列规格 → 生成 → 静态校验 → 落盘。返回结果摘要。"""
    table = read_table(input_path)
    if spec_path and os.path.exists(spec_path):
        # utf-8-sig：Windows 记事本/PowerShell 存出的 JSON 常带 BOM，直接 utf-8 读会 JSONDecodeError
        with open(spec_path, "r", encoding="utf-8-sig") as fh:
            try:
                spec = json.load(fh)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"spec 文件 {spec_path} 不是合法 JSON：{exc}") from exc
    else:
        spec = default_spec(table, caption=caption or "（请填写表题）",
                            label=label or "tab:result")
        if not quiet:
            print(f"[table_gen] 未提供 spec，已按数据推断列规格（请人工核对单位与有效位数）")

    columns = build_columns(spec, table)
    opt = GenOptions(
        align=align or spec.get("align", "right"),
        size=spec.get("size", "small"),
        placement=spec.get("placement", "htbp"),
        missing=spec.get("missing", MISSING_TOKEN),
        note_lines=[str(n) for n in spec.get("notes", [])],
    )
    tex = generate_table(
        table, columns,
        caption=caption or spec.get("caption", "（请填写表题）"),
        label=label or spec.get("label", "tab:result"),
        opt=opt,
        midrule_before=spec.get("midrule_before", []),
        bold_rows=spec.get("bold_rows", []),
        source=source or spec.get("source"),
    )
    issues = validate_tex(tex)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(tex)
    if not quiet:
        print(f"[table_gen] 已写出 {out_path}")
        print(f"[table_gen] {describe(table, columns, tex)}")
        print(f"[table_gen] 静态校验：{'通过（0 问题）' if not issues else str(len(issues)) + ' 个问题'}")
        for it in issues:
            print(f"           ! {it}")
    return {"path": out_path, "issues": issues, "summary": describe(table, columns, tex),
            "tex": tex}


# --------------------------------------------------------------------------- #
# 自检：用合成数据生成两张表（right / decimal），跑静态校验并打印
# --------------------------------------------------------------------------- #
def _sample_table() -> Table:
    """合成数据：三枚干扰弹的投放方案（含缺测值与合计行）。全部为示意性数据。

    故意不引入随机数：自检输出必须逐字可复现，否则"重跑一遍对不对"就无从判断。
    """
    rows = []
    for i, (t0, z0, dur) in enumerate([(115.62, 1662, 1.05), (127.48, 1611, 2.15),
                                       (139.35, 1558, 1.12)], start=1):
        rows.append({"弹序": f"弹 {i}", "投放时刻 (s)": t0, "起爆点 z (m)": z0,
                     "有效时长 (s)": dur, "相对提升 (%)": None})
    rows.append({"弹序": "合计（并集）", "投放时刻 (s)": None, "起爆点 z (m)": None,
                 "有效时长 (s)": 4.62, "相对提升 (%)": 149.7})
    return Table(headers=["弹序", "投放时刻 (s)", "起爆点 z (m)", "有效时长 (s)", "相对提升 (%)"],
                 rows=rows)


def _selfcheck() -> int:
    print("=== cumcm-table-figure / table_gen.py 自检 ===")
    print(f"Python {sys.version.split()[0]}；工作目录 {os.getcwd()}")
    table = _sample_table()
    spec = {
        "caption": "三枚干扰弹的最优投放方案明细（示意性数据，自检用）",
        "label": "tab:selfcheck",
        "align": "right",
        "source": "E02（合成数据，仅用于自检）",
        "midrule_before": [4],
        "bold_rows": [4],
        "notes": ["合计行为三个遮蔽区间的并集长度，不等于三行之和。"],
        "columns": [
            {"key": "弹序", "header": "弹序", "kind": "text"},
            {"key": "投放时刻 (s)", "header": "投放时刻 $t_{1,i}$", "unit": "s",
             "decimals": 2, "best": "min"},
            {"key": "起爆点 z (m)", "header": "起爆点 $z$", "unit": "m", "decimals": 0},
            {"key": "有效时长 (s)", "header": "有效时长", "unit": "s",
             "decimals": 2, "best": "max"},
            {"key": "相对提升 (%)", "header": "相对提升", "unit": "\\%",
             "decimals": 1, "best": "max", "signed": True},
        ],
    }
    print(f"[1/6] 合成数据：{len(table.rows)} 行 × {len(table.headers)} 列"
          f"（含 2 个空值、1 个合计行）")

    columns = build_columns(spec, table)
    print("[2/6] 列规格：" + " | ".join(
        f"{c.header}[{c.kind},dec={c.decimals},best={c.best}]" for c in columns))

    here = os.path.dirname(os.path.abspath(__file__))
    out_right = os.path.join(here, "_selfcheck_table_right.tex")
    tex_right = generate_table(table, columns, caption=spec["caption"], label=spec["label"],
                               opt=GenOptions(align="right", note_lines=spec["notes"]),
                               midrule_before=spec["midrule_before"],
                               bold_rows=spec["bold_rows"], source=spec["source"])
    issues_right = validate_tex(tex_right)
    with open(out_right, "w", encoding="utf-8") as fh:
        fh.write(tex_right)
    print(f"[3/6] right 模式（默认）：{describe(table, columns, tex_right)} → "
          f"{out_right}")
    print(f"      静态校验：{'通过（0 问题）' if not issues_right else issues_right}")

    out_dec = os.path.join(here, "_selfcheck_table_decimal.tex")
    tex_dec = generate_table(table, columns, caption=spec["caption"], label=spec["label"],
                             opt=GenOptions(align="decimal", note_lines=spec["notes"]),
                             midrule_before=spec["midrule_before"],
                             bold_rows=spec["bold_rows"], source=spec["source"])
    issues_dec = validate_tex(tex_dec)
    with open(out_dec, "w", encoding="utf-8") as fh:
        fh.write(tex_dec)
    print(f"[4/6] decimal 模式（siunitx S 列）：{describe(table, columns, tex_dec)} → "
          f"{out_dec}")
    print(f"      静态校验：{'通过（0 问题）' if not issues_dec else issues_dec}")

    # 负例：故意造两处违规，确认校验器真的能抓到（校验器自己也要被校验）
    lines = tex_right.splitlines()
    for i, ln in enumerate(lines):
        if "弹 1" in ln and ln.rstrip().endswith(r"\\"):
            lines[i] = ln.rstrip()[:-2] + " & 多出来的一列 \\\\"
            break
    bad = "\n".join(lines).replace(r"\toprule", r"\hline", 1)
    bad_issues = validate_tex(bad)
    print(f"[5/6] 负例校验（故意插入 \\hline 与多出一列）：抓到 {len(bad_issues)} 个问题")
    for it in bad_issues:
        print(f"           ! {it}")

    print("[6/6] 生成物预览（right 模式，前 22 行）：")
    for line in tex_right.splitlines()[:22]:
        print("       " + line)

    ok = (not issues_right) and (not issues_dec) and len(bad_issues) >= 2
    print("\n自检结论：" + ("全部通过" if ok else "存在问题，请检查上面的输出"))
    print(f"  正例（right）问题数 {len(issues_right)}；正例（decimal）问题数 {len(issues_dec)}；"
          f"负例抓到问题数 {len(bad_issues)}（应 ≥ 2）")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    # 与仓库其它脚本一致：Windows 控制台按 UTF-8 输出，中文与 LaTeX 源码不出现乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001  （旧版 Python / 特殊 stdout 下静默降级）
        pass

    ap = argparse.ArgumentParser(
        description="从 CSV/Excel 生成国赛三线表 LaTeX 源码（booktabs，含表题与表注）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", help="数据文件路径（.csv/.tsv/.xlsx）")
    ap.add_argument("--out", help="输出的 .tex 路径")
    ap.add_argument("--spec", help="列配置 JSON（省略则按数据推断，建议用 --emit-spec 生成后人工修改）")
    ap.add_argument("--emit-spec", metavar="PATH", help="只输出一份推断出的 spec 模板，不生成表格")
    ap.add_argument("--align", choices=["right", "decimal"], help="覆盖 spec 的对齐方式")
    ap.add_argument("--caption", help="覆盖表题")
    ap.add_argument("--label", help="覆盖 \\label")
    ap.add_argument("--source", help="数据来源（写进表注，如 'E04'）")
    ap.add_argument("--check", metavar="TEX", help="只对已有 .tex 做静态校验")
    args = ap.parse_args(argv)

    if args.check:
        issues = validate_tex(open(args.check, "r", encoding="utf-8").read())
        print(f"[table_gen] 静态校验 {args.check}："
              f"{'通过（0 问题）' if not issues else str(len(issues)) + ' 个问题'}")
        for it in issues:
            print(f"  ! {it}")
        return 0 if not issues else 1

    if not args.input:
        return _selfcheck()          # 无参数 = 自检

    if args.emit_spec:
        spec = default_spec(read_table(args.input), caption=args.caption or "（请填写表题）",
                            label=args.label or "tab:result")
        os.makedirs(os.path.dirname(os.path.abspath(args.emit_spec)) or ".", exist_ok=True)
        with open(args.emit_spec, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, ensure_ascii=False, indent=2)
        print(f"[table_gen] 已写出 spec 模板 {args.emit_spec}（请人工核对 unit/decimals/best）")
        return 0

    out = args.out or os.path.splitext(args.input)[0] + ".tex"
    res = run(args.input, out, args.spec, align=args.align, source=args.source,
              caption=args.caption, label=args.label)
    return 0 if not res["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
