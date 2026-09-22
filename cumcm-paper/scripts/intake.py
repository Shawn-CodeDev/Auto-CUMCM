"""题面与数据的自动化勘察：把一个"题目 PDF + 附件"变成一个可读的 intake 报告。

这是 cumcm-paper 流水线的第 0 步。它做的是**确定性**工作（不需要判断力）：
  * 从赛题 PDF 抽出全文，并按"问题1/问题2/问题3"切成任务条目
  * 扫描同目录的附件，逐个读出结构、表头、缺失、异常、量纲线索
  * 交叉比对：题面提到的表（表1/表2）与 result*.xlsx 模板，推断每个任务的交付格式
  * 输出 problem_spec.md 骨架（待 agent 补判断）与 data_report.md 骨架

用法：
    python intake.py --problem <题面.pdf> --data-dir <数据目录> --out <输出目录>

设计原则：脚本只搬运与统计，不做任何建模判断；判断留给 agent 并按契约填写。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import OrderedDict

import pandas as pd

# 数据文件类型
DATA_EXT = (".xlsx", ".xls", ".csv", ".txt", ".dat", ".json")
DOC_EXT = (".docx", ".doc", ".pdf")


# --------------------------------------------------------------------------- #
# 题面解析
# --------------------------------------------------------------------------- #
# 国赛题面里任务条目的写法："问题1 ..."、"问题 1：..."。
# 必须要求「行首 + 紧跟分隔符或直接接正文」，否则会把正文里的
# "和问题3 用到的经验公式" 这类**交叉引用**误判成新任务（实测会多出 2 条）。
TASK_RE = re.compile(
    r"(?m)^[ \t　]*(?:问题\s*([0-9一二三四五])\s*[、．.:：]?|第\s*([0-9一二三四五])\s*问\s*[、．.:：]?)"
    r"[ \t　]*",
)
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
# 参数名前缀虚词，提取时要剥掉
PARTICLES = re.compile(r"^(?:为|是|约|并将|并|将|且|其|则|故|即)+")


def read_pdf(path: str) -> tuple[str, int]:
    try:
        import pymupdf as fitz  # type: ignore
    except Exception:
        import fitz  # type: ignore
    doc = fitz.open(path)
    pages = doc.page_count
    txt = "\n".join(p.get_text() for p in doc)
    doc.close()
    return txt, pages


def read_docx(path: str) -> str:
    """不依赖 python-docx，直接读 docx 里的 document.xml 文本。"""
    import zipfile
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return f"<无法读取 docx: {e}>"
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def split_tasks(text: str) -> list[dict]:
    """把题面切成任务条目。返回 [{no, title, body, tables, files}]。

    只保留**真正的任务条款**：编号必须出现在行首（见 TASK_RE），且正文长度
    达到阈值——正文里"和问题3 用到的经验公式"这类交叉引用会紧跟在段落中间，
    既不在行首、正文也很短，两道闸门一起把它们挡掉。
    """
    marks = list(TASK_RE.finditer(text))
    if not marks:
        return []
    tasks = []
    for i, m in enumerate(marks):
        raw = m.group(1) or m.group(2)
        try:
            no = int(raw)
        except (TypeError, ValueError):
            no = CN_NUM.get(str(raw).strip(), i + 1)
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[start:end].strip()
        if len(body) < 120:          # 太短 → 交叉引用，不是任务条款
            continue
        first_line = body.splitlines()[0].strip() if body else ""
        # 该任务自己提到的表与结果文件
        tables = [f"表{n}" for n in dict.fromkeys(re.findall(r"表\s*(\d+)", body))]
        files = list(dict.fromkeys(
            f.replace(" ", "") for f in re.findall(r"(result\s*\d*\s*\.\s*xlsx)", body, re.I)))
        tasks.append({
            "no": no,
            "title": first_line[:80],
            "body": body,
            "chars": len(body),
            "tables": tables,
            "files": files,
        })
    # 去重（同一问可能被重复匹配）
    seen, uniq = set(), []
    for t in tasks:
        if t["no"] in seen:
            continue
        seen.add(t["no"])
        uniq.append(t)
    return sorted(uniq, key=lambda x: x["no"])


def find_deliverables(text: str) -> list[dict]:
    """找出题面里明确要求的交付物：表 N、resultN.xlsx、文件等。"""
    items = []
    for m in re.finditer(r"表\s*(\d+)\s*([^\n]{0,40})", text):
        items.append({"kind": "table", "id": f"表{m.group(1)}", "hint": m.group(2).strip()})
    for m in re.finditer(r"(result\s*\d*\s*\.\s*xlsx)", text, re.I):
        items.append({"kind": "file", "id": m.group(1).replace(" ", ""), "hint": ""})
    for m in re.finditer(r"所有结果保留\s*([一二三四五六七八九十\d]+)\s*位小数", text):
        items.append({"kind": "format", "id": f"保留{m.group(1)}位小数", "hint": ""})
    # 去重
    seen, out = set(), []
    for it in items:
        k = (it["kind"], it["id"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def find_params(text: str, limit: int = 40) -> list[str]:
    """抽出题面里带数值+单位的物理参数，供 P8 核对量纲与取值。

    题干里的"长为 25 cm"会把虚词"长为"当成参数名，所以要剥掉前缀虚词，
    并要求剥完后仍是像样的词（≥2 字且不含句读）。
    """
    pat = re.compile(
        r"([\u4e00-\u9fff]{2,12}?)\s*(?:为|是|约|取)?\s*"
        r"(-?\d+(?:\.\d+)?)\s*"
        r"(°C|℃|cm|mm|kg/kg|kg/m3|kg/m³|W/\(m·K\)|W/\(m·℃\)|m/s|min|h|s|%)"
    )
    out, seen = [], set()
    for m in pat.finditer(text):
        name = PARTICLES.sub("", m.group(1)).strip()
        if len(name) < 2 or re.search(r"[，。；：、（）()\s]", name):
            continue
        val, unit = m.group(2), m.group(3)
        key = (name, val, unit)
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{name} = {val} {unit}")
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# 数据勘察
# --------------------------------------------------------------------------- #
def profile_frame(df: pd.DataFrame, name: str, max_sample: int = 3) -> dict:
    n_rows, n_cols = df.shape
    cols = []
    for c in list(df.columns)[:20]:
        s = df[c]
        nonnull = int(s.notna().sum())
        info = {
            "name": str(c)[:40],
            "dtype": str(s.dtype),
            "missing_pct": round(100 * (1 - nonnull / max(n_rows, 1)), 2),
            "n_unique": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            d = s.dropna()
            if len(d):
                info.update({
                    "min": round(float(d.min()), 4),
                    "max": round(float(d.max()), 4),
                    "mean": round(float(d.mean()), 4),
                })
        else:
            vals = s.dropna().astype(str).unique()[:max_sample]
            info["sample"] = [v[:28] for v in vals]
        cols.append(info)

    # 全空列 / 模板占位：题面附件里 result*.xlsx 常是空模板
    empty_cols = [c["name"] for c in cols if c["missing_pct"] >= 99.9]
    return {
        "sheet": name,
        "rows": n_rows,
        "cols": n_cols,
        "columns": cols,
        "empty_columns": empty_cols,
        "is_likely_template": bool(empty_cols) and len(empty_cols) >= max(1, n_cols // 2),
    }


def profile_file(path: str) -> dict:
    fn = os.path.basename(path)
    ext = os.path.splitext(fn)[1].lower()
    rec = {"file": fn, "ext": ext, "bytes": os.path.getsize(path), "sheets": []}
    try:
        if ext == ".csv":
            df = pd.read_csv(path, nrows=5000)
            rec["sheets"].append(profile_frame(df, "csv"))
        elif ext in (".xlsx", ".xls"):
            xl = pd.ExcelFile(path)
            for s in xl.sheet_names:
                df = xl.parse(s, nrows=5000)
                rec["sheets"].append(profile_frame(df, s))
        else:
            rec["note"] = "非表格数据，未做结构化勘察"
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


# --------------------------------------------------------------------------- #
# 报告生成
# --------------------------------------------------------------------------- #
def render_problem_spec(problem_path, text, pages, tasks, deliverables, params) -> str:
    L = [
        "# P1 赛题解析（自动勘察 + 待人工确认）",
        "",
        f"> 来源：`{os.path.basename(problem_path)}`（{pages} 页，{len(text)} 字符）",
        "> 本文件由 `intake.py` 生成骨架；**带 ❓ 的条目必须由 agent 依据题面补全**。",
        "",
        "## 一、题目概况",
        "",
        f"- 题面全文：见 `intake/problem_text.txt`",
        f"- 识别到任务条款：**{len(tasks)}** 个",
        f"- 识别到交付要求：**{len(deliverables)}** 条",
        "",
        "## 二、任务清单",
        "",
        "| 编号 | 首句 | 字数 | 该问要求的表 | 该问要求的文件 | 待澄清 ❓ |",
        "|---|---|---|---|---|---|",
    ]
    for t in tasks:
        tbl = "、".join(t.get("tables") or []) or "—"
        fil = "、".join(t.get("files") or []) or "—"
        L.append(f"| 问题{t['no']} | {t['title']} | {t['chars']} | {tbl} | {fil} | ❓ |")
    L.append("")
    L.append("## 三、题面明确的交付要求")
    L.append("")
    if deliverables:
        L.append("| 类型 | 标识 | 题面线索 |")
        L.append("|---|---|---|")
        for d in deliverables:
            L.append(f"| {d['kind']} | `{d['id']}` | {d['hint']} |")
    else:
        L.append("❓ 未自动识别到交付要求，需人工从题面确认。")
    L.append("")
    L.append("## 四、题面给定的参数（供 P8 量纲与取值核对）")
    L.append("")
    if params:
        for p in params:
            L.append(f"- {p}")
    else:
        L.append("❓ 未自动识别到带单位参数。")
    L.append("")
    L.append("## 五、每个任务的详细题面")
    L.append("")
    for t in tasks:
        L.append(f"### 问题 {t['no']}")
        L.append("")
        L.append("```text")
        L.append(t["body"][:3000])
        L.append("```")
        L.append("")
    L.append("## 六、待澄清清单（P8 的输入，必须逐条给出结论）")
    L.append("")
    L.append("| 编号 | 待澄清问题 | 处置（转为假设 / 由数据决定 / 不影响） |")
    L.append("|---|---|---|")
    for t in tasks:
        L.append(f"| C{t['no']}-1 | 问题{t['no']} 的边界条件与初始条件是否已明确？ | ❓ |")
    L.append("")
    return "\n".join(L)


def render_data_report(profiles, data_dir) -> str:
    L = [
        "# P5 数据审计（自动勘察）",
        "",
        f"> 数据目录：`{data_dir}`",
        "> 本文件由 `intake.py` 生成；**清洗规则与理由必须由 agent 补齐**。",
        "",
        "## 一、文件登记",
        "",
        "| 文件 | 类型 | 体积 | 表/工作表 | 行×列 | 疑似模板 | 备注 |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in profiles:
        sheets = p.get("sheets", [])
        desc = "；".join(f"{s['sheet']}({s['rows']}×{s['cols']})" for s in sheets) or "—"
        tpl = "是" if any(s.get("is_likely_template") for s in sheets) else "否"
        note = p.get("note") or p.get("error") or ""
        L.append(f"| `{p['file']}` | {p['ext']} | {p['bytes']/1024:.1f} KB | "
                 f"{len(sheets)} | {desc} | {tpl} | {note} |")
    L.append("")
    L.append("## 二、逐列勘察")
    L.append("")
    for p in profiles:
        for s in p.get("sheets", []):
            L.append(f"### `{p['file']}` / {s['sheet']}  （{s['rows']} 行 × {s['cols']} 列）")
            L.append("")
            L.append("| 列名 | 类型 | 缺失率 | 唯一值 | 最小 | 最大 | 均值 |")
            L.append("|---|---|---|---|---|---|---|")
            for c in s["columns"]:
                L.append(f"| {c['name']} | {c['dtype']} | {c['missing_pct']}% | {c['n_unique']} | "
                         f"{c.get('min', '')} | {c.get('max', '')} | {c.get('mean', '')} |")
            if s.get("is_likely_template"):
                L.append("")
                L.append("> ⚠️ **疑似空白模板**：半数以上列全空。这通常是题面给的"
                         "提交模板（result*.xlsx），不是输入数据，不要拿去建模。")
            L.append("")
    L.append("## 三、清洗规则（❓ 待 agent 填写）")
    L.append("")
    L.append("| 问题 | 处理方法 | 理由 |")
    L.append("|---|---|---|")
    L.append("| 缺失值 | ❓ | ❓ |")
    L.append("| 异常值 | ❓ | ❓ |")
    L.append("| 量纲统一 | ❓ | ❓ |")
    L.append("")
    L.append("## 四、数据局限（P12 适用边界的原料）")
    L.append("")
    L.append("- ❓")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="题面与数据的自动化勘察")
    ap.add_argument("--problem", required=True, help="赛题 PDF 或 DOCX")
    ap.add_argument("--data-dir", required=True, help="附件所在目录")
    ap.add_argument("--out", required=True, help="输出目录（intake 产物）")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    os.makedirs(args.out, exist_ok=True)
    ext = os.path.splitext(args.problem)[1].lower()
    if ext == ".pdf":
        text, pages = read_pdf(args.problem)
    elif ext in (".docx", ".doc"):
        text, pages = read_docx(args.problem), 1
    else:
        print(f"不支持的题面格式：{ext}")
        return 2

    open(os.path.join(args.out, "problem_text.txt"), "w", encoding="utf-8").write(text)

    tasks = split_tasks(text)
    deliverables = find_deliverables(text)
    params = find_params(text)

    profiles = []
    for f in sorted(os.listdir(args.data_dir)):
        p = os.path.join(args.data_dir, f)
        if not os.path.isfile(p):
            continue
        if os.path.splitext(f)[1].lower() in DATA_EXT:
            profiles.append(profile_file(p))

    open(os.path.join(args.out, "problem_spec.md"), "w", encoding="utf-8").write(
        render_problem_spec(args.problem, text, pages, tasks, deliverables, params))
    open(os.path.join(args.out, "data_report.md"), "w", encoding="utf-8").write(
        render_data_report(profiles, args.data_dir))

    summary = {
        "problem_file": os.path.basename(args.problem),
        "pages": pages,
        "text_chars": len(text),
        "n_tasks": len(tasks),
        "tasks": [{"no": t["no"], "title": t["title"]} for t in tasks],
        "deliverables": deliverables,
        "params": params,
        "n_data_files": len(profiles),
        "data_files": [p["file"] for p in profiles],
        "template_files": [p["file"] for p in profiles
                           if any(s.get("is_likely_template") for s in p.get("sheets", []))],
    }
    open(os.path.join(args.out, "intake_summary.json"), "w", encoding="utf-8").write(
        json.dumps(summary, ensure_ascii=False, indent=2))

    print(f"题面：{pages} 页 / {len(text)} 字符")
    print(f"任务条目：{len(tasks)} 个 -> {[t['no'] for t in tasks]}")
    print(f"交付要求：{len(deliverables)} 条")
    print(f"数据文件：{len(profiles)} 个，其中疑似模板 {len(summary['template_files'])} 个")
    print(f"产物写入：{args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
