# 时间索引：从资产准备到 MTP 共振收口（2026-10-05 → 2026-11-17）

这是本仓库的**完整时间索引**（母本），把每一次会话/实验的关键节点按时间正序排成一张表，每条给一句结论。

- **条目数**：43 条（覆盖 `PROGRESS.md` 全部 33 个 `## ` 条目，另含 10 个源文档中的补充节点）
- **日期范围**：2026-10-05 → 2026-11-17
- **覆盖的实验线**：E0 可靠性工装 · 基础设施与工具链 · TQR-JEV 实验资产 · RWKV-7 状态探针 · prompt-based JEV · TreeJev-Mem · 神经元剪枝 / 条件计算 · MTP 多层共振
- **取数原则**：结论摘自对应源文档原文（`PROGRESS.md`、`PROMPT-JEV-PLAN.md`、`memory-jev/results/REPORT-2026-11-12-neuron-pruning.md` 等），数字保留原精度，未做美化；本页只做导航，完整设置、边界与证据见「实验线」列链接的日志。
- **排序规则**：按时间正序；同一天多条按事件先后，源文档给出时刻的标 `YYYY-MM-DD HH:MM`。
- **源文档无条目的空档**：2026-10-09 → 10-21、2026-10-23 → 11-09，索引据实留空、不做推断。
- **脱敏**：内网地址、实例连接信息、账户与凭证一律省略或泛化（实例代号保留）。

| 日期 | 事件 | 结果 / 结论 | 实验线 |
|---|---|---|---|
| 2026-10-05 | 阶段 0 起步：模型 / 数据 / 代码统一进 autodl-fs，明确不跑实验 | 14/14 模型文件与源站字节一致；fs 用量 17G/200G | [TQR](logs/03-tqr-jev-assets.html) [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-06 | 阶段 0 收尾快照：远端 GPU 本会话始终不可用 | 资产复核 17G/200G；E0/E1/E3 无法运行 | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 更正：实例是被停止，不是本机代理被劫持 | 普通容器实例不在 Pro API 内；先充值再开机 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-06 | E0 工具链交付：六特征抽取 + 可靠性 harness | ICC=0.9940、flip=0.000，G0 PASS | [E0](logs/01-e0-reliability.html) |
| 2026-10-06 | E0 改造：逐条独立打分 + 顺序一致性作主判据 | 注入 bias=0.20 时 rho 跌到 0.8582，G0 FAIL | [E0](logs/01-e0-reliability.html) |
| 2026-10-06 | Qwen3.8-Flash-Next GGUF：fs 装不下四个档位 | 20 文件 294.82G；只下完 mmproj 0.91G | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 按用户要求清理 Strata 数据（只删 Strata 产物） | 数据盘 49M→780K；fs 17G 不受影响 | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 下载 Qwen3.5-9B-Base 与 NuminaMath-CoT | 19.33G 分片字节一致；859,494 行 | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 数据增殖脚本 v3 调通（DeepSeek Flash） | 3 条 accept 100%；数学判重须用字符 3-gram | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 在 westb 的 4090 24G 上验证 Qwen3.5-9B-Base | bf16 18.8G，生成 23.6 tok/s | [INFRA](logs/02-infra-toolchain.html) [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-06 | 工作区落盘收尾：INDEX / DATA-AUGMENT-REF 入库 | augment.py 源码无法在本机落盘 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-06 | RLCD 数据选型 + 下载 rlcd-lite | 校准须 RLCR（ECE 0.08 vs 0.35） | [TQR](logs/03-tqr-jev-assets.html) |
| 2026-10-07 | 飞书云文档长期管理能力落地（官方 lark-cli 1.0.97） | 存储 / 搜索 / 读取 / 修改 / 管理均已实测 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-07 | 飞书操作经验落盘 FEISHU-NOTES | EPERM 与钥匙串报错真因是沙箱与策略 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-08 | 10-07 工作进度写入飞书（文档 + 消息） | 文档 rev 6→8；8 个补授权 scope 未完成 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-08 | 文档 × 时间线：飞书 Base 建三视图 + 11 条记录 | docx 无时间线组件，改用 gantt 视图 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-08 | 飞书写入改增量：log.sh + targets.env | 文档 append 到 rev 13；重复运行有保护 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-08 | 通用经验提升到 DSH 全局基线 | 写入后本会话立即生效，无需重启 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-10-08 | 盘点局域网工作机（GTX 1080 Ti 11G） | 5,075 tok/s；10k prompt ≈17 min，探针无需充值 | [INFRA](logs/02-infra-toolchain.html) [RWKV7](logs/04-rwkv7-state-probe.html) |
| 2026-10-22 | prompt-based JEV 首轮 pilot（Qwen3-1.7B-Base，1876 条） | Q2 探针 acc 0.916 / AUROC 0.966 | [PJEV](logs/05-prompt-jev.html) |
| 2026-10-22 | 第二轮：K=2..5 选项格式 / ensemble / noul / steering | 最优 0.921 acc / 0.970 AUROC / ECE 0.033 | [PJEV](logs/05-prompt-jev.html) |
| 2026-11-10 | TreeJev-Mem v2 设计与原型落地（autodl 实例 weste 无卡） | 两遍门 + 锐化共鸣；CPU 冒烟通过 | [TREEJEV](logs/06-treejev-mem.html) |
| 2026-11-10 | 图审 17 个问题：共鸣 v1 被数值复核为负优化 | Σa_iV_i 0.612 < q0 0.754；p=4 到 0.795 | [TREEJEV](logs/06-treejev-mem.html) |
| 2026-11-10 04:15 | 4090 首轮真实实验：E1 树 vs 平铺、E2 多步共鸣 | 树 0.887 vs 平铺 0.575；多步共鸣判伪 | [TREEJEV](logs/06-treejev-mem.html) |
| 2026-11-10 05:05 | J5 端到端：后训 labeler 出 meta 接回逐跳寻址 | content top-1 0.253→0.518（+26.5pt） | [TREEJEV](logs/06-treejev-mem.html) |
| 2026-11-10 21:19 | Lead-RRTree 分包实验（预注册 + 8 个 worker） | 90.5 vs 94.0（+3.5 <+5），判据无法区分 | [INFRA](logs/02-infra-toolchain.html) |
| 2026-11-11 | 「重排 + 逐步清空」首轮：静态只值 2% | 静态免费 ~2%，动态 20–30%，差 10× | [PRUNE](logs/07-neuron-pruning.html) |
| 2026-11-11 | R5–R8：神经簇合并判负、动态路由不可兑现 | 合并仅 +34.3%；路由端到端 +191.7% | [PRUNE](logs/07-neuron-pruning.html) |
| 2026-11-12 | 神经元剪枝可行性报告：四条路线全判负 | 静态 2–3%、组级 +18~80%、恢复买回 ~70% | [PRUNE](logs/07-neuron-pruning.html) |
| 2026-11-15 | SenseNova-Loop-9B 调研 + 后训练可行性核查 | 循环 2 遍 99.5% vs 1 遍 0.5%；4090 只能非官方 LoRA | [PRUNE](logs/07-neuron-pruning.html) |
| 2026-11-15 | Mercury 3 与「循环 × 扩散」文献调研 | API 12-28 关停且无权重；5 篇正面对撞 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-16 | Strata 能否在 1080 Ti 上跑：卡在内存不是显卡 | 最小档需 32GB RAM，本机 15GB | [INFRA](logs/02-infra-toolchain.html) |
| 2026-11-16 | MTP 多层共振 S0 探针（3 模型 5 组） | 5 组 ΔAUC≈0；共振信号全低于置信度 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 | E-1 跨视界共振：接受率有增量 | ΔAUC +0.0287；增量只在最后 1–2 层 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 | E-2 路径级共振：不显著且功效不足 | ΔAUC +0.050，CI [−0.010,+0.108] 含 0 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 | E-3 激发探针：首个统计显著正增量 | ΔAUC +0.089 [0.018,0.161]；不是多峰 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 | E-4 复现：局部化信息注入 +5~9pt | pooled +0.058 [+0.017,+0.091] | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 01:35 | E-5a token 级激发零增量；mean_ig ≡ 熵 | ΔAUC −0.0009；mean_ig 与熵相关 −1.000 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 01:50 | E-5a 已跑完但实例失联，结果留在数据盘 | 重启后可直接取回，无需重跑 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 02:35 | E-6 决定性对照：熵轨迹基线后仍显著 | pooled +0.041 [+0.008,+0.077] | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 02:37 | E-7 边界：instruct 模型上增量不显著 | +1.6pt，CI [−0.006,+0.043]；增量是条件性的 | [MTP](logs/08-mtp-resonance.html) |
| 2026-11-17 03:03 | 收工：实例已关机，结果归档到本地 | 8.4MB / 54 文件；约 3.5h ≈ ¥8–10 | [MTP](logs/08-mtp-resonance.html) [INFRA](logs/02-infra-toolchain.html) |
| 2026-11-17 09:05 | PEAR 机器人 agentic RL：要什么卡、什么模型 | 训练 256×H100；4090-48G 跑不了 | [INFRA](logs/02-infra-toolchain.html) |
