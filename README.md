# ONE SHOT 一镜

**一句提示词 一镜到底**

Claude Opus 5.5 用例大全。把 GitHub 上 12 个 Opus 5.5 合集仓库合并去重，每部作品附原帖、视频和能找到的提示词。

- 在线看：**https://one-shot-peach.vercel.app** 可按分类筛选、搜索、看视频、复制提示词
- 本地看：打开 [`web/index.html`](web/index.html)
- 关注我们：[@sciencedegens](https://x.com/sciencedegens)

整理日期 2026-09-28，源仓库数据截至 2026-09-27。

## 总数

- **人工整理过的用例 1022 条**：至少被一个仓库人工收录。按 X 帖子 ID 去重，同一条帖子在几个仓库出现只算一次。
  - 其中 379 条被两个及以上仓库同时收录
  - 542 条带提示词，其中 453 条是原文（其余是摘要、摘录或实现指南）
- **待核实候选 728 条**：只出现在 athemeroy 的分类器语料里，没人细看过，单独放在 [待核实候选](cases/08-待核实候选.md)。
- **开源仓库 262 个**：作品源码、skill、工具，见 [开源工具与仓库](cases/09-开源工具与仓库.md)。

## 分类

| 分类 | 条数 | 文件 |
|---|---:|---|
| 视频与动画 | 782 | [cases/01-视频与动画.md](cases/01-视频与动画.md) |
| 游戏 | 104 | [cases/02-游戏.md](cases/02-游戏.md) |
| 3D 场景与交互 | 74 | [cases/03-3D场景与交互.md](cases/03-3D场景与交互.md) |
| 网页、UI 与 SVG | 17 | [cases/04-网页UI与SVG.md](cases/04-网页UI与SVG.md) |
| Agent 与编程 | 9 | [cases/05-Agent与编程.md](cases/05-Agent与编程.md) |
| 评测与模型对比 | 26 | [cases/06-评测与模型对比.md](cases/06-评测与模型对比.md) |
| 官方、合集与资源 | 10 | [cases/07-官方合集与资源.md](cases/07-官方合集与资源.md) |
| 待核实候选 | 728 | [cases/08-待核实候选.md](cases/08-待核实候选.md) |
| 开源工具与仓库 | 262 | [cases/09-开源工具与仓库.md](cases/09-开源工具与仓库.md) |

视频与动画的子类：产品发布与广告 165 · 动效与作品集 180 · 知识讲解 85 · 叙事与角色动画 117 · 音乐视频 40 · 历史与纪录 21 · 素材改编与剪辑 34 · AI 自我叙事 38 · 其他 102

## 来源仓库

“贡献”是这个仓库收录、且进了人工整理表的条数；“独有”是只有它收了的条数。

| 仓库 | 内容 | 贡献 | 独有 |
|---|---|---:|---:|
| [athemeroy/awesome-opus-5-5-videos](https://github.com/athemeroy/awesome-opus-5-5-videos) | 研究档案：1,401 个视频语料 + 168 条人工深读 | 191 | 86 |
| [opusvideo/awesome-claude-video](https://github.com/opusvideo/awesome-claude-video) | 53 条高浏览量精选 + 实现指南 | 53 | 7 |
| [zhuyansen/awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) | 180 个做视频的 skill/工具（非作品合集） | — | — |
| [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) | 作者自制 39 种风格样片 + 风格提示词 | 39 | 39 |
| [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) | 282 条热门视频，带提示词 | 282 | 83 |
| [Li-Evan/awesome-opus-5.5-video-prompts](https://github.com/Li-Evan/awesome-opus-5.5-video-prompts) | 334 条逐字提示词 | 334 | 102 |
| [theolundqvist/frontier-games](https://github.com/theolundqvist/frontier-games) | Opus 5.5 / GPT-6 Astra 游戏和影片（本表只取 Opus） | 108 | 49 |
| [coolbat/awesome-opus-5.5-usecase](https://github.com/coolbat/awesome-opus-5.5-usecase) | 游戏、3D、影片、agent 综合用例 | 335 | 183 |
| [krillinai/awesome-opus-animation](https://github.com/krillinai/awesome-opus-animation) | 动画、3D 场景和可玩项目 | 114 | 34 |
| [OpenVGLab/awesome-opus5.5-frontend-showcases](https://github.com/OpenVGLab/awesome-opus5.5-frontend-showcases) | 前端作品：SVG、Lottie、Three.js、鹈鹕测试 | 68 | 49 |
| [joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts) | 54 个案例的中文提示词 | 54 | 11 |
| [riba2534/claude-opus-5-5-demo](https://github.com/riba2534/claude-opus-5-5-demo) | 作者自制演示项目（无帖子链接，列入工具与仓库） | — | — |

## 怎么合并的

- **去重**：X 帖子统一成 `https://x.com/作者/status/ID`，按 ID 合并；不是 X 帖子的（GitHub、B 站、网站）按链接合并。
- **分类**：每个仓库原有的分类映射到统一分类后投票，票数相同时按 游戏 > 3D 场景 > 网页 > Agent > 评测 > 视频 的顺序定。athemeroy 分类器的票权重较低。
- **提示词**：同一条有多个来源时，优先取逐字原文（Li-Evan > yihui-dev > joeseesun > OpenVGLab），其次是 opusvideo 实现指南、krillinai 摘录、athemeroy 摘要。
- **日期**：X 帖子的日期从帖子 ID 里直接算出（UTC）。
- **互动数**：取各仓库记录里最大的一个。各仓库抓取时间不同（9 月 25–27 日），只能大致参考。
- **只收 Opus 5.5**：frontier-games 里 GPT-6 Astra 的作品没收；athemeroy 语料里分类器判为“与 Opus 无关”的 282 个没收。

## 已知缺口

- 源仓库都只更新到 9 月 26–27 日，之后的新帖没有。
- 模型是否真是 Opus 5.5 基本靠作者自述，没有逐条复核。
- 视频和游戏收得多；Agent、编程、长任务这类用例几乎没人整理，这里也很少。
- 标题、简介保留源仓库原文，部分只有英文。

## 文件

- `cases/*.md`：按分类阅读
- `data/cases.csv`：全部条目（含待核实），Excel 可直接打开
- `data/cases.json`：完整数据，含全部提示词
- `scripts/build.py`：合并脚本。`python3 scripts/build.py --fetch` 会拉取源仓库最新版本再重新生成
- `sources/`：12 个源仓库的本地克隆
