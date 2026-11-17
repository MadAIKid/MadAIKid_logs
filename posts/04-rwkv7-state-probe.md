---
id: RWKV7
slug: 04-rwkv7-state-probe
title: RWKV-7 矩阵状态「读路径」探针：先修公式，再证明探针工具可判
subtitle: JEV 原案勘误 × x070.rc2 纯 PyTorch loader × 六臂读数的合成信号自检
date_start: 2026-10-07
date_end: 2026-10-08
status: 部分完成
verdict: 勘误 24 条；合成自检 R0=0.939、R3=0.912；真权重主实验 S2 未跑
tags: [探针, 探针工具, 文献, 判负]
hardware: GTX 1080 Ti 11 GB（Pascal CC 6.1）· 无 Triton / 无 bf16
models: RWKV-7 x070.rc2-172m-pile（171,807,744 参数）
datasets: LAMBADA（5153 条）· 合成信号自检（n=3000）
source_docs: [RWKV7-JEV-REVIEW.md, RWKV7-PROBE-PLAN.md, rwkv7_sizes.py, rwkv7_jev_proto.py, rwkv7-probe/README.md, rwkv7-probe/smoke_output.txt, rwkv7-probe/lambada_output.txt, probe/README.md, probe/readouts.py, PROGRESS.md]
---

# RWKV-7 矩阵状态「读路径」探针：先修公式，再证明探针工具可判

> **一句话**：原案「用 RWKV-7 的矩阵状态外挂多个 JEV-style 决策头」的骨架可做，但公式与文献定位有 24 处问题（最贵的一处是 Adapter 参数量被低估 L 倍）；本轮先把公式改对、把 Pascal 卡上的纯 PyTorch loader 与六臂读数 harness 建起来并用合成信号自检（rank1 场景 R0=0.939，fullrank 场景 R3=0.912），**但真权重上的 R0 vs R1/R2/R3 主实验（S2）没有跑**，因此这条线「值不值得做」仍未判决。

## 0. 摘要

本轮的产出不是实验结论，而是**两份可复用的前置资产**：一份把原案公式与文献逐条改对的勘误（24 条），一套能在 Pascal 卡上严格加载 x070.rc2 权重、并抽出每层每头矩阵状态 `S_T` 的纯 PyTorch 实现。

四个可验证点全部通过：权重严格加载（426/426 keys、171,807,744 参数、缺失与多余 key 均为空）、LAMBADA 客观评分（5153 条，ppl 20.4244 / acc 40.21%）、六臂读数 harness 在合成信号上能干净分辨「自适应性」与「结构自由度」两根轴、零假设臂稳定落在 0.5 附近。

但**边界必须写在最前面**：主实验 S2（真权重上 R0 对 R1/R2/R3 的读数对比）停在「待接入」，一行真权重探针数字都没有；P0/P1/P2 价值底线臂同样未跑。因此本轮只能声明「工具可判」，不能声明「RWKV-7 的 state 静态可读/不可读」。

| 实验 | 问题 | 结果 | 判定 |
|---|---|---|---|
| RWKV7-A | 原案的公式与文献定位站得住吗？ | 逐节勘误 **24 条**；核心状态式改减号且 k̃≠κ̂ | ✅ 已改对 |
| RWKV7-B | State Adapter 到底多贵？ | 0.4B 上 `W·Flatten(S)` = **1,661 M**（backbone 的 3.7 倍）；层间共享后 **4.3 M / 17.3 M** | ✅ 纯算术可复算 |
| RWKV7-C | x070.rc2 能否在 Pascal 上纯 PyTorch 严格加载？ | 426 keys、171,807,744 参数、missing/unexpected 均空 | ✅ |
| RWKV7-D | 加载出来的真是「对的模型」吗？ | LAMBADA n=5153：ppl **20.4244**、acc **40.21%** | ✅ 客观检查 |
| RWKV7-E | 六臂读数能否分辨秩与自适应性？ | rank1 场景 R0 **0.939**；fullrank 场景 R3 **0.912**；Z 0.507/0.517 | ✅ |
| RWKV7-F | 真权重上 R0 vs R1/R2/R3 谁更强？ | **未跑**（只有合成自检） | ❌ 主实验缺口 |

## 1. 问题与假设

这条线要回答的决策问题是：**要不要在 RWKV-7 的矩阵值循环状态上继续投入（外挂决策头 / State Adapter / 动态特征）？** 原案（一份《RWKV-7 State × JEV 多头 System-1》设计稿）给出的是「值得做」的肯定回答，本轮的任务是先检查它凭什么是肯定的。

评审给出的预注册式判据是三条可证伪命题（否证即判负）：

| # | 命题 | 否证条件 |
|---|---|---|
| P1 | state 比它自己的 hidden 读出**多**含决策信息 | 输入门控后的 hidden 探针 ≥ state 探针（同 F1 / 同 ECE） |
| P2 | 循环 state 比**廉价词袋特征**更值得（Pareto 前沿更优） | TF-IDF+LR 落在 state 探针前沿右下方之外 |
| P3 | state 动力学（`e_t`/`ΔS_t`）比静态 state 更有决策价值 | `[S_t, e_t]` 与 `[S_t]` 的 AURC 差异落在 CI 内 |

怀疑原案的理由集中在四处：公式来源、Adapter 成本、`ΔS` 的信息论地位、以及新颖性定位（完整的文献检索后，原案约 **75–80% 是标准先验**：learning-to-defer、校准、探针协议、多头 MTL、按收敛停止都有 1970–2024 的规范文献）。表里是逐条勘误中最影响实验设计的那几行，`原式 → 订正式`：

| 原案位置 | 原案写法 | 错在哪 | 订正式 |
|---|---|---|---|
| §1 状态更新 | $S_t = S_{t-1}(\mathrm{diag}(w_t) + a_t^T b_t) + v_t^T k_t$ | 加号来自 AI 撰写的 wiki（作者已免责）；且移除键 ≠ 写入键 | 论文 Eq.17：$S_t = S_{t-1}(\mathrm{diag}(w_t) - \hat\kappa_t^T(a_t \odot \hat\kappa_t)) + v_t^T \tilde{k}_t$ |
| §6B adapter | $z = W\,\mathrm{Flatten}(S)$ | 0.4B 上 1,661 M 参数 = backbone 3.7×；低秩版每 token 仍吃前向 46% | 层间共享投影：$(HN^2+2d)\,r$ = 4.3 M(r=64) / 17.3 M(r=256) |
| §7 ΔState | `ΔS_t` =「刚发生了什么变化」的新信息 | $(S_{t-1},S_t) \leftrightarrow (S_t,\Delta S_t)$ 是双射；给定当前 state 与相邻 token 后条件信息为零；遗忘项恒非零 | 用精确 innovation $e_t = S_t - G_t S_{t-1} = v_t^T \tilde{k}_t$ |
| §20 多头 | 多个 Head 比一个大 Head 更重要 | $Y \to Z \to J \to A$ 是 Markov 链，DPI 给出 $I(A;Y) \le I(J;Y) \le I(Z;Y)$：多头只可能丢信息 | 改写成三条可检验理由（正则 / 延迟 / 可监督），并做 ①/②/③ 三臂消融 |
| §13 校准 | 把 ECE 加进损失；$\mathrm{CE} + \lambda\,\mathrm{Brier}$ | ECE 不可微且有限样本下有偏；两者作用于同一标签是双重计数 | 只用 proper scoring rule；ECE 只作评测并报 bootstrap CI |
| §9 三元组 | head 输出 $(y_i, p_i, c_i)$ | $y=\arg\max p$、$c$ 为分布统计量时都是确定性函数 | head 只输出 `p_i`；confidence 由分布导出 |
| §16 early-exit | $D_t=\|P(S_t)-P(S_{t-1})\| \to 0$ 即「想清楚了」 | 稳态吞吐（ΔS=0 而信息仍在全速流动）、$\rho(G)$ 无小于 1 的下界、`P` 多对一 | `‖e_t‖` + 相邻 `ΔS` 方向余弦，且必须做无信息输入的零假设对照 |
| §17/§18 基线 | A–G 全是神经方法 | 缺 TF-IDF/fastText+LR 价值底线 | H 臂必做，否则「同精度下省一个数量级」不能证成 |
| §23 资料 | 把 wiki.rwkv.com 列为官方资料 | 作者在 README 里明确免责 *AI-written. might contain errors* | 权威序：论文 > 官方代码 > README > Wiki |
| §24 新颖性 | 「该组合视为本方向首创」 | 已有公开实现（RWKV-7-1B + Jev 式受限 softmax，acc 0.541，未复核） | 新颖性收窄到**表示层**：矩阵状态探针 |

## 2. 实验设置

### 2.1 环境

| 项 | 实测值 |
|---|---|
| GPU | GTX 1080 Ti 11 GB，**compute capability 6.1（Pascal）**，驱动 525.147.05 / CUDA 12.0 |
| 系统 | Ubuntu 18.04.6 · i5-7600K（4 核，长期任务占了约 3 核）· 15 GiB |
| 框架 | conda env `gi`：python 3.10 · torch 2.5.1（`cuda_available=True`） |
| 算力实测 | 4096³ matmul：fp32 **9.63 TFLOP/s**、fp16 **8.43 TFLOP/s** |
| 缺失组件 | **无 `nvcc`、无 `triton`、无 `fla`**；`sm_61 < CC 7.0` ⇒ Triton 根本无法使用 |

硬件约束直接决定了实现路线：**全部纯 PyTorch**，不用 `torch.utils.cpp_extension`、不编译 CUDA 扩展、不调 Triton/FLA；权重是 bfloat16 而 Pascal 不支持 bf16，必须在加载时 upcast 到 float32。

### 2.2 模型与数据

- checkpoint：`rwkv-x070-rc2-172m-pile.pth`（343 MB，md5 `b87190fa798b473bc6a71633fe772189`，两份副本字节一致）。
- 结构（从 ckpt 的 key 与形状反推）：`n_layer=12`、`n_embd=768`、`dim_ffn=2688`、`n_head=12`、`head_size=64`、`vocab=50304`；FFN 用 **x060 的 channel-mix**；LayerNorm 实为 `GroupNorm(12, 768, eps=64e-5)`（`eps = 1e-5 · 8²`）。
- tokenizer 必须用 Pile 那份 `20B_tokenizer.json`（vocab 50277，padding 到 50304）；用 World 的 65536 词表会产出垃圾 token id。
- LAMBADA：`lambada_test.jsonl` 全量 5153 条，stride=1（不抽样）。

### 2.3 方法

**（a）模型自身读出写成泛函族。** 论文 Eq.21 的读出是 $p_t = \mathrm{LayerNorm}(r_t S_t^T) + u_t$，逐坐标展开即 $(r_t S_t^T)_j = \langle e_j r_t^T,\ S_t\rangle$。也就是说，LM 自己的读出是「右因子锁在单一输入相关 `r_t` 上」的一族秩一线性泛函。于是「探针 vs 模型自己」不是包含关系，而是两根正交轴上的四个读数族（`K` 个决策类，单头参数）：

| 族 | 泛函 | 轴 | 参数量 |
|---|---|---|---|
| **R0** | $\langle c\,r_t^T, S\rangle$ | 自适应（右因子=$r_t$） | $KHN$ |
| **R1** | $\langle a_k b^T, S\rangle$（$b$ 跨类共享固定） | 静态 | $HN(K+1)$ |
| **R2** | $\langle a_k b_k^T, S\rangle$（两因子各自学） | 静态 | $2HKN$ |
| **R3** | $\langle W_k, S\rangle$（满秩，可 rank 截断做容量控制） | 静态 | $HKN^2$ |

**（b）六臂对照（一次跑完）。** P0 = TF-IDF+LR 价值底线；P1 = R0；P2 = hidden 向量 + **输入门控** MLP（门控是必需的，否则「自适应 vs 静态读出」这个混杂因子会污染对照）；P3 = R2 主实验；P3′ = 输入条件读 `Q(x_t)S`；P4 = R3 上界 + MDL 容量约束。Z 臂（标签置换 / 随机特征）是门禁：不过关则整轮作废。

**（c）指标。** AUROC / Brier / ECE（等频分箱）/ 风险-覆盖率 AURC，全部带 bootstrap CI；ECE 的去偏估计（Roelofs 式）**未实现**，返回值里用 `ece_debiased_implemented=False` 显式标出。

**（d）自检先于真权重。** 在碰真权重之前，用合成信号验证「状态 → 读数族 → 指标」这条链路：`S ~ N(0, 1/√N)`、`r` 同分布，`n=3000`、`H=4`、`N=8`、噪声 1.0、seed 0；两个场景分别打两根轴——`rank1`（信号 = `Σ_h c_hᵀ(S_h r_h)`，右因子输入相关）与 `fullrank`（信号 = `Σ_h ⟨M_h,S_h⟩`，`M_h` 满秩且与输入无关）。

## 3. 结果

### 3.1 主结果

| 配置 | 指标 | 数值 | 95% CI | 判定 |
|---|---|---|---|---|
| `load_x070` 严格加载 | missing / unexpected keys | `[]` / `[]` | — | ✅ |
| 同上 | 参数量（对账 ckpt） | 171,807,744（171.808 M） | — | ✅ |
| 同上 | 加载耗时 / dtype | 5.1–6.4 s；bf16→fp32 | — | — |
| 合成自检 `rank1` | R0 AUROC | **0.939** | 未记录（单种子） | ✅ |
| 合成自检 `rank1` | R1 / R2 / R3(rank=2) | 0.517 / 0.481 / 0.514 | 未记录 | ✅ 落随机 |
| 合成自检 `fullrank` | R3 AUROC | **0.912** | 未记录 | ✅ |
| 合成自检 `fullrank` | R0 / R1 / R2 / R3(rank=2) | 0.509 / 0.701 / 0.684 / 0.820 | 未记录 | ✅ |
| 零假设臂 | label_shuffle / random_feat | 0.507 / 0.517 | 未记录 | ✅ |
| LAMBADA（真权重） | ppl / acc | **20.4244** / **40.21%**（2072/5153） | 未记录 | ✅ 客观检查 |
| 吞吐（真权重，B=1） | RNN decode / prefill T=256 | 61.2 tok/s（16.34 ms/token）/ 558 tok/s | — | — |
| **真权重读数对比** | R0 vs R1/R2/R3 | **未跑** | — | ❌ S2 缺口 |

三件被真跑过的实现事实：① `S` 的形状确认为 `[B,H,N,N]`（每层），最后一层 `S.absmax` 达 38.76，而 `x.absmax` 逐层从 18.10 长到 406.11；② batched 前向与 RNN 逐 token 解码数值等价，`max|Δlogit| = 1.144e-05`；③ 贪心生成在真 tokenizer 下能给出 `The Eiffel tower is in the city of Paris, France.`。

**原案参数预算复算**（`rwkv7_sizes.py`，纯标准库、可独立复算，对账论文 Appendix E.2）：

| 方案 | 参数（0.4B，r=64） | 参数（r=256） | 说明 |
|---|---|---|---|
| A 全局池化 | ~0 | ~0 | — |
| B `W·Flatten(S)` | **1,661 M** | **1,661 M** | backbone 的 3.7 倍 |
| B′ 展平→r 低秩 | 104 M | **415 M** | r=256 时 = 前向的 46% |
| C 层间共享投影 | **4.3 M** | **17.3 M** | 与层数无关，约为前向的 1.9% |

WKV state 与 hidden 的关系有一个干净恒等式：`|S_wkv|/|H_stack| = N = head_size`，而已发布的 RWKV-7 全部 `head_size=64`，所以这个倍数恒为 64（0.4B：`|S|=1,622,016` floats = 6.49 MB/token）。

### 3.2 对照与消融

- **两场景互为对照**：`rank1` 场景里静态族全部塌到 0.48–0.52，`fullrank` 场景里自适应族塌到 0.509——两根轴被干净分离，说明 harness 不是「怎么读都能读出信号」。
- **Z 臂过关**：label_shuffle 0.507、random_feat 0.517，都贴着 0.5 ⇒ 指标没有被探针容量高估（至少在这个合成设定下）。
- **容量控制**：`fullrank` 场景把 R3 从满秩降到 rank=2，AUROC 从 0.912 掉到 0.820，方向正确（降秩降能力），说明 `R3Readout(rank=)` 的截断确实起作用。
- **生成文本不能当判据**：同一次 smoke 里，第二个 prompt 的贪心输出是复读 ` User: What is the capital of France?`，看不出「模型对不对」。所以客观正确性改用 LAMBADA 的全量评分（40.21%），而不是「生成看起来像不像」。

### 3.3 反直觉 / 负结果

1. **自检抓到两个真问题（都已修）**：① `R3` 的 einsum 维度写错（`bhkij` 少一维）⇒ 运行期 `RuntimeError`；② 第一版判据没有区分度——用「每头秩二」信号当场景时，随机高斯 `S` 下最优秩一近似仍能到 **AUROC 0.98**（R1 0.9789 vs R2 0.9805），**秩二场景区分不出 R1/R2**。换成 `rank1` / `fullrank` 两个场景才有区分度，这条也写进了 `probe/smoke.py` 的文档字符串：**合成自检也会骗人，判据本身要单独验证**。
2. **`fullrank` 里 R1(0.701) 略高于 R2(0.684)**，而 R2 的形式是 R1 的超集。CI 大幅重叠，判为优化噪声而非表达力倒挂；单种子 + 早停看 val AUROC，无法排除。这正是「正式实验必须多种子」的直接理由。
3. **权重定义不在工作树里**：ckpt 的 key（`time_maa_x` / `time_aaaaa` / `gate_w1` …）对应的是 git 历史里的 rc2 版本，工作树里躺着的 demo 是更晚的重命名版本。按 ckpt key 命名实现后可以 strict 加载，但「对着错版本的代码读权重」是一个必踩的坑。
4. **三处吞吐数字不可互相引用**：B=1 的 RNN decode 是 61.2 tok/s（16.34 ms/token），prefill T=256 是 558 tok/s，LAMBADA 全序列 scoring 是 457.3 tok/s，而同机另一个 162.2 M 的退化 RWKV-7 在 16×256 batch 下报 5,075 tok/s。**脱离 batching 与模式谈吞吐没有意义**。
5. **算术小账对不上**：层间共享方案在 r=256 下给出 17.3 M，但评审正文/`INDEX` 摘要写「17.6 M / 1.95%」。按 2×450.8 M ≈ 901.5 M MAC 复算，17.3 M 对应约 **1.92%**，1.95% 对应 17.6 M。以可复算脚本的 17.3 M 为准。
6. **主实验 S2 没有跑**，所以「为什么必须是 state」这个核心问题（P1）本轮连一条真权重数字都没有。

## 4. 结论与判定

**判定：部分完成。** 勘误、预算核算、loader、读数 harness 与自检全部完成并通过；S2 及 P0/P1/P2 臂未跑，故不给出方向性判决。

**可写（支持的结论）**：

1. 原案最贵的一处是 Adapter 参数量：`W·Flatten(S)` 在 0.4B 上是 **1,661 M**（backbone 的 3.7 倍），低秩版每 token 仍占前向 **46%**；改成层间共享投影后是 **4.3 M（r=64）/ 17.3 M（r=256）**。这条是纯算术，可独立复算。
2. `ΔS_t` 是 `(S_{t−1},S_t)` 的确定性重参数化；给定 $(S_t, x_t, x_{t-1})$ 后 $I(\Delta S_t; Y \mid S_t, x_t, x_{t-1}) = 0$，且它的遗忘项恒非零、在低信息 token 上主导，因此 `‖ΔS_t‖` 分不清「忘了」与「学了」；干净替代是精确 innovation $e_t = v_t^T \tilde{k}_t$。
3. x070.rc2 172M 权重可在 Pascal 上纯 PyTorch **严格**加载（426 keys / 171,807,744 参数 / 缺失与多余 key 均空），且在 LAMBADA 全量 5153 条上得 ppl **20.4244** / acc **40.21%**。
4. 六臂读数 harness 在合成信号上双向可判：`rank1` 场景 R0 **0.939** vs 静态族 0.481–0.517；`fullrank` 场景 R3 **0.912** vs R0 0.509；Z 臂 0.507/0.517。

**不可写（诚实边界）**：

1. 不能说「RWKV-7 的 state 静态可读」或「静态不可读」——S2 未跑。
2. 不能说 state 探针优于 hidden 探针（P1），也不能说它优于 TF-IDF（P2）——两条臂都未跑。
3. 不能用「每步最多移除 45.5%」推出 state 会收敛或可用于 early-exit：$G = \mathrm{diag}(w) - \hat\kappa^T(a \odot \hat\kappa)$ 是「对角+秩一」，谱半径没有小于 1 的下界（`w≈1, a≈1` 时可有 N−1 个特征值恰为 1）。
4. 不能把 40.21% 说成「与官方数字对齐」——源文档里**没有** rc2-172m-pile 的官方 LAMBADA 参考值（未记录）。

**对后续决策的含义**：这条线仍然值得做，但顺序必须反过来——先跑 P0（TF-IDF 价值底线）、再跑 P1/P2（hidden vs state 对照），只有出现正信号才碰 `e_t` 与 router。S0 的天花板（teacher 标签一致率）必须先测，否则探针 accuracy 的上下限都不可解释。

## 5. 踩坑与修正

| 现象 | 根因 | 解法 |
|---|---|---|
| 论文式与官方代码符号不一致（一处 `−`，一处 `+`） | 代码把减号折进了 `ab = (−kk)ᵀ(kk·a)`；而 wiki 上直接写成 `+` | 权威序取论文 Eq.17；已做数值验证：论文式与代码式在 fp64 下 `max|Δ| = 1.8e-15` |
| 照抄公式得到转置的 state | 论文明确说 wkv 相对 RWKV-5/6 **被转置**以对齐代码 | 按 `[B,H,i,j]`（`i`=receptive、`j`=key）约定写全部 einsum |
| 加载直接报 bf16 相关错误/退化 | ckpt dtype 是 **bfloat16**，1080 Ti 不支持 | 加载时统一 upcast 到 float32（探针阶段固定并报告 dtype） |
| `load_state_dict(strict=True)` 报 key 对不上 | 工作树里的 `rwkv_v7_demo.py` 是 rc2 之后的重命名版本 | 权重的定义版本在 git 历史（`time_aaaaa` 在 rc2 提交里存在），loader 按 ckpt key 命名 ⇒ strict 通过 |
| `time_faaaa` 形状不匹配 | ckpt 里是 `(1,1,768)`，模块要 `(12,64)`（numel 相同） | 唯一一处 shape fix-up：`reshape(-1, 64)` |
| `head_size` 无法从 ckpt 恢复 | 它是 demo 里硬编码的常量（注释 *don't change*） | 暴露成 `load_x070(..., head_size=64)`，不猜 |
| tokenizer 用错、生成全是乱码 | 用的是 World 的 65536 词表，模型是 Pile 的 50277/50304 | 换成 `20B_tokenizer.json` |
| `kk` 归一化的范围不确定（整条 C 向量 vs 每头） | rc2 是 `F.normalize(kk, p=2)` 整条；后续版本改成 per-head | 默认 `kk_norm_mode="full"`，保留 `"head"` 供对照；实测只有 `full` 能生成连贯文本 |
| 自检里 R3 一跑就 `RuntimeError` | einsum 少一维（`bhkij` 写成缺一维） | 修维度；自检的价值正在于此 |
| 自检判据无区分度（R1 0.9789 vs R2 0.9805） | 用「每头秩二」当场景，秩一近似就能捞到 0.98 | 换成覆盖自适应性与秩的两场景 |
| `rsync` 同步 harness 到工作机失败 | 该机 rsync 协议不兼容 | 改用 `tar czf - . \| ssh ... tar xzf -` |

## 6. 未做 / 下一步

| 未做 | 原因 / 成本 |
|---|---|
| **S2 主实验**（真权重 `S_T`/`r_T` → R0/R1/R2/R3 对比） | 只到合成自检；前置是 `S_T`/`r_T` 特征落盘与 P0 基线 |
| P0（TF-IDF+LR）与 P1/P2 臂 | 未跑，但成本最低、判决力最强 |
| S3 层/头分解 | 依赖 S2 |
| S4 动态特征 `e_t`（逐 token，需 RNN 模式或 chunk 边界） | 依赖 S1/S2 |
| S0 反事实路由标签 `retrieve = 1[cheap_correct = 0]` | 需 `strong_pass_rate` 数据池 |
| 多种子 + 方差 + 去偏 ECE | 自检单种子；ECE 去偏未实现（已在返回值标注） |
| `verify_readout.py` 的逐层 `S@r` 对照输出 | 脚本已写，**产物未落盘**（无记录数字） |
| `rwkv7_jev_proto.py`（修正版原型骨架） | **未执行**，只过 `py_compile`（本机 python 无 torch） |

下一步的性价比排序：① 补 P0 与标签天花板（CPU 即可）；② 同一 harness 跑 hidden 与 state 的对照（< 1 GPU 小时）；③ 只有出现正信号才做 `e_t` 与 S3 层分解。另需注意：状态抽取在这台机器上不是瓶颈（同机另一实现 162.2 M 退化 RWKV-7 实测前向 5,075 tok/s，10k prompt ≈ 17 min；172M 权重每样本 fp32 状态 192 KB ⇒ 10k ≈ 1.9 GB，换 0.4B 则按规划为 3.24 MB/样本 ⇒ 32 GB），真正的瓶颈是**判决顺序**而不是算力。

## 7. 证据与产物

| 路径（相对 `autodl/`） | 说明 |
|---|---|
| `RWKV7-JEV-REVIEW.md` | 原案评审：§2 公式推演、§3 外部事实核查、§4 逐节勘误（24 行）、§5 修正路线 |
| `RWKV7-PROBE-PLAN.md` | 读路径探针计划：四族读数、六臂、kill criteria、S0–S4 排期 |
| `rwkv7_sizes.py` | state / Adapter 预算计算器（纯标准库，已跑通，对账论文 Appendix E.2） |
| `rwkv7_jev_proto.py` | 修正版原型骨架（未执行，仅 `py_compile`） |
| `rwkv7-probe/README.md` | loader 设计、Pascal 约束、API、复现命令 |
| `rwkv7-probe/x070_loader.py` | 纯 PyTorch 模型定义 + 严格加载 + `forward_states` / `rnn_step` |
| `rwkv7-probe/smoke_output.txt` | 端到端原始输出：加载统计、逐层 `S` 统计、贪心文本、吞吐、交叉校验 |
| `rwkv7-probe/lambada_eval.py` / `lambada_output.txt` | LAMBADA 全量客观评分（n=5153，ppl 20.4244 / acc 40.21%） |
| `rwkv7-probe/verify_readout.py` | 逐层 `S@r` 与 kernel `y_last` 的对照脚本（输出未落盘） |
| `probe/README.md` | 六臂 harness 说明 + 合成自检表 + 已知局限 |
| `probe/readouts.py` / `metrics.py` / `fit.py` | R0–R3 读数、带 bootstrap CI 的指标、单臂训练/评测 harness |
| `probe/smoke.py` | 合成信号自检（两场景 + Z 注入 + 判据反例的文档字符串） |
| `PROGRESS.md`（2026-10-08 条目） | 工作机硬件/算力实测、bf16 坑、状态抽取算力换算 |
