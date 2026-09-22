"""国赛配图自动终检（cumcm-figure 的 QA 契约实现）。

检查每张导出图是否满足国赛交付要求。可单独使用，也可接进流水线：

    python figure_check.py                      # 检查 results/figures 与 sop/project/figures
    python figure_check.py --dir path/to/figs
    python figure_check.py --pdf paper/manuscript.pdf   # 顺带查论文里的图与身份信息

检查项
  A. 文件层面   —— 是否成对产出 PDF+PNG、体积是否在预算内、是否异常小（空图）
  B. PDF 层面   —— 字体是否嵌入（不嵌入会在评委机器上乱码）、页尺寸是否合理
  C. PNG 层面   —— 有效分辨率、尺寸是否与单栏/通栏匹配
  D. 合规层面   —— 图文件名与内嵌文本是否含身份信息（校名/姓名/学号/赛区）
  E. 命名规范   —— 建议 results/figures/<E0x>_<name>.pdf 便于追溯 P11 实验编号
"""
from __future__ import annotations

import argparse
import os
import re
import sys

def _find_repo_root(start: str) -> str:
    """向上找到真正的仓库根（含 scripts/ 与 skills/ 的那一层）。

    不能简单用 dirname 三次：脚本被复制到别处或从不同深度调用时会指错，
    报告就会写进奇怪的地方（实测曾写进 skills/logs/）。
    """
    cur = start
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "scripts")) and os.path.isdir(os.path.join(cur, "skills")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.dirname(os.path.dirname(os.path.dirname(start)))


ROOT = _find_repo_root(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(ROOT, "logs")

# 身份信息模式（与 scripts/validate_pipeline.py 口径一致）
IDENTITY_PATTERNS = [
    (r"[\u4e00-\u9fff]{2,12}大学", "校名"),
    (r"[\u4e00-\u9fff]{2,12}学院", "学院名"),
    (r"[\u4e00-\u9fff]{2,10}职业技术学院", "校名"),
    (r"学\s*号\s*[:：]?\s*\d{6,}", "学号"),
    (r"[\u4e00-\u9fff]{2,4}\s*赛区", "赛区"),
    (r"C:\\Users\\[A-Za-z0-9_.\-]+", "本机绝对路径"),
    (r"/home/[A-Za-z0-9_.\-]+", "本机绝对路径"),
]
# 规则文本、模板占位属于正常出现
IDENTITY_ALLOW = re.compile(r"XX大学|某某大学|示例|占位|placeholder|规范|章程|样例|论文|中国大学生在线")

# 体积预算：论文 PDF 上限 20MB，一张图占 0.3–1.5MB 是正常区间
PDF_BUDGET_KB = 1500
PNG_BUDGET_KB = 2500
MIN_BYTES = 4000          # 小于此值多半是空图

# 单栏 8.5cm / 通栏 17cm，允许 ±15% 误差
SINGLE_CM = 8.5
DOUBLE_CM = 17.0
LONG_EDGE_MIN_PX = 900    # 600dpi 下 8.5cm ≈ 2008px；≥900 说明至少不是低清截图


def _load_pdf_tools():
    try:
        import pymupdf as fitz  # type: ignore
        return fitz, "pymupdf"
    except Exception:
        try:
            import fitz  # type: ignore
            return fitz, "fitz"
        except Exception:
            return None, None


def check_pdf(path: str, fitz) -> tuple[list[str], list[str], dict]:
    """返回 (问题, 提醒, 指标)。"""
    problems, notes, info = [], [], {}
    try:
        doc = fitz.open(path)
    except Exception as e:  # noqa: BLE001
        return [f"无法打开 PDF：{e}"], [], info

    nfont_total = nfont_embedded = 0
    unembedded: list[str] = []
    text_parts: list[str] = []
    for page in doc:
        for f in page.get_fonts(full=True):
            # f = (xref, ext, type, basefont, name, encoding, ...)
            name = f[3] if len(f) > 3 else "?"
            ext = (f[1] or "").lower()
            nfont_total += 1
            if ext in ("ttf", "otf", "cff", "type1", "cff2") or "subset" in name.lower():
                nfont_embedded += 1
            else:
                # ext 为空常见于内置/未嵌入字体
                unembedded.append(name)
        text_parts.append(page.get_text())
        if len(info) == 0:
            r = page.rect
            info["page_cm"] = (round(r.width / 72 * 2.54, 2), round(r.height / 72 * 2.54, 2))

    info["pages"] = doc.page_count
    info["fonts_total"] = nfont_total
    info["fonts_embedded"] = nfont_embedded
    # 近空图检测：统计"绘制算子"与文字量。
    # 实测矢量 PDF 里"只有坐标轴"与"200 个数据点"体积几乎相同
    # （2041B / 54 算子 vs 4065B / 137 算子），所以用绝对体积判不出来；
    # 这里用"内容流极小 且 几乎没有文字"作为可疑近空图的下界信号，
    # 更可靠的空图检测在导出时由 cumcm_style.save_cumcm_figure 完成。
    try:
        stream_len = 0
        d2 = fitz.open(path)
        for page in d2:
            for xref in page.get_contents():
                stream_len += len(d2.xref_stream(xref) or b"")
        n_images = sum(len(p.get_images(full=True)) for p in d2)
        n_draw = sum(len(p.get_drawings()) for p in d2)
        d2.close()
        info["content_bytes"] = stream_len
        info["images"] = n_images
        info["drawings"] = n_draw
        if stream_len < 1400 and n_images == 0 and len(info.get("text", "")) < 30:
            problems.append(
                f"内容流仅 {stream_len} 字节、绘制对象 {n_draw} 个且几乎无文字，"
                f"疑似近空图（只画了坐标轴，没有数据）")
    except Exception:  # noqa: BLE001
        pass
    try:
        meta = doc.metadata or {}
        info["meta_author"] = meta.get("author") or ""
        info["meta_title"] = meta.get("title") or ""
    except Exception:  # noqa: BLE001
        pass
    doc.close()

    if nfont_total == 0:
        notes.append("PDF 中未检测到字体记录（可能整图是位图描边），无法确认文字是否嵌入")
    elif unembedded:
        problems.append(f"存在可能未嵌入的字体：{sorted(set(unembedded))[:4]} —— "
                        f"评委机器缺字体会显示为方块")
    else:
        notes.append(f"字体已嵌入 {nfont_embedded}/{nfont_total}")

    info["text"] = "\n".join(text_parts)[:200000]
    # 近空图检测（启发式下界）：矢量 PDF 里"只有坐标轴"与"200 个数据点"体积
    # 几乎相同（实测 2041B vs 4065B），所以这里只标出"内容流极小且几乎无文字"
    # 的明显空图；更强的判据是导出时 count_drawn_artists 的数据元素计数。
    if info.get("content_bytes", 1 << 30) < 1400 and info.get("images", 0) == 0 \
            and len(info["text"]) < 30:
        problems.append(
            f"内容流仅 {info['content_bytes']} 字节、无位图且几乎无文字，"
            f"疑似近空图（只画了坐标轴，没有数据）")
    return problems, notes, info


def check_png(path: str) -> tuple[list[str], list[str], dict]:
    problems, notes, info = [], [], {}
    try:
        from PIL import Image
    except Exception:
        return [], ["未安装 Pillow，跳过 PNG 尺寸检查"], info
    try:
        with Image.open(path) as im:
            w, h = im.size
            dpi = im.info.get("dpi")
    except Exception as e:  # noqa: BLE001
        return [f"无法打开 PNG：{e}"], [], info

    info["px"] = (w, h)
    info["dpi"] = dpi
    if max(w, h) < LONG_EDGE_MIN_PX:
        problems.append(f"位图分辨率过低（{w}×{h}），600 dpi 下 8.5cm 宽应约 2008px")
    if dpi and dpi[0] < 300:
        notes.append(f"PNG 声明 DPI 为 {dpi[0]:.0f}，低于 600，插入 Word 时尺寸可能被误判")
    # 长宽比检查：避免"又高又窄"的图在论文里占掉半页
    if h > 0 and w > 0 and (h / w) > 1.6:
        notes.append(f"图高宽比 {h/w:.2f} 偏大，通栏时会占据大量纵向空间，考虑压缩或拆分")
    return problems, notes, info


def check_identity(text: str, filename: str) -> list[str]:
    hits = []
    for pat, kind in IDENTITY_PATTERNS:
        for m in re.finditer(pat, text or ""):
            win = (text or "")[max(0, m.start() - 40): m.end() + 40]
            if IDENTITY_ALLOW.search(win):
                continue
            hits.append(f"图内文本疑似{kind}：{m.group(0).strip()}")
            break
    for pat, kind in IDENTITY_PATTERNS:
        m = re.search(pat, filename)
        if m and not IDENTITY_ALLOW.search(filename):
            hits.append(f"文件名疑似{kind}：{filename}")
            break
    return hits


def check_basename(name: str) -> list[str]:
    notes = []
    if not re.match(r"^E\d{2,3}[_\-]", name):
        notes.append("文件名未以实验编号（E0x_）开头，不利于追溯到 P11 实验登记表")
    return notes


def walk_figures(dirs: list[str]) -> list[str]:
    found: list[str] = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _dd, files in os.walk(d):
            for f in files:
                if f.lower().endswith((".pdf", ".png", ".svg")) and not f.startswith("_"):
                    found.append(os.path.join(root, f))
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser(description="国赛配图自动终检")
    ap.add_argument("--dir", action="append", default=None,
                    help="要检查的图片目录（可多次指定）")
    ap.add_argument("--pdf", default=None, help="额外检查论文 PDF（体积、身份信息）")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

    dirs = args.dir or [
        os.path.join(ROOT, "results", "figures"),
        os.path.join(ROOT, "sop", "project", "figures"),
    ]
    files = walk_figures(dirs)

    fitz, backend = _load_pdf_tools()

    L: list[str] = []
    L.append("=" * 76)
    L.append("国赛配图终检报告")
    L.append("=" * 76)
    L.append(f"扫描目录: {', '.join(os.path.relpath(d, ROOT) for d in dirs)}")
    L.append(f"PDF 后端: {backend or '不可用（跳过 PDF 内层检查）'}")
    L.append(f"发现图片文件: {len(files)}")
    L.append("")

    hard: list[str] = []
    soft: list[str] = []
    ok_count = 0

    by_base: dict[str, set[str]] = {}
    for f in files:
        base, ext = os.path.splitext(f)
        by_base.setdefault(base, set()).add(ext.lower())

    for base, exts in sorted(by_base.items()):
        name = os.path.basename(base)
        rel = os.path.relpath(base, ROOT)
        probs: list[str] = []
        notes: list[str] = []
        info: dict = {}

        if ".pdf" not in exts:
            probs.append("缺少矢量 PDF 版本（论文插图应优先用矢量）")
        if ".png" not in exts:
            notes.append("缺少 600dpi PNG 预览（支撑材料/快速查看用）")

        for ext in sorted(exts):
            p = base + ext
            size = os.path.getsize(p)
            info[f"{ext}_KB"] = round(size / 1024, 1)
            if size < MIN_BYTES:
                probs.append(f"{ext} 只有 {size} 字节，疑似空图")
            budget = PDF_BUDGET_KB if ext == ".pdf" else PNG_BUDGET_KB
            if size / 1024 > budget:
                notes.append(f"{ext} 体积 {size/1024:.0f}KB 超过建议预算 {budget}KB")

        pdfp = base + ".pdf"
        if os.path.exists(pdfp) and fitz:
            p2, n2, i2 = check_pdf(pdfp, fitz)
            probs += p2
            notes += n2
            info.update(i2)
            probs += check_identity(info.get("text", ""), name)
        pngp = base + ".png"
        if os.path.exists(pngp):
            p3, n3, i3 = check_png(pngp)
            probs += p3
            notes += n3
            info.update({f"png_{k}": v for k, v in i3.items()})

        notes += check_basename(name)

        status = "✘" if probs else "✔"
        if probs:
            hard += [f"{rel}: {x}" for x in probs]
        else:
            ok_count += 1
        soft += [f"{rel}: {x}" for x in notes]

        if not args.quiet:
            L.append(f"{status} {rel}")
            L.append("    指标: " + ", ".join(f"{k}={v}" for k, v in info.items()
                                             if k in ("pages", "page_cm", "px", "dpi",
                                                      "fonts_embedded", "fonts_total",
                                                      "pdf_KB", "png_KB")))
            for x in probs:
                L.append("    ✘ " + x)
            for x in notes:
                L.append("    ! " + x)

    # 论文 PDF 附加检查
    if args.pdf and os.path.exists(args.pdf):
        L.append("")
        L.append(f"--- 论文 PDF: {os.path.relpath(args.pdf, ROOT)} ---")
        mb = os.path.getsize(args.pdf) / 1e6
        L.append(f"  体积: {mb:.2f} MB " + ("✔ ≤20MB" if mb <= 20 else "✘ 超过 20MB 上限"))
        if mb > 20:
            hard.append(f"论文 PDF {mb:.2f}MB 超过 20MB 合规上限")
        if fitz:
            p2, n2, i2 = check_pdf(args.pdf, fitz)
            for x in p2:
                L.append("  ✘ " + x)
                hard.append(f"论文 PDF: {x}")
            for x in n2:
                L.append("  ! " + x)
            ident = check_identity(i2.get("text", ""), os.path.basename(args.pdf))
            for x in ident:
                L.append("  ✘ " + x)
                hard.append(f"论文 PDF: {x}")
            if not ident:
                L.append("  ✔ 正文未见身份信息")
            ma = (i2.get("meta_author") or "").strip()
            if ma and not re.search(r"latex|tex|word|writer|microsoft|acrobat", ma, re.I):
                L.append(f"  ✘ PDF 元数据作者字段：{ma}")
                hard.append(f"论文 PDF 元数据残留作者：{ma}")
            else:
                L.append("  ✔ PDF 元数据未见作者信息")
            L.append(f"  PDF 页数: {i2.get('pages')}")

    L.append("")
    L.append("-" * 76)
    L.append(f"通过 {ok_count} 张，硬性问题 {len(hard)} 条，提醒 {len(soft)} 条")
    if hard:
        L.append("")
        L.append("硬性问题（必须修）：")
        for x in hard:
            L.append("  ✘ " + x)
    if soft and not args.quiet:
        L.append("")
        L.append("提醒（可接受，但值得看一眼）：")
        for x in soft[:20]:
            L.append("  ! " + x)

    report = "\n".join(L)
    dest = os.path.join(LOGDIR, "figure_check.txt")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
