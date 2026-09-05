#!/usr/bin/env python3
"""产出自检：交付前对生成的接口文档 HTML 跑一遍，查八类机械可判的问题。

用法: python3 lint_output.py <产出.html> [产出2.html ...] [--template <模板路径>]
模板默认取脚本同级的 ../assets/template.html。

查的是「肉眼扫一遍看不出、但读者一定会撞上」的几类：
  1. <style>/<script> 与模板不一致 —— 自己改了样式或加了 CSS，样例就不再是同一份
  2. 用了样式表里没有的 class —— 静默失效，没有任何报错
  3. 残留 {{占位符}}
  4. 空话单元格（无 / 暂无 / N/A / — / TODO ...）—— 这一格没内容就该删掉整行
  5. 模板的示范文字被原样留下（"A 端"、"典型响应"、"示例来源："...）
  6. 目录 href 指向不存在的 id、或有 h2 没进目录 —— 滚动高亮和锚点静默失效
  7. 替团队做承诺的句式（"我们会"、"届时会"、"请提出来"...）—— 写文档的是模型，
     无权承诺接口演进和团队流程，读者却会当成后端的正式表态；改成「待决策 + 该问谁」
  8. .tag.ok 写了"均已/全部"却同时挂着 .tag.todo —— 首部总括话术和正文待补验证项矛盾
     （首部 .facts 里已经写明"待补验证"就不算矛盾，作者已对齐）

有问题 exit 1，否则 exit 0。
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def block(text, tag):
    i = text.find("<%s>" % tag)
    j = text.find("</%s>" % tag)
    return text[i:j] if i >= 0 and j >= 0 else ""


def strip_comments(s):
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def text_of(html):
    return re.sub(r"<[^>]+>", "", html)


FILLER = re.compile(r"^\s*(无|暂无|没有|N/?A|-|—|——|待补充|TODO|略)\s*[。.]?\s*$", re.I)
# 模板里的示范文字，留在产出里说明这块没改
DEMO = ("A 端", "B 端", "最容易踩的坑，加粗", "结论先行，加粗", "典型响应",
        "关键字段的判定口径", "均已实跑 / 有未验证项", "示例来源：")
# 替团队做承诺的句式
PROMISE = ("我们会", "届时会", "后续会", "会提前", "请提出来", "我们将")
SENT_SPLIT = re.compile(r"[。！？；\n]")


def lint(path, tpl_style, tpl_script, defined):
    html = Path(path).read_text(encoding="utf-8")
    body = strip_comments(html[html.find("</style>"):])
    plain = text_of(body)
    probs = []

    # 1. 与模板走样
    if block(html, "style") != tpl_style:
        probs.append("<style> 与模板不一致（改了样式或自己加了 CSS）")
    if block(html, "script") != tpl_script:
        probs.append("<script> 与模板不一致")

    # 2. 未定义的 class
    used = {c for m in re.finditer(r'class="([^"]+)"', body) for c in m.group(1).split()}
    undefined = sorted(used - defined)
    if undefined:
        probs.append("用了样式表没有的 class: " + ", ".join("." + c for c in undefined))

    # 3. 残留占位符
    left = re.findall(r"\{\{[^}]*\}\}", body)
    if left:
        probs.append("残留占位符 %d 处: %s" % (len(left), "; ".join(left[:4])))

    # 4. 空话单元格
    filler = sorted({text_of(c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)
                     if FILLER.match(text_of(c))})
    if filler:
        probs.append("空话单元格 %d 种: %s —— 没内容就删掉整行" % (len(filler), ", ".join(filler)))

    # 5. 模板示范文字未替换
    for phrase in DEMO:
        if phrase in plain:
            probs.append("模板示范文字未替换: 「%s」" % phrase)

    # 6. 目录 href ↔ id
    toc = re.search(r'id="toc">(.*?)</ol>', body, re.S)
    links = re.findall(r'href="#([^"]+)"', toc.group(1)) if toc else []
    ids = set(re.findall(r'id="([^"]+)"', body)) - {"toc"}
    dangling = [l for l in links if l not in ids]
    if dangling:
        probs.append("目录指向不存在的 id: " + ", ".join("#" + l for l in dangling))
    h2 = re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', body, re.S)
    absent = [i for i, _ in h2 if i not in links]
    if absent:
        probs.append("h2 不在目录里: " + ", ".join("#" + i for i in absent))

    # 7. 替团队做承诺
    hits = [s.strip() for s in SENT_SPLIT.split(plain) if any(k in s for k in PROMISE)]
    if hits:
        probs.append("疑似替团队承诺 %d 处（改成「待决策 + 该问谁」）: %s"
                     % (len(hits), "; ".join(s[:40] for s in hits[:4])))

    # 8. 总括话术与待补验证项矛盾
    facts = re.search(r'class="facts">(.*?)</div>', body, re.S)
    aligned = "待补验证" in text_of(facts.group(1)) if facts else False
    ok_tags = [text_of(t) for t in re.findall(r'class="tag ok">(.*?)</span>', body, re.S)]
    if not aligned and "tag todo" in body:
        overclaim = [t for t in ok_tags if "均已" in t or "全部" in t]
        if overclaim:
            probs.append("总括话术与待补验证项矛盾: .tag.ok 写着「%s」，文档里却挂着 .tag.todo；"
                         "要么改措辞，要么在首部 .facts 里写明有待补验证项" % "、".join(overclaim))

    print(path)
    if probs:
        for p in probs:
            print("  x " + p)
    else:
        print("  ok  无问题")
    print("  %d 节 / %d 表 / %d 代码块 / warn %d · todo %d · ok %d / %d 字节"
          % (len(h2), body.count("<table"), body.count("<pre>"), body.count('class="warn"'),
             body.count("tag todo"), len(ok_tags), len(html.encode("utf-8"))))
    return probs


def main(argv):
    args, tpl_path = [], Path(__file__).resolve().parent.parent / "assets" / "template.html"
    it = iter(argv)
    for a in it:
        if a == "--template":
            tpl_path = Path(next(it))
        else:
            args.append(a)
    if not args:
        print(__doc__.strip())
        return 2
    tpl = tpl_path.read_text(encoding="utf-8")
    tpl_style, tpl_script = block(tpl, "style"), block(tpl, "script")
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", tpl_style))
    bad = 0
    for path in args:
        if lint(path, tpl_style, tpl_script, defined):
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
