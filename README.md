# x86_64 System Call & Kernel Trap Simulator

A production-grade, interactive operating system simulator implemented in pure Python (standard library only, zero external dependencies). Realistically models how modern x86_64 operating systems (such as Linux) handle user-to-kernel space context transitions, privilege rings, virtual memory safety, process control blocks, and POSIX system call execution.

---

## 🏛️ Architecture Overview

```
                      +---------------------------------------+
                      |      Ring 3: User Space Program       |
                      |   (Registers: RAX, RDI, RSI, ...)     |
                      +---------------------------------------+
                                          |
                         [SYSCALL] or [INT 0x80] Hardware Trap
                                          v
                      +---------------------------------------+
                      | CPU Hardware Context Save             |
                      | Push struct pt_regs to Kernel Stack   |
                      | RSP -> Kernel RSP (TSS rsp0)          |
                      | Privilege Switch: Ring 3 -> Ring 0    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      | Interrupt Vector Table (IVT) Dispatch |
                      | Lookup RAX System Call Vector         |
                      +---------------------------------------+
                                          |
            +-----------------------------+-----------------------------+
            |                             |                             |
            v                             v                             v
  +-------------------+         +-------------------+         +-------------------+
  | Virtual File Sys  |         | Memory Management |         |  Process Table    |
  | Inodes, Dentries  |         | Page Tables, brk  |         | PCB, State, FDs   |
  | sys_open/read/etc |         | SIGSEGV Checks    |         | sys_fork/sys_exit |
  +-------------------+         +-------------------+         +-------------------+
            |                             |                             |
            +-----------------------------+-----------------------------+
                                          |
                                Return Value -> RAX
                                          v
                      +---------------------------------------+
                      | Context Restoration & SYSRETQ / IRETQ |
                      | Pop struct pt_regs, Restore RSP & RIP |
                      | Privilege Switch: Ring 0 -> Ring 3    |
                      +---------------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Resume Ring 3 User Space         |
                      |         (RAX = Return Code)           |
                      +---------------------------------------+
```

---

## 🚀 Key Architectural Specifications

### 1. CPU & Hardware Emulation
* **64-bit General Purpose Registers**: `RAX`, `RDI`, `RSI`, `RDX`, `R10`, `R8`, `R9`, `RSP`, `RIP`, `RFLAGS`.
* **Privilege Rings**: `Ring 3` (User Space unprivileged) vs `Ring 0` (Supervisor Kernel Space).
* **Interrupt Vector Table (IVT)**: Extensible vector dispatch table mapping system call numbers to kernel routines.
* **Hardware Trap (`SYSCALL` / `INT 0x80`)**:
  - Automatically pushes `struct pt_regs` snapshot to the process kernel stack (`TSS rsp0`).
  - Switches Current Privilege Level (CPL): Ring 3 ➔ Ring 0.
  - Validates user pointers and executes kernel subsystems.
  - Returns result in `pt_regs.RAX` and invokes `SYSRETQ` to restore user context.

### 2. Kernel Subsystems & State
* **In-Memory VFS (Virtual File System)**:
  - Inodes with type (`REGULAR`, `DIR`, `CHAR_DEV`), octal permissions, size, and timestamps.
  - POSIX directory hierarchy: `/`, `/etc` (`os-release`, `motd`, `hostname`), `/home/user`, `/tmp`, and `/dev` (`null`, `zero`).
  - Standard POSIX open flags: `O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_CREAT`, `O_EXCL`, `O_TRUNC`, `O_APPEND`.
* **Per-Process File Descriptor Table**:
  - Maps integer descriptors to open file descriptions.
  - Pre-allocated `0` (STDIN), `1` (STDOUT), `2` (STDERR), and dynamic file descriptors `>= 3`.
  - Shared open file offsets across processes spawned via `sys_fork`.
* **Virtual Memory Manager (VMM) & Heap Break**:
  - Canonical 48-bit user virtual memory layout: Text (`0x00400000`), Static Data (`0x00402000`), Heap (`0x00600000` `start_brk`), and Stack (`0x7FFFFFFFE000`).
  - Dynamic heap expansion/contraction (`sys_brk`).
  - **Memory Safety Protection**: Invalid pointer dereferences trigger `SIGSEGV` and return `-EFAULT` (14).
* **Process Control Block (PCB) & Process Table**:
  - Tracks PID, PPID, execution state (`RUNNING`, `READY`, `TERMINATED`), priority, registers, memory space, and file descriptor table.
  - `sys_fork` with copy-on-write page emulation.
  - **Fork Bomb Guard**: Safeguard threshold preventing system exhaustion, returning `-EAGAIN` (11).

---

## 📜 POSIX / x86_64 System Call Table

| Syscall | RAX | Parameters (ABI: RDI, RSI, RDX, R10, R8, R9) | Description |
|---|:---:|---|---|
| `sys_read` | `0` | `RDI` = fd, `RSI` = buf_addr, `RDX` = count | Reads bytes from fd into user memory |
| `sys_write` | `1` | `RDI` = fd, `RSI` = buf_addr, `RDX` = count | Writes bytes from user memory to fd |
| `sys_open` | `2` | `RDI` = path_addr, `RSI` = flags, `RDX` = mode | Opens/creates file, returns fd |
| `sys_close` | `3` | `RDI` = fd | Closes file descriptor handle |
| `sys_brk` | `12` | `RDI` = new_brk | Queries (`0`) or expands heap break |
| `sys_fork` | `57` | *(none)* | Duplicates PCB (child PID in parent, 0 in child) |
| `sys_exit` | `60` | `RDI` = exit_code | Terminates process and releases resources |

---

## 💻 Interactive REPL & Assembly Emulator

Run the simulator in interactive REPL mode:
```bash
python kernel_sim.py
```

### Supported Commands:
* `MOV <REG>, <VAL>`: Assign register with an integer, hex (`0x...`), another register, or a quoted string literal `MOV RSI, "Hello\n"` (automatically stored in user data memory).
* `SYSCALL` / `INT 0x80`: Trigger the hardware trap into Ring 0 kernel space.
* `DUMP`: Show live 64-bit registers in Hex and Decimal, CPL privilege ring, memory boundaries, and open file descriptors.
* `LS_DISK`: Display inode table, permissions, sizes, and file paths on the virtual hard disk.
* `CAT <filepath>`: Inspect contents of a file on the virtual disk.
* `LOAD <demo_name>`: Load a pre-configured assembly program:
  * `hello_world`: Syscall write to STDOUT and exit.
  * `file_io`: Full lifecycle test: create, write, close, open, read into heap, echo to STDOUT.
  * `fork_bomb_guard`: Repeated forks demonstrating kernel throttle returning `-EAGAIN`.
  * `heap_alloc`: Query break, illegal write (SIGSEGV prevention), heap expansion via `sys_brk`, and safe heap write.
* `LIST`: Display instructions of the currently loaded demo program.
* `STEP`: Execute one instruction from the loaded program.
* `RUN`: Execute loaded program to completion.
* `MEM <addr> [len]`: Display virtual memory hexdump at address.
* `STORE <addr> <val/string>`: Write raw bytes or string to virtual memory.
* `PS`: Display kernel process table.
* `SWITCH <pid>`: Switch active CPU context to target process.
* `RESET`: Reset CPU and processes to clean initial state.
* `HELP`: Show full command manual.
* `EXIT`: Terminate simulator.

---

## 🧪 Running Automated Tests

Run the built-in test suite:
```bash
python kernel_sim.py --test
```
Or run the dedicated `unittest` test suite:
```bash
python -m unittest test_kernel_sim.py
```

---

## 📄 Batch Script Execution

You can run assembly scripts directly from a file:
```bash
python kernel_sim.py sample.asm
```
