#!/usr/bin/env python3
"""
================================================================================
System Call & Kernel Trap Simulator (x86_64 Architecture)
================================================================================
A production-grade, interactive operating system simulator implemented in pure
Python standard library. Realistically models how modern x86_64 OS kernels (like
Linux) handle user-to-kernel space context transitions, privilege rings, virtual
memory safety, process management, and POSIX system call execution.

Key Architectural Components:
1. CPU & Hardware Emulation:
   - 64-bit general-purpose registers (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS)
   - Privilege rings: Ring 3 (User Space) vs Ring 0 (Kernel Space)
   - Interrupt Vector Table (IVT) & MSR_LSTAR syscall entry dispatcher
   - Hardware trap mechanism with automatic pt_regs stack frame save/restore

2. Kernel Subsystems & State:
   - In-memory Virtual File System (VFS) with inodes, dentries, permissions, and /dev nodes
   - Per-process File Descriptor Table (fd 0 STDIN, 1 STDOUT, 2 STDERR, dynamic handles)
   - Virtual Memory Manager (VMM) with page mappings, heap break (brk/sbrk), and SIGSEGV traps
   - Process Control Block (PCB) & Process Table with PID, PPID, state, priority, and snapshots

3. POSIX/x86_64 System Calls:
   - sys_read  (RAX=0)  : Read from stdin or open VFS file descriptor
   - sys_write (RAX=1)  : Write to stdout, stderr, or VFS file
   - sys_open  (RAX=2)  : Open or create file with POSIX flags (O_RDONLY, O_WRONLY, O_CREAT, etc.)
   - sys_close (RAX=3)  : Release file descriptor
   - sys_brk   (RAX=12) : Query or adjust program heap break
   - sys_fork  (RAX=57) : Duplicate PCB, VMM, and register state with fork bomb guard
   - sys_exit  (RAX=60) : Terminate process and report exit status

4. Interactive REPL & Assembly Emulator:
   - MOV, SYSCALL, INT 0x80, DUMP, LS_DISK, CAT, LOAD, STEP, RUN, STORE, MEM, PS, HELP, EXIT

Author: Senior Operating Systems Engineer
License: MIT / Public Domain
================================================================================
"""

import sys
import os
import time
import enum
import shlex
import struct
from typing import Dict, List, Optional, Tuple, Callable, Any, Union
from dataclasses import dataclass, field

# Enable UTF-8 encoding and ANSI Virtual Terminal Processing on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        os.system("")  # Initialize Windows 10/11 VT100 ANSI mode
    except Exception:
        pass

# ==============================================================================
# SECTION 1: TERMINAL COLORS & VISUAL FORMATTING
# ==============================================================================

class Colors:
    """ANSI color codes with terminal auto-detection."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground standard
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Foreground bright
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_BLUE = "\033[44m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_DARK = "\033[48;5;236m"

_COLOR_ENABLED = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"

def colorize(text: str, *styles: str) -> str:
    """Applies ANSI color styles if color output is enabled."""
    if not _COLOR_ENABLED or not styles:
        return text
    prefix = "".join(styles)
    return f"{prefix}{text}{Colors.RESET}"


# ==============================================================================
# SECTION 2: CONSTANTS, POSIX ERRNO, OPEN FLAGS & PRIVILEGE LEVELS
# ==============================================================================

class PrivilegeLevel(enum.IntEnum):
    """CPU Execution Rings (Current Privilege Level - CPL)."""
    RING_0 = 0  # Supervisor / Kernel Space
    RING_1 = 1  # Hypervisor / Device Drivers (uncommon in modern OS)
    RING_2 = 2  # OS Services (uncommon in modern OS)
    RING_3 = 3  # User Space (Unprivileged Application Code)


class PosixErrno(enum.IntEnum):
    """Standard POSIX Error Numbers (Linux x86_64 aligned)."""
    SUCCESS = 0
    EPERM   = 1    # Operation not permitted
    ENOENT  = 2    # No such file or directory
    ESRCH   = 3    # No such process
    EIO     = 5    # Input/output error
    EBADF   = 9    # Bad file descriptor
    EAGAIN  = 11   # Resource temporarily unavailable / Try again (fork limit)
    ENOMEM  = 12   # Cannot allocate memory
    EACCES  = 13   # Permission denied
    EFAULT  = 14   # Bad address (Segmentation fault)
    EEXIST  = 17   # File exists
    EINVAL  = 22   # Invalid argument
    ENFILE  = 23   # Too many open files in system
    EMFILE  = 24   # Too many open files for process
    ENOSYS  = 38   # Invalid system call number


# POSIX File Open Flags
O_RDONLY = 0x0000
O_WRONLY = 0x0001
O_RDWR   = 0x0002
O_CREAT  = 0x0040
O_EXCL   = 0x0080
O_TRUNC  = 0x0200
O_APPEND = 0x0400

# x86_64 Virtual Address Space Layout (Simulated 48-bit Canonical Layout)
USER_TEXT_BASE    = 0x0000000000400000  # Default ELF binary base (4MB)
USER_DATA_BASE    = 0x0000000000402000  # Initial data / string literals section
USER_HEAP_START   = 0x0000000000600000  # Initial program break (start_brk)
USER_HEAP_MAX     = 0x0000000000800000  # Maximum heap ceiling (2MB for simulation)
USER_STACK_TOP    = 0x00007FFFFFFFFFF0  # Top of user stack
USER_STACK_INIT   = 0x00007FFFFFFFE000  # Initial user stack pointer (RSP)
USER_SPACE_CEIL   = 0x00007FFFFFFFFFFF  # Upper boundary of canonical user space
KERNEL_SPACE_BASE = 0xFFFF800000000000  # Start of kernel virtual space

# RFLAGS bitmask constants
RFLAGS_IF = 0x0200  # Interrupt Flag enabled
RFLAGS_ZF = 0x0040  # Zero Flag
RFLAGS_DEFAULT = 0x0202  # Standard Linux userspace initial RFLAGS

# 64-bit integer mask
MASK_64 = 0xFFFFFFFFFFFFFFFF


def to_u64(val: int) -> int:
    """Wraps an integer into a 64-bit unsigned integer."""
    return val & MASK_64


def to_i64(val: int) -> int:
    """Interprets a 64-bit unsigned integer as a signed two's complement integer."""
    val = val & MASK_64
    if val >= (1 << 63):
        return val - (1 << 64)
    return val


def errno_to_u64(err: PosixErrno) -> int:
    """Encodes a negative POSIX error code as an unsigned 64-bit return value."""
    return to_u64(-int(err))


def format_u64(val: int) -> str:
    """Formats a 64-bit integer in hexadecimal and decimal."""
    u_val = to_u64(val)
    i_val = to_i64(val)
    if i_val < 0 and i_val >= -133:
        # Recognized negative errno
        try:
            err_name = PosixErrno(-i_val).name
            return f"0x{u_val:016x} ({i_val} -{err_name})"
        except ValueError:
            pass
    return f"0x{u_val:016x} ({u_val})"


# ==============================================================================
# SECTION 3: VIRTUAL MEMORY MANAGER & SEGMENTATION FAULT PROTECTION
# ==============================================================================

class SegmentationFault(Exception):
    """Raised when user-space code references unmapped or forbidden memory."""
    def __init__(self, message: str, fault_addr: int):
        super().__init__(message)
        self.fault_addr = fault_addr


class VirtualMemoryManager:
    """
    Simulates a per-process 48-bit virtual address space.
    Enforces page boundary checks, tracks program break (brk/sbrk),
    and raises SIGSEGV upon out-of-bounds dereferences.
    """
    PAGE_SIZE = 4096  # 4KB pages

    def __init__(self, pid: int):
        self.pid = pid
        # Virtual pages: page_aligned_addr -> bytearray(4096)
        self.pages: Dict[int, bytearray] = {}

        # Memory boundaries
        self.text_base = USER_TEXT_BASE
        self.data_base = USER_DATA_BASE
        self.start_brk = USER_HEAP_START
        self.current_brk = USER_HEAP_START
        self.max_brk = USER_HEAP_MAX
        self.stack_top = USER_STACK_TOP
        self.stack_base = USER_STACK_INIT

        # Initialize data segment page
        self._ensure_page(self.data_base)
        self._data_alloc_offset = self.data_base

        # Initialize user stack page
        self._ensure_page(self.stack_base)

    def _page_align(self, addr: int) -> int:
        return addr & ~(self.PAGE_SIZE - 1)

    def _ensure_page(self, addr: int) -> bytearray:
        page_addr = self._page_align(addr)
        if page_addr not in self.pages:
            self.pages[page_addr] = bytearray(self.PAGE_SIZE)
        return self.pages[page_addr]

    def is_address_valid(self, addr: int, size: int = 1, is_write: bool = False) -> bool:
        """
        Validates if [addr, addr + size) falls strictly within mapped user memory.
        Mapped areas:
        - Text/Data segment: [USER_TEXT_BASE, USER_TEXT_BASE + 0x100000)
        - Allocated Heap:    [USER_HEAP_START, current_brk)
        - Stack segment:     [stack_ptr, USER_STACK_TOP)
        """
        if addr < USER_TEXT_BASE or (addr + size) > USER_SPACE_CEIL:
            return False

        # Check each page touched by the range
        curr = addr
        end = addr + size
        while curr < end:
            # Segment 1: Text / Static Data
            in_text_data = (USER_TEXT_BASE <= curr < USER_TEXT_BASE + 0x100000)
            # Segment 2: Allocated Heap
            in_heap = (self.start_brk <= curr < self.current_brk)
            # Segment 3: User Stack (allow 64KB around stack pointer)
            in_stack = (USER_STACK_INIT - 0x10000 <= curr <= USER_STACK_TOP)

            if not (in_text_data or in_heap or in_stack):
                return False

            # Move to next page
            curr = self._page_align(curr) + self.PAGE_SIZE
        return True

    def validate_range(self, addr: int, size: int, is_write: bool = False):
        """Raises SegmentationFault if the range is invalid."""
        if size == 0:
            return
        if not self.is_address_valid(addr, size, is_write):
            raise SegmentationFault(
                f"SIGSEGV: Invalid memory reference at virtual address 0x{addr:016x} (size={size})",
                fault_addr=addr
            )

    def read_bytes(self, addr: int, count: int) -> bytes:
        """Reads count bytes from user virtual memory, raising SIGSEGV if unmapped."""
        self.validate_range(addr, count, is_write=False)
        result = bytearray()
        for i in range(count):
            curr_addr = addr + i
            page_addr = self._page_align(curr_addr)
            offset = curr_addr % self.PAGE_SIZE
            page = self._ensure_page(page_addr)
            result.append(page[offset])
        return bytes(result)

    def write_bytes(self, addr: int, data: bytes):
        """Writes data into user virtual memory, raising SIGSEGV if unmapped."""
        self.validate_range(addr, len(data), is_write=True)
        for i, byte in enumerate(data):
            curr_addr = addr + i
            page_addr = self._page_align(curr_addr)
            offset = curr_addr % self.PAGE_SIZE
            page = self._ensure_page(page_addr)
            page[offset] = byte

    def read_string(self, addr: int, max_len: int = 1024) -> str:
        """Reads a null-terminated string starting at addr."""
        chars = bytearray()
        for i in range(max_len):
            curr_addr = addr + i
            self.validate_range(curr_addr, 1, is_write=False)
            page_addr = self._page_align(curr_addr)
            offset = curr_addr % self.PAGE_SIZE
            page = self._ensure_page(page_addr)
            b = page[offset]
            if b == 0:
                break
            chars.append(b)
        else:
            raise SegmentationFault(
                f"SIGSEGV: Unterminated string exceeded {max_len} bytes at 0x{addr:016x}",
                fault_addr=addr
            )
        return chars.decode("utf-8", errors="replace")

    def allocate_static_string(self, s: str) -> int:
        """Stores a string literal in the data segment and returns its address."""
        encoded = s.encode("utf-8") + b"\x00"
        addr = self._data_alloc_offset
        self.write_bytes(addr, encoded)
        self._data_alloc_offset += len(encoded)
        # 8-byte align next allocation
        self._data_alloc_offset = (self._data_alloc_offset + 7) & ~7
        return addr

    def sys_brk(self, new_brk: int) -> int:
        """
        Implements sys_brk (POSIX/Linux semantics):
        - If new_brk == 0: query program break.
        - If new_brk < start_brk: reject, return current_brk.
        - If new_brk > max_brk: reject (ENOMEM), return current_brk.
        - If valid: adjust program break, zeroing newly allocated pages.
        """
        if new_brk == 0:
            return self.current_brk

        if new_brk < self.start_brk:
            return self.current_brk

        if new_brk > self.max_brk:
            # Memory ceiling exceeded
            return self.current_brk

        old_brk = self.current_brk
        self.current_brk = new_brk

        # If expanding, ensure all pages up to new_brk exist and are zeroed
        if new_brk > old_brk:
            curr = self._page_align(old_brk)
            end = self._page_align(new_brk + self.PAGE_SIZE - 1)
            while curr < end:
                self._ensure_page(curr)
                curr += self.PAGE_SIZE
        else:
            # If contracting heap, purge freed pages
            pages_to_remove = [
                p for p in self.pages
                if self.start_brk <= p and p >= self._page_align(new_brk + self.PAGE_SIZE - 1)
            ]
            for p in pages_to_remove:
                del self.pages[p]

        return self.current_brk

    def clone(self, new_pid: int) -> "VirtualMemoryManager":
        """Duplicates virtual memory space for sys_fork (copy-on-write simulation)."""
        new_vmm = VirtualMemoryManager(new_pid)
        new_vmm.current_brk = self.current_brk
        new_vmm._data_alloc_offset = self._data_alloc_offset
        new_vmm.pages = {
            addr: bytearray(page_bytes)
            for addr, page_bytes in self.pages.items()
        }
        return new_vmm


# ==============================================================================
# SECTION 4: IN-MEMORY VIRTUAL FILE SYSTEM (VFS)
# ==============================================================================

class InodeType(enum.Enum):
    FILE = "REGULAR"
    DIRECTORY = "DIR"
    CHAR_DEV = "CHAR_DEV"


@dataclass
class Inode:
    """Represents a VFS Inode on the virtual hard disk."""
    ino: int
    name: str
    itype: InodeType
    permissions: int = 0o644
    data: bytearray = field(default_factory=bytearray)
    entries: Dict[str, int] = field(default_factory=dict)  # name -> ino for dirs
    uid: int = 1000
    gid: int = 1000
    ctime: float = field(default_factory=time.time)
    mtime: float = field(default_factory=time.time)
    atime: float = field(default_factory=time.time)

    # Optional character device hooks
    read_device: Optional[Callable[[int], bytes]] = None
    write_device: Optional[Callable[[bytes], int]] = None

    @property
    def size(self) -> int:
        if self.itype == InodeType.DIRECTORY:
            return len(self.entries) * 32
        return len(self.data)


@dataclass
class OpenFileDescription:
    """Kernel open file state shared across duplicated file descriptors."""
    inode: Inode
    flags: int
    offset: int = 0
    ref_count: int = 1


class VirtualFileSystem:
    """
    Production-grade in-memory VFS with virtual inodes, permissions,
    directory hierarchies, and POSIX /dev devices.
    """
    def __init__(self):
        self.inodes: Dict[int, Inode] = {}
        self._next_ino = 1
        self._init_default_tree()

    def _allocate_inode(self, name: str, itype: InodeType, perms: int) -> Inode:
        ino = self._next_ino
        self._next_ino += 1
        inode = Inode(ino=ino, name=name, itype=itype, permissions=perms)
        self.inodes[ino] = inode
        return inode

    def _init_default_tree(self):
        """Builds standard Linux root filesystem tree (/etc, /dev, /home, /tmp)."""
        # Root directory (ino 1)
        root = self._allocate_inode("/", InodeType.DIRECTORY, 0o755)
        root.entries["."] = root.ino
        root.entries[".."] = root.ino

        # Standard directories
        self.mkdir("/", "etc", 0o755)
        self.mkdir("/", "dev", 0o755)
        self.mkdir("/", "home", 0o755)
        self.mkdir("/home", "user", 0o755)
        self.mkdir("/", "tmp", 0o777)

        # /etc system files
        self.create_file(
            "/etc", "os-release",
            b'NAME="KernelSim Linux"\nVERSION="6.1.0-custom-x86_64"\nID=kernelsim\n',
            0o644
        )
        self.create_file(
            "/etc", "motd",
            b"=====================================================\n"
            b" Welcome to the System Call & Kernel Trap Simulator! \n"
            b" Architecture: x86_64 (Ring 0 / Ring 3 privilege)   \n"
            b"=====================================================\n",
            0o644
        )
        self.create_file("/etc", "hostname", b"kernelsim-x86-64\n", 0o644)

        # /home/user sample files
        self.create_file(
            "/home/user", "readme.txt",
            b"Simulated Linux Virtual File System (VFS).\n"
            b"Test POSIX system calls sys_open, sys_read, sys_write, and sys_close!\n",
            0o644
        )

        # Special character devices
        self._create_char_dev("/dev", "null", lambda n: b"", lambda b: len(b))
        self._create_char_dev("/dev", "zero", lambda n: b"\x00" * n, lambda b: len(b))

    def _create_char_dev(
        self, parent_path: str, name: str,
        read_fn: Callable[[int], bytes], write_fn: Callable[[bytes], int]
    ):
        parent = self.resolve_path(parent_path)
        if not parent or parent.itype != InodeType.DIRECTORY:
            return
        dev_inode = self._allocate_inode(name, InodeType.CHAR_DEV, 0o666)
        dev_inode.read_device = read_fn
        dev_inode.write_device = write_fn
        parent.entries[name] = dev_inode.ino

    def resolve_path(self, path: str, cwd: str = "/") -> Optional[Inode]:
        """Resolves an absolute or relative path to its Inode."""
        if not path:
            return None

        # Normalize path
        if not path.startswith("/"):
            path = os.path.normpath(os.path.join(cwd, path))
        else:
            path = os.path.normpath(path)

        path = path.replace("\\", "/")
        parts = [p for p in path.split("/") if p and p != "."]

        curr = self.inodes[1]  # root
        for part in parts:
            if curr.itype != InodeType.DIRECTORY:
                return None
            if part not in curr.entries:
                return None
            ino = curr.entries[part]
            curr = self.inodes[ino]
        return curr

    def mkdir(self, parent_path: str, name: str, perms: int = 0o755) -> Optional[Inode]:
        parent = self.resolve_path(parent_path)
        if not parent or parent.itype != InodeType.DIRECTORY:
            return None
        if name in parent.entries:
            return None
        dir_inode = self._allocate_inode(name, InodeType.DIRECTORY, perms)
        dir_inode.entries["."] = dir_inode.ino
        dir_inode.entries[".."] = parent.ino
        parent.entries[name] = dir_inode.ino
        return dir_inode

    def create_file(self, parent_path: str, name: str, data: bytes = b"", perms: int = 0o644) -> Optional[Inode]:
        parent = self.resolve_path(parent_path)
        if not parent or parent.itype != InodeType.DIRECTORY:
            return None
        if name in parent.entries:
            return None
        file_inode = self._allocate_inode(name, InodeType.FILE, perms)
        file_inode.data = bytearray(data)
        parent.entries[name] = file_inode.ino
        return file_inode

    def open_file(self, path: str, flags: int, mode: int = 0o644, cwd: str = "/") -> Tuple[Optional[OpenFileDescription], PosixErrno]:
        """Opens or creates a file according to POSIX flags."""
        target = self.resolve_path(path, cwd=cwd)

        # Check creation flag
        if target is None:
            if not (flags & O_CREAT):
                return None, PosixErrno.ENOENT

            # Resolve parent directory
            norm = os.path.normpath(os.path.join(cwd, path) if not path.startswith("/") else path).replace("\\", "/")
            parent_dir, basename = os.path.split(norm)
            parent_inode = self.resolve_path(parent_dir)
            if not parent_inode or parent_inode.itype != InodeType.DIRECTORY:
                return None, PosixErrno.ENOENT

            # Verify directory write permissions
            if not (parent_inode.permissions & 0o200):
                return None, PosixErrno.EACCES

            target = self._allocate_inode(basename, InodeType.FILE, mode)
            parent_inode.entries[basename] = target.ino
        else:
            # File exists
            if (flags & O_CREAT) and (flags & O_EXCL):
                return None, PosixErrno.EEXIST

            if target.itype == InodeType.DIRECTORY and ((flags & O_WRONLY) or (flags & O_RDWR)):
                return None, PosixErrno.EACCES

            # Check permissions
            is_write_req = bool((flags & O_WRONLY) or (flags & O_RDWR))
            is_read_req = not (flags & O_WRONLY)

            if is_read_req and not (target.permissions & 0o400):
                return None, PosixErrno.EACCES
            if is_write_req and not (target.permissions & 0o200):
                return None, PosixErrno.EACCES

            # Handle truncation
            if (flags & O_TRUNC) and is_write_req and target.itype == InodeType.FILE:
                target.data = bytearray()
                target.mtime = time.time()

        offset = len(target.data) if (flags & O_APPEND) else 0
        desc = OpenFileDescription(inode=target, flags=flags, offset=offset)
        return desc, PosixErrno.SUCCESS


# ==============================================================================
# SECTION 5: FILE DESCRIPTOR TABLE & STANDARD STREAMS
# ==============================================================================

class ConsoleStream:
    """Models stdin / stdout / stderr stream buffers."""
    def __init__(self, name: str, readable: bool, writable: bool):
        self.name = name
        self.readable = readable
        self.writable = writable
        self.read_buffer = bytearray()
        self.write_buffer = bytearray()

    def feed_input(self, data: bytes):
        self.read_buffer.extend(data)

    def read(self, count: int) -> bytes:
        if not self.readable:
            return b""
        actual = min(count, len(self.read_buffer))
        chunk = bytes(self.read_buffer[:actual])
        del self.read_buffer[:actual]
        return chunk

    def write(self, data: bytes) -> int:
        if not self.writable:
            return 0
        self.write_buffer.extend(data)
        return len(data)


class FileDescriptorTable:
    """Per-process file descriptor table mapping integer FDs to open descriptions."""
    MAX_FDS = 1024

    def __init__(self):
        # fd -> OpenFileDescription | ConsoleStream
        self.table: Dict[int, Union[OpenFileDescription, ConsoleStream]] = {}
        # Prepopulate standard streams
        self.table[0] = ConsoleStream("STDIN", readable=True, writable=False)
        self.table[1] = ConsoleStream("STDOUT", readable=False, writable=True)
        self.table[2] = ConsoleStream("STDERR", readable=False, writable=True)

    def allocate_fd(self, desc: Union[OpenFileDescription, ConsoleStream]) -> int:
        """Finds the lowest available descriptor number >= 3."""
        for fd in range(3, self.MAX_FDS):
            if fd not in self.table:
                self.table[fd] = desc
                if isinstance(desc, OpenFileDescription):
                    desc.ref_count += 1
                return fd
        return -int(PosixErrno.EMFILE)

    def get(self, fd: int) -> Optional[Union[OpenFileDescription, ConsoleStream]]:
        return self.table.get(fd)

    def close(self, fd: int) -> PosixErrno:
        if fd not in self.table:
            return PosixErrno.EBADF
        desc = self.table[fd]
        if isinstance(desc, OpenFileDescription):
            desc.ref_count -= 1
        del self.table[fd]
        return PosixErrno.SUCCESS

    def clone(self) -> "FileDescriptorTable":
        """Duplicates table for sys_fork, incrementing reference counts on open files."""
        new_table = FileDescriptorTable()
        new_table.table.clear()
        for fd, desc in self.table.items():
            if isinstance(desc, ConsoleStream):
                # Duplicate standard streams
                new_table.table[fd] = ConsoleStream(desc.name, desc.readable, desc.writable)
            elif isinstance(desc, OpenFileDescription):
                desc.ref_count += 1
                new_table.table[fd] = desc
        return new_table


# ==============================================================================
# SECTION 6: CPU REGISTERS, PT_REGS CONTEXT & PROCESS CONTROL BLOCK (PCB)
# ==============================================================================

REGISTER_NAMES = ("RAX", "RDI", "RSI", "RDX", "R10", "R8", "R9", "RSP", "RIP", "RFLAGS")

@dataclass
class PtRegs:
    """
    Snapshot of user CPU registers saved onto the kernel stack during trap entry.
    Mirrors Linux kernel struct pt_regs on x86_64.
    """
    rax: int = 0
    rdi: int = 0
    rsi: int = 0
    rdx: int = 0
    r10: int = 0
    r8: int = 0
    r9: int = 0
    rsp: int = 0
    rip: int = 0
    rflags: int = RFLAGS_DEFAULT
    cpl: int = PrivilegeLevel.RING_3

    def copy(self) -> "PtRegs":
        return PtRegs(
            rax=self.rax, rdi=self.rdi, rsi=self.rsi, rdx=self.rdx,
            r10=self.r10, r8=self.r8, r9=self.r9,
            rsp=self.rsp, rip=self.rip, rflags=self.rflags, cpl=self.cpl
        )


class ProcessState(enum.Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    READY = "READY"
    SLEEPING = "SLEEPING"
    ZOMBIE = "ZOMBIE"
    TERMINATED = "TERMINATED"


class PCB:
    """
    Process Control Block (PCB) tracking task execution state,
    registers, virtual memory, and open file descriptors.
    """
    def __init__(self, pid: int, ppid: int = 0, name: str = "init"):
        self.pid = pid
        self.ppid = ppid
        self.name = name
        self.state = ProcessState.READY
        self.priority = 20  # standard nice value
        self.cwd = "/home/user"
        self.exit_code: Optional[int] = None

        # 64-bit general purpose registers
        self.regs: Dict[str, int] = {reg: 0 for reg in REGISTER_NAMES}
        self.regs["RSP"] = USER_STACK_INIT
        self.regs["RIP"] = USER_TEXT_BASE
        self.regs["RFLAGS"] = RFLAGS_DEFAULT

        # Current CPU privilege ring
        self.cpl = PrivilegeLevel.RING_3

        # Subsystems
        self.vmm = VirtualMemoryManager(self.pid)
        self.fd_table = FileDescriptorTable()

        # Kernel stack context snapshot
        self.saved_pt_regs: Optional[PtRegs] = None
        # TSS Kernel Stack Pointer (Ring 0 RSP)
        self.kernel_rsp = KERNEL_SPACE_BASE | (0x100000 * self.pid) | 0xFFE0

    def read_reg(self, name: str) -> int:
        return self.regs[name.upper()]

    def write_reg(self, name: str, val: int):
        self.regs[name.upper()] = to_u64(val)


class ProcessManager:
    """Manages active processes, fork duplication, and process limits."""
    MAX_PROCESSES = 16  # Fork bomb guard threshold

    def __init__(self):
        self.processes: Dict[int, PCB] = {}
        self.active_pid: int = 1000
        self._next_pid: int = 1000

        # Initialize PID 1000 (primary user process)
        init_proc = PCB(pid=self.active_pid, ppid=1, name="shell")
        init_proc.state = ProcessState.RUNNING
        self.processes[self.active_pid] = init_proc

    @property
    def current(self) -> PCB:
        return self.processes[self.active_pid]

    def fork(self, parent: PCB) -> Tuple[Optional[PCB], PosixErrno]:
        """Duplicates PCB and memory space, returning (child_pcb, errno)."""
        if len(self.processes) >= self.MAX_PROCESSES:
            return None, PosixErrno.EAGAIN

        self._next_pid += 1
        child_pid = self._next_pid
        child = PCB(pid=child_pid, ppid=parent.pid, name=f"{parent.name}_child")

        # Duplicate register states
        child.regs = dict(parent.regs)
        child.cpl = parent.cpl
        child.cwd = parent.cwd
        child.priority = parent.priority
        child.state = ProcessState.READY

        # Clone VMM and File Descriptor Table
        child.vmm = parent.vmm.clone(child_pid)
        child.fd_table = parent.fd_table.clone()

        self.processes[child_pid] = child
        return child, PosixErrno.SUCCESS

    def terminate(self, proc: PCB, exit_code: int):
        """Terminates process, closing open handles."""
        proc.state = ProcessState.TERMINATED
        proc.exit_code = exit_code

        # Close all open file descriptors
        open_fds = list(proc.fd_table.table.keys())
        for fd in open_fds:
            proc.fd_table.close(fd)


# ==============================================================================
# SECTION 7: INTERRUPT VECTOR TABLE (IVT) & SYSTEM CALL DISPATCHER
# ==============================================================================

# Syscall signature: (kernel: "Kernel", proc: PCB, rdi: int, rsi: int, rdx: int, r10: int, r8: int, r9: int) -> int
SyscallHandler = Callable[["Kernel", PCB, int, int, int, int, int, int], int]

class InterruptVectorTable:
    """
    Interrupt Vector Table / Dispatch Table mapping 64-bit syscall numbers
    to kernel routine handlers. Extensible for adding new system calls.
    """
    def __init__(self):
        self.table: Dict[int, Tuple[str, SyscallHandler]] = {}

    def register(self, syscall_nr: int, name: str, handler: SyscallHandler):
        self.table[syscall_nr] = (name, handler)

    def lookup(self, syscall_nr: int) -> Optional[Tuple[str, SyscallHandler]]:
        return self.table.get(syscall_nr)


# ==============================================================================
# SECTION 8: VISUAL LOGGING & HARDWARE TRAP PIPELINE
# ==============================================================================

class VisualTrapLogger:
    """
    Renders high-fidelity, color-coded execution logs detailing each phase
    of the user-to-kernel space context transition.
    """
    WIDTH = 80

    @classmethod
    def banner(cls, title: str, subtitle: str = ""):
        line = "═" * cls.WIDTH
        print(colorize(f"\n╔{line}╗", Colors.BRIGHT_BLUE, Colors.BOLD))
        print(colorize(f"║ {title.center(cls.WIDTH - 2)} ║", Colors.BRIGHT_WHITE, Colors.BOLD, Colors.BG_BLUE))
        if subtitle:
            print(colorize(f"║ {subtitle.center(cls.WIDTH - 2)} ║", Colors.BRIGHT_CYAN))
        print(colorize(f"╚{line}╝", Colors.BRIGHT_BLUE, Colors.BOLD))

    @classmethod
    def step(cls, step_num: int, title: str, details: List[str], alert: bool = False, success: bool = False):
        border_color = Colors.BRIGHT_RED if alert else (Colors.BRIGHT_GREEN if success else Colors.BRIGHT_YELLOW)
        header = f"[STEP {step_num}] {title}"
        print(colorize(f"\n┌─ {header} " + "─" * max(2, cls.WIDTH - len(header) - 5), border_color, Colors.BOLD))
        for line in details:
            print(f"│  {line}")
        print(colorize("└" + "─" * (cls.WIDTH - 1), border_color))

    @classmethod
    def summary(cls, success: bool, msg: str):
        color = Colors.BRIGHT_GREEN if success else Colors.BRIGHT_RED
        symbol = "✔" if success else "✖"
        line = "─" * (cls.WIDTH - 2)
        print(colorize(f"\n{symbol} {msg}", color, Colors.BOLD))
        print(colorize(f"  {line}\n", Colors.DIM))


# ==============================================================================
# SECTION 9: KERNEL IMPLEMENTATION & SYSTEM CALL ROUTINES
# ==============================================================================

class Kernel:
    """
    Operating System Kernel core managing hardware privilege transitions,
    VFS subsystem, virtual memory safety, process table, and the IVT.
    """
    def __init__(self):
        self.vfs = VirtualFileSystem()
        self.proc_mgr = ProcessManager()
        self.ivt = InterruptVectorTable()
        self.logger = VisualTrapLogger()
        self._register_syscalls()

    def _register_syscalls(self):
        """Binds POSIX x86_64 system call handlers."""
        self.ivt.register(0,  "sys_read",  self._syscall_read)
        self.ivt.register(1,  "sys_write", self._syscall_write)
        self.ivt.register(2,  "sys_open",  self._syscall_open)
        self.ivt.register(3,  "sys_close", self._syscall_close)
        self.ivt.register(12, "sys_brk",   self._syscall_brk)
        self.ivt.register(57, "sys_fork",  self._syscall_fork)
        self.ivt.register(60, "sys_exit",  self._syscall_exit)

    # --------------------------------------------------------------------------
    # SYSCALL: sys_read (RAX=0)
    # --------------------------------------------------------------------------
    def _syscall_read(self, proc: PCB, fd: int, buf_addr: int, count: int, *args) -> int:
        """
        sys_read(unsigned int fd, char __user *buf, size_t count)
        Reads up to count bytes from fd into user memory buffer at buf_addr.
        """
        signed_count = to_i64(count)
        if signed_count < 0:
            return errno_to_u64(PosixErrno.EINVAL)
        count = signed_count
        if count == 0:
            return 0

        # Validate file descriptor
        handle = proc.fd_table.get(fd)
        if handle is None:
            return errno_to_u64(PosixErrno.EBADF)

        # Validate user-space destination buffer
        try:
            proc.vmm.validate_range(buf_addr, count, is_write=True)
        except SegmentationFault:
            return errno_to_u64(PosixErrno.EFAULT)

        read_data = b""
        if isinstance(handle, ConsoleStream):
            if not handle.readable:
                return errno_to_u64(PosixErrno.EBADF)
            read_data = handle.read(count)
        elif isinstance(handle, OpenFileDescription):
            if handle.flags & O_WRONLY:
                return errno_to_u64(PosixErrno.EBADF)

            inode = handle.inode
            if inode.itype == InodeType.CHAR_DEV and inode.read_device:
                read_data = inode.read_device(count)
            elif inode.itype == InodeType.FILE:
                available = len(inode.data) - handle.offset
                if available <= 0:
                    read_data = b""
                else:
                    actual = min(count, available)
                    read_data = bytes(inode.data[handle.offset:handle.offset + actual])
                    handle.offset += actual
                    inode.atime = time.time()
            else:
                return errno_to_u64(PosixErrno.EINVAL)

        # Copy data to user virtual memory
        proc.vmm.write_bytes(buf_addr, read_data)
        return len(read_data)

    # --------------------------------------------------------------------------
    # SYSCALL: sys_write (RAX=1)
    # --------------------------------------------------------------------------
    def _syscall_write(self, proc: PCB, fd: int, buf_addr: int, count: int, *args) -> int:
        """
        sys_write(unsigned int fd, const char __user *buf, size_t count)
        Writes up to count bytes from user memory buffer at buf_addr to fd.
        """
        signed_count = to_i64(count)
        if signed_count < 0:
            return errno_to_u64(PosixErrno.EINVAL)
        count = signed_count
        if count == 0:
            return 0

        # Validate file descriptor
        handle = proc.fd_table.get(fd)
        if handle is None:
            return errno_to_u64(PosixErrno.EBADF)

        # Validate user-space source buffer
        try:
            data = proc.vmm.read_bytes(buf_addr, count)
        except SegmentationFault:
            return errno_to_u64(PosixErrno.EFAULT)

        if isinstance(handle, ConsoleStream):
            if not handle.writable:
                return errno_to_u64(PosixErrno.EBADF)
            handle.write(data)
            # Output directly to real terminal
            text = data.decode("utf-8", errors="replace")
            if fd == 1:
                print(colorize(f"[STDOUT PID {proc.pid}] ", Colors.BRIGHT_GREEN) + text, end="", flush=True)
            elif fd == 2:
                print(colorize(f"[STDERR PID {proc.pid}] ", Colors.BRIGHT_RED) + text, end="", flush=True)
            return len(data)
        elif isinstance(handle, OpenFileDescription):
            is_writable = bool((handle.flags & O_WRONLY) or (handle.flags & O_RDWR))
            if not is_writable:
                return errno_to_u64(PosixErrno.EBADF)

            inode = handle.inode
            if inode.itype == InodeType.CHAR_DEV and inode.write_device:
                return inode.write_device(data)
            elif inode.itype == InodeType.FILE:
                if handle.flags & O_APPEND:
                    handle.offset = len(inode.data)

                # Ensure buffer size
                needed = handle.offset + len(data)
                if needed > len(inode.data):
                    inode.data.extend(b"\x00" * (needed - len(inode.data)))

                inode.data[handle.offset:handle.offset + len(data)] = data
                handle.offset += len(data)
                inode.mtime = time.time()
                return len(data)
            else:
                return errno_to_u64(PosixErrno.EINVAL)

        return errno_to_u64(PosixErrno.EBADF)

    # --------------------------------------------------------------------------
    # SYSCALL: sys_open (RAX=2)
    # --------------------------------------------------------------------------
    def _syscall_open(self, proc: PCB, path_addr: int, flags: int, mode: int, *args) -> int:
        """
        sys_open(const char __user *filename, int flags, umode_t mode)
        Opens or creates a file in VFS, allocating a per-process file descriptor.
        """
        try:
            filepath = proc.vmm.read_string(path_addr)
        except SegmentationFault:
            return errno_to_u64(PosixErrno.EFAULT)

        desc, err = self.vfs.open_file(filepath, flags=flags, mode=mode, cwd=proc.cwd)
        if err != PosixErrno.SUCCESS or desc is None:
            return errno_to_u64(err)

        fd = proc.fd_table.allocate_fd(desc)
        if fd < 0:
            return errno_to_u64(PosixErrno.EMFILE)
        return fd

    # --------------------------------------------------------------------------
    # SYSCALL: sys_close (RAX=3)
    # --------------------------------------------------------------------------
    def _syscall_close(self, proc: PCB, fd: int, *args) -> int:
        """
        sys_close(unsigned int fd)
        Releases the given file descriptor.
        """
        err = proc.fd_table.close(fd)
        if err != PosixErrno.SUCCESS:
            return errno_to_u64(err)
        return 0

    # --------------------------------------------------------------------------
    # SYSCALL: sys_brk (RAX=12)
    # --------------------------------------------------------------------------
    def _syscall_brk(self, proc: PCB, new_brk: int, *args) -> int:
        """
        sys_brk(unsigned long brk)
        Expands or queries the process heap break address.
        """
        return proc.vmm.sys_brk(new_brk)

    # --------------------------------------------------------------------------
    # SYSCALL: sys_fork (RAX=57)
    # --------------------------------------------------------------------------
    def _syscall_fork(self, proc: PCB, *args) -> int:
        """
        sys_fork(void)
        Duplicates the calling process PCB, memory space, and file table.
        Returns child PID in parent context, and 0 in child context.
        """
        child, err = self.proc_mgr.fork(proc)
        if err != PosixErrno.SUCCESS or child is None:
            return errno_to_u64(err)

        # In child context, sys_fork returns 0 in RAX
        child.write_reg("RAX", 0)

        # Return child PID in parent RAX
        return child.pid

    # --------------------------------------------------------------------------
    # SYSCALL: sys_exit (RAX=60)
    # --------------------------------------------------------------------------
    def _syscall_exit(self, proc: PCB, exit_code: int, *args) -> int:
        """
        sys_exit(int error_code)
        Terminates the current process.
        """
        self.proc_mgr.terminate(proc, exit_code)
        return exit_code

    # --------------------------------------------------------------------------
    # TRAP EXECUTION PIPELINE (Ring 3 -> Ring 0 -> Ring 3)
    # --------------------------------------------------------------------------
    def trigger_trap(self, instruction_name: str = "SYSCALL") -> int:
        """
        Executes the full hardware trap sequence:
        1. Capture software trap signal in User Space (Ring 3).
        2. Hardware pushes user context (pt_regs) to Kernel Stack.
        3. Privilege switch: Ring 3 -> Ring 0 (CPL=0), Stack switch: User RSP -> Kernel RSP.
        4. Lookup syscall number in RAX via Interrupt Vector Table.
        5. Kernel performs parameter safety checks and invokes handler.
        6. Return value written to saved RAX in pt_regs.
        7. SYSRETQ: Stack switch, privilege switch (Ring 0 -> Ring 3), restore context.
        """
        proc = self.proc_mgr.current
        user_rip = proc.read_reg("RIP")
        user_rsp = proc.read_reg("RSP")
        user_rflags = proc.read_reg("RFLAGS")
        syscall_nr = proc.read_reg("RAX")

        # Arguments according to x86_64 ABI: RDI, RSI, RDX, R10, R8, R9
        rdi = proc.read_reg("RDI")
        rsi = proc.read_reg("RSI")
        rdx = proc.read_reg("RDX")
        r10 = proc.read_reg("R10")
        r8  = proc.read_reg("R8")
        r9  = proc.read_reg("R9")

        # ----------------------------------------------------------------------
        # VISUAL LOG: BANNER
        # ----------------------------------------------------------------------
        lookup_entry = self.ivt.lookup(syscall_nr)
        syscall_name = lookup_entry[0] if lookup_entry else f"unknown_syscall_{syscall_nr}"
        self.logger.banner(
            f"CPU HARDWARE TRAP: {instruction_name} DISPATCH",
            f"Transition: Ring 3 (User) ➔ Ring 0 (Kernel) | Syscall #{syscall_nr} ({syscall_name})"
        )

        # ----------------------------------------------------------------------
        # STEP 1: TRAP FIRED
        # ----------------------------------------------------------------------
        self.logger.step(
            1, "CPU Trap Detected (MSR_LSTAR / Vector 0x80)",
            [
                f"Active Process: PID {proc.pid} ('{proc.name}') | PPID: {proc.ppid}",
                f"Instruction: {colorize(instruction_name, Colors.BOLD, Colors.BRIGHT_YELLOW)} at RIP: 0x{user_rip:016x}",
                f"Privilege Mode: Ring {proc.cpl.value} ({proc.cpl.name})",
                f"Syscall Requested: RAX = {syscall_nr} (0x{syscall_nr:04x})"
            ]
        )

        # ----------------------------------------------------------------------
        # STEP 2: HARDWARE CONTEXT SAVE (pt_regs on Kernel Stack)
        # ----------------------------------------------------------------------
        pt_regs = PtRegs(
            rax=syscall_nr, rdi=rdi, rsi=rsi, rdx=rdx,
            r10=r10, r8=r8, r9=r9, rsp=user_rsp, rip=user_rip,
            rflags=user_rflags, cpl=proc.cpl.value
        )
        proc.saved_pt_regs = pt_regs

        self.logger.step(
            2, "Hardware Context Save (Push struct pt_regs to Kernel Stack)",
            [
                f"Saving User Registers onto Kernel Stack (TSS RSP0: 0x{proc.kernel_rsp:016x}):",
                f"  RAX: 0x{syscall_nr:016x}   RDI: 0x{rdi:016x}",
                f"  RSI: 0x{rsi:016x}   RDX: 0x{rdx:016x}",
                f"  R10: 0x{r10:016x}   R8:  0x{r8:016x}   R9: 0x{r9:016x}",
                f"  RSP: 0x{user_rsp:016x} (Saved User Stack Pointer)",
                f"  RIP: 0x{user_rip:016x} (Saved User Return Address)",
                f"  RFLAGS: 0x{user_rflags:016x} (IF={(user_rflags & RFLAGS_IF) != 0})"
            ]
        )

        # ----------------------------------------------------------------------
        # STEP 3: PRIVILEGE LEVEL & STACK SWITCH
        # ----------------------------------------------------------------------
        old_cpl = proc.cpl
        proc.cpl = PrivilegeLevel.RING_0
        proc.regs["RSP"] = proc.kernel_rsp

        self.logger.step(
            3, "Privilege & Stack Switch (Ring 3 ➔ Ring 0)",
            [
                f"CPL Transition: {colorize('Ring 3 (USER)', Colors.BRIGHT_CYAN)} ➔ {colorize('Ring 0 (SUPERVISOR)', Colors.BRIGHT_RED, Colors.BOLD)}",
                f"Stack Switch: RSP shifted from User 0x{user_rsp:016x} ➔ Kernel 0x{proc.kernel_rsp:016x}",
                "Interrupts disabled during transition (CLI / RFLAGS mask applied)."
            ]
        )

        # ----------------------------------------------------------------------
        # STEP 4: IVT DISPATCH
        # ----------------------------------------------------------------------
        if lookup_entry is None:
            ret_val = errno_to_u64(PosixErrno.ENOSYS)
            self.logger.step(
                4, "Interrupt Vector Table (IVT) Lookup",
                [
                    f"Vector Index: RAX = {syscall_nr}",
                    colorize(f"Lookup FAILED: Syscall #{syscall_nr} is not implemented (-ENOSYS).", Colors.BRIGHT_RED)
                ],
                alert=True
            )
        else:
            name, handler = lookup_entry
            self.logger.step(
                4, "Interrupt Vector Table (IVT) Lookup & Parameter Decoding",
                [
                    f"Vector Index: RAX = {syscall_nr} ➔ Handler: {colorize(name, Colors.BOLD, Colors.BRIGHT_GREEN)}",
                    f"ABI Arguments:",
                    f"  Arg 1 (RDI): 0x{rdi:016x} ({to_i64(rdi)})",
                    f"  Arg 2 (RSI): 0x{rsi:016x} ({to_i64(rsi)})",
                    f"  Arg 3 (RDX): 0x{rdx:016x} ({to_i64(rdx)})",
                    f"  Arg 4 (R10): 0x{r10:016x} ({to_i64(r10)})",
                    f"  Arg 5 (R8) : 0x{r8:016x} ({to_i64(r8)})",
                    f"  Arg 6 (R9) : 0x{r9:016x} ({to_i64(r9)})"
                ]
            )

            # ------------------------------------------------------------------
            # STEP 5: KERNEL SUBSYSTEM EXECUTION
            # ------------------------------------------------------------------
            try:
                ret_val = handler(proc, rdi, rsi, rdx, r10, r8, r9)
                i_ret = to_i64(ret_val)
                is_error = (i_ret < 0 and i_ret >= -133)
                detail_lines = [
                    f"Executing kernel routine {name}() with supervisor privileges.",
                    f"Kernel execution completed: return_code = {format_u64(ret_val)}"
                ]
                if is_error:
                    detail_lines.append(colorize(f"Syscall returned POSIX errno: {PosixErrno(-i_ret).name}", Colors.BRIGHT_RED))
                self.logger.step(
                    5, f"Kernel Subsystem Execution ({name})",
                    detail_lines,
                    alert=is_error,
                    success=not is_error
                )
            except SegmentationFault as segv:
                ret_val = errno_to_u64(PosixErrno.EFAULT)
                self.logger.step(
                    5, "Kernel Memory Protection Trap (SIGSEGV)",
                    [
                        colorize(f"CRITICAL MEMORY VIOLATION: {segv}", Colors.BRIGHT_RED, Colors.BOLD),
                        f"Faulting Virtual Address: 0x{segv.fault_addr:016x}",
                        "Kernel caught illegal dereference. Returning -EFAULT (-14) to user space."
                    ],
                    alert=True
                )

        # ----------------------------------------------------------------------
        # STEP 6: RETURN VALUE WRITEBACK & SYSRETQ RESTORE
        # ----------------------------------------------------------------------
        pt_regs.rax = ret_val
        proc.write_reg("RAX", ret_val)

        # Restore stack pointer to user stack
        proc.regs["RSP"] = user_rsp
        # Switch privilege back to Ring 3
        proc.cpl = PrivilegeLevel.RING_3
        # Advance instruction pointer past syscall
        proc.regs["RIP"] = user_rip + 2

        self.logger.step(
            6, "Context Restoration & SYSRETQ (Ring 0 ➔ Ring 3)",
            [
                f"Writing syscall result {format_u64(ret_val)} into RAX.",
                "Executing SYSRETQ instruction:",
                f"  Privilege Level: {colorize('Ring 0', Colors.BRIGHT_RED)} ➔ {colorize('Ring 3 (USER)', Colors.BRIGHT_GREEN, Colors.BOLD)}",
                f"  Restoring User Stack Pointer: RSP ➔ 0x{user_rsp:016x}",
                f"  Restoring RFLAGS ➔ 0x{user_rflags:016x}",
                f"  Resuming User Execution at RIP: 0x{proc.read_reg('RIP'):016x}"
            ]
        )

        i_res = to_i64(ret_val)
        success_flag = not (i_res < 0 and i_res >= -133)
        self.logger.summary(
            success_flag,
            f"Trap Complete. Resumed User Space (PID {proc.pid}, Ring 3). RAX = {format_u64(ret_val)}"
        )
        return ret_val


# ==============================================================================
# SECTION 10: ASSEMBLY INSTRUCTIONS & PRE-LOADED DEMO PROGRAMS
# ==============================================================================

@dataclass
class AsmInstruction:
    """Represents a single assembly instruction in a loaded program."""
    opcode: str
    args: List[str]
    raw: str
    comment: str = ""


class DemoPrograms:
    """Provides realistic assembly demonstration programs for the simulator."""

    @staticmethod
    def hello_world(kernel: Kernel) -> List[AsmInstruction]:
        """
        Classic Hello World demonstration:
        Stores string in data section, loads pointers, executes sys_write, then sys_exit.
        """
        proc = kernel.proc_mgr.current
        msg = "Hello, World from x86_64 User Space (Ring 3)!\n"
        str_addr = proc.vmm.allocate_static_string(msg)
        msg_len = len(msg.encode("utf-8"))

        return [
            AsmInstruction("MOV", ["RAX", "1"], "MOV RAX, 1", "Syscall #1 = sys_write"),
            AsmInstruction("MOV", ["RDI", "1"], "MOV RDI, 1", "fd 1 = STDOUT"),
            AsmInstruction("MOV", ["RSI", hex(str_addr)], f"MOV RSI, {hex(str_addr)}", f'buf = "{msg.strip()}"'),
            AsmInstruction("MOV", ["RDX", str(msg_len)], f"MOV RDX, {msg_len}", f"count = {msg_len} bytes"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap to kernel to write message"),
            AsmInstruction("MOV", ["RAX", "60"], "MOV RAX, 60", "Syscall #60 = sys_exit"),
            AsmInstruction("MOV", ["RDI", "0"], "MOV RDI, 0", "exit status = 0 (SUCCESS)"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap to kernel to terminate")
        ]

    @staticmethod
    def file_io(kernel: Kernel) -> List[AsmInstruction]:
        """
        Complete POSIX file I/O demonstration:
        1. sys_open with O_WRONLY | O_CREAT (0x41)
        2. sys_write to disk file
        3. sys_close
        4. sys_open with O_RDONLY (0x0)
        5. sys_read from file into heap memory
        6. sys_write to STDOUT (fd 1) to echo file contents
        7. sys_close
        """
        proc = kernel.proc_mgr.current
        filename = "/home/user/sim_demo.txt"
        file_addr = proc.vmm.allocate_static_string(filename)

        payload = "Kernel Trap Simulator: In-memory VFS persistence verified!\n"
        payload_addr = proc.vmm.allocate_static_string(payload)
        payload_len = len(payload.encode("utf-8"))

        # Heap destination buffer for reading back
        heap_buf = proc.vmm.start_brk

        # Flags: O_WRONLY (1) | O_CREAT (64) = 65
        flags_create = O_WRONLY | O_CREAT
        mode_rw = 0o644

        return [
            # 1. sys_open for writing
            AsmInstruction("MOV", ["RAX", "2"], "MOV RAX, 2", "Syscall #2 = sys_open"),
            AsmInstruction("MOV", ["RDI", hex(file_addr)], f"MOV RDI, {hex(file_addr)}", f'path = "{filename}"'),
            AsmInstruction("MOV", ["RSI", str(flags_create)], f"MOV RSI, {flags_create}", "flags = O_WRONLY | O_CREAT (65)"),
            AsmInstruction("MOV", ["RDX", oct(mode_rw)], f"MOV RDX, {oct(mode_rw)}", "mode = 0644"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Open/create file (FD returned in RAX)"),

            # 2. sys_write to file
            AsmInstruction("MOV", ["RDI", "RAX"], "MOV RDI, RAX", "Copy allocated FD into RDI"),
            AsmInstruction("MOV", ["RAX", "1"], "MOV RAX, 1", "Syscall #1 = sys_write"),
            AsmInstruction("MOV", ["RSI", hex(payload_addr)], f"MOV RSI, {hex(payload_addr)}", "Source buffer"),
            AsmInstruction("MOV", ["RDX", str(payload_len)], f"MOV RDX, {payload_len}", f"Count = {payload_len} bytes"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Write payload to VFS file"),

            # 3. sys_close file
            AsmInstruction("MOV", ["RAX", "3"], "MOV RAX, 3", "Syscall #3 = sys_close"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Close file handle"),

            # 4. sys_open for reading
            AsmInstruction("MOV", ["RAX", "2"], "MOV RAX, 2", "Syscall #2 = sys_open"),
            AsmInstruction("MOV", ["RDI", hex(file_addr)], f"MOV RDI, {hex(file_addr)}", f'path = "{filename}"'),
            AsmInstruction("MOV", ["RSI", "0"], "MOV RSI, 0", "flags = O_RDONLY (0)"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Open file for reading (FD returned in RAX)"),

            # 5. sys_read from file
            AsmInstruction("MOV", ["R8", "RAX"], "MOV R8, RAX", "Save read FD in R8"),
            AsmInstruction("MOV", ["RAX", "0"], "MOV RAX, 0", "Syscall #0 = sys_read"),
            AsmInstruction("MOV", ["RDI", "R8"], "MOV RDI, R8", "FD to read"),
            AsmInstruction("MOV", ["RSI", hex(heap_buf)], f"MOV RSI, {hex(heap_buf)}", "Dest buffer in heap"),
            AsmInstruction("MOV", ["RDX", "128"], "MOV RDX, 128", "Max count = 128 bytes"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Read file data into heap memory"),

            # 6. sys_write to STDOUT
            AsmInstruction("MOV", ["RDX", "RAX"], "MOV RDX, RAX", "Count = bytes read from previous syscall"),
            AsmInstruction("MOV", ["RAX", "1"], "MOV RAX, 1", "Syscall #1 = sys_write"),
            AsmInstruction("MOV", ["RDI", "1"], "MOV RDI, 1", "fd 1 = STDOUT"),
            AsmInstruction("MOV", ["RSI", hex(heap_buf)], f"MOV RSI, {hex(heap_buf)}", "Echo buffer"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Echo read data to terminal STDOUT"),

            # 7. sys_close file
            AsmInstruction("MOV", ["RAX", "3"], "MOV RAX, 3", "Syscall #3 = sys_close"),
            AsmInstruction("MOV", ["RDI", "R8"], "MOV RDI, R8", "Close read FD"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Close file"),

            # 8. sys_exit
            AsmInstruction("MOV", ["RAX", "60"], "MOV RAX, 60", "Syscall #60 = sys_exit"),
            AsmInstruction("MOV", ["RDI", "0"], "MOV RDI, 0", "Status = 0"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Terminate")
        ]

    @staticmethod
    def fork_bomb_guard(kernel: Kernel) -> List[AsmInstruction]:
        """
        Fork Bomb Guard demonstration:
        Executes repeated sys_fork calls until the kernel process table limit (16)
        is saturated, triggering the OS safeguard returning -EAGAIN (11).
        """
        instructions = []
        # Attempt 18 forks (exceeding MAX_PROCESSES limit of 16)
        for i in range(18):
            instructions.append(
                AsmInstruction("MOV", ["RAX", "57"], "MOV RAX, 57", f"Syscall #57 = sys_fork (attempt {i+1})")
            )
            instructions.append(
                AsmInstruction("SYSCALL", [], "SYSCALL", f"Trap: Fork process (guard threshold test {i+1})")
            )
        return instructions

    @staticmethod
    def heap_alloc(kernel: Kernel) -> List[AsmInstruction]:
        """
        Heap Allocation (sys_brk) & SIGSEGV Memory Protection demo:
        1. Query initial program break via sys_brk(0)
        2. Attempt to write to unallocated heap address (triggers SIGSEGV / EFAULT)
        3. Extend heap break by 4096 bytes via sys_brk(initial + 4096)
        4. Write to the newly allocated address (succeeds)
        5. Output heap data to STDOUT
        """
        proc = kernel.proc_mgr.current
        start_brk = proc.vmm.start_brk
        new_brk = start_brk + 4096
        safe_addr = start_brk + 64

        test_msg = "Heap Allocation Verified: Dynamic memory accessed safely!\n"
        msg_addr = proc.vmm.allocate_static_string(test_msg)
        msg_len = len(test_msg.encode("utf-8"))

        return [
            # 1. Query break
            AsmInstruction("MOV", ["RAX", "12"], "MOV RAX, 12", "Syscall #12 = sys_brk"),
            AsmInstruction("MOV", ["RDI", "0"], "MOV RDI, 0", "brk(0) = query current program break"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Returns initial break in RAX"),

            # 2. Attempt illegal memory access beyond current break
            AsmInstruction("MOV", ["RAX", "1"], "MOV RAX, 1", "Syscall #1 = sys_write"),
            AsmInstruction("MOV", ["RDI", "1"], "MOV RDI, 1", "fd 1 = STDOUT"),
            AsmInstruction("MOV", ["RSI", hex(start_brk + 2048)], f"MOV RSI, {hex(start_brk + 2048)}", "Unmapped heap address!"),
            AsmInstruction("MOV", ["RDX", "32"], "MOV RDX, 32", "Count = 32 bytes"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Triggers SIGSEGV / -EFAULT due to unallocated memory"),

            # 3. Expand heap break via sys_brk
            AsmInstruction("MOV", ["RAX", "12"], "MOV RAX, 12", "Syscall #12 = sys_brk"),
            AsmInstruction("MOV", ["RDI", hex(new_brk)], f"MOV RDI, {hex(new_brk)}", f"Expand break to {hex(new_brk)} (+4KB)"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Kernel maps new pages and returns new brk"),

            # 4. Now safe to write message to STDOUT
            AsmInstruction("MOV", ["RAX", "1"], "MOV RAX, 1", "Syscall #1 = sys_write"),
            AsmInstruction("MOV", ["RDI", "1"], "MOV RDI, 1", "fd 1 = STDOUT"),
            AsmInstruction("MOV", ["RSI", hex(msg_addr)], f"MOV RSI, {hex(msg_addr)}", "Heap allocation success message"),
            AsmInstruction("MOV", ["RDX", str(msg_len)], f"MOV RDX, {msg_len}", f"Count = {msg_len} bytes"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Print success message to STDOUT"),

            # 5. Exit
            AsmInstruction("MOV", ["RAX", "60"], "MOV RAX, 60", "Syscall #60 = sys_exit"),
            AsmInstruction("MOV", ["RDI", "0"], "MOV RDI, 0", "Status = 0"),
            AsmInstruction("SYSCALL", [], "SYSCALL", "Trap: Terminate")
        ]


# ==============================================================================
# SECTION 11: REPL & INTERACTIVE ASSEMBLY EMULATOR
# ==============================================================================

class AssemblyEmulatorREPL:
    """
    Interactive Command-Line REPL providing a realistic terminal assembly
    debugging environment with live register displays, disk inspection,
    and step-by-step trap execution.
    """
    def __init__(self, kernel: Optional[Kernel] = None):
        self.kernel = kernel or Kernel()
        self.loaded_program: List[AsmInstruction] = []
        self.pc = 0  # program counter index in loaded_program

    def print_welcome(self):
        banner = """
 ██████╗ ███████╗    ██╗  ██╗███████╗██████╗ ███╗   ██╗███████╗██╗     
██╔═══██╗██╔════╝    ██║ ██╔╝██╔════╝██╔══██╗████╗  ██║██╔════╝██║     
██║   ██║███████╗    █████╔╝ █████╗  ██████╔╝██╔██╗ ██║█████╗  ██║     
██║   ██║╚════██║    ██╔═██╗ ██╔══╝  ██╔══██╗██║╚██╗██║██╔══╝  ██║     
╚██████╔╝███████║    ██║  ██╗███████╗██║  ██║██║ ╚████║███████╗███████╗
 ╚═════╝ ╚══════╝    ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝
    x86_64 SYSTEM CALL & KERNEL TRAP SIMULATOR (Ring 3 ➔ Ring 0)
"""
        print(colorize(banner, Colors.BRIGHT_CYAN, Colors.BOLD))
        print(colorize("Type 'HELP' for available commands, 'LOAD hello_world' to run a demo.\n", Colors.DIM))

    def cmd_dump(self):
        """Displays live register states, privilege ring, and open file descriptors."""
        proc = self.kernel.proc_mgr.current
        line = "═" * 78
        print(colorize(f"\n╔{line}╗", Colors.BRIGHT_BLUE))
        title = f" live cpu context | pid: {proc.pid} ('{proc.name}') | cpl: ring {proc.cpl.value} ({proc.cpl.name}) "
        print(colorize(f"║{title.center(78)}║", Colors.BRIGHT_WHITE, Colors.BOLD, Colors.BG_BLUE))
        print(colorize(f"╠{line}╣", Colors.BRIGHT_BLUE))

        # Register table (2 columns)
        regs = list(REGISTER_NAMES)
        for i in range(0, len(regs), 2):
            r1 = regs[i]
            v1 = proc.read_reg(r1)
            f1 = f"{r1:<6} = 0x{v1:016x} ({v1})"

            if i + 1 < len(regs):
                r2 = regs[i + 1]
                v2 = proc.read_reg(r2)
                f2 = f"{r2:<6} = 0x{v2:016x} ({v2})"
            else:
                f2 = ""

            row = f"  {f1:<36} │  {f2:<36}"
            print(colorize(f"║{row}║", Colors.BRIGHT_WHITE))

        print(colorize(f"╠{line}╣", Colors.BRIGHT_BLUE))
        print(colorize("║  MEMORY BOUNDARIES:".ljust(79) + "║", Colors.BRIGHT_YELLOW))
        mem_info = (
            f"  Text: 0x{proc.vmm.text_base:012x}   Heap Start: 0x{proc.vmm.start_brk:012x}   "
            f"Heap Break: 0x{proc.vmm.current_brk:012x}   Stack: 0x{proc.read_reg('RSP'):012x}"
        )
        print(colorize(f"║{mem_info.ljust(78)}║", Colors.WHITE))

        print(colorize(f"╠{line}╣", Colors.BRIGHT_BLUE))
        print(colorize("║  OPEN FILE DESCRIPTORS (fd_table):".ljust(79) + "║", Colors.BRIGHT_YELLOW))
        for fd, handle in sorted(proc.fd_table.table.items()):
            if isinstance(handle, ConsoleStream):
                desc_str = f"  fd {fd}: [Console Stream] {handle.name} (r={handle.readable}, w={handle.writable})"
            elif isinstance(handle, OpenFileDescription):
                flags_desc = []
                if handle.flags & O_WRONLY: flags_desc.append("O_WRONLY")
                elif handle.flags & O_RDWR: flags_desc.append("O_RDWR")
                else: flags_desc.append("O_RDONLY")
                if handle.flags & O_CREAT: flags_desc.append("O_CREAT")
                if handle.flags & O_APPEND: flags_desc.append("O_APPEND")
                desc_str = (
                    f"  fd {fd}: Inode #{handle.inode.ino} ('{handle.inode.name}') "
                    f"type={handle.inode.itype.name} perms={oct(handle.inode.permissions)} "
                    f"offset={handle.offset} size={handle.inode.size} flags={'|'.join(flags_desc)}"
                )
            else:
                desc_str = f"  fd {fd}: Unknown"
            print(colorize(f"║{desc_str.ljust(78)}║", Colors.WHITE))

        print(colorize(f"╚{line}╝\n", Colors.BRIGHT_BLUE))

    def cmd_ls_disk(self):
        """Lists all files and directories on the virtual hard drive."""
        print(colorize("\n[VIRTUAL HARD DISK INODE TABLE]", Colors.BRIGHT_CYAN, Colors.BOLD))
        header = f"{'INODE':<8} {'TYPE':<10} {'PERMS':<8} {'SIZE':<10} {'NAME':<20} {'PATH'}"
        print(colorize(header, Colors.UNDERLINE, Colors.BOLD))
        
        # Traverse from root
        def walk(ino: int, current_path: str):
            inode = self.kernel.vfs.inodes.get(ino)
            if not inode:
                return
            itype = inode.itype.value
            perms = oct(inode.permissions)
            size = f"{inode.size} B"
            name = inode.name
            path_display = current_path if current_path else "/"
            print(f"{ino:<8} {itype:<10} {perms:<8} {size:<10} {name:<20} {path_display}")
            if inode.itype == InodeType.DIRECTORY:
                for entry_name, child_ino in sorted(inode.entries.items()):
                    if entry_name in (".", ".."):
                        continue
                    child_path = os.path.join(current_path, entry_name).replace("\\", "/")
                    walk(child_ino, child_path)

        walk(1, "/")
        print()

    def cmd_cat(self, filepath: str):
        """Displays the contents of a file on the virtual disk."""
        proc = self.kernel.proc_mgr.current
        inode = self.kernel.vfs.resolve_path(filepath, cwd=proc.cwd)
        if inode is None:
            print(colorize(f"cat: {filepath}: No such file or directory", Colors.BRIGHT_RED))
            return
        if inode.itype == InodeType.DIRECTORY:
            print(colorize(f"cat: {filepath}: Is a directory", Colors.BRIGHT_YELLOW))
            return
        if inode.itype == InodeType.CHAR_DEV:
            print(colorize(f"cat: {filepath}: [Character Device Node]", Colors.BRIGHT_MAGENTA))
            return

        print(colorize(f"--- Content of {filepath} ({len(inode.data)} bytes) ---", Colors.DIM))
        content = inode.data.decode("utf-8", errors="replace")
        print(content)
        if not content.endswith("\n"):
            print()

    def cmd_mov(self, reg_name: str, val_str: str):
        """
        Assigns a register a value:
        MOV <REG>, <INTEGER | HEX | REGISTER | STRING_LITERAL>
        If string literal is passed, stores in user memory and sets register to address.
        """
        proc = self.kernel.proc_mgr.current
        reg_upper = reg_name.upper()
        if reg_upper not in REGISTER_NAMES:
            print(colorize(f"Error: Unknown register '{reg_name}'. Allowed: {', '.join(REGISTER_NAMES)}", Colors.BRIGHT_RED))
            return

        val_str = val_str.strip()

        # Case 1: String literal (enclosed in quotes)
        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            raw_str = val_str[1:-1].encode("utf-8").decode("unicode_escape")
            addr = proc.vmm.allocate_static_string(raw_str)
            proc.write_reg(reg_upper, addr)
            print(colorize(
                f"[Memory Manager] Stored string literal ({len(raw_str)} bytes) at 0x{addr:016x}. "
                f"{reg_upper} set to 0x{addr:016x}", Colors.BRIGHT_GREEN
            ))
            return

        # Case 2: Another register
        val_upper = val_str.upper()
        if val_upper in REGISTER_NAMES:
            val = proc.read_reg(val_upper)
            proc.write_reg(reg_upper, val)
            print(colorize(f"{reg_upper} ➔ 0x{val:016x} (copied from {val_upper})", Colors.BRIGHT_GREEN))
            return

        # Case 3: Numeric literal (hex or decimal)
        try:
            if val_str.startswith("0x") or val_str.startswith("0X"):
                val = int(val_str, 16)
            elif val_str.startswith("0o") or val_str.startswith("0O"):
                val = int(val_str, 8)
            else:
                val = int(val_str)
            proc.write_reg(reg_upper, val)
            print(colorize(f"{reg_upper} ➔ {format_u64(val)}", Colors.BRIGHT_GREEN))
        except ValueError:
            print(colorize(f"Error: Invalid value expression '{val_str}'", Colors.BRIGHT_RED))

    def cmd_load(self, demo_name: str):
        """Loads a pre-defined demo assembly program into the emulator."""
        name = demo_name.lower().strip()
        if name == "hello_world":
            self.loaded_program = DemoPrograms.hello_world(self.kernel)
        elif name == "file_io":
            self.loaded_program = DemoPrograms.file_io(self.kernel)
        elif name == "fork_bomb_guard":
            self.loaded_program = DemoPrograms.fork_bomb_guard(self.kernel)
        elif name == "heap_alloc":
            self.loaded_program = DemoPrograms.heap_alloc(self.kernel)
        else:
            print(colorize(
                f"Error: Unknown demo '{demo_name}'. Available: hello_world, file_io, fork_bomb_guard, heap_alloc",
                Colors.BRIGHT_RED
            ))
            return

        self.pc = 0
        print(colorize(f"\n✔ Successfully loaded demo '{name}' ({len(self.loaded_program)} instructions).", Colors.BRIGHT_GREEN, Colors.BOLD))
        self.cmd_list()
        print(colorize("Use 'STEP' to execute one instruction or 'RUN' to execute to completion.\n", Colors.DIM))

    def cmd_list(self):
        """Displays the loaded program instructions with the current PC pointer."""
        if not self.loaded_program:
            print(colorize("No program currently loaded. Use 'LOAD <demo_name>' to load one.", Colors.BRIGHT_YELLOW))
            return

        print(colorize("\n[LOADED ASSEMBLY PROGRAM]", Colors.BRIGHT_CYAN, Colors.BOLD))
        for idx, inst in enumerate(self.loaded_program):
            marker = "➔" if idx == self.pc else " "
            color = (Colors.BRIGHT_GREEN, Colors.BOLD) if idx == self.pc else (Colors.WHITE,)
            comment_part = f" ; {inst.comment}" if inst.comment else ""
            line_str = f"  {marker} [{idx:02d}] {inst.raw:<24}{comment_part}"
            print(colorize(line_str, *color))
        print()

    def cmd_step(self):
        """Executes the current instruction at PC in the loaded program."""
        if not self.loaded_program:
            print(colorize("No program loaded. Use 'LOAD <demo_name>' first.", Colors.BRIGHT_YELLOW))
            return
        if self.pc >= len(self.loaded_program):
            print(colorize("Program execution finished. Use 'LOAD <demo_name>' to reload.", Colors.BRIGHT_YELLOW))
            return

        inst = self.loaded_program[self.pc]
        print(colorize(f"\n[EXEC PC {self.pc:02d}] {inst.raw} ; {inst.comment}", Colors.BRIGHT_YELLOW, Colors.BOLD))
        self.pc += 1

        if inst.opcode == "MOV":
            self.cmd_mov(inst.args[0], inst.args[1])
        elif inst.opcode in ("SYSCALL", "INT"):
            trap_name = f"{inst.opcode} {' '.join(inst.args)}".strip()
            self.kernel.trigger_trap(trap_name)
        else:
            print(colorize(f"Warning: Unknown opcode '{inst.opcode}' skipped.", Colors.BRIGHT_RED))

    def cmd_run(self):
        """Executes all remaining instructions in the loaded program."""
        if not self.loaded_program:
            print(colorize("No program loaded. Use 'LOAD <demo_name>' first.", Colors.BRIGHT_YELLOW))
            return
        print(colorize(f"\n>>> Running program from PC {self.pc} to completion...\n", Colors.BRIGHT_GREEN, Colors.BOLD))
        while self.pc < len(self.loaded_program):
            self.cmd_step()
            time.sleep(0.05)  # brief pause for visual pacing
        print(colorize("✔ Program execution finished.\n", Colors.BRIGHT_GREEN, Colors.BOLD))

    def cmd_mem(self, addr_str: str, length_str: str = "32"):
        """Displays memory hexdump at given address."""
        proc = self.kernel.proc_mgr.current
        try:
            addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)
            length = int(length_str)
        except ValueError:
            print(colorize("Usage: MEM <address> [length_in_bytes]", Colors.BRIGHT_RED))
            return

        try:
            data = proc.vmm.read_bytes(addr, length)
            print(colorize(f"\n[HEXDUMP @ 0x{addr:016x} ({length} bytes)]", Colors.BRIGHT_CYAN, Colors.BOLD))
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_bytes = " ".join(f"{b:02x}" for b in chunk)
                ascii_chars = "".join((chr(b) if 32 <= b <= 126 else ".") for b in chunk)
                offset = addr + i
                print(f"  0x{offset:016x}:  {hex_bytes:<48}  |{ascii_chars}|")
            print()
        except SegmentationFault as segv:
            print(colorize(f"Segmentation Fault: {segv}", Colors.BRIGHT_RED))

    def cmd_store(self, addr_str: str, val_str: str):
        """Directly writes bytes or string to virtual memory address."""
        proc = self.kernel.proc_mgr.current
        try:
            addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)
        except ValueError:
            print(colorize("Usage: STORE <address> <value_or_string>", Colors.BRIGHT_RED))
            return

        val_str = val_str.strip()
        if (val_str.startswith('"') and val_str.endswith('"')) or (val_str.startswith("'") and val_str.endswith("'")):
            data = val_str[1:-1].encode("utf-8").decode("unicode_escape").encode("utf-8") + b"\x00"
        else:
            try:
                num = int(val_str, 16) if val_str.startswith("0x") else int(val_str)
                data = struct.pack("<Q", num)
            except ValueError:
                print(colorize(f"Invalid store data: '{val_str}'", Colors.BRIGHT_RED))
                return

        try:
            proc.vmm.write_bytes(addr, data)
            print(colorize(f"✔ Successfully stored {len(data)} bytes at 0x{addr:016x}.", Colors.BRIGHT_GREEN))
        except SegmentationFault as segv:
            print(colorize(f"Segmentation Fault: {segv}", Colors.BRIGHT_RED))

    def cmd_ps(self):
        """Displays the kernel process table."""
        print(colorize("\n[KERNEL PROCESS TABLE]", Colors.BRIGHT_CYAN, Colors.BOLD))
        header = f"{'PID':<8} {'PPID':<8} {'STATE':<12} {'PRIO':<6} {'NAME':<16} {'HEAP_BRK':<18} {'ACTIVE'}"
        print(colorize(header, Colors.UNDERLINE, Colors.BOLD))
        for pid, proc in sorted(self.kernel.proc_mgr.processes.items()):
            active = "➔ (current)" if pid == self.kernel.proc_mgr.active_pid else ""
            brk_str = f"0x{proc.vmm.current_brk:012x}"
            line = f"{pid:<8} {proc.ppid:<8} {proc.state.value:<12} {proc.priority:<6} {proc.name:<16} {brk_str:<18} {active}"
            color = (Colors.BRIGHT_GREEN, Colors.BOLD) if active else (Colors.WHITE,)
            print(colorize(line, *color))
        print()

    def cmd_switch(self, pid_str: str):
        """Switches CPU execution context to another PID."""
        try:
            pid = int(pid_str)
        except ValueError:
            print(colorize("Usage: SWITCH <pid>", Colors.BRIGHT_RED))
            return
        if pid not in self.kernel.proc_mgr.processes:
            print(colorize(f"Error: PID {pid} not found in process table.", Colors.BRIGHT_RED))
            return
        self.kernel.proc_mgr.active_pid = pid
        print(colorize(f"✔ Switched active CPU context to PID {pid}.", Colors.BRIGHT_GREEN))

    def cmd_help(self):
        """Prints complete interactive help menu."""
        help_text = f"""
{colorize("╔════════════════════════════════════════════════════════════════════════════╗", Colors.BRIGHT_BLUE)}
{colorize("║           SYSTEM CALL & KERNEL TRAP SIMULATOR - COMMAND HELP               ║", Colors.BRIGHT_WHITE, Colors.BOLD, Colors.BG_BLUE)}
{colorize("╚════════════════════════════════════════════════════════════════════════════╝", Colors.BRIGHT_BLUE)}

{colorize("ASSEMBLY & TRAP EXECUTION:", Colors.BRIGHT_YELLOW, Colors.BOLD)}
  MOV <REG>, <VAL>          Assign register (e.g. MOV RAX, 1 | MOV RSI, "Hello\\n")
  SYSCALL or INT 0x80       Trigger hardware trap into Ring 0 kernel dispatcher
  DUMP                      Display live registers, privilege ring, and open FDs
  LOAD <demo_name>          Load demo: hello_world, file_io, fork_bomb_guard, heap_alloc
  LIST                      List instructions of currently loaded demo
  STEP                      Execute one instruction from loaded program
  RUN                       Execute loaded program to completion

{colorize("VIRTUAL FILE SYSTEM (VFS) & MEMORY:", Colors.BRIGHT_YELLOW, Colors.BOLD)}
  LS_DISK                   List all files, inodes, sizes, and permissions on disk
  CAT <filepath>            Display contents of a file on the virtual hard drive
  MEM <addr> [len]          Display memory hexdump at virtual address
  STORE <addr> <val/str>    Write raw bytes or string into virtual memory address

{colorize("PROCESS MANAGEMENT & SYSTEM:", Colors.BRIGHT_YELLOW, Colors.BOLD)}
  PS                        Show kernel process table (PIDs, PPIDs, states, heap breaks)
  SWITCH <pid>              Switch active CPU context to target process PID
  RESET                     Reset CPU registers and active process state
  HELP                      Display this command manual
  EXIT / QUIT               Exit simulator

{colorize("x86_64 SYSTEM CALL TABLE REFERENCE:", Colors.BRIGHT_CYAN, Colors.BOLD)}
  RAX=0  : sys_read  (RDI=fd, RSI=buf, RDX=count)
  RAX=1  : sys_write (RDI=fd, RSI=buf, RDX=count)
  RAX=2  : sys_open  (RDI=path, RSI=flags, RDX=mode) [O_RDONLY=0, O_WRONLY=1, O_CREAT=64]
  RAX=3  : sys_close (RDI=fd)
  RAX=12 : sys_brk   (RDI=brk) [brk=0 queries current break]
  RAX=57 : sys_fork  (no args) [returns child PID in parent, 0 in child]
  RAX=60 : sys_exit  (RDI=status)
"""
        print(help_text)

    def execute_command_line(self, line: str) -> bool:
        """Parses and executes a single REPL command. Returns False to exit."""
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            return True

        # Custom split to preserve quotes
        try:
            tokens = shlex.split(line)
        except ValueError as err:
            print(colorize(f"Syntax error: {err}", Colors.BRIGHT_RED))
            return True

        if not tokens:
            return True

        cmd = tokens[0].upper()

        if cmd in ("EXIT", "QUIT"):
            print(colorize("Halting Kernel Simulator. Goodbye!\n", Colors.BRIGHT_CYAN))
            return False

        elif cmd == "HELP":
            self.cmd_help()

        elif cmd == "DUMP":
            self.cmd_dump()

        elif cmd == "LS_DISK":
            self.cmd_ls_disk()

        elif cmd == "CAT":
            if len(tokens) < 2:
                print(colorize("Usage: CAT <filepath>", Colors.BRIGHT_RED))
            else:
                self.cmd_cat(tokens[1])

        elif cmd == "MOV":
            # Handle comma if present (e.g. MOV RAX, 1)
            raw_args = line[len(tokens[0]):].strip()
            if "," in raw_args:
                parts = raw_args.split(",", 1)
                reg_name = parts[0].strip()
                val_str = parts[1].strip()
            elif len(tokens) >= 3:
                reg_name = tokens[1]
                val_str = tokens[2]
            else:
                print(colorize("Usage: MOV <REG>, <VALUE>", Colors.BRIGHT_RED))
                return True
            self.cmd_mov(reg_name, val_str)

        elif cmd in ("SYSCALL", "INT"):
            trap_name = " ".join(tokens) if cmd == "INT" else cmd
            self.kernel.trigger_trap(trap_name)

        elif cmd == "LOAD":
            if len(tokens) < 2:
                print(colorize("Usage: LOAD <hello_world | file_io | fork_bomb_guard | heap_alloc>", Colors.BRIGHT_RED))
            else:
                self.cmd_load(tokens[1])

        elif cmd == "LIST":
            self.cmd_list()

        elif cmd == "STEP":
            self.cmd_step()

        elif cmd == "RUN":
            self.cmd_run()

        elif cmd == "MEM":
            if len(tokens) < 2:
                print(colorize("Usage: MEM <address> [length]", Colors.BRIGHT_RED))
            else:
                length = tokens[2] if len(tokens) >= 3 else "32"
                self.cmd_mem(tokens[1], length)

        elif cmd == "STORE":
            if len(tokens) < 3:
                print(colorize("Usage: STORE <address> <value_or_string>", Colors.BRIGHT_RED))
            else:
                self.cmd_store(tokens[1], " ".join(tokens[2:]))

        elif cmd == "PS":
            self.cmd_ps()

        elif cmd == "SWITCH":
            if len(tokens) < 2:
                print(colorize("Usage: SWITCH <pid>", Colors.BRIGHT_RED))
            else:
                self.cmd_switch(tokens[1])

        elif cmd == "RESET":
            self.kernel = Kernel()
            self.loaded_program.clear()
            self.pc = 0
            print(colorize("✔ CPU context and process state reset to initial boot condition.", Colors.BRIGHT_GREEN))

        else:
            print(colorize(f"Unknown command '{tokens[0]}'. Type 'HELP' for instructions.", Colors.BRIGHT_RED))

        return True

    def run_repl(self):
        """Runs the interactive command loop."""
        self.print_welcome()
        while True:
            proc = self.kernel.proc_mgr.current
            prompt_str = colorize(f"[kernel-sim:PID {proc.pid}:Ring {proc.cpl.value}]$ ", Colors.BRIGHT_CYAN, Colors.BOLD)
            try:
                line = input(prompt_str)
            except (EOFError, KeyboardInterrupt):
                print(colorize("\nReceived interrupt. Exiting simulator.", Colors.DIM))
                break

            should_continue = self.execute_command_line(line)
            if not should_continue:
                break


# ==============================================================================
# SECTION 12: UNIT & INTEGRATION TEST SUITE
# ==============================================================================

def run_all_tests() -> bool:
    """
    Comprehensive test suite verifying registers, memory boundaries,
    VFS operations, and every POSIX syscall implementation.
    """
    print(colorize("\n" + "=" * 80, Colors.BRIGHT_BLUE))
    print(colorize("RUNNING COMPREHENSIVE KERNEL SIMULATOR TEST SUITE", Colors.BRIGHT_WHITE, Colors.BOLD))
    print(colorize("=" * 80 + "\n", Colors.BRIGHT_BLUE))

    test_passed = 0
    test_failed = 0

    def assert_true(condition: bool, test_name: str):
        nonlocal test_passed, test_failed
        if condition:
            print(colorize(f"  [PASS] {test_name}", Colors.BRIGHT_GREEN))
            test_passed += 1
        else:
            print(colorize(f"  [FAIL] {test_name}", Colors.BRIGHT_RED, Colors.BOLD))
            test_failed += 1

    # Test 1: Register operations & 64-bit bounds
    k = Kernel()
    proc = k.proc_mgr.current
    proc.write_reg("RAX", 0xFFFFFFFFFFFFFFFF)
    assert_true(proc.read_reg("RAX") == 0xFFFFFFFFFFFFFFFF, "Register 64-bit max value wrapping")
    proc.write_reg("RDI", 0x10000000000000001)
    assert_true(proc.read_reg("RDI") == 1, "Register 64-bit overflow masking")

    # Test 2: Virtual Memory Manager bounds & heap break
    initial_brk = proc.vmm.current_brk
    assert_true(proc.vmm.sys_brk(0) == initial_brk, "sys_brk(0) returns current program break")
    expanded_brk = proc.vmm.sys_brk(initial_brk + 4096)
    assert_true(expanded_brk == initial_brk + 4096, "sys_brk expansion creates valid pages")
    # Illegal write beyond break
    illegal_addr = expanded_brk + 0x10000
    try:
        proc.vmm.write_bytes(illegal_addr, b"FAIL")
        assert_true(False, "SIGSEGV triggered on unmapped memory write")
    except SegmentationFault:
        assert_true(True, "SIGSEGV triggered on unmapped memory write")

    # Test 3: VFS path resolution & file creation
    etc_release = k.vfs.resolve_path("/etc/os-release")
    assert_true(etc_release is not None and b"KernelSim" in etc_release.data, "VFS /etc/os-release resolved")
    desc, err = k.vfs.open_file("/home/user/new.txt", flags=O_WRONLY | O_CREAT, mode=0o644)
    assert_true(err == PosixErrno.SUCCESS and desc is not None, "VFS file creation with O_CREAT")

    # Test 4: sys_write to stdout (RAX=1)
    test_str = "Test stdout write\n"
    str_addr = proc.vmm.allocate_static_string(test_str)
    proc.write_reg("RAX", 1)  # sys_write
    proc.write_reg("RDI", 1)  # stdout
    proc.write_reg("RSI", str_addr)
    proc.write_reg("RDX", len(test_str.encode("utf-8")))
    ret = k.trigger_trap("SYSCALL")
    assert_true(ret == len(test_str.encode("utf-8")), "sys_write to stdout returns correct byte count")

    # Test 5: sys_write to invalid buffer (EFAULT)
    proc.write_reg("RAX", 1)
    proc.write_reg("RDI", 1)
    proc.write_reg("RSI", 0x0000DEADBEEF0000)  # illegal address
    proc.write_reg("RDX", 16)
    ret = k.trigger_trap("SYSCALL")
    assert_true(ret == errno_to_u64(PosixErrno.EFAULT), "sys_write with bad pointer returns -EFAULT")

    # Test 6: sys_open and sys_read on VFS file
    readme_path_addr = proc.vmm.allocate_static_string("/home/user/readme.txt")
    proc.write_reg("RAX", 2)  # sys_open
    proc.write_reg("RDI", readme_path_addr)
    proc.write_reg("RSI", O_RDONLY)
    fd = k.trigger_trap("SYSCALL")
    assert_true(fd >= 3, f"sys_open allocated valid file descriptor ({fd})")

    # Read from the opened fd
    dest_buf = proc.vmm.start_brk
    proc.write_reg("RAX", 0)  # sys_read
    proc.write_reg("RDI", fd)
    proc.write_reg("RSI", dest_buf)
    proc.write_reg("RDX", 32)
    bytes_read = k.trigger_trap("SYSCALL")
    assert_true(bytes_read == 32, "sys_read fetched 32 bytes from VFS file")

    # Test 7: sys_close
    proc.write_reg("RAX", 3)  # sys_close
    proc.write_reg("RDI", fd)
    close_ret = k.trigger_trap("SYSCALL")
    assert_true(close_ret == 0, "sys_close released file descriptor successfully")

    # Test 8: sys_fork duplication and fork bomb guard
    k_fork = Kernel()
    parent = k_fork.proc_mgr.current
    parent.write_reg("RAX", 57)  # sys_fork
    child_pid = k_fork.trigger_trap("SYSCALL")
    assert_true(child_pid > parent.pid, f"sys_fork spawned child PID {child_pid}")
    child_pcb = k_fork.proc_mgr.processes[child_pid]
    assert_true(child_pcb.read_reg("RAX") == 0, "sys_fork returned 0 in child context")

    # Fork bomb guard threshold
    for _ in range(ProcessManager.MAX_PROCESSES + 2):
        k_fork.proc_mgr.fork(parent)
    parent.write_reg("RAX", 57)
    guard_ret = k_fork.trigger_trap("SYSCALL")
    assert_true(guard_ret == errno_to_u64(PosixErrno.EAGAIN), "Fork bomb guard returned -EAGAIN on table saturation")

    # Test 9: sys_exit
    parent.write_reg("RAX", 60)  # sys_exit
    parent.write_reg("RDI", 42)
    exit_ret = k_fork.trigger_trap("SYSCALL")
    assert_true(parent.state == ProcessState.TERMINATED and parent.exit_code == 42, "sys_exit properly terminated process")

    # Test 10: Demo Program executions (hello_world, file_io, heap_alloc)
    repl = AssemblyEmulatorREPL(k)
    repl.cmd_load("hello_world")
    assert_true(len(repl.loaded_program) > 0, "LOAD hello_world populated program")
    repl.cmd_run()
    assert_true(repl.pc == len(repl.loaded_program), "RUN hello_world executed all instructions")

    repl.cmd_load("file_io")
    repl.cmd_run()
    created_file = k.vfs.resolve_path("/home/user/sim_demo.txt")
    assert_true(created_file is not None and len(created_file.data) > 0, "file_io demo successfully wrote and persisted file")

    print(colorize("\n" + "=" * 80, Colors.BRIGHT_BLUE))
    print(colorize(f"TEST RESULTS: {test_passed} PASSED, {test_failed} FAILED", Colors.BRIGHT_GREEN if test_failed == 0 else Colors.BRIGHT_RED, Colors.BOLD))
    print(colorize("=" * 80 + "\n", Colors.BRIGHT_BLUE))
    return test_failed == 0


# ==============================================================================
# SECTION 13: MAIN ENTRY POINT
# ==============================================================================

def main():
    """Main CLI entry point."""
    if "--test" in sys.argv:
        success = run_all_tests()
        sys.exit(0 if success else 1)

    repl = AssemblyEmulatorREPL()

    # Optional script execution: python kernel_sim.py <script.asm>
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        script_file = sys.argv[1]
        if not os.path.exists(script_file):
            print(colorize(f"Error: Script file '{script_file}' not found.", Colors.BRIGHT_RED))
            sys.exit(1)
        with open(script_file, "r", encoding="utf-8") as f:
            for line in f:
                repl.execute_command_line(line)
        sys.exit(0)

    # Interactive REPL
    repl.run_repl()


if __name__ == "__main__":
    main()
