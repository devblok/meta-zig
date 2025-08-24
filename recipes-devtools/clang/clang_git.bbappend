# Enable all LLVM targets required by Zig compiler
# Zig requires all default targets to be built with LLVM

LLVM_TARGETS_TO_BUILD = "AMDGPU;AArch64;ARM;AVR;BPF;Hexagon;Lanai;Mips;MSP430;NVPTX;PowerPC;RISCV;Sparc;SystemZ;VE;WebAssembly;X86;XCore;LoongArch;SPIRV"
