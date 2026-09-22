#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国赛提交包 · allowlist 打包 + 身份信息扫描器（cumcm-release）

核心原则：**验证打包后的产物，而不是产生它的工作区。**
工作目录里含有那个"缺失的文件"，所以从工作目录里看永远看不出问题。

四个动作可以单独跑，也可以按固定顺序串起来跑：

    --allowlist   把 allowlist 文件解析成**显式文件列表**并打印（供人工复核）
    --stage       把 allowlisted 文件复制到空的 staging 目录（只复制，不推导）
    --scan        扫描 staged tree：文件名 + 内容 + 容器格式内部
    --selftest    在真实格式里植入已知字符串，确认扫描器真的在工作，然后清理

典型用法：

    python stage_and_scan.py --allowlist allowlist.txt
    python stage_and_scan.py --allowlist allowlist.txt --stage --stage-dir _stage --scan
    python stage_and_scan.py --scan --stage-dir _stage --report scan_report.txt
    python stage_and_scan.py --selftest --report scan_report.txt

    # 一键：解析 → 复制 → 扫描 → 出报告
    python stage_and_scan.py --allowlist allowlist.txt --stage --scan --selftest

为什么必须扫 staged tree 而不是源目录：
    源目录里同时存在论文 PDF、支撑材料 ZIP、以及**那个泄露身份的文件**。
    你从里面看，看到的是一棵"什么都有"的树，看不出提交包里会缺什么、多什么。
    只有把 allowlist 解析出来的文件复制到一个**空目录**里，再扫那棵新树，
    你观察到的才是"评委真正会拿到的东西"。

为什么必须植入已知字符串：
    干净树上的"0 命中"和"扫描器根本没运行"输出**完全一样**。
    把已知字符串放进真实格式（.docx 的 XML、无扩展名文件、
    含输出单元格的 .ipynb、中文路径的文件名），看它是否被抓到，
    才能把这两件事区分开。自检同时报"漏报"和"误报"。

退出码：0 = 无阻塞问题；1 = 有阻断项（真实命中 / 自检失败 / 解析错误）。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from datetime import datetime

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------
STAGE_DEFAULT = "_stage"
REPORT_DEFAULT = "scan_report.txt"

# 容器格式：内容是 ZIP，内部有 XML / JSON 文本
ZIP_CONTAINER_EXTS = {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp",
                      ".zip", ".jar", ".whl", ".egg", ".epub"}
# 容器格式：内容是 JSON
JSON_CONTAINER_EXTS = {".ipynb"}
# 嵌套压缩包最多递归几层
MAX_ZIP_DEPTH = 3
# 单个成员的扫描上限，防止把 20MB 包读爆内存
MAX_MEMBER_BYTES = 24 * 1024 * 1024

# 文本编码尝试顺序（中文 Windows 上 GBK 文件很常见）
TEXT_ENCODINGS = ("utf-8", "gb18030", "utf-16")


# --------------------------------------------------------------------------
# 泄露模式库
# --------------------------------------------------------------------------
# 说明：这些模式与 scripts/validate_pipeline.py 的 IDENTITY_PATTERNS 保持同源，
# 并在其基础上补齐"打包环节才会暴露"的载体（绝对路径、邮箱、容器内部）。
class Pattern:
    def __init__(self, name: str, regex: str, level: str, note: str):
        self.name = name
        self.regex = re.compile(regex)
        self.level = level          # 致命 / 严重
        self.note = note

    def find(self, text: str):
        return [m.group(0).strip() for m in self.regex.finditer(text)]


PATTERNS: list[Pattern] = [
    # ---------- 中文身份信息 ----------
    Pattern("中文校名（XX大学）",
            r"[\u4e00-\u9fff]{2,12}大学",
            "致命", "规则：任何地方不得出现所在学校信息"),
    Pattern("中文校名（XX学院）",
            r"[\u4e00-\u9fff]{2,12}学院",
            "致命", "规则：任何地方不得出现所在学校信息"),
    Pattern("中文校名（职业技术学院）",
            r"[\u4e00-\u9fff]{2,10}职业技术(?:大学|学院)",
            "致命", "高职高专院校名同样属于学校信息"),
    Pattern("英文校名",
            r"\b(?:University|College|Institute\s+of\s+Technology|Academy)\b",
            "严重", "英文校名/院名，需人工判断是否为通用词"),
    Pattern("赛区编号或赛区名",
            r"(?:[\u4e00-\u9fff]{2,6}赛区|\b赛区\s*[:：]?\s*[A-Za-z0-9\u4e00-\u9fff]{1,8})",
            "致命", "规则：不得出现赛区信息（赛区名、赛区编号）"),
    Pattern("学号",
            r"学\s*号\s*[:：]?\s*\d{4,}|(?<!\d)20\d{2}\d{4,}(?!\d)",
            "致命", "学号是最直接的身份标识（也匹配裸的 10 位学号）"),
    Pattern("姓名+学号组合",
            r"[\u4e00-\u9fff]{2,4}\s*[,，、\s]\s*(?:20\d{2})?\d{6,}",
            "致命", "姓名与学号同时出现"),
    Pattern("身份声明句式",
            r"我们(?:学校|学院|队|组)|本(?:校|院|队)(?:学生|成员)|指导教[师师]\s*[:：]?\s*[\u4e00-\u9fff]{2,4}",
            "致命", "自述式身份暴露，比校名更隐蔽"),
    Pattern("署名行",
            r"(?:作者|作\s*者|编写人|完成人|队员|队\s*员|组\s*员)\s*[:：]\s*[\u4e00-\u9fff]{2,4}",
            "致命", "代码注释与文档属性里最常见的残留"),
    Pattern("英文署名行",
            r"(?im)^\s*(?:[#/*<!-]+\s*)?(?:@?author|maintainer|created\s+by|written\s+by)"
            r"\s*[:：=]\s*\S{2,60}",
            "致命", "IDE/编辑器模板自动写入的英文署名（如 # author: zhangsan）"),

    # ---------- 机器与路径 ----------
    Pattern("Windows 绝对路径（含用户名）",
            r"[A-Za-z]:[\\/]{1,2}(?:Users|Documents\s+and\s+Settings)[\\/]{1,2}[^\\/\s\"'<>|]+",
            "致命", "路径里的用户名就是身份信息"),
    Pattern("Windows 盘符绝对路径",
            r"\b[A-Za-z]:\\(?:[^\\\s\"'<>|:*?]+\\){1,}",
            "严重", "评审机盘符不同，既泄露环境又跑不通"),
    Pattern("POSIX 家目录路径",
            r"/(?:home|Users)/[A-Za-z0-9._\u4e00-\u9fff-]+",
            "致命", "家目录用户名即身份信息"),
    Pattern("邮箱地址",
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "致命", "邮箱可反查姓名与学校"),
    Pattern("主机名/内网地址",
            r"\b(?:192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"
            r"|\\\\[A-Za-z0-9_.-]+\\",
            "严重", "内网地址与 UNC 路径暴露所属单位网络"),
    Pattern("QQ/微信/电话",
            r"\b[1-9]\d{4,10}\b(?=\s*(?:\(QQ\)|QQ|微信|电话|手机))"
            r"|(?<!\d)1[3-9]\d{9}(?!\d)",
            "致命", "联系方式即身份信息"),
    Pattern("账号或密钥",
            r"(?i)\b(?:password|passwd|pwd|token|api[_-]?key|secret)\b\s*[:=]\s*\S{6,}",
            "致命", "凭证绝不允许随包发布"),
]

# 「大学 / 学院」是日常词，规则原文、模板占位里到处都有。但它同时也是最要命的
# 泄露载体，所以这里**只放宽两类确凿的通用表述**，并紧贴匹配位置判断：
#   1) 前 1–6 个字就是占位符（某某、某、XX、××、YY），如「XX大学」
#   2) 命中落在规则条文式的上下文里（全国大学生数学建模 / 竞赛组委会 / 学校信息…）
# 绝不把「大学」本身放进白名单——那会让所有"XX大学"的命中被静默吞掉，
# 恰恰是自检要抓的"扫描器看起来在跑，其实全漏"。
PLACEHOLDER_PREFIX_RE = re.compile(r"(?:某某|某|XX|xx|××|[A-Z]\s?校)\s*$")
# 规则条文里的连接词形式的"及赛区/和赛区/或赛区"，指的是规则对象而不是某个具体赛区
CONNECTOR_PREFIX_RE = re.compile(r"(?:及|和|或|与|的|各|本|所在|以及)\s*$")
RULE_CONTEXT_RE = re.compile(
    r"全国大学生数学建模|竞赛组委会|参赛学校|所在学校|学校信息|学校名称|校名|"
    r"示例|占位|placeholder|\.template\.|/templates/|templates\\|规范|章程|样例"
)
SCHOOL_PATTERN_NAMES = frozenset(
    {"中文校名（XX大学）", "中文校名（XX学院）", "中文校名（职业技术学院）"}
)
REGION_PATTERN_NAME = "赛区编号或赛区名"

# 备份 / 缓存 / 临时文件——**包内出现本身就是缺陷**
JUNK_FILE_RE = re.compile(
    r"(?:~$|\.swp$|\.swo$|\.bak$|\.tmp$|\.orig$|\.rej$|"
    r"^\.DS_Store$|^Thumbs\.db$|^desktop\.ini$|"
    r"^\.~lock\.|\.pyc$|\.pyo$|\.log$|\.aux$|\.out$|\.toc$|\.synctex\.gz$)",
    re.I,
)
JUNK_DIR_RE = re.compile(r"^(?:__pycache__|\.ipynb_checkpoints|\.git|\.idea|\.vscode|"
                         r"\.mypy_cache|\.pytest_cache|node_modules|\.Rproj\.user)$", re.I)

# 容器格式内部：这些内部成员名是"结构性"的，不算泄露
ZIP_MEMBER_SKIP_RE = re.compile(
    r"^(?:\[Content_Types\]\.xml|_rels/|docProps/(?:app|core)\.xml$|"
    r"xl/(?:styles|theme|sharedStrings)\.xml$|word/(?:styles|settings|fontTable)\.xml$)",
    re.I,
)


# --------------------------------------------------------------------------
# 文本识别
# --------------------------------------------------------------------------
def decode_bytes(data: bytes) -> str | None:
    """把字节解成文本；二进制（含 NUL 或解码失败）返回 None。

    顺手剥掉 UTF-8 BOM：BOM 是编码标记不是内容，留着会让 `^` 行首锚定的
    模式（如英文署名行）在第一行静默失配——这正是"扫描器看起来在跑其实漏了"。
    """
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    if not data:
        return ""
    if b"\x00" in data[:8192]:
        # 含 NUL 基本是二进制；但 UTF-16 文本也含 NUL，单独试一次
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                txt = data.decode(enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
            printable = sum(1 for ch in txt[:2000] if ch.isprintable() or ch in "\r\n\t")
            if printable >= 0.9 * min(len(txt), 2000):
                return txt
        return None
    for enc in TEXT_ENCODINGS:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return None


def looks_like_text_file(path: str) -> bool:
    """按扩展名粗判；无扩展名文件**也算可疑文本**，必须读（源 skill 的核心洞见）。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in ZIP_CONTAINER_EXTS or ext in JSON_CONTAINER_EXTS:
        return False
    return True


def extract_xml_text(raw: bytes) -> str:
    """从 docx/xlsx 的内部 XML 取可见文本。

    关键：Word 会把一句话切成多个 <w:t> 片段（拼写检查、修订、样式边界都会切），
    所以必须**把片段拼回来再扫**，否则"XX大学"被切成"XX"+"大学"就漏报。
    """
    txt = decode_bytes(raw)
    if txt is None:
        return ""
    parts: list[str] = []
    for tag in ("w:t", "a:t", "t"):
        for m in re.finditer(rf"<(?:\w+:)?{tag}(?:\s[^>]*)?>(.*?)</(?:\w+:)?{tag}>",
                             txt, re.S):
            parts.append(m.group(1))
    joined = "".join(parts)
    # 属性值里也会藏东西（docProps/core.xml 的 dc:creator、xlsx 的 sheet 名）
    attrs = re.findall(r'\w+="([^"]{2,200})"', txt)
    return "\n".join([joined, "\n".join(attrs), txt])


def extract_ipynb_text(raw: bytes) -> str:
    """从 notebook 取 source 与 outputs（输出单元格是最常被忽略的泄露点）。"""
    txt = decode_bytes(raw)
    if txt is None:
        return ""
    try:
        nb = json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return txt
    out: list[str] = []
    for cell in nb.get("cells", []) or []:
        src = cell.get("source")
        if isinstance(src, list):
            out.append("".join(str(s) for s in src))
        elif src:
            out.append(str(src))
        for o in cell.get("outputs", []) or []:
            for key in ("text",):
                v = o.get(key)
                if isinstance(v, list):
                    out.append("".join(str(s) for s in v))
                elif v:
                    out.append(str(v))
            data = o.get("data") or {}
            for k, v in data.items():
                if k.startswith("text/") and isinstance(v, list):
                    out.append("".join(str(s) for s in v))
            if o.get("ename"):
                out.append(f"{o.get('ename')}: {o.get('evalue', '')}")
    meta = nb.get("metadata") or {}
    out.append(json.dumps(meta, ensure_ascii=False))
    out.append(txt)          # 兜底：原始 JSON 全文也扫一遍
    return "\n".join(out)


# --------------------------------------------------------------------------
# 命中记录
# --------------------------------------------------------------------------
class Hit:
    __slots__ = ("level", "where", "pattern", "snippet", "note")

    def __init__(self, level: str, where: str, pattern: str, snippet: str, note: str = ""):
        self.level = level
        self.where = where
        self.pattern = pattern
        self.snippet = " ".join(snippet.split())[:160]
        self.note = note

    def key(self):
        return (self.level, self.where, self.pattern, self.snippet)

    def line(self) -> str:
        return f"[{self.level}] {self.where}  ← 《{self.pattern}》  {self.snippet}"


def is_benign_school_mention(text: str, start: int, end: int, pattern_name: str) -> bool:
    """判断一命中是否属于合法出现（占位符、规则条文、连接词形式）。"""
    left = text[max(0, start - 8): start]
    win = text[max(0, start - 60): end + 60]
    if pattern_name in SCHOOL_PATTERN_NAMES:
        # 1) 紧贴匹配位置向左看：占位符前缀（"XX大学"里的 "XX" 在匹配之外）
        if PLACEHOLDER_PREFIX_RE.search(left):
            return True
        # 2) 规则条文式上下文
        return bool(RULE_CONTEXT_RE.search(win))
    if pattern_name == REGION_PATTERN_NAME:
        m = text[start:end]
        # "赛区信息""赛区名称"是规则条文里的通用表述，不是某个赛区名
        if re.match(r"^赛区(?:信息|名称|名)", m):
            return True
        # "学校及赛区"这类连接词形式指的是规则对象，不是某个具体赛区名。
        # 匹配本身可能已含连接词（如"学校及赛区"），所以同时看命中内部与左侧。
        inner = re.match(r"([\u4e00-\u9fff]{0,6}?)(?:及|和|或|与|的|各|本|所在|以及)", m)
        if inner and inner.group(1):
            return True
        return bool(CONNECTOR_PREFIX_RE.search(left))
    return False


def scan_text(text: str, where: str, extra_keywords: list[str]) -> list[Hit]:
    """在给定文本上跑全部模式 + 自定义关键词。"""
    hits: list[Hit] = []
    for p in PATTERNS:
        for m in p.regex.finditer(text):
            start, end = m.start(), m.end()
            if is_benign_school_mention(text, start, end, p.name):
                continue
            hits.append(Hit(p.level, where, p.name, m.group(0), p.note))
    for kw in extra_keywords:
        if not kw:
            continue
        for m in re.finditer(re.escape(kw), text):
            hits.append(Hit("致命", where, f"自定义关键词：{kw}", m.group(0),
                            "由 --keyword / --keywords-file 指定（不套用任何白名单）"))
    return hits


# --------------------------------------------------------------------------
# 扫描器
# --------------------------------------------------------------------------
class Scanner:
    def __init__(self, keywords: list[str] | None = None, verbose: bool = False):
        self.keywords = list(keywords or [])
        self.verbose = verbose
        self.scanned: list[tuple[str, int]] = []      # (相对路径, 字节数)
        self.skipped: list[str] = []
        self.junk: list[str] = []
        self.hits: list[Hit] = []
        self.errors: list[str] = []

    # ---------------- 文件名 ----------------
    def scan_names(self, relpaths: list[str]) -> None:
        for rel in relpaths:
            norm = rel.replace("\\", "/")
            for part in norm.split("/"):
                if JUNK_DIR_RE.match(part):
                    self.junk.append(f"{rel}  ← 目录 {part}/ 不应出现在提交包里")
                if JUNK_FILE_RE.search(part):
                    self.junk.append(f"{rel}  ← 备份/缓存/日志文件不应出现在提交包里")
            if os.path.splitext(norm)[1] == "" and not norm.endswith("/"):
                self.skipped.append(f"{rel}  ← 无扩展名文件（已按文本读取，勿跳过）")
            self.hits += scan_text(norm, f"文件名：{rel}", self.keywords)

    # ---------------- 内容 ----------------
    def scan_file(self, path: str, rel: str) -> None:
        try:
            size = os.path.getsize(path)
        except OSError as e:
            self.errors.append(f"{rel}: 无法读取大小 {e}")
            return
        self.scanned.append((rel, size))
        ext = os.path.splitext(path)[1].lower()

        if ext in ZIP_CONTAINER_EXTS:
            self.hits += scan_text(rel, f"容器条目名：{rel}", self.keywords)
            self._scan_zip(path, rel, depth=0)
            return
        if ext in JSON_CONTAINER_EXTS:
            with open(path, "rb") as fh:
                raw = fh.read(MAX_MEMBER_BYTES)
            self.hits += scan_text(extract_ipynb_text(raw), f"{rel}", self.keywords)
            return
        if not looks_like_text_file(path):
            return
        with open(path, "rb") as fh:
            raw = fh.read(MAX_MEMBER_BYTES)
        txt = decode_bytes(raw)
        if txt is None:
            self.skipped.append(f"{rel}  ← 二进制内容，未做文本扫描（请人工确认）")
            return
        self.hits += scan_text(txt, rel, self.keywords)

    # ---------------- 容器内部 ----------------
    def _scan_zip(self, path: str, rel: str, depth: int) -> None:
        if depth > MAX_ZIP_DEPTH:
            self.errors.append(f"{rel}: 嵌套压缩包超过 {MAX_ZIP_DEPTH} 层，未继续展开")
            return
        try:
            zf = zipfile.ZipFile(path)
        except (zipfile.BadZipFile, OSError) as e:
            self.errors.append(f"{rel}: 不是可读的 ZIP 容器（{e}）")
            return
        with zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                inner = f"{rel} :: {info.filename}"
                # 内部成员名：目录名与文件名同样泄露
                self.hits += scan_text(info.filename, f"容器内文件名：{inner}", self.keywords)
                if info.file_size > MAX_MEMBER_BYTES:
                    self.skipped.append(f"{inner}  ← 内部成员过大（{info.file_size} B），未扫描")
                    continue
                try:
                    raw = zf.read(info)
                except (zipfile.BadZipFile, OSError, RuntimeError) as e:
                    self.errors.append(f"{inner}: 读取失败 {e}")
                    continue
                inner_ext = os.path.splitext(info.filename)[1].lower()
                if inner_ext in ZIP_CONTAINER_EXTS and not ZIP_MEMBER_SKIP_RE.match(info.filename):
                    # 嵌套压缩包（如 xlsx 内嵌、zip 套 zip）
                    self._scan_member_zip(raw, inner, depth + 1)
                    continue
                if inner_ext in JSON_CONTAINER_EXTS:
                    self.hits += scan_text(extract_ipynb_text(raw), inner, self.keywords)
                    continue
                if inner_ext in (".xml", ".rels") or info.filename.startswith(("word/", "xl/", "ppt/")):
                    self.hits += scan_text(extract_xml_text(raw), inner, self.keywords)
                    continue
                if ZIP_MEMBER_SKIP_RE.match(info.filename):
                    continue
                txt = decode_bytes(raw)
                if txt is None:
                    continue
                self.hits += scan_text(txt, inner, self.keywords)

    def _scan_member_zip(self, raw: bytes, inner: str, depth: int) -> None:
        if depth > MAX_ZIP_DEPTH:
            return
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except (zipfile.BadZipFile, OSError):
            return
        with zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                sub = f"{inner} :: {info.filename}"
                self.hits += scan_text(info.filename, f"容器内文件名：{sub}", self.keywords)
                if info.file_size > MAX_MEMBER_BYTES:
                    continue
                try:
                    data = zf.read(info)
                except (zipfile.BadZipFile, OSError, RuntimeError):
                    continue
                ext = os.path.splitext(info.filename)[1].lower()
                if ext in ZIP_CONTAINER_EXTS and not ZIP_MEMBER_SKIP_RE.match(info.filename):
                    self._scan_member_zip(data, sub, depth + 1)
                elif ext in JSON_CONTAINER_EXTS:
                    self.hits += scan_text(extract_ipynb_text(data), sub, self.keywords)
                elif ext in (".xml", ".rels") or info.filename.startswith(("word/", "xl/", "ppt/")):
                    self.hits += scan_text(extract_xml_text(data), sub, self.keywords)
                else:
                    txt = decode_bytes(data)
                    if txt is not None:
                        self.hits += scan_text(txt, sub, self.keywords)

    # ---------------- 报告 ----------------
    def dedup(self) -> None:
        seen = set()
        uniq = []
        for h in self.hits:
            if h.key() in seen:
                continue
            seen.add(h.key())
            uniq.append(h)
        self.hits = uniq


# --------------------------------------------------------------------------
# allowlist 解析
# --------------------------------------------------------------------------
def parse_allowlist(path: str) -> tuple[list[str], list[str]]:
    """读 allowlist 文件，解析成显式文件列表。

    每一行：一条路径或一个 glob（支持 `**`）。`#` 开头为注释。
    返回 (解析后的绝对路径列表, 报错行)。
    """
    import glob as globmod

    if not os.path.exists(path):
        raise FileNotFoundError(f"allowlist 文件不存在：{path}")
    base = os.path.dirname(os.path.abspath(path)) or "."
    entries: list[str] = []
    errors: list[str] = []
    with open(path, "rb") as fh:
        head = fh.read(4)
    enc = "utf-8-sig" if head.startswith(b"\xef\xbb\xbf") else "utf-8"
    with open(path, encoding=enc) as fh:
        for lineno, line in enumerate(fh, 1):
            s = line.strip().lstrip("\ufeff")   # 兜底：带 BOM 的 UTF-8 不算内容
            if not s or s.startswith("#"):
                continue
            entries.append((lineno, s))

    files: list[str] = []
    for lineno, entry in entries:
        raw = entry.replace("\\", "/")
        # 相对路径按 allowlist 文件所在目录解析
        if os.path.isabs(raw) or re.match(r"^[A-Za-z]:/", raw):
            pattern = raw
        else:
            pattern = os.path.join(base, raw)
        hits = globmod.glob(pattern, recursive=True)
        if not hits:
            errors.append(f"第 {lineno} 行：'{entry}' 未匹配到任何文件")
            continue
        for h in hits:
            h = os.path.abspath(h)
            if os.path.isdir(h):
                for dp, dns, fns in os.walk(h):
                    for fn in sorted(fns):
                        files.append(os.path.join(dp, fn))
            else:
                files.append(h)
    # 去重且保持稳定顺序
    out, seen = [], set()
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out, errors


def sha256_of(path: str, limit: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk or limit <= 0:
                break
            limit -= len(chunk)
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------
def stage_files(files: list[str], stage_dir: str, base: str) -> tuple[int, list[str]]:
    """把 allowlisted 文件复制到**空的** staging 目录。返回 (复制数, 冲突列表)。"""
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir, onerror=_force_rm)
    os.makedirs(stage_dir, exist_ok=True)
    copied, clashes = 0, []
    for src in files:
        rel = os.path.relpath(src, base)
        if rel.startswith(".."):
            rel = os.path.basename(src)
        dst = os.path.join(stage_dir, rel)
        if os.path.exists(dst):
            clashes.append(rel)
            continue
        os.makedirs(os.path.dirname(dst) or stage_dir, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    return copied, clashes


def _force_rm(func, path, _exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def walk_stage(stage_dir: str) -> list[str]:
    rels: list[str] = []
    for dp, dns, fns in os.walk(stage_dir):
        dns.sort()
        for fn in sorted(fns):
            rels.append(os.path.relpath(os.path.join(dp, fn), stage_dir).replace("\\", "/"))
    return sorted(rels)


# --------------------------------------------------------------------------
# 自检：在**真实格式**里植入已知字符串
# --------------------------------------------------------------------------
SELFTEST_SEEDS = [
    ("中文校名（docx 正文 XML，且被切分成两个 run）", "南京某某大学",
     "seeds/论文摘要.docx", "中文校名（XX大学）"),
    ("学号（xlsx 单元格）", "2026123456",
     "seeds/数据台账.xlsx", "学号"),
    ("POSIX 家目录路径（ipynb 输出单元格）", "/home/zhangsan/project",
     "seeds/建模过程.ipynb", "POSIX 家目录路径"),
    ("Windows 用户名路径（无扩展名文件）", "C:\\Users\\zhangsan\\Desktop",
     "seeds/说明文件", "Windows 绝对路径（含用户名）"),
    ("邮箱（纯文本）", "zhangsan@nju.edu.cn",
     "seeds/requirements.txt", "邮箱地址"),
    ("赛区名（验证白名单没有把真赛区一起放行）", "江苏赛区",
     "seeds/说明文件", "赛区编号或赛区名"),
]

_DOCX_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

_DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

_DOCX_CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:creator>孙七</dc:creator><cp:lastModifiedBy>孙七</cp:lastModifiedBy>
</cp:coreProperties>"""


def _docx_document_xml() -> str:
    """故意把校名切成两个 <w:t>，检验扫描器是否把 run 拼回来。"""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>本文由</w:t></w:r><w:r><w:t>南京某某</w:t></w:r><w:r><w:t>大学</w:t></w:r>
<w:r><w:t>参赛队完成。</w:t></w:r></w:p></w:body></w:document>"""


def write_docx(path: str) -> None:
    # 必须显式 encoding="utf-8"：zipfile.writestr 对 str 参数用 cp1252 编码会写坏中文
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _DOCX_CT.encode("utf-8"))
        zf.writestr("_rels/.rels", _DOCX_RELS.encode("utf-8"))
        zf.writestr("docProps/core.xml", _DOCX_CORE.encode("utf-8"))
        zf.writestr("word/document.xml", _docx_document_xml().encode("utf-8"))


def write_xlsx(path: str) -> None:
    ct = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    wb = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheets><sheet name="南京某某大学台账" sheetId="1" r:id="rId1"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets></workbook>"""
    sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="inlineStr"><is><t>学号</t></is></c>
<c r="B1" t="inlineStr"><is><t>2026123456</t></is></c></row>
</sheetData></worksheet>"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct.encode("utf-8"))
        zf.writestr("_rels/.rels", rels.encode("utf-8"))
        zf.writestr("xl/workbook.xml", wb.encode("utf-8"))
        zf.writestr("xl/worksheets/sheet1.xml", sheet.encode("utf-8"))


def write_ipynb(path: str) -> None:
    nb = {
        "cells": [
            {"cell_type": "code", "execution_count": 1, "metadata": {},
             "source": ["import pandas as pd\n", "df = pd.read_csv('data.csv')\n"],
             "outputs": [{"output_type": "stream", "name": "stdout",
                          "text": ["读取 /home/zhangsan/project/data.csv 完成\n"]}]},
        ],
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                     "language_info": {"name": "python", "version": "3.11.5"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(nb, fh, ensure_ascii=False, indent=1)


# 干净对照：这些文件里不含任何植入串，若产生命中即为**误报**
SELFTEST_CLEAN = {
    "seeds/clean_notes.md": "# 模型说明\n\n本队使用混合整数规划求解，目标函数为日运行成本最小。\n"
                            "参数取自题目附件，单位统一为元/(kW·h)。\n",
    "seeds/clean.ipynb": json.dumps({"cells": [{"cell_type": "code", "source": ["x = 1\n"],
                                                "outputs": [], "metadata": {}}],
                                     "metadata": {}, "nbformat": 4, "nbformat_minor": 5},
                                    ensure_ascii=False),
}
# 白名单对照：规则原文、模板占位、通用表述里的「大学/学院」**不应**报泄露。
# 这半边与"漏报检查"同等重要：白名单收得太宽 = 静默漏报，收得太紧 = 满屏噪音。
SELFTEST_ALLOWED = {
    "seeds/clean_rules.md":
        "- [ ] 已完成：论文全文（摘要页/正文/附录）无参赛者身份、学校及赛区信息\n"
        "- [ ] 已完成：XX大学模板占位已替换为中性命名\n"
        "依据《全国大学生数学建模竞赛论文格式规范》，参赛学校有责任监督竞赛纪律。\n"
        "学校信息、赛区信息一律不得出现在任何位置。\n",
}


def scan_one(path: str, rel: str, keywords: list[str]) -> list[Hit]:
    """扫单个文件并返回命中（自检用）。"""
    sc = Scanner(keywords=keywords)
    sc.scan_file(path, rel)
    sc.dedup()
    return sc.hits


def run_selftest(root: str, keywords: list[str], verbose: bool) -> tuple[bool, list[str]]:
    """在 root/selftest 下造一棵含已知泄露的 staged tree，验证扫描器在工作。"""
    log: list[str] = []
    tree = os.path.join(root, "selftest")
    if os.path.isdir(tree):
        shutil.rmtree(tree, onerror=_force_rm)
    os.makedirs(os.path.join(tree, "seeds"), exist_ok=True)

    write_docx(os.path.join(tree, "seeds", "论文摘要.docx"))
    write_xlsx(os.path.join(tree, "seeds", "数据台账.xlsx"))
    write_ipynb(os.path.join(tree, "seeds", "建模过程.ipynb"))
    # 无扩展名文件——文本扫描默认按扩展名跳过，这里专门验证它没被跳过
    with open(os.path.join(tree, "seeds", "说明文件"), "w", encoding="utf-8") as fh:
        fh.write("运行说明\n本地路径：C:\\Users\\zhangsan\\Desktop\\建模\\code\n"
                 "参赛环境：江苏赛区（植入用）\n")
    with open(os.path.join(tree, "seeds", "requirements.txt"), "w", encoding="utf-8") as fh:
        fh.write("# 维护人 zhangsan@nju.edu.cn\nnumpy==1.26.4\npandas==2.2.2\n")
    # 备份文件：包内出现即缺陷
    with open(os.path.join(tree, "seeds", "model.py~"), "w", encoding="utf-8") as fh:
        fh.write("# 编辑器备份文件\n")
    os.makedirs(os.path.join(tree, "seeds", "__pycache__"), exist_ok=True)
    with open(os.path.join(tree, "seeds", "__pycache__", "model.cpython-311.pyc"),
              "wb") as fh:
        fh.write(b"\x00\x01binary cache\x00")
    # 干净对照
    for rel, content in SELFTEST_CLEAN.items():
        p = os.path.join(tree, rel.replace("/", os.sep))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
    # 白名单对照
    for rel, content in SELFTEST_ALLOWED.items():
        p = os.path.join(tree, rel.replace("/", os.sep))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)

    rels = walk_stage(tree)
    sc = Scanner(keywords=keywords, verbose=verbose)
    sc.scan_names(rels)
    for rel in rels:
        sc.scan_file(os.path.join(tree, rel.replace("/", os.sep)), rel)
    sc.dedup()

    ok = True
    log.append("植入的已知字符串（应为每条都能被抓到）：")
    for desc, seed, where, want in SELFTEST_SEEDS:
        hit = next((h for h in sc.hits
                    if h.where.startswith(where) and h.pattern == want), None)
        mark = "命中" if hit else "**漏报**"
        if not hit:
            ok = False
        log.append(f"  [{mark}] {desc}")
        log.append(f"          植入：{seed}")
        log.append(f"          位置：{where}")
        if hit:
            log.append(f"          抓到：《{hit.pattern}》 @ {hit.where}")
            log.append(f"          证据：{hit.snippet}")
        else:
            log.append(f"          期望模式：《{want}》（未命中——这是自检失败，不是'包很干净'）")

    log.append("干净对照（应为 0 命中，否则是误报）：")
    for rel in SELFTEST_CLEAN:
        bad = [h for h in sc.hits if h.where.startswith(rel)]
        mark = "干净" if not bad else f"**误报 {len(bad)} 条**"
        if bad:
            ok = False
        log.append(f"  [{mark}] {rel}")
        for h in bad:
            log.append(f"          误报：《{h.pattern}》 → {h.snippet}")

    log.append("白名单上下文对照（规则原文与模板占位里的「大学/学院」不应算泄露）：")
    for rel, text in SELFTEST_ALLOWED.items():
        p = os.path.join(tree, rel.replace("/", os.sep))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        got = scan_one(p, rel, keywords)
        mark = "已放行" if not got else f"**误报 {len(got)} 条**"
        if got:
            ok = False
        log.append(f"  [{mark}] {rel}")
        for h in got:
            log.append(f"          误报：《{h.pattern}》 → {h.snippet}")

    log.append("垃圾文件侦测（包内出现即缺陷）：")
    junk_expect = ("model.py~", "__pycache__")
    for token in junk_expect:
        got = [j for j in sc.junk if token in j]
        mark = "抓到" if got else "**漏报**"
        if not got:
            ok = False
        log.append(f"  [{mark}] {token}")
        for g in got[:3]:
            log.append(f"          {g}")

    log.append(f"自检扫描统计：文件 {len(sc.scanned)} 个，命中 {len(sc.hits)} 条，"
               f"垃圾项 {len(sc.junk)} 条，未扫描 {len(sc.skipped)} 条")
    shutil.rmtree(tree, onerror=_force_rm)
    log.append("自检临时树已清理。")
    return ok, log


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def build_report(args, sections: list[str]) -> str:
    head = [
        "=" * 78,
        "国赛提交包 · allowlist 打包与身份信息扫描报告",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"工作目录：{os.path.abspath(os.getcwd())}",
        "=" * 78,
        "",
    ]
    return "\n".join(head + sections) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="国赛提交包 allowlist 打包 + 身份信息扫描（staged tree）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allowlist", metavar="FILE",
                    help="allowlist 文件：每行一个路径或 glob（# 开头为注释）")
    ap.add_argument("--base", default=".",
                    help="计算 staging 内相对路径的基准目录（默认：当前目录）")
    ap.add_argument("--stage", action="store_true", help="把 allowlisted 文件复制到空 staging 目录")
    ap.add_argument("--stage-dir", default=STAGE_DEFAULT, help=f"staging 目录（默认 {STAGE_DEFAULT}）")
    ap.add_argument("--scan", action="store_true", help="扫描 staged tree（文件名 + 内容 + 容器内部）")
    ap.add_argument("--selftest", action="store_true",
                    help="在真实格式里植入已知字符串，验证扫描器真的在工作（含泄误报检查）")
    ap.add_argument("--keyword", action="append", default=[],
                    help="额外关键词，可重复（如本校校名、队员姓名）")
    ap.add_argument("--keywords-file", help="关键词文件，每行一个")
    ap.add_argument("--report", default=REPORT_DEFAULT, help=f"报告输出文件（默认 {REPORT_DEFAULT}）")
    ap.add_argument("--json", dest="json_out", help="同时输出机器可读的 JSON 摘要")
    ap.add_argument("--quiet", action="store_true", help="不打印报告正文")
    args = ap.parse_args(argv)

    # 关键字
    keywords = list(args.keyword)
    if args.keywords_file and os.path.exists(args.keywords_file):
        with open(args.keywords_file, encoding="utf-8") as fh:
            keywords += [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    if not any([args.allowlist, args.scan, args.selftest]):
        ap.print_help()
        return 2

    sections: list[str] = []
    exit_code = 0
    summary = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "allowlist_count": 0, "staged_count": 0,
               "hits": [], "junk": [], "selftest_ok": None}

    # ---------------- 1. allowlist ----------------
    files: list[str] = []
    if args.allowlist:
        try:
            files, errs = parse_allowlist(args.allowlist)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2
        base = os.path.abspath(args.base)
        sections.append("【1】allowlist 解析（这份**显式文件列表**才是产物，生成它的命令不是）")
        sections.append(f"  allowlist 文件：{os.path.abspath(args.allowlist)}")
        sections.append(f"  解析出 {len(files)} 个文件（glob 已展开，无目录、无通配符）：")
        sections.append("")
        sections.append(f"  {'相对路径':<58}{'字节':>12}  SHA256(前16)")
        sections.append("  " + "-" * 92)
        for f in files:
            rel = os.path.relpath(f, base) if not os.path.relpath(f, base).startswith("..") \
                else os.path.basename(f)
            try:
                size = os.path.getsize(f)
                digest = sha256_of(f)[:16]
            except OSError:
                size, digest = -1, "读取失败"
            sections.append(f"  {rel:<58}{size:>12}  {digest}")
        sections.append("")
        sections.append(f"  合计 {len(files)} 个文件，"
                        f"{sum(os.path.getsize(f) for f in files if os.path.exists(f))} 字节")
        if errs:
            exit_code = 1
            sections.append("  ✗ 以下 allowlist 行未匹配到文件（必须改对再打包）：")
            for e in errs:
                sections.append(f"      {e}")
        sections.append("  ⚠️ 请**人工逐行复核上表**：包内容由这份列表决定，不由排除规则决定。")
        sections.append("")
        summary["allowlist_count"] = len(files)

    # ---------------- 2. stage ----------------
    stage_dir = os.path.abspath(args.stage_dir)
    if args.stage:
        if not files:
            print("--stage 需要同时给出 --allowlist", file=sys.stderr)
            return 2
        base = os.path.abspath(args.base)
        sections.append("【2】复制到空 staging 目录（此后只认 staged tree）")
        sections.append(f"  staging 目录：{stage_dir}")
        copied, clashes = stage_files(files, stage_dir, base)
        sections.append(f"  复制 {copied} 个文件；重名冲突 {len(clashes)} 个")
        for c in clashes:
            sections.append(f"      ✗ 重名：{c}（allowlist 里两个不同路径映射到同一目标）")
        if clashes:
            exit_code = 1
        staged_files = walk_stage(stage_dir)
        sections.append(f"  staged tree 实际文件数：{len(staged_files)}（应等于 {len(files)}）")
        if len(staged_files) != len(files):
            exit_code = 1
            sections.append("  ✗ 数量不符：staging 里多出或少了文件，先查清楚再继续")
        sections.append("  ⚠️ 从这里开始**只看 staging**。工作目录里含那个'缺失的文件'，"
                        "从里面看永远看不出问题。")
        sections.append("")
        summary["staged_count"] = len(staged_files)

    # ---------------- 3. scan ----------------
    if args.scan:
        if not os.path.isdir(stage_dir):
            print(f"staging 目录不存在：{stage_dir}（先跑 --stage）", file=sys.stderr)
            return 2
        rels = walk_stage(stage_dir)
        sc = Scanner(keywords=keywords)
        sc.scan_names(rels)
        for rel in rels:
            sc.scan_file(os.path.join(stage_dir, rel.replace("/", os.sep)), rel)
        sc.dedup()

        sections.append("【3】扫描 staged tree（文件名 + 内容 + 容器格式内部）")
        sections.append(f"  扫描对象：{stage_dir}")
        sections.append(f"  文件数：{len(sc.scanned)}；总计 {sum(s for _, s in sc.scanned)} 字节")
        sections.append(f"  自定义关键词：{keywords if keywords else '（无）'}")
        sections.append("")
        sections.append("  已扫描清单（逐字节扫描的范围，作为证据留痕）：")
        for rel, size in sc.scanned:
            sections.append(f"      {rel:<64}{size:>10} B")
        if sc.skipped:
            sections.append("")
            sections.append("  未做文本扫描（需人工确认）：")
            for s in sc.skipped:
                sections.append(f"      - {s}")
        if sc.errors:
            sections.append("")
            sections.append("  读取异常（先修掉，别当成'没问题'）：")
            for e in sc.errors:
                sections.append(f"      ! {e}")

        fatal = [h for h in sc.hits if h.level == "致命"]
        severe = [h for h in sc.hits if h.level == "严重"]
        sections.append("")
        sections.append(f"  命中汇总：致命 {len(fatal)} 条，严重 {len(severe)} 条，"
                        f"垃圾/备份文件 {len(sc.junk)} 项")
        if sc.hits:
            sections.append("")
            sections.append("  ── 命中明细（每一条都必须处置：删掉、改名、或清空容器属性）──")
            for h in sorted(sc.hits, key=lambda x: (x.level != "致命", x.where)):
                sections.append(f"      {h.line()}")
                if h.note:
                    sections.append(f"          依据：{h.note}")
            exit_code = 1
        else:
            sections.append("")
            sections.append("  ✓ 内容与文件名 0 命中。")
            sections.append("    ⚠️ 注意：'0 命中'与'扫描器没在跑'输出相同——"
                            "必须看下一节的自检结果才能区分。")
        if sc.junk:
            sections.append("")
            sections.append("  ── 不该进包的备份/缓存文件（包内出现本身就是缺陷）──")
            for j in sc.junk:
                sections.append(f"      {j}")
        sections.append("")
        summary["hits"] = [{"level": h.level, "where": h.where, "pattern": h.pattern,
                            "snippet": h.snippet} for h in sc.hits]
        summary["junk"] = sc.junk

    # ---------------- 4. selftest ----------------
    if args.selftest:
        tmp_root = args.stage_dir if os.path.isdir(args.stage_dir) else "."
        sections.append("【4】自检：植入已知字符串，验证扫描器真的在工作")
        sections.append("  目的：干净树的'0 命中'与'扫描器根本没运行'输出完全一样。")
        sections.append("  做法：把已知串放进**真实格式**（docx 的 XML run、xlsx 单元格、"
                        "ipynb 输出单元格、")
        sections.append("        无扩展名文件、纯文本），再看扫描器是否抓到；"
                        "同时放两个干净文件查误报。")
        sections.append("")
        ok, log = run_selftest(os.path.abspath(tmp_root), keywords, verbose=False)
        sections += ["  " + ln for ln in log]
        sections.append("")
        sections.append(f"  自检结论：{'通过（扫描器确实在工作）' if ok else '**失败——扫描结果不可信，禁止据此提交**'}")
        sections.append("")
        summary["selftest_ok"] = ok
        if not ok:
            exit_code = 1

    # ---------------- 5. 收尾 ----------------
    sections.append("【5】本报告的分工")
    sections.append("  本脚本负责：包内容 = allowlist 的显式列表；staged tree 的字节级身份信息扫描；")
    sections.append("             扫描器有效性自检。")
    sections.append("  本脚本不负责：论文正文与 PDF 元数据（用 validate_pipeline.py --stage P14）、")
    sections.append("             提交包文件名与体积上限（--stage P16）、")
    sections.append("             附录代码能否跑通（必须解压到干净目录实跑一遍）。")
    sections.append("")
    sections.append(f"结论：{'存在阻断项，禁止提交' if exit_code else '未发现阻断项'}"
                    "（人工复核仍不可省略）")

    report = build_report(args, sections)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)
    if args.json_out:
        summary["exit_code"] = exit_code
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)
    if not args.quiet:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(report)
    else:
        print(f"报告已写入 {args.report}；退出码 {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
