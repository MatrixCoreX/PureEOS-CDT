# AIC CDT 1.0.0：独立发行身份

2026-10-23。AIC 是基于 EOSIO / Antelope 技术开发的独立新项目。

自有工具链名称为 **AIC CDT**，版本为 **1.0.0**。唯一版本输入为仓库根目录
`VERSION`，CMake 和打包工具都从该文件读取；`UPSTREAM_BASELINE.json` 单独
记录上游编译器基线及固定依赖提交。自有发行版本不表示上游版本被追溯修改。

当前改动包括：

- `CMakeLists.txt` / `modules/AICCDTVersion.cmake`：项目身份、版本、安装目录、包名与厂商；版本格式在实际 CMake 和 Python 路径中一致检查。
- `cdt-cc`、`cdt-cpp`、`cdt-ld`、`cdt-abidiff`、`cdt-init`：对外版本输出为 `AIC CDT 1.0.0 (工具名)`，保留现有命令入口便于合约工程使用。
- 编译器选项新增 `__aic_cdt__`、`__aic_cdt_major__`、`__aic_cdt_minor__`、`__aic_cdt_patchlevel__`；当前工具链版本数字均从1.0.0生成。
- CMake导出 `AIC_CDT_PRODUCT_NAME` 与 `AIC_CDT_VERSION`，配套系统合约构建要求 AIC CDT 1.0.x。
- 归档目录为 `aic-cdt-1.0.0`，开发候选包名为 `aic-cdt-1.0.0-candidate.tar.gz`，来源记录为 `AIC_CDT_PROVENANCE.json`。
- 继承的构建/发布工作流同步匹配 `aic-cdt` 包名和新的工件名称；YAML语法已检查，实际GitHub工作流尚未执行，不算平台构建通过。

项目的 EOSIO / Antelope ABI、接口、命名空间和第三方组件各自保留其技术含义，
原始版权与许可证保留。旧的测试记录继续显示当时实际使用的编译器身份。

独立发展与原创内容的许可范围见 [LICENSING.md](LICENSING.md)；已新增
[AIC 开源许可 1.0](AIC_LICENSE.md)，不据此覆盖继承代码的 MIT 或组件许可。

40项控制已实际通过，包含真实编译的项目生成器、版本读取、安装归档权限、
覆盖拒绝和路径边界；这不是新版全部工具前端或节点联合验收通过声明。
五个前端正使用冻结的AIC源码与固定的LLVM/Clang库重建，后续必须核验实际
`--version`、真实合约编译、WASM/ABI和系统合约摘要对照、搬迁安装与节点运行。
打包入口要求显式 `--frontend-evidence` 和对应程序摘要，旧前端不能仅靠新包名
通过打包门槛。当前仍为未发布候选，与并行首版共同验收、共同发布。
