"""打印附录 2/3/4 的原文片段（带可见换行标记），用于校准抽取正则。"""
import re
t = open(r"E:\Math-SOP\logs\A2026_problem_text.txt", encoding="utf-8").read()
t = t.replace("（", "(").replace("）", ")")
for tag in ("附录2", "附录3", "附录4"):
    i = t.find(tag)
    seg = t[i:i + 700] if i >= 0 else "<未找到>"
    print("=" * 70)
    print(f"--- {tag} @ {i} ---")
    print(repr(seg[:650]))
    print()
