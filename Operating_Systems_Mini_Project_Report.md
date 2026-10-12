# DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR

### **21CSC202J – OPERATING SYSTEMS**
### **A MINI-PROJECT REPORT**

**Submitted By:**
* **HARISH RAGAV V [RA2511032020045]**
* **PRADEEP M [RA2511032020014]**
* **MIDHUN GANESAN S [RA2511032020031]**

*in partial fulfilment for the award of the degree of*  
**BACHELOR OF TECHNOLOGY**  
*in*  
**COMPUTER SCIENCE AND ENGINEERING W/S IOT**  
*of*  
**FACULTY OF ENGINEERING AND TECHNOLOGY**

---

### **SRM INSTITUTE OF SCIENCE AND TECHNOLOGY**
**RAMAPURAM CAMPUS, CHENNAI – 600089**  
**OCTOBER 2026**

---

## BONAFIDE CERTIFICATE

Certified that this mini project report titled **“DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR”** is the bonafide work of:

* **HARISH RAGAV V (RA2511032020045)**
* **PRADEEP M (RA2511032020014)**
* **MIDHUN GANESAN S (RA2511032020031)**

who carried out the project under my supervision for the course **21CSC202J – OPERATING SYSTEMS**.

| | SIGNATURE |
|---|---|
| | **Dr. TKS Rathish babu, M.E., Ph.D.** |
| | Associate Professor |
| | Dept of CSE W/S IOT |
| | SRM Institute of Science and Technology |
| | Ramapuram Campus, Chennai – 600089 |

---

## DECLARATION

We hereby declare that the entire work contained in this mini project report titled **“DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR”** has been carried out by **HARISH RAGAV V [RA2511032020045]**, **PRADEEP M [RA2511032020014]**, and **MIDHUN GANESAN S [RA2511032020031]** at SRM Institute of Science and Technology, Ramapuram Campus, Chennai – 600089, in partial fulfilment of the requirements for the course **21CSC202J – OPERATING SYSTEMS**.

**Place:** Chennai  
**Date:** 08-10-2026  

1. **HARISH RAGAV V [RA2511032020045]**
2. **PRADEEP M [RA2511032020014]**
3. **MIDHUN GANESAN S [RA2511032020031]**

---

## ABSTRACT

In modern operating system architectures, the boundary between user space and kernel space forms the fundamental security and reliability perimeter of the system. Operating system pedagogical tools frequently suffer from an abstraction gap: students study low-level hardware transitions (such as x86_64 privilege rings, Task State Segment stack switches, and Model-Specific Register dispatch) theoretically, but lack an inspectable, deterministic platform to trace these transitions step by step.

This project presents the design and implementation of an interactive, production-grade **System Call & Kernel Trap Simulator** developed strictly using the Python standard library with zero external dependencies. The simulator models the x86_64 architecture's privilege levels (Current Privilege Level Ring 3 vs Ring 0), CPU general-purpose registers (`RAX`, `RDI`, `RSI`, `RDX`, `R10`, `R8`, `R9`, `RSP`, `RIP`, `RFLAGS`), and hardware trap mechanisms supporting both modern fast system calls via `MSR_LSTAR` (`SYSCALL`/`SYSRETQ`) and legacy software interrupts (`INT 0x80`/`IRETQ`).

Within the simulated kernel space, the system incorporates an in-memory Virtual File System (VFS) with virtual inodes, permissions, and directory traversal; a per-process File Descriptor Table managing standard streams (`0: STDIN`, `1: STDOUT`, `2: STDERR`) and dynamically allocated handles; a Virtual Memory Manager simulating heap break adjustment (`brk`/`sbrk`) with boundary enforcement triggering simulated `SIGSEGV` page faults; and a Process Control Block (PCB) subsystem supporting process creation (`sys_fork`), state transitions, and fork-bomb prevention. An integrated interactive assembly Read-Eval-Print Loop (REPL) allows step-by-step execution, dynamic memory inspection, and automated execution of pre-loaded programs (`hello_world`, `file_io`, `heap_alloc`, `fork_bomb_guard`). The implementation is verified against an automated suite of 42 unit tests, demonstrating 100% compliance with POSIX error handling and x86_64 ABI calling conventions.

---

## TABLE OF CONTENTS

| Chapter No. | Title | Page No. |
|---|---|---|
| | **ABSTRACT** | iv |
| | **LIST OF TABLES** | vii |
| | **LIST OF FIGURES** | viii |
| | **LIST OF ABBREVIATIONS** | ix |
| **1** | **INTRODUCTION** | **1** |
| | 1.1 Overview | 1 |
| | 1.2 Problem Statement | 2 |
| | 1.3 Aim and Objectives | 2 |
| | 1.4 Scope of the Project | 3 |
| **2** | **SYSTEM REQUIREMENTS & SPECIFICATIONS** | **4** |
| | 2.1 Hardware Requirements | 4 |
| | 2.2 Software Requirements | 4 |
| | 2.3 CPU and Architectural Specifications | 5 |
| **3** | **SYSTEM DESIGN AND ARCHITECTURE** | **7** |
| | 3.1 Architectural Overview | 7 |
| | 3.2 CPU & Hardware Trap Pipeline | 9 |
| | 3.3 Kernel Subsystems & Data Structures | 11 |
| | 3.3.1 Virtual File System (VFS) & Inodes | 11 |
| | 3.3.2 File Descriptor Table & Open File Descriptions | 12 |
| | 3.3.3 Virtual Memory Manager & Heap Segmentation | 13 |
| | 3.3.4 Process Control Block & Process Management | 14 |
| | 3.4 Supported POSIX/x86_64 System Calls | 16 |
| | 3.5 Interactive Assembly Interpreter (REPL) | 18 |
| **4** | **EXPERIMENTAL RESULTS AND VERIFICATION** | **21** |
| | 4.1 Test Harness & Automated Unit Verification | 21 |
| | 4.2 Step-by-Step Trap Execution Trace | 23 |
| | 4.3 Virtual Memory Violation (`SIGSEGV`) Demonstration | 26 |
| | 4.4 Process Duplication (`sys_fork`) & Fork-Bomb Guard | 28 |
| **5** | **CONCLUSION AND FUTURE SCOPE** | **30** |
| | 5.1 Conclusion | 30 |
| | 5.2 Future Scope | 31 |
| | **REFERENCES** | **32** |
| | **APPENDIX: SOURCE CODE** | **33** |

---

## LIST OF TABLES

| Table No. | Table Name | Page No. |
|---|---|---|
| **2.1** | Hardware and Host Platform Specifications | 4 |
| **2.2** | Emulated 64-Bit CPU Registers & Calling Conventions | 5 |
| **3.1** | Implemented POSIX System Calls & ABI Register Mappings | 16 |
| **3.2** | POSIX Error Numbers (`errno`) Handled by Simulated Kernel | 17 |
| **3.3** | Interactive Assembly REPL Command Reference | 19 |
| **4.1** | Automated Unit Test Suite Summary (42 Test Cases) | 22 |

---

## LIST OF FIGURES

| Fig No. | Figure Name | Page No. |
|---|---|---|
| **3.1** | High-Level Architecture of System Call & Kernel Trap Simulator | 8 |
| **3.2** | User-to-Kernel 6-Step Hardware Trap Lifecycle | 10 |
| **3.3** | Virtual File System (VFS) and Inode Hierarchical Model | 12 |
| **3.4** | Process Virtual Memory Space & Heap Break (`brk`) Layout | 14 |
| **4.1** | ANSI-Colored Hardware Trap Execution Trace Output | 25 |
| **4.2** | Unmapped Address Dereference and `SIGSEGV` Crash Dump | 27 |
| **4.3** | Process Tree State Before and After `sys_fork` Execution | 29 |

---

## LIST OF ABBREVIATIONS

| Abbreviation | Expansion |
|---|---|
| **ABI** | Application Binary Interface |
| **CPL** | Current Privilege Level (CPU Rings 0–3) |
| **CPU** | Central Processing Unit |
| **FD** | File Descriptor |
| **FDT** | File Descriptor Table |
| **GPR** | General Purpose Register |
| **IDT** | Interrupt Descriptor Table |
| **IVT** | Interrupt Vector Table |
| **MSR** | Model-Specific Register (`MSR_LSTAR`) |
| **OS** | Operating System |
| **PCB** | Process Control Block |
| **POSIX** | Portable Operating System Interface |
| **REPL** | Read-Eval-Print Loop |
| **TSS** | Task State Segment |
| **VFS** | Virtual File System |
| **VMM** | Virtual Memory Manager |

---

# CHAPTER 1: INTRODUCTION

### 1.1 Overview
An Operating System acts as the primary intermediary between user-level application software and physical computational hardware. In modern computers running processor architectures like x86_64, isolation is strictly enforced via hardware-assisted execution privilege levels known as **Privilege Rings**. User applications run in **Ring 3** (least privileged), while the core operating system kernel executes in **Ring 0** (supervisor mode).

Whenever a user-space program requires a privileged resource—such as reading user input from a terminal, writing a buffer to disk, adjusting dynamic heap allocations, or creating an independent child process—it cannot execute those hardware instructions directly. Instead, it must trigger a controlled **Software Trap** or **System Call (Syscall)**. 

During this trap, the CPU performs an atomic transition: it preserves the user program's register states, switches the execution stack pointer from the user stack to an elevated kernel stack, elevates the privilege ring to Ring 0, indexes into an Interrupt Vector Table (IVT) or enters through a Model-Specific Register (`MSR_LSTAR`), executes the kernel routine, writes the return value back into the accumulator register (`RAX`), and restores user-space execution via `SYSRETQ` or `IRETQ`.

### 1.2 Problem Statement
Understanding the precise boundary of system call traps is central to systems programming, kernel engineering, and security research. However, existing operating systems (e.g., standard Linux distributions or Windows) present significant educational challenges:
1. **Black-Box Nature**: Commercial and monolithic kernels execute syscall transitions in sub-microsecond hardware routines, masking intermediate steps such as stack switches, `pt_regs` preservation, and ABI register decoding from developer observation.
2. **Crash Fragility**: Experimenting with illegal pointers, kernel stack corruption, or fork-bombs on bare-metal systems results in kernel panics, frozen operating systems, or irrecoverable system crashes.
3. **Complex Dependencies**: Standard bare-metal simulators (such as QEMU or Bochs) require heavy binary toolchains, cross-compilers, and kernel compilation pipelines, creating high setup friction for student exploration.

There is a distinct need for a zero-dependency, fully inspectable, deterministic operating system simulator that authentically mirrors x86_64 kernel trapping, memory segmentation, virtual file systems, and process control.

### 1.3 Aim and Objectives
The primary aim of this project is to build an interactive, production-grade **System Call & Kernel Trap Simulator** in pure Python that models user-to-kernel space context transitions with zero external dependencies.

Specific objectives include:
* Emulating a 64-bit CPU architecture featuring GPRs (`RAX`, `RDI`, `RSI`, `RDX`, `R10`, `R8`, `R9`, `RSP`, `RIP`, `RFLAGS`) and dual privilege levels (`Ring 3` vs `Ring 0`).
* Modeling the complete 6-step hardware trap lifecycle supporting both `SYSCALL` (`MSR_LSTAR`) and legacy `INT 0x80`.
* Developing an in-memory Virtual File System (VFS) with virtual inodes, permissions, file tables, and POSIX path resolution.
* Implementing a per-process File Descriptor Table mapping standard streams (`0`, `1`, `2`) and dynamically assigned descriptors.
* Simulating virtual memory protection (`brk`/`sbrk`) that detects out-of-bounds addresses and raises simulated `SIGSEGV` signals.
* Implementing seven POSIX-aligned system calls (`sys_read`, `sys_write`, `sys_open`, `sys_close`, `sys_brk`, `sys_fork`, `sys_exit`).
* Building an interactive terminal REPL and assembly emulator with step-by-step visual execution logs.

### 1.4 Scope of the Project
The simulator serves as an interactive instructional and diagnostic testbed for Operating Systems courses. Students and researchers can write or load simulated assembly scripts, trace register-level calling conventions, test POSIX file operations, observe memory allocation boundaries, and safely analyze kernel behavior under edge conditions without hardware risk.

---

# CHAPTER 2: SYSTEM REQUIREMENTS & SPECIFICATIONS

### 2.1 Hardware Requirements
The simulator was developed and evaluated on standard x86_64 host hardware. Due to its pure standard-library architecture, hardware overhead is minimal:

**Table 2.1: Hardware and Host Platform Specifications**
| Component | Minimum Specification | Recommended Specification |
|---|---|---|
| **Processor** | Dual Core x86_64 / ARM64, 1.8 GHz | Quad Core Intel i5 / AMD Ryzen 5, 2.5 GHz+ |
| **System Memory (RAM)** | 2 GB | 8 GB or higher |
| **Storage (Disk)** | 50 MB free space | 500 MB free space |
| **Display/Terminal** | 80x24 standard terminal | 120x30 ANSI/VT100 color-enabled terminal |

### 2.2 Software Requirements
* **Operating System**: Platform-independent (Windows 10/11, Ubuntu 20.04/22.04 LTS, macOS Monterey/Ventura/Sonoma).
* **Programming Language**: Python 3.8 or higher (tested on Python 3.10 / 3.11 / 3.12).
* **External Dependencies**: **Zero (0)**. Uses strictly the Python standard library (`sys`, `os`, `time`, `enum`, `shlex`, `struct`, `typing`, `dataclasses`, `unittest`).

### 2.3 CPU and Architectural Specifications
The simulator adheres to the System V AMD64 ABI specification for system calls.

**Table 2.2: Emulated 64-Bit CPU Registers & Calling Conventions**
| Register | Bit Width | Architectural Function & Linux ABI Role |
|---|---|---|
| **`RAX`** | 64-bit | Syscall Number on input; Return Value / Error Code (`-errno`) on output |
| **`RDI`** | 64-bit | 1st Argument passed to system call |
| **`RSI`** | 64-bit | 2nd Argument passed to system call (e.g., buffer pointer) |
| **`RDX`** | 64-bit | 3rd Argument passed to system call (e.g., byte count) |
| **`R10`** | 64-bit | 4th Argument passed to system call (replaces `RCX` which is clobbered by `SYSCALL`) |
| **`R8`** | 64-bit | 5th Argument passed to system call |
| **`R9`** | 64-bit | 6th Argument passed to system call |
| **`RSP`** | 64-bit | Stack Pointer (User stack `0x7fffffffe000` vs Kernel TSS `0xffff8000...`) |
| **`RIP`** | 64-bit | Instruction Pointer (Program Counter) |
| **`RFLAGS`** | 64-bit | Status Flags register (Interrupt Enable `IF`, Zero `ZF`, Sign `SF`) |

---

# CHAPTER 3: SYSTEM DESIGN AND ARCHITECTURE

### 3.1 Architectural Overview
The simulator is structured into distinct, modular layers mirroring a production operating system: the Hardware/CPU Layer, the Trap & Dispatch Layer, the Kernel Subsystems Layer, and the User/REPL Layer.

```
+-----------------------------------------------------------------------------------+
|                        USER SPACE REPL & ASSEMBLY PARSER                          |
|    Commands: MOV, SYSCALL, INT 0x80, DUMP, LS_DISK, CAT, LOAD, STEP, RUN, PS     |
|    Demos: hello_world, file_io, heap_alloc, fork_bomb_guard                      |
+-----------------------------------------+-----------------------------------------+
                                          |
                              [Privilege Ring Boundary]
                                          |
+-----------------------------------------v-----------------------------------------+
|                              CPU & TRAP DISPATCHER                                |
|  - 64-bit GPRs (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS)               |
|  - Privilege Levels: Ring 3 (User) <---> Ring 0 (Kernel Supervisor)               |
|  - Trap Vectors: MSR_LSTAR (Fast SYSCALL) & IDT Vector 0x80 (Legacy Software)    |
|  - Stack Context Push: struct pt_regs pushed onto Task State Segment (TSS RSP0)  |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            KERNEL SUBSYSTEMS (RING 0)                             |
|                                                                                   |
|  [Interrupt Vector Table]   [Virtual Memory Manager]   [Process Control Subsystem]|
|   - 0:  sys_read             - Segment Range Tracker    - Process Table (PIDs)    |
|   - 1:  sys_write            - brk/sbrk Heap Allocator  - PCB State Snapshots     |
|   - 2:  sys_open             - SIGSEGV Trap Generator   - Fork Bomb Guard (Max 32)|
|   - 3:  sys_close                                                                 |
|   - 12: sys_brk             [Virtual File System]      [File Descriptor Table]    |
|   - 57: sys_fork             - Inodes & Dentries        - FD 0 (STDIN)            |
|   - 60: sys_exit             - Directory Trees          - FD 1 (STDOUT)           |
|                              - /dev/null, /dev/zero     - FD 2 (STDERR)           |
|                              - POSIX Permissions        - Dynamic FDs (>= 3)      |
+-----------------------------------------------------------------------------------+
```
*Figure 3.1: High-Level Architecture of System Call & Kernel Trap Simulator*

### 3.2 CPU & Hardware Trap Pipeline
When a user process executes `SYSCALL` or `INT 0x80`, the CPU initiates an atomic, 6-step context switch:

```
[User Ring 3 Execution]
        |
        v
Step 1: Trap Detected (MSR_LSTAR / IDT Vector 0x80)
        |
        v
Step 2: Save Hardware Context (Push struct pt_regs to Kernel Stack TSS RSP0)
        |
        v
Step 3: Elevate Privilege & Switch Stacks (CPL 3 -> CPL 0; User RSP -> Kernel RSP0)
        |
        v
Step 4: IVT Vector Lookup & x86_64 ABI Parameter Decoding (RDI, RSI, RDX, R10, R8, R9)
        |
        v
Step 5: Execute Privileged Kernel Routine (VFS / VMM / Process Manager)
        |
        v
Step 6: Restore Context & Return (Write return code to RAX; SYSRETQ/IRETQ restores Ring 3)
        |
        v
[Resume User Ring 3 Execution]
```
*Figure 3.2: User-to-Kernel 6-Step Hardware Trap Lifecycle*

1. **Trap Detection**: The CPU detects a trap instruction. In modern mode, it accesses Model-Specific Register `MSR_LSTAR` (`0xC0000082`). In legacy mode, it references Interrupt Descriptor Table vector `0x80`.
2. **Context Save**: The CPU saves the user-space registers (`RAX`, `RDI`, `RSI`, `RDX`, `R10`, `R8`, `R9`, `RSP`, `RIP`, `RFLAGS`) into a `struct pt_regs` frame on the kernel stack.
3. **Privilege Elevation**: The Current Privilege Level (CPL) shifts from `Ring 3` to `Ring 0`. The stack pointer shifts from the user stack (`0x00007fffffffe000`) to the Task State Segment supervisor stack (`0xffff80003e80ffe0`).
4. **IVT Lookup & ABI Decoding**: The kernel reads `RAX` to identify the syscall number and extracts input arguments from `RDI`, `RSI`, `RDX`, and `R10`.
5. **Kernel Subsystem Execution**: The requested privileged operation runs within supervisor mode.
6. **Context Restoration**: The return status (or negative `-errno`) is stored into the saved `RAX` slot. The CPU executes `SYSRETQ` or `IRETQ`, restoring user registers and lowering the privilege level back to `Ring 3`.

### 3.3 Kernel Subsystems & Data Structures

#### 3.3.1 Virtual File System (VFS) & Inodes
The simulator implements an in-memory Virtual File System representing UNIX-like file trees:
* **`VirtualInode`**: Stores inode number, file type (`FILE`, `DIRECTORY`, `CHAR_DEVICE`), POSIX permissions (`rwxr-xr-x`), file size, link count, timestamps, and data payload.
* **Special Device Nodes**: Supports `/dev/null` (discards writes, returns EOF on read) and `/dev/zero` (supplies infinite null bytes).
* **Directory Traversal**: Resolves absolute and relative paths, validating path components and permissions.

#### 3.3.2 File Descriptor Table & Open File Descriptions
Every process maintains its own `FileDescriptorTable`:
* Standard streams (`0: STDIN`, `1: STDOUT`, `2: STDERR`) are mapped by default.
* File descriptors point to an underlying `OpenFileDescription` structure holding file offset, open flags, and active reference counts.
* Calling `sys_open` allocates the lowest available integer file descriptor index `fd >= 3`.

#### 3.3.3 Virtual Memory Manager & Heap Segmentation
The virtual address space of each simulated process is partitioned into distinct segments:
* **`.text`** (`0x00400000 - 0x00401fff`): Read-Only / Execute.
* **`.data`** (`0x00402000 - 0x00403fff`): Read / Write.
* **`.heap`** (`0x00600000 - Program Break`): Dynamic memory managed by `sys_brk`.
* **`.stack`** (`0x7ffff7ffe000 - 0x7fffffffe000`): User call stack growing downward.

If user code attempts to read or write memory outside these mapped segments, the VMM detects the violation, halts instruction processing, and generates a simulated `SIGSEGV` fault with full register and memory crash dumps.

#### 3.3.4 Process Control Block & Process Management
The `ProcessControlBlock` (PCB) encapsulates the execution state of an independent process:
* Process Identifiers: `pid`, parent `ppid`.
* Execution State: `RUNNING`, `READY`, `ZOMBIE`, `TERMINATED`.
* Memory and Descriptor Maps: Process-specific VMM instance and File Descriptor Table.
* **Fork-Bomb Guard**: The `ProcessManager` caps total simultaneous active processes at `MAX_PROCESSES = 32`. Attempting to spawn processes past this limit causes `sys_fork` to abort safely and return `-EAGAIN` (`-11`).

### 3.4 Supported POSIX/x86_64 System Calls

**Table 3.1: Implemented POSIX System Calls & ABI Register Mappings**
| Syscall Name | RAX | Arguments (Registers) | Success Return | Error Return |
|---|---|---|---|---|
| **`sys_read`** | `0` | `RDI`=fd, `RSI`=buf, `RDX`=count | Bytes read | `-EBADF` (9), `-EFAULT` (14), `-EISDIR` (21) |
| **`sys_write`** | `1` | `RDI`=fd, `RSI`=buf, `RDX`=count | Bytes written | `-EBADF` (9), `-EFAULT` (14), `-EINVAL` (22) |
| **`sys_open`** | `2` | `RDI`=path_ptr, `RSI`=flags, `RDX`=mode | Allocated FD | `-ENOENT` (2), `-EACCES` (13), `-EEXIST` (17) |
| **`sys_close`** | `3` | `RDI`=fd | `0` | `-EBADF` (9) |
| **`sys_brk`** | `12` | `RDI`=new_brk | Current / New brk | `-ENOMEM` (12) |
| **`sys_fork`** | `57` | *(None)* | Child PID to parent, `0` to child | `-EAGAIN` (11) if process cap reached |
| **`sys_exit`** | `60` | `RDI`=status | *(Process terminates)* | *(None)* |

**Table 3.2: POSIX Error Numbers (`errno`) Handled by Simulated Kernel**
| Symbolic Constant | Numeric Value | Description |
|---|---|---|
| `ENOENT` | `2` | No such file or directory |
| `EBADF` | `9` | Bad file descriptor |
| `EAGAIN` | `11` | Resource temporarily unavailable (process limit reached) |
| `ENOMEM` | `12` | Cannot allocate memory (out of virtual memory) |
| `EACCES` | `13` | Permission denied |
| `EFAULT` | `14` | Bad address (unmapped virtual address dereference) |
| `EEXIST` | `17` | File exists |
| `ENOTDIR` | `20` | Not a directory |
| `EISDIR` | `21` | Is a directory |
| `EINVAL` | `22` | Invalid argument passed |

### 3.5 Interactive Assembly Interpreter (REPL)

**Table 3.3: Interactive Assembly REPL Command Reference**
| Command | Syntax Example | Functional Description |
|---|---|---|
| `MOV` | `MOV RAX, 1` | Assigns an immediate integer, hexadecimal value, or ASCII character to a register. |
| `MOV [addr], val` | `MOV [0x600000], 65` | Stores a byte directly into the specified virtual memory address. |
| `SYSCALL` | `SYSCALL` | Triggers a fast hardware trap via `MSR_LSTAR` and executes the 6-step lifecycle. |
| `INT 0x80` | `INT 0x80` | Triggers a software interrupt trap via IDT Vector 128. |
| `DUMP` | `DUMP` | Prints current registers, privilege level, virtual memory boundaries, and open FDs. |
| `LS_DISK` | `LS_DISK /tmp` | Lists files, directories, sizes, and permissions on the virtual disk. |
| `CAT` | `CAT /tmp/demo.txt` | Displays the raw content of a virtual file. |
| `LOAD` | `LOAD hello_world` | Loads pre-configured assembly programs (`hello_world`, `file_io`, `heap_alloc`, `fork_bomb_guard`). |
| `STEP` / `RUN` | `STEP` or `RUN` | Steps through a single instruction or executes all instructions until `sys_exit`. |
| `INPUT` | `INPUT Hello World` | Loads input text into the simulated STDIN buffer for `sys_read(0, ...)`. |
| `MEM` | `MEM 0x600000 32` | Displays a formatted hexadecimal dump of virtual memory. |
| `PS` | `PS` | Displays the kernel Process Table showing PIDs, PPIDs, states, and heap breaks. |
| `HELP` / `EXIT` | `HELP` | Prints command reference or terminates the simulator session. |

---

# CHAPTER 4: EXPERIMENTAL RESULTS AND VERIFICATION

### 4.1 Test Harness & Automated Unit Verification
To confirm robustness and compliance with standard kernel behavior, an automated test suite was constructed in `test_kernel_sim.py` containing **42 unit tests** spanning every architectural layer.

**Table 4.1: Automated Unit Test Suite Summary (42 Test Cases)**
| Test Category | Number of Tests | Verified Behaviors |
|---|---|---|
| **CPU Core & Registers** | 6 | 64-bit integer clamping, register preservation, flag manipulation, privilege changes. |
| **Virtual Memory Manager** | 8 | Heap expansion via `brk`, boundary checking, write protection on `.text`, `SIGSEGV` triggers. |
| **Virtual File System** | 8 | Inode creation, directory walking, file truncating, append mode, `/dev/null` discarding. |
| **File Descriptor Table** | 6 | Standard stream inheritance, dynamic allocation `>= 3`, reference counting, FD exhaustion. |
| **POSIX System Calls** | 10 | POSIX errno returns (`-EBADF`, `-EFAULT`, `-ENOENT`, `-EISDIR`), buffer copying, clean exits. |
| **Process Management** | 4 | `sys_fork` child register isolation (`RAX=0`), memory duplication, fork-bomb guard (`EAGAIN`). |

Execution of the test suite yielded 100% pass rates:
```text
$ python -m unittest test_kernel_sim.py
..........................................
----------------------------------------------------------------------
Ran 42 tests in 8.284s

OK
```

### 4.2 Step-by-Step Trap Execution Trace
Executing `LOAD hello_world` followed by `RUN` generates the full 6-step visual execution trace:

```text
╔════════════════════════════════════════════════════════════════════════════════╗
║                      CPU HARDWARE TRAP: SYSCALL DISPATCH                       ║
║      Transition: Ring 3 (User) ➔ Ring 0 (Kernel) | Syscall #1 (sys_write)      ║
╚════════════════════════════════════════════════════════════════════════════════╝
┌─ [STEP 1] CPU Trap Detected (MSR_LSTAR) ─────────────────────────────────────
│  Active Process: PID 1000 ('shell') | PPID: 1
│  Instruction: SYSCALL at RIP: 0x0000000000400002
│  Trap Entry: MSR_LSTAR Fast Syscall Entry (Register 0xC0000082)
│  Privilege Mode: Ring 3 (RING_3) | Syscall Requested: RAX = 1
└───────────────────────────────────────────────────────────────────────────────
┌─ [STEP 2] Hardware Context Save (Push struct pt_regs to Kernel Stack) ───────
│  Saving User Registers onto Kernel Stack (TSS RSP0: 0xffff80003e80ffe0):
│    RAX: 0x0000000000000001   RDI: 0x0000000000000001
│    RSI: 0x0000000000402000   RDX: 0x000000000000000e
│    RSP: 0x00007fffffffe000   RIP: 0x0000000000400002
└───────────────────────────────────────────────────────────────────────────────
┌─ [STEP 3] Privilege & Stack Switch (Ring 3 ➔ Ring 0) ────────────────────────
│  CPL Transition: Ring 3 (USER) ➔ Ring 0 (SUPERVISOR)
│  Stack Switch: RSP shifted from User 0x00007fffffffe000 ➔ Kernel 0xffff80003e80ffe0
└───────────────────────────────────────────────────────────────────────────────
┌─ [STEP 4] Interrupt Vector Table (IVT) Lookup & Parameter Decoding ──────────
│  Vector Index: RAX = 1 ➔ Handler: sys_write
│  ABI Arguments: Arg 1 (RDI): 1, Arg 2 (RSI): 0x402000, Arg 3 (RDX): 14
└───────────────────────────────────────────────────────────────────────────────
[STDOUT PID 1000] Hello, World!
┌─ [STEP 5] Kernel Subsystem Execution (sys_write) ────────────────────────────
│  Kernel execution completed: return_code = 14 (bytes written)
└───────────────────────────────────────────────────────────────────────────────
┌─ [STEP 6] Context Restoration & SYSRETQ (Ring 0 ➔ Ring 3) ───────────────────
│  Writing syscall result 14 into RAX.
│  SYSRETQ: Privilege Level: Ring 0 ➔ Ring 3 (USER)
│  Restoring User Stack Pointer: RSP ➔ 0x00007fffffffe000
│  Resuming User Execution at RIP: 0x0000000000400004
└───────────────────────────────────────────────────────────────────────────────
✔ Trap Complete. Resumed User Space (PID 1000, Ring 3). RAX = 14
```

### 4.3 Virtual Memory Violation (`SIGSEGV`) Demonstration
To evaluate memory isolation, user code passes an invalid address (`0x99999999`) to `sys_write`. The Virtual Memory Manager intercepts the access, aborts the system call, returns `-EFAULT` (`-14`), and displays a detailed Segmentation Fault diagnostic report:

```text
[KERNEL FAULT DETECTED]
Signal: SIGSEGV (Signal 11: Segmentation Violation)
Faulting Address: 0x0000000099999999 (Address is outside mapped virtual memory)
Current Break: 0x0000000000600000
Action: Terminating faulting process or returning -EFAULT (-14) to caller.
```

### 4.4 Process Duplication (`sys_fork`) & Fork-Bomb Guard
Running the `fork_bomb_guard` demo tests process isolation and resource limits. When `sys_fork` executes in a loop, the process table dynamically tracks spawned processes until reaching the configured ceiling of 32 processes. Subsequent forks are rejected with `-EAGAIN` (`-11`), preventing host resource starvation.

---

# CHAPTER 5: CONCLUSION AND FUTURE SCOPE

### 5.1 Conclusion
This project successfully designed and implemented an interactive, production-grade System Call & Kernel Trap Simulator in pure Python with zero external dependencies. The simulator faithfully models the x86_64 architecture's privilege ring transitions, Task State Segment stack switching, ABI register conventions, in-memory Virtual File System, per-process descriptor tables, virtual memory boundary enforcement, and process lifecycle management.

Through 42 automated unit tests and interactive REPL demonstrations, the system was verified to adhere rigorously to POSIX error codes and architectural calling conventions. The simulator bridges the pedagogical gap between abstract operating system theory and tangible software implementation, providing a transparent, crash-resilient environment for student learning and system call exploration.

### 5.2 Future Scope
Future enhancements planned for the simulator include:
1. **Multi-Core SMP & Preemptive Scheduling**: Modeling timer interrupt ticks (PIT/APIC) to preempt running processes and simulate round-robin multi-process scheduling.
2. **Paging & TLB Simulation**: Simulating multi-level 4-level page table walks (PML4, PDPT, PD, PT) and Translation Lookaside Buffer (TLB) hit/miss metrics.
3. **Inter-Process Communication (IPC)**: Implementing `sys_pipe` (RAX=22) and Unix domain sockets for inter-process data exchange.
4. **Signal Handling Subsystem**: Adding support for `sys_rt_sigaction` and user-space signal handler trampolines via `sigreturn`.

---

## REFERENCES
1. Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). *Operating System Concepts* (10th ed.). Wiley.
2. Tanenbaum, A. S., & Bos, H. (2015). *Modern Operating Systems* (4th ed.). Pearson.
3. Bovet, D. P., & Cesati, M. (2005). *Understanding the Linux Kernel* (3rd ed.). O'Reilly Media.
4. Love, R. (2010). *Linux Kernel Development* (3rd ed.). Addison-Wesley Professional.
5. Intel Corporation (2023). *Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A: System Programming Guide*.
6. IEEE and The Open Group (2018). *The Open Group Base Specifications Issue 7 / IEEE Std 1003.1-2017 (POSIX.1)*.
