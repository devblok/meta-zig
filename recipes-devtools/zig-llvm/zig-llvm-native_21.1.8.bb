# Private native dependency for the pinned Zig compiler, not a clang provider.
# Source/patch provenance: the LLVM 21.1.8 monolith vendored in this layer
# from meta-clang walnascar. Do not inherit its target/SDK/shared-source suite.
SUMMARY = "Private LLVM, Clang and LLD static libraries for Zig"
HOMEPAGE = "https://llvm.org/"
LICENSE = "Apache-2.0-with-LLVM-exception"
LIC_FILES_CHKSUM = " \
    file://llvm/LICENSE.TXT;md5=8a15a0759ef07f2682d2ba4b893c9afe \
    file://clang/LICENSE.TXT;md5=ff42885ed2ab98f1ecb8c1fc41205343 \
    file://lld/LICENSE.TXT;md5=ae7dc7c027b1fa89b5b013d391d3ee2b \
"

SRC_URI = " \
    https://github.com/llvm/llvm-project/releases/download/llvmorg-${PV}/llvm-project-${PV}.src.tar.xz \
    file://0001-llvm-use-OE-compression-library-names.patch \
"
SRC_URI[sha256sum] = "4633a23617fa31a3ea51242586ea7fb1da7140e426bd62fc164261fe036aa142"
S = "${UNPACKDIR}/llvm-project-${PV}.src"

DEPENDS = "python3-native zlib-native zstd-native"

inherit cmake python3native native

# Keep tools, headers, libraries, CMake exports and data below one private
# prefix, including after sstate relocation into a consumer's native sysroot.
ZIG_LLVM_PREFIX = "${STAGING_LIBDIR_NATIVE}/zig-llvm-21"
prefix = "${ZIG_LLVM_PREFIX}"
exec_prefix = "${prefix}"
bindir = "${prefix}/bin"
sbindir = "${prefix}/sbin"
libexecdir = "${prefix}/libexec"
libdir = "${prefix}/lib"
includedir = "${prefix}/include"
datadir = "${prefix}/share"
sysconfdir = "${prefix}/etc"
sharedstatedir = "${prefix}/com"
localstatedir = "${prefix}/var"
SYSROOT_DIRS = "${ZIG_LLVM_PREFIX}"
SYSROOT_DIRS_NATIVE = ""

# A binary llvm-config relocates itself using its executable location; never
# run the text-file sstate substitution over it.
SSTATE_SCAN_FILES:remove = "*-config"

OECMAKE_SOURCEPATH = "${S}/llvm"
TOOLCHAIN = "gcc"

# Install the native tools as well as the libraries so every executable named
# by LLVM/Clang/LLD's CMake exports is present in the private sysroot subtree.
# All default LLVM 21 targets (including ARM and SPIRV) are required by Zig.
EXTRA_OECMAKE = " \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    -DLLVM_BUILD_LLVM_DYLIB=OFF \
    -DLLVM_LINK_LLVM_DYLIB=OFF \
    -DCLANG_BUILD_CLANG_DYLIB=OFF \
    -DCLANG_LINK_CLANG_DYLIB=OFF \
    -DLLVM_ENABLE_PROJECTS='clang;lld' \
    -DLLVM_ENABLE_RUNTIMES='' \
    -DLLVM_TARGETS_TO_BUILD=all \
    -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD='' \
    -DLLVM_ENABLE_RTTI=ON \
    -DLLVM_ENABLE_EH=ON \
    -DLLVM_ENABLE_PIC=ON \
    -DLLVM_ENABLE_ASSERTIONS=OFF \
    -DLLVM_APPEND_VC_REV=OFF \
    -DLLVM_VERSION_SUFFIX='' \
    -DLLVM_LIBDIR_SUFFIX='' \
    -DLLVM_ENABLE_ZLIB=FORCE_ON \
    -DLLVM_ENABLE_ZSTD=FORCE_ON \
    -DLLVM_ENABLE_FFI=OFF \
    -DLLVM_ENABLE_LIBEDIT=OFF \
    -DLLVM_ENABLE_LIBXML2=OFF \
    -DLLVM_ENABLE_CURL=OFF \
    -DLLVM_ENABLE_HTTPLIB=OFF \
    -DLLVM_ENABLE_Z3_SOLVER=OFF \
    -DLLVM_ENABLE_BINDINGS=OFF \
    -DLLVM_INCLUDE_TESTS=OFF \
    -DLLVM_INCLUDE_EXAMPLES=OFF \
    -DLLVM_INCLUDE_BENCHMARKS=OFF \
    -DCLANG_INCLUDE_TESTS=OFF \
    -DLLD_INCLUDE_TESTS=OFF \
    -DLLVM_BUILD_TOOLS=ON \
    -DCLANG_BUILD_TOOLS=ON \
    -DLLD_BUILD_TOOLS=ON \
    -DLLVM_INSTALL_TOOLCHAIN_ONLY=OFF \
    -DLLVM_INSTALL_UTILS=ON \
    -DLLVM_INSTALL_PACKAGE_DIR=lib/cmake/llvm \
    -DCLANG_INSTALL_PACKAGE_DIR=lib/cmake/clang \
    -DLLD_INSTALL_PACKAGE_DIR=lib/cmake/lld \
"
