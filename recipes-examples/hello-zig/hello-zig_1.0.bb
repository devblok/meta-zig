SUMMARY = "Hello World example in Zig"
DESCRIPTION = "Simple Zig program to test meta-zig layer functionality"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://main.zig \
    file://build.zig \
"

S = "${WORKDIR}"

inherit zig

# Simple project doesn't need additional build arguments
ZIG_BUILD_ARGS = ""

# Test that files are correctly created
do_install:append() {
    # Verify the binary was created
    if [ ! -f "${D}${bindir}/hello-zig" ]; then
        bbfatal "hello-zig binary was not installed correctly"
    fi
}