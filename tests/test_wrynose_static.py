#!/usr/bin/env python3
"""Focused migration gate; does not import or invoke any Yocto tooling.

Optional source tests use LLVM21_ARCHIVE and ZIG_SOURCE_GIT (read-only).
CMake tests configure synthetic projects with mock libraries, never compile.
All generated files live in disposable directories inside this worktree.
"""
import ast
import glob
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ZIG_REV = "7056ba9a5c750305726be862a51ff18e2318c138"
LLVM_RECIPE = ROOT / "recipes-devtools/zig-llvm/zig-llvm-native_21.1.8.bb"
ZIG_RECIPE = ROOT / "recipes-devtools/zig/zig-native_git.bb"
PRIVATE_PATHS = {
    "prefix": "${ZIG_LLVM_PREFIX}",
    "exec_prefix": "${prefix}",
    **{name: "${prefix}/" + suffix for name, suffix in (
        ("bindir", "bin"), ("sbindir", "sbin"), ("libexecdir", "libexec"),
        ("libdir", "lib"), ("includedir", "include"), ("datadir", "share"),
        ("sysconfdir", "etc"), ("sharedstatedir", "com"),
        ("localstatedir", "var"),
    )},
}


def qualified_private_paths(text):
    """Guard literal declarations, not a BitBake parser or evaluator."""
    names = "|".join(PRIVATE_PATHS)
    matches = re.findall(rf'^({names}):class-native = "([^"]+)"$', text, re.M)
    if len(matches) != len(PRIVATE_PATHS) or dict(matches) != PRIVATE_PATHS:
        raise AssertionError("private paths must all use exact class-native overrides")
    if re.search(rf"^({names})\s*[.=]", text, re.M):
        raise AssertionError("plain install paths can be overwritten by deferred native")
    return dict(matches)


def run(*args, cwd=ROOT, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=60)


def patch_files(text):
    return re.findall(r"^--- a/(.+)$", text, re.M)


def apply_patch(path, directory):
    result = run("patch", "--batch", "--fuzz=0", "-p1", "-i", str(path),
                 cwd=directory)
    if "offset" in result.stdout or "fuzz" in result.stdout:
        raise AssertionError(result.stdout)


class MetadataTests(unittest.TestCase):
    def test_discovery_and_providers(self):
        conf = (ROOT / "conf/layer.conf").read_text()
        block = re.search(r'BBFILES \+= "(.*?)"', conf, re.S)[1]
        patterns = block.replace("\\", "").replace("${LAYERDIR}", str(ROOT)).split()
        discovered = sorted(Path(p).relative_to(ROOT).as_posix()
                            for pattern in patterns for p in glob.glob(pattern))
        self.assertEqual(discovered, [
            "recipes-devtools/zig-llvm/zig-llvm-native_21.1.8.bb",
            "recipes-devtools/zig/zig-native_git.bb",
            "recipes-examples/hello-zig/hello-zig_1.0.bb",
        ])
        self.assertIn('LAYERSERIES_COMPAT_zig = "wrynose"', conf)
        self.assertIn('LAYERDEPENDS_zig = "core clang-layer"', conf)
        self.assertNotIn("PREFERRED_VERSION_", conf)
        for relative in discovered:
            text = (ROOT / relative).read_text()
            self.assertNotRegex(text, r"(?m)^(require|include|PROVIDES|BBCLASSEXTEND|BPN|PN)\s")
            self.assertNotIn("work-shared", text)
            self.assertNotIn("deltask", text)
            self.assertNotIn("[noexec]", text)
            self.assertNotIn("is_work_shared_spdx", text)
            for names in re.findall(r"^inherit (.+)$", text, re.M):
                for name in names.split():
                    self.assertNotEqual(name, "cmake-native")
                    candidates = [ROOT / "classes" / (name + ".bbclass")]
                    core = ROOT.parent / "openembedded-core/meta"
                    candidates += [core / d / (name + ".bbclass")
                                   for d in ("classes", "classes-recipe", "classes-global")]
                    self.assertTrue(any(p.is_file() for p in candidates), name)
            for filename in re.findall(r"file://([^;\s\"]+\.patch)", text):
                patch = ROOT / relative
                patch = patch.parent / "files" / filename
                self.assertTrue(patch.is_file(), patch)
                self.assertIn("Upstream-Status:", patch.read_text())

    def test_wrynose_dependency_and_task_interfaces(self):
        core = ROOT.parent / "openembedded-core/meta"
        conf = (core / "conf/bitbake.conf").read_text()
        self.assertIn('UNPACKDIR ??= "${WORKDIR}/sources"', conf)
        self.assertIn('BB_GIT_DEFAULT_DESTSUFFIX = "${BP}"', conf)
        self.assertIn('S = "${UNPACKDIR}/${BP}"', conf)
        cmake = (core / "classes-recipe/cmake.bbclass").read_text()
        self.assertIn('DEPENDS:prepend = "cmake-native "', cmake)
        self.assertIn('d.appendVar("DEPENDS", " ninja-native")', cmake)
        self.assertTrue(list((core / "recipes-devtools/cmake").glob("cmake-native_*.bb")))
        pkgconfig = (core / "classes-recipe/pkgconfig.bbclass").read_text()
        self.assertIn('DEPENDS:prepend = "pkgconf-native "', pkgconfig)
        pkgconf = next((core / "recipes-devtools/pkgconf").glob("pkgconf_*.bb")).read_text()
        self.assertRegex(pkgconf, r'BBCLASSEXTEND = "[^"]*native')
        native = (core / "classes-recipe/native.bbclass").read_text()
        self.assertIn('do_populate_sysroot[sstate-inputdirs] = "${SYSROOT_DESTDIR}/${STAGING_DIR_NATIVE}/"', native)
        staging = (core / "classes-global/staging.bbclass").read_text()
        self.assertIn('addtask populate_sysroot after do_install', staging)
        self.assertIn('for dir in ${SYSROOT_DIRS}', staging)
        spdx = (core / "classes/create-spdx-3.0.bbclass").read_text()
        order = spdx[spdx.index("addtask do_create_spdx after"):spdx.index('SSTATETASKS += "do_create_spdx"')]
        for task in ("do_unpack", "do_patch", "do_populate_sysroot", "do_create_recipe_spdx"):
            self.assertIn(task, order)
        cls = (ROOT / "classes/zig.bbclass").read_text()
        for interface in ("EXPORT_FUNCTIONS do_configure do_compile do_install",
                          'do_configure[depends] += "zig-native:do_populate_sysroot"'):
            self.assertIn(interface, cls)

    def test_pinned_source_fetch_policy(self):
        text = ZIG_RECIPE.read_text()
        revision = re.search(r'^SRCREV = "([^"]+)"', text, re.M).group(1)
        uris = re.search(r'SRC_URI = "([^"]+)"', text).group(1).split()
        git_uris = [uri for uri in uris if uri.startswith("git://")]
        self.assertEqual(revision, ZIG_REV)
        self.assertEqual(git_uris, [
            "git://codeberg.org/ziglang/zig.git;protocol=https;nobranch=1",
        ])
        original = run("git", "show",
                       "6672955:recipes-devtools/zig/zig-native_git.bb").stdout
        # No recipe behavior changes beyond the branch-validation parameter.
        def metadata(value):
            return [line for line in value.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(metadata(text),
                         metadata(original.replace("branch=0.16.x", "nobranch=1")))

    def test_private_paths_and_source_conventions(self):
        llvm = LLVM_RECIPE.read_text()
        zig = ZIG_RECIPE.read_text()
        private = 'ZIG_LLVM_PREFIX = "${STAGING_LIBDIR_NATIVE}/zig-llvm-21"'
        for text in (llvm, zig):
            self.assertIn(private, text)
            self.assertNotIn("clang-native", text)
        self.assertEqual(qualified_private_paths(llvm), PRIVATE_PATHS)
        self.assertIn('SYSROOT_DIRS = "${ZIG_LLVM_PREFIX}"', llvm)
        self.assertIn('SYSROOT_DIRS_NATIVE = ""', llvm)
        self.assertIn('SSTATE_SCAN_FILES:remove = "*-config"', llvm)
        for flag in ("BUILD_SHARED_LIBS=OFF", "LLVM_BUILD_LLVM_DYLIB=OFF",
                     "LLVM_LINK_LLVM_DYLIB=OFF", "LLVM_TARGETS_TO_BUILD=all",
                     "LLVM_INSTALL_TOOLCHAIN_ONLY=OFF", "LLVM_INSTALL_UTILS=ON"):
            self.assertIn(flag, llvm)
        for project in ("LLVM", "CLANG", "LLD"):
            self.assertIn(f"-D{project}_INSTALL_PACKAGE_DIR=lib/cmake/{project.lower()}", llvm)
        self.assertIn('S = "${UNPACKDIR}/llvm-project-${PV}.src"', llvm)
        self.assertIn('S = "${UNPACKDIR}/${BP}"', zig)
        self.assertIn(ZIG_REV, zig)
        self.assertIn("-DZIG_LLVM_CONFIG_EXECUTABLE='${ZIG_LLVM_PREFIX}/bin/llvm-config'", zig)
        self.assertIn("-DZIG_STATIC_LLVM=ON", zig)
        hello = (ROOT / "recipes-examples/hello-zig/hello-zig_1.0.bb").read_text()
        self.assertIn('S = "${UNPACKDIR}"', hello)
        cls = (ROOT / "classes/zig.bbclass").read_text()
        self.assertIn("inherit pkgconfig", cls)
        self.assertNotIn("export PKG_CONFIG", cls)
        self.assertIn("${@'-Dcpu=' + d.getVar('ZIG_MCPU')", cls)

    def test_deferred_native_install_paths(self):
        core = ROOT.parent / "openembedded-core/meta"
        conf = (core / "conf/bitbake.conf").read_text()
        deferred = re.search(r'^BB_DEFER_BBCLASSES = "([^"]+)"$', conf, re.M)[1].split()
        self.assertIn("native", deferred)
        native = (core / "classes-recipe/native.bbclass").read_text()
        for line in ('base_prefix = "${STAGING_DIR_NATIVE}"',
                     'prefix = "${STAGING_DIR_NATIVE}${prefix_native}"',
                     'exec_prefix = "${STAGING_DIR_NATIVE}${prefix_native}"',
                     'bindir = "${STAGING_BINDIR_NATIVE}"',
                     'libdir = "${STAGING_LIBDIR_NATIVE}"',
                     'includedir = "${STAGING_INCDIR_NATIVE}"',
                     'CLASSOVERRIDE = "class-native"',
                     'do_populate_sysroot[sstate-inputdirs] = "${SYSROOT_DESTDIR}/${STAGING_DIR_NATIVE}/"'):
            self.assertIn(line, native)
        original = run("git", "show", "40fad22:" + str(LLVM_RECIPE.relative_to(ROOT))).stdout
        current = LLVM_RECIPE.read_text()
        with self.assertRaises(AssertionError):
            qualified_private_paths(original)
        for name in PRIVATE_PATHS:
            with self.subTest(path=name), self.assertRaises(AssertionError):
                qualified_private_paths(current.replace("\n" + name + ":class-native =",
                                                        "\n" + name + " ="))
        with self.assertRaises(AssertionError):
            qualified_private_paths(current.replace('prefix:class-native = "${ZIG_LLVM_PREFIX}"',
                                                    'prefix:class-native = "${STAGING_DIR_NATIVE}/usr"'))
        # No metadata behavior changes beyond qualifying the existing paths.
        def metadata(text):
            return [line for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        expected = original
        for name in PRIVATE_PATHS:
            expected = expected.replace("\n" + name + " =", "\n" + name + ":class-native =")
        self.assertEqual(metadata(current), metadata(expected))

    def test_public_class_and_arm_mapping(self):
        cls = (ROOT / "classes/zig.bbclass").read_text()
        original = run("git", "show", "4623895:classes/zig.bbclass").stdout
        def function(text):
            return text[text.index("def zig_target_map"):text.index("zig_do_configure()")]
        self.assertEqual(ast.dump(ast.parse(function(cls))),
                         ast.dump(ast.parse(function(original))))
        api = r"^(?:TOOLCHAIN_zig|ZIG\w*|B|EXTRA_ZIGBUILD)\s.*$"
        self.assertEqual(re.findall(api, cls, re.M), re.findall(api, original, re.M))
        namespace = {}
        exec(compile(function(cls), "zig_target_map", "exec"), namespace)
        class Data:
            def __init__(self, **values):
                self.values = values
            def getVar(self, key):
                return self.values.get(key)
        for arch, tune, expected in (
            ("arm", "arm cortexa9 neon callconvention-hard", "arm-linux-gnueabihf.2.43"),
            ("arm", "arm cortexa9 neon", "arm-linux-gnueabi.2.43"),
            ("armeb", "callconvention-hard", "armeb-linux-gnueabihf.2.43"),
        ):
            with self.subTest(arch=arch, tune=tune):
                data = Data(TARGET_ARCH=arch, TARGET_OS="linux-gnueabi",
                            TUNE_FEATURES=tune, GLIBCVERSION="2.43%")
                self.assertEqual(namespace["zig_target_map"](data), expected)
        data = Data(TARGET_ARCH="arm", TARGET_OS="linux-gnueabi",
                    TUNE_FEATURES="callconvention-hard")
        self.assertEqual(namespace["zig_target_map"](data), "arm-linux-gnueabihf.2.39")


class InstallStagingTests(unittest.TestCase):
    """Synthetic CMake install/copy fixture, not actual Yocto staging or LLVM."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix=".migration-test-", dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.paths = qualified_private_paths(LLVM_RECIPE.read_text())
        self.producer = self.directory / "producer/recipe-sysroot-native"
        self.private_relative = Path("usr/lib/zig-llvm-21")
        self.private = self.producer / self.private_relative
        self.source = self.directory / "source"
        self.source.mkdir()
        config = self.source / "llvm-config"
        config.write_text('''#!/bin/sh
prefix=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
case "$1" in
 --prefix) echo "$prefix" ;;
 --libdir) echo "$prefix/lib" ;;
 --includedir) echo "$prefix/include" ;;
 --version) echo 21.1.8 ;;
 *) exit 1 ;;
esac
''')
        config.chmod(0o755)
        (self.source / "header.h").write_text("/* mock header: no compilation */\n")
        (self.source / "data.txt").write_text("mock LLVM data\n")
        rules = ['cmake_minimum_required(VERSION 3.18)', 'project(private_install NONE)',
                 'install(PROGRAMS llvm-config DESTINATION "${CMAKE_INSTALL_BINDIR}")',
                 'install(FILES header.h DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/llvm")',
                 'install(FILES data.txt DESTINATION "${CMAKE_INSTALL_DATADIR}/llvm")']
        for package, folder, target in (("LLVM", "llvm", "LLVMCore"),
                                        ("Clang", "clang", "clangFrontend"),
                                        ("LLD", "lld", "lldELF")):
            (self.source / f"lib{target}.a").write_text("mock static library: no linking\n")
            export = self.source / f"{package}Config.cmake"
            export.write_text(f'''get_filename_component(_mock_prefix "${{CMAKE_CURRENT_LIST_DIR}}/../../.." ABSOLUTE)
set({package.upper()}_INCLUDE_DIRS "${{_mock_prefix}}/include")
add_library({target} STATIC IMPORTED)
set_target_properties({target} PROPERTIES IMPORTED_LOCATION "${{_mock_prefix}}/lib/lib{target}.a")
''')
            if package == "LLVM":
                with export.open("a") as f:
                    f.write('add_executable(llvm-config IMPORTED)\n'
                            'set_target_properties(llvm-config PROPERTIES IMPORTED_LOCATION "${_mock_prefix}/bin/llvm-config")\n')
            rules += [f'install(FILES lib{target}.a DESTINATION "${{CMAKE_INSTALL_LIBDIR}}")',
                      f'install(FILES {export.name} DESTINATION "${{CMAKE_INSTALL_LIBDIR}}/cmake/{folder}")']
        (self.source / "CMakeLists.txt").write_text("\n".join(rules) + "\n")

    def install_and_stage(self, name, install_prefix):
        case = self.directory / name
        build = case / "build"
        image = case / "image"
        args = ["-DCMAKE_INSTALL_PREFIX=" + str(install_prefix)]
        for name, cmake_name in (("bindir", "BINDIR"), ("libdir", "LIBDIR"),
                                 ("includedir", "INCLUDEDIR"), ("datadir", "DATADIR")):
            # Controlled literal suffixes guarded above; no metadata evaluation.
            args.append("-DCMAKE_INSTALL_" + cmake_name + "=" +
                        self.paths[name].removeprefix("${prefix}/"))
        run("cmake", "-S", str(self.source), "-B", str(build), *args)
        env = dict(os.environ, DESTDIR=str(image))
        result = subprocess.run(["cmake", "--install", str(build)], env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=60, check=True)
        self.assertIn("llvm-config", result.stdout)
        installed_private = image / self.private.relative_to("/")
        staging = case / "sysroot-destdir"
        # Model only the two inspected copy boundaries, not staging.bbclass.
        sstate_input = staging / self.producer.relative_to("/")
        sstate_input.mkdir(parents=True)
        if installed_private.is_dir():
            shutil.copytree(installed_private, sstate_input / self.private_relative)
        component = case / "component"
        shutil.copytree(sstate_input, component)
        marker = component / "sysroot-providers/zig-llvm-native"
        marker.parent.mkdir()
        marker.touch()
        consumer = case / "consumer/recipe-sysroot-native"
        shutil.copytree(component, consumer)
        return image, component, consumer

    def test_private_install_staging_and_consumer_relocation(self):
        image, component, consumer = self.install_and_stage("private", self.private)
        private = consumer / self.private_relative
        self.assertTrue((image / self.private.relative_to("/") / "bin/llvm-config").is_file())
        self.assertTrue((component / self.private_relative / "bin/llvm-config").is_file())
        for flag, expected in (("--prefix", private), ("--libdir", private / "lib"),
                               ("--includedir", private / "include")):
            self.assertEqual(run(str(private / "bin/llvm-config"), flag).stdout.strip(), str(expected))
        self.assertEqual(run(str(private / "bin/llvm-config"), "--version").stdout.strip(), "21.1.8")
        self.assertTrue((private / "include/llvm/header.h").is_file())
        self.assertTrue((private / "share/llvm/data.txt").is_file())
        self.assertFalse(self.producer.exists())
        for tree in (component, consumer):
            self.assertFalse((tree / "usr/bin/llvm-config").exists())
            self.assertFalse((tree / "usr/lib/libLLVMCore.a").exists())
            for path in tree.rglob("*"):
                if path.is_file() and path.suffix == ".cmake":
                    self.assertNotIn(str(self.producer), path.read_text())
        source = self.directory / "consumer-source"
        source.mkdir()
        (source / "CMakeLists.txt").write_text(f'''cmake_minimum_required(VERSION 3.18)
project(relocated_exports NONE)
find_package(LLVM CONFIG REQUIRED PATHS "{private}/lib/cmake/llvm" NO_DEFAULT_PATH)
find_package(Clang CONFIG REQUIRED PATHS "{private}/lib/cmake/clang" NO_DEFAULT_PATH)
find_package(LLD CONFIG REQUIRED PATHS "{private}/lib/cmake/lld" NO_DEFAULT_PATH)
foreach(target LLVMCore clangFrontend lldELF llvm-config)
  get_target_property(location ${{target}} IMPORTED_LOCATION)
  string(FIND "${{location}}" "{private}/" position)
  if(NOT position EQUAL 0 OR NOT EXISTS "${{location}}")
    message(FATAL_ERROR "missing/escaped relocated export: ${{location}}")
  endif()
endforeach()
foreach(path ${{LLVM_INCLUDE_DIRS}} ${{CLANG_INCLUDE_DIRS}} ${{LLD_INCLUDE_DIRS}})
  if(NOT path STREQUAL "{private}/include" OR NOT IS_DIRECTORY "${{path}}")
    message(FATAL_ERROR "escaped relocated headers: ${{path}}")
  endif()
endforeach()
''')
        run("cmake", "-S", str(source), "-B", str(self.directory / "consumer-build"))

    def test_ordinary_install_leaves_private_component_empty(self):
        image, component, consumer = self.install_and_stage("ordinary", self.producer / "usr")
        self.assertTrue((image / self.producer.relative_to("/") / "usr/bin/llvm-config").is_file())
        self.assertEqual([p.relative_to(component).as_posix() for p in component.rglob("*") if p.is_file()],
                         ["sysroot-providers/zig-llvm-native"])
        self.assertFalse((consumer / self.private_relative).exists())
        self.assertFalse((consumer / "usr/bin/llvm-config").exists())


@unittest.skipUnless(os.environ.get("LLVM21_ARCHIVE") and os.environ.get("ZIG_SOURCE_GIT"),
                     "set LLVM21_ARCHIVE and ZIG_SOURCE_GIT for source/CMake gate")
class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix=".migration-test-", dir=ROOT)
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name)
        archive = Path(os.environ["LLVM21_ARCHIVE"])
        with archive.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        assert digest == "4633a23617fa31a3ea51242586ea7fb1da7140e426bd62fc164261fe036aa142"
        cls.llvm_patch = next((ROOT / "recipes-devtools/zig-llvm/files").glob("*.patch"))
        wanted = set(patch_files(cls.llvm_patch.read_text()))
        wanted.update(("llvm/LICENSE.TXT", "clang/LICENSE.TXT", "lld/LICENSE.TXT"))
        with tarfile.open(archive) as tar:
            for name in wanted:
                data = tar.extractfile("llvm-project-21.1.8.src/" + name).read()
                dest = cls.directory / "llvm" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        cls.zig = cls.directory / "zig"
        cls.zig.mkdir()
        cls.original_modules = {}
        for path in ("CMakeLists.txt", "LICENSE", "cmake/Findllvm.cmake",
                     "cmake/Findclang.cmake", "cmake/Findlld.cmake"):
            data = run("git", "--no-optional-locks", "-C", os.environ["ZIG_SOURCE_GIT"],
                       "show", ZIG_REV + ":" + path).stdout
            dest = cls.zig / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(data)
            cls.original_modules[path] = data
        for patch in sorted((ROOT / "recipes-devtools/zig/files").glob("*.patch")):
            apply_patch(patch, cls.zig)

    def test_llvm_patch_and_license_checksums(self):
        apply_patch(self.llvm_patch, self.directory / "llvm")
        for name, expected in (("llvm", "8a15a0759ef07f2682d2ba4b893c9afe"),
                               ("clang", "ff42885ed2ab98f1ecb8c1fc41205343"),
                               ("lld", "ae7dc7c027b1fa89b5b013d391d3ee2b")):
            data = (self.directory / "llvm" / name / "LICENSE.TXT").read_bytes()
            self.assertEqual(hashlib.md5(data).hexdigest(), expected)
        self.assertEqual(hashlib.md5((self.zig / "LICENSE").read_bytes()).hexdigest(),
                         "d934d7758eb646c9c6a2162d88427689")

    def test_private_cmake_selection_and_failures(self):
        private = self.directory / "private"
        ordinary = self.directory / "ordinary"
        for prefix in (private, ordinary):
            (prefix / "bin").mkdir(parents=True)
            (prefix / "lib").mkdir()
            for header in ("clang/Frontend/ASTUnit.h", "lld/Common/Driver.h", "llvm/IR/IRBuilder.h"):
                dest = prefix / "include" / header
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.touch()
        libraries = ["LLVMCore"]
        for project in ("clang", "lld"):
            original = self.original_modules[f"cmake/Find{project}.cmake"]
            libraries += re.findall(r"FIND_AND_ADD_\w+_LIB\((\w+)\)", original)
        for prefix in (private, ordinary):
            for library in libraries:
                (prefix / "lib" / ("lib" + library + ".a")).touch()
        targets = "AArch64 AMDGPU ARM AVR BPF Hexagon Lanai LoongArch Mips MSP430 NVPTX PowerPC RISCV SPIRV Sparc SystemZ VE WebAssembly X86 XCore"
        script = self.directory / "CMakeLists.txt"
        script.write_text(f'''cmake_minimum_required(VERSION 3.18)
project(private_selection NONE)
set(CMAKE_FIND_LIBRARY_PREFIXES lib)
set(CMAKE_FIND_LIBRARY_SUFFIXES .a)
list(PREPEND CMAKE_MODULE_PATH "{self.zig}/cmake")
find_package(llvm 21 REQUIRED)
find_package(clang 21 REQUIRED)
find_package(lld 21 REQUIRED)
foreach(path ${{LLVM_INCLUDE_DIRS}} ${{CLANG_INCLUDE_DIRS}} ${{LLD_INCLUDE_DIRS}} ${{CLANG_LIBRARIES}} ${{LLD_LIBRARIES}})
  string(FIND "${{path}}" "{private}/" position)
  if(NOT position EQUAL 0)
    message(FATAL_ERROR "escaped private prefix: ${{path}}")
  endif()
endforeach()
''')
        config = private / "bin/llvm-config"
        def configure(case, version="21.1.8", built_targets=targets, explicit=True):
            config.write_text(f'''#!/bin/sh
case "$1" in
 --version) echo "{version}" ;;
 --targets-built) echo "{built_targets}" ;;
 --libs) echo "-lLLVMCore" ;;
 --libfiles) echo "{private}/lib/libLLVMCore.a" ;;
 --libdir) echo "{private}/lib" ;;
 --includedir) echo "{private}/include" ;;
 --system-libs) echo "-lz -lzstd" ;;
 --shared-mode) echo static ;;
 *) exit 1 ;;
esac
''')
            config.chmod(0o755)
            if not explicit:
                config.unlink()
            return run("cmake", "-S", str(self.directory), "-B", str(self.directory / case),
                       "-DZIG_USE_LLVM_CONFIG=ON", "-DZIG_STATIC_LLVM=ON",
                       "-DZIG_LLVM_PREFIX=" + str(private),
                       "-DZIG_LLVM_CONFIG_EXECUTABLE=" + str(config),
                       "-DCMAKE_PREFIX_PATH=" + str(ordinary), check=False)
        result = configure("valid")
        self.assertEqual(result.returncode, 0, result.stdout)
        for case, kwargs, message in (
            ("wrong-version", {"version": "22.1.8"}, "expected LLVM 21.x"),
            ("missing-arm", {"built_targets": targets.replace(" ARM", "")}, "missing target ARM"),
            ("missing-config", {"explicit": False}, "missing private llvm-config"),
        ):
            result = configure(case, **kwargs)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(message, result.stdout)
        for library in ("clangFrontend", "lldELF"):
            missing = private / "lib" / ("lib" + library + ".a")
            missing.unlink()
            result = configure("missing-" + library)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn("Could not find", result.stdout)
            missing.touch()


if __name__ == "__main__":
    unittest.main(verbosity=2)
