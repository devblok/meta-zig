# meta-zig

OpenEmbedded/Yocto layer for the Zig programming language.

This layer provides:
- Native Zig compiler built from source using meta-clang's LLVM 20.1.1
- `zig.bbclass` for building Zig projects
- Integration with Yocto's cross-compilation system

## Dependencies

- `meta-clang` layer with LLVM 20.1.1 support
- Compatible with Scarthgap and later releases

## Usage

Add this layer to your `bblayers.conf`:

```
BBLAYERS += "/path/to/meta-zig"
```

### Building Zig Projects

Use the `zig` class in your recipes:

```bitbake
inherit zig

SRC_URI = "https://github.com/example/zig-project.git"
```

The class expects a `build.zig` file in the source directory.

## Configuration

- `ZIGVERSION`: Zig version to use (default: 0.14.1)
- `ZIG_BUILD_MODE`: Build optimization mode (default: ReleaseSafe)
- `ZIG_TARGET`: Target architecture (auto-detected from OE variables)
