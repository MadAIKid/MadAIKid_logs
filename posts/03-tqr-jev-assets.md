---
id: TQR
slug: 03-tqr-jev-assets
title: TQR-JEV 资产准备：模型能跑、增殖能出样本，但 1k 与三原语头没做
subtitle: 阶段 0 · 9B 在 4090 上 18.8 GB / 23.6 tok/s · 增殖 v3 小样 accept 100%
date_start: 2026-10-05
date_end: 2026-10-06
status: 部分完成
verdict: 资产就绪（9B 19.33 GB / Numina 859,494 行），v3 仅 3 条样本，1k 与 JEV 头未做
tags: [模型下载, 数据构建, 校准, 运维]
hardware: AutoDL RTX 4090 24 GB（westb 验证机）· AutoDL 无卡实例 westc（下载机）· 本地 Mac（零 GPU）
models: Qwen3.5-9B-Base 19.33 GB · Qwen3-8B 16 GB
datasets: NuminaMath-CoT 859,494 行 / 1.23 GB · PRM800K 488 MB · rlcd-lite 自带 BoolQ/MMLU/Banking77/CLINC150
source_docs: [PROGRESS.md, DATA-AUGMENT-REF.md, GPU-VALIDATION.md, RLCD-DATASETS.md, EXPERIMENT_PLAN.md, COLD-START.md, PROGRESS-SUMMARY.md, INDEX.md, SESSION-2026-10-06.md]
---

# TQR-JEV 资产准备：模型能跑、增殖能出样本，但 1k 与三原语头没做

> **一句话**：TQR-JEV 要不要继续花 GPU 钱，取决于冻结 9B 能不能跑、数学数据能不能增殖成带标签的节点样本 —— 本轮把模型（19.33 GB）、数据（859,494 行）、代码落进跨实例共享存储，9B 在 4090 上实测 18.8 GB 显存 / 23.6 tok/s，增殖脚本修到 v3 后 3 条样本 accept 100%；但 1k 放量、JEV 三原语头、RR-tree 全部未做。

## 0. 摘要

本轮是 TQR 宏观注意力实验的**阶段 0：资产准备**，不做训练、不跑打分。做完的四件事：模型/数据/代码进 `autodl-fs`（跨实例复用，17 G / 200 G）；把 DeepSeek Flash 增殖脚本从 v1 修到 v3（三轮修正，均有实测证据）；在 RTX 4090 24 GB 上验证 Qwen3.5-9B-Base 能加载能生成；核验 RLCD 校准头的数据集选型。

结论是「资产就绪、模型可跑、增殖脚本小样可用」，但**证据强度只够支撑下一步动工，不够支撑任何效果结论**：增殖只验了 3 条，1k 未跑；JEV 三原语头、RR-tree 生成、E1 LLM-judge 全部未实现。账户资金是硬约束（紧张），放量前必须先对账。

| 实验 | 问题 | 结果 | 判定 |
|---|---|---|---|
| TQR-A0a | 模型/数据/代码能否一次落盘、跨机复用？ | 模型/数据/代码进 fs，用量 17 G / 200 G；Qwen3-8B 14 文件 16 G | ✅ |
| TQR-A0b | 9B 权重与 1k 级数据能否下载并真校验？ | 9B 19.33 GB（4 分片 Content-Length 全对）；Numina 1.23 GB / 859,494 行 | ✅ |
| TQR-A0c | 9B-Base 能否在 24 GB 卡上加载并生成？ | 显存 18.8 GB（峰值 18.9）、加载约 2 分钟、23.6 tok/s | ✅ |
| TQR-A0d | 增殖脚本能否稳定产出 B/C 变体？ | 3 条 → baseline/perturb/branch 各 3、failed 0、accept 100% | ✅（n=3） |
| TQR-A0e | 校准头需要什么数据、公开数据够不够？ | 步骤级真软标签存在（426,449 行、33.5% 非二值）；硬 0/1 也已够 | ✅ |
| TQR-A0f | 1k 增殖 / JEV 头 / RR-tree | 未跑 / 未实现 / 未生成 | ❌ |

## 1. 问题与假设

这条线要回答的**决策问题**不是「TQR 分数怎么算」，而是：**值不值得为 TQR-JEV 继续租 GPU 做可学习的校准读数头？** 该问题被拆成 S0–S6 与 G0–G5 六道 Gate，主 go/no-go 是 E3（同预算下 TQR 引导搜索是否打赢随机重排序）。阶段 0 只负责把「能开工」这件事证明掉 —— 如果 9B 在 24G 卡上跑不动、或者数学 CoT 增殖不出带标签的节点样本，后面所有 Gate 都是空谈。

预注册式判据（本轮自定，只针对资产层）：

- **A0-1 可复用**：资产放在跨实例共享存储，另一台机器开机即可读；脚本不得硬编码挂载路径。
- **A0-2 可加载**：9B-Base bf16 在 24 GB 卡上显存占用 < 24 GB 且能生成，不依赖量化。
- **A0-3 可增殖**：LLM 增殖产出的 perturb 必须是真错误步（不是等价改写）、错误步落在中间位置、分支候选带标签，小样本 accept 率 100%。
- **A0-4 判据校准**：下载校验以实际字节为准；RLCD 数据选型必须带行数/字段/体积的实时核验，不留「听说有」的条目。

为什么先做资产而不是先做方法：JEV 本身没有官方论文与权重，分支掩码与读出结构是逆向推断；TQR 公式在真相源里仍是占位符（`_alpha/_beta_r/_beta_n/_delta` 直接 `return 1.0/0.0`）。在这种前提下，先证明「模型能跑 + 数据能造 + 参考实现能拿」是唯一不浪费 GPU 钱的顺序。

## 2. 实验设置

### 2.1 环境

本轮跨三台机器，能力各不相同：

| 机器 | 角色 | 关键事实 |
|---|---|---|
| 本地 Mac | 文档与零算力工具 | 单次命令约 200–300 字符上限，`printf`/长 heredoc 易卡死 300s；`/tmp` 与 `~/.cache` 会被重置；后台进程活不过一次工具调用 |
| AutoDL westc（无卡模式） | 下载机 | `/dev/nvidia*` 不存在、`nvidia-smi` 无输出 → 只能下载/装包；`uv` 未装；非登录 shell 无 `python3`（miniconda 在 `/root/miniconda3`） |
| AutoDL westb（RTX 4090 24 GB） | GPU 验证机 | 系统盘 30 G、数据盘 `/root/autodl-tmp` 50 G；镜像自带 torch 2.8.0+cu128，无 transformers/accelerate |

初始候选其实是「48G vGPU」（实测 FP32 82.58 / FP16-T 165.2 TFLOPS，与 RTX 4090 官方数字吻合，属 AD102 级而非 A100），但真正跑 GPU 验证的是 westb 的 **RTX 4090 24 GB**。候选 48G 与实测 24G 的差异原因**未记录**（存疑），本轮只按实测机报数。

环境搭建实测：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple transformers accelerate safetensors`，装上 **transformers 5.18.0 + accelerate 1.15.0 + tokenizers 0.23.2**；transformers 5.18.0 原生支持 `qwen3_5` 架构，无需 `trust_remote_code`。

### 2.2 模型与数据

| 资产 | 位置 | 规模 | 校验方式与结果 |
|---|---|---|---|
| Qwen3.5-9B-Base | `autodl-fs/models/Qwen3.5-9B-Base/` | **19.33 GB**，4 分片 + tokenizer + 视觉预处理器 | 4 个分片逐个与 mirror `Content-Length` 一致；单分片字节数未记录 |
| Qwen3-8B（备用骨干） | `autodl-fs/models/Qwen3-8B/` | 16 GB，14 个文件 | `14/14` 文件与 mirror `Content-Length` 逐项一致 |
| NuminaMath-CoT | `autodl-fs/datasets/numina-cot/` | **1.23 GB**，train 5 分片，**859,494 行**（官方 ~860k） | 5 个分片解析后合计行数对齐官方量级；列 `source / problem / solution / messages`，`solution` 为分步 CoT（空行分段） |
| PRM800K（原始） | `autodl-fs/datasets/prm800k-raw/` | 488 MB | `6/6` 文件 md5 与本地 LFS 源逐项一致（`b855388b…`/`cf130db1…`/`16af793c…`/`7bf0558d…`/`d06a3ab6…`/`ad0c5428…`） |
| Stellan 代码副本 | `autodl-fs/code/Stellan/` | 2.2 MB，3 个模块 | `EXPERIMENT_PLAN.md` md5 = `8437b58b9b7961d7b968652baad5c72e`，与本地一致 |
| Qwen3.8-Flash-Next（仅 mmproj） | `autodl-fs/models/Qwen3.8-Flash-Next-GGUF/` | 907,543,008 B | 单文件下载完成；主权重档位未下载（用户中止） |
| rlcd-lite（参考实现） | `autodl-fs/code/rlcd-lite/` | 1.9 MB / 29 个 `.py` | commit `b0f981fab5e6ce53dd089eae71b141ab1099c31a`（2026-09-18），`git status` 干净（`--depth 1`） |

**下载与校验的真实口径**（这是本轮最有复用价值的部分）：

1. **以 mirror 实际 `Content-Length` 校验，不信 HF API 的 `size` 字段**：同一分片 API 报 `3960337888`，mirror 实际 `3959604768`，差 733 KB；API 元数据会过期。
2. **`hf download` 必须加 `HF_HUB_DISABLE_XET=1`**，否则 xet 后端直接崩（`TypeError: process() takes no keyword arguments`）。
3. hf-mirror 的限速是**按字节段**而非按文件：同一文件 `Range: 0-20000000` → 31 KB/s，`Range: 500000000-520000000` → 3.9 MB/s；用 `curl -C -` 越过慢段后续到 3.1 GB 时实测 8.6 MB/s（`898MB→3102MB/250s`）。
4. 部分 repo 在 mirror 上要鉴权：`hendrycks/competition_math` 403 → 换 `EleutherAI/hendrycks_math`；`openai/PRM800K` / `RLHFlow/PRM800K` 401 → 改从 GitHub LFS 取真数据，经本地中继传输。

### 2.3 方法

**增殖的变体定义**（`DATA-AUGMENT-REF.md` 的便携规格）：每条 Numina 题目产出 3 个变体 —— `baseline`（原 CoT 分步，全部 `useful`）、`perturb`（中间某一步替换成似是而非的错误步，该步 `useless`）、`branch`（某步给 3 个候选下一跳，1 对 + 2 错，带标签）。默认 3x。

**v3 的四个硬校验**（全部通过才接受，最多重试 3 次）：

- `index ∈ [1, len-2]`：禁止改末步，否则只学到「结论错了」；
- `norm(wrong) != norm(orig)`：不允许等价改写；
- 长度比 `|len(a)-len(b)| / max(1,len(a)) <= 0.50`；
- 字符级相似度 $\mathrm{sim3}(a,b) = \dfrac{|3\text{-}gram(A) \cap 3\text{-}gram(B)|}{|A \cup B|} \ge 0.30$（先 `norm()` 去 LaTeX 标记与空白）。

其余实现点：`re.split(r"\n\s*\n", solution)` 分步、上限 20 步、`len(steps) < 3` 直接丢弃；**覆盖写入**（`open(out,"w")`）而非追加，每行 `flush()`；蓄水池抽样 `--sample N --seed 42` 可复现。API 走 `deepseek-flash`（由 `/v1/models` 查得，另有 `deepseek-v4-pro`）。

**GPU smoke test**：`AutoTokenizer` + `AutoModelForImageTextToText.from_pretrained(..., dtype=torch.bfloat16, device_map={"": 0})`；prompt 为纯文本 completion 格式 `Problem: %s\n\nSolution:\n`，`max_new_tokens=200`、`do_sample=False`（greedy），单条、无批处理。

**RLCD 选型核验方式**：所有 id / 行数 / 字段 / 体积均来自实时核验 —— `hf-mirror.com/api/datasets` + `datasets-server.huggingface.co`（info/size/rows）+ 真实下载样本解析 schema（核验后清理，未在仓库留存数据）+ GitHub / Zenodo API；401 需用 mirror 搜索索引交叉确认（hf-mirror 用 401 同时表示「不存在」和「gated」）。

## 3. 结果

### 3.1 主结果

| 配置 | 指标 | 数值 | 95% CI | 判定 |
|---|---|---|---|---|
| 首批资产落盘 | fs 用量 / 模型文件一致性 | 17 G / 200 G；14/14 一致；PRM800K md5 6/6 | 未记录 | ✅ |
| Qwen3.5-9B-Base 下载 | 字节数 / 分片校验 | 19.33 GB；4/4 `Content-Length` 一致 | 未记录 | ✅ |
| NuminaMath-CoT 下载 | 行数 / 体积 | 859,494 行；1.23 GB | 未记录 | ✅ |
| 9B bf16 加载 | 显存占用 / 峰值 / 加载耗时 | 18.8 GB / 18.9 GB / 约 2 分钟 | 未记录 | ✅ |
| 9B 生成 | 吞吐 | 23.6 tok/s（单条、greedy、无批处理） | 未记录 | ✅ |
| 增殖 v3（3 条样本） | 变体数 / 失败数 / accept 率 | baseline 3 / perturb 3 / branch 3 / failed 0；100% | 未记录（n=3） | ✅ |
| perturb 错误步位置 | 落在 `[1, len-2]` 的比例 | 3/3 | 未记录 | ✅ |
| RLCD 数据选型 | 步骤级真软标签可用性 | ReST-MCTS 426,449 行、33.5% 非二值；AlphaMath 309,327 步 × P/Q | 未记录 | ✅ |
| rlcd-lite 就位 | 体积 / 文件数 / 工作区状态 | 1.9 MB / 29 个 `.py` / 干净 | 未记录 | ✅ |
| 1k 增殖 / JEV 头 / RR-tree | — | 未跑 / 未实现 / 未生成 | — | ❌ |

v3 的三条 perturb 人工抽查（这是唯一的质量证据，n=3）：`(y+z)^2 → y^2 + z^2`（漏交叉项，教科书级代数错误）、`(1+1)(2+1)(1+1)=12 → (1+1)+(2+1)+(1+1)=7`（乘号改加号）、结论 `1,2,4 → 1,3`（条件判断错误）。branch 的错误候选也多为真推理错误（符号错、模运算误用、LCM 算错）。

### 3.2 对照与消融

本轮没有统计意义上的对照组，但有三组「判据对照」，恰好证明指标没被高估：

| 对照 | 设置 | 结果 | 说明 |
|---|---|---|---|
| 下载校验口径 | HF API `size` vs mirror 实际 `Content-Length` | API 3,960,337,888 vs 实际 3,959,604,768（差 733 KB） | 证明「按 API 字段校验」会给出假一致/假不一致 |
| 网络线路 | `network_turbo` vs `hf-mirror` 直连 | turbo 后 GitHub/HF 仍 HTTP 000（超时 10s）；mirror 200 | 证明下载成功不是「加速器生效」的错觉 |
| 相似度判据 | v2 词级重叠 vs v3 字符 3-gram | v2 把同段小幅改写全部拒绝（日志 `orig_norm=477 / wrong_norm=429 / ratio=0.10`），perturb 全灭 | 证明 accept 率由判据决定，不是由模型能力决定 |

RLCD 侧另有 rlcd-lite 自带的 7 条小模型实测（见 `RLCD-DATASETS.md` §8.3），本轮择要采信 4 条作为设计先验：

| # | 结论 | 对本实验的含义 |
|---|---|---|
| 1 | 只用 Brier 是陷阱，奖励必须 = 正确性 + Brier（RLCR） | binary reward 的 ECE **0.35** vs RLCR **0.08**（acc 0.76/0.78 持平） |
| 2 | 校准 ≠ 有信息：RLCR 置信度 reliability 0.007 但 resolution **0.000**，AURC 0.21 远差于温度缩放 softmax 的 0.07 | 判别信息在 choice 分布里，Score 头要读分布 |
| 3 | RL 会把原始 softmax 压塌：裸概率 ECE **0.21–0.23**（基座 0.18），一个拟合温度可修到 0.10–0.13 | E2 必须把「温度缩放后」与「裸概率」分开报 |
| 4 | 选项顺序翻转约一半答案：BoolQ **52%** / MMLU **46%**，TV 距离 ~0.35 | E0 现有「翻转率 ≤ 15%」判据严重过于乐观，应改置换平均 |

### 3.3 反直觉 / 负结果

1. **「软标签最稀缺」的直觉是错的。** RLCD（RL for Calibrated Decisions）的奖励是 proper scoring rule $reward = \mathbb{1}[correct] - (confidence - \mathbb{1}[correct])^2$，硬 0/1 就够 —— 预训练只需「答案可自动判对」+「难度覆盖带」。真正的敌人是全对/全错样本：OpenR1-Math-220k 抽样 100 行只有 **17%** 对错混合，k=2 占 **94%**（pass rate 只能取 {0, 0.5, 1}）。步骤级真软标签确实存在（此前「公开数据只有硬标签」的判断错误），但它是「可以做，不是必须做」。
2. **词级相似度在数学文本上失效。** `a^2+y^2=c^2` 这类内容两边无法按空格分词匹配，词重叠恒 0 → v2 的 perturb **100% 被误杀**。教训写死在规格里：对数学/LaTeX 必须用字符级相似度。
3. **「远端 GitHub 不可达」被推翻。** 10-05 记录的「必须走本地中继」在 10-06 20:07 实测作废：`curl -I https://github.com` → HTTP/2 200，`git clone` 直接成功（`COLD-START.md` 与旧 PROGRESS 记载已过期）。
4. **「`network_turbo` 能加速 HF」被推翻。** `source /etc/network_turbo` 后 `github.com` / `huggingface.co` 仍返回 HTTP 000；当前可行线路只剩 hf-mirror。`COLD-START.md` §4 的「真 HF 7.7–21 MB/s」在本次实例上失效。
5. **位置判据比预想的更脆。** E0 线原本的「top-1 翻转率 ≤ 15%」在 rlcd-lite 的 BoolQ/MMLU 实测下被打穿（52%/46%）；同时顺序一致性 rho 才是有效判据（注入 bias=0.20 时翻转率 0.075 仍合格、rho 已跌到 0.8582）—— 跨线结论，但直接影响本线 Choice 头的评测设计。
6. **小模型不能替 9B 验证 Choice 头。** 0.5B 在 77 路 / 151 路选择上全在随机水平，47% / 90% 的预测挤在同一 label 位置，却**自称置信度 0.83–0.89**（自信地错）。
7. **账务口径存疑，未采信。** 10-05 同一条记录既写「fs 用量 17G / 200G」又写「超 20G 免费额度约 3G → 约 ¥0.03/日」，两半互相矛盾；本轮只引用「17 G / 200 G」这一可复核值，费用口径不做结论。

## 4. 结论与判定

- **判定：部分完成。** 依据：资产层判据 A0-1/A0-2/A0-4 全部 PASS（含实测字节数、显存、吞吐）；A0-3 只在 n=3 上 PASS，放量未做；JEV 三原语头与 RR-tree 为 0。
- **可写（支持的结论）**：
  1. 在这套 AutoDL 环境里，19.33 GB 的 Qwen3.5-9B-Base 可用 bf16 直接加载进 24 GB 卡（显存 18.8 GB、峰值 18.9 GB），单条 greedy 生成 23.6 tok/s；加载耗时约 2 分钟，瓶颈是 `autodl-fs` 网络存储 IO 而非算力。
  2. 增殖 v3 在 3 条样本上能 100% 产出 baseline/perturb/branch 三类变体，错误步 3/3 落在中间步，错误类型为真代数/运算/条件错误；校验必须用字符 3-gram（`sim3 >= 0.30`），不能用词级重叠。
  3. 校准头的步骤级数据不必自建：`zd21/ReST-MCTS-PRM-0th` 426,449 行、**33.5% 非二值**；`MARIO-Math-Reasoning/AlphaMath-Trainset` 309,327 步、每步 P/Q 双浮点 —— 建议下载合计 < 3 G。
  4. 下载完整性只能以 mirror 实际 `Content-Length`（及 PRM800K 的 md5）为准，19.33 GB 模型 + 1.23 GB 数据这类资产可以在 200 G 文件存储上一次落盘、跨机复用。
- **不可写（诚实边界）**：
  1. 不能说「增殖脚本已验证可放量」—— n=3，accept 率 100% 未给置信区间；1k 串行 10–17 小时是**估算**，不是实测；1k 约 400 万 token 的成本也没有对账。
  2. 不能说「TQR-JEV 头有效」—— 三原语头、RR-tree 生成、E1 LLM-judge 均为 0；TQR 子分仍是 `return 1.0/0.0` 占位，`evaluate_tqr()` 仍恒返 9.1761。
  3. 不能把 23.6 tok/s 当作 RR-tree 采样吞吐 —— 单条、无批处理、无 KV cache 压测；显存只剩约 5 G（24 − 18.9），batch 上限未测。
  4. 不能引用任何 fs 路径为「固定挂载点」—— westc 是 `/root/autodl-fs`、westb 是 `/autodl-fs/data`，脚本硬编码必挂。
- **对后续决策的含义**：继续，但顺序固定为「给增殖脚本补并发 → 先对账再跑 1k → 用 v3 产物建 JEV 三原语头」。账户资金紧张是当前最硬的约束，任何「先开机再说」的方案都不成立。

## 5. 踩坑与修正

| 现象 | 根因 | 解法 |
|---|---|---|
| `hf download` 崩：`TypeError: process() takes no keyword arguments` | 默认走 hf_xet 后端，与本机环境不兼容 | `HF_HUB_DISABLE_XET=1`，成为必设项 |
| 同一文件下载速度跳变（31 KB/s ↔ 3.9 MB/s） | hf-mirror 限速按字节段而非按文件 | `curl -C -` 分段续传，越过慢段；实测回升到 8.6 MB/s |
| 分片字节数与 API 元数据差 733 KB | HF API 的 `size` 字段会过期 | 一律以实际 `Content-Length` 校验 |
| `hendrycks/competition_math` 403、`openai/PRM800K` 401 | mirror 对部分 repo 要求鉴权/已 gated | 换 `EleutherAI/hendrycks_math`；PRM800K 改走 GitHub LFS 真数据 |
| `ValueError: Cannot use apply_chat_template ...` | Base 模型没有 chat template（Instruct 版才有） | 全部生成脚本改用纯文本 completion（`Problem: …\n\nSolution:\n`） |
| 同一份脚本在东/西两台机上找不到模型 | `autodl-fs` 挂载点因机而异 | 开机先 `df -h \| grep -i autofs` 确认真实挂载点，不硬编码 |
| SSH 连不上（仓库内 `autodl-westc` 别名的旧端口失效） | 实例换机/重开后端口与域名都会变 | 用控制台新端口 + 仓库内 `known_hosts`，不写全局 `~/.ssh` |
| dry-run 与正式跑产出重复（`nm-0/1/2-base` 重复） | v1 用追加写入，两个阶段写进同一文件 | v2 改覆盖写入 + 每行 `flush()` |
| v1 有 50% perturb 只改最后一步（10 条里 5 条 `idx=last`） | prompt 未约束错误步位置 | v2 禁止改末步，强制 `index ∈ [1, len-2]` |
| v1 有 2/10 是 LaTeX 记号等价改写，被当成负例 | 没做等价性校验 | v2 加校验重试；v3 定成 4 条硬校验 |
| v2 的 perturb 全部被拒（accept 0） | 用「空格分词后的词重叠」，数学文本几乎无空格 → 恒 0 | v3 改字符 3-gram Jaccard `>= 0.30`，长度比放宽到 0.50 |
| 本机落盘 `augment.py` 源码多次卡死 300s | 本机写入通道对含 regex/花括号的 Python 文件稳定失败（markdown 正常） | 正本放远端 `autodl-fs/datasets/tqr_jev/augment.py`（用户手动保存），本地只留便携规格 |
| Strata 相关下载全部返 `Invalid rev id` | revision sha 打错一个字母；且 mirror 不认 pinned revision | 逐字符核对 sha；放弃严格 pin、改用 `resolve/main`（代价：无法保证与 Strata 同日同文件） |
| 把「GPU 不可用」误判成 TUN 代理劫持 | 未先判断实例是否已停止 | 用户确认实例已停止；判定顺序改为先看实例状态，再看网络/驱动 |

## 6. 未做 / 下一步

1. **1k 增殖未跑**（用户要求先确认）。串行预估 10–17 小时；1k 约 400 万 token；建议先加 `ThreadPoolExecutor`（8 线程 → 1.5–2 小时）再放量，放量前核对账户资金。
2. **JEV 三原语头未实现**（Noul / Choice / Score），共享 state + block-causal 分支掩码 + 一次前向并行读出的骨架未写；RR-tree 未生成；E1 LLM-judge 未跑。
3. **阻塞项**：`Stellan_Core/sub_agent_framework/base_agent.py:168` 的 `evaluate_tqr()` 用全默认 `TQRScore()`、不读 node → 任意节点恒返 9.176056742068813；`tqr_guided_rl/src/tqr/__init__.py` 的 α/β_r/β_n/δ 仍是占位符。不修则后续判别力测量无效。
4. **待拍板**：① RLCD 决策粒度 —— 最终答案（数据现成、rlcd-lite 直接抄）还是 RR-tree 节点/候选（需自建 k=8 节点级 rollout，要 GPU 钱）？② Score 头软标签主线 —— ReST-MCTS（426k 行、33.5% 非二值，最省事）还是 AlphaMath（309k 步 × 2 浮点，更贴近逐步 MCTS）？
5. **rlcd-lite 依赖未装、测试未跑**（27 个测试用微型随机模型，不需下载；`scripts/ab_eval.sh` 复现校准结论需真实 GPU）。B/C 层数据集只做了元数据与样本级核验，**没有下载任何数据**。
6. **账户资金紧张（< ¥20）**，且普通实例连续关机 15 天会被自动释放；`autodl-fs` 上的资产不受释放影响，但 1k 增殖与 GPU 对照必须先充值。

## 7. 证据与产物

| 路径（相对 `autodl/`） | 说明 |
|---|---|
| `PROGRESS.md` | 逐步记录：10-05 阶段 0、10-06 增殖 v3 / GPU 验证 / RLCD 选型 / Strata 清理 |
| `DATA-AUGMENT-REF.md` | 增殖 v3 便携规格（输出 schema、4 条校验、实测验证、待改进） |
| `GPU-VALIDATION.md` | 9B 加载/生成实测数据与三个坑、性能建议、边界 |
| `RLCD-DATASETS.md` | 数据集核验（B1/B2/B3、评测集、负面清单、头映射）、rlcd-lite 7 条实测结论 |
| `EXPERIMENT_PLAN.md` | TQR-JEV 设计蓝图、H1–H8、S0–S6 与 Gate、风险 |
| `PROGRESS-SUMMARY.md` | 一页式状态与「下次开机提醒」 |
| `INDEX.md` | 远端资产清单、当前状态、环境限制备忘 |
| `SESSION-2026-10-06.md` | 10-06 晚会话快照与明确的边界清单 |
| `features.py` / `e0_harness.py` | 同批 E0 工具（另一条线，本轮零改动） |
| 远端 `autodl-fs/{models,datasets,code,logs}/` + `MANIFEST.md` | 全部资产与逐文件大小/sha256 清单 |
| 远端 `autodl-fs/datasets/tqr_jev/augment.py` | 增殖脚本 v3 正本（本地无源码，只有规格） |

> 复现提示：GPU smoke test 脚本落在 `/tmp/smoke2.py`（会被清），日志在 `autodl-fs/logs/smoke9b2.log`（持久）；增殖小样命令为 `python3 augment.py --sample 1000 --limit 10 --out /tmp/dev10.jsonl`，放量为 `--out .../train.1k.jsonl`。
