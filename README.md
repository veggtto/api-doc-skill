# api-doc — 接口文档生成技能

一个 Agent Skill：把跑通的接口变成一份**自包含 HTML 对接文档**，调用方双击就能看、能直接转发、能打印成 PDF。

跨项目通用，也不绑定某一个宿主——标准 `SKILL.md` 格式，Claude Code、Claude 桌面/网页版、Agent SDK 吃的是同一份目录，正文里没有任何宿主专有的 API。

> **In English** — An Agent Skill that turns a working HTTP API into a self-contained HTML handoff document: one file, no build step, no external assets. Open it by double-clicking, forward it as-is, print it to PDF.
>
> The skill is written in Chinese and produces Chinese documents. What carries over regardless of language is the method it encodes: only write the doc *after* the endpoint has actually been exercised, quote real request/response payloads instead of what the code appears to intend, mark anything unverified rather than quietly implying it was tested, and lay the page out like a reference manual (ruled headings, bordered tables, boxed code) rather than a reading page.
>
> Install: `claude plugin marketplace add veggtto/api-doc-skill`, then `claude plugin install api-doc@veggtto-skills`. Start a new session to pick it up. MIT licensed.

## 安装

任意 shell 里两条命令：

```bash
claude plugin marketplace add veggtto/api-doc-skill
```

```bash
claude plugin install api-doc@veggtto-skills
```

之后 `claude plugin marketplace update veggtto-skills` 拿更新。

Claude Code **终端**里也可以用交互式的 `/plugin marketplace add …` / `/plugin install …`。注意桌面 App 的 Code 标签页**不支持 `/plugin`**（它是终端专属的交互面板命令），在那儿请用上面的 `claude plugin …` 形式。

装完**新开一个会话**才生效。之后直接描述「给这个接口写份对接文档」，让它按 frontmatter 的 `description` 自己命中；也可以显式调用 `/api-doc:api-doc`。

**不用插件机制的话**，`skills/api-doc/` 这个目录本身就是一份完整的标准技能，拷到宿主的技能目录即可（Claude Code 是 `~/.claude/skills/api-doc`），内容一个字不用改。Claude 桌面/网页版打包上传这个目录，Agent SDK 放进它自己的 skills 目录。

## 仓库结构

仓库同时是插件市场和插件本体（`source: "./"`）。

```
api-doc-skill/
├── .claude-plugin/
│   ├── marketplace.json    # 市场清单，让 /plugin marketplace add 认得
│   └── plugin.json         # 插件清单
├── skills/
│   └── api-doc/            # 技能本体，可整个拷走单独使用
│       ├── SKILL.md        # 什么时候写、写什么、什么不能写
│       ├── assets/
│       │   └── template.html   # 自包含 HTML 模板（含占位符）
│       └── scripts/
│           └── lint_output.py  # 产出自检，交付前对生成的文档跑一次
├── examples/
│   ├── keyboard-tree.html  # 样例一：单端点、两端对照（已脱敏）
│   └── webhooks.html       # 样例二：非 CRUD 形状（事件回调），结构随内容变
└── scripts/
    └── check.py            # 模板自检，改完跑一次
```

## 技能解决什么问题

写接口文档最容易出两类错，SKILL.md 针对的就是这两类：

**内容上**——写成"是什么"的字段清单，没有"你会怎么踩坑、为什么这么设计"。真正有用的密度在注意事项里：为什么没有分页、为什么传错 id 返回 400 而不是空列表、两个接口对同一种数据口径为什么不同且是有意的。

**画法上**——按"阅读页"画而不是按"参考手册"画。前端读文档是扫读、跳读、对齐着看，手册的画法是标题有线、表格有格、代码是框、粗体标句眼，全页重量均匀；靠留白和灰度分层在这个场景下天然吃亏，文档越小越吃亏。

## 模板已经内置的东西

- `body` 即居中列（980px），标题 / 目录 / 正文全在列里
- 目录只维护一份，JS 克隆成宽屏常驻侧栏；窄屏用正文里的目录盒 + 回顶按钮；打印时反过来
- 滚动高亮用「最后一个越过顶部基准线」判断，带页面到底和无 scroll 事件两种兜底
- 章节编号用 CSS 计数器自动生成，插删章节不用回头改序号
- 方法徽标按 method 分色（GET / POST / PUT / PATCH / DELETE），无修饰类时中性灰兜底
- 轻量 JSON 语法着色，不引第三方库，打印退回单色
- 代码块复制按钮，带 `execCommand` 回退（`file://` 打开时 `navigator.clipboard` 不可用）
- 一套浅色主题，不跟随系统深浅色——文件会被转发、被打印，所有人该看到同一份

## 维护约定

改完跑一次自检——下面这些腐化肉眼都看不出来，而且**静默失效，没有任何报错**：

```bash
python scripts/check.py
```

它查：模板和样例的 body 有没有用样式表里不存在的 class；模板的 `<style>`/`<script>` 有没有和 `examples/` 走样；SKILL.md 有没有在推荐已经删掉的 class、CSS 变量或元素选择器；目录 `href` 和 `h2` 的 `id` 是否一一对应；`examples/` 里有没有残留 `{{占位符}}`。这些都真实发生过——有一轮模板的样式换成了新做法，body 骨架却还停在上一代，引用了 9 个已不存在的 class。

其余约定：

- **SKILL.md 里的每条规则都应该是踩过的坑**，不要写泛泛的最佳实践。加规则时把「为什么」一起写上，否则下次会被当成可有可无的建议绕过去。
- **加规则前先用假接口跑一轮**。硬规则 6、7（不替团队做承诺、共享环境里只动自己建的数据）就是这么来的——拿三个不同形状的假接口做了一次评估，才看到模型会替后端许承诺、会按猜出来的 id 删掉别人的数据。凭空想的规则不如跑出来的规则。
- **规则的篇幅要配得上它的重要性**。单节超过 30 行就该压缩；整个文件超过 200 行会稀释注意力，模型容易略过中段。
- **改动优先落在模板，不是 SKILL.md**。能用 CSS/骨架固化的就别写成文字规则——写成规则要靠模型每次记得遵守，做进模板则是默认行为。
- **`description` 是唯一影响命中率的字段**。该用没用上、或不该用却用上了，改 frontmatter 的 `description`，别改正文。
- **响应式必须测 1366 和 1440**，别只测 1600/2400。很多布局 bug 只在「窄于侧栏断点、宽于手机」这一段出现。
- **发版记得 bump `.claude-plugin/plugin.json` 的 `version`**。版本号不变，已安装的用户拿不到更新。

## 由来

从一个实际项目的接口文档反复迭代出来的。过程里最有价值的两次修正都不是凭空想出来的：一次是拿另一份公认更好的文档逐项对比，一次是把两份文档交给另一个模型做设计评审。SKILL.md 里那些看起来很具体的条款，基本都对应一次返工。

## License

MIT — 见 [LICENSE](LICENSE)。
