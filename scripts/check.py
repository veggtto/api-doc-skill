#!/usr/bin/env python3
"""模板自检：改完 skills/api-doc/assets/template.html 或 examples/ 跑一次。

查六件事，都是肉眼看不出来的腐化：
  1. body 用了样式表没定义的 class —— 静默失效，没有任何报错
  2. 模板的 style/script 和样例走样 —— 历次只同步样式忘了同步骨架
  3. SKILL.md 里推荐的 class / CSS 变量 / 元素选择器模板已经没有了 —— 文档教了不存在的用法
  4. 目录 href 和 h2 的 id 对不上 —— 滚动高亮和锚点静默失效
  5. 样例里残留 {{占位符}} —— 样例应当是真实产出
  6. 模板主骨架混进了特定项目的前提（两端对照、新旧对拍）—— 默认路径该是填空，不是删改
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "api-doc"
TPL = SKILL_DIR / "assets" / "template.html"
EX_DIR = ROOT / "examples"
SKILL = SKILL_DIR / "SKILL.md"

problems = []


def block(text, tag):
    return text[text.index("<%s>" % tag):text.index("</%s>" % tag)]


tpl = TPL.read_text(encoding="utf-8")
tpl_style = block(tpl, "style")
tpl_body = tpl[tpl.index("</style>"):]
defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", tpl_style))
root_vars = set(re.findall(r"--[a-zA-Z][\w-]*", re.search(r":root\{(.*?)\}", tpl_style, re.S).group(1)))
tpl_tags = set(re.findall(r"<([a-zA-Z][\w-]*)", tpl_body))

examples = sorted(p for p in EX_DIR.glob("*.html")) if EX_DIR.exists() else []


# 1. body 引用了未定义的 class（模板和样例共用同一份样式表）
def check_classes(label, body):
    used = {c for m in re.finditer(r'class="([^"]+)"', body) for c in m.group(1).split()}
    missing = sorted(used - defined)
    if missing:
        problems.append("%s 用了样式表没定义的 class: %s" % (label, ", ".join("." + c for c in missing)))


check_classes("模板 body", tpl_body)

# 2. 模板与样例是否同源
for ex_path in examples:
    ex = ex_path.read_text(encoding="utf-8")
    for tag in ("style", "script"):
        if block(tpl, tag) != block(ex, tag):
            problems.append(
                "模板的 <%s> 与 examples/%s 不一致 —— "
                "样例是回归基准，改了模板要同步样例（反之亦然）" % (tag, ex_path.name)
            )
    check_classes("examples/%s body" % ex_path.name, ex[ex.index("</style>"):])

# 3. SKILL.md 推荐的 class / CSS 变量 / 元素选择器是否还在模板里
CLASS_RE = re.compile(r"(?:tr)?\.([a-zA-Z][\w-]*(?:\.[a-zA-Z][\w-]*)?)")
# 选择器前面允许是行首、空白、引号、括号、子选择器 >；紧跟字母数字的 . 是属性访问，不算
OK_PREFIX = " \t\n'\"(>"
# 围栏代码块先吃掉，否则 ``` 会把之后的行内反引号配对整体错位，后半篇文档白查
FRAG_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```|`([^`\n]+)`", re.S)


def class_names(frag):
    for m in CLASS_RE.finditer(frag):
        i = m.start()
        prev = frag[i - 1] if i else ""
        if prev and prev not in OK_PREFIX:
            continue
        # <feature>.html 这类路径不是选择器：> 前面还贴着字母
        if prev == ">" and i >= 2 and (frag[i - 2].isalnum() or frag[i - 2] == "_"):
            continue
        for c in m.group(1).split("."):
            yield c


if SKILL.exists():
    doc = SKILL.read_text(encoding="utf-8")
    recommended, used_vars, used_tags = set(), set(), set()
    for m in FRAG_RE.finditer(doc):
        frag = m.group(1) or m.group(2)
        recommended.update(class_names(frag))
        used_vars.update(re.findall(r"--[a-zA-Z][\w-]*", frag))
        used_tags.update(re.findall(r"(?:^|[\s'\"(>;}])([a-zA-Z][\w-]*)\{", frag))
    gone = sorted(c for c in recommended if c not in defined)
    if gone:
        problems.append(
            "SKILL.md 推荐了模板里已不存在的 class: " + ", ".join("." + c for c in gone)
        )
    gone_vars = sorted(v for v in used_vars if v not in root_vars)
    if gone_vars:
        problems.append(
            "SKILL.md 提到了模板 :root 里没有的 CSS 变量: " + ", ".join(gone_vars)
        )
    gone_tags = sorted(t for t in used_tags if t not in tpl_tags)
    if gone_tags:
        problems.append(
            "SKILL.md 用了模板里不存在的元素选择器: " + ", ".join(t + "{…}" for t in gone_tags)
        )

# 4. 目录 href 与 h2 的 id 一一对应
for label, text in [("模板", tpl)] + [("examples/" + p.name, p.read_text(encoding="utf-8")) for p in examples]:
    m = re.search(r'id="toc"(.*?)</ol>', text, re.S)
    if not m:
        problems.append("%s 找不到 id=\"toc\" 的目录块" % label)
        continue
    hrefs = re.findall(r'href="#([^"]+)"', m.group(1))
    ids = set(re.findall(r'\bid="([^"]+)"', text))
    dangling = [h for h in hrefs if h not in ids]
    if dangling:
        problems.append("%s 目录里的 href 找不到对应元素: %s" % (label, ", ".join("#" + h for h in dangling)))
    absent = [i for i in re.findall(r'<h2[^>]*\bid="([^"]+)"', text) if i not in hrefs]
    if absent:
        problems.append("%s 有 h2 没进目录: %s" % (label, ", ".join("#" + i for i in absent)))

# 5. 样例里不该残留占位符
for ex_path in examples:
    if "{{" in ex_path.read_text(encoding="utf-8"):
        problems.append("examples/%s 里残留了 {{占位符}} —— 样例应当是真实产出" % ex_path.name)

# 6. 主骨架（注释之外）必须保持中性：单端、全新接口、任意方法
bare = re.sub(r"<!--.*?-->", "", tpl_body, flags=re.S)
leaked = [s for s in ('class="end', 'class="split', "原接口", "对照接口", "对拍") if s in bare]
if leaked:
    problems.append(
        "模板主骨架出现了特定项目的前提: %s —— 两端对照和新旧对拍属于可选块，"
        "只能待在 body 末尾的注释里；主骨架要保持单端、全新接口、任意方法" % ", ".join(leaked)
    )

if problems:
    print("发现 %d 处问题：" % len(problems))
    for p in problems:
        print("  x " + p)
    sys.exit(1)

print("ok  模板 %d 行，%d 个占位符，class 全部有定义，目录对得上，与 %d 个样例同源"
      % (tpl.count("\n") + 1, len(re.findall(r"\{\{", tpl_body)), len(examples)))
