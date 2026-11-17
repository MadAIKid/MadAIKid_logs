---
id: PJEV
slug: 05-prompt-jev
title: prompt-based JEV pilot：冻结 LM 的答案位置比它自己的嘴多知道什么
subtitle: 严格 readout gap +9.4 pt 成立，但「格式不变的单方向判断向量」判负
date_start: 2026-10-22
date_end: 2026-10-22
status: 部分完成
verdict: 严格 readout gap +9.4 pt CI[+7.6,+11.3]；格式不变单方向判负
tags: [探针, 校准, 可解释性, 判负]
hardware: GTX 1080 Ti 11 GB（Pascal·fp16）
models: Qwen3-1.7B-Base（fp16，冻结）
datasets: Geometry of Truth 8 子集（1876 条 / 1543 组）
source_docs: [PROMPT-JEV-PLAN.md, prompt-jev/README.md, prompt-jev/jevlib.py, prompt-jev/analyze.py, prompt-jev/out/rep_strict2/report.md, prompt-jev/out/optk_report/report.md, prompt-jev/out/opt4_report/report.md, prompt-jev/out/optk_ens/report.md, prompt-jev/out/noul/report.md, prompt-jev/out/steer/report.md, prompt-jev/out/steer_joint/report.md, prompt-jev/out/head_subspace/report.md, INDEX.md]
---

# prompt-based JEV pilot：冻结 LM 的答案位置比它自己的嘴多知道什么

> **一句话**：在冻结的 Qwen3-1.7B-Base 上，答案提示词末位的 `h_T` 线性可读到 0.916 acc，显著高于**同监督**训练的 2D logits 校准（0.822，+9.4 pt，CI [+7.6, +11.3]），差距集中在否定/比较类反事实陈述上——「readout gap」成立；但把同一探针搬到选项顺序反转的格式上只有 0.472，**「格式不变的单方向判断向量」被判负**，因此这条线的定位只能是「格式内读出 + 校准」，不能宣称通用判断方向。

## 0. 摘要

本 pilot 要回答的决策问题是：**给冻结 LM 外挂一个 JEV-style 零生成读出头，到底有没有真实增量**。做法是把「判断向量」拆成三层——`h_T`（脑）、受限到标签 token 的 logits（嘴）、外挂线性头——并在 1876 条配对反事实陈述上跑同一套 5 折 GroupKFold。

首轮结论是**有增量，但增量不是免费的**：Q2 线性探针 0.916 acc / 0.966 AUROC，高于模型自己的嘴（Q0′ 0.777）**13.9 pt**；把对照换成同样用过标签、同监督的 2D logits 校准（Q0-cal 0.822）后，严格 gap 仍是 **+9.4 pt [+7.6, +11.3]**。词袋基线 P0 = 0.513、标签置换 Z = 0.497 ± 0.015，排除了词汇捷径与探针容量伪迹。

第二轮把选项接口做成 K-generic（K=2..8）并补了弃权与因果检验：K=2 最稳（flip 4.1%），K=5 读出最强（probe 0.923），头+探针 stacking 到 **0.921 acc / 0.970 AUROC / 0.033 ECE**；显式 unknown 选项的 mass 是有效弃权信号（AUROC 0.835）。机制上，探针用到的信息**几乎完全在 LM head 的 letter 子空间之外**（投影掉后 0.931→0.929）。

边界：只有一个 1.7B base 模型、英文、1876 条；`score` 原语、instruct 模型、全量 13k、9B 均未跑，也没有 JevBench 外部有效性。

| 实验 | 问题 | 结果 | 判定 |
|---|---|---|---|
| PJEV-A | 决策点（答案位置）成立吗？ | 最佳零样本 `T1/cn` 0.833、`T3/answer` 0.830；纯换行类掉到 0.545–0.709 | ✅ |
| PJEV-B | 线性头比模型自己的嘴多读出多少？ | Q2 0.916 vs Q0′ 0.777（+13.9 pt）；严格 vs 同监督 Q0-cal **+9.4 pt** | ✅ |
| PJEV-C | 这是「判断」还是「格式」？ | 跨选项顺序迁移 **0.472 / 0.257**，方向余弦 0.154 | ❌ 判负 |
| PJEV-D | K 越大越好吗？ | K=2 acc 0.839 / flip 4.1%；K=5 probe 0.923。K 是接口自由度 | ✅ |
| PJEV-E | 弃权（noul）有信号吗？ | K=3 neutral mass→head 错误 AUROC **0.835**；80% 覆盖 acc 0.902 | ✅ |
| PJEV-F | 探针方向有因果作用吗？ | L23 ±4σ：p_true 0.369→0.423、flip 3%；三层联合 0.332→0.462 | ⚠️ 真实但弱 |
| PJEV-G | 信息是否就在 head 的 letter 子空间里？ | 投影掉该子空间后 probe 0.931→**0.929**，cos ≈ 0.001–0.065 | ✅ 机制 |

## 1. 问题与假设

「给冻结 LM 加一个决策头」这件事本身不新：`h_T` 上的 true/false 线性探针、truth direction、因果干预已被系统做过（Marks & Tegmark 2023 等）。所以本 pilot 的贡献点不是「探针能读出真假」，而是下面三条可证伪的对比：

| 编号 | 假设 | 预注册判据 |
|---|---|---|
| H2（主） | **readout gap**：外挂线性头 > 模型自己的受限 softmax | Q2 − Q0-cal 的配对 bootstrap 95% CI 下界 > 0 |
| H1 | **格式不变的判断方向**：同一事实换模板/换选项顺序仍可读 | 跨格式迁移明显低于同格式 ⇒ 判负（源文档口径：只在同格式有效 = 格式分类器，不是判断向量） |
| H5 | **terminator 是因果接口**：换错终止符会压低零样本与探针 | `answer` 类提示显著优于纯换行 |

主判据写成算式（$\mathrm{acc}$ 为严格 group split 下的 5 折 OOF 准确率）：

$$\Delta_{\mathrm{strict}} = \mathrm{acc}(Q2) - \mathrm{acc}(Q0_{\mathrm{cal}})$$

三个必须分开的对象（概念上最容易混的一处）：**V1** = `h_T`，终止符所在位置的 residual stream（final norm 之后，即 `lm_head` 的输入，无训练）；**V2** = $z = h_T W_U$ 受限到标签 token 的 softmax（零参数，模型「嘴上说」的判断）；**V3** = `g(h_T)` 外挂头（有训练）。标准 next-token prediction 里位置 `T` 之后并没有「另一个输出向量」，所谓「分类向量」只能是 V2 或 V3。

判死条件（预先写死）：P0（TF-IDF+LR）追平 Q2 ⇒ 词汇捷径、停；Z 臂不接近 0.5 ⇒ 探针协议无效、停；跨选项顺序迁移塌到随机以下 ⇒ 只是格式分类器、不能叫判断向量。

## 2. 实验设置

### 2.1 环境

| 项 | 实测值 |
|---|---|
| 主机 | 局域网工作机（内网 IP 已隐去；GTX 1080 Ti 11 GB，Pascal，**无 bf16**） |
| 环境 | conda env `gi`：python 3.10 · torch 2.5.1 · transformers 5.15.1 · sklearn 1.7 |
| 精度 | **fp16 强制**（1080 Ti 不支持 bf16）；单次前向、模型全程冻结、零生成 |
| 模型 | Qwen3-1.7B-Base（ModelScope 权重，本地路径 `models/Qwen/Qwen3-1___7B-Base`） |

### 2.2 模型与数据

- 数据：Geometry of Truth 8 个子集 —— cities(600) / neg_cities(200) / sp_en_trans(176) / neg_sp_en_trans(100) / larger_than(200) / smaller_than(100) / companies(200) / common_claim(300)，pilot 共 **1876 条**，标签平衡。
- 切分：按**实体**统一 group 的 5 折 GroupKFold（`cities:X` 与 `neg_cities:X` 同组，`sp_en:X` 与 `neg_sp_en:X` 同组），共 **1543 组**，防止同实体跨 train/test。
- 提示：4 模板 × 4 终止符 = 16 组合；主组合 `T1/answer`（`Statement: … A. True B. False\nAnswer:`）。`T1b` 是选项顺序反转的对照格式。
- 标签 token 检查（必须先做）：` A`=362、` B`=425、` True`=3007、` False`=3557，均为**单 token**；前导空格必须保留（`" True"` ≠ `"True"`），受限 softmax 用模板里真实出现的那个 id。

### 2.3 方法

`h_T` = 末位 residual（post final norm）；`z` = 受限到标签 token 的 logits。对照臂：

| 臂 | 读出 | 参数量 | 监督 | 作用 |
|---|---|---|---|---|
| Q0 | 受限 softmax（温度校准） | 0 | 无 | Jev 式零生成基线 |
| Q0′ | DC-PMI / contextual calibration | 0 | 无 | 去掉标签先验后的嘴 |
| **Q0-cal** | **2D logits 上的逻辑回归** | 2 | **有** | **同监督的公平校准对照**（严格判据的分母） |
| Q1 | diff-in-means 方向 $\mu_+ - \mu_-$ | `d` | 有 | 判断是否单方向 |
| **Q2** | 线性探针 $\mathrm{softmax}(W h_T + b)$（L2，5 折 OOF） | `d·K` | 有 | 主实验 |
| P0 | TF-IDF + LR（只看陈述文本） | — | 有 | **价值底线** |
| Z | 标签置换 | — | — | 零假设门禁 |

指标：Accuracy / AUROC / Brier / ECE / 风险-覆盖率（AURC），配对差值用 bootstrap 95% CI（bootstrap 次数源文档未记录）。所有 acc 均为严格 group split 下的 5 折 OOF；第二轮为选项接口加 K-generic 实现（K=2..8，letter A–H），每个 K 做 K 个循环排列，并做排列 ensemble、头/探针 stacking、`noul` 弃权与 L15/L21/L23 steering。

## 3. 结果

### 3.1 主结果（首轮，primary `T1/answer`，n=1876）

| 配置 | 指标 | 数值 | 95% CI | 判定 |
|---|---|---|---|---|
| Q0 受限 softmax（温度校准） | acc / AUROC / Brier / ECE | 0.787 / 0.915 / 0.228 / 0.316 | 逐臂 CI 未记录 | 基线 |
| Q0′ DC-PMI | acc / AUROC / Brier / ECE | 0.777 / 0.915 / 0.126 / 0.101 | 未记录 | 基线 |
| Q0-cal 同监督 2D logits | acc / AUROC / Brier / ECE | 0.822 / 0.934 / 0.106 / 0.066 | 未记录 | **严格分母** |
| Q1 diff-in-means | acc / AUROC / Brier / ECE | 0.795 / 0.906 / 0.132 / 0.095 | 未记录 | 单方向不足 |
| **Q2 线性探针** | acc / AUROC / Brier / ECE | **0.916 / 0.966 / 0.070 / 0.051** | 未记录 | ✅ |
| P0 TF-IDF+LR | acc / AUROC / Brier / ECE | 0.513 / 0.512 / 0.253 / 0.062 | 未记录 | ✅ 随机 |
| Z 标签置换 | acc | 0.497 ± 0.015 | — | ✅ 门禁过关 |

配对 bootstrap（95% CI）——**严格判据就是第二行**：

| 对比 | Δacc | ΔAUROC |
|---|---|---|
| Q2 − Q0′（宽松版 gap） | **+0.139 [+0.117, +0.160]** | +0.051 [+0.040, +0.063] |
| **Q2 − Q0-cal（严格版 gap）** | **+0.094 [+0.076, +0.113]** | +0.032 [+0.023, +0.042] |
| Q2 − P0 | +0.403 [+0.378, +0.430] | +0.454 [+0.428, +0.481] |
| Q2 − Q1 | +0.121 [+0.101, +0.140] | +0.059 [+0.048, +0.071] |
| Q1 − Q0′ | +0.019 [+0.004, +0.034] | −0.008 [−0.012, −0.004] |

误差分解：两者都对 1373 条、仅 Q2 对 346 条、仅 Q0′ 对 85 条、都错 72 条。两半训练集的 diff-in-means 方向余弦 **0.992**：单方向很稳，但不是最优读出。

### 3.2 对照与消融

**（a）gap 集中在哪里（最重要的细读）。** 在模型「嘴上已经会」的事实题上探针没有增量；在否定与比较上，嘴接近/低于随机而 `h_T` 线性可读到 0.92–0.98：

| dataset | n | Q0′ | Q0-cal | Q2 | P0 |
|---|---|---|---|---|---|
| cities | 600 | 0.990 | 0.985 | 0.990 | 0.483 |
| sp_en_trans | 176 | 0.989 | 0.994 | 0.994 | 0.500 |
| larger_than | 200 | 1.000 | 1.000 | 1.000 | 0.700 |
| **neg_cities** | 200 | **0.195** | 0.595 | **0.945** | 0.485 |
| **neg_sp_en_trans** | 100 | **0.220** | 0.260 | **0.920** | 0.540 |
| **smaller_than** | 100 | 0.500 | 0.560 | **0.980** | 0.340 |
| companies | 200 | 0.825 | 0.840 | 0.780 | 0.445 |
| common_claim | 300 | 0.713 | 0.690 | 0.717 | 0.570 |

P0 在配对反事实数据上全部落在随机水平（0.340–0.700），排除词袋捷径；`companies` 是唯一 Q2(0.780) 略低于嘴(0.825) 的子集，说明 gap 不是全局的。

**（b）决策点。** 最佳零样本组合 `T1/cn` 0.833、`T3/answer` 0.830，而纯换行类明显更差（`T1/nl` 0.545、`T2/nl` 0.600）⇒ H5 初步成立：`answer` 类提示确实是一个「要作答」的位置。

**（c）层。** 二值主线的层扫描：L0–L7 ≈ 0.52–0.59 → L10 0.706 → L14 0.891 → **L15 0.926** → **L23 0.934（峰值）** → final 0.916。K=4 重扫（p0 排列）把峰值定在 **L21**（0.931 / AUROC 0.974），L15–L23 平台 0.929–0.931。真值在中后层才线性可读，**末层反而略降**，所以读出头未必要接最后一层。

**（d）K sweep（同一批 1876 条，cue=`answer`，跨 rotation 平均）。** K 是接口自由度，不是容量：

| spec | K | acc_dc | AUROC | Brier | ECE | accK | flip rate | probe within | probe aug（留出排列） |
|---|---|---|---|---|---|---|---|---|---|
| k2 | 2 | **0.839** | 0.928 | 0.112 | 0.063 | 0.828 | **0.041** | 0.913 | 0.662 |
| k3 | 3 | 0.832 | 0.923 | 0.111 | **0.060** | 0.807 | 0.120 | 0.913 | 0.858 |
| k4 | 4 | 0.821 | 0.923 | 0.120 | 0.081 | 0.811 | **0.298** | 0.914 | 0.876 |
| k5 | 5 | 0.818 | 0.909 | 0.131 | 0.099 | 0.777 | 0.203 | **0.923** | **0.889** |

K 增大不提高原始准确率；K=4 的顺序敏感性最差（flip 29.8%），K=5 的 probe 最强。A/B/C/D 四选项单独一轮（4 个循环排列）给出 flip 23.0%，而二值只有 9.2%。

**（e）排列 ensemble + 头/探针 stacking（最优配方）。**

| spec | method | acc | AUROC | Brier | ECE |
|---|---|---|---|---|---|
| k2 | probe_mean | 0.906 | 0.962 | 0.078 | 0.063 |
| k2 | stack(head+probe) | 0.909 | 0.966 | 0.070 | **0.028** |
| k3 | stack | 0.912 | 0.966 | 0.070 | 0.031 |
| k4 | stack | 0.914 | 0.967 | 0.069 | 0.031 |
| k5 | probe_mean | 0.920 | 0.969 | 0.066 | 0.045 |
| **k5** | **stack** | **0.921** | **0.970** | **0.064** | 0.033 |

头与探针**互补**：ensemble 只把头从 0.818 抬到 0.833，但把 probe 与 head 一起喂给 stacker 能稳定拿到 0.909–0.921、ECE 降到 0.028–0.033。

**（f）`noul` 弃权。** 显式 unknown 选项的 mass 能预测 head 错误：

| spec | K | head acc | probe acc | neutral mean | AUROC(err~neutral) | acc@80% 覆盖 | AURC |
|---|---|---|---|---|---|---|---|
| k2 | 2 | 0.842 | 0.913 | 0.000 | 0.500 | 0.848 | 0.154 |
| k3 | 3 | 0.839 | 0.913 | 0.029 | **0.835** | **0.902** | **0.046** |
| k4 | 4 | 0.827 | 0.914 | 0.033 | 0.811 | 0.888 | 0.055 |
| k5 | 5 | 0.806 | 0.923 | 0.038 | 0.794 | 0.902 | 0.082 |

K=3 时 neutral mass 对错误的 AUROC **0.835**，优于 entropy（0.646）与 margin（0.821）⇒ K>2 的价值不在准确率，而在 JEV 的 `noul` 原语。

**（g）steering（K=5，200 条分层样本，α 从 −4 到 +4）。** 探针方向单调、且强于随机方向（probe–α corr = 1.000），但效应很小：

| 干预层 | direction | mean p_true（−4 → +4） | flip@±4 | mean \|Δ\| vs random |
|---|---|---|---|---|
| L21 | probe | 0.384 → 0.406 | 1.0% / 1.0% | 0.005 vs 0.003 |
| L23 | probe | **0.369 → 0.423** | 1.5% / **3.0%** | **0.014 vs 0.003（4.7×）** |
| L15+L21+L23 联合 | probe | **0.332 → 0.462** | **5.0% / 4.5%** | 0.063 vs 0.003 |

联合干预把效应放大到 13 pt / flip 5%，约是单层 L23 的 4.5 倍 ⇒ 因果效应**分布在多层**，单层干预会低估它；但 ±4σ 也只翻转 5% 样本，方向是「真实但部分」的因果因素。

**（h）机制：探针不在 head 的 letter 子空间里（K=5，`U = W[A..E]`）。**

| representation | full-h probe | 仅用 K=5 head 基（$h U^T$） | 投影掉 head 子空间后 | $\cos(w_{\mathrm{probe}},\, u_{\mathrm{true}}-u_{\mathrm{false}})$ |
|---|---|---|---|---|
| final(post-norm) | 0.923 | 0.826 | 0.921 | 0.065 |
| L21 | **0.931** | 0.843 | **0.931** | 0.009 |
| L23 | 0.929 | 0.826 | 0.928 | 0.001 |
| L15 | 0.930 | 0.614 | 0.929 | 0.005 |

只用 head 的 K 个 letter 方向做特征只有 0.614–0.843（L15 最低 0.614，final/L23 0.826，L21 0.843），这正是「嘴」的上界；把该子空间投影掉后 probe 几乎不掉（0.931→0.929），且探针方向与 `u_true−u_false` 几乎正交 ⇒ **模型用来输出 A/B/C/D 的那组方向，几乎不承载它内部可线性解码的真值信息**。这是 readout gap 的机制解释。

### 3.3 反直觉 / 负结果

1. **没有「格式不变的单方向判断向量」（本条判负）。** 同格式内 Q2 都能读（T1 0.916、T1b 0.909），但跨选项顺序迁移：T1→T1b **0.472**（AUROC 0.414）、T1b→T1 **0.257**（AUROC 0.189），都低于随机。类别均值方向余弦仅 **0.154**；只做每格式中心化也修不好（0.442 / 0.254），所以不是简单的 offset。而模型自己的零样本语义预测跨选项顺序一致率 **0.940**（同位置率 0.060）——**行为是语义不变的，线性表示不是**。
2. **「中心化/共享结构」不足以救它。** 两个格式上训出的 LR 权重余弦其实有 0.817，说明共享结构存在，只是这个结构**不承载类别顺序**；因此「换模板还能用」不能靠减去均值实现。
3. **格式增广至少需要 2 个排列。** 留出排列上的 probe：K=2 只有 1 个训练排列所以 0.662，K≥3 到 0.858–0.889。产品化含义是「要么固定部署模板，要么训练时混多个排列」。
4. **K 变大不是更好。** acc_dc 从 K=2 的 0.839 单调降到 K=5 的 0.818，ECE 从 0.063 涨到 0.099；K 换来的只是读出上限（probe 0.913→0.923）与 `noul` 接口。
5. **严格化对照会让 gap 缩水三分之一。** 拿 Q0′ 当对手是 +13.9 pt，换成同监督的 Q0-cal 后是 +9.4 pt。**报 gap 必须报同监督版本**，否则是把「多用了标签」算成「多读了信息」。
6. **`companies` 子集上 Q2 < 嘴**（0.780 vs 0.825）。gap 不是全局性质，按数据集平均会掩盖这一点。
7. **因果效应弱于相关效应。** 探针读出 0.93，但 ±4σ 干预只翻转 3–5% 样本：方向被模型使用，但远不是「唯一决定项」，所以 JEV 头更适合**读出/校准**，不适合强干预。

## 4. 结论与判定

**判定：部分完成。** 首轮 pilot（S0/S1 + H2/H1/H5）与第二轮机制探索（K 扫描、ensemble、stacking、noul、steering、head-subspace）全部跑完并给出可判结论；instruct 模型、全量 13k、9B、`score` 原语与外部有效性未做。

**可写（支持的结论）**：

1. **严格 readout gap 成立**：Q2 0.916 acc / 0.966 AUROC，比**同监督**的 Q0-cal（0.822 / 0.934）高 **+9.4 pt [+7.6, +11.3]**、AUROC +0.032 [+0.023, +0.042]；且 P0 = 0.513、Z = 0.497 ± 0.015 排除词袋与容量伪迹。条件：Qwen3-1.7B-Base / 英文配对陈述 / `T1/answer` / 末位单点读出。
2. **gap 的机制是「嘴的方向不对」**：只用 LM head 的 K 个 letter 方向做特征只有 0.614–0.843，投影掉 letter 子空间后 probe 不掉（0.931→0.929），cos ≈ 0.001–0.065。
3. **`noul` 有表示层基础**：显式 unknown 选项的 mass 对 head 错误的 AUROC **0.835**（K=3），80% 覆盖下 acc 从 0.839 升到 **0.902**（AURC 0.046）。
4. **头 + 探针 stacking 是当前最优配方**：K=5 下 0.921 acc / 0.970 AUROC / 0.033 ECE，在 pilot 范围内优于任一单臂。

**不可写（诚实边界）**：

1. **不能说存在「通用判断向量」或「格式不变的方向」**：跨选项顺序迁移 0.472 / 0.257，余弦 0.154，中心化修不好。
2. **不能外推到 instruct / 更大模型 / 中文 / 多 token 计算**：只跑了 1.7B base、英文、1876 条、单点读出；9B fp16 ≈ 18 G 放不进 11 G 卡。
3. **不能把探针方向说成「因果判断方向」**：steering 在 L23 只把 p_true 推 5.4 pt、flip 3%，三层联合 13 pt / 5% ⇒ 真实但部分。
4. **不能声称复现了 JEV 三原语**：只做了 `choice`（+ 作为第三选项的 `noul`），`score`/序数原语未做，也没有 JevBench 之类的外部集。

**对后续决策的含义**：继续，但把「格式不变性」当作一等公民——要么固定部署模板、要么训练时混多个排列；下一步优先跑 instruct（真实 JEV 接口的决策点是 assistant header）与全量 13k 压 CI，而不是继续找新读出。

## 5. 踩坑与修正

| 现象 | 根因 | 解法 |
|---|---|---|
| 在 1080 Ti 上用 bf16 直接崩/退化 | Pascal（CC 6.1）不支持 bf16 | 全程 `dtype=torch.float16`，并在报告里固定精度 |
| 受限 softmax 读到错误的 token | `" True"` 与 `"True"` 是不同 id；标签实际带前导空格 | 先跑「标签单 token 检查」，用模板里真实出现的 id（` A`=362、` B`=425） |
| 中英标签 token 数不一致 | `正确/错误` 可能被切成 2 个 token | 只取单 token 标签，或整串 log-prob 长度归一化；本轮准备了多套 label set |
| gap 被高估 | 只跟零参数的 Q0′ 比，等于把「多用了标签」算成信息 | 加**同监督**的 Q0-cal 作严格分母（+13.9 pt → +9.4 pt） |
| 探针准确率虚高 | `h_T` 维度高、样本少，探针容量可能背下任务 | P0（词袋）与 Z（标签置换）双门禁；Z = 0.497 ± 0.015 |
| 想用「删掉某方向」证明必要性 | 重拟合的探针能从正交补恢复信息 | 必要性用 steering 因果检验，不用单方向消融 |
| 只读最后一层差点漏掉真信号 | 末层反而略降（final 0.916 vs L23 0.934） | 层扫描；K=4 重扫把峰值定在 L21（0.931） |
| 格式增广后仍不可用 | K=2 只有 1 个训练排列 | K≥3 至少两个排列；增广后 0.858–0.889 |
| 按数据集平均看不出崩塌 | cities 0.990 掩盖 neg_cities 的 Q0′ 0.195 | 逐数据集报表，gap 只看否定/比较类 |
| 文档里「已知局限」与结果冲突 | `prompt-jev/README.md` 仍写「未做 steering / 只读末位」，而第二轮已做 | 以 `PROMPT-JEV-PLAN.md` §15 与 `out/*/report.md` 为准 |

## 6. 未做 / 下一步

| 未做 | 原因 |
|---|---|
| instruct 模型（chat template 的 assistant header 作决策点） | 权重未下/未跑；这是「真实 JEV 接口」的第一步 |
| 全量 13k 与 9B | 9B fp16 ≈ 18 G > 11 G，需 4090；全量只为压 CI |
| `score` 原语（序数回归 / `{1..5}` 期望） | pilot 只做了 `choice`（+`noul` 弃权） |
| CoT / 多 token 计算后的读出 | 本轮只有末位单点，「生成对但读出不对」的样本未单独分析 |
| 中文 / 跨语言迁移 | 只用到带 `cn` cue 的模板，没有中文数据集 |
| JevBench 等外部有效性 | 无公开可比集，只有自建 held-out |
| bootstrap 次数、逐臂 CI | 源文档**未记录**，只给了配对差值的 CI |

下一步的性价比排序：① instruct + chat template 决策点（最容易翻掉 base 的结论）；② 全量 13k 压 CI（K=3 走 `noul`、K=2 走稳定性）；③ 把「≥2 个排列的格式增广」做成标准训练配方；④ 只有前三步都稳，才谈打包成三原语头。

## 7. 证据与产物

| 路径（相对 `autodl/`） | 说明 |
|---|---|
| `PROMPT-JEV-PLAN.md` | 设计与预注册判据；§14 首轮结果、§15 第二轮（K/ensemble/noul/steering） |
| `prompt-jev/README.md` | 文件职责、环境、复现命令、两轮关键数字（局限段已过期） |
| `prompt-jev/jevlib.py` / `extract.py` / `analyze.py` | 模板/token/指标库、`h_T` 抽取、Q0–Q2/P0/Z 分析与报告 |
| `prompt-jev/out/rep_strict2/report.md` | **首轮主报告**：16 组合零样本、读出族、配对 CI、格式迁移、逐数据集、样例 |
| `prompt-jev/out/optk_report/report.md` | K=2..5 扫描 + 各 rotation 细节 |
| `prompt-jev/out/opt4_report/report.md` | A/B/C/D 四选项一轮：选项顺序不变性、探针、层扫描、distractor 诊断 |
| `prompt-jev/out/optk_ens/report.md` | 排列 ensemble + 头/探针 stacking |
| `prompt-jev/out/noul/report.md` | `noul` 弃权：neutral mass / entropy / margin 的 AUROC、覆盖率、AURC |
| `prompt-jev/out/steer/report.md` / `steer_joint/report.md` | L21/L23 单层与 L15+L21+L23 联合 steering 的剂量-响应 |
| `prompt-jev/out/head_subspace/report.md` | 探针 vs LM head letter 子空间的对齐/投影残差 |
| `INDEX.md` | 资产索引第 51 行：prompt-jev pilot 与首轮结论 |
