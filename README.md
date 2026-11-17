# MadAIKid · 实验日志

一条条真实跑过的实验，整理成可追溯的日志：**问题 → 设置 → 结果 → 判定 → 边界**。

- **在线阅读**：<https://madaikid.github.io/MadAIKid_logs/>
- **本页用途**：这就是**操作手册**。以后不管你在哪个项目里、换哪个会话，只读这个 GitHub 主页
  就能继续添加与维护，不必打开渲染站点，也不必翻别的文档。

不是论文、不是计划书、不是宣传。判断标准只有一条：**每个数字都能追溯到一个真实跑过的实验，
每个结论都明确标出「可写 / 不可写」的边界。** 负结果和正结果同等重要——这个仓库里被判死的假设，
比做成的实验更多，也更值钱。

## 目录

- [1. 仓库结构](#1-仓库结构)
- [2. 看什么](#2-看什么)
- [3. 添加一篇日志（5 步）](#3-添加一篇日志5-步)
- [4. 维护与发布](#4-维护与发布)
- [5. 写作约定（浓缩版）](#5-写作约定浓缩版)
- [6. 常见问题](#6-常见问题)
- [7. 已有实验线](#7-已有实验线)

---

## 1. 仓库结构

```
MadAIKid_logs/
├── README.md            ← 本操作手册
├── WRITING-RULES.md     ← 完整写作契约（frontmatter 字段表 / 七节骨架 / 脱敏规则 / 自查清单）
├── posts/               ← ★ 日志母本（Markdown，唯一需要手写的目录）
│   ├── _TEMPLATE.md     ← 复制这个开始写（下划线开头 = 不会被构建）
│   ├── 01-e0-reliability.md
│   └── … 08-mtp-resonance.md
├── timeline.md          ← ★ 时间索引母本（43 条，一行一个节点）
├── build.py             ← 构建器：frontmatter 校验 + pandoc 渲染 + 断链校验
├── assets/style.css     ← 全站样式（只有一个文件，改这里就够）
├── index.html           ← 构建产物：首页（时间序卡片 + 标签筛选）
├── timeline.html        ← 构建产物：时间索引页
├── logs/NN-slug.html    ← 构建产物：每篇日志一个页面
└── .nojekyll            ← 让 GitHub Pages 不套 Jekyll
```

**手写**：`posts/*.md`、`timeline.md`、`assets/style.css`。
**生成**（不要手改）：`index.html`、`timeline.html`、`logs/*.html`。

## 2. 看什么

| 入口 | 内容 |
|---|---|
| <https://madaikid.github.io/MadAIKid_logs/> | 首页：全部日志按时间排序，可按标签筛选 |
| `timeline.html` | **完整时间索引**：按时间正序列出每个节点与结论 |
| `posts/` | 日志源文件（GitHub 上可直接读，不依赖渲染） |
| `timeline.md` | 时间索引母本 |

本地预览（不需要任何构建工具）：

```bash
cd MadAIKid_logs && python3 -m http.server 8000   # 打开 http://127.0.0.1:8000
```

## 3. 添加一篇日志（5 步）

约定：文件名 `NN-slug.md`，`NN` 为两位数序号（接在现有最大号之后），**frontmatter 里的 `slug` 必须与文件名（去掉 `.md`）完全一致**。

### ① 拿到仓库

```bash
# 本地母本（推荐：和源实验仓库放一起）
cd ~/projects/ai/autodl/blog

# 或：任何目录下重新克隆
git clone git@github.com:MadAIKid/MadAIKid_logs.git && cd MadAIKid_logs
```

### ② 从模板复制

```bash
cp posts/_TEMPLATE.md posts/09-my-experiment.md
```

### ③ 填 frontmatter 与七节正文

- frontmatter 全部字段见模板注释；只要求**不编数字、CI 照抄、负结果如实写**。
- 正文七节顺序固定：`0 摘要` · `1 问题与假设` · `2 实验设置` · `3 结果` · `4 结论与判定` ·
  `5 踩坑与修正` · `6 未做 / 下一步` · `7 证据与产物`。
- `status` 只能取：`完成` / `部分完成` / `判负` / `中止` / `进行中`。

### ④ 在时间索引里加一行

编辑 `timeline.md`，按日期正序插入（列顺序固定，单元格内不要出现 `|`）：

```markdown
| 2026-11-17 | 一句话事件 | 一句真实结论（带数字） | [MTP](logs/08-mtp-resonance.html) |
```

实验线列写成 `[短名](logs/NN-slug.html)`，同一行可以挂多个链接。

### ⑤ 构建、验、推

```bash
python3 build.py      # 校验 frontmatter + 渲染 + 0 断链检查
git add -A && git commit -m "add 09 my-experiment" && git push
```

推送后 GitHub Pages 通常 1 分钟内自动重建，站点会同步出现新日志与新索引行。

## 4. 维护与发布

### 常用命令

```bash
cd ~/projects/ai/autodl/blog     # 或任意 clone 目录

python3 build.py --check          # 只校验：frontmatter 字段、status 取值、slug 唯一、0 断链
python3 build.py                  # 构建：index.html / timeline.html / logs/*.html
python3 -m http.server 8000       # 本地预览 http://127.0.0.1:8000
```

构建器会自己做的检查（失败会非零退出并逐条列出）：

- frontmatter 必填字段缺失、`status` 非法、`date_start` 格式不对、`slug` 与文件名不一致或重复；
- 页面内部链接断链（时间索引指向不存在的日志、导航指向不存在的页面）。

### 发布

```bash
git add -A
git commit -m "add 09 my-experiment"      # 或 "fix: …" / "style: …"
git push            # main 分支，GitHub Pages 从 main 根目录发布
```

- 站点地址：<https://madaikid.github.io/MadAIKid_logs/>
- Pages 设置：仓库 **Settings → Pages**，Source = `Deploy from a branch`，分支 `main` / 目录 `/`。
- 想关掉站点：同一处把 Source 设为 `None`（仓库内容与历史不受影响）。

### 加图 / 改样式

- 图片放 `assets/`，正文里写 `![说明](../assets/x.png)`（页面在 `logs/` 子目录，所以是 `../assets/`）。
- 配色、字号、表格、时间轴样式全在 `assets/style.css`，文件顶部是一组 CSS 变量（含深色模式），改变量即可。

### 定期体检

```bash
# 1) 脱敏扫描：应当无输出
grep -rnE '192\.168\.|10\.[0-9]+\.[0-9]+\.[0-9]+|seetacloud|feishu\.cn|/Users/[a-z]+|id_rsa|oc_[a-z0-9]{6}|cli_[a-z0-9]{6}' posts/ timeline.md

# 2) 构建 + 断链
python3 build.py
```

时间索引覆盖率：实验源仓库（`~/projects/ai/autodl/`）里 `grep -c '^## ' PROGRESS.md` 的条目数，
应当等于 `timeline.md` 里 `grep -c '^| 2026'` 的行数（允许一行覆盖多个条目，只多不少）。

## 5. 写作约定（浓缩版）

完整规范见 [`WRITING-RULES.md`](WRITING-RULES.md)，这里只放必须记住的：

1. **不许编数字。** 找不到精确值就写「未记录」，不要估。
2. **保留置信区间与阈值。** 原文说「不显著」就不要写成「有趋势」；判负要写清判死依据。
3. **每个结论标边界。** 写成「可写（支持的结论）」与「不可写（诚实边界）」两栏。
4. **一段话能说清就别写三段。** 单篇 150–320 行；表格优先，别写成散文。
5. **不做「我」叙事。** 用「本实验 / 本轮」；不写子代理、任务分配之类的过程元信息。
6. **公开仓库，必须脱敏**：

| 类型 | 写法 |
|---|---|
| 内网 / 公网 IP | 不出现具体地址，写「局域网工作机（IP 已隐去）」 |
| 实例域名 + 端口 | 「autodl 实例 westc（域名/端口已隐去）」；代号 `westb/westc/weste` 可留 |
| 账户余额 | 「账户资金紧张（< ¥20）」或直接省略；**实验实际花费可以写** |
| token / app id / 会话 id | 一律不写 |
| 本地用户名 / 私钥路径 | 省略或写 `~/...` |
| 项目内路径（`/root/autodl-tmp/`、`/data/projects/ai/`） | 可以保留 |

## 6. 常见问题

| 现象 | 原因 / 解法 |
|---|---|
| `错误：找不到 pandoc` | `brew install pandoc`（仅构建需要；只看 Markdown 不需要） |
| 构建报「缺 frontmatter 字段 / status 不在……」 | 按报错行补字段；`status` 只能取 5 个合法值 |
| 构建报「断链 …」 | `timeline.md` 里的链接写错 slug，或日志文件名改了但链接没跟着改 |
| 时间索引页少了新行 | 新行不在 `timeline.md` 表格里，或日期格式不是 `YYYY-MM-DD` |
| 推送后线上没变化 | 等 1 分钟；仍无变化看 **Settings → Pages** 的最近一次部署 |
| 页面公式显示成源码 | 公式要用 `$...$` / `$$...$$`（构建输出 MathML，不需要 JS） |
| 想加新标签 | 直接在 `tags: [...]` 里写，首页标签栏会自动出现 |
| 只想改样式 | 改 `assets/style.css` → `git push`（所有页面引用同一份 CSS，无需重建） |

## 7. 已有实验线

| # | 日志 | 时间 | 判定 |
|---|---|---|---|
| 01 | [E0 可靠性工装](posts/01-e0-reliability.md) | 2026-10-05 → 10-06 | 完成 · ICC=0.9940 / rho=0.9830，G0 PASS |
| 02 | [运维与工具链](posts/02-infra-toolchain.md) | 2026-10-05 → 11-17 | 部分完成 · Strata 判负（26 GiB < 27.6 GB） |
| 03 | [TQR-JEV 资产准备](posts/03-tqr-jev-assets.md) | 2026-10-05 → 10-06 | 部分完成 · 9B 18.8 GB / 23.6 tok/s，1k 未跑 |
| 04 | [RWKV-7 状态探针](posts/04-rwkv7-state-probe.md) | 2026-10-07 → 10-08 | 部分完成 · 六臂自检 R0 0.939 / R3 0.912，S2 未跑 |
| 05 | [prompt-based JEV](posts/05-prompt-jev.md) | 2026-10-22 | 部分完成 · 严格 gap +9.4pt，单方向被证伪 |
| 06 | [TreeJev-Mem](posts/06-treejev-mem.md) | 2026-11-10 → 11-12 | 部分完成 · 多步共鸣判伪，树 ≥3.4k 时 +7.5pt |
| 07 | [神经元级剪枝](posts/07-neuron-pruning.md) | 2026-11-11 → 11-12 | **判负** · 静态 2–3%，动态 oracle 40% 不可兑现 |
| 08 | [MTP 多层共振](posts/08-mtp-resonance.md) | 2026-11-16 → 11-17 | 部分完成 · S0/E-2/E-5a 零，E-6 +0.041 [+0.008,+0.077] |

---

源经验仍在实验仓库（`~/projects/ai/autodl/PROGRESS.md` 等）里：**每做一个实验，先补源文档，
再往这里加一篇日志与一行索引**。本仓库只做索引与结论文本，不存模型、数据与代码。
