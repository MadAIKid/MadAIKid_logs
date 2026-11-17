# MadAIKid · 实验日志

一条条真实跑过的实验，整理成可追溯的日志：**问题 → 设置 → 结果 → 判定 → 边界**。

不是论文、不是计划书、不是宣传。判断标准只有一条：**每个数字都能追溯到一个真实跑过的实验，
每个结论都明确标出「可写 / 不可写」的边界。** 负结果和正结果同等重要——这个仓库里被判死的假设，
比做成的实验更多，也更值钱。

## 怎么看

| 入口 | 内容 |
|---|---|
| [`index.html`](index.html) | 全部日志，按时间排序，可按标签筛选 |
| [`timeline.html`](timeline.html) | **完整时间索引**：按时间正序列出每一次会话/实验的节点与结论 |
| [`posts/`](posts/) | 日志源文件（Markdown，GitHub 上可直接读） |
| [`timeline.md`](timeline.md) | 时间索引母本 |

本地预览（不需要任何构建工具）：

```bash
cd blog && python3 -m http.server 8000   # 打开 http://127.0.0.1:8000
```

## 实验线

| # | 日志 | 时间 | 一句话 |
|---|---|---|---|
| 01 | [E0 可靠性工装](posts/01-e0-reliability.md) | 2026-10-05 → 10-06 | 先证明「打分器」可信：ICC=0.9940，但阴性对照推翻了原判据 |
| 02 | [运维与工具链](posts/02-infra-toolchain.md) | 2026-10-05 → 11-17 | 实例/局域网机/文档工具链的真实踩坑与硬件判定 |
| 03 | [TQR-JEV 资产准备](posts/03-tqr-jev-assets.md) | 2026-10-05 → 10-06 | 模型能跑、增殖能出样本，但 1k 与三原语头没做 |
| 04 | [RWKV-7 状态探针](posts/04-rwkv7-state-probe.md) | 2026-10-07 → 10-08 | 先砍掉原案的三处公式错误，再把读路径写成可测的六臂 |
| 05 | [prompt-based JEV](posts/05-prompt-jev.md) | 2026-10-22 | 冻结 LM 的答案位置读数：严格 readout gap 成立，单方向格式不变不成立 |
| 06 | [TreeJev-Mem](posts/06-treejev-mem.md) | 2026-11-10 → 11-12 | 树状记忆 × 潜向量共鸣；图审抓出「共鸣是负优化」 |
| 07 | [神经元级剪枝](posts/07-neuron-pruning.md) | 2026-11-11 → 11-12 | 静态只值 2–3%，动态可达 20–40% 但不可兑现 |
| 08 | [MTP 多层共振](posts/08-mtp-resonance.md) | 2026-11-16 → 11-17 | 从「多层投票」被实验逼成「局部化信息注入剖面」 |

## 一篇日志长什么样

```markdown
---
id: E0                          # 编号
slug: 01-e0-reliability         # = 文件名
title: …                        # 标题
date_start: 2026-10-05
date_end: 2026-10-06
status: 完成                    # 完成 / 部分完成 / 判负 / 中止 / 进行中
verdict: ICC=0.9940，G0 PASS    # 一句话判定，带数字
tags: [评测方法, 校准]
hardware: 本地 Mac（零 GPU）
models: —
datasets: —
source_docs: [E0.md, PROGRESS.md]
---
```

正文固定七节：`0 摘要` · `1 问题与假设` · `2 实验设置` · `3 结果` · `4 结论与判定` ·
`5 踩坑与修正` · `6 未做 / 下一步` · `7 证据与产物`。模板与写作规范见
[`WRITING-RULES.md`](WRITING-RULES.md)。

## 构建

只用标准库 + `pandoc`（Markdown → HTML，数学公式输出 MathML，**页面零 JS 依赖**，无外链字体/CDN）：

```bash
python3 build.py            # 生成 index.html / timeline.html / logs/*.html
python3 build.py --check    # 只校验 frontmatter 与字段，不写文件
```

## 新增一篇

1. 在 `posts/` 下新建 `NN-slug.md`，按 `WRITING-RULES.md` 填 frontmatter 与七节正文；
2. 在 `timeline.md` 表格里补对应时间节点；
3. `python3 build.py`，检查 `index.html`；
4. 提交。

## 脱敏约定

本仓库公开，源材料中的**内网/公网 IP、实例域名与端口、账户余额、各类 token**一律按
`WRITING-RULES.md` §5 处理（打码或省略），实验结论与规格不受影响。
