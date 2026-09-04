#!/usr/bin/env python3
"""模板自检：改完 assets/template.html 或 examples/ 跑一次。

查三件事，都是肉眼看不出来的腐化：
  1. body 用了样式表没定义的 class —— 静默失效，没有任何报错
  2. 模板的 style/script 和样例走样 —— 历次只同步样式忘了同步骨架
  3. SKILL.md 里推荐的 class 模板已经没有了 —— 文档教了不存在的用法
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "assets" / "template.html"
EX = ROOT / "examples" / "keyboard-tree.html"
SKILL = ROOT / "SKILL.md"

problems = []


def block(text, tag):
    return text[text.index("<%s>" % tag):text.index("</%s>" % tag)]


tpl = TPL.read_text(encoding="utf-8")
tpl_style = block(tpl, "style")
tpl_body = tpl[tpl.index("</style>"):]
defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", tpl_style))

# 1. body 引用了未定义的 class
used = {c for m in re.finditer(r'class="([^"]+)"', tpl_body) for c in m.group(1).split()}
missing = sorted(used - defined)
if missing:
    problems.append("模板 body 用了样式表没定义的 class: " + ", ".join("." + c for c in missing))

# 2. 模板与样例是否同源
if EX.exists():
    ex = EX.read_text(encoding="utf-8")
    for tag in ("style", "script"):
        if block(tpl, tag) != block(ex, tag):
            problems.append(
                "模板的 <%s> 与 examples/%s 不一致 —— "
                "样例是回归基准，改了模板要同步样例（反之亦然）" % (tag, EX.name)
            )

# 3. SKILL.md 推荐的 class 是否还在模板里
if SKILL.exists():
    doc = SKILL.read_text(encoding="utf-8")
    # 只看表格里 `.foo` / `.foo.bar` / `tr.new` 这种形态的反引号片段
    recommended = set()
    for frag in re.findall(r"`([^`]+)`", doc):
        for m in re.finditer(r"(?:^|\s)(?:tr)?\.([a-zA-Z][\w-]*(?:\.[a-zA-Z][\w-]*)?)", frag):
            recommended.update(m.group(1).split("."))
    gone = sorted(c for c in recommended if c not in defined)
    if gone:
        problems.append(
            "SKILL.md 推荐了模板里已不存在的 class: " + ", ".join("." + c for c in gone)
        )

if problems:
    print("发现 %d 处问题：" % len(problems))
    for p in problems:
        print("  x " + p)
    sys.exit(1)

print("ok  模板 %d 行，%d 个占位符，class 全部有定义，与样例同源"
      % (tpl.count("\n") + 1, len(re.findall(r"\{\{", tpl_body))))
