# Sample Assembly Script for KernelSim
# Demonstrates register assignments, memory allocations, traps, and inline comments

DUMP                        ; Inspect live CPU registers and initial mode
LS_DISK                     ; Inspect root directory and inodes on disk
CAT /etc/os-release         ; Inspect virtual /etc/os-release

# 1. Print message via sys_write (RAX=1, RDI=1)
MOV RAX, 1                  ; Syscall #1 = sys_write
MOV RDI, 1                  ; fd 1 = STDOUT
MOV RSI, "Testing batch script mode in KernelSim!\n" ; Load message
MOV RDX, 40                 ; Length = 40 bytes
SYSCALL                     ; Fast syscall trap (MSR_LSTAR -> SYSRETQ)

# 2. Query heap break using legacy software interrupt INT 0x80
MOV RAX, 12                 ; Syscall #12 = sys_brk
MOV RDI, 0                  ; Query current break
INT 0x80                    ; Software interrupt trap (IDT Gate 0x80 -> IRETQ)

# 3. Inspect process table
PS                          ; Display active PCB entries

# 4. Exit
EXIT                        ; Terminate simulation

