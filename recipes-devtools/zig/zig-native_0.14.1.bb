SUMMARY = "Zig programming language compiler - native"
DESCRIPTION = "Zig is a general-purpose programming language and toolchain for maintaining robust, optimal, and reusable software."
HOMEPAGE = "https://ziglang.org/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

DEPENDS = "clang-native cmake-native ninja-native python3-native zlib-native zstd-native"

SRCREV = "d03a147ea0a590ca711b3db07106effc559b0fc6"
SRC_URI = "git://github.com/ziglang/zig.git;protocol=https;branch=0.14.x"

S = "${WORKDIR}/git"

inherit cmake

EXTRA_OECMAKE = " \
    -DCMAKE_PREFIX_PATH='${STAGING_LIBDIR_NATIVE}/llvm;${STAGING_DIR_NATIVE}' \
    -DZIG_STATIC_LLVM=ON \
    -DZIG_STATIC_ZLIB=ON \
    -DZIG_STATIC_ZSTD=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DZIG_TARGET_MCPU=baseline \
    -G Ninja \
"

# Zig needs a lot of memory during compilation
PARALLEL_MAKE = "-j 1"

do_install() {
    install -d ${D}${bindir}
    install -m 755 ${B}/zig ${D}${bindir}/zig
    
    # Install lib directory for zig std library and builtin modules
    if [ -d "${B}/lib" ]; then
        cp -r ${B}/lib ${D}${prefix}/
    fi
}

BBCLASSEXTEND = "native"

# Zig is architecture-specific
INSANE_SKIP:${PN} = "arch"
