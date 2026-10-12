#!/usr/bin/env python3
"""
Unit and integration test suite for kernel_sim.py.
Thoroughly tests CPU registers, VMM, VFS, PCB, Syscalls, REPL, and edge cases.
"""

import unittest
import io
import sys
import os
from contextlib import redirect_stdout, redirect_stderr

from kernel_sim import (
    Kernel, VirtualMemoryManager, VirtualFileSystem, FileDescriptorTable,
    ProcessManager, ProcessState, PrivilegeLevel, PosixErrno, InodeType,
    Inode, OpenFileDescription,
    AssemblyEmulatorREPL, DemoPrograms, AsmInstruction, SegmentationFault,
    O_RDONLY, O_WRONLY, O_RDWR, O_CREAT, O_EXCL, O_TRUNC, O_APPEND,
    USER_TEXT_BASE, USER_DATA_BASE, USER_HEAP_START, USER_HEAP_MAX,
    USER_STACK_INIT, to_u64, to_i64, errno_to_u64, format_u64
)


class TestCpuAndRegisters(unittest.TestCase):
    """Test 64-bit register manipulations, wrapping, and signed conversions."""

    def test_u64_wrapping(self):
        self.assertEqual(to_u64(0), 0)
        self.assertEqual(to_u64(0xFFFFFFFFFFFFFFFF), 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(to_u64(0x10000000000000000), 0)
        self.assertEqual(to_u64(-1), 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(to_u64(-2), 0xFFFFFFFFFFFFFFFE)

    def test_i64_conversion(self):
        self.assertEqual(to_i64(0), 0)
        self.assertEqual(to_i64(100), 100)
        self.assertEqual(to_i64(0xFFFFFFFFFFFFFFFF), -1)
        self.assertEqual(to_i64(0xFFFFFFFFFFFFFFFE), -2)
        self.assertEqual(to_i64(errno_to_u64(PosixErrno.ENOENT)), -2)

    def test_register_access(self):
        k = Kernel()
        proc = k.proc_mgr.current
        proc.write_reg("RAX", 0x123456789ABCDEF0)
        self.assertEqual(proc.read_reg("RAX"), 0x123456789ABCDEF0)
        # Test case insensitivity
        proc.write_reg("rax", 42)
        self.assertEqual(proc.read_reg("RAX"), 42)
        # 64-bit overflow handling
        proc.write_reg("RDI", 0x10000000000000005)
        self.assertEqual(proc.read_reg("RDI"), 5)

    def test_format_u64(self):
        s_pos = format_u64(42)
        self.assertIn("42", s_pos)
        s_err = format_u64(errno_to_u64(PosixErrno.ENOENT))
        self.assertIn("ENOENT", s_err)


class TestVirtualMemoryManager(unittest.TestCase):
    """Test virtual memory mapping, boundary enforcement, brk/sbrk, and SIGSEGV."""

    def setUp(self):
        self.vmm = VirtualMemoryManager(pid=1000)

    def test_initial_boundaries(self):
        self.assertEqual(self.vmm.text_base, USER_TEXT_BASE)
        self.assertEqual(self.vmm.start_brk, USER_HEAP_START)
        self.assertEqual(self.vmm.current_brk, USER_HEAP_START)

    def test_data_segment_allocation(self):
        addr1 = self.vmm.allocate_static_string("Hello")
        addr2 = self.vmm.allocate_static_string("World")
        self.assertGreaterEqual(addr1, USER_DATA_BASE)
        self.assertGreater(addr2, addr1)
        self.assertEqual(self.vmm.read_string(addr1), "Hello")
        self.assertEqual(self.vmm.read_string(addr2), "World")

    def test_heap_expansion_and_access(self):
        old_brk = self.vmm.current_brk
        # Expand heap by 4KB
        new_brk = self.vmm.sys_brk(old_brk + 4096)
        self.assertEqual(new_brk, old_brk + 4096)
        # Writing within newly allocated heap must succeed
        self.vmm.write_bytes(old_brk + 10, b"Heap Data")
        data = self.vmm.read_bytes(old_brk + 10, 9)
        self.assertEqual(data, b"Heap Data")

    def test_sigsegv_on_unmapped_access(self):
        # Accessing unmapped memory above current heap break
        unmapped_addr = self.vmm.current_brk + 0x10000
        with self.assertRaises(SegmentationFault):
            self.vmm.read_bytes(unmapped_addr, 4)
        with self.assertRaises(SegmentationFault):
            self.vmm.write_bytes(unmapped_addr, b"FAIL")

    def test_sigsegv_on_null_pointer(self):
        with self.assertRaises(SegmentationFault):
            self.vmm.read_bytes(0x0, 8)

    def test_sigsegv_on_kernel_space_access(self):
        with self.assertRaises(SegmentationFault):
            self.vmm.read_bytes(0xFFFF800000000000, 8)

    def test_brk_query_and_limits(self):
        curr = self.vmm.current_brk
        # Query
        self.assertEqual(self.vmm.sys_brk(0), curr)
        # Attempt shrinking below start_brk should fail (return curr)
        self.assertEqual(self.vmm.sys_brk(self.vmm.start_brk - 100), curr)
        # Attempt expanding beyond max_brk should fail (return curr)
        self.assertEqual(self.vmm.sys_brk(self.vmm.max_brk + 1000), curr)

    def test_vmm_clone(self):
        self.vmm.write_bytes(USER_DATA_BASE, b"Parent data")
        child_vmm = self.vmm.clone(new_pid=1001)
        self.assertEqual(child_vmm.read_bytes(USER_DATA_BASE, 11), b"Parent data")
        # Mutating child memory must not affect parent
        child_vmm.write_bytes(USER_DATA_BASE, b"Child  data")
        self.assertEqual(child_vmm.read_bytes(USER_DATA_BASE, 11), b"Child  data")
        self.assertEqual(self.vmm.read_bytes(USER_DATA_BASE, 11), b"Parent data")


class TestVirtualFileSystem(unittest.TestCase):
    """Test VFS tree, path resolution, permissions, and file operations."""

    def setUp(self):
        self.vfs = VirtualFileSystem()

    def test_default_tree(self):
        root = self.vfs.resolve_path("/")
        self.assertIsNotNone(root)
        self.assertEqual(root.itype, InodeType.DIRECTORY)

        etc_release = self.vfs.resolve_path("/etc/os-release")
        self.assertIsNotNone(etc_release)
        self.assertEqual(etc_release.itype, InodeType.FILE)
        self.assertIn(b"KernelSim", etc_release.data)

        readme = self.vfs.resolve_path("/home/user/readme.txt")
        self.assertIsNotNone(readme)
        self.assertIn(b"Virtual File System", readme.data)

    def test_path_normalization(self):
        # Test relative paths, dot, and dot-dot
        inode1 = self.vfs.resolve_path("/etc/../home/user/readme.txt")
        inode2 = self.vfs.resolve_path("/home/user/./readme.txt")
        self.assertIsNotNone(inode1)
        self.assertEqual(inode1.ino, inode2.ino)

    def test_file_creation_and_open_flags(self):
        # Open nonexistent file without O_CREAT -> ENOENT
        desc, err = self.vfs.open_file("/home/user/missing.txt", flags=O_RDONLY)
        self.assertEqual(err, PosixErrno.ENOENT)
        self.assertIsNone(desc)

        # Open nonexistent file with O_CREAT -> SUCCESS
        desc, err = self.vfs.open_file("/home/user/created.txt", flags=O_WRONLY | O_CREAT, mode=0o644)
        self.assertEqual(err, PosixErrno.SUCCESS)
        self.assertIsNotNone(desc)

        # Open existing file with O_CREAT | O_EXCL -> EEXIST
        desc2, err2 = self.vfs.open_file("/home/user/created.txt", flags=O_WRONLY | O_CREAT | O_EXCL)
        self.assertEqual(err2, PosixErrno.EEXIST)

    def test_truncation_flag(self):
        # Create file with data
        self.vfs.create_file("/home/user", "trunc.txt", data=b"Existing content")
        # Open with O_TRUNC
        desc, err = self.vfs.open_file("/home/user/trunc.txt", flags=O_WRONLY | O_TRUNC)
        self.assertEqual(err, PosixErrno.SUCCESS)
        self.assertEqual(len(desc.inode.data), 0)

    def test_append_flag(self):
        self.vfs.create_file("/home/user", "append.txt", data=b"Initial")
        desc, err = self.vfs.open_file("/home/user/append.txt", flags=O_WRONLY | O_APPEND)
        self.assertEqual(err, PosixErrno.SUCCESS)
        self.assertEqual(desc.offset, 7)

    def test_character_devices(self):
        dev_null = self.vfs.resolve_path("/dev/null")
        self.assertIsNotNone(dev_null)
        self.assertEqual(dev_null.read_device(100), b"")
        self.assertEqual(dev_null.write_device(b"Discard me"), 10)

        dev_zero = self.vfs.resolve_path("/dev/zero")
        self.assertIsNotNone(dev_zero)
        self.assertEqual(dev_zero.read_device(5), b"\x00\x00\x00\x00\x00")


class TestFileDescriptorTable(unittest.TestCase):
    """Test per-process file descriptor allocation, closing, and cloning."""

    def setUp(self):
        self.fdt = FileDescriptorTable()

    def test_standard_streams(self):
        stdin = self.fdt.get(0)
        stdout = self.fdt.get(1)
        stderr = self.fdt.get(2)
        self.assertTrue(stdin.readable)
        self.assertFalse(stdin.writable)
        self.assertFalse(stdout.readable)
        self.assertTrue(stdout.writable)
        self.assertTrue(stderr.writable)

    def test_dynamic_allocation(self):
        inode = Inode(ino=99, name="test", itype=InodeType.FILE)
        desc = OpenFileDescription(inode=inode, flags=O_RDONLY)
        fd3 = self.fdt.allocate_fd(desc)
        self.assertEqual(fd3, 3)
        self.assertEqual(desc.ref_count, 1)  # 1 active reference

        fd4 = self.fdt.allocate_fd(desc)
        self.assertEqual(fd4, 4)
        self.assertEqual(desc.ref_count, 2)  # 2 active references

        # Close fd 3 and reallocate -> lowest available fd is 3
        err = self.fdt.close(fd3)
        self.assertEqual(err, PosixErrno.SUCCESS)
        self.assertEqual(desc.ref_count, 1)  # 1 active reference remaining

        fd_new = self.fdt.allocate_fd(desc)
        self.assertEqual(fd_new, 3)
        self.assertEqual(desc.ref_count, 2)

    def test_close_invalid_fd(self):
        self.assertEqual(self.fdt.close(999), PosixErrno.EBADF)


class TestSyscalls(unittest.TestCase):
    """Comprehensive test of all 7 implemented POSIX x86_64 system calls."""

    def setUp(self):
        self.kernel = Kernel()
        self.proc = self.kernel.proc_mgr.current

    def test_sys_write_and_sys_read_stdout_and_file(self):
        # 1. sys_write to stdout (fd 1)
        msg = "Unit test message\n"
        str_addr = self.proc.vmm.allocate_static_string(msg)
        self.proc.write_reg("RAX", 1)  # sys_write
        self.proc.write_reg("RDI", 1)  # stdout
        self.proc.write_reg("RSI", str_addr)
        self.proc.write_reg("RDX", len(msg))
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, len(msg))

        # 2. sys_write to bad file descriptor (fd 99)
        self.proc.write_reg("RAX", 1)
        self.proc.write_reg("RDI", 99)
        self.proc.write_reg("RSI", str_addr)
        self.proc.write_reg("RDX", len(msg))
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, errno_to_u64(PosixErrno.EBADF))

        # 3. sys_write with invalid memory address (SIGSEGV -> EFAULT)
        self.proc.write_reg("RAX", 1)
        self.proc.write_reg("RDI", 1)
        self.proc.write_reg("RSI", 0x0000000000001000)  # unmapped low address
        self.proc.write_reg("RDX", 16)
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, errno_to_u64(PosixErrno.EFAULT))

    def test_sys_open_and_sys_close(self):
        # Open existing file /etc/os-release
        path_addr = self.proc.vmm.allocate_static_string("/etc/os-release")
        self.proc.write_reg("RAX", 2)  # sys_open
        self.proc.write_reg("RDI", path_addr)
        self.proc.write_reg("RSI", O_RDONLY)
        self.proc.write_reg("RDX", 0)
        with redirect_stdout(io.StringIO()):
            fd = self.kernel.trigger_trap("SYSCALL")
        self.assertGreaterEqual(fd, 3)

        # Close the open fd
        self.proc.write_reg("RAX", 3)  # sys_close
        self.proc.write_reg("RDI", fd)
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, 0)

        # Closing already closed fd -> -EBADF
        self.proc.write_reg("RAX", 3)
        self.proc.write_reg("RDI", fd)
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, errno_to_u64(PosixErrno.EBADF))

    def test_sys_brk(self):
        # Query current break
        self.proc.write_reg("RAX", 12)  # sys_brk
        self.proc.write_reg("RDI", 0)
        with redirect_stdout(io.StringIO()):
            curr_brk = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(curr_brk, self.proc.vmm.start_brk)

        # Extend break by 8192 bytes
        target_brk = curr_brk + 8192
        self.proc.write_reg("RAX", 12)
        self.proc.write_reg("RDI", target_brk)
        with redirect_stdout(io.StringIO()):
            new_brk = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(new_brk, target_brk)

    def test_sys_fork_and_guard(self):
        # Basic fork
        self.proc.write_reg("RAX", 57)  # sys_fork
        with redirect_stdout(io.StringIO()):
            child_pid = self.kernel.trigger_trap("SYSCALL")
        self.assertGreater(child_pid, self.proc.pid)
        self.assertIn(child_pid, self.kernel.proc_mgr.processes)

        # Child RAX must be 0
        child = self.kernel.proc_mgr.processes[child_pid]
        self.assertEqual(child.read_reg("RAX"), 0)

        # Saturate process table to test fork bomb guard
        for _ in range(ProcessManager.MAX_PROCESSES + 2):
            self.kernel.proc_mgr.fork(self.proc)

        self.proc.write_reg("RAX", 57)
        with redirect_stdout(io.StringIO()):
            guard_ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(guard_ret, errno_to_u64(PosixErrno.EAGAIN))

    def test_sys_exit(self):
        self.proc.write_reg("RAX", 60)  # sys_exit
        self.proc.write_reg("RDI", 15)  # exit code 15
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, 15)
        self.assertEqual(self.proc.state, ProcessState.TERMINATED)
        self.assertEqual(self.proc.exit_code, 15)

    def test_unimplemented_syscall(self):
        # RAX = 999 (invalid syscall)
        self.proc.write_reg("RAX", 999)
        with redirect_stdout(io.StringIO()):
            ret = self.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret, errno_to_u64(PosixErrno.ENOSYS))


class TestAssemblyEmulatorREPL(unittest.TestCase):
    """Test interactive REPL command execution and demo runs."""

    def setUp(self):
        self.kernel = Kernel()
        self.repl = AssemblyEmulatorREPL(self.kernel)

    def test_cmd_mov_variants(self):
        with redirect_stdout(io.StringIO()):
            self.repl.cmd_mov("RAX", "100")
            self.assertEqual(self.kernel.proc_mgr.current.read_reg("RAX"), 100)

            self.repl.cmd_mov("RDI", "0x2A")
            self.assertEqual(self.kernel.proc_mgr.current.read_reg("RDI"), 42)

            self.repl.cmd_mov("RSI", "RAX")
            self.assertEqual(self.kernel.proc_mgr.current.read_reg("RSI"), 100)

            self.repl.cmd_mov("RDX", '"REPL String Literal\\n"')
            rdx_val = self.kernel.proc_mgr.current.read_reg("RDX")
            self.assertGreaterEqual(rdx_val, USER_DATA_BASE)
            # Memory should hold the string
            stored = self.kernel.proc_mgr.current.vmm.read_string(rdx_val)
            self.assertEqual(stored, "REPL String Literal\n")

    def test_repl_commands_execute_without_error(self):
        commands = [
            "DUMP",
            "LS_DISK",
            "CAT /etc/os-release",
            "CAT /dev/null",
            "PS",
            "MEM 0x00402000 16",
            "STORE 0x00402000 \"Test Store\"",
            "HELP",
            "RESET",
        ]
        with redirect_stdout(io.StringIO()):
            for cmd in commands:
                cont = self.repl.execute_command_line(cmd)
                self.assertTrue(cont)

    def test_demos_execution(self):
        demos = ["hello_world", "file_io", "fork_bomb_guard", "heap_alloc"]
        for demo in demos:
            with redirect_stdout(io.StringIO()):
                self.repl.cmd_load(demo)
                self.assertGreater(len(self.repl.loaded_program), 0)
                self.repl.cmd_run()
                self.assertEqual(self.repl.pc, len(self.repl.loaded_program))

    def test_int_0x80_trap(self):
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 12)  # sys_brk
        self.repl.kernel.proc_mgr.current.write_reg("RDI", 0)
        with redirect_stdout(io.StringIO()):
            cont = self.repl.execute_command_line("INT 0x80")
            self.assertTrue(cont)
        self.assertEqual(self.repl.kernel.proc_mgr.current.read_reg("RAX"), USER_HEAP_START)

    def test_shared_file_offset_on_fork(self):
        # Open file in parent
        path_addr = self.repl.kernel.proc_mgr.current.vmm.allocate_static_string("/home/user/shared.txt")
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 2)  # sys_open
        self.repl.kernel.proc_mgr.current.write_reg("RDI", path_addr)
        self.repl.kernel.proc_mgr.current.write_reg("RSI", O_RDWR | O_CREAT)
        self.repl.kernel.proc_mgr.current.write_reg("RDX", 0o644)
        with redirect_stdout(io.StringIO()):
            fd = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertGreaterEqual(fd, 3)

        # Write 5 bytes in parent
        data_addr = self.repl.kernel.proc_mgr.current.vmm.allocate_static_string("ABCDE")
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 1)  # sys_write
        self.repl.kernel.proc_mgr.current.write_reg("RDI", fd)
        self.repl.kernel.proc_mgr.current.write_reg("RSI", data_addr)
        self.repl.kernel.proc_mgr.current.write_reg("RDX", 5)
        with redirect_stdout(io.StringIO()):
            self.repl.kernel.trigger_trap("SYSCALL")

        # Fork
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 57)  # sys_fork
        with redirect_stdout(io.StringIO()):
            child_pid = self.repl.kernel.trigger_trap("SYSCALL")

        # Switch to child and write 5 more bytes to the same fd
        child_proc = self.repl.kernel.proc_mgr.processes[child_pid]
        child_data_addr = child_proc.vmm.allocate_static_string("FGHIJ")
        child_proc.write_reg("RAX", 1)  # sys_write
        child_proc.write_reg("RDI", fd)
        child_proc.write_reg("RSI", child_data_addr)
        child_proc.write_reg("RDX", 5)
        with redirect_stdout(io.StringIO()):
            # Temporarily activate child
            self.repl.kernel.proc_mgr.active_pid = child_pid
            self.repl.kernel.trigger_trap("SYSCALL")
            self.repl.kernel.proc_mgr.active_pid = 1000  # switch back to parent

        # Check file content and offset
        inode = self.repl.kernel.vfs.resolve_path("/home/user/shared.txt")
        self.assertEqual(bytes(inode.data), b"ABCDEFGHIJ")
        parent_desc = self.repl.kernel.proc_mgr.current.fd_table.get(fd)
        self.assertEqual(parent_desc.offset, 10)

    def test_eof_and_permissions_edge_cases(self):
        # Read from empty file returns 0 (EOF)
        empty_path = self.repl.kernel.proc_mgr.current.vmm.allocate_static_string("/dev/null")
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 2)
        self.repl.kernel.proc_mgr.current.write_reg("RDI", empty_path)
        self.repl.kernel.proc_mgr.current.write_reg("RSI", O_RDONLY)
        with redirect_stdout(io.StringIO()):
            fd = self.repl.kernel.trigger_trap("SYSCALL")

        self.repl.kernel.proc_mgr.current.vmm.sys_brk(USER_HEAP_START + 4096)
        buf_addr = self.repl.kernel.proc_mgr.current.vmm.start_brk
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 0)  # sys_read
        self.repl.kernel.proc_mgr.current.write_reg("RDI", fd)
        self.repl.kernel.proc_mgr.current.write_reg("RSI", buf_addr)
        self.repl.kernel.proc_mgr.current.write_reg("RDX", 10)
        with redirect_stdout(io.StringIO()):
            count = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertEqual(count, 0)

        # Write to O_RDONLY fd returns -EBADF
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 1)  # sys_write
        self.repl.kernel.proc_mgr.current.write_reg("RDI", fd)
        self.repl.kernel.proc_mgr.current.write_reg("RSI", buf_addr)
        self.repl.kernel.proc_mgr.current.write_reg("RDX", 10)
        with redirect_stdout(io.StringIO()):
            err_code = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertEqual(err_code, errno_to_u64(PosixErrno.EBADF))

        # Negative count returns -EINVAL
        self.repl.kernel.proc_mgr.current.write_reg("RAX", 0)
        self.repl.kernel.proc_mgr.current.write_reg("RDX", -5)
        with redirect_stdout(io.StringIO()):
            inv_ret = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertEqual(inv_ret, errno_to_u64(PosixErrno.EINVAL))

    def test_heap_contraction_purges_pages(self):
        vmm = VirtualMemoryManager(pid=2000)
        # Allocate 2 pages (8192 bytes)
        b1 = vmm.sys_brk(vmm.start_brk + 8192)
        target_addr = vmm.start_brk + 5000
        vmm.write_bytes(target_addr, b"Valid data")
        self.assertEqual(vmm.read_bytes(target_addr, 10), b"Valid data")

        # Contract heap back to start_brk + 4096 (dropping second page)
        vmm.sys_brk(vmm.start_brk + 4096)
        # target_addr is now unmapped and must trigger SIGSEGV
        with self.assertRaises(SegmentationFault):
            vmm.read_bytes(target_addr, 10)

    def test_fork_child_register_and_privilege_state(self):
        """Verify child process context after sys_fork (Ring 3, user RSP, next RIP, RAX=0)."""
        proc = self.repl.kernel.proc_mgr.current
        proc.write_reg("RAX", 57)  # sys_fork
        user_rsp_before = proc.read_reg("RSP")
        user_rip_before = proc.read_reg("RIP")

        with redirect_stdout(io.StringIO()):
            child_pid = self.repl.kernel.trigger_trap("SYSCALL")

        self.assertGreater(child_pid, proc.pid)
        child = self.repl.kernel.proc_mgr.processes[child_pid]

        # Verify child state
        self.assertEqual(child.cpl, PrivilegeLevel.RING_3)
        self.assertEqual(child.read_reg("RAX"), 0)
        self.assertEqual(child.read_reg("RSP"), user_rsp_before)
        self.assertEqual(child.read_reg("RIP"), user_rip_before + 2)
        # Parent RAX is child PID
        self.assertEqual(proc.read_reg("RAX"), child_pid)

    def test_sys_read_stdin_buffered(self):
        """Verify sys_read reads data from STDIN (fd 0)."""
        proc = self.repl.kernel.proc_mgr.current
        stdin_stream = proc.fd_table.get(0)
        stdin_stream.feed_input(b"Hello Stdin\n")

        proc.vmm.sys_brk(USER_HEAP_START + 4096)
        buf_addr = proc.vmm.start_brk

        proc.write_reg("RAX", 0)  # sys_read
        proc.write_reg("RDI", 0)  # STDIN
        proc.write_reg("RSI", buf_addr)
        proc.write_reg("RDX", 12)

        with redirect_stdout(io.StringIO()):
            bytes_read = self.repl.kernel.trigger_trap("SYSCALL")

        self.assertEqual(bytes_read, 12)
        self.assertEqual(proc.vmm.read_bytes(buf_addr, 12), b"Hello Stdin\n")

    def test_count_zero_on_invalid_fd_returns_ebadf(self):
        """Verify read and write with count=0 on invalid fd return -EBADF."""
        proc = self.repl.kernel.proc_mgr.current
        proc.write_reg("RAX", 0)  # sys_read
        proc.write_reg("RDI", 999)  # bad fd
        proc.write_reg("RSI", USER_DATA_BASE)
        proc.write_reg("RDX", 0)
        with redirect_stdout(io.StringIO()):
            ret_read = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret_read, errno_to_u64(PosixErrno.EBADF))

        proc.write_reg("RAX", 1)  # sys_write
        proc.write_reg("RDI", 999)  # bad fd
        proc.write_reg("RSI", USER_DATA_BASE)
        proc.write_reg("RDX", 0)
        with redirect_stdout(io.StringIO()):
            ret_write = self.repl.kernel.trigger_trap("SYSCALL")
        self.assertEqual(ret_write, errno_to_u64(PosixErrno.EBADF))

    def test_open_file_posix_edge_cases(self):
        """Test open_file empty path, EISDIR on directory write, and ENOTDIR on trailing slash."""
        # 1. Empty string -> ENOENT
        desc, err = self.repl.kernel.vfs.open_file("", flags=O_RDONLY)
        self.assertEqual(err, PosixErrno.ENOENT)
        self.assertIsNone(desc)

        desc, err = self.repl.kernel.vfs.open_file("", flags=O_CREAT | O_WRONLY)
        self.assertEqual(err, PosixErrno.ENOENT)
        self.assertIsNone(desc)

        # 2. Open directory for write -> EISDIR
        desc, err = self.repl.kernel.vfs.open_file("/home", flags=O_WRONLY)
        self.assertEqual(err, PosixErrno.EISDIR)

        # 3. Trailing slash on regular file -> ENOTDIR
        desc, err = self.repl.kernel.vfs.open_file("/etc/os-release/", flags=O_RDONLY)
        self.assertEqual(err, PosixErrno.ENOTDIR)

    def test_repl_inline_comments(self):
        """Verify REPL strips inline comments (; and #) properly."""
        with redirect_stdout(io.StringIO()):
            self.repl.execute_command_line("MOV RAX, 123 ; inline comment here")
            self.assertEqual(self.repl.kernel.proc_mgr.current.read_reg("RAX"), 123)

            self.repl.execute_command_line("MOV RDI, 456 # hash comment here")
            self.assertEqual(self.repl.kernel.proc_mgr.current.read_reg("RDI"), 456)

            # Quoted comments should be preserved in literals
            self.repl.execute_command_line("MOV RSI, \"String; with # symbols\" ; trailing comment")
            rsi_addr = self.repl.kernel.proc_mgr.current.read_reg("RSI")
            stored = self.repl.kernel.proc_mgr.current.vmm.read_string(rsi_addr)
            self.assertEqual(stored, "String; with # symbols")

    def test_repl_memory_mov_dereference(self):
        """Verify MOV [addr], val and MOV reg, [addr] work via REPL."""
        addr = USER_DATA_BASE + 256
        with redirect_stdout(io.StringIO()):
            self.repl.execute_command_line(f"MOV [{hex(addr)}], 0xCAFEBABE")
            self.repl.execute_command_line(f"MOV R9, [{hex(addr)}]")
        self.assertEqual(self.repl.kernel.proc_mgr.current.read_reg("R9"), 0xCAFEBABE)

    def test_consecutive_demos_reset_process_state(self):
        """Verify consecutive demos run cleanly even if prior demo called sys_exit."""
        with redirect_stdout(io.StringIO()):
            # hello_world exits with sys_exit(0)
            self.repl.cmd_load("hello_world")
            self.repl.cmd_run()
            self.assertEqual(self.repl.kernel.proc_mgr.current.state, ProcessState.TERMINATED)

            # file_io should revitalize process context and succeed
            self.repl.cmd_load("file_io")
            self.assertEqual(self.repl.kernel.proc_mgr.current.state, ProcessState.RUNNING)
            self.assertIsNotNone(self.repl.kernel.proc_mgr.current.fd_table.get(1))
            self.repl.cmd_run()
            self.assertEqual(self.repl.pc, len(self.repl.loaded_program))

            # heap_alloc should also revitalize and succeed
            self.repl.cmd_load("heap_alloc")
            self.assertEqual(self.repl.kernel.proc_mgr.current.state, ProcessState.RUNNING)
            self.repl.cmd_run()
            self.assertEqual(self.repl.pc, len(self.repl.loaded_program))

    def test_text_segment_write_protection(self):
        """Verify writing to code segment [USER_TEXT_BASE, USER_DATA_BASE) raises SegmentationFault."""
        vmm = VirtualMemoryManager(pid=3000)
        # Read from text base is allowed
        self.assertTrue(vmm.is_address_valid(USER_TEXT_BASE, 8, is_write=False))
        # Write to text base triggers fault
        self.assertFalse(vmm.is_address_valid(USER_TEXT_BASE, 8, is_write=True))
        with self.assertRaises(SegmentationFault):
            vmm.write_bytes(USER_TEXT_BASE, b"ILLEGAL")


if __name__ == "__main__":
    unittest.main()
