SUMMARY = "Zig programming language compiler - native"
DESCRIPTION = "Zig is a general-purpose programming language and toolchain for maintaining robust, optimal, and reusable software."
HOMEPAGE = "https://ziglang.org/"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://LICENSE;md5=d934d7758eb646c9c6a2162d88427689"

DEPENDS = "clang-native cmake-native ninja-native python3-native zlib-native zstd-native"

# Zig's canonical source is now Codeberg (github.com/ziglang/zig is a stale
# mirror). Pinned to the 0.16.x branch HEAD (0.16.0 release + stabilization
# fixes) -- the 0.16.0 tag itself had a std bug (os/emscripten.zig STOPSIG
# declared u32 but returns the SIG enum) that broke wasm32-emscripten builds.
# Zig 0.16 statically links LLVM/clang/lld 21 (see PREFERRED_VERSION_clang*
# in meta-zig/conf/layer.conf, which selects the vendored LLVM-21 clang recipe).
SRCREV = "7056ba9a5c750305726be862a51ff18e2318c138"
SRC_URI = "git://codeberg.org/ziglang/zig.git;protocol=https;branch=0.16.x \
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
