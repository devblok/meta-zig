SUMMARY = "Zig programming language compiler - native"
DESCRIPTION = "Zig is a general-purpose programming language and toolchain for maintaining robust, optimal, and reusable software."
HOMEPAGE = "https://ziglang.org/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d934d7758eb646c9c6a2162d88427689"

DEPENDS = "clang-native cmake-native ninja-native python3-native zlib-native zstd-native"

SRCREV = "d03a147ea0a590ca711b3db07106effc559b0fc6"
SRC_URI = "git://github.com/ziglang/zig.git;protocol=https;branch=0.14.x \
           file://0001-fix-zig-wasm2c-path.patch"

S = "${WORKDIR}/git"

inherit cmake native

DEPENDS = "clang-native cmake-native ninja-native python3-native zlib-native zstd-native"

EXTRA_OECMAKE = " \
    -DCMAKE_PREFIX_PATH='${STAGING_DIR_NATIVE}' \
    -DZIG_STATIC_LLVM=ON \
    -DZIG_STATIC_ZLIB=ON \
    -DZIG_STATIC_ZSTD=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DZIG_TARGET_MCPU=baseline \
    -G Ninja \
"

# Zig needs a lot of memory during compilation
# PARALLEL_MAKE = "-j 1"

do_install() {
    install -d ${D}${bindir}
    install -m 755 ${B}/stage3/bin/zig ${D}${bindir}/zig
    
    # Install lib directory for zig std library and builtin modules
    if [ -d "${B}/stage3/lib" ]; then
        cp -r ${B}/stage3/lib ${D}${prefix}/
    fi
}


# Zig is architecture-specific
INSANE_SKIP:${PN} = "arch"
