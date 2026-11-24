# RNA-seq 批量分组方法（2026-11-23）

> 隶属计划 `20261123-ppgr-rnaseq-curation`。计数是 **experiment 数、未剔单细胞的上界**
> （单细胞 RNA-seq 用户 2026-11-23 明确定不要，策展时按 STANDARD.md §3.8 剔除，行数以策展结果为准）。

## 计数方法

表上 taxid → NCBI taxonomy 规范名核对 → `txid + RNA-Seq[Strategy]` esearch。实验数 ≠ run 数（多 run 实验会让 run 数更高），GSA-only 还会再加。

## 分组原则

- 实验数最大的物种各成一组；其余按 experiment 数贪心均分，每组总量均衡。
- 分组按 experiment 数与物种数双维均衡：物种数过多的一组，即使 experiment 数均衡，逐物种抓属性、建缓存的开销也会倾斜——两维同时看，单组物种数异常时拆分。
- 分组清单（每组物种 + 计数 + taxid + 规范名 + name_match）是本地输入，不进仓库。

## 命名陷阱（先定名再策展）

- 表上 taxid 与接受名不一致（name_match=false）的物种，按接受名重查，计数仅作体量参考。
- 两个物种共用一个表上 taxid：表本身可能写错了，策展时须按接受名重查（见 PITFALLS #10）。
- 杂交种无独立 taxid：按杂交名/亲本双通道查；0 计数不等于无数据（见 PITFALLS #11）。
- 表上无 taxid 的物种按名解析；试点已解决的接受名陷阱见 PITFALLS #1。

## NCBI 计数 0 的物种

仍需走 ENA/GSA/文献查一遍再定 0。若三源皆无，JSON 记 0 行 + EVIDENCE.md 写明查过。

## 执行方式

- 每组一个策展人，按试点方法（NCBI 为主、ENA 按项目补拉、逐物种 diff、接受名先行、SAMD 走 ENA、GSA 的 CRR 枚举走浏览器）逐物种出 JSON + EVIDENCE.md。
- 多组并行；逐组亲手复核（结构/计数/sha256/四元组/抽查）后再汇总总报告。
- 单组最大的活若想先放一放或分阶段，可以在确认时说。
