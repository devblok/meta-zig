# meta-zig

OpenEmbedded/Yocto layer for the Zig programming language.

This layer provides:
- Native Zig 0.15.1 compiler built from source using meta-clang's LLVM 20.1.1
- `zig.bbclass` for building Zig projects with full cross-compilation support
- Integration with Yocto's build system and staging areas
- Extended LLVM target support for comprehensive cross-compilation
- Example projects demonstrating Zig integration patterns

## Quick Start

```bash
# Add layer to bblayers.conf
bitbake-layers add-layer /path/to/meta-zig

# Build Zig compiler
bitbake zig-native

# Test with example
bitbake hello-zig
```

## Requirements

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended for parallel builds)
- **Disk Space**: ~2GB additional for LLVM with all targets
- **Build Host**: x86_64 architecture (for native compiler bootstrap)
- **Network**: Internet access for source downloads

### Yocto/OpenEmbedded Compatibility
| Yocto Release | Status | Notes |
|---------------|--------|-------|
| Scarthgap (5.0) | ✅ Supported | Tested primary target |
| Styhead (5.1) | ✅ Supported | Current development |
| Walnascar (6.0) | ✅ Supported | Future release |

## Dependencies

### Layer Dependencies
Add these layers to your `bblayers.conf` in order:

```bash
BBLAYERS += " \
    /path/to/openembedded-core/meta \
    /path/to/meta-openembedded \
    /path/to/meta-clang \
    /path/to/meta-zig \
"
```

**Required layers:**
- **meta-clang**: LLVM/Clang infrastructure (must support LLVM 20.1.1+)
- **openembedded-core**: Base OE functionality  
- **meta-openembedded**: Additional build tools

### Build Dependencies
Automatically resolved by recipes:
- `clang-native` (LLVM 20.1.1)
- `cmake-native`, `ninja-native`
- `python3-native`
- `zlib-native`, `zstd-native`

### LLVM Target Support
This layer extends meta-clang to build LLVM with all Zig-required targets:

**Standard**: AArch64, ARM, X86, PowerPC, RISCV, Mips  
**Extended**: AMDGPU, AVR, BPF, Hexagon, Lanai, MSP430, NVPTX, Sparc, SystemZ, VE, WebAssembly, XCore, LoongArch, SPIRV

## Building Zig Projects

### Basic Recipe Template

```bitbake
SUMMARY = "My Zig application"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=..."

SRC_URI = "https://github.com/user/project.git;protocol=https;branch=main"
SRCREV = "..."

inherit zig

# Optional: customize build
ZIG_BUILD_MODE = "ReleaseFast"
ZIG_BUILD_ARGS = "-Denable-feature=true"
```

### Zig Class Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZIG_BUILD_MODE` | `ReleaseSafe` | Optimization mode: `Debug`, `ReleaseSafe`, `ReleaseFast`, `ReleaseSmall` |
| `ZIG_TARGET` | Auto-detected | Cross-compilation target (e.g., `aarch64-linux-gnu.2.31`) |
| `ZIG_BUILD_ARGS` | Empty | Additional arguments to `zig build` |
| `ZIG_CACHE_DIR` | `${WORKDIR}/.zig-cache` | Per-recipe cache directory |
| `ZIG_GLOBAL_CACHE_DIR` | `${TMPDIR}/zig-cache` | Global cache for artifacts |

### Advanced Build Configuration

```bitbake
# Custom build.zig arguments
ZIG_BUILD_ARGS = " \
    -Dtarget-cpu=cortex-a53 \
    -Denable-lto=true \
    -Duse-system-libs=false \
"

# Override target for specific architecture
ZIG_TARGET = "aarch64-linux-musl"

# Custom cache locations
ZIG_CACHE_DIR = "${WORKDIR}/my-cache"
ZIG_GLOBAL_CACHE_DIR = "${TMPDIR}/shared-zig-cache"
```

## Project Structure Requirements

### Minimal Project
```
my-zig-project/
├── build.zig          # Zig build script
├── src/
│   └── main.zig       # Main source file
└── LICENSE
```

### Example build.zig
```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "my-app",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });

    b.installArtifact(exe);
}
```

## Cross-Compilation

### Automatic Target Detection
The layer automatically maps OE architecture variables to Zig targets:

| OE Architecture | Zig Target |
|----------------|------------|
| `x86_64` | `x86_64-linux-gnu.2.31` |
| `aarch64` | `aarch64-linux-gnu.2.31` |
| `arm` | `arm-linux-gnueabihf.2.31` |
| `mips64` | `mips64-linux-gnu.2.31` |
| `riscv64` | `riscv64-linux-gnu.2.31` |

### Manual Target Override
```bitbake
# Force specific target
ZIG_TARGET = "aarch64-linux-musl"

# Target with specific CPU
ZIG_BUILD_ARGS = "-Dcpu=cortex_a72"
```

## Performance Optimization

### Build Performance
```bash
# In local.conf - adjust based on system resources
PARALLEL_MAKE = "-j 8"

# Zig-specific optimizations
ZIG_GLOBAL_CACHE_DIR = "/tmp/zig-cache"  # Use fast storage
```

### Memory Management
```bash
# For systems with limited RAM
PARALLEL_MAKE = "-j 2"

# Monitor memory usage during builds
bitbake -v zig-native 2>&1 | grep -E "(memory|RAM|swap)"
```

## Testing and Validation

### Build Test Suite
```bash
# Test native compiler
bitbake zig-native

# Test example application
bitbake hello-zig

# Test cross-compilation (if applicable)
MACHINE=raspberrypi4-64 bitbake hello-zig

# Test on target
runqemu core-image-minimal
```

### Validation Commands
```bash
# Verify Zig installation
oe-run-native zig-native zig version

# Check supported targets
oe-run-native zig-native zig targets

# Test compilation
oe-run-native zig-native zig run hello.zig
```

## Version Information

- **Zig Version**: 0.15.1
- **LLVM Version**: 20.1.1 (from meta-clang)
- **Minimum Yocto**: Scarthgap (5.0)
- **Layer Version**: Compatible with LAYERSERIES_COMPAT

## Advanced Usage

### Custom Zig Recipes

```bitbake
# Recipe with external dependencies
SUMMARY = "Zig project with C library"
DEPENDS += "openssl zlib"

inherit zig

# Pass library paths to Zig
ZIG_BUILD_ARGS = " \
    -Dsystem-ssl=${STAGING_DIR_TARGET}${includedir} \
    -Dsystem-zlib=${STAGING_DIR_TARGET}${libdir} \
"
```

### Integration with Yocto SDK

```bash
# Generate SDK with Zig support
bitbake -c populate_sdk core-image-minimal

# In SDK environment
source environment-setup-*
zig build -Dtarget=$ZIG_TARGET
```

## License

MIT License - See LICENSE file for details.
