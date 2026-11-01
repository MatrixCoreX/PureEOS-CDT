# PureEOS CDT

[简体中文](#简体中文) · [English](#english)

## 简体中文

**PureEOS CDT 1.0.0** 是 PureEOS 智能合约开发工具链和 SDK，提供 C/C++ 合约编译、WASM 链接、ABI 生成、项目生成器及合约运行库。

### 安装和使用

从 [PureEOS CDT 最新发行](https://github.com/MatrixCoreX/PureEOS-CDT/releases/tag/pureeos-v1.0.0)或 [PureEOS 联合发行](https://github.com/MatrixCoreX/PureEOS/releases/latest)下载 SDK、源码和 SHA256SUMS。核验下载后解压：

```bash
sha256sum -c SHA256SUMS --ignore-missing
tar -xzf pureeos-cdt-1.0.0-linux-x86_64.tar.gz
export PATH="$PWD/pureeos-cdt-1.0.0/bin:$PATH"
export CMAKE_PREFIX_PATH="$PWD/pureeos-cdt-1.0.0${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
cdt-cpp --version
cdt-init --project=hello --path="$PWD"
cmake -S hello -B hello-build
cmake --build hello-build --parallel 2
```

SDK 根目录为 `pureeos-cdt-1.0.0`。项目生成器创建新目录并拒绝覆盖已有项目。当前工具版本输出和部分 CMake 标识为 `AIC CDT 1.0.0` / `cdt`；对外产品名称为 PureEOS CDT。以发行清单、版本及摘要识别工具链。

配套PureEOS1.0.0使用CPU16、NET4MiB、状态库16GiB，包含7天升级审查和永久黑名单不占位/递补。[完整基线](https://github.com/MatrixCoreX/PureEOS/blob/v1.0.0/docs/BASELINE.md)。

### Ubuntu 支持和配套节点

Ubuntu **24.04 LTS**、**26.04 LTS** 和 **26.10** 的 SDK 工具、实际合约编译、ABI 及原生 SDK 检查见 [兼容性报告](https://github.com/MatrixCoreX/PureEOS/blob/main/docs/ubuntu/COMPATIBILITY_20261030.md)。报告区分使用 SDK 编译合约、重编 SDK 组件和完整 LLVM 后端构建，系统支持以实际检查范围为准。

合约使用配套 [PureEOS](https://github.com/MatrixCoreX/PureEOS) 节点。系统合约构建须保留单选投票、出块/确认/轮岗、BP 发现与维护、10%/90% 资源模式、奖励及治理设置。RAM 通过 `setramrate(1024)` 初始化；延迟交易禁用。

### 从当前源码开发和验证

新开发从 `develop` 开始。合约编译使用上面的 SDK 和 CMake 步骤；也可直接编译单个合约：

```bash
cdt-cpp -abigen -contract=hello -o hello.wasm hello.cpp
```

工具链自身的完整源码构建入口是根目录 `CMakeLists.txt`，先取得仓库固定的 LLVM、musl、libc++ 和 SoftFloat 子模块。完整 LLVM 后端重建未包含在本轮 Ubuntu 兼容性资格中；构建前应按依赖源码准备适配的主机编译器和 CMake。当前 SDK 的实际合约编译与运行检查已单独记录。完整源码构建流程为：

```bash
git clone --branch develop https://github.com/MatrixCoreX/PureEOS-CDT.git
cd PureEOS-CDT
git submodule update --init --recursive
sudo apt-get install -y build-essential git python3-venv zlib1g-dev libtinfo-dev
python3 -m venv .venv-cdt-build
. .venv-cdt-build/bin/activate
python3 -m pip install 'cmake==3.28.3'
cmake -S . -B build/cdt -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_TESTS=OFF -DCMAKE_INSTALL_PREFIX="$PWD/sdk-build"
cmake --build build/cdt --parallel 2
cmake --install build/cdt
```

该源码入口包含编译器后端、工具前端及运行库；当前 CMake 安装子目录为 `sdk-build/aic-cdt`。上述虚拟环境固定使用 CMake 3.28.3，供依赖子项目共同使用；直接源码重建的环境和结果应另行验收。测试输出使用新的独立目录：

```bash
git clone --branch develop https://github.com/MatrixCoreX/PureEOS-CDT.git
cd PureEOS-CDT
python3 -m unittest discover -s tests/hardening -p 'test_*.py' -v
python3 tests/hardening/run_native_tests.py --output /path/to/new-native-results
python3 tests/hardening/run_toolchain_suite.py --sdk /path/to/pureeos-cdt-1.0.0 --output /path/to/new-toolchain-results
python3 tests/hardening/run_sdk_native_units.py --sdk /path/to/pureeos-cdt-1.0.0 --output /path/to/new-sdk-unit-results
```

`run_wasm_checks.py`、`build_system_contracts.py`、`run_system_check.py` 和 `package_sdk_candidate.py` 提供 WASM、系统合约、节点整合及 SDK 打包入口，参数见各自 `--help`。验证应绑定同一候选的源码、工具链、运行库、节点和合约摘要，并包含实际编译、搬迁、运行及错误拒绝。

### 许可

见 [AIC_LICENSE.md](AIC_LICENSE.md)、[LICENSING.md](LICENSING.md)、[LICENSE](LICENSE) 和各组件的版权及第三方声明。

---

## English

**PureEOS CDT 1.0.0** is the smart-contract toolchain and SDK for PureEOS. It provides C/C++ contract compilation, WASM linking, ABI generation, a project generator and contract runtime libraries.

### Install and use

Download the SDK, source and SHA256SUMS from the [latest PureEOS CDT release](https://github.com/MatrixCoreX/PureEOS-CDT/releases/tag/pureeos-v1.0.0) or the [joint PureEOS release](https://github.com/MatrixCoreX/PureEOS/releases/latest). Verify downloads, extract the SDK and use the commands above to configure PATH, CMAKE_PREFIX_PATH and a generated project.

The SDK directory is `pureeos-cdt-1.0.0`. The generator creates a new project and refuses to overwrite an existing destination. Current tool version output and some CMake identifiers are `AIC CDT 1.0.0` / `cdt`; the product name is PureEOS CDT. Identify the toolchain using its release manifest, version and hashes.

### Ubuntu support and matching node

The [compatibility report](https://github.com/MatrixCoreX/PureEOS/blob/main/docs/ubuntu/COMPATIBILITY_20261030.md) records SDK execution, real contract compilation, ABI checks and native SDK tests on Ubuntu **24.04 LTS**, **26.04 LTS**, and **26.10**. It distinguishes compiling contracts with the SDK, rebuilding SDK components and rebuilding the complete LLVM backend. Support claims follow the recorded scope.

Use the matching [PureEOS](https://github.com/MatrixCoreX/PureEOS) node. System-contract builds retain single-choice voting, proposer/finalizer/rotation, BP discovery and maintenance, the 10%/90% resource model, rewards and governance. Initialize RAM growth with `setramrate(1024)` and keep deferred transactions disabled.

### Develop and verify current source

Start new development from `develop`. To compile a single contract using the installed SDK:

```bash
cdt-cpp -abigen -contract=hello -o hello.wasm hello.cpp
```

For a CMake project, add the SDK's `bin/` directory to PATH and its root to CMAKE_PREFIX_PATH, then run:

```bash
cdt-init --project=hello --path="$PWD"
cmake -S hello -B hello-build
cmake --build hello-build --parallel 2
```

The root `CMakeLists.txt` builds the complete toolchain, including its backend, frontends and libraries. First fetch the pinned LLVM, musl, libc++ and SoftFloat submodules and prepare a host compiler and CMake compatible with those sources:

```bash
git clone --branch develop https://github.com/MatrixCoreX/PureEOS-CDT.git
cd PureEOS-CDT
git submodule update --init --recursive
sudo apt-get install -y build-essential git python3-venv zlib1g-dev libtinfo-dev
python3 -m venv .venv-cdt-build
. .venv-cdt-build/bin/activate
python3 -m pip install 'cmake==3.28.3'
cmake -S . -B build/cdt -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_TESTS=OFF -DCMAKE_INSTALL_PREFIX="$PWD/sdk-build"
cmake --build build/cdt --parallel 2
cmake --install build/cdt
```

The current CMake install subdirectory is `sdk-build/aic-cdt`. The virtual environment pins CMake 3.28.3 for the dependency subprojects as well. A complete LLVM backend rebuild is outside this campaign's Ubuntu qualification; its environment and results require separate qualification. SDK contract compilation and execution are recorded separately.

Use the regression commands above and new, isolated output directories. `run_wasm_checks.py`, `build_system_contracts.py`, `run_system_check.py` and `package_sdk_candidate.py` provide WASM, system-contract, node-integration and SDK-packaging checks; consult their `--help` output. Qualification binds source, toolchain, runtime libraries, node and contract hashes to the same candidate and includes actual compilation, relocation, execution and expected error rejection.

### Licenses

See [AIC_LICENSE.md](AIC_LICENSE.md), [LICENSING.md](LICENSING.md), [LICENSE](LICENSE), component copyrights and third-party notices.
