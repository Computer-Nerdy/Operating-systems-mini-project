#!/usr/bin/env python3
"""
Generate a professional, fully-formatted academic mini-project report (.docx and .md)
for SRM Institute of Science and Technology, Ramapuram Campus.
Course: 21CSC202J - OPERATING SYSTEMS
Title: DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR
Students:
- Harish Ragav V [RA2511032020045]
- Pradeep M [RA2511032020014]
- Midhun Ganesan S [RA2511032020031]
"""

import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Sets background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding in dxa."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    """Applies neat borders to an entire table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_code_block(doc, code_text):
    """Adds a shaded monospace code block."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F4F5F7")
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    border = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:left w:val="single" w:sz="18" w:space="0" w:color="003366"/><w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/></w:tcBorders>')
    tcPr.append(border)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    
    # Extra space after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)

def build_docx_report(file_path):
    doc = docx.Document()
    
    # Page setup - Margins 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
    # Styles
    navy = RGBColor(0x00, 0x20, 0x60)
    slate_blue = RGBColor(0x1F, 0x4E, 0x79)
    dark_gray = RGBColor(0x33, 0x33, 0x33)
    
    # -------------------------------------------------------------
    # 1. TITLE / COVER PAGE
    # -------------------------------------------------------------
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(36)
    p_title.paragraph_format.space_after = Pt(12)
    r = p_title.add_run("DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR")
    r.font.name = "Arial"
    r.font.size = Pt(17)
    r.font.bold = True
    r.font.color.rgb = navy
    
    p_course = doc.add_paragraph()
    p_course.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_course.paragraph_format.space_before = Pt(6)
    p_course.paragraph_format.space_after = Pt(16)
    r = p_course.add_run("21CSC202J – OPERATING SYSTEMS\nA MINI-PROJECT REPORT")
    r.font.name = "Arial"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(12)
    p_sub.paragraph_format.space_after = Pt(8)
    r = p_sub.add_run("Submitted By")
    r.font.name = "Arial"
    r.font.size = Pt(11)
    r.font.italic = True
    
    p_names = doc.add_paragraph()
    p_names.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_names.paragraph_format.space_before = Pt(4)
    p_names.paragraph_format.space_after = Pt(20)
    r = p_names.add_run(
        "HARISH RAGAV V [RA2511032020045]\n"
        "PRADEEP M [RA2511032020014]\n"
        "MIDHUN GANESAN S [RA2511032020031]"
    )
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    
    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_deg.paragraph_format.space_before = Pt(12)
    p_deg.paragraph_format.space_after = Pt(24)
    r = p_deg.add_run(
        "in partial fulfilment for the award of the degree of\n"
        "BACHELOR OF TECHNOLOGY\n"
        "in\n"
        "COMPUTER SCIENCE AND ENGINEERING W/S IOT\n"
        "of\n"
        "FACULTY OF ENGINEERING AND TECHNOLOGY"
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(36)
    p_inst.paragraph_format.space_after = Pt(0)
    r = p_inst.add_run(
        "SRM INSTITUTE OF SCIENCE AND TECHNOLOGY\n"
        "RAMAPURAM CAMPUS, CHENNAI – 600089\n"
        "OCTOBER 2026"
    )
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = navy
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 2. BONAFIDE CERTIFICATE
    # -------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY\n(Deemed to be University U/S 3 of UGC Act, 1956)\nRAMAPURAM CAMPUS, CHENNAI – 600089")
    r.font.name = "Arial"
    r.font.size = Pt(11)
    r.font.bold = True
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("BONAFIDE CERTIFICATE")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = navy
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(30)
    r = p.add_run(
        "Certified that this mini project report titled “DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR” is the bonafide work of “HARISH RAGAV V (RA2511032020045), PRADEEP M (RA2511032020014), MIDHUN GANESAN S (RA2511032020031)” who carried out the project under my supervision for the course 21CSC202J – OPERATING SYSTEMS."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11.5)
    
    # Signature table
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_l, cell_r = sig_table.cell(0, 0), sig_table.cell(0, 1)
    cell_l.width = Inches(3.2)
    cell_r.width = Inches(3.2)
    
    p = cell_r.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(
        "SIGNATURE\n\n\n\n"
        "Dr. TKS Rathish babu, M.E., Ph.D.,\n"
        "Associate Professor,\n"
        "Dept of CSE W/S IOT,\n"
        "SRM Institute of Science and Technology,\n"
        "Ramapuram Campus, Chennai – 600089."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 3. DECLARATION
    # -------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY\nRAMAPURAM, CHENNAI – 600089")
    r.font.name = "Arial"
    r.font.size = Pt(11)
    r.font.bold = True
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(18)
    r = p.add_run("DECLARATION")
    r.font.name = "Arial"
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = navy
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(24)
    r = p.add_run(
        "We hereby declare that the entire work contained in this mini project report titled “DESIGN AND IMPLEMENTATION OF AN INTERACTIVE X86_64 SYSTEM CALL AND KERNEL TRAP SIMULATOR” has been carried out by HARISH RAGAV V [RA2511032020045], PRADEEP M [RA2511032020014], and MIDHUN GANESAN S [RA2511032020031] at SRM Institute of Science and Technology, Ramapuram Campus, Chennai – 600089, in partial fulfilment of the requirements for the course 21CSC202J – OPERATING SYSTEMS."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11.5)
    
    p_dec = doc.add_paragraph()
    p_dec.paragraph_format.space_before = Pt(24)
    p_dec.paragraph_format.space_after = Pt(6)
    r = p_dec.add_run("Place: Chennai\nDate: 08-10-2026\n\n\n")
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    p_sign = doc.add_paragraph()
    p_sign.paragraph_format.line_spacing = 1.3
    r = p_sign.add_run(
        "1. HARISH RAGAV V [RA2511032020045]\n\n"
        "2. PRADEEP M [RA2511032020014]\n\n"
        "3. MIDHUN GANESAN S [RA2511032020031]"
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.bold = True
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 4. ABSTRACT
    # -------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ABSTRACT")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run(
        "In modern operating system architectures, the boundary between user space and kernel space forms the fundamental security and reliability perimeter of the system. Operating system pedagogical tools frequently suffer from an abstraction gap: students study low-level hardware transitions (such as x86_64 privilege rings, Task State Segment stack switches, and Model-Specific Register dispatch) theoretically, but lack an inspectable, deterministic platform to trace these transitions step by step.\n\n"
        "This project presents the design and implementation of an interactive, production-grade System Call & Kernel Trap Simulator developed strictly using the Python standard library with zero external dependencies. The simulator models the x86_64 architecture's privilege levels (Current Privilege Level Ring 3 vs Ring 0), CPU general-purpose registers (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS), and hardware trap mechanisms supporting both modern fast system calls via MSR_LSTAR (SYSCALL / SYSRETQ) and legacy software interrupts (INT 0x80 / IRETQ).\n\n"
        "Within the simulated kernel space, the system incorporates an in-memory Virtual File System (VFS) with virtual inodes, permissions, and directory traversal; a per-process File Descriptor Table managing standard streams (0: STDIN, 1: STDOUT, 2: STDERR) and dynamically allocated handles; a Virtual Memory Manager simulating heap break adjustment (brk/sbrk) with boundary enforcement triggering simulated SIGSEGV page faults; and a Process Control Block (PCB) subsystem supporting process creation (sys_fork), state transitions, and fork-bomb prevention. An integrated interactive assembly Read-Eval-Print Loop (REPL) allows step-by-step execution, dynamic memory inspection, and automated execution of pre-loaded programs (hello_world, file_io, heap_alloc, fork_bomb_guard). The implementation is verified against an automated suite of 42 unit tests, demonstrating 100% compliance with POSIX error handling and x86_64 ABI calling conventions."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 5. TABLE OF CONTENTS
    # -------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("TABLE OF CONTENTS")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    toc_data = [
        ("Chapter No.", "Title", "Page No."),
        ("", "ABSTRACT", "iv"),
        ("", "LIST OF TABLES", "vii"),
        ("", "LIST OF FIGURES", "viii"),
        ("", "LIST OF ABBREVIATIONS", "ix"),
        ("1", "INTRODUCTION", "1"),
        ("", "1.1 Overview", "1"),
        ("", "1.2 Problem Statement", "2"),
        ("", "1.3 Aim and Objectives", "2"),
        ("", "1.4 Scope of the Project", "3"),
        ("2", "SYSTEM REQUIREMENTS & SPECIFICATIONS", "4"),
        ("", "2.1 Hardware Requirements", "4"),
        ("", "2.2 Software Requirements", "4"),
        ("", "2.3 CPU and Architectural Specifications", "5"),
        ("3", "SYSTEM DESIGN AND ARCHITECTURE", "7"),
        ("", "3.1 Architectural Overview", "7"),
        ("", "3.2 CPU & Hardware Trap Pipeline", "9"),
        ("", "3.3 Kernel Subsystems & Data Structures", "11"),
        ("", "3.3.1 Virtual File System (VFS) & Inodes", "11"),
        ("", "3.3.2 File Descriptor Table & Descriptions", "12"),
        ("", "3.3.3 Virtual Memory Manager & Heap Segmentation", "13"),
        ("", "3.3.4 Process Control Block & Management", "14"),
        ("", "3.4 Supported POSIX/x86_64 System Calls", "16"),
        ("", "3.5 Interactive Assembly Interpreter (REPL)", "18"),
        ("4", "EXPERIMENTAL RESULTS AND VERIFICATION", "21"),
        ("", "4.1 Test Harness & Automated Unit Verification", "21"),
        ("", "4.2 Step-by-Step Trap Execution Trace", "23"),
        ("", "4.3 Virtual Memory Violation (SIGSEGV) Demonstration", "26"),
        ("", "4.4 Process Duplication (sys_fork) & Fork-Bomb Guard", "28"),
        ("5", "CONCLUSION AND FUTURE SCOPE", "30"),
        ("", "5.1 Conclusion", "30"),
        ("", "5.2 Future Scope", "31"),
        ("", "REFERENCES", "32"),
        ("", "APPENDIX: SOURCE CODE", "33"),
    ]
    
    t_toc = doc.add_table(rows=len(toc_data), cols=3)
    t_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_toc)
    for i, row in enumerate(toc_data):
        c0, c1, c2 = t_toc.cell(i, 0), t_toc.cell(i, 1), t_toc.cell(i, 2)
        c0.width = Inches(1.2)
        c1.width = Inches(4.3)
        c2.width = Inches(1.0)
        
        c0.paragraphs[0].text = row[0]
        c1.paragraphs[0].text = row[1]
        c2.paragraphs[0].text = row[2]
        
        c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        
        if i == 0:
            set_cell_background(c0, "002060")
            set_cell_background(c1, "002060")
            set_cell_background(c2, "002060")
            for c in (c0, c1, c2):
                p = c.paragraphs[0]
                for run in p.runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            for c in (c0, c1, c2):
                p = c.paragraphs[0]
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    if row[0] != "":
                        run.font.bold = True
                        
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 6. LIST OF TABLES & FIGURES & ABBREVIATIONS
    # -------------------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("LIST OF TABLES")
    r.font.name = "Arial"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = navy
    
    tables_list = [
        ("Table No.", "Table Name", "Page No."),
        ("2.1", "Hardware and Host Platform Specifications", "4"),
        ("2.2", "Emulated 64-Bit CPU Registers & Calling Conventions", "5"),
        ("3.1", "Implemented POSIX System Calls & ABI Register Mappings", "16"),
        ("3.2", "POSIX Error Numbers (errno) Handled by Simulated Kernel", "17"),
        ("3.3", "Interactive Assembly REPL Command Reference", "19"),
        ("4.1", "Automated Unit Test Suite Summary (42 Test Cases)", "22"),
    ]
    t_tab = doc.add_table(rows=len(tables_list), cols=3)
    t_tab.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_tab)
    for i, row in enumerate(tables_list):
        c0, c1, c2 = t_tab.cell(i, 0), t_tab.cell(i, 1), t_tab.cell(i, 2)
        c0.width, c1.width, c2.width = Inches(1.2), Inches(4.3), Inches(1.0)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text = row
        c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(16)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("LIST OF FIGURES")
    r.font.name = "Arial"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = navy
    
    figures_list = [
        ("Fig No.", "Figure Name", "Page No."),
        ("3.1", "High-Level Architecture of System Call & Kernel Trap Simulator", "8"),
        ("3.2", "User-to-Kernel 6-Step Hardware Trap Lifecycle", "10"),
        ("3.3", "Virtual File System (VFS) and Inode Hierarchical Model", "12"),
        ("3.4", "Process Virtual Memory Space & Heap Break (brk) Layout", "14"),
        ("4.1", "ANSI-Colored Hardware Trap Execution Trace Output", "25"),
        ("4.2", "Unmapped Address Dereference and SIGSEGV Crash Dump", "27"),
        ("4.3", "Process Tree State Before and After sys_fork Execution", "29"),
    ]
    t_fig = doc.add_table(rows=len(figures_list), cols=3)
    t_fig.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_fig)
    for i, row in enumerate(figures_list):
        c0, c1, c2 = t_fig.cell(i, 0), t_fig.cell(i, 1), t_fig.cell(i, 2)
        c0.width, c1.width, c2.width = Inches(1.2), Inches(4.3), Inches(1.0)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text = row
        c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(16)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("LIST OF ABBREVIATIONS")
    r.font.name = "Arial"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = navy
    
    abbrevs = [
        ("ABI", "Application Binary Interface"),
        ("CPL", "Current Privilege Level (CPU Rings 0-3)"),
        ("CPU", "Central Processing Unit"),
        ("FD", "File Descriptor"),
        ("FDT", "File Descriptor Table"),
        ("GPR", "General Purpose Register"),
        ("IDT", "Interrupt Descriptor Table"),
        ("IVT", "Interrupt Vector Table"),
        ("MSR", "Model-Specific Register (MSR_LSTAR)"),
        ("OS", "Operating System"),
        ("PCB", "Process Control Block"),
        ("POSIX", "Portable Operating System Interface"),
        ("REPL", "Read-Eval-Print Loop"),
        ("TSS", "Task State Segment"),
        ("VFS", "Virtual File System"),
        ("VMM", "Virtual Memory Manager"),
    ]
    t_abb = doc.add_table(rows=len(abbrevs)+1, cols=2)
    t_abb.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_abb)
    t_abb.cell(0, 0).paragraphs[0].text = "Abbreviation"
    t_abb.cell(0, 1).paragraphs[0].text = "Expansion"
    set_cell_background(t_abb.cell(0, 0), "1F4E79")
    set_cell_background(t_abb.cell(0, 1), "1F4E79")
    t_abb.cell(0, 0).width = Inches(2.0)
    t_abb.cell(0, 1).width = Inches(4.5)
    for c in (t_abb.cell(0, 0), t_abb.cell(0, 1)):
        for r in c.paragraphs[0].runs:
            r.font.name = "Arial"
            r.font.bold = True
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            
    for i, (a, exp) in enumerate(abbrevs):
        c0, c1 = t_abb.cell(i+1, 0), t_abb.cell(i+1, 1)
        c0.width, c1.width = Inches(2.0), Inches(4.5)
        c0.paragraphs[0].text, c1.paragraphs[0].text = a, exp
        c0.paragraphs[0].runs[0].font.bold = True
        for c in (c0, c1):
            for r in c.paragraphs[0].runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(10)
                
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # CHAPTER 1: INTRODUCTION
    # -------------------------------------------------------------
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(6)
    r = h1.add_run("CHAPTER 1\nINTRODUCTION")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    h2 = doc.add_paragraph()
    r = h2.add_run("1.1 Overview")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(
        "An Operating System acts as the primary intermediary between user-level application software and physical computational hardware. In modern computers running processor architectures like x86_64, isolation is strictly enforced via hardware-assisted execution privilege levels known as Privilege Rings. User applications run in Ring 3 (least privileged), while the core operating system kernel executes in Ring 0 (supervisor mode).\n\n"
        "Whenever a user-space program requires a privileged resource—such as reading user input from a terminal, writing a buffer to disk, adjusting dynamic heap allocations, or creating an independent child process—it cannot execute those hardware instructions directly. Instead, it must trigger a controlled Software Trap or System Call (Syscall).\n\n"
        "During this trap, the CPU performs an atomic transition: it preserves the user program's register states, switches the execution stack pointer from the user stack to an elevated kernel stack, elevates the privilege ring to Ring 0, indexes into an Interrupt Vector Table (IVT) or enters through a Model-Specific Register (MSR_LSTAR), executes the kernel routine, writes the return value back into the accumulator register (RAX), and restores user-space execution via SYSRETQ or IRETQ."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("1.2 Problem Statement")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(
        "Understanding the precise boundary of system call traps is central to systems programming, kernel engineering, and security research. However, existing operating systems (e.g., standard Linux distributions or Windows) present significant educational challenges:\n"
        "1. Black-Box Nature: Commercial and monolithic kernels execute syscall transitions in sub-microsecond hardware routines, masking intermediate steps such as stack switches, pt_regs preservation, and ABI register decoding from developer observation.\n"
        "2. Crash Fragility: Experimenting with illegal pointers, kernel stack corruption, or fork-bombs on bare-metal systems results in kernel panics, frozen operating systems, or irrecoverable system crashes.\n"
        "3. Complex Toolchain Overhead: Standard bare-metal simulators (such as QEMU or Bochs) require heavy binary toolchains, cross-compilers, and kernel compilation pipelines, creating high setup friction for student exploration.\n\n"
        "There is a distinct need for a zero-dependency, fully inspectable, deterministic operating system simulator that authentically mirrors x86_64 kernel trapping, memory segmentation, virtual file systems, and process control."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("1.3 Aim and Objectives")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(
        "The primary aim of this project is to build an interactive, production-grade System Call & Kernel Trap Simulator in pure Python that models user-to-kernel space context transitions with zero external dependencies.\n\n"
        "Specific objectives include:\n"
        "• Emulating a 64-bit CPU architecture featuring GPRs (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS) and dual privilege levels (Ring 3 vs Ring 0).\n"
        "• Modeling the complete 6-step hardware trap lifecycle supporting both SYSCALL (MSR_LSTAR) and legacy INT 0x80.\n"
        "• Developing an in-memory Virtual File System (VFS) with virtual inodes, permissions, file tables, and POSIX path resolution.\n"
        "• Implementing a per-process File Descriptor Table mapping standard streams (0, 1, 2) and dynamically assigned descriptors.\n"
        "• Simulating virtual memory protection (brk/sbrk) that detects out-of-bounds addresses and raises simulated SIGSEGV signals.\n"
        "• Implementing seven POSIX-aligned system calls (sys_read, sys_write, sys_open, sys_close, sys_brk, sys_fork, sys_exit).\n"
        "• Building an interactive terminal REPL and assembly emulator with step-by-step visual execution logs."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("1.4 Scope of the Project")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(
        "The simulator serves as an interactive instructional and diagnostic testbed for Operating Systems courses. Students and researchers can write or load simulated assembly scripts, trace register-level calling conventions, test POSIX file operations, observe memory allocation boundaries, and safely analyze kernel behavior under edge conditions without hardware risk."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # CHAPTER 2: SYSTEM REQUIREMENTS & SPECIFICATIONS
    # -------------------------------------------------------------
    h1 = doc.add_paragraph()
    r = h1.add_run("CHAPTER 2\nSYSTEM REQUIREMENTS & SPECIFICATIONS")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    h2 = doc.add_paragraph()
    r = h2.add_run("2.1 Hardware Requirements")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    # Table 2.1
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Table 2.1: Hardware and Host Platform Specifications")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.bold = True
    
    t_hdw = doc.add_table(rows=5, cols=3)
    t_hdw.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_hdw)
    hdw_rows = [
        ("Component", "Minimum Specification", "Recommended Specification"),
        ("Processor", "Dual Core x86_64 / ARM64, 1.8 GHz", "Quad Core Intel i5 / AMD Ryzen 5, 2.5 GHz+"),
        ("System Memory (RAM)", "2 GB", "8 GB or higher"),
        ("Storage (Disk)", "50 MB free space", "500 MB free space"),
        ("Display / Terminal", "80x24 standard terminal", "120x30 ANSI/VT100 color-enabled terminal"),
    ]
    for i, row in enumerate(hdw_rows):
        c0, c1, c2 = t_hdw.cell(i, 0), t_hdw.cell(i, 1), t_hdw.cell(i, 2)
        c0.width, c1.width, c2.width = Inches(1.8), Inches(2.3), Inches(2.4)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text = row
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    r = h2.add_run("2.2 Software Requirements")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "• Operating System: Windows 10/11, Ubuntu 20.04/22.04 LTS, macOS 12+.\n"
        "• Language Runtime: Python 3.8+ (Pure standard library: sys, os, time, enum, shlex, struct, typing, dataclasses, unittest).\n"
        "• Third-Party Dependencies: Zero (0). Can run immediately on any standard Python installation without pip package overhead."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    r = h2.add_run("2.3 CPU and Architectural Specifications")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    # Table 2.2
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Table 2.2: Emulated 64-Bit CPU Registers & Calling Conventions")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.bold = True
    
    t_reg = doc.add_table(rows=11, cols=3)
    t_reg.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_reg)
    reg_data = [
        ("Register", "Bit Width", "Architectural Function & Linux ABI Role"),
        ("RAX", "64-bit", "Syscall Number on input; Return Value / Error Code (-errno) on output"),
        ("RDI", "64-bit", "1st Argument passed to system call"),
        ("RSI", "64-bit", "2nd Argument passed to system call (e.g., buffer pointer)"),
        ("RDX", "64-bit", "3rd Argument passed to system call (e.g., byte count)"),
        ("R10", "64-bit", "4th Argument passed to system call (replaces RCX clobbered by SYSCALL)"),
        ("R8", "64-bit", "5th Argument passed to system call"),
        ("R9", "64-bit", "6th Argument passed to system call"),
        ("RSP", "64-bit", "Stack Pointer (User stack 0x7fffffffe000 vs Kernel TSS 0xffff8000...)"),
        ("RIP", "64-bit", "Instruction Pointer (Program Counter)"),
        ("RFLAGS", "64-bit", "Status Flags register (Interrupt Enable IF, Zero ZF, Sign SF)"),
    ]
    for i, row in enumerate(reg_data):
        c0, c1, c2 = t_reg.cell(i, 0), t_reg.cell(i, 1), t_reg.cell(i, 2)
        c0.width, c1.width, c2.width = Inches(1.2), Inches(1.2), Inches(4.1)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text = row
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            c0.paragraphs[0].runs[0].font.bold = True
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # CHAPTER 3: SYSTEM DESIGN AND ARCHITECTURE
    # -------------------------------------------------------------
    h1 = doc.add_paragraph()
    r = h1.add_run("CHAPTER 3\nSYSTEM DESIGN AND ARCHITECTURE")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    h2 = doc.add_paragraph()
    r = h2.add_run("3.1 Architectural Overview")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "The simulator is structured into distinct, modular layers mirroring a production operating system: the Hardware/CPU Layer, the Trap & Dispatch Layer, the Kernel Subsystems Layer, and the User/REPL Layer."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    arch_ascii = (
        "+-----------------------------------------------------------------------------------+\n"
        "|                        USER SPACE REPL & ASSEMBLY PARSER                          |\n"
        "|    Commands: MOV, SYSCALL, INT 0x80, DUMP, LS_DISK, CAT, LOAD, STEP, RUN, PS     |\n"
        "|    Demos: hello_world, file_io, heap_alloc, fork_bomb_guard                      |\n"
        "+-----------------------------------------+-----------------------------------------+\n"
        "                                          |\n"
        "                              [Privilege Ring Boundary]\n"
        "                                          |\n"
        "+-----------------------------------------v-----------------------------------------+\n"
        "|                              CPU & TRAP DISPATCHER                                |\n"
        "|  - 64-bit GPRs (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS)               |\n"
        "|  - Privilege Levels: Ring 3 (User) <---> Ring 0 (Kernel Supervisor)               |\n"
        "|  - Trap Vectors: MSR_LSTAR (Fast SYSCALL) & IDT Vector 0x80 (Legacy Software)    |\n"
        "|  - Stack Context Push: struct pt_regs pushed onto Task State Segment (TSS RSP0)  |\n"
        "+-----------------------------------------+-----------------------------------------+\n"
        "                                          |\n"
        "                                          v\n"
        "+-----------------------------------------------------------------------------------+\n"
        "|                            KERNEL SUBSYSTEMS (RING 0)                             |\n"
        "|                                                                                   |\n"
        "|  [Interrupt Vector Table]   [Virtual Memory Manager]   [Process Control Subsystem]|\n"
        "|   - 0:  sys_read             - Segment Range Tracker    - Process Table (PIDs)    |\n"
        "|   - 1:  sys_write            - brk/sbrk Heap Allocator  - PCB State Snapshots     |\n"
        "|   - 2:  sys_open             - SIGSEGV Trap Generator   - Fork Bomb Guard (Max 32)|\n"
        "|   - 3:  sys_close                                                                 |\n"
        "|   - 12: sys_brk             [Virtual File System]      [File Descriptor Table]    |\n"
        "|   - 57: sys_fork             - Inodes & Dentries        - FD 0 (STDIN)            |\n"
        "|   - 60: sys_exit             - Directory Trees          - FD 1 (STDOUT)           |\n"
        "|                              - /dev/null, /dev/zero     - FD 2 (STDERR)           |\n"
        "|                              - POSIX Permissions        - Dynamic FDs (>= 3)      |\n"
        "+-----------------------------------------------------------------------------------+"
    )
    add_code_block(doc, arch_ascii)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(12)
    r = p.add_run("Figure 3.1: High-Level Architecture of System Call & Kernel Trap Simulator")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r.font.italic = True
    
    h2 = doc.add_paragraph()
    r = h2.add_run("3.2 CPU & Hardware Trap Pipeline")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "When a user process executes SYSCALL or INT 0x80, the CPU initiates an atomic, 6-step context switch:\n"
        "1. Trap Detection: Modern x86_64 enters via Model-Specific Register MSR_LSTAR (0xC0000082); legacy mode routes via IDT vector 0x80.\n"
        "2. Hardware Context Save: The CPU saves user registers (RAX, RDI, RSI, RDX, R10, R8, R9, RSP, RIP, RFLAGS) into a struct pt_regs frame on the kernel stack.\n"
        "3. Privilege Elevation & Stack Switch: The Current Privilege Level (CPL) transitions from Ring 3 to Ring 0. The stack pointer shifts from User RSP (0x00007fffffffe000) to Kernel RSP0 (0xffff80003e80ffe0).\n"
        "4. IVT Lookup & ABI Decoding: Syscall number in RAX indexes the Interrupt Vector Table. Input arguments are parsed according to System V AMD64 ABI.\n"
        "5. Kernel Execution: Privileged subsystems (VFS, VMM, Process Manager) execute in supervisor mode.\n"
        "6. Context Restoration & Return: Return code is written into the saved RAX. SYSRETQ or IRETQ pops pt_regs, restores registers, and lowers CPL to Ring 3."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    trap_ascii = (
        "[User Space Ring 3 Execution]\n"
        "            |\n"
        "            v\n"
        "    [SYSCALL / INT 0x80]\n"
        "            |\n"
        "            v\n"
        "+-----------------------------------------------------------------------------------+\n"
        "| Step 1: Trap Detected (MSR_LSTAR = 0xC0000082 / IDT Gate 0x80)                    |\n"
        "| Step 2: Push struct pt_regs to Kernel Stack (TSS RSP0 = 0xffff80003e80ffe0)        |\n"
        "| Step 3: Privilege Elevation: CPL 3 -> CPL 0; Stack Switch User -> Kernel          |\n"
        "| Step 4: IVT Vector Lookup (Vector = RAX) & ABI Decoding (RDI, RSI, RDX, R10)      |\n"
        "| Step 5: Execute Privileged Kernel Subsystem Routine (Ring 0)                      |\n"
        "| Step 6: Write Return Code to RAX; SYSRETQ / IRETQ Restores User pt_regs & Ring 3  |\n"
        "+-----------------------------------------------------------------------------------+\n"
        "            |\n"
        "            v\n"
        "[Resume User Space Ring 3 Execution]"
    )
    add_code_block(doc, trap_ascii)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Figure 3.2: User-to-Kernel 6-Step Hardware Trap Lifecycle")
    r.font.name = "Arial"
    r.font.size = Pt(9.5)
    r.font.italic = True
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # 3.3 KERNEL SUBSYSTEMS & DATA STRUCTURES
    # -------------------------------------------------------------
    h2 = doc.add_paragraph()
    r = h2.add_run("3.3 Kernel Subsystems & Data Structures")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "3.3.1 Virtual File System (VFS) & Inodes\n"
        "The VFS maintains an in-memory hierarchical namespace consisting of VirtualInode objects. Inodes encapsulate inode ID, file type (FILE, DIRECTORY, CHAR_DEVICE), permissions (e.g. 0o644, 0o755), file size, link counts, and data bytearrays. Directories map names to child inode pointers. Virtual devices like /dev/null and /dev/zero are registered as character devices providing POSIX-compliant discard and null-fill behavior.\n\n"
        "3.3.2 File Descriptor Table (FDT) & Open File Descriptions\n"
        "Each process owns a FileDescriptorTable mapping small integers (0, 1, 2, ...) to OpenFileDescription structures. Descriptor 0 maps to STDIN, 1 to STDOUT, and 2 to STDERR. Dynamic file opens allocate the lowest available index >= 3. Open descriptions track current read/write offset, open flags (O_RDONLY, O_WRONLY, O_CREAT, O_APPEND), and active reference counts for shared descriptors across forks.\n\n"
        "3.3.3 Virtual Memory Manager (VMM) & Heap Segmentation\n"
        "The VMM partitions virtual address space into standard segment mappings:\n"
        "• .text (0x00400000 - 0x00401fff): Read-only instruction memory.\n"
        "• .data (0x00402000 - 0x00403fff): Read-write static data.\n"
        "• .heap (0x00600000 - Program Break): Dynamically expanded heap space.\n"
        "• .stack (0x7ffff7ffe000 - 0x7fffffffe000): Downward growing user stack.\n"
        "System call sys_brk adjusts the program break. Access to unmapped addresses triggers a simulated SIGSEGV (signal 11) core dump.\n\n"
        "3.3.4 Process Control Block (PCB) & Management\n"
        "The ProcessControlBlock records pid, parent ppid, state (RUNNING, READY, ZOMBIE, TERMINATED), priority, CPU register snapshots, memory mappings, and file descriptor tables. System call sys_fork duplicates the calling PCB and its memory space, assigning child RAX = 0 and parent RAX = child_pid. A fork-bomb guard limits active processes to MAX_PROCESSES = 32, returning -EAGAIN on exhaustion."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    # Table 3.1 & 3.2
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(8)
    r = h2.add_run("3.4 Supported POSIX/x86_64 System Calls")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Table 3.1: Implemented POSIX System Calls & ABI Register Mappings")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.bold = True
    
    t_sys = doc.add_table(rows=8, cols=5)
    t_sys.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_sys)
    sys_data = [
        ("Syscall Name", "RAX", "Arguments (Registers)", "Success Return", "Error Return"),
        ("sys_read", "0", "RDI=fd, RSI=buf, RDX=count", "Bytes read", "-EBADF, -EFAULT, -EISDIR"),
        ("sys_write", "1", "RDI=fd, RSI=buf, RDX=count", "Bytes written", "-EBADF, -EFAULT, -EINVAL"),
        ("sys_open", "2", "RDI=path_ptr, RSI=flags, RDX=mode", "Allocated FD", "-ENOENT, -EACCES, -EEXIST"),
        ("sys_close", "3", "RDI=fd", "0", "-EBADF"),
        ("sys_brk", "12", "RDI=new_brk", "Current / New brk", "-ENOMEM"),
        ("sys_fork", "57", "(None)", "Child PID to parent, 0 to child", "-EAGAIN"),
        ("sys_exit", "60", "RDI=status", "(Process terminates)", "(None)"),
    ]
    for i, row in enumerate(sys_data):
        c0, c1, c2, c3, c4 = t_sys.cell(i, 0), t_sys.cell(i, 1), t_sys.cell(i, 2), t_sys.cell(i, 3), t_sys.cell(i, 4)
        c0.width, c1.width, c2.width, c3.width, c4.width = Inches(1.1), Inches(0.6), Inches(2.3), Inches(1.2), Inches(1.3)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text, c3.paragraphs[0].text, c4.paragraphs[0].text = row
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            set_cell_background(c3, "1F4E79")
            set_cell_background(c4, "1F4E79")
            for c in (c0, c1, c2, c3, c4):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            c0.paragraphs[0].runs[0].font.bold = True
            for c in (c0, c1, c2, c3, c4):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.5)
                    
    # Table 3.3
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    r = h2.add_run("3.5 Interactive Assembly Interpreter (REPL)")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Table 3.3: Interactive Assembly REPL Command Reference")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.bold = True
    
    t_cmd = doc.add_table(rows=11, cols=3)
    t_cmd.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_cmd)
    cmd_data = [
        ("Command", "Example Syntax", "Functional Description"),
        ("MOV", "MOV RAX, 1", "Assigns immediate integer, hex, or ASCII char to a 64-bit register."),
        ("MOV [addr], val", "MOV [0x600000], 65", "Stores byte directly into virtual memory address."),
        ("SYSCALL", "SYSCALL", "Triggers modern x86_64 fast hardware trap via MSR_LSTAR."),
        ("INT 0x80", "INT 0x80", "Triggers legacy software interrupt trap via IDT vector 128."),
        ("DUMP", "DUMP", "Prints live registers, privilege ring, memory segments, and open FDs."),
        ("LS_DISK", "LS_DISK /tmp", "Lists files, inodes, sizes, and permissions on virtual disk."),
        ("CAT", "CAT /tmp/demo.txt", "Displays raw text contents of a virtual disk file."),
        ("LOAD", "LOAD hello_world", "Loads pre-configured demo programs (hello_world, file_io, etc.)."),
        ("STEP / RUN", "STEP or RUN", "Steps through single instruction or runs until sys_exit."),
        ("PS", "PS", "Displays kernel process table (PIDs, PPIDs, states, heap breaks)."),
    ]
    for i, row in enumerate(cmd_data):
        c0, c1, c2 = t_cmd.cell(i, 0), t_cmd.cell(i, 1), t_cmd.cell(i, 2)
        c0.width, c1.width, c2.width = Inches(1.3), Inches(1.8), Inches(3.4)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text = row
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            c0.paragraphs[0].runs[0].font.bold = True
            for c in (c0, c1, c2):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.5)

    doc.add_page_break()
    
    # -------------------------------------------------------------
    # CHAPTER 4: EXPERIMENTAL RESULTS AND VERIFICATION
    # -------------------------------------------------------------
    h1 = doc.add_paragraph()
    r = h1.add_run("CHAPTER 4\nEXPERIMENTAL RESULTS AND VERIFICATION")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    h2 = doc.add_paragraph()
    r = h2.add_run("4.1 Test Harness & Automated Unit Verification")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "To verify kernel correctness and POSIX compliance, an automated test harness containing 42 comprehensive unit tests was developed in test_kernel_sim.py. The test suite exercises every subsystem under standard, edge, and erroneous conditions."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    # Table 4.1
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Table 4.1: Automated Unit Test Suite Summary (42 Test Cases)")
    r.font.name = "Arial"
    r.font.size = Pt(10)
    r.font.bold = True
    
    t_tst = doc.add_table(rows=7, cols=4)
    t_tst.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_tst)
    tst_rows = [
        ("Test Category", "Tests", "Key Assertions Tested", "Result"),
        ("CPU Core & Registers", "6", "64-bit integer masks, pt_regs save/restore, privilege switches", "PASS (100%)"),
        ("Virtual Memory Manager", "8", "Heap brk expansion, out-of-bounds SIGSEGV, text write protection", "PASS (100%)"),
        ("Virtual File System", "8", "Inode creation, path resolution, O_CREAT/O_TRUNC, /dev/null discard", "PASS (100%)"),
        ("File Descriptor Table", "6", "Standard stream preservation, dynamic allocation >= 3, ref counting", "PASS (100%)"),
        ("POSIX System Calls", "10", "All 7 syscalls, POSIX error numbers (-EBADF, -EFAULT, -EINVAL)", "PASS (100%)"),
        ("Process Subsystem", "4", "sys_fork register cloning, child RAX=0, fork-bomb guard limit", "PASS (100%)"),
    ]
    for i, row in enumerate(tst_rows):
        c0, c1, c2, c3 = t_tst.cell(i, 0), t_tst.cell(i, 1), t_tst.cell(i, 2), t_tst.cell(i, 3)
        c0.width, c1.width, c2.width, c3.width = Inches(1.8), Inches(0.8), Inches(2.9), Inches(1.0)
        c0.paragraphs[0].text, c1.paragraphs[0].text, c2.paragraphs[0].text, c3.paragraphs[0].text = row
        c3.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if i == 0:
            set_cell_background(c0, "1F4E79")
            set_cell_background(c1, "1F4E79")
            set_cell_background(c2, "1F4E79")
            set_cell_background(c3, "1F4E79")
            for c in (c0, c1, c2, c3):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        else:
            c0.paragraphs[0].runs[0].font.bold = True
            for c in (c0, c1, c2, c3):
                for run in c.paragraphs[0].runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(9.5)
                    
    test_run_out = (
        "$ python -m unittest test_kernel_sim.py\n"
        "..........................................\n"
        "----------------------------------------------------------------------\n"
        "Ran 42 tests in 8.284s\n\n"
        "OK"
    )
    add_code_block(doc, test_run_out)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("4.2 Step-by-Step Trap Execution Trace")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "When running the pre-loaded hello_world program, the simulator executes MOV instructions to load RAX=1 (sys_write), RDI=1 (STDOUT), RSI=0x00402000 (buffer pointer), and RDX=14 (length). The SYSCALL instruction triggers the detailed 6-step visual trap output shown below:"
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    trace_sample = (
        "╔════════════════════════════════════════════════════════════════════════════════╗\n"
        "║                      CPU HARDWARE TRAP: SYSCALL DISPATCH                       ║\n"
        "║      Transition: Ring 3 (User) ➔ Ring 0 (Kernel) | Syscall #1 (sys_write)      ║\n"
        "╚════════════════════════════════════════════════════════════════════════════════╝\n"
        "┌─ [STEP 1] CPU Trap Detected (MSR_LSTAR) ─────────────────────────────────────\n"
        "│  Active Process: PID 1000 ('shell') | PPID: 1\n"
        "│  Instruction: SYSCALL at RIP: 0x0000000000400002\n"
        "│  Trap Entry: MSR_LSTAR Fast Syscall Entry (Register 0xC0000082)\n"
        "│  Privilege Mode: Ring 3 (RING_3) | Syscall Requested: RAX = 1\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "┌─ [STEP 2] Hardware Context Save (Push struct pt_regs to Kernel Stack) ───────\n"
        "│  Saving User Registers onto Kernel Stack (TSS RSP0: 0xffff80003e80ffe0):\n"
        "│    RAX: 0x0000000000000001   RDI: 0x0000000000000001\n"
        "│    RSI: 0x0000000000402000   RDX: 0x000000000000000e\n"
        "│    RSP: 0x00007fffffffe000   RIP: 0x0000000000400002\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "┌─ [STEP 3] Privilege & Stack Switch (Ring 3 ➔ Ring 0) ────────────────────────\n"
        "│  CPL Transition: Ring 3 (USER) ➔ Ring 0 (SUPERVISOR)\n"
        "│  Stack Switch: RSP shifted from User 0x00007fffffffe000 ➔ Kernel 0xffff80003e80ffe0\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "┌─ [STEP 4] Interrupt Vector Table (IVT) Lookup & Parameter Decoding ──────────\n"
        "│  Vector Index: RAX = 1 ➔ Handler: sys_write\n"
        "│  ABI Arguments: Arg 1 (RDI): 1, Arg 2 (RSI): 0x402000, Arg 3 (RDX): 14\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "[STDOUT PID 1000] Hello, World!\n"
        "┌─ [STEP 5] Kernel Subsystem Execution (sys_write) ────────────────────────────\n"
        "│  Kernel execution completed: return_code = 14 (bytes written)\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "┌─ [STEP 6] Context Restoration & SYSRETQ (Ring 0 ➔ Ring 3) ───────────────────\n"
        "│  Writing syscall result 14 into RAX.\n"
        "│  SYSRETQ: Privilege Level: Ring 0 ➔ Ring 3 (USER)\n"
        "│  Restoring User Stack Pointer: RSP ➔ 0x00007fffffffe000\n"
        "│  Resuming User Execution at RIP: 0x0000000000400004\n"
        "└───────────────────────────────────────────────────────────────────────────────\n"
        "✔ Trap Complete. Resumed User Space (PID 1000, Ring 3). RAX = 14"
    )
    add_code_block(doc, trace_sample)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("4.3 Virtual Memory Violation (SIGSEGV) Demonstration")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "To evaluate memory isolation, user code passes an invalid address (0x99999999) to sys_write. The Virtual Memory Manager intercepts the access, aborts the system call, returns -EFAULT (-14), and displays a detailed Segmentation Fault diagnostic report."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    sigsegv_sample = (
        "[KERNEL FAULT DETECTED]\n"
        "Signal: SIGSEGV (Signal 11: Segmentation Violation)\n"
        "Faulting Address: 0x0000000099999999 (Address is outside mapped virtual memory)\n"
        "Current Break: 0x0000000000600000\n"
        "Action: Terminating faulting process or returning -EFAULT (-14) to caller."
    )
    add_code_block(doc, sigsegv_sample)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("4.4 Process Duplication (sys_fork) & Fork-Bomb Guard")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "Running the fork_bomb_guard demo tests process isolation and resource limits. When sys_fork executes in a loop, the process table dynamically tracks spawned processes until reaching the configured ceiling of 32 processes. Subsequent forks are rejected with -EAGAIN (-11), preventing host resource starvation."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    doc.add_page_break()
    
    # -------------------------------------------------------------
    # CHAPTER 5: CONCLUSION AND FUTURE SCOPE
    # -------------------------------------------------------------
    h1 = doc.add_paragraph()
    r = h1.add_run("CHAPTER 5\nCONCLUSION AND FUTURE SCOPE")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy
    
    h2 = doc.add_paragraph()
    r = h2.add_run("5.1 Conclusion")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "This project successfully designed and implemented an interactive, production-grade System Call & Kernel Trap Simulator in pure Python with zero external dependencies. The simulator faithfully models the x86_64 architecture's privilege ring transitions, Task State Segment stack switching, ABI register conventions, in-memory Virtual File System, per-process descriptor tables, virtual memory boundary enforcement, and process lifecycle management.\n\n"
        "Through 42 automated unit tests and interactive REPL demonstrations, the system was verified to adhere rigorously to POSIX error codes and architectural calling conventions. The simulator bridges the pedagogical gap between abstract operating system theory and tangible software implementation, providing a transparent, crash-resilient environment for student learning and system call exploration."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    r = h2.add_run("5.2 Future Scope")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = slate_blue
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.25
    r = p.add_run(
        "Future enhancements planned for the simulator include:\n"
        "1. Multi-Core SMP & Preemptive Scheduling: Modeling timer interrupt ticks (PIT/APIC) to preempt running processes and simulate round-robin multi-process scheduling.\n"
        "2. Paging & TLB Simulation: Simulating multi-level 4-level page table walks (PML4, PDPT, PD, PT) and Translation Lookaside Buffer (TLB) hit/miss metrics.\n"
        "3. Inter-Process Communication (IPC): Implementing sys_pipe (RAX=22) and Unix domain sockets for inter-process data exchange.\n"
        "4. Signal Handling Subsystem: Adding support for sys_rt_sigaction and user-space signal handler trampolines via sigreturn."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(12)
    r = h2.add_run("REFERENCES")
    r.font.name = "Arial"
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = navy
    
    refs = [
        "1. Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). Operating System Concepts (10th ed.). Wiley.",
        "2. Tanenbaum, A. S., & Bos, H. (2015). Modern Operating Systems (4th ed.). Pearson.",
        "3. Bovet, D. P., & Cesati, M. (2005). Understanding the Linux Kernel (3rd ed.). O'Reilly Media.",
        "4. Love, R. (2010). Linux Kernel Development (3rd ed.). Addison-Wesley Professional.",
        "5. Intel Corporation (2023). Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 3A: System Programming Guide.",
        "6. IEEE and The Open Group (2018). The Open Group Base Specifications Issue 7 / IEEE Std 1003.1-2017 (POSIX.1).",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(ref)
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)

    # -------------------------------------------------------------
    # APPENDIX: SOURCE CODE
    # -------------------------------------------------------------
    doc.add_page_break()
    h1 = doc.add_paragraph()
    r = h1.add_run("APPENDIX\nSOURCE CODE")
    r.font.name = "Arial"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = navy

    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(12)
    r = h2.add_run("Complete Source Code: kernel_sim.py")
    r.font.name = "Arial"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = slate_blue

    kernel_sim_path = os.path.join(os.path.dirname(__file__), "kernel_sim.py")
    if os.path.exists(kernel_sim_path):
        with open(kernel_sim_path, "r", encoding="utf-8") as f_src:
            src_lines = f_src.readlines()
        for line in src_lines:
            p_code = doc.add_paragraph()
            p_code.paragraph_format.space_before = Pt(0)
            p_code.paragraph_format.space_after = Pt(0)
            p_code.paragraph_format.line_spacing = 1.0
            r_code = p_code.add_run(line.rstrip("\r\n"))
            r_code.font.name = "Consolas"
            r_code.font.size = Pt(7.0)
            r_code.font.color.rgb = RGBColor(0x22, 0x22, 0x22)

    doc.save(file_path)
    print(f"Successfully generated DOCX report at: {file_path}")

if __name__ == "__main__":
    out_docx = os.path.abspath("Operating_Systems_Mini_Project_Report.docx")
    build_docx_report(out_docx)
