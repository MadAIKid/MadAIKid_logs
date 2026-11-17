---
id: INFRA
slug: 02-infra-toolchain
title: 运维工具链：一次判负、一台免费 GPU、一条不再覆盖已有内容的文档线
subtitle: AutoDL 实例 · 局域网 1080 Ti 工作机 · 飞书云文档与增量写入
date_start: 2026-10-05
date_end: 2026-11-17
status: 部分完成
verdict: Strata 判负（26 GiB < 27.6 GB）；1080 Ti 以 5,075 tok/s 承接探针，省下开机钱
tags: [运维, 工具链, 判负, 文档同步]
hardware: AutoDL RTX 4090 24G / 4080S 32G（按次租用）· 局域网 GTX 1080 Ti 11G
models: Qwen3.8-Flash-Next（仅调查，未下载）
datasets: —
source_docs: [COLD-START.md, HOST-<内网IP>.md, STRATA-<内网IP>.md, API-SKILL.md, API-NOTES-instance.md, FEISHU-DOCS.md, FEISHU-NOTES.md, AGENTS.md, INDEX.md, PROGRESS.md]
---

# 运维工具链：一次判负、一台免费 GPU、一条不再覆盖已有内容的文档线

> **一句话**：为了让实验能落地，先把执行面查清 —— AutoDL 实例（4090 24G / 50GB 数据盘 / 200GB 文件存储）
> 与局域网 GTX 1080 Ti 工作机（11G 显存 / 15GiB 内存 / 1.5T 数据盘）逐项实测 →
> 两个判负（Strata 在两台机器上都跑不起来；账户资金不够长跑），一个正收益（1080 Ti 以 5,075 tok/s 承接探针，
> 不必充值）→ 顺手把飞书写入从「读全文再整篇覆盖」改成「只发增量」。

## 0. 摘要

本线要回答的是**执行面问题**，不是模型问题：现有 AutoDL 实例能干什么、局域网那台 GTX 1080 Ti 能不能顶上、
Strata（Qwen3.8-Flash-Next 125B MoE 的本地推理方案）到底卡在哪、以及长跑日志怎么存才不丢。

结论分三块。**判负**：Strata 在 AutoDL 那台卡在磁盘（最大可写目录 50GB，官方要求约 80GB，且该机不支持扩容），
在局域网那台卡在内存（最小档 Gyro-S 需 27.6 GB 显存+内存合计，本机 11 GiB + 15 GiB ≈ 26 GiB）；
**正收益**：局域网 1080 Ti 实测 RWKV-7 162 M 前向 5,075 tok/s，10k prompt 状态抽取约 17 分钟，
把「先充值再跑探针」这个前置依赖直接消掉；**工程**：飞书云文档从整篇 `overwrite` 改成 `append` 增量写入，
配 Base 时间线做双视图，并沉淀出一条规则——判成功用 `ok == true` 而不是 `code == 0`。

| 实验 | 问题 | 结果 | 判定 |
|---|---|---|---|
| INFRA-a | 实例资产能否跨机共享？ | `autodl-fs` 17G→37G / 200G，重启与释放均不丢 | ✅ |
| INFRA-b | 公开 API 能否管现有实例？ | `instance/pro/list` 返回 `result_total=0` | ❌ 不覆盖普通实例 |
| INFRA-c | 1080 Ti 能否承接 RWKV-7 探针？ | 5,075 tok/s → 10k prompt ≈ 17 min | ✅ 免充值 |
| INFRA-d | 1080 Ti 能否跑 E1 的 9B judge？ | 9B fp16 ≈ 18 G > 11 G | ❌ 放不下 |
| INFRA-e | Strata 在 1080 Ti 上能跑吗？ | 26 GiB < Gyro-S 27.6 GB；`--check` exit 1 | ❌ 判负 |
| INFRA-f | 飞书四类操作 + 时间线可用？ | 存储/搜索/读取/修改全通；Base 3 视图 | ✅ |
| INFRA-g | 增量写入是否解决覆盖问题？ | 文档 rev 13、母本 154 行，不再读全文 | ✅ |

## 1. 问题与假设

**决策问题**（每条都对应「要不要花钱」）：

1. 要不要继续给 AutoDL 充值、租 4090？——需要知道现有实例状态、账户资金、以及 AutoDL 到底哪些能力有 API。
2. 有没有零租金的替代执行面？——局域网那台 GTX 1080 Ti 到底能跑什么、不能跑什么。
3. Strata（用户提出的"本地跑 Qwen3.8"方案）值不值得投入时间？——需要给出「跑不动」的硬门槛，而不是"试试看"。
4. 实验日志写到哪里、怎么写才不会互相覆盖？——飞书云文档 + 多维表格时间线。

**预注册判据**：

| 问题 | 判据 | 通过条件 |
|---|---|---|
| 1080 Ti 能否跑探针 | S1–S4 只需纯 PyTorch 前向 | 前向吞吐可测且状态可取出 |
| Strata 能否在 1080 Ti 跑 | 权重 GB ≤ RAM + VRAM 才算 fits（`fit_label.py`） | 最小档 27.6 GB ≤ 26 GiB |
| 增量写入是否更好 | 不读全文、不覆盖云端手工改动 | 只发本条增量且 rev 递增 |

**为什么怀疑已有做法**：旧同步脚本 `sync.sh` 的默认值是 `TOKEN="${2:-${DOC_TOKEN:-}}"`，
而项目 `targets.env` 永远有 `DOC_TOKEN` —— 意味着「新建文档」分支实际走不到，任何"新建"都会覆盖主文档。
这条不是猜的，是本轮真实发生并靠历史版本回滚恢复的事故（见 §5）。

## 2. 实验设置

### 2.1 环境

**（a）AutoDL 实例（普通容器实例，非 Pro）**

| 项 | 实测值 |
|---|---|
| 容器 | `autodl-container-252b4992ea-2d76f8e2` |
| OS / kernel | Ubuntu 22.04.5 / 5.15.0-91 |
| GPU | 1× RTX 4090 24 GB，驱动 595.71.05（空载） |
| CPU | Xeon Platinum 8352V，128 vCPU，支持 AVX-512（含 BW/VL/VNNI/VBMI） |
| 内存 | 755 GiB |
| 磁盘 | `/` overlay 30 GB · `/root/autodl-tmp` 50 GB（xfs, prjquota） · `/root/autodl-pub` 20 TB 只读 |
| 文件存储 | `/root/autodl-fs` 200 GB，同地区实例共享 |
| Python | **无系统 `python3`**，只有 `/root/miniconda3/bin/python3`（3.12.3），非登录 shell 不在 PATH |

另有一个按次租用的档位在实际跑实验时出现过：**RTX 4080 SUPER / 32 GB**（与文档里 4090-48G 的预期不符，已记录）。

**（b）局域网工作机（GTX 1080 Ti）** —— 全部 2026-10-08 当场命令输出：

| 项 | 值 |
|---|---|
| 系统 | Ubuntu 18.04.6 LTS（已 EOL） |
| CPU | Intel i5-7600K，4 核 4 线程 @3.8 GHz |
| 内存 | 15 GiB + 2 GiB swap |
| GPU | GTX 1080 Ti **11 GB**（11264 MiB），驱动 525.147.05，CUDA 12.0 |
| 架构 | compute capability (6,1) = Pascal，28 SM；**无 bf16、无 TF32** |
| 磁盘 | `/` 440 G 余 199 G · `/data` **1.8 T 余 1.5 T** |
| 算力 | 4096³ 矩阵乘：fp32 **9.63 TFLOP/s**，fp16 8.43 TFLOP/s |
| 环境 | conda env `ai`（py3.10.16 / torch 2.5.1+cu121）· `rwkv`（py3.12.8 / torch 2.2.2+cu121） |
| 缺失 | `nvcc`、`triton`、`fla` —— 且 sm_61 < sm_70，Triton 官方最低 CC 7.0 |

**（c）工具链** —— 官方 `lark-cli 1.0.97`（MIT）+ 随附 26 个 Agent Skills；`lark-cli` 的 workspace 由
`HERMES_HOME` 决定，`~/.local/bin` 里是 `lark` / `feishu-log` / `feishu-sync` / `feishu-msg` / `feishu-send` 的软链。

### 2.2 模型与数据

**本线不产出模型权重**，只把已有资产放到能被多台实例共享的位置：

| 资产 | 体积 | 说明 |
|---|---|---|
| `Qwen3.5-9B-Base` | 19 G | TQR-JEV 骨干（4090 上加载/生成已验证，23.6 tok/s） |
| `Qwen3-8B` | 16 G | 备用骨干 |
| `Qwen3.8-Flash-Next-GGUF` | 866 M | 仅 mmproj（Strata 用，**权重未下载**） |
| `NuminaMath-CoT` | 1.23 G | 859,494 行（增殖原料） |
| `PRM800K` | 488 M | 过程监督，md5 已校验 |
| `code/Stellan` | 2.2 M | 代码副本 |
| `code/rlcd-lite` | 1.9 M | RLCD 参考实现（commit `b0f981f`） |

校验方式：模型 14/14 文件与 hf-mirror 的 `Content-Length` 逐项一致；PRM800K 6/6 文件 md5 与本地 LFS 源一致；
`EXPERIMENT_PLAN.md` md5 `8437b58b9b7961d7b968652baad5c72e` 与本地一致。fs 用量早期 `17G/200G`，
当天 20:07 复核为 `37G/200G`（models 35 G · datasets 1.9 G）。

### 2.3 方法

1. **实例侧**：`bin/autodl` 包装器（固定仓库内 `ssh/config` + `known_hosts`，不写全局 `~/.ssh`）；
   API 侧用开发者 Token 打 `wallet/balance` 与 `instance/pro/list`，验证「公开 API 覆盖谁」。
2. **局域网侧**：实测 `pytest` 套件、4096³ 矩阵乘算力、RWKV-7 前向吞吐、`git status` 欠账盘点。
3. **Strata 侧**：把 v0.2.15（commit `c775728`）clone 到 `/tmp/strata-src/Strata`，
   读 `setup.py` 的 `MODELS` / `check` / `low_ram_fits` 与 `docs/{MODELS,OLDER_GPUS,GYRO}.md`，
   再用 10-08 的硬件实测数字算账（机器当天不在线，无法现场跑 `--check`）。
4. **文档侧**：`feishu-log` 一条命令同时做三件事 —— 本地母本 `>>` 追加、云文档 `--command append`、
   可选 Base `record-batch-create` 一条；`--force` 做重复保护（标题已在母本里则整条跳过）。

## 3. 结果

### 3.1 主结果

| 配置 | 指标 | 数值 | 95% CI | 判定 |
|---|---|---|---|---|
| 4090 实例 · Qwen3.5-9B 加载 | 显存占用 / 生成速度 | 18.8 G / 23.6 tok/s | 未记录 | ✅ |
| 1080 Ti · `rwkvstack` 测试 | 用例 | 33 passed in 82.09 s | — | ✅ |
| 1080 Ti · RWKV-7 162.2 M 前向 | 吞吐 | **5,075 tok/s**（18.27 M tok/h，807 ms/16×256） | 未记录 | ✅ |
| 1080 Ti · 状态存储 | 每样本 fp32 | 196,608 B（192 KB）→ 10k prompt ≈ 1.9 GB | — | ✅ |
| 1080 Ti · GPU 峰值显存 | 前向 | 1,296.7 MB | — | ✅ |
| 1080 Ti · 探针预算 | 10k prompt × 512 token = 5.12 M token | **≈ 17 分钟** | — | ✅ 免充值 |
| 1080 Ti · E1 9B judge | fp16 显存需求 | ≈ 18 G vs 11 G | — | ❌ 放不下 |
| AutoDL API | 账户资金 | **< ¥20**（不足 4090 跑 8 小时） | — | ❌ 硬约束 |
| AutoDL API | Pro 实例列表 | `code=Success` 但 `result_total=0` | — | ❌ 不覆盖普通实例 |
| Strata · 1080 Ti 最小档 | Gyro-S 需 27.6 GB（VRAM+RAM） vs 本机 ≈26 GiB | 差约 1.6 | — | ❌ |
| Strata · 1080 Ti 常规最小档 | Coder `IQ1_M` 29.6 GB / 官方 RAM ≥ 32 GB | — | — | ❌ |
| Strata · AutoDL 4090 | 最大可写目录 50 GB vs `Q2_0` need ≈114 GB | — | — | ❌ |
| 飞书 · 四类操作 | 建文档 / 搜索 / 读取 / 修改 | rev 3→4（append）、4→6（overwrite） | — | ✅ |
| 飞书 · 增量写入 | 文档 rev / 母本行数 | rev=13 / 154 行 | — | ✅ |

补充：`Q2_0` 之所以最费盘，是 `setup.py:3410` 对 `model == "Q2_0" and avx512 and family == "qwen"` 额外预留 40 GB，
而那台 4090 机的 Xeon 8352V 恰好支持 AVX-512，所以「最快档」反而成了需求最大的一档。

### 3.2 对照与消融

**（a）两台机器的出网能力是互补的，不是同一套**

| 目标 | Mac | 1080 Ti 工作机 |
|---|---|---|
| `hf-mirror.com` | ✅ 通 | ❌ 超时 |
| `modelscope.cn` | — | ✅ 302 |
| `github.com` | ✅ | ✅ 200 但慢（8.4 s 握手） |
| `huggingface.co` | 直连不通 | ❌ Connection refused |

推论：下载前必须先确认目标站在**当前这台机器**上可达，不能把一台机器的线路经验搬到另一台。

**（b）存储层级与生命周期**（决定"东西放哪"）

| 位置 | 容量/价格 | 关机 | 释放实例 |
|---|---|---|---|
| 系统盘 `/` | 30 GB 不可扩（Pro 可扩到 500 GB，**不可缩**） | 保留 | **清空** |
| 数据盘 `/root/autodl-tmp` | 50 GB 免费；扩容 ¥0.0066/GB/日 | 保留 | **清空** |
| 文件存储 `/root/autodl-fs` | 200 GB；¥0.01/GB/日（20 GB 内免费） | 保留 | **保留** |

同一份 80 GB 放一年：数据盘扩容 ≈ ¥72（但连续关机 15 天随实例释放被清）vs `autodl-fs` ≈ ¥219（不会）——
**便宜买不到长期**，这是本线最重要的一条存储结论。挂载点还因机器而异：westc 是 `/root/autodl-fs`，
westb 是 `/autodl-fs/data`，换机时必须先确认。

**（c）实例档位对照**

| 档位 | 代价 | 副作用 |
|---|---|---|
| 普通实例 | 免费 50 GB 数据盘、本地 NVMe | 无 API、GPU 不足时可能开不了机、连续关机 15 天释放 |
| 容器实例 Pro | 有 API、关机 60 天释放 | 只有系统盘（网络存储、IO 更慢）、只要存在就每天至少扣 ¥0.1 |
| 无卡模式 | ¥0.1/h（本次约 40 min ≈ ¥0.07） | **1 CPU 核 + cgroup 内存 2 GB**（`memory.max=2147483648`）——4B 模型加载会静默 OOM |

**（d）增量写入 vs 整篇覆盖**

| 层 | 旧做法 | 新做法 |
|---|---|---|
| 本地母本 | 读全文 → 编辑 → 写回 | `>>` 追加 |
| 飞书文档 | `docs +update --command overwrite` | `--command append`（只发这一条） |
| 多维表格 | 手工拼 JSON | `record-batch-create` 追加一条 |

`feishu-sync` 从「默认覆盖」降级为「首次建档 / 母本大改后重建」，不传 `--doc` / `--default` 时走 `docs +create`。

### 3.3 反直觉 / 负结果

1. **Strata 判负的瓶颈不是显卡**。直觉上 11 GB 显存跑不动 125B MoE 是"显卡不够"，
   实测卡点是 **15 GiB 系统内存**：最小档要 27.6 GB（显存+内存合计），本机合计 ≈26 GiB；
   官方 `--check` 直接判 `This PC cannot run Strata yet`（exit 1），且 `any_fits` 不把 `mem_total` 类的 Gyro 计入。
   low-RAM 兜底也不够：`ram-6 + (vram-5-MTP) ≈ 14.5 < Coder arena 23.4`。
2. **磁盘不是所有机器的瓶颈**。AutoDL 那台是磁盘（50 GB < 80 GB 需求，且不支持扩容）；
   1080 Ti 那台是内存（1.5 T 余量对 58–84 GB 下载完全够）。同一份"能不能跑"的结论，两台机器的死因相反。
3. **「4090-48G 约 ¥3.03/h」这条成本口径没能用上**：账户资金 < ¥20，连 8 小时都跑不了；
   忘关一天 ≈ ¥73 的说法在本线只作为风险提示，没有真实账单支撑。
4. **飞书「授权成功 ≠ 权限齐全」**：`auth login` 返回 `ok` 的同时可能带 `warning.type = missing_scope`；
   本轮实测仍是 **155 个 scope**，`im:message.send_as_user` / `wiki:node:update` /
   `contact:user.base:readonly` / `base:workflow:delete` 均缺失，发消息只能继续走 Open API 应急通道。
5. **公开 API 不覆盖普通实例**：`instance/pro/list` 返回 `result_total=0` 不是"没有实例"，
   而是「现有实例是普通容器实例，不在 Pro API 管辖内」——差点被误读为实例已释放。
6. **位置/端口随时会变**：实例停止后 SSH 端口即失效（`kex_exchange_identification`），开机换新端口；
   切有卡模式也会换端口。这条不能当作故障，但会反复消耗排查时间。

## 4. 结论与判定

- **判定：部分完成**。执行面事实已查清并留下可复核证据；两个方向判负（Strata、AutoDL 长跑）、
  一个替代执行面确认可用（1080 Ti + 纯 PyTorch）、工具链改造完成。
- **可写（支持的结论）**：
  1. **Strata 在 1080 Ti 工作机上跑不起来，硬约束是 15 GiB 内存**：最小档 Gyro-S 需 27.6 GB（显存+内存合计），
     本机合计 ≈26 GiB；另有驱动 525 < 575.51、Pascal 实验路径、Ubuntu 18.04 三条次要门槛。
  2. **Strata 在 AutoDL 那台 4090 上跑不起来，硬约束是磁盘**：官方要求约 80 GB 单可写目录，
     该机最大可写目录 50 GB，且用户确认不支持扩容。
  3. **1080 Ti 足以承接 RWKV-7 探针**：162.2 M 前向 5,075 tok/s，10k prompt × 512 token ≈ 17 分钟，
     状态 1.9 GB；前提是走**纯 PyTorch**路径（sm_61 用不了 Triton/FLA），且 CPU 密集型部分会被 19 天的长任务挤。
  4. **增量写入解决了"每写一条都要读全文"的问题**，且默认值不再是破坏性的（`feishu-sync` 不传 token 走 create）。
- **不可写（诚实边界）**：
  1. **不能**说"局域网机可以替代 AutoDL"：9B fp16 ≈18 G > 11 G，E1 的 LLM-judge 与 Strata 都不行；
     它只顶掉了「探针」这一段。
  2. **不能**说"Strata 升级后就能跑"：升到 ≥32 GB 内存 + 驱动 580 只够跑最小档，
     Pascal 是官方明说的实验路径（很多开关"未在 CC 6.1 实测"），且引擎包 glibc 下限在 18.04 上**未验证**。
  3. **不能**说"飞书权限已配齐"：权限层仍缺「列出/移除协作者」4 组 scope，消息链路仍靠应急通道。
  4. **不能**说"17 min/10k prompt 是端到端探针成本"：这是前向吞吐换算值，不含数据加载、落盘与 CPU 争抢的实测。
- **对后续决策的含义**：探针线继续（零租金）；AutoDL 只在需要 9B 及以上模型时开机，且开机前必须先解决账户资金；
  Strata 计划停在这里，不再尝试下载。

## 5. 踩坑与修正

| 现象 | 根因 | 解法 |
|---|---|---|
| `source /etc/network_turbo` 后 GitHub / HF 仍 HTTP 000 | 该实例上加速代理已不生效（与 `COLD-START.md` §4 记载不符） | 可行线路只剩 hf-mirror；文档结论标记为**时效性失效** |
| 同一文件不同 Range 速度差 100 倍（31 KB/s vs 3.9 MB/s） | 限速是**按字节段**而非按文件 | `curl -C -` 分段续传，越过慢段后回升（实测 8.6 MB/s） |
| 文件字节数与 HF API 的 `size` 对不上（差 733 KB） | API 元数据会过期 | 校验一律以实际 `Content-Length` 为准 |
| `npm` 报 `EPERM ... root-owned files` | **误导**：真因是沙箱不允许写工作区外，`~/.npm` 属主正常 | 先跑 `touch ~/.dsh-write-test` 验证沙箱，**不要** `sudo chown` |
| `lark-cli` 报 `not configured`（配置齐全） | workspace 由 `HERMES_HOME` 决定，未设时落到 `local` | 封装 wrapper 固定 `HERMES_HOME`；单用 `--profile` 无效 |
| `keychain not initialized` | 沙箱挡住 macOS 钥匙串，**不是**凭证过期 | 放宽文件策略即可；报错先怀疑策略，再怀疑凭证 |
| `str_replace` 改了但回读没变（`$?` 仍 0） | 按文本 run 匹配，跨格式边界会失败；`degrade_code=1013` 时退出码仍是 0 | 判成功读 `result`/`data` 字段；格式问题走 `block_replace` |
| `sync.sh <file>` 未传第二参数 → 覆盖了主文档 | 旧版默认值 `TOKEN="${2:-${DOC_TOKEN:-}}"`，`targets.env` 永远有 `DOC_TOKEN` | `docs +history-list` 取版本号 → `history-revert` 恢复；全局版改为默认 `create` |
| 脚本报 `TITLE?: unbound variable`，但写入已经发生 | bash 把 `$VAR` 紧跟的全角字符首字节并入变量名 | 一律写 `${VAR}`；写操作后不要放可能失败的展开（本次因此多出一条重复 Base 记录，已删） |
| `base +record-list` 查不到刚写的记录 | `--page-size N` 是**从表头开始**的第一页；`--format json` 下记录在 `data` 数组本身 | 放大 page-size 或翻页；按 `data['items']` 解析会得 0 条 |
| 无卡模式装环境时 4B 模型静默 OOM | cgroup 仍是 2 GB / 0.5 核 | 装环境用无卡模式，跑模型前切有卡 |
| `web_fetch` 全部失败（non-public IP） | 本机 DNS 把域名解析到 `198.18.0.0/15` | 改用 bash 的 `curl` 做事实核查 |
| 远端长任务挂住 ssh | 会话被前台进程占住 | `setsid nohup … &` 起任务 + 另开会话轮询日志 |

## 6. 未做 / 下一步

1. **账户资金**：需要先充值（当前 < ¥20，不足 4090 跑 8 小时），这是 AutoDL 侧最硬的约束；充值前不开机。
2. **普通实例 API 不可用**：创建/开关/查询只能走控制台或 SSH，无法用 token 自动化；
   若要自动化得换容器实例 Pro（代价见 §3.2c）。
3. **Strata 未现场复核**：1080 Ti 那台在判定当天不在线（ping 不通、ARP incomplete），
   硬件数字取自 10-08 清单；机器开机后可 `./setup.sh --check` 复跑（注意 `--check` **不检查磁盘空间**）。
4. **飞书权限缺口**：4 组 scope 需在开发者后台补齐并**发布版本**后重新授权；`im` 类 scope 缺失导致消息仍走应急通道。
5. **`autodl-fs` 用量口径已过时**：2026-10-26 起模型改为默认落实例本地数据盘（`/root/autodl-tmp`，
   Pro 数据盘已扩容、当前 250 G），`autodl-fs` 只保留作跨实例中转/备份；§2.2 的清单是 10 月初的历史状态。
6. **局域网机的欠账未清**：`rwkvstack` 有大批未提交成果（最后一次实验 09-02 09:21，pyramid 0.74 / equal 0.49 / flat 0.25），
   与该仓库 README 的「进展必须落在提交历史」相悖；此项零算力成本但需要用户拍板。
7. **长期保留策略未执行**：公开权重不值得付费归档（记 repo id + revision/commit + SHA 即可），
   真正该付费保存的是自训 checkpoint、自建数据集与日志——这条只是结论，尚未落成流程。

## 7. 证据与产物

| 路径（相对 `autodl/`） | 说明 |
|---|---|
| `COLD-START.md` | 实例硬件/磁盘/网络实测 + Strata 装不下的调查 + 存储层级与生命周期（§10） |
| `API-SKILL.md` | AutoDL 开发者 API 速查（账户资金/Pro 实例端点）+ 实测记录 |
| `API-NOTES-instance.md` | 「公开 API 不覆盖普通实例」+ 停止状态的三个后果 |
| `HOST-<内网 IP>.md` | 1080 Ti 工作机全量盘点：硬件/软件/出网/能力表/两个坑 |
| `STRATA-<内网 IP>.md` | Strata 判定页：官方内存要求表、源码依据、三条次要门槛、升级路径 |
| `FEISHU-DOCS.md` | 飞书规范：全局落点、凭证与沙箱、增量优先、文档注册表、Base 时间线、权限现状 |
| `FEISHU-NOTES.md` | 飞书踩坑与决策记录：13 类真实报错 → 根因 → 解法 |
| `AGENTS.md` | 仓库常驻铁律：模型落本地盘、下载选源/校验、远程执行姿势、踩坑清单 |
| `INDEX.md` | 导航与当前状态；`autodl-fs` 资产清单与 10-26 存放口径修订 |
| `PROGRESS.md` | 逐日证据：10-05 / 10-06 / 10-07 / 10-08 / 11-16 / 11-17 各节 |

> 说明：局域网工作机的文档以该机内网 IP 命名，本仓库对外发布时统一写成 `HOST-<内网 IP>.md`。

按日期可复核的关键节点：

```text
2026-10-05  资产入 autodl-fs（17G/200G），network_turbo 失效
2026-10-06  账户资金 <¥20；Pro API result_total=0；实例停止
2026-10-07  lark-cli 1.0.97 落地，四类文档操作跑通（rev 3→6）
2026-10-08  Base 时间线（3 视图/11 条）；增量写入改造（rev=13）；1080 Ti 盘点
2026-11-16  Strata 判负（26 GiB < 27.6 GB）；AutoDL 实例关机连不上
2026-11-17  实例失联→重置后数据盘完好；收工 shutdown，结果归档 8.4 MB / 54 文件
```
