# meta-zig — Wrynose migration

This branch provides the pinned **Zig 0.16.x native compiler**, the existing
`zig.bbclass` cross-build interface, and `hello-zig`. It declares Wrynose
compatibility as a **static-validated migration candidate**, not as a claim of
successful Yocto builds or Pluto hardware qualification.

## Toolchain boundary

Zig revision `7056ba9a5c750305726be862a51ff18e2318c138` from Codeberg's
`0.16.x` branch needs LLVM/Clang/LLD **21**. Wrynose's ordinary LLVM **22.1.8**
is not a substitute. `zig-native` retains its public recipe name and depends
on `zig-llvm-native`, built from the layer's existing LLVM **21.1.8** monolithic
release archive:

- SHA256: `4633a23617fa31a3ea51242586ea7fb1da7140e426bd62fc164261fe036aa142`
- Original recipe/patch provenance: meta-clang walnascar, vendored at
  `9880651562c713b28dbd99797a5d1b138955a7cf` and retained in this layer's history.
- The private recipe builds static LLVM, Clang and LLD component libraries,
  all default LLVM 21 backends (including ARM, NEON support and SPIRV), headers,
  CMake exports and the native tools referenced by those exports.
- Everything is installed/staged under
  `${STAGING_LIBDIR_NATIVE}/zig-llvm-21/{bin,lib,include,share,...}`. No tools,
  headers, libraries or CMake packages are installed in the ordinary native
  LLVM paths. The private binaries are not added to the general tool PATH.
- `zig-native` selects the private `llvm-config` explicitly. Its patched CMake
  finders reject a wrong LLVM version or missing backend and require every
  Clang/LLD library from the private prefix; they cannot fall back to a host
  or ordinary native provider. Default upstream discovery is unchanged when
  these private options are absent.
- The compression-library export patch is rebased from the vendored patch
  `0028`. It keeps zlib/zstd references independent of the producer's absolute
  sysroot and imported CMake compression targets. Target-driver, runtime,
  LLDB, SDK and cross-toolchain patches are not carried into this native-only
  dependency. The old executable-export suppression patch is unnecessary:
  native tools and exports are staged together in the private subtree.

There is **no global LLVM21 version/provider contract**. The old preferred
versions for `clang` and `clang-native` are removed. The `clang-layer` dependency
is deliberately retained; changing manifest/layer dependencies is outside
this component's scope. OE-Core supplies ordinary Wrynose compiler recipes.

## Active and dormant metadata

`conf/layer.conf` discovers only:

- `recipes-devtools/zig-llvm/zig-llvm-native_*.bb`
- `recipes-devtools/zig/zig-native_*.bb`
- `recipes-examples/*/*.bb`

The complete old `recipes-devtools/clang/` suite and its broad
`clang_git.bbappend` remain in the checkout for provenance but are **not
exposed through BBFILES**. They are **not qualified for Wrynose**, target use,
SDK use, shared-source SPDX generation, or coexistence with ordinary LLVM.
Do not re-enable them as a workaround. This layer does not provide Zig in an
SDK, target LLVM21, compiler-rt, libc++, LLDB, OpenMP or a global clang override.

The active LLVM recipe owns its normal fetch/unpack/patch tasks and source
tree under `${UNPACKDIR}`. It does not reuse the obsolete `work-shared` source
provider, delete source tasks, or override SPDX shared-source detection.
Wrynose's normal SPDX3 dependency/task ordering applies. The `cmake` class
supplies the **cmake-native recipe dependency** and Ninja; the removed
`cmake-native` **class** is neither inherited nor copied into this layer.

Git sources now follow Wrynose's `${UNPACKDIR}/${BP}` default destination;
`hello-zig`'s local files use `${UNPACKDIR}`. The example uses the pinned Zig
series' `root_module` and `std.Io`/`std.process.Init` interfaces.

## Building projects with `zig.bbclass`

The public class variables and target mapping are preserved:

| Variable | Default | Purpose |
| --- | --- | --- |
| `TOOLCHAIN_zig` | `zig` | Existing toolchain identifier |
| `ZIG` | `${STAGING_BINDIR_NATIVE}/zig` | Native compiler |
| `ZIG_BUILD_MODE` | `ReleaseSafe` | Optimization mode |
| `ZIG_TARGET` | `zig_target_map(d)` | Cross-compilation triple |
| `ZIG_MCPU` | Empty | Optional `-Dcpu=` selection |
| `ZIG_OUT` | `${WORKDIR}/build` | Installation/build output |
| `ZIG_BUILD_ARGS` | Empty | Arguments to `zig build` |
| `EXTRA_ZIGBUILD` | Empty | Additional arguments |
| `ZIG_CACHE_DIR` | `${WORKDIR}/.zig-cache` | Per-recipe cache |
| `ZIG_GLOBAL_CACHE_DIR` | `${TMPDIR}/zig-cache` | Shared artifact cache |

The existing `B` default and layer `ZIGVERSION`/version variables are also
retained. Recipes continue to inherit `zig`, set their source and license,
and optionally customize these variables. For example:

```bitbake
inherit zig
ZIG_BUILD_MODE = "ReleaseFast"
ZIG_MCPU = "cortex_a9+neon"
```

For ARM with `TARGET_OS = "linux-gnueabi"`, `callconvention-hard` in
`TUNE_FEATURES` selects `arm-linux-gnueabihf`; soft-float still selects
`gnueabi`. The glibc version comes from the existing class logic, including
`GLIBCVERSION` fallback and wildcard stripping. Cortex-A9/NEON CPU selection
via `ZIG_MCPU` is unchanged; the class does not invent or override the tune.
The Pluto/BSP recipe remains responsible for its CPU setting.

The class now inherits `pkgconfig`, obtaining `pkgconf-native` and OE's
exported target-sysroot environment instead of hardcoding pkg-config paths
without a provider dependency. The configure/compile/install hooks, native
Zig staging dependency and cross-build arguments remain intact.

## Static validation gate

Run the focused tests without any Yocto setup or commands:

```sh
LLVM21_ARCHIVE=/path/to/llvm-project-21.1.8.src.tar.xz \
ZIG_SOURCE_GIT=/path/to/cached/codeberg.org.ziglang.zig.git \
python3 tests/test_wrynose_static.py
git diff --check
zig fmt --check recipes-examples/hello-zig/files/*.zig
```

The source repository is read-only; the tests use the pinned revision, not
its current HEAD. Generated fixtures live in disposable directories inside
this worktree. The full gate needs both source inputs: without them the
source/CMake tests are explicitly skipped, not counted as qualification.

Checks cover recipe discovery, class/path/provider boundaries, preservation
of the public class interface and ARM mapping, the release checksum and all
three LLVM-project license checksums plus Zig's license checksum, zero-fuzz
and zero-offset patch application, and synthetic CMake discovery with mock
static libraries. CMake tests prove private-path selection and rejection of
LLVM22, missing ARM support, missing llvm-config, and missing private
Clang/LLD libraries even when an ordinary prefix supplies matching names.
These fixtures **do not compile or link LLVM or Zig**.

## Qualification still required

No Yocto, BitBake, devtool, setup sourcing or other Yocto tooling was run for
this migration. Actual parsing/signatures, LLVM21 and pinned Zig compilation,
static linking, sysroot population/coexistence, sstate relocation, SPDX3
output, `hello-zig` cross-compilation and Pluto execution remain unverified.
The all-backend monolithic build can require substantial RAM and disk.
Product, BSP, manifest and deployment migration/qualification are separate
coordinator-owned work. No SDK support or hardware behavior is claimed here.

## License

Layer metadata: MIT (see `LICENSE`). LLVM-project and Zig sources retain the
licenses and checksums specified by their recipes.
