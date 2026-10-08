SUMMARY = "Zig programming language compiler - native"
DESCRIPTION = "Zig is a general-purpose programming language and toolchain for maintaining robust, optimal, and reusable software."
HOMEPAGE = "https://ziglang.org/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d934d7758eb646c9c6a2162d88427689"

DEPENDS = "zig-llvm-native python3-native zlib-native zstd-native"

# Zig's canonical source is Codeberg (github.com/ziglang/zig is a stale
# mirror). Preserve this 0.16.x-era commit, retained under pull-request refs
# rather than a current 0.16.x branch. Validate the exact SRCREV in any ref.
# The 0.16.0 tag itself had a std bug (os/emscripten.zig STOPSIG declared u32
# but returns the SIG enum) that broke wasm32-emscripten builds.
# Zig 0.16 statically links LLVM/Clang/LLD 21, supplied only by the private
# zig-llvm-native dependency. Wrynose's ordinary LLVM 22 is not a substitute.
SRCREV = "7056ba9a5c750305726be862a51ff18e2318c138"
SRC_URI = "git://codeberg.org/ziglang/zig.git;protocol=https;nobranch=1 \
           file://0001-fix-zig-wasm2c-path.patch \
           file://0002-cmake-select-private-LLVM-toolchain.patch"

# Wrynose's git fetcher unpacks into BB_GIT_DEFAULT_DESTSUFFIX = BP.
S = "${UNPACKDIR}/${BP}"

inherit cmake native

ZIG_LLVM_PREFIX = "${STAGING_LIBDIR_NATIVE}/zig-llvm-21"

EXTRA_OECMAKE = " \
    -DCMAKE_PREFIX_PATH='${ZIG_LLVM_PREFIX}' \
    -DZIG_LLVM_PREFIX='${ZIG_LLVM_PREFIX}' \
    -DZIG_LLVM_CONFIG_EXECUTABLE='${ZIG_LLVM_PREFIX}/bin/llvm-config' \
    -DZIG_USE_LLVM_CONFIG=ON \
    -DZIG_STATIC_LLVM=ON \
    -DZIG_STATIC_ZLIB=ON \
    -DZIG_STATIC_ZSTD=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DZIG_TARGET_MCPU=baseline \
"

# Zig needs a lot of memory during compilation
# PARALLEL_MAKE = "-j 1"

do_install() {
    install -d ${D}${bindir}
    install -m 755 ${B}/stage3/bin/zig ${D}${bindir}/zig

    # The standard library is required, not an optional installation artifact.
    cp -R ${B}/stage3/lib ${D}${prefix}/
}


# Zig is architecture-specific
INSANE_SKIP:${PN} = "arch"
