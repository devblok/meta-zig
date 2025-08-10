# meta-zig

OpenEmbedded/Yocto layer for the Zig programming language.

This layer provides:
- Native Zig compiler built from source using meta-clang's LLVM 19.1.7
- `zig.bbclass` for building Zig projects
- Integration with Yocto's cross-compilation system
- Extended LLVM target support for comprehensive cross-compilation

## Requirements

### System Requirements
- Minimum 8GB RAM (16GB recommended for parallel builds)
- Sufficient disk space for LLVM with all targets (~2GB additional)
- x86_64 build host (for native compiler bootstrap)

### Yocto/OpenEmbedded Requirements
- **Yocto Version**: Scarthgap (5.0) or later
- **Compatible Releases**: Scarthgap, Nanbield, future LTS releases

## Dependencies

### Layer Dependencies (Required)
- **meta-clang**: Provides LLVM/Clang infrastructure
  - Must support LLVM 19.1.7 or compatible
  - This layer extends meta-clang with additional LLVM targets required by Zig
- **openembedded-core**: Base OE functionality
- **meta-openembedded**: Additional tools and libraries

### Build Dependencies (Automatically Handled)
- `clang-native`: Native LLVM/Clang compiler (19.1.7)
- `cmake-native`: CMake build system
- `ninja-native`: Ninja build tool
- `python3-native`: Python 3 interpreter
- `zlib-native`: Compression library
- `zstd-native`: Zstandard compression

### LLVM Target Requirements
This layer automatically configures meta-clang to build LLVM with all targets required by Zig:
- **Standard targets**: AArch64, ARM, X86, PowerPC, RISCV, Mips
- **Additional targets**: AMDGPU, AVR, BPF, Hexagon, Lanai, MSP430, NVPTX, Sparc, SystemZ, VE, WebAssembly, XCore, LoongArch

**Note**: The `clang_git.bbappend` in this layer extends the default LLVM target list from meta-clang to ensure Zig has access to all required compilation targets.

## Usage

Add this layer to your `bblayers.conf`:

```
BBLAYERS += "/path/to/meta-zig"
```

### Building Zig Projects

Use the `zig` class in your recipes:

```bitbake
inherit zig

SRC_URI = "https://github.com/example/zig-project.git"
```

The class expects a `build.zig` file in the source directory.

## Setup Instructions

### 1. Add Layer Dependencies
Ensure all required layers are in your `bblayers.conf`:

```
BBLAYERS += " \
    /path/to/openembedded-core/meta \
    /path/to/meta-openembedded \
    /path/to/meta-clang \
    /path/to/meta-zig \
"
```

### 2. Build Native Zig Compiler
```bash
bitbake zig-native
```

### 3. Test with Example Recipe
```bash
bitbake hello-zig
```

## Configuration

### Recipe Variables
- `ZIGVERSION`: Zig version to use (default: 0.14.1)
- `ZIG_BUILD_MODE`: Build optimization mode (default: ReleaseSafe)
- `ZIG_TARGET`: Target architecture (auto-detected from OE variables)

### Global Configuration
Add to `local.conf` if needed:
```bash
# Enable Zig in images
IMAGE_INSTALL:append = " hello-zig"

# Debug symbols (optional)
EXTRA_IMAGE_FEATURES += "debug-tweaks"
```

## Troubleshooting

### Common Issues

**1. "LLVM missing target" errors during zig-native build**
- Solution: The `clang_git.bbappend` should automatically fix this
- Verify meta-zig layer is properly added and has priority

**2. CMake infinite loop during configuration**
- Cause: Incomplete LLVM target configuration
- Solution: Clean and rebuild clang-native: `bitbake -c cleanall clang-native && bitbake clang-native`

**3. Memory issues during build**
- Increase available RAM or reduce parallelism: `PARALLEL_MAKE = "-j 2"`
- Consider building on a machine with more resources

**4. Cross-compilation target not found**
- Ensure the target architecture is supported by both Yocto and Zig
- Check `ZIG_TARGET` mapping in `zig.bbclass`

### Getting Help
- Check build logs: `bitbake -v zig-native`
- Examine CMake configuration: Look in `tmp/work/*/zig-native/*/build/`
- Report issues with full build logs and system information
