# Zig build system integration for OpenEmbedded/Yocto
#
# This class provides support for building Zig projects with the Zig build system (build.zig)
#

# Set default toolchain to zig
TOOLCHAIN_zig = "zig"

# Zig compiler and build tool
ZIG = "${STAGING_BINDIR_NATIVE}/zig"

# Default build mode
ZIG_BUILD_MODE ??= "ReleaseSafe"

# Target architecture for cross-compilation
ZIG_TARGET ??= "${@zig_target_map(d)}"

# Build directory
B ?= "${WORKDIR}/build"

# Zig build arguments
ZIG_BUILD_ARGS ??= ""

# Additional zig build arguments
EXTRA_ZIGBUILD ??= ""

DEPENDS:append = " zig-native"

def zig_target_map(d):
    """Map OE target architecture to Zig target triple"""
    import re
    
    target_arch = d.getVar('TARGET_ARCH')
    target_os = d.getVar('TARGET_OS')
    target_vendor = d.getVar('TARGET_VENDOR') or 'unknown'
    
    # Map common architectures
    arch_map = {
        'x86_64': 'x86_64',
        'i686': 'i386',
        'i586': 'i386',
        'i486': 'i386',
        'aarch64': 'aarch64',
        'arm': 'arm',
        'armeb': 'armeb',
        'mips': 'mips',
        'mipsel': 'mipsel',
        'mips64': 'mips64',
        'mips64el': 'mips64el',
        'powerpc': 'powerpc',
        'powerpc64': 'powerpc64',
        'riscv32': 'riscv32',
        'riscv64': 'riscv64',
    }
    
    zig_arch = arch_map.get(target_arch, target_arch)
    
    # Map OS
    os_map = {
        'linux': 'linux',
        'mingw32': 'windows',
        'darwin': 'macos',
    }
    
    zig_os = os_map.get(target_os, target_os)
    
    # For now, assume GNU ABI for Linux
    if zig_os == 'linux':
        return f"{zig_arch}-{zig_os}-gnu"
    else:
        return f"{zig_arch}-{zig_os}"

zig_do_configure() {
    bbnote "Configuring Zig build"
    
    if [ ! -f "${S}/build.zig" ]; then
        bbfatal "No build.zig found in ${S}"
    fi
    
    # Create build directory
    mkdir -p ${B}
}

zig_do_compile() {
    bbnote "Compiling with Zig build system"
    bbnote "Using Zig: ${ZIG}"
    bbnote "Target: ${ZIG_TARGET}"
    bbnote "Build mode: ${ZIG_BUILD_MODE}"
    
    cd ${S}
    ${ZIG} build \
        --prefix-exe-dir ${B}/bin \
        --prefix-lib-dir ${B}/lib \
        --prefix-include-dir ${B}/include \
        -Doptimize=${ZIG_BUILD_MODE} \
        -Dtarget=${ZIG_TARGET} \
        ${ZIG_BUILD_ARGS} \
        ${EXTRA_ZIGBUILD}
}

zig_do_install() {
    bbnote "Installing Zig project"
    
    # Install binaries
    if [ -d "${B}/bin" ]; then
        install -d ${D}${bindir}
        install -m 755 ${B}/bin/* ${D}${bindir}/
    fi
    
    # Install libraries
    if [ -d "${B}/lib" ]; then
        install -d ${D}${libdir}
        cp -r ${B}/lib/* ${D}${libdir}/
    fi
    
    # Install headers
    if [ -d "${B}/include" ]; then
        install -d ${D}${includedir}
        cp -r ${B}/include/* ${D}${includedir}/
    fi
}

# Export the functions
EXPORT_FUNCTIONS do_configure do_compile do_install

# Default task dependencies
do_configure[depends] += "zig-native:do_populate_sysroot"