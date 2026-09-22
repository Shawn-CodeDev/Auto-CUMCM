"""精确调试：把附录2/3/4 区块原文写到文件（避免控制台编码问题）。"""
import re
t = open(r"E:\Math-SOP\logs\A2026_problem_text.txt", encoding="utf-8").read()
t = t.replace("（", "(").replace("）", ")")

out = []
for tag in ("附录1", "附录2", "附录3", "附录4"):
    ms = [m.start() for m in re.finditer(re.escape(tag) + r"\s{2,}\S", t)]
    out.append(f"{tag}: 标题匹配位置 {ms}")
    out.append(f"   全文出现次数 {t.count(tag)}")

i2 = (re.search(r"附录2\s{2,}\S", t) or re.match(r"", "")).start() if re.search(r"附录2\s{2,}\S", t) else -1
i3 = (re.search(r"附录3\s{2,}\S", t) or re.match(r"", "")).start() if re.search(r"附录3\s{2,}\S", t) else -1
out.append(f"\n=== 附录2 区块 [{i2}:{i3}] 原文 ===")
out.append(t[i2:i3])
out.append("\n=== 附录2 区块 repr ===")
out.append(ascii(t[i2:i3]))
out.append("\n=== 附录3 区块原文 ===")
i4s = re.search(r"附录4\s{2,}\S", t)
i4 = i4s.start() if i4s else len(t)
out.append(t[i3:i4])
out.append("\n=== 附录4 区块原文 ===")
out.append(t[i4:])
out.append("\n=== 关键词计数 ===")
for kw in ("对流换热系数", "对流传质系数", "换热", "W/(m2·K)", "W/(m2", "kg/m3"):
    out.append(f"  {kw!r}: 全文 {t.count(kw)} 次；附录2区块内 {t[i2:i3].count(kw)} 次")

open(r"E:\Math-SOP\logs\dbg_appendix2.txt", "w", encoding="utf-8").write("\n".join(out))
print("written")
