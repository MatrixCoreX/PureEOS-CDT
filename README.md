# PureEOS CDT

[简体中文](#简体中文) · [English](#english)

## 简体中文

**PureEOS CDT** 是独立维护的智能合约开发工具链与 SDK。当前发行版本为 **1.0.0**；既有 1.0.0 制品此前以 **AIC CDT 1.0.0** 发布，保留原文件名、目录及校验摘要。

本项目独立制定技术路线。版本见 [VERSION](VERSION)，依赖基线见 [UPSTREAM_BASELINE.json](UPSTREAM_BASELINE.json)。该发行与 PureEOS 2.0.0 并行首版配套验收；SDK 和完整源码在[联合发行页](https://github.com/MatrixCoreX/PureEOS/releases/tag/v2.0.0)提供。使用来源清单和 SHA256SUMS 核对工具链、SDK 运行库及匹配合约。开发分支、历史候选与稳定制品分别记录。

当前加固范围是固定上游后端、重建工具前端，以及 SDK 头文件和运行库加固。LLVM 主版本迁移和完整编译器现代化另行规划。修复与发布门槛见 [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md)，1.0.0 的历史发行身份见 [AIC_CDT_1.0.0_IDENTITY.md](AIC_CDT_1.0.0_IDENTITY.md)。

### 开发回归

从仓库根目录运行，输出写入新的独立目录：

```sh
python3 -m unittest discover -s tests/hardening -p 'test_*.py' -v
python3 tests/hardening/run_native_tests.py --output /path/to/new-native-results
python3 tests/hardening/run_toolchain_suite.py --sdk /path/to/sdk --output /path/to/new-toolchain-results
python3 tests/hardening/run_sdk_native_units.py --sdk /path/to/sdk --output /path/to/new-sdk-unit-results
```

原版失败对照须指定独立、未修改的上游源码目录：

```sh
python3 tests/hardening/run_native_tests.py --baseline /path/to/unmodified-cdt --output /path/to/new-comparison-results
```

整体验收还包括真实 WASM 和节点检查。`run_wasm_checks.py`、`build_system_contracts.py` 和 `run_system_check.py` 须显式提供节点源码、程序、SDK 或系统合约目录；参数见各自 `--help`。验收绑定同一最终候选的源码、工具链、程序和合约摘要，并保留失败记录。

### 打包与安装身份

开发候选使用 `tests/hardening/package_sdk_candidate.py` 打包，参数见 `--help`。它将测试 SDK 的绝对链接转为独立文件，保留工具、脚本和第三方许可证，并按 CMake 文件自身位置定位 SDK。

打包验证包括实际搬迁后的 CMake、工具链、原生 SDK、真实合约编译对照，以及解压后生成/构建、已有文件保护和确定性归档。该开发入口不生成稳定标签。稳定包在节点联合验收完成后独立生成，保持已验收编译器、库和头文件字节，仅更新来源记录与发行说明。

项目生成器：

```sh
cdt-init --project=NAME --path=/path/to/existing-parent
```

它创建新项目并拒绝覆盖已有目录。新项目使用现代 CMake，通过 `CMAKE_PREFIX_PATH` 选择 SDK。**PureEOS CDT** 是当前项目名称；已发布 1.0.0 工具的版本输出、`aic-cdt-1.0.0` 安装目录及旧报告保留当时的 AIC CDT 身份，以便复核原制品。

### 来源与许可

自有原创部分见 [AIC 开源许可 1.0](AIC_LICENSE.md)，适用范围见 [LICENSING.md](LICENSING.md)。继承的 CDT 和第三方代码保留原版权与许可，详见 [LICENSE](LICENSE) 和各组件目录。[继承的历史 README](docs/INHERITED_README.md) 仅作来源参考。项目改名不改变继承代码的授权范围。

---

## English

**PureEOS CDT** is an independently maintained smart-contract development toolchain and SDK. The current release is **1.0.0**. Existing 1.0.0 artifacts were published as **AIC CDT 1.0.0** and retain their original filenames, directories, and checksums.

The project maintains its own technical roadmap. See [VERSION](VERSION) for the release version and [UPSTREAM_BASELINE.json](UPSTREAM_BASELINE.json) for pinned dependencies. This release was jointly qualified with the first parallel release of PureEOS 2.0.0. The SDK and complete sources are available on the [joint release page](https://github.com/MatrixCoreX/PureEOS/releases/tag/v2.0.0). Verify the toolchain, SDK runtime libraries, and matching contracts against the provenance manifests and SHA256SUMS. Development branches, historical candidates, and stable artifacts retain separate identities.

Current hardening covers a pinned upstream backend, rebuilt tool frontends, and SDK headers/runtime libraries. LLVM major-version migration and broader compiler modernization are separate work. See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for fixes and release gates, and [AIC_CDT_1.0.0_IDENTITY.md](AIC_CDT_1.0.0_IDENTITY.md) for the historical 1.0.0 release identity.

### Development regression checks

Run from the repository root and use new, independent output directories:

```sh
python3 -m unittest discover -s tests/hardening -p 'test_*.py' -v
python3 tests/hardening/run_native_tests.py --output /path/to/new-native-results
python3 tests/hardening/run_toolchain_suite.py --sdk /path/to/sdk --output /path/to/new-toolchain-results
python3 tests/hardening/run_sdk_native_units.py --sdk /path/to/sdk --output /path/to/new-sdk-unit-results
```

An original-version failure comparison requires a separate, unmodified upstream source directory:

```sh
python3 tests/hardening/run_native_tests.py --baseline /path/to/unmodified-cdt --output /path/to/new-comparison-results
```

Full qualification also includes real WASM and node checks. `run_wasm_checks.py`, `build_system_contracts.py`, and `run_system_check.py` require explicit node-source, program, SDK, or system-contract paths; see each script's `--help`. Qualification binds source, toolchain, program, and contract hashes to the same final candidate and preserves failed attempts.

### Packaging and installation identity

Package development candidates with `tests/hardening/package_sdk_candidate.py`; see `--help`. It replaces absolute links in the test SDK with independent files, preserves tools, scripts, and third-party licenses, and locates the SDK relative to its CMake files.

Package checks cover relocation, CMake, toolchain execution, native SDK tests, real-contract compilation comparisons, unpacked project generation/builds, existing-file protection, and deterministic archives. This development entry point does not create stable tags. Stable packages are generated separately after joint node qualification, retaining the qualified compiler, library, and header bytes while updating provenance and release notes.

Project generator:

```sh
cdt-init --project=NAME --path=/path/to/existing-parent
```

It creates a new project and rejects an existing destination. Generated projects use modern CMake and select the SDK through `CMAKE_PREFIX_PATH`. **PureEOS CDT** is the current project name. Version output from published 1.0.0 tools, the `aic-cdt-1.0.0` installation directory, and historical reports retain their original AIC CDT identity so those artifacts remain verifiable.

### Provenance and licenses

Original work is covered by the [AIC Open Source License 1.0](AIC_LICENSE.md); see [LICENSING.md](LICENSING.md) for scope. Inherited CDT and third-party code retain their copyrights and licenses; see [LICENSE](LICENSE) and component directories. The [inherited historical README](docs/INHERITED_README.md) is a provenance reference. Renaming the project does not change inherited licensing terms.
