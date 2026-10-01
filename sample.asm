# Sample Assembly Script for KernelSim
# Demonstrates register assignments, memory allocations, and traps

DUMP
LS_DISK
CAT /etc/os-release

# 1. Print message via sys_write (RAX=1, RDI=1)
MOV RAX, 1
MOV RDI, 1
MOV RSI, "Testing batch script mode in KernelSim!\n"
MOV RDX, 40
SYSCALL

# 2. Query heap break
MOV RAX, 12
MOV RDI, 0
SYSCALL

# 3. Inspect process table
PS

# 4. Exit
EXIT
