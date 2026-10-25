2026-10-23 18:34UTC补充：稀疏工作区不能代表完整Git工作流清单，现按工作区+
Git索引+明确删除联合检查，旧标签工作流已逐字节归档并标记从待提交树删除。
新增6项实际Git控制，本机71项Python全过；完整5768文件导出并在独立本地Git
仓库执行本入口，71项Python+4编译+12运行共17作业全过。完整源还原40份原稀疏
文件，四编译器子模块未构建，不称完整LLVM或最终GitHub远程CI通过。
节点工具检查另为466项固定三轮全过。原反例和删除补丁保留，旧两份归档未改写。
详见节点PX7_V1_SPARSE_WORKFLOW_REPAIR_20261024.md；以下原记录保留。

# AIC CDT 自动源码检查

当前 `.github/workflows/build.yaml` 对 Ubuntu 26.04 / 26.10 用户空间运行
`python3 -B tests/hardening/run_native_tests.py --output ci-results/sdk-native`。
构建机为标准 GitHub Ubuntu 24.04，每个用户空间单独一个容器；它们共用构建机内核。

入口安装 g++、CMake、Python、python3-yaml 和 Git，检出当前仓库，不拉取完整 LLVM
子模块或旧节点发行包。实际执行 hardening Python 检查，以及 SDK 序列化/分配器的
普通与 ASan/UBSan 编译，各运行三轮。源码执行前后摘要须不变，失败保留原始记录。

2026-10-23 16:35 UTC，本机同入口实际通过 56 项 Python 检查、4 次 C++ 编译和
12 次普通/ASan/UBSan 执行，共 17 个作业；本批未请求原版源码负对照。
新工作流的 actionlint 检查通过。旧两份配置已逐字节保存在
`ci-reference-20261024`，附有 SHA 清单，旧自动发行步骤未执行。

这只是 SDK 源码和原生专项检查，不是完整 LLVM/五前端重编、WASM 工具链语料、
完整 SDK 安装搬迁或节点联合验收。已有实际五前端/新 SDK/23 份合约证据保持各自
准确来源。最终提交后的 GitHub 远程运行、最终整合节点和联合正式发布仍待完成，
当前没有自动发布步骤。
