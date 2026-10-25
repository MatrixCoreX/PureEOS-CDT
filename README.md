# AIC CDT

AIC 独立项目的智能合约开发工具链与 SDK，本发行版本为 **1.0.0**。
本项目独立维护、独立制定技术路线。自有发行版本见 [VERSION](VERSION)，
依赖基线见 [UPSTREAM_BASELINE.json](UPSTREAM_BASELINE.json)。
本标签与 PureEOS 2.0.0 并行首版配套验收，SDK和完整项目源码在
[联合发行页](https://github.com/MatrixCoreX/PureEOS/releases/tag/v2.0.0)提供。
使用该页的来源清单和 SHA256SUMS 核对工具链、SDK运行库和匹配合约；
开发分支与历史候选包仍保留各自身份，不替代本发行。

本轮修复及发布门槛见 [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)。目前采用
固定上游后端，重新构建AIC工具前端，并对 SDK 头文件及运行库进行加固和重编；不声称完成了 LLVM
主版本迁移或全编译器现代化，也不把修改后的 SDK 冒充官方未修改安装包。
自有版本配置、工具输出和新包验收安排见
[AIC_CDT_1.0.0_IDENTITY.md](AIC_CDT_1.0.0_IDENTITY.md)。

## 开发回归

从仓库根目录运行，所有输出使用新的独立目录，不覆盖既有结果：

```sh
python3 -m unittest discover -s tests/hardening -p 'test_*.py' -v
python3 tests/hardening/run_native_tests.py --output /path/to/new-native-results
python3 tests/hardening/run_toolchain_suite.py --sdk /path/to/sdk --output /path/to/new-toolchain-results
python3 tests/hardening/run_sdk_native_units.py --sdk /path/to/sdk --output /path/to/new-sdk-unit-results
```

原版失败对照必须显式指定独立、未修改的上游源码目录，不能用本仓库自身作为对照：

```sh
python3 tests/hardening/run_native_tests.py --baseline /path/to/unmodified-cdt --output /path/to/new-comparison-results
```

原生检查不能替代真实 WASM/节点验收。`run_wasm_checks.py`、
`build_system_contracts.py`、`run_system_check.py` 需要显式提供对应节点源码、
程序、SDK 或系统合约目录；各自 `--help` 列出参数。正式验收须绑定相同最终候选
的源码、工具链、程序与合约摘要，并保留失败记录。

开发候选打包使用 `tests/hardening/package_sdk_candidate.py`（参数见 `--help`）。
它将测试 SDK 的绝对链接转成独立文件，保留完整工具、脚本和第三方许可证，
并按 CMake 文件自身位置定位 SDK。打包必须经过实际搬迁后的 CMake、工具链、
原生 SDK 和真实合约编译对照；测试目录不能直接冒充可安装发行包。
该开发入口不生成稳定标签。本版的稳定包在最终节点联合验收通过后独立生成，
只更新来源记录和发行说明，编译器、库及头文件保持已验收字节。
发行工具显示`AIC CDT 1.0.0`，旧工具及报告保留原版本身份。
项目生成器 `cdt-init --project=NAME --path=/已存在的父目录` 只创建新项目，
拒绝覆盖已有目录。新项目支持现代 CMake，通过 `CMAKE_PREFIX_PATH` 选择 SDK。
打包还验证解压安装后的生成/构建、原文件保护和确定性归档，不把测试 staging
目录或已知失败的旧生成器直接交付为稳定版。

## 来源与许可

自有原创部分的授权方式见 [AIC 开源许可 1.0](AIC_LICENSE.md)，
具体适用范围见 [LICENSING.md](LICENSING.md)。
保留继承的 CDT/第三方源码和版权声明，许可见 [LICENSE](LICENSE) 及各组件目录。
[继承的历史 README](docs/INHERITED_README.md) 仅作来源参考，不是本仓库的当前
发行、安装或平台支持承诺。
