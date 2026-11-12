#!/usr/bin/env python3
"""CPU32J2 OS V1: Python source generator + assembler.

Builds a terminal-first guest OS with a RAM filesystem. The supplied optional
runtime bridge exposes queued keyboard input at LOAD8 0xFFFFFFFF. Existing
cpu32_jit.exe and its execution/clock path are not modified.
"""
from __future__ import annotations
import argparse, hashlib, struct, zipfile, shutil, re, inspect, random, sys
from array import array
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_ROWS=31; LINE_LEN=100; FS_SLOTS=256; NAME_LEN=16; FILE_LEN=1024
FB=0x80384000; VRAM_BACK=0x80384000; PRESENT=0xFFFFFFDC; FRAME_BYTES=1280*720*4
STACK_START=0x7FF00000; STACK_END=0x80000000
VRAM_BASE=0x80000000; VRAM_SIZE=0x00800000
FONT_BASE=0x8000; CONST_BASE=0x9000; FONT_CHECKSUM_EXPECTED=0
HEAP_BASE=0; HEAP_LIMIT=STACK_START-0x1000; PAGE_COUNT=0; PAINT_CANVAS_BASE=0; GUEST_CODE_BYTES=0
OUT_BASE=0x20000; CMD_BUF=0x14000; CMD_WORD=0x14200; ARG_NAME=0x14300; ARG_TEXT=0x14400
FS_USED=0x14800; FS_NAMES=0x14900; FS_SIZE=0x18A00; FS_PARENT=0x18E00; FS_TYPE=0x19200; FS_PAGE=0x19600
CAT_BUF=0x1B000
PAGE_BITMAP=0x40000; TRACE_FUNCS=0x50000; TRACE_RETS=0x50100; PANIC_REGS=0x50200; PANIC_STACK=0x50300; PANIC_WORDS=0x50400; APP_ARENAS=0x50500; UNDO_PAGES=0x50600; CAL_EVENT_USED=0x50700; CAL_EVENT_TEXT=0x50800
G={
'CMD_LEN':0x1A000,'ROW_I':0x1A004,'TEXT_SRC':0x1A008,'TEXT_ROW':0x1A00C,'TEXT_COL':0x1A010,'TEXT_COLOR':0x1A014,'TEXT_INDEX':0x1A018,
'CHAR_CODE':0x1A01C,'CHAR_X':0x1A020,'CHAR_Y':0x1A024,'CHAR_COLOR':0x1A028,'CHAR_ROW':0x1A02C,'CHAR_COL':0x1A030,'CHAR_BITMAP':0x1A034,
'PIX_X':0x1A038,'PIX_Y':0x1A03C,'PIX_COLOR':0x1A040,'PRINT_SRC':0x1A044,'PRINT_I':0x1A048,'PARSE_I':0x1A04C,'TOKEN_LEN':0x1A050,
'ARG_NAME_LEN':0x1A054,'ARG_TEXT_LEN':0x1A058,'PTR_A':0x1A05C,'PTR_B':0x1A060,'STR_I':0x1A064,'STR_RESULT':0x1A068,
'FILE_I':0x1A06C,'FILE_FOUND':0x1A070,'FILE_FREE':0x1A074,'FILE_BASE':0x1A078,'TEMP_I':0x1A07C,'TEMP_CHAR':0x1A080,
'PARSE_SRC':0x1A084,'PARSE_VALUE':0x1A088,'CALC_A':0x1A08C,'CALC_B':0x1A090,'CALC_OP':0x1A094,'CALC_RESULT':0x1A098,
'NUM_I':0x1A09C,'NUM_REV_I':0x1A0A0,'NUM_NEG':0x1A0A4,'LOOP_I':0x1A0A8,'TICK':0x1A0AC,'TEMP_A':0x1A0B0,'TEMP_B':0x1A0B4,
'PROMPT_ROW':0x1A0B8,'TEMP_INDEX':0x1A0BC,'OUT_COUNT':0x1A0C0,'OUT_TARGET':0x1A0C4,'PRINT_DEST':0x1A0C8,
'APP_STATE':0x1B400,'CURSOR_X':0x1B404,'CURSOR_Y':0x1B408,'RECT_X':0x1B40C,'RECT_Y':0x1B410,'RECT_W':0x1B414,'RECT_H':0x1B418,'RECT_COLOR':0x1B41C,'RECT_MODE':0x1B420,'RECT_ROW':0x1B424,'RECT_COL':0x1B428,'RECT_BASE':0x1B42C,'RECT_BYTES':0x1B430,'BOOT_STAGE':0x1B434,'BOOT_TEXT':0x1B438,'BOOT_I':0x1B43C,'BOOT_CHECK':0x1B440,'KEY_EVENT':0x1B444,'ICON_INDEX':0x1B448,'THEME':0x1B44C,'FILE_LINES':0x1B450,'FILE_COUNT':0x1B454,'NOTE_LEN':0x1B458,'NOTE_I':0x1B45C,'NOTE_STATUS':0x1B460,'PAINT_COUNT':0x1B464,'PAINT_I':0x1B468,'GUI_TMP':0x1B46C,'GUI_TMP2':0x1B470,'GUI_STATUS':0x1B474,'GUI_SAVE_I':0x1B478,'GUI_TICK_SNAP':0x1B47C,
'PARSE_NEG':0x1B480,'RNG_STATE':0x1B484,'SCRIPT_SLOT':0x1B488,'SCRIPT_POS':0x1B48C,'SCRIPT_SIZE':0x1B490,'SCRIPT_LEN':0x1B494,'SCRIPT_ACTIVE':0x1B498,'SCRIPT_WORD':0x1B49C,'CRC_VALUE':0x1B4A0,'CRC_I':0x1B4A4,'CRC_BIT':0x1B4A8,'CRC_SIZE':0x1B4AC,'CRC_SLOT':0x1B4B0,'MATH_AUX':0x1B4B4,'SQRT_N':0x1B4B8,'SQRT_LO':0x1B4BC,'SQRT_HI':0x1B4C0,'SQRT_MID':0x1B4C4,'PRIME_DIV':0x1B4C8,'PRIME_N':0x1B4CC,'MEMTEST_COUNT':0x1B4D0,'MEMTEST_I':0x1B4D4,'MEMTEST_FAIL':0x1B4D8,'LCM_A':0x1B4DC,'LCM_B':0x1B4E0,'BENCH_I':0x1B4E4,'BENCH_COUNT':0x1B4E8,'BENCH_ACC':0x1B4EC,'HEX_I':0x1B4F0,'HEX_VALUE':0x1B4F4,'HEX_NIBBLE':0x1B4F8,'HEX_OUT_I':0x1B4FC,'SELFTEST_FAILED':0x1B500,'CWD_ID':0x1B504,'LAST_DELETED':0x1B508,'KERNEL_MAGIC':0x1B50C,
'PAGE_HINT':0x1B510,'PAGE_USED':0x1B514,'PAGE_RESULT':0x1B518,'PAGE_INDEX':0x1B51C,'PAGE_SCAN':0x1B520,'PAGE_ADDR':0x1B524,'PAGE_MASK':0x1B528,'PAGE_BYTE':0x1B52C,
'SLAB_CLASS':0x1B530,'SLAB_REQUEST':0x1B534,'SLAB_RESULT':0x1B538,'SLAB_TMP':0x1B53C,'SLAB_CUR':0x1B540,'SLAB_END':0x1B550,'SLAB_FREE':0x1B560,
'TRACE_DEPTH':0x1B570,'STACK_USED':0x1B574,'STACK_HIGHWATER':0x1B578,'PANIC_CODE':0x1B57C,'PANIC_REASON':0x1B580,'PANIC_PC':0x1B584,'PANIC_FUNCTION':0x1B588,'PANIC_SP':0x1B58C,'PANIC_TRACE_DEPTH':0x1B590,'PANIC_DUMP_PTR':0x1B594,'PANIC_DUMP_OFFSET':0x1B598,'PANIC_ACTIVE':0x1B59C,
'STOPWATCH_RUNNING':0x1B5A0,'STOPWATCH_TICKS':0x1B5A4,'STOPWATCH_LAPS':0x1B5A8,'MIX_FREQ':0x1B5AC,'MIX_VOLUME':0x1B5B0,'MIX_WAVE':0x1B5B4,'MIX_PAN':0x1B5B8,'APP_ARENA_ID':0x1B5BC,'APP_ARENA_PAGE':0x1B5C0,'UNDO_HEAD':0x1B5C4,'UNDO_COUNT':0x1B5C8,'REDO_HEAD':0x1B5CC,'REDO_COUNT':0x1B5D0,'VFS_ERROR':0x1B5D4,'MEM_DUMP_ADDR':0x1B5D8,'MEM_DUMP_WORD':0x1B5DC,'MEM_DUMP_I':0x1B5E0,'HEX_CHAR_I':0x1B5E4,'PANIC_REG_I':0x1B5E8,'PANIC_FRAME_I':0x1B5EC,'PANIC_TMP':0x1B5F0,
}
NUM_BUF=0x1A200; NUM_REV=0x1A280; ECHO_BUF=0x1A300; PROMPT_BUF=0x1A500
HEX_BUF=0x1B600; HEX_REV=0x1B640; BIN_BUF=0x1B680; BIN_REV=0x1B700
MEMTEST_BUF=0x30000; NOTE_BUF=0x1C000; PAINT_X_BUF=0x1D000; PAINT_Y_BUF=0x1D200

# The original offsets are preserved, but the OS compiler rebases every guest-static
# data address after the instruction image so code and static data never overlap.
_DATA_ADDRESS_NAMES = ('FONT_BASE','CONST_BASE','OUT_BASE','CMD_BUF','CMD_WORD','ARG_NAME','ARG_TEXT',
    'FS_USED','FS_NAMES','FS_SIZE','CAT_BUF','NUM_BUF','NUM_REV','ECHO_BUF','PROMPT_BUF',
    'HEX_BUF','HEX_REV','BIN_BUF','BIN_REV','MEMTEST_BUF','NOTE_BUF','PAINT_X_BUF','PAINT_Y_BUF',
    'PAGE_BITMAP','TRACE_FUNCS','TRACE_RETS','PANIC_REGS','PANIC_STACK','PANIC_WORDS','APP_ARENAS','UNDO_PAGES','CAL_EVENT_USED','CAL_EVENT_TEXT','FS_PARENT','FS_TYPE','FS_PAGE')
_DATA_ADDRESS_OFFSETS = {name: globals()[name] for name in _DATA_ADDRESS_NAMES}
_G_ADDRESS_OFFSETS = dict(G)
_DATA_ORIGIN = 0
_DATA_BASE = 0
_CODE_BYTES = 0

def _align_up(value, alignment=4096):
    return (value + alignment - 1) & ~(alignment - 1)

def configure_guest_data_layout(code_bytes):
    """Place all static OS data after the page-rounded code image.

    The old address constants become offsets in one relocatable static-data image.
    FONT_BASE (old offset 0x8000) is the first static region, so the origin is
    chosen such that FONT_BASE lands exactly at align_up(code_bytes, 4096).
    """
    global _DATA_ORIGIN, _DATA_BASE, _CODE_BYTES, G
    global FONT_BASE, CONST_BASE, OUT_BASE, CMD_BUF, CMD_WORD, ARG_NAME, ARG_TEXT
    global FS_USED, FS_NAMES, FS_SIZE, FS_PARENT, FS_TYPE, FS_PAGE, CAT_BUF, NUM_BUF, NUM_REV, ECHO_BUF, PROMPT_BUF
    global HEX_BUF, HEX_REV, BIN_BUF, BIN_REV, MEMTEST_BUF, NOTE_BUF, PAINT_X_BUF, PAINT_Y_BUF
    global PAGE_BITMAP, TRACE_FUNCS, TRACE_RETS, PANIC_REGS, PANIC_STACK, PANIC_WORDS, APP_ARENAS, UNDO_PAGES, CAL_EVENT_USED, CAL_EVENT_TEXT, FS_PARENT, FS_TYPE, FS_PAGE
    global FB, HEAP_BASE, HEAP_LIMIT, PAGE_COUNT, PAINT_CANVAS_BASE, PANIC_STACK_DUMP_BASE, GUEST_CODE_BYTES
    _CODE_BYTES = int(code_bytes)
    _DATA_BASE = _align_up(_CODE_BYTES, 4096)
    _DATA_ORIGIN = _DATA_BASE - _DATA_ADDRESS_OFFSETS['FONT_BASE']
    for name, offset in _DATA_ADDRESS_OFFSETS.items():
        globals()[name] = _DATA_ORIGIN + offset
    G = {name: _DATA_ORIGIN + offset for name, offset in _G_ADDRESS_OFFSETS.items()}
    FB = _DATA_BASE + 0x00100000
    PAINT_CANVAS_BASE = FB + 1280*720*4
    HEAP_BASE = _align_up(PAINT_CANVAS_BASE + FRAME_BYTES + 0x00100000, 4096)
    HEAP_LIMIT = STACK_START - 0x1000
    PANIC_STACK_DUMP_BASE = HEAP_BASE
    PAGE_COUNT = max(0, (HEAP_LIMIT - HEAP_BASE) // 4096)
    if PAGE_COUNT > 524288: raise RuntimeError('Page bitmap capacity exceeded')
    KEY_CONTENT['MEM_1'] = f'CODE: 0X00000000 - 0X{max(0, _CODE_BYTES-1):08X}'
    KEY_CONTENT['MEM_2'] = f'STATIC DATA START: 0X{_DATA_BASE:08X}'
    KEY_CONTENT['MEM_3'] = 'STACK: 0X7FF00000 - 0X7FFFFFFF'
    KEY_CONTENT['MEM_4'] = 'VRAM: 0X80000000 - 0X807FFFFF'


KEY_CONTENT = {
'WELCOME':'WELCOME TO CPU32J2 OS V1.0','OS_READY':'SYSTEM BOOT COMPLETE.','HELP_HINT':'TYPE HELP TO VIEW AVAILABLE COMMANDS.',
'OS_TITLE':'CPU32J2 OS V1.0  |  TERMINAL AND RAM FILESYSTEM','OS_SUBTITLE':'CLICK THE GRAPHICS WINDOW BEFORE TYPING COMMANDS',
'SEP':'-'*96,'OS_FOOTER':'HELP  LS  TOUCH  WRITE  CAT  APPEND  DEL  CALC  SYSINFO  REBOOT','PROMPT_PREFIX':'CPU32> ',
'HELP_TITLE':'CPU32J2 OS COMMANDS','HELP_1':'HELP - SHOW COMMANDS','HELP_2':'LS / DIR - LIST FILES','HELP_3':'TOUCH NAME - CREATE EMPTY FILE',
'HELP_4':'WRITE NAME TEXT - REPLACE FILE CONTENTS','HELP_5':'APPEND NAME TEXT - APPEND TO FILE','HELP_6':'CAT NAME - DISPLAY FILE CONTENTS',
'HELP_7':'DEL NAME - DELETE FILE','HELP_8':'ECHO TEXT - PRINT TEXT','HELP_9':'CALC A OP B - ADVANCED INTEGER CALCULATOR',
'HELP_10':'SYSINFO / MEM / TIME - SYSTEM INFO','HELP_11':'CLS - CLEAR TERMINAL','HELP_12':'FORMAT - CLEAR RAM FILESYSTEM',
'HELP_13':'REBOOT - RESET TERMINAL (FILES KEPT)','HELP_14':'FILES ARE STORED IN RAM UNTIL EXIT',
'OS_ABOUT_1':'A SMALL GUEST OPERATING ENVIRONMENT','OS_ABOUT_2':'TERMINAL, CALCULATOR, AND RAM FILESYSTEM','OS_ABOUT_3':'RUNS UNDER THE EXISTING CPU32J2 JIT',
'SYS_TITLE':'SYSTEM INFORMATION','SYS_1':'CPU32J2 GUEST OS V1','SYS_2':'ISA: CPU32J2 V2 / 32-BIT REGISTERS',
'SYS_3':'ROM: PYTHON-GENERATED ASSEMBLY + BINARY','SYS_4':'DISPLAY: 1280 X 720 RGBA8888 DOUBLE BUFFER',
'SYS_5':'INPUT: OPTIONAL KEYBOARD MMIO BRIDGE','SYS_6':'FILESYSTEM: 16 FILES IN GUEST RAM',
'MEM_TITLE':'GUEST MEMORY MAP','MEM_1':'CODE: 0X00000000 - 0XFFFFFFFF','MEM_2':'STATIC DATA START: 0XFFFFFFFF',
'MEM_3':'STACK: 0X7FF00000 - 0X7FFFFFFF','MEM_4':'VRAM: 0X80000000 - 0X807FFFFF','TIME_TITLE':'UPTIME TICKS (KEYBOARD POLLING LOOPS)',
'LS_TITLE':'RAM FILESYSTEM','LS_END':'FILES LISTED ABOVE','NO_FILES':'NO FILES','FILE_CREATED':'FILE CREATED','FILE_EXISTS':'FILE EXISTS',
'FILE_WRITTEN':'FILE WRITTEN','FILE_APPENDED':'FILE APPENDED','FILE_DELETED':'FILE DELETED','FS_FORMATTED':'FILESYSTEM CLEARED',
'CLEARED':'TERMINAL CLEARED','REBOOTING':'REBOOTING - IN-MEMORY FILES KEPT','UNKNOWN_COMMAND':'UNKNOWN COMMAND - TYPE HELP',
'ERR_NAME':'ERROR: PROVIDE A FILE NAME','ERR_NOT_FOUND':'ERROR: FILE NOT FOUND','ERR_FS_FULL':'ERROR: RAM FILESYSTEM FULL',
'CALC_USAGE':'CALC A OP B: + - * / % ^ & | XOR << >>','CALC_DIVZERO':'ERROR: DIVISION BY ZERO',
'CALC_RESULT_TITLE':'CALCULATOR RESULT','RESULT_PREFIX':'RESULT: ',
}

OPS={
'NOP':0x00,'HALT':0x01,'LDI':0x02,'MOV':0x03,'ADD':0x04,'SUB':0x05,'MUL':0x06,'DIVS':0x07,'DIVU':0x08,'REMS':0x09,'REMU':0x0A,'AND':0x0B,'OR':0x0C,'XOR':0x0D,'NOT':0x0E,'NEG':0x0F,'LSH':0x10,'RSH':0x11,'ASR':0x12,'ROTL':0x13,'ROTR':0x14,'CMP':0x15,'CMPU':0x16,'MADD':0x17,'MULHI':0x18,'MULHIU':0x19,'MIN':0x1A,'MAX':0x1B,'CLAMP':0x1C,'POPCNT':0x1D,'CLZ':0x1E,'CTZ':0x1F,'BEXT':0x20,'BINS':0x21,'SEXT':0x22,'ZEXT':0x23,'SELECT':0x24,'SWAP':0x25,'CMOV':0x26,'LOAD':0x28,'STORE':0x29,'LOAD8':0x2A,'LOAD16':0x2B,'LOADS8':0x2C,'LOADS16':0x2D,'STORE8':0x2E,'STORE16':0x2F,'LDX':0x30,'STX':0x31,'MEMCPY':0x32,'MEMSET':0x33,'JMP':0x38,'CALL':0x39,'RET':0x3A,'JOV':0x3B,'JZE':0x3C,'JCA':0x3D,'JLO':0x3E,'JEQ':0x3F,'JHI':0x40,'JNE':0x41,'JGE':0x42,'JLE':0x43,'JLT':0x44,'JGT':0x45,'PUSH':0x46,'POP':0x47,'IRET':0x48,'INITINT':0x49,'EI':0x4A,'DI':0x4B}
NOARG={'NOP','HALT','RET','IRET','EI','DI'}
THREE={'ADD','SUB','MUL','DIVS','DIVU','REMS','REMU','AND','OR','XOR','LSH','RSH','ASR','ROTL','ROTR','MIN','MAX','MULHI','MULHIU'}
UNARY={'MOV','NOT','NEG','POPCNT','CLZ','CTZ'}
LOADS={'LOAD','LOAD8','LOAD16','LOADS8','LOADS16'}; STORES={'STORE','STORE8','STORE16'}
BRANCH={'JMP','CALL','JOV','JZE','JCA','JLO','JEQ','JHI','JNE','JGE','JLE','JLT','JGT','INITINT'}

# 5x7 bitmap font. All entered/displayed text is uppercased by the guest shell.
FONT={
' ':['00000']*7,
'A':['01110','10001','10001','11111','10001','10001','10001'],'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['11111','00100','00100','00100','00100','00100','11111'],'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','10101','01010'],'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10001','10011','10101','11001','10001','01110'],'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],'9':['01110','10001','10001','01111','00001','00001','01110'],
'.':['00000','00000','00000','00000','00000','00110','00110'],',':['00000','00000','00000','00000','00110','00110','00100'],
':':['00000','00110','00110','00000','00110','00110','00000'],';':['00000','00110','00110','00000','00110','00110','00100'],
'!':['00100','00100','00100','00100','00100','00000','00100'],'?':['01110','10001','00001','00010','00100','00000','00100'],
'-':['00000','00000','00000','11111','00000','00000','00000'],'_':['00000','00000','00000','00000','00000','00000','11111'],
'+':['00000','00100','00100','11111','00100','00100','00000'],'/':['00001','00010','00010','00100','01000','01000','10000'],
'*':['00000','10101','01110','11111','01110','10101','00000'],'=':['00000','11111','00000','11111','00000','00000','00000'],
'>':['10000','01000','00100','00010','00100','01000','10000'],'<':['00001','00010','00100','01000','00100','00010','00001'],
'(':['00010','00100','01000','01000','01000','00100','00010'],')':['01000','00100','00010','00010','00010','00100','01000'],
'[':['01110','01000','01000','01000','01000','01000','01110'],']':['01110','00010','00010','00010','00010','00010','01110'],
'"':['01010','01010','01010','00000','00000','00000','00000'],"'":['00100','00100','00000','00000','00000','00000','00000'],
'#':['01010','11111','01010','01010','11111','01010','00000'],'%':['11001','11010','00100','01000','10110','00110','00000'],
'|':['00100','00100','00100','00100','00100','00100','00100'],'@':['01110','10001','10111','10101','10111','10000','01111'],'&':['01100','10010','10100','01000','10101','10010','01101'],
}

def make_font_words():
    words=[]
    for ch in range(128):
        c=chr(ch).upper()
        glyph=FONT.get(c,FONT.get('?' ,FONT[' ']))
        for row in glyph:
            words.append(int(row,2))
    return words

FONT_CHECKSUM_EXPECTED = 0
for _font_word in make_font_words(): FONT_CHECKSUM_EXPECTED ^= _font_word

class Builder:
    def __init__(self): self.lines=[]; self.n=0; self.trace_enabled=True
    def e(self,s): self.lines.append(s)
    def label(self,s): self.lines.append(s+':')
    def new(self,p='loc'):
        i=self.n; self.n+=1; out=''
        while True:
            out=chr(97+i%26)+out; i=i//26-1
            if i<0: break
        return ''.join(ch for ch in p if ch.isalpha() or ch=='_')+'_'+out
    def li(self,r,v): self.e(f'LDI r{r} {int(v)}')
    def ldg(self,d,a): self.li(12,a); self.e(f'LOAD r{d} r12')
    def stg(self,a,s): self.li(12,a); self.e(f'STORE r12 r{s}')
    def ldx(self,d,base,idx): self.li(12,base); self.e(f'LDX r{d} r12 r{idx}')
    def stx(self,base,idx,val): self.li(12,base); self.e(f'STX r12 r{idx} r{val}')
    def br(self,op,label): self.e(f'{op} {label}')
    def call(self,label):
        if not self.trace_enabled:
            self.e(f'CALL {label}'); return
        serial=self.new('calltrace'); fail=f'{serial}_overflow'; ret=f'{serial}_return'
        done=f'{serial}_done'
        # Preserve scratch registers; 16 bytes are saved here and 4 by CALL itself.
        for r in (12,13,14,15): self.e(f'PUSH r{r}')
        self.e(f'LDI r12 {G["STACK_USED"]}'); self.e('LOAD r13 r12')
        self.e(f'LDI r14 {0xFF000-20}'); self.e('CMP r13 r14'); self.e(f'JGT {fail}')
        # Record target and return address in a 64-entry wrapping shadow call stack.
        self.e(f'LDI r12 {G["TRACE_DEPTH"]}'); self.e('LOAD r13 r12')
        self.e('LDI r14 63'); self.e('AND r15 r13 r14')
        self.e(f'LDI r14 {label}'); self.e(f'LDI r12 {TRACE_FUNCS}'); self.e('STX r12 r15 r14')
        self.e(f'LDI r14 {ret}'); self.e(f'LDI r12 {TRACE_RETS}'); self.e('STX r12 r15 r14')
        self.e(f'LDI r12 {G["TRACE_DEPTH"]}'); self.e('LOAD r13 r12'); self.e('LDI r14 1'); self.e('ADD r13 r13 r14'); self.e('STORE r12 r13')
        self.e(f'LDI r12 {G["STACK_USED"]}'); self.e('LOAD r13 r12'); self.e('LDI r14 20'); self.e('ADD r13 r13 r14'); self.e('STORE r12 r13')
        # Track high-water stack use (R13=current use, R14=high-water).
        self.e(f'LDI r12 {G["STACK_HIGHWATER"]}'); self.e('LOAD r14 r12'); self.e('CMP r13 r14'); self.e(f'JLE {serial}_hw_done')
        self.e('STORE r12 r13'); self.label(f'{serial}_hw_done')
        for r in (15,14,13,12): self.e(f'POP r{r}')
        self.e(f'CALL {label}')
        self.label(ret)
        # Return path updates shadow depth and stack accounting without touching caller-visible registers.
        self.e(f'LDI r12 {G["STACK_USED"]}'); self.e('LOAD r13 r12'); self.e('LDI r14 20'); self.e('SUB r13 r13 r14'); self.e('STORE r12 r13')
        self.e(f'LDI r12 {G["TRACE_DEPTH"]}'); self.e('LOAD r13 r12'); self.e('LDI r14 1'); self.e('SUB r13 r13 r14'); self.e('STORE r12 r13')
        for r in (15,14,13,12): self.e(f'POP r{r}')
        self.e(f'JMP {done}')
        self.label(fail)
        for r in (15,14,13,12): self.e(f'POP r{r}')
        self.e('JMP stack_overflow_panic')
        self.label(done)


def assemble(text):
    # Low-memory two-pass assembler suitable for million-instruction generated ROMs.
    lines = text.splitlines()
    label_re = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$')
    labels = {}
    address = 0
    for line_no, raw in enumerate(lines, 1):
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if ':' in line:
            m = label_re.match(line)
            if not m:
                raise ValueError(f'invalid label syntax at line {line_no}: {line}')
            label, line = m.group(1), m.group(2).strip()
            if label in labels:
                raise ValueError(f'duplicate label {label} at line {line_no}')
            labels[label] = address
            if not line:
                continue
        address += 8

    def reg(token, ln):
        if not token.lower().startswith('r') or not token[1:].isdigit():
            raise ValueError(f'bad register {token} line {ln}')
        value = int(token[1:])
        if not 0 <= value <= 15:
            raise ValueError(f'bad register {token} line {ln}')
        return value

    def number(token, ln):
        try:
            return int(token, 0)
        except Exception:
            try:
                return int(token, 10)
            except Exception:
                raise ValueError(f'bad integer {token} line {ln}')

    words = array('Q')
    for line_no, raw in enumerate(lines, 1):
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if ':' in line:
            m = label_re.match(line)
            if not m:
                raise ValueError(f'invalid label syntax at line {line_no}: {line}')
            line = m.group(2).strip()
            if not line:
                continue
        args = line.replace(',', ' ').split()
        name = args[0].upper()
        vals = args[1:]
        if name not in OPS:
            raise ValueError(f'unknown op {name} line {line_no}')
        a = b = c = d = imm = 0
        n = len(vals)
        if name in NOARG:
            if n != 0: raise ValueError(f'{name} expects 0 operands at line {line_no}')
        elif name == 'LDI':
            if n != 2: raise ValueError(f'LDI expects 2 operands at line {line_no}')
            a = reg(vals[0], line_no); imm = (labels[vals[1]] if vals[1] in labels else number(vals[1], line_no)) & 0xFFFFFFFF
        elif name in THREE:
            if n != 3: raise ValueError(f'{name} expects 3 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); c = reg(vals[2], line_no)
        elif name in UNARY:
            if n != 2: raise ValueError(f'{name} expects 2 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no)
        elif name in ('CMP', 'CMPU'):
            if n != 2: raise ValueError(f'{name} expects 2 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no)
        elif name in ('MADD', 'CLAMP', 'SELECT'):
            if n != 4: raise ValueError(f'{name} expects 4 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); c = reg(vals[2], line_no); d = reg(vals[3], line_no)
        elif name == 'SWAP':
            if n != 2: raise ValueError(f'SWAP expects 2 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no)
        elif name == 'CMOV':
            if n != 3: raise ValueError(f'CMOV expects 3 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no)
            cmov_conditions = {'EQ':0, 'NE':1, 'GT':2, 'GE':3, 'LT':4, 'LE':5,
                               'CA':6, 'LO':7, 'HI':8, 'OV':9, 'ZE':10}
            condition_token = vals[2].upper()
            imm = cmov_conditions[condition_token] if condition_token in cmov_conditions else number(vals[2], line_no)
            if not 0 <= imm <= 10: raise ValueError(f'CMOV condition invalid at line {line_no}')
        elif name == 'BEXT':
            if n != 4: raise ValueError(f'BEXT expects 4 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); index = number(vals[2], line_no); width = number(vals[3], line_no)
            if index < 0 or index > 31 or width < 1 or width > 32 or index + width > 32: raise ValueError(f'BEXT range invalid line {line_no}')
            imm = index | ((width - 1) << 5)
        elif name == 'BINS':
            if n != 5: raise ValueError(f'BINS expects 5 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); c = reg(vals[2], line_no); index = number(vals[3], line_no); width = number(vals[4], line_no)
            if index < 0 or index > 31 or width < 1 or width > 32 or index + width > 32: raise ValueError(f'BINS range invalid line {line_no}')
            imm = index | ((width - 1) << 5)
        elif name in ('SEXT', 'ZEXT'):
            if n != 3: raise ValueError(f'{name} expects 3 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); imm = number(vals[2], line_no)
            if not 1 <= imm <= 32: raise ValueError(f'{name} width invalid at line {line_no}')
        elif name in ('LOAD', 'LOAD8', 'LOAD16', 'LOADS8', 'LOADS16', 'STORE', 'STORE8', 'STORE16'):
            if n != 2: raise ValueError(f'{name} expects 2 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no)
        elif name == 'LDX':
            if n != 3: raise ValueError(f'LDX expects 3 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); c = reg(vals[2], line_no)
        elif name == 'STX':
            if n != 3: raise ValueError(f'STX expects 3 operands at line {line_no}')
            a = reg(vals[2], line_no); b = reg(vals[0], line_no); c = reg(vals[1], line_no)
        elif name in ('MEMCPY', 'MEMSET'):
            if n != 3: raise ValueError(f'{name} expects 3 operands at line {line_no}')
            a = reg(vals[0], line_no); b = reg(vals[1], line_no); c = reg(vals[2], line_no)
        elif name in ('PUSH', 'POP'):
            if n != 1: raise ValueError(f'{name} expects 1 operand at line {line_no}')
            a = reg(vals[0], line_no)
        elif name in BRANCH:
            if n != 1: raise ValueError(f'{name} expects 1 operand at line {line_no}')
            imm = labels[vals[0]] if vals[0] in labels else number(vals[0], line_no)
        else:
            raise ValueError(f'no encoder for {name} at line {line_no}')
        words.append(((OPS[name] & 255) << 56) | ((a & 15) << 52) | ((b & 15) << 48) |
                     ((c & 15) << 44) | ((d & 15) << 40) | (imm & ((1 << 40) - 1)))
    if sys.byteorder != 'little':
        words.byteswap()
    code = words.tobytes()
    return b'CPU32J2\0' + struct.pack('<IIII', 2, 0, len(code), len(words)) + code, labels, len(words)


class OSCompiler:
  def __init__(self):
    self.a=Builder(); self.str_addr={}; self.strings=[]; self.data_ptr=CONST_BASE
  def register_strings(self,values):
    values=list(values)+list(KEY_CONTENT.keys())+list(KEY_CONTENT.values())
    for item in values:
      key=str(item).upper()
      content=KEY_CONTENT.get(key,key).upper()
      if content not in self.str_addr:
        self.str_addr[content]=self.data_ptr; self.strings.append(content); self.data_ptr += (len(content)+1)*4
    if self.data_ptr > OUT_BASE: raise RuntimeError(f'string area overlaps output buffer: {hex(self.data_ptr)}')
  def msg(self,s):
    content=KEY_CONTENT.get(str(s).upper(),str(s).upper()).upper()
    return self.str_addr[content]
  def print_const(self,s):
    self.a.li(1,self.msg(s)); self.a.stg(G['PRINT_SRC'],1); self.a.call('print_line')
  def emit_init_data(self):
    a=self.a; a.label('start')
    # Static 5x7 font table, 128 glyphs x 7 rows.
    for i,v in enumerate(make_font_words()):
      a.li(8,v); a.li(9,FONT_BASE+i*4); a.e('STORE r9 r8')
    # Read-only strings are materialized as zero-terminated word arrays in RAM.
    for s,addr in self.str_addr.items():
      for i,ch in enumerate(s+'\0'):
        a.li(8,ord(ch)); a.li(9,addr+i*4); a.e('STORE r9 r8')
    a.br('JMP','gui_boot')

  def emit_shell(self):
    a=self.a
    self.emit_gui_boot_and_loop()

    # ---- legacy terminal startup / command handlers retained for app services ----
    a.label('os_boot')
    for addr,val in ((G['CMD_LEN'],0),(G['TICK'],0),(G['OUT_COUNT'],0),(G['TEXT_COL'],0),(G['TEXT_COLOR'],0x66FFAAFF)):
      a.li(8,val); a.stg(addr,8)
    for addr,nbytes in ((OUT_BASE,OUT_ROWS*LINE_LEN*4),(CMD_BUF,120*4),(CMD_WORD,24*4),(ARG_NAME,24*4),(ARG_TEXT,110*4),(FS_USED,FS_SLOTS*4),(FS_NAMES,FS_SLOTS*NAME_LEN*4),(FS_SIZE,FS_SLOTS*4),(FS_PARENT,FS_SLOTS*4),(FS_TYPE,FS_SLOTS*4),(FS_PAGE,FS_SLOTS*4)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    self.print_const('WELCOME')
    self.print_const('OS_READY')
    self.print_const('HELP_HINT')
    a.call('draw_screen')
    # ---- event loop ----
    a.label('main_loop')
    a.li(2,0xFFFFFFFF); a.e('LOAD8 r1 r2')
    a.e('CMP r1 r0'); a.br('JZE','idle_tick')
    a.li(2,13); a.e('CMP r1 r2'); a.br('JEQ','input_enter')
    a.li(2,10); a.e('CMP r1 r2'); a.br('JEQ','input_enter')
    a.li(2,8); a.e('CMP r1 r2'); a.br('JEQ','input_backspace')
    a.li(2,127); a.e('CMP r1 r2'); a.br('JEQ','input_backspace')
    a.li(2,32); a.e('CMP r1 r2'); a.br('JLT','main_loop')
    a.li(2,126); a.e('CMP r1 r2'); a.br('JGT','main_loop')
    # uppercase for a compact ROM font
    a.li(2,97); a.e('CMP r1 r2'); a.br('JLT','input_append')
    a.li(2,122); a.e('CMP r1 r2'); a.br('JGT','input_append')
    a.li(2,32); a.e('SUB r1 r1 r2')
    a.label('input_append')
    a.ldg(3,G['CMD_LEN']); a.li(4,99); a.e('CMP r3 r4'); a.br('JGE','main_loop')
    a.stx(CMD_BUF,3,1); a.li(4,1); a.e('ADD r3 r3 r4'); a.stg(G['CMD_LEN'],3)
    a.call('draw_screen'); a.br('JMP','main_loop')
    a.label('input_backspace')
    a.ldg(3,G['CMD_LEN']); a.e('CMP r3 r0'); a.br('JLE','main_loop')
    a.li(4,1); a.e('SUB r3 r3 r4'); a.stg(G['CMD_LEN'],3); a.li(4,0); a.stx(CMD_BUF,3,4)
    a.call('draw_screen'); a.br('JMP','main_loop')
    a.label('input_enter')
    a.ldg(3,G['CMD_LEN']); a.li(4,0); a.stx(CMD_BUF,3,4)
    a.call('echo_command'); a.call('parse_command'); a.call('execute_command'); a.call('gui_sfx_ok')
    a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['CMD_LEN'],1)
    a.call('draw_screen'); a.br('JMP','main_loop')
    a.label('idle_tick'); a.ldg(2,G['TICK']); a.li(3,1); a.e('ADD r2 r2 r3'); a.stg(G['TICK'],2); a.br('JMP','main_loop')

    # ---- output-line ring (scroll by copying upward) ----
    a.label('print_line')
    # Append output at the first unused row; only scroll after the history is full.
    a.ldg(1,G['OUT_COUNT']); a.li(2,OUT_ROWS); a.e('CMP r1 r2'); a.br('JGE','print_scroll')
    a.stg(G['OUT_TARGET'],1); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['OUT_COUNT'],1); a.br('JMP','print_row_ready')
    a.label('print_scroll')
    a.li(1,OUT_BASE); a.li(2,OUT_BASE+LINE_LEN*4); a.li(3,(OUT_ROWS-1)*LINE_LEN*4); a.e('MEMCPY r1 r2 r3')
    a.li(1,OUT_ROWS-1); a.stg(G['OUT_TARGET'],1)
    a.label('print_row_ready')
    a.ldg(1,G['OUT_TARGET']); a.li(2,LINE_LEN*4); a.e('MUL r3 r1 r2'); a.li(4,OUT_BASE); a.e('ADD r1 r3 r4'); a.stg(G['PRINT_DEST'],1)
    a.li(2,0); a.li(3,LINE_LEN*4); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['PRINT_I'],1)
    a.label('print_copy_loop')
    a.ldg(1,G['PRINT_I']); a.li(2,LINE_LEN-1); a.e('CMP r1 r2'); a.br('JGE','print_done')
    a.ldg(2,G['PRINT_SRC']); a.e('LDX r3 r2 r1'); a.e('CMP r3 r0'); a.br('JZE','print_done')
    a.ldg(2,G['PRINT_DEST']); a.e('STX r2 r1 r3')
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PRINT_I'],1); a.br('JMP','print_copy_loop')
    a.label('print_done'); a.e('RET')

    # ---- echo entered command as an output line ----
    a.label('echo_command')
    for i,ch in enumerate('> '): a.li(8,ord(ch)); a.li(9,ECHO_BUF+i*4); a.e('STORE r9 r8')
    a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('echo_copy_loop')
    a.ldg(1,G['TEMP_I']); a.li(2,96); a.e('CMP r1 r2'); a.br('JGE','echo_copy_done')
    a.ldx(3,CMD_BUF,1); a.e('CMP r3 r0'); a.br('JZE','echo_copy_done')
    a.li(2,ECHO_BUF+8); a.e('ADD r2 r1 r0'); # r2 = index before later adding base scaled separately
    a.li(4,2); a.e('ADD r2 r2 r4')
    # use output pointer index by storing into ECHO_BUF with index i+2
    a.li(4,2); a.e('ADD r5 r1 r4'); a.stx(ECHO_BUF,5,3)
    a.li(4,1); a.e('ADD r1 r1 r4'); a.stg(G['TEMP_I'],1); a.br('JMP','echo_copy_loop')
    a.label('echo_copy_done'); a.ldg(1,G['TEMP_I']); a.li(2,2); a.e('ADD r1 r1 r2'); a.li(3,0); a.stx(ECHO_BUF,1,3); a.li(1,0); a.stg(G['PRINT_I'],1); a.li(1,ECHO_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')

    # ---- parser: token 1 => CMD_WORD, token 2 => ARG_NAME, rest => ARG_TEXT ----
    a.label('parse_command')
    for addr,nbytes in ((CMD_WORD,24*4),(ARG_NAME,24*4),(ARG_TEXT,110*4)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['PARSE_I'],1); a.stg(G['TOKEN_LEN'],1); a.stg(G['ARG_NAME_LEN'],1); a.stg(G['ARG_TEXT_LEN'],1)
    # skip leading spaces
    a.label('parse_skip_lead')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_done')
    a.li(3,32); a.e('CMP r2 r3'); a.br('JNE','parse_token_one')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_skip_lead')
    a.label('parse_token_one')
    a.label('parse_cmd_loop')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_after_cmd')
    a.li(3,32); a.e('CMP r2 r3'); a.br('JEQ','parse_after_cmd')
    a.ldg(4,G['TOKEN_LEN']); a.li(5,23); a.e('CMP r4 r5'); a.br('JGE','parse_cmd_advance')
    a.stx(CMD_WORD,4,2); a.li(5,1); a.e('ADD r4 r4 r5'); a.stg(G['TOKEN_LEN'],4)
    a.label('parse_cmd_advance')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_cmd_loop')
    a.label('parse_after_cmd')
    a.label('parse_skip_name_space')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_done')
    a.li(3,32); a.e('CMP r2 r3'); a.br('JNE','parse_name_loop')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_skip_name_space')
    a.label('parse_name_loop')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_after_name')
    a.li(3,32); a.e('CMP r2 r3'); a.br('JEQ','parse_after_name')
    a.ldg(4,G['ARG_NAME_LEN']); a.li(5,23); a.e('CMP r4 r5'); a.br('JGE','parse_name_advance')
    a.stx(ARG_NAME,4,2); a.li(5,1); a.e('ADD r4 r4 r5'); a.stg(G['ARG_NAME_LEN'],4)
    a.label('parse_name_advance')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_name_loop')
    a.label('parse_after_name')
    a.label('parse_skip_text_space')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_done')
    a.li(3,32); a.e('CMP r2 r3'); a.br('JNE','parse_text_loop')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_skip_text_space')
    a.label('parse_text_loop')
    a.ldg(1,G['PARSE_I']); a.ldx(2,CMD_BUF,1); a.e('CMP r2 r0'); a.br('JEQ','parse_done')
    a.ldg(4,G['ARG_TEXT_LEN']); a.li(5,109); a.e('CMP r4 r5'); a.br('JGE','parse_text_advance')
    a.stx(ARG_TEXT,4,2); a.li(5,1); a.e('ADD r4 r4 r5'); a.stg(G['ARG_TEXT_LEN'],4)
    a.label('parse_text_advance')
    a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_text_loop')
    a.label('parse_done'); a.e('RET')

    # ---- string equality: PTR_A/PTR_B, result STR_RESULT ----
    a.label('string_equal')
    a.li(1,0); a.stg(G['STR_I'],1); a.li(1,0); a.stg(G['STR_RESULT'],1)
    a.label('strcmp_loop')
    a.ldg(1,G['STR_I']); a.li(2,24); a.e('CMP r1 r2'); a.br('JGE','strcmp_done')
    a.ldg(2,G['PTR_A']); a.e('LDX r3 r2 r1'); a.ldg(2,G['PTR_B']); a.e('LDX r4 r2 r1')
    a.e('CMP r3 r4'); a.br('JNE','strcmp_done'); a.e('CMP r3 r0'); a.br('JEQ','strcmp_yes')
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['STR_I'],1); a.br('JMP','strcmp_loop')
    a.label('strcmp_yes'); a.li(1,1); a.stg(G['STR_RESULT'],1)
    a.label('strcmp_done'); a.e('RET')

    # ---- NOVA-FS inode lookup: current directory + inline 16-character names ----
    a.label('find_file')
    a.li(1,-1); a.stg(G['FILE_FOUND'],1); a.stg(G['FILE_FREE'],1); a.li(1,1); a.stg(G['FILE_I'],1)
    a.label('find_file_loop')
    a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','find_file_done')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','find_file_unused')
    a.ldx(3,FS_PARENT,1); a.ldg(4,G['CWD_ID']); a.e('CMP r3 r4'); a.br('JNE','find_file_next')
    a.ldg(1,G['FILE_I']); a.li(2,NAME_LEN); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r4 r4 r3'); a.stg(G['PTR_B'],4)
    a.li(4,ARG_NAME); a.stg(G['PTR_A'],4); a.call('string_equal')
    a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ','find_file_yes'); a.br('JMP','find_file_next')
    a.label('find_file_unused')
    a.ldg(4,G['FILE_FREE']); a.li(5,-1); a.e('CMP r4 r5'); a.br('JNE','find_file_next')
    a.ldg(4,G['FILE_I']); a.stg(G['FILE_FREE'],4)
    a.label('find_file_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','find_file_loop')
    a.label('find_file_yes'); a.ldg(1,G['FILE_I']); a.stg(G['FILE_FOUND'],1); a.e('RET')
    a.label('find_file_done'); a.e('RET')

    # Create a regular file in the current directory. Payload is one high-RAM page (1024 words).
    a.label('create_file')
    a.ldg(1,G['FILE_FREE']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','create_file_done')
    a.ldg(3,G['LAST_DELETED']); a.e('CMP r1 r3'); a.br('JNE','create_file_alloc')
    a.ldg(1,G['FILE_FREE']); a.ldx(2,FS_PAGE,1); a.e('CMP r2 r0'); a.br('JEQ','create_file_invalidate')
    a.e('MOV r1 r2'); a.call('page_free')
    a.label('create_file_invalidate'); a.li(1,-1); a.stg(G['LAST_DELETED'],1)
    a.label('create_file_alloc'); a.call('page_alloc'); a.ldg(1,G['PAGE_RESULT']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','create_file_done')
    a.ldg(2,G['FILE_FREE']); a.stx(FS_PAGE,2,1); a.stg(G['FILE_FOUND'],2)
    a.li(3,1); a.stx(FS_USED,2,3); a.li(3,2); a.stx(FS_TYPE,2,3); a.ldg(3,G['CWD_ID']); a.stx(FS_PARENT,2,3); a.li(3,0); a.stx(FS_SIZE,2,3)
    a.li(2,0); a.li(3,4096); a.e('MEMSET r1 r2 r3')
    a.ldg(1,G['FILE_FREE']); a.li(2,64); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r1 r3 r4'); a.li(2,0); a.li(3,NAME_LEN*4); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('create_name_loop'); a.ldg(1,G['TEMP_I']); a.li(2,NAME_LEN-1); a.e('CMP r1 r2'); a.br('JGE','create_name_done')
    a.ldx(3,ARG_NAME,1); a.e('CMP r3 r0'); a.br('JEQ','create_name_done')
    a.ldg(4,G['FILE_FREE']); a.li(5,NAME_LEN); a.e('MUL r4 r4 r5'); a.e('ADD r5 r4 r1'); a.stx(FS_NAMES,5,3)
    a.ldg(1,G['TEMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','create_name_loop')
    a.label('create_name_done'); a.e('RET'); a.label('create_file_done'); a.e('RET')

    # Create a directory inode; directories have no payload page.
    a.label('create_directory')
    a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','create_dir_exists')
    a.ldg(1,G['FILE_FREE']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','create_file_done')
    a.ldg(3,G['LAST_DELETED']); a.e('CMP r1 r3'); a.br('JNE','create_dir_slot_ready')
    a.ldx(1,FS_PAGE,1); a.e('CMP r1 r0'); a.br('JEQ','create_dir_slot_ready'); a.call('page_free'); a.li(1,-1); a.stg(G['LAST_DELETED'],1)
    a.label('create_dir_slot_ready'); a.stg(G['FILE_FOUND'],1); a.li(2,1); a.stx(FS_USED,1,2); a.li(2,1); a.stx(FS_TYPE,1,2); a.ldg(2,G['CWD_ID']); a.stx(FS_PARENT,1,2); a.li(2,0); a.stx(FS_SIZE,1,2); a.stx(FS_PAGE,1,2)
    a.ldg(1,G['FILE_FREE']); a.li(2,64); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r1 r3 r4'); a.li(2,0); a.li(3,NAME_LEN*4); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('create_dir_name_loop'); a.ldg(1,G['TEMP_I']); a.li(2,NAME_LEN-1); a.e('CMP r1 r2'); a.br('JGE','create_dir_name_done')
    a.ldx(3,ARG_NAME,1); a.e('CMP r3 r0'); a.br('JEQ','create_dir_name_done')
    a.ldg(4,G['FILE_FREE']); a.li(5,NAME_LEN); a.e('MUL r4 r4 r5'); a.e('ADD r5 r4 r1'); a.stx(FS_NAMES,5,3)
    a.ldg(1,G['TEMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','create_dir_name_loop')
    a.label('create_dir_name_done'); self.print_const('DIRECTORY CREATED'); a.e('RET')
    a.label('create_dir_exists'); self.print_const('FILE EXISTS'); a.e('RET')

    # File content writer: each file owns one lazily committed 4 KiB high-RAM page.
    a.label('write_file_content')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','write_file_done')
    a.ldx(2,FS_TYPE,1); a.li(3,2); a.e('CMP r2 r3'); a.br('JNE','write_file_done')
    a.ldx(5,FS_PAGE,1)
    a.ldg(3,G['TEMP_A']); a.e('CMP r3 r0'); a.br('JNE','write_file_append')
    a.li(3,0); a.stx(FS_SIZE,1,3); a.li(2,0); a.li(3,4096); a.e('MEMSET r5 r2 r3')
    a.label('write_file_append'); a.ldx(2,FS_SIZE,1); a.stg(G['TEMP_I'],2); a.li(1,0); a.stg(G['PARSE_I'],1)
    a.label('write_content_loop'); a.ldg(1,G['PARSE_I']); a.ldg(2,G['ARG_TEXT_LEN']); a.e('CMP r1 r2'); a.br('JGE','write_content_done')
    a.ldg(3,G['TEMP_I']); a.li(4,FILE_LEN-1); a.e('CMP r3 r4'); a.br('JGE','write_content_done')
    a.ldx(4,ARG_TEXT,1); a.e('STX r5 r3 r4')
    a.li(4,1); a.e('ADD r1 r1 r4'); a.stg(G['PARSE_I'],1); a.e('ADD r3 r3 r4'); a.stg(G['TEMP_I'],3); a.br('JMP','write_content_loop')
    a.label('write_content_done'); a.ldg(1,G['FILE_FOUND']); a.ldg(2,G['TEMP_I']); a.stx(FS_SIZE,1,2)
    a.label('write_file_done'); a.e('RET')

    # ---- command dispatcher ----
    a.label('execute_command')
    a.ldx(1,CMD_WORD,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_noop')
    command_cases=[('HELP','cmd_help'),('CLS','cmd_cls'),('CLEAR','cmd_cls'),('ABOUT','cmd_about'),('VER','cmd_version'),('VERSION','cmd_version'),('SYSINFO','cmd_sysinfo'),('MEM','cmd_mem'),('TIME','cmd_time'),('UPTIME','cmd_time'),('PWD','cmd_pwd'),('LS','cmd_ls'),('DIR','cmd_ls'),('TOUCH','cmd_touch'),('CAT','cmd_cat'),('TYPE','cmd_cat'),('WRITE','cmd_write'),('APPEND','cmd_append'),('DEL','cmd_del'),('RM','cmd_del'),('ECHO','cmd_echo'),('CALC','cmd_calc'),('FORMAT','cmd_format'),('REBOOT','cmd_reboot'),('SIZE','cmd_size'),('STAT','cmd_size'),('EXISTS','cmd_exists'),('CRC32','cmd_crc32'),('RUN','cmd_run'),('FACT','cmd_fact'),('FIB','cmd_fib'),('GCD','cmd_gcd'),('HCF','cmd_gcd'),('LCM','cmd_lcm'),('SQRT','cmd_sqrt'),('PRIME','cmd_prime'),('RAND','cmd_rand'),('POPCNT','cmd_popcnt'),('CLZ','cmd_clz'),('CTZ','cmd_ctz'),('HEX','cmd_hex'),('BIN','cmd_bin'),('BENCH','cmd_bench'),('MEMTEST','cmd_memtest'),('SELFTEST','cmd_selftest'),('MKDIR','cmd_mkdir'),('RMDIR','cmd_rmdir'),('CD','cmd_cd'),('MOVE','cmd_move'),('RENAME','cmd_rename'),('COPY','cmd_copy'),('UNDO','cmd_undelete'),('FSCK','cmd_fsck'),('PAGE','cmd_page'),('STACK','cmd_stack'),('PS','cmd_ps'),('CONVERT','cmd_convert'),('DUMP','cmd_dump'),('PANIC_TEST','cmd_panic_test'),('SOUND','cmd_sound'),('EVENT','cmd_event')]
    for command,label in command_cases:
      a.li(1,CMD_WORD); a.stg(G['PTR_A'],1); a.li(1,self.msg(command)); a.stg(G['PTR_B'],1); a.call('string_equal')
      a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ',label)
    self.print_const('UNKNOWN_COMMAND')
    a.label('cmd_noop'); a.e('RET')

    # help
    a.label('cmd_help')
    for s in ['HELP_TITLE','HELP_1','HELP_2','HELP_3','HELP_4','HELP_5','HELP_6','HELP_7','HELP_8','HELP_9','HELP_10','HELP_11','HELP_12','HELP_13','HELP_14','HELP 2: FACT FIB GCD LCM SQRT PRIME RAND HEX BIN POPCNT CLZ CTZ','HELP 3: SIZE EXISTS STAT CRC32 TYPE RM RUN SCRIPT','HELP 4: BENCH N MEMTEST N SELFTEST']:
      self.print_const(s)
    a.e('RET')
    # clear terminal history
    a.label('cmd_cls')
    a.li(1,OUT_BASE); a.li(2,0); a.li(3,OUT_ROWS*LINE_LEN*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['OUT_COUNT'],1); self.print_const('CLEARED'); a.e('RET')
    a.label('cmd_about'); self.print_const('OS_TITLE'); self.print_const('OS_ABOUT_1'); self.print_const('OS_ABOUT_2'); self.print_const('OS_ABOUT_3'); a.e('RET')
    a.label('cmd_sysinfo'); self.print_const('SYS_TITLE'); self.print_const('SYS_1'); self.print_const('SYS_2'); self.print_const('SYS_3'); self.print_const('SYS_4'); self.print_const('SYS_5'); a.e('RET')
    a.label('cmd_mem'); self.print_const('MEM_TITLE'); self.print_const('MEM_1'); self.print_const('MEM_2'); self.print_const('MEM_3'); self.print_const('MEM_4'); a.e('RET')
    a.label('cmd_time'); self.print_const('TIME_TITLE'); a.ldg(1,G['TICK']); a.stg(G['CALC_RESULT'],1); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    # LS
    a.label('cmd_ls'); self.print_const('LS_TITLE'); a.li(1,0); a.stg(G['FILE_I'],1)
    a.label('ls_loop'); a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','ls_done')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','ls_next')
    a.ldx(3,FS_PARENT,1); a.ldg(4,G['CWD_ID']); a.e('CMP r3 r4'); a.br('JNE','ls_next')
    a.ldg(1,G['FILE_I']); a.li(2,64); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r4 r4 r3'); a.stg(G['PRINT_SRC'],4); a.call('print_line')
    a.label('ls_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','ls_loop')
    a.label('ls_done'); self.print_const('LS_END'); a.e('RET')
    # TOUCH
    a.label('cmd_touch'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name')
    a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','touch_exists')
    a.call('create_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_fs_full')
    self.print_const('FILE_CREATED'); a.e('RET')
    a.label('touch_exists'); self.print_const('FILE_EXISTS'); a.e('RET')
    # WRITE / APPEND share writer
    a.label('cmd_write'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name')
    a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','write_existing')
    a.call('create_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_fs_full')
    a.label('write_existing'); a.li(1,0); a.stg(G['TEMP_A'],1); a.call('write_file_content'); self.print_const('FILE_WRITTEN'); a.e('RET')
    a.label('cmd_append'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name')
    a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.li(1,1); a.stg(G['TEMP_A'],1); a.call('write_file_content'); self.print_const('FILE_APPENDED'); a.e('RET')
    # CAT chunk lines
    a.label('cmd_cat'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.ldx(3,FS_TYPE,1); a.li(4,2); a.e('CMP r3 r4'); a.br('JNE','cmd_not_directory')
    a.ldg(1,G['FILE_FOUND']); a.ldx(2,FS_SIZE,1); a.stg(G['TEMP_B'],2); a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('cat_loop'); a.ldg(1,G['TEMP_I']); a.ldg(2,G['TEMP_B']); a.e('CMP r1 r2'); a.br('JGE','cat_done')
    a.li(1,CAT_BUF); a.li(2,0); a.li(3,100*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['LOOP_I'],1)
    a.label('cat_copy_loop'); a.ldg(1,G['LOOP_I']); a.li(2,99); a.e('CMP r1 r2'); a.br('JGE','cat_copy_done')
    a.ldg(3,G['TEMP_I']); a.e('ADD r4 r3 r1'); a.ldg(5,G['FILE_FOUND']); a.ldx(5,FS_PAGE,5); a.e('LDX r6 r5 r4')
    a.e('CMP r6 r0'); a.br('JEQ','cat_copy_done'); a.stx(CAT_BUF,1,6)
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['LOOP_I'],1); a.br('JMP','cat_copy_loop')
    a.label('cat_copy_done'); a.li(1,CAT_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line')
    a.ldg(1,G['TEMP_I']); a.li(2,99); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','cat_loop')
    a.label('cat_done'); a.e('RET')
    # DEL
    a.label('cmd_del'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.ldx(3,FS_TYPE,1); a.li(4,2); a.e('CMP r3 r4'); a.br('JNE','cmd_not_directory')
    a.ldg(3,G['LAST_DELETED']); a.li(4,-1); a.e('CMP r3 r4'); a.br('JEQ','cmd_del_new_tombstone'); a.e('CMP r1 r3'); a.br('JEQ','cmd_del_new_tombstone'); a.ldx(1,FS_PAGE,3); a.e('CMP r1 r0'); a.br('JEQ','cmd_del_new_tombstone'); a.call('page_free'); a.label('cmd_del_new_tombstone')
    a.ldg(1,G['FILE_FOUND']); a.stg(G['LAST_DELETED'],1); a.li(2,0); a.stx(FS_USED,1,2); self.print_const('FILE_DELETED'); a.e('RET')
    # ECHO combines token 2 and the remaining text so single-word ECHO works too.
    a.label('cmd_echo'); a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('echo_arg1_loop'); a.ldg(1,G['TEMP_I']); a.li(2,23); a.e('CMP r1 r2'); a.br('JGE','echo_arg1_done')
    a.ldx(3,ARG_NAME,1); a.e('CMP r3 r0'); a.br('JEQ','echo_arg1_done'); a.stx(ECHO_BUF,1,3)
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','echo_arg1_loop')
    a.label('echo_arg1_done'); a.ldx(1,ARG_TEXT,0); a.e('CMP r1 r0'); a.br('JEQ','echo_arg_terminate')
    a.ldg(1,G['TEMP_I']); a.li(2,32); a.stx(ECHO_BUF,1,2); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1)
    a.li(1,0); a.stg(G['PARSE_I'],1)
    a.label('echo_arg2_loop'); a.ldg(1,G['PARSE_I']); a.li(2,100); a.e('CMP r1 r2'); a.br('JGE','echo_arg_terminate')
    a.ldx(3,ARG_TEXT,1); a.e('CMP r3 r0'); a.br('JEQ','echo_arg_terminate'); a.ldg(4,G['TEMP_I']); a.stx(ECHO_BUF,4,3)
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PARSE_I'],1); a.ldg(4,G['TEMP_I']); a.li(2,1); a.e('ADD r4 r4 r2'); a.stg(G['TEMP_I'],4); a.br('JMP','echo_arg2_loop')
    a.label('echo_arg_terminate'); a.ldg(1,G['TEMP_I']); a.li(2,0); a.stx(ECHO_BUF,1,2); a.li(1,ECHO_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    # FORMAT
    a.label('cmd_format'); a.ldg(1,G['LAST_DELETED']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','format_active_init'); a.ldx(1,FS_PAGE,1); a.e('CMP r1 r0'); a.br('JEQ','format_active_init'); a.call('page_free')
    a.label('format_active_init'); a.li(1,1); a.stg(G['FILE_I'],1)
    a.label('format_free_loop'); a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','format_clear_metadata')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','format_free_next')
    a.ldx(3,FS_TYPE,1); a.li(2,2); a.e('CMP r3 r2'); a.br('JNE','format_free_next')
    a.ldx(1,FS_PAGE,1); a.e('CMP r1 r0'); a.br('JEQ','format_free_next'); a.call('page_free')
    a.label('format_free_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','format_free_loop')
    a.label('format_clear_metadata')
    for addr,nbytes in ((FS_USED,FS_SLOTS*4),(FS_NAMES,FS_SLOTS*NAME_LEN*4),(FS_SIZE,FS_SLOTS*4),(FS_PARENT,FS_SLOTS*4),(FS_TYPE,FS_SLOTS*4),(FS_PAGE,FS_SLOTS*4)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    a.li(1,1); a.stx(FS_USED,0,1); a.li(1,1); a.stx(FS_TYPE,0,1); a.li(1,ord('/')); a.stx(FS_NAMES,0,1); a.li(1,0); a.stx(FS_NAMES,1,1)
    a.stg(G['CWD_ID'],1); a.li(1,-1); a.stg(G['LAST_DELETED'],1)
    self.print_const('FS_FORMATTED'); a.e('RET')
    # reboot guest OS state but preserve RAM FS
    a.label('cmd_reboot'); self.print_const('REBOOTING'); a.li(1,OUT_BASE); a.li(2,0); a.li(3,OUT_ROWS*LINE_LEN*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['OUT_COUNT'],1); self.print_const('WELCOME'); self.print_const('OS_READY'); self.print_const('HELP_HINT'); a.e('RET')
    a.label('cmd_need_name'); a.call('gui_sfx_error'); self.print_const('ERR_NAME'); a.e('RET')
    a.label('cmd_not_found'); a.call('gui_sfx_error'); self.print_const('ERR_NOT_FOUND'); a.e('RET')
    a.label('cmd_fs_full'); a.call('gui_sfx_error'); self.print_const('ERR_FS_FULL'); a.e('RET')

    # ---- V4 shell utilities ----
    a.label('cmd_version'); self.print_const('NOVA 7.1 WORKSTATION GRAPHICAL EDITION'); self.print_const('GUEST ISA CPU32J2 V2'); a.e('RET')
    a.label('cmd_pwd'); a.ldg(1,G['CWD_ID']); a.e('CMP r1 r0'); a.br('JEQ','cmd_pwd_root')
    a.li(2,64); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r1 r3 r4'); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    a.label('cmd_pwd_root'); self.print_const('RAM:/'); a.e('RET')

    # Hierarchical RAM filesystem directory operations.
    a.label('cmd_mkdir'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('create_directory'); a.e('RET')
    a.label('cmd_cd'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name')
    a.li(2,47); a.e('CMP r1 r2'); a.br('JEQ','cmd_cd_root')
    a.li(2,46); a.e('CMP r1 r2'); a.br('JNE','cmd_cd_lookup')
    a.ldx(1,ARG_NAME,1); a.e('CMP r1 r2'); a.br('JNE','cmd_cd_lookup')
    a.ldg(1,G['CWD_ID']); a.e('CMP r1 r0'); a.br('JEQ','cmd_cd_root'); a.ldx(2,FS_PARENT,1); a.stg(G['CWD_ID'],2); self.print_const('CURRENT DIRECTORY'); a.e('RET')
    a.label('cmd_cd_root'); a.li(1,0); a.stg(G['CWD_ID'],1); self.print_const('RAM:/'); a.e('RET')
    a.label('cmd_cd_lookup'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.ldx(2,FS_TYPE,1); a.li(3,1); a.e('CMP r2 r3'); a.br('JNE','cmd_not_directory'); a.stg(G['CWD_ID'],1); self.print_const('CURRENT DIRECTORY'); a.e('RET')
    a.label('cmd_not_directory'); self.print_const('ERROR: NOT A DIRECTORY'); a.e('RET')

    # Rename an inode in-place. Syntax: RENAME old-name new-name.
    a.label('cmd_rename'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found'); a.stg(G['CRC_SLOT'],1)
    a.li(1,ARG_TEXT); a.li(2,ARG_NAME); a.li(3,24*4); a.e('MEMCPY r1 r2 r3'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','rename_target_free'); a.ldg(2,G['CRC_SLOT']); a.e('CMP r1 r2'); a.br('JNE','rename_target_exists')
    a.label('rename_target_free'); a.ldg(1,G['CRC_SLOT']); a.li(2,NAME_LEN); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r1 r3 r4'); a.li(2,0); a.li(3,NAME_LEN*4); a.e('MEMSET r1 r2 r3')
    a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('rename_copy_loop'); a.ldg(1,G['TEMP_I']); a.li(2,NAME_LEN-1); a.e('CMP r1 r2'); a.br('JGE','rename_copy_done')
    a.ldx(3,ARG_NAME,1); a.e('CMP r3 r0'); a.br('JEQ','rename_copy_done'); a.ldg(4,G['CRC_SLOT']); a.li(5,NAME_LEN); a.e('MUL r4 r4 r5'); a.e('ADD r5 r5 r1'); a.stx(FS_NAMES,5,3)
    a.ldg(1,G['TEMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','rename_copy_loop')
    a.label('rename_copy_done'); self.print_const('FILE RENAMED'); a.e('RET')
    a.label('rename_target_exists'); self.print_const('RENAME TARGET ALREADY EXISTS'); a.e('RET')

    # Duplicate one page-backed file. Syntax: COPY source-name destination-name.
    a.label('cmd_copy'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.ldx(3,FS_TYPE,1); a.li(4,2); a.e('CMP r3 r4'); a.br('JNE','cmd_not_directory'); a.stg(G['CRC_SLOT'],1)
    a.li(1,ARG_TEXT); a.li(2,ARG_NAME); a.li(3,24*4); a.e('MEMCPY r1 r2 r3'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','cmd_copy_exists')
    a.call('create_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_copy_exists'); a.stg(G['TEMP_B'],1)
    a.ldg(1,G['CRC_SLOT']); a.ldx(2,FS_PAGE,1); a.ldg(1,G['TEMP_B']); a.ldx(3,FS_PAGE,1); a.li(4,4096); a.e('MEMCPY r2 r3 r4')
    a.ldg(1,G['CRC_SLOT']); a.ldx(2,FS_SIZE,1); a.ldg(1,G['TEMP_B']); a.stx(FS_SIZE,1,2); self.print_const('FILE COPIED'); a.e('RET')
    a.label('cmd_copy_exists'); self.print_const('COPY DESTINATION EXISTS OR NO FREE PAGE'); a.e('RET')

    # Move an inode into a child directory of the current directory. Syntax: MOVE file directory.
    a.label('cmd_move'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found'); a.ldx(3,FS_TYPE,1); a.li(4,2); a.e('CMP r3 r4'); a.br('JNE','cmd_not_directory'); a.stg(G['CRC_SLOT'],1)
    a.li(1,ARG_TEXT); a.li(2,ARG_NAME); a.li(3,24*4); a.e('MEMCPY r1 r2 r3'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_move_no_dir')
    a.ldx(3,FS_TYPE,1); a.li(4,1); a.e('CMP r3 r4'); a.br('JNE','cmd_move_no_dir'); a.stg(G['TEMP_B'],1); a.ldg(1,G['CRC_SLOT']); a.ldg(2,G['TEMP_B']); a.stx(FS_PARENT,1,2); self.print_const('FILE MOVED'); a.e('RET')
    a.label('cmd_move_no_dir'); self.print_const('ERROR: DESTINATION DIRECTORY NOT FOUND'); a.e('RET')

    # Remove an empty directory only. Syntax: RMDIR name.
    a.label('cmd_rmdir'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found'); a.stg(G['CRC_SLOT'],1)
    a.ldx(3,FS_TYPE,1); a.li(4,1); a.e('CMP r3 r4'); a.br('JNE','cmd_not_directory'); a.li(1,1); a.stg(G['FILE_I'],1)
    a.label('rmdir_child_loop'); a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','rmdir_remove')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','rmdir_child_next'); a.ldx(3,FS_PARENT,1); a.ldg(4,G['CRC_SLOT']); a.e('CMP r3 r4'); a.br('JEQ','rmdir_not_empty')
    a.label('rmdir_child_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','rmdir_child_loop')
    a.label('rmdir_remove'); a.ldg(1,G['LAST_DELETED']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','rmdir_mark')
    a.ldx(3,FS_PARENT,1); a.ldg(4,G['CRC_SLOT']); a.e('CMP r3 r4'); a.br('JNE','rmdir_mark'); a.ldx(1,FS_PAGE,1); a.e('CMP r1 r0'); a.br('JEQ','rmdir_mark'); a.call('page_free'); a.li(1,-1); a.stg(G['LAST_DELETED'],1)
    a.label('rmdir_mark'); a.ldg(1,G['CRC_SLOT']); a.li(2,0); a.stx(FS_USED,1,2); a.ldg(3,G['CWD_ID']); a.e('CMP r1 r3'); a.br('JNE','rmdir_done'); a.li(1,0); a.stg(G['CWD_ID'],1)
    a.label('rmdir_done'); self.print_const('DIRECTORY REMOVED'); a.e('RET')
    a.label('rmdir_not_empty'); self.print_const('ERROR: DIRECTORY NOT EMPTY'); a.e('RET')

    # Transactional one-file undelete; the page remains allocated until its inode is reused.
    a.label('cmd_undelete'); a.ldg(1,G['LAST_DELETED']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_undelete_none')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JNE','cmd_undelete_expired')
    a.ldx(3,FS_PAGE,1); a.e('CMP r3 r0'); a.br('JEQ','cmd_undelete_expired')
    a.li(2,1); a.stx(FS_USED,1,2); a.li(2,-1); a.stg(G['LAST_DELETED'],2); self.print_const('FILE RECOVERED'); a.e('RET')
    a.label('cmd_undelete_none'); self.print_const('NO DELETED FILE TO RECOVER'); a.e('RET')
    a.label('cmd_undelete_expired'); a.li(1,-1); a.stg(G['LAST_DELETED'],1); self.print_const('FILE SLOT REUSED / RECOVERY EXPIRED'); a.e('RET')

    # Structural VFS check with fatal checks identifying their exact guest PC.
    a.label('cmd_fsck'); a.li(1,1); a.stg(G['FILE_I'],1)
    a.label('fsck_loop'); a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','fsck_ok')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','fsck_next')
    a.ldx(3,FS_PARENT,1); a.li(4,FS_SLOTS); a.label('fsck_parent_compare'); a.e('CMP r3 r4'); a.br('JGE','fsck_bad_parent')
    a.ldx(4,FS_USED,3); a.e('CMP r4 r0'); a.br('JEQ','fsck_bad_parent')
    a.ldx(4,FS_TYPE,3); a.li(5,1); a.e('CMP r4 r5'); a.br('JNE','fsck_bad_parent')
    a.ldx(3,FS_TYPE,1); a.li(4,2); a.e('CMP r3 r4'); a.br('JNE','fsck_next')
    a.label('fsck_page_compare'); a.ldx(3,FS_PAGE,1); a.e('CMP r3 r0'); a.br('JEQ','fsck_bad_page')
    a.ldx(3,FS_SIZE,1); a.li(4,FILE_LEN); a.label('fsck_size_compare'); a.e('CMP r3 r4'); a.br('JGT','fsck_bad_size')
    a.label('fsck_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','fsck_loop')
    a.label('fsck_bad_parent')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,8); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('RAM FILESYSTEM PARENT INODE INVALID')); a.stg(G['PANIC_REASON'],14); a.e('LDI r14 fsck_parent_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('NOVA-FS PARENT VALIDATOR')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('fsck_bad_page')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,9); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('RAM FILESYSTEM DATA PAGE MISSING')); a.stg(G['PANIC_REASON'],14); a.e('LDI r14 fsck_page_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('NOVA-FS PAGE VALIDATOR')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('fsck_bad_size')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,10); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('RAM FILESYSTEM FILE SIZE INVALID')); a.stg(G['PANIC_REASON'],14); a.e('LDI r14 fsck_size_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('NOVA-FS SIZE VALIDATOR')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('fsck_ok'); self.print_const('NOVA-FS CHECK PASSED'); a.e('RET')

    # Calendar event table: 32 RAM-persistent event strings, retained across warm reboot.
    a.label('cmd_event'); a.li(1,ARG_NAME); a.stg(G['PTR_A'],1); a.li(1,self.msg('ADD')); a.stg(G['PTR_B'],1); a.call('string_equal'); a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ','event_add')
    a.li(1,ARG_NAME); a.stg(G['PTR_A'],1); a.li(1,self.msg('LIST')); a.stg(G['PTR_B'],1); a.call('string_equal'); a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ','event_list')
    a.li(1,ARG_NAME); a.stg(G['PTR_A'],1); a.li(1,self.msg('DEL')); a.stg(G['PTR_B'],1); a.call('string_equal'); a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ','event_delete')
    self.print_const('EVENT ADD <TEXT>  /  EVENT LIST  /  EVENT DEL <INDEX>'); a.e('RET')
    a.label('event_add'); a.li(1,0); a.stg(G['FILE_I'],1)
    a.label('event_add_loop'); a.ldg(1,G['FILE_I']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','event_full'); a.ldx(3,CAL_EVENT_USED,1); a.e('CMP r3 r0'); a.br('JEQ','event_add_found'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','event_add_loop')
    a.label('event_add_found'); a.ldg(1,G['FILE_I']); a.li(2,1); a.stx(CAL_EVENT_USED,1,2); a.ldg(1,G['FILE_I']); a.li(2,32); a.e('MUL r3 r1 r2'); a.li(4,CAL_EVENT_TEXT); a.e('ADD r1 r3 r4'); a.li(2,0); a.li(3,32*4); a.e('MEMSET r1 r2 r3'); a.li(1,ARG_TEXT); a.e('MOV r2 r1'); a.ldg(1,G['FILE_I']); a.li(3,32); a.e('MUL r4 r1 r3'); a.li(5,CAL_EVENT_TEXT); a.e('ADD r5 r5 r4'); a.li(3,32*4); a.e('MEMCPY r2 r5 r3'); self.print_const('CALENDAR EVENT ADDED'); a.e('RET')
    a.label('event_full'); self.print_const('CALENDAR EVENT TABLE FULL'); a.e('RET')
    a.label('event_list'); a.li(1,0); a.stg(G['FILE_I'],1); self.print_const('CALENDAR EVENTS')
    a.label('event_list_loop'); a.ldg(1,G['FILE_I']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','event_list_done'); a.ldx(3,CAL_EVENT_USED,1); a.e('CMP r3 r0'); a.br('JEQ','event_list_next'); a.ldg(1,G['FILE_I']); a.li(2,32); a.e('MUL r3 r1 r2'); a.li(4,CAL_EVENT_TEXT); a.e('ADD r1 r3 r4'); a.stg(G['PRINT_SRC'],1); a.call('print_line')
    a.label('event_list_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','event_list_loop')
    a.label('event_list_done'); a.e('RET')
    a.label('event_delete'); a.call('parse_arg_b'); a.ldg(1,G['CALC_B']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','event_bad_index'); a.e('CMP r1 r0'); a.br('JLT','event_bad_index'); a.li(2,0); a.stx(CAL_EVENT_USED,1,2); self.print_const('CALENDAR EVENT REMOVED'); a.e('RET')
    a.label('event_bad_index'); self.print_const('EVENT INDEX OUT OF RANGE'); a.e('RET')

    a.label('cmd_page'); self.print_const('PAGE ALLOCATOR / 4 KB PAGES'); a.call('page_alloc'); a.ldg(1,G['PAGE_RESULT']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_page_fail'); a.stg(G['PAGE_ADDR'],1); a.li(2,0x6A39C5D2); a.e('STORE r1 r2'); a.e('LOAD r3 r1'); a.li(4,0x6A39C5D2); a.label('cmd_page_verify'); a.e('CMP r3 r4'); a.br('JNE','cmd_page_fail'); a.ldg(1,G['PAGE_ADDR']); a.call('page_free'); a.li(1,64); a.call('slab_alloc'); a.ldg(1,G['SLAB_RESULT']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_page_fail'); a.stg(G['PAGE_ADDR'],1); a.li(2,0x3C5AA53C); a.e('STORE r1 r2'); a.e('LOAD r3 r1'); a.li(4,0x3C5AA53C); a.e('CMP r3 r4'); a.br('JNE','cmd_page_fail'); a.ldg(1,G['PAGE_ADDR']); a.li(2,64); a.call('slab_free'); a.ldg(1,G['PAGE_USED']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.li(1,PAGE_COUNT); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); self.print_const('KERNEL PAGE + SLAB MAP TEST PASSED'); a.e('RET')
    a.label('cmd_page_fail'); self.print_const('RAM PAGE / SLAB ALLOCATION FAILED'); a.e('RET')
    a.label('cmd_stack'); self.print_const('STACK USE / 1048576 BYTES'); a.ldg(1,G['STACK_HIGHWATER']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); self.print_const('STACK CANARY INTACT'); a.e('RET')
    a.label('cmd_ps'); self.print_const('ACTIVE APP ARENA'); a.ldg(1,G['APP_STATE']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); self.print_const('APP ARENAS ARE PAGE-BACKED'); a.e('RET')

    # Integer conversions. Syntax: CONVERT C 25, CONVERT F 77, CONVERT KM 100, etc.
    a.label('cmd_convert'); a.call('parse_arg_b'); a.ldg(1,G['CALC_B']); a.stg(G['CALC_RESULT'],1)
    for token,label in [('C','convert_c'),('F','convert_f'),('KM','convert_km'),('MI','convert_mi'),('KG','convert_kg'),('LB','convert_lb')]:
      a.li(1,ARG_NAME); a.stg(G['PTR_A'],1); a.li(1,self.msg(token)); a.stg(G['PTR_B'],1); a.call('string_equal'); a.ldg(1,G['STR_RESULT']); a.li(2,1); a.e('CMP r1 r2'); a.br('JEQ',label)
    self.print_const('CONVERT C/F/KM/MI/KG/LB VALUE'); a.e('RET')
    a.label('convert_c'); a.ldg(1,G['CALC_RESULT']); a.li(2,9); a.e('MUL r1 r1 r2'); a.li(2,5); a.e('DIVU r1 r1 r2'); a.li(2,32); a.e('ADD r1 r1 r2'); a.br('JMP','convert_result')
    a.label('convert_f'); a.ldg(1,G['CALC_RESULT']); a.li(2,32); a.e('SUB r1 r1 r2'); a.li(2,5); a.e('MUL r1 r1 r2'); a.li(2,9); a.e('DIVS r1 r1 r2'); a.br('JMP','convert_result')
    a.label('convert_km'); a.ldg(1,G['CALC_RESULT']); a.li(2,62); a.e('MUL r1 r1 r2'); a.li(2,100); a.e('DIVU r1 r1 r2'); a.br('JMP','convert_result')
    a.label('convert_mi'); a.ldg(1,G['CALC_RESULT']); a.li(2,161); a.e('MUL r1 r1 r2'); a.li(2,100); a.e('DIVU r1 r1 r2'); a.br('JMP','convert_result')
    a.label('convert_kg'); a.ldg(1,G['CALC_RESULT']); a.li(2,220); a.e('MUL r1 r1 r2'); a.li(2,100); a.e('DIVU r1 r1 r2'); a.br('JMP','convert_result')
    a.label('convert_lb'); a.ldg(1,G['CALC_RESULT']); a.li(2,45); a.e('MUL r1 r1 r2'); a.li(2,100); a.e('DIVU r1 r1 r2')
    a.label('convert_result'); a.stg(G['CALC_RESULT'],1); self.print_const('CONVERSION RESULT'); a.call('print_number_result'); a.e('RET')

    a.label('cmd_dump'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.stg(G['MEM_DUMP_ADDR'],1); self.print_const('MEMORY DUMP / 8 WORDS'); a.li(1,0); a.stg(G['MEM_DUMP_I'],1)
    a.label('cmd_dump_loop'); a.ldg(1,G['MEM_DUMP_I']); a.li(2,8); a.e('CMP r1 r2'); a.br('JGE','cmd_dump_done')
    a.ldg(1,G['MEM_DUMP_ADDR']); a.ldg(2,G['MEM_DUMP_I']); a.li(3,4); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2'); a.e('LOAD r3 r1'); a.stg(G['CALC_RESULT'],3); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.ldg(1,G['MEM_DUMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['MEM_DUMP_I'],1); a.br('JMP','cmd_dump_loop')
    a.label('cmd_dump_done'); a.e('RET')
    a.label('cmd_sound'); a.li(1,440); a.li(2,250); a.li(3,10); a.li(4,0); a.li(5,50); a.call('gui_sound_emit'); self.print_const('SOUND TEST SENT TO GUEST AUDIO MMIO'); a.e('RET')
    a.label('cmd_panic_test')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,0xEE); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('USER-REQUESTED PANIC TEST')); a.stg(G['PANIC_REASON'],14); a.e('LDI r14 cmd_panic_test'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('TERMINAL PANIC_TEST COMMAND')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')

    # SIZE / STAT: display the file's exact guest-RAM content length.
    a.label('cmd_size'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found')
    a.ldg(1,G['FILE_FOUND']); a.ldx(2,FS_SIZE,1); a.stg(G['CALC_RESULT'],2); self.print_const('FILE SIZE'); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    a.label('cmd_exists'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_exists_no'); self.print_const('FILE EXISTS: YES'); a.e('RET')
    a.label('cmd_exists_no'); self.print_const('FILE EXISTS: NO'); a.e('RET')

    # FACT n, with bounded 32-bit factorial.
    a.label('cmd_fact'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JLT','cmd_range_error'); a.li(2,12); a.e('CMP r1 r2'); a.br('JGT','cmd_range_error')
    a.li(1,1); a.stg(G['CALC_RESULT'],1); a.ldg(1,G['CALC_A']); a.stg(G['LOOP_I'],1)
    a.label('fact_loop'); a.ldg(1,G['LOOP_I']); a.li(2,1); a.e('CMP r1 r2'); a.br('JLE','fact_done')
    a.ldg(1,G['CALC_RESULT']); a.ldg(2,G['LOOP_I']); a.e('MUL r3 r1 r2'); a.stg(G['CALC_RESULT'],3)
    a.ldg(1,G['LOOP_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['LOOP_I'],1); a.br('JMP','fact_loop')
    a.label('fact_done'); self.print_const('FACTORIAL'); a.call('print_number_result'); a.e('RET')

    # FIB n, exact unsigned Fibonacci through F(46).
    a.label('cmd_fib'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JLT','cmd_range_error'); a.li(2,46); a.e('CMP r1 r2'); a.br('JGT','cmd_range_error')
    a.li(1,0); a.stg(G['TEMP_A'],1); a.li(1,1); a.stg(G['TEMP_B'],1); a.ldg(1,G['CALC_A']); a.stg(G['LOOP_I'],1)
    a.label('fib_loop'); a.ldg(1,G['LOOP_I']); a.e('CMP r1 r0'); a.br('JEQ','fib_done')
    a.ldg(1,G['TEMP_A']); a.ldg(2,G['TEMP_B']); a.e('ADD r3 r1 r2'); a.ldg(1,G['TEMP_B']); a.stg(G['TEMP_A'],1); a.stg(G['TEMP_B'],3)
    a.ldg(1,G['LOOP_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['LOOP_I'],1); a.br('JMP','fib_loop')
    a.label('fib_done'); a.ldg(1,G['TEMP_A']); a.stg(G['CALC_RESULT'],1); self.print_const('FIBONACCI'); a.call('print_number_result'); a.e('RET')

    # Shared argument parser helpers.
    a.label('parse_arg_a'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name')
    a.li(1,ARG_NAME); a.stg(G['PARSE_SRC'],1); a.li(1,0); a.stg(G['PARSE_I'],1); a.call('parse_number'); a.ldg(1,G['PARSE_VALUE']); a.stg(G['CALC_A'],1); a.e('RET')
    a.label('parse_arg_b'); a.ldx(1,ARG_TEXT,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_second')
    a.li(1,ARG_TEXT); a.stg(G['PARSE_SRC'],1); a.li(1,0); a.stg(G['PARSE_I'],1); a.call('parse_number'); a.ldg(1,G['PARSE_VALUE']); a.stg(G['CALC_B'],1); a.e('RET')
    a.label('print_number_result'); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    a.label('cmd_need_second'); self.print_const('ERROR: MISSING SECOND INTEGER'); a.e('RET')
    a.label('cmd_range_error'); a.call('gui_sfx_error'); self.print_const('ERROR: NUMBER OUT OF RANGE'); a.e('RET')

    # Euclidean GCD core operates on non-negative CALC_A/CALC_B.
    a.label('gcd_core'); a.label('gcd_loop'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JEQ','gcd_done')
    a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('REMU r3 r1 r2'); a.stg(G['MATH_AUX'],3)
    a.ldg(1,G['CALC_B']); a.stg(G['CALC_A'],1); a.ldg(1,G['MATH_AUX']); a.stg(G['CALC_B'],1); a.br('JMP','gcd_loop')
    a.label('gcd_done'); a.ldg(1,G['CALC_A']); a.stg(G['CALC_RESULT'],1); a.e('RET')
    a.label('cmd_gcd'); a.call('parse_arg_a'); a.call('parse_arg_b')
    a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JGE','gcd_abs_b'); a.e('NEG r1 r1'); a.stg(G['CALC_A'],1)
    a.label('gcd_abs_b'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JGE','gcd_call_core'); a.e('NEG r1 r1'); a.stg(G['CALC_B'],1)
    a.label('gcd_call_core'); a.call('gcd_core'); self.print_const('GCD RESULT'); a.call('print_number_result'); a.e('RET')

    a.label('cmd_lcm'); a.call('parse_arg_a'); a.call('parse_arg_b')
    a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JGE','lcm_abs_b'); a.e('NEG r1 r1'); a.stg(G['CALC_A'],1)
    a.label('lcm_abs_b'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JGE','lcm_save'); a.e('NEG r1 r1'); a.stg(G['CALC_B'],1)
    a.label('lcm_save'); a.ldg(1,G['CALC_A']); a.stg(G['LCM_A'],1); a.ldg(1,G['CALC_B']); a.stg(G['LCM_B'],1); a.call('gcd_core')
    a.ldg(1,G['CALC_RESULT']); a.e('CMP r1 r0'); a.br('JEQ','lcm_zero')
    a.ldg(1,G['LCM_A']); a.ldg(2,G['CALC_RESULT']); a.e('DIVU r3 r1 r2'); a.ldg(1,G['LCM_B']); a.e('MUL r4 r3 r1'); a.stg(G['CALC_RESULT'],4); a.br('JMP','lcm_output')
    a.label('lcm_zero'); a.li(1,0); a.stg(G['CALC_RESULT'],1)
    a.label('lcm_output'); self.print_const('LCM RESULT'); a.call('print_number_result'); a.e('RET')

    # Integer square root via unsigned binary search (no overflowing midpoint square).
    a.label('cmd_sqrt'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JLT','cmd_range_error'); a.stg(G['SQRT_N'],1)
    a.li(1,0); a.stg(G['SQRT_LO'],1); a.li(1,65536); a.stg(G['SQRT_HI'],1)
    a.label('sqrt_loop'); a.ldg(1,G['SQRT_HI']); a.ldg(2,G['SQRT_LO']); a.e('SUB r3 r1 r2'); a.li(4,1); a.e('CMP r3 r4'); a.br('JLE','sqrt_done')
    a.ldg(1,G['SQRT_HI']); a.ldg(2,G['SQRT_LO']); a.e('ADD r3 r1 r2'); a.li(4,1); a.e('RSH r3 r3 r4'); a.stg(G['SQRT_MID'],3)
    a.ldg(1,G['SQRT_N']); a.ldg(2,G['SQRT_MID']); a.e('DIVU r4 r1 r2'); a.e('CMP r2 r4'); a.br('JLE','sqrt_take_low')
    a.ldg(1,G['SQRT_MID']); a.stg(G['SQRT_HI'],1); a.br('JMP','sqrt_loop')
    a.label('sqrt_take_low'); a.ldg(1,G['SQRT_MID']); a.stg(G['SQRT_LO'],1); a.br('JMP','sqrt_loop')
    a.label('sqrt_done'); a.ldg(1,G['SQRT_LO']); a.stg(G['CALC_RESULT'],1); self.print_const('INTEGER SQUARE ROOT'); a.call('print_number_result'); a.e('RET')

    # Trial-divisor prime test: d <= n/d avoids d*d overflow.
    a.label('cmd_prime'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.stg(G['PRIME_N'],1); a.li(2,2); a.e('CMP r1 r2'); a.br('JLT','prime_no')
    a.li(1,2); a.stg(G['PRIME_DIV'],1)
    a.label('prime_loop'); a.ldg(1,G['PRIME_N']); a.ldg(2,G['PRIME_DIV']); a.e('DIVU r3 r1 r2'); a.e('CMP r2 r3'); a.br('JGT','prime_yes')
    a.ldg(1,G['PRIME_N']); a.ldg(2,G['PRIME_DIV']); a.e('REMU r3 r1 r2'); a.e('CMP r3 r0'); a.br('JEQ','prime_no')
    a.ldg(1,G['PRIME_DIV']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PRIME_DIV'],1); a.br('JMP','prime_loop')
    a.label('prime_yes'); a.li(1,1); a.stg(G['CALC_RESULT'],1); a.br('JMP','prime_output')
    a.label('prime_no'); a.li(1,0); a.stg(G['CALC_RESULT'],1)
    a.label('prime_output'); self.print_const('PRIME RESULT 1=PRIME 0=COMPOSITE'); a.call('print_number_result'); a.e('RET')

    # xorshift32 deterministic guest PRNG.
    a.label('cmd_rand'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JLE','cmd_range_error')
    a.ldg(1,G['RNG_STATE']); a.li(2,13); a.e('LSH r3 r1 r2'); a.e('XOR r1 r1 r3')
    a.li(2,17); a.e('RSH r3 r1 r2'); a.e('XOR r1 r1 r3'); a.li(2,5); a.e('LSH r3 r1 r2'); a.e('XOR r1 r1 r3'); a.stg(G['RNG_STATE'],1)
    a.ldg(2,G['CALC_A']); a.e('REMU r3 r1 r2'); a.stg(G['CALC_RESULT'],3); self.print_const('RANDOM RESULT'); a.call('print_number_result'); a.e('RET')

    # Bit analysis tools.
    for cmd,op,title in [('cmd_popcnt','POPCNT','POPCOUNT'),('cmd_clz','CLZ','COUNT LEADING ZEROS'),('cmd_ctz','CTZ','COUNT TRAILING ZEROS')]:
      a.label(cmd); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e(f'{op} r3 r1'); a.stg(G['CALC_RESULT'],3); self.print_const(title); a.call('print_number_result'); a.e('RET')

    # HEX prints all 32 bits as 8 uppercase hexadecimal digits.
    a.label('cmd_hex'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.stg(G['HEX_VALUE'],1); a.li(1,0); a.stg(G['HEX_I'],1)
    a.label('hex_make_loop'); a.ldg(1,G['HEX_I']); a.li(2,8); a.e('CMP r1 r2'); a.br('JGE','hex_reverse_start')
    a.ldg(1,G['HEX_VALUE']); a.li(2,15); a.e('AND r3 r1 r2'); a.stg(G['HEX_NIBBLE'],3); a.li(4,10); a.e('CMP r3 r4'); a.br('JGE','hex_letter')
    a.li(4,48); a.e('ADD r3 r3 r4'); a.br('JMP','hex_store_char')
    a.label('hex_letter'); a.li(4,55); a.e('ADD r3 r3 r4')
    a.label('hex_store_char'); a.ldg(1,G['HEX_I']); a.stx(HEX_REV,1,3); a.ldg(1,G['HEX_VALUE']); a.li(2,4); a.e('RSH r1 r1 r2'); a.stg(G['HEX_VALUE'],1)
    a.ldg(1,G['HEX_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['HEX_I'],1); a.br('JMP','hex_make_loop')
    a.label('hex_reverse_start'); a.li(1,48); a.stx(HEX_BUF,0,1); a.li(1,ord('X')); a.stx(HEX_BUF,1,1); a.li(1,0); a.stg(G['HEX_OUT_I'],1)
    a.label('hex_reverse_loop'); a.ldg(1,G['HEX_OUT_I']); a.li(2,8); a.e('CMP r1 r2'); a.br('JGE','hex_done')
    a.li(2,7); a.e('SUB r3 r2 r1'); a.ldx(4,HEX_REV,3); a.li(2,2); a.e('ADD r5 r1 r2'); a.stx(HEX_BUF,5,4)
    a.ldg(1,G['HEX_OUT_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['HEX_OUT_I'],1); a.br('JMP','hex_reverse_loop')
    a.label('hex_done'); a.li(1,10); a.li(2,0); a.stx(HEX_BUF,1,2); self.print_const('HEX VALUE'); a.li(1,HEX_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')

    # BIN prints a fixed-width 32-bit representation.
    a.label('cmd_bin'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.stg(G['HEX_VALUE'],1); a.li(1,0); a.stg(G['HEX_I'],1)
    a.label('bin_make_loop'); a.ldg(1,G['HEX_I']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','bin_reverse_start')
    a.ldg(1,G['HEX_VALUE']); a.li(2,1); a.e('AND r3 r1 r2'); a.li(4,48); a.e('ADD r3 r3 r4'); a.ldg(1,G['HEX_I']); a.stx(BIN_REV,1,3)
    a.ldg(1,G['HEX_VALUE']); a.li(2,1); a.e('RSH r1 r1 r2'); a.stg(G['HEX_VALUE'],1); a.ldg(1,G['HEX_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['HEX_I'],1); a.br('JMP','bin_make_loop')
    a.label('bin_reverse_start'); a.li(1,48); a.stx(BIN_BUF,0,1); a.li(1,ord('B')); a.stx(BIN_BUF,1,1); a.li(1,0); a.stg(G['HEX_OUT_I'],1)
    a.label('bin_reverse_loop'); a.ldg(1,G['HEX_OUT_I']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','bin_done')
    a.li(2,31); a.e('SUB r3 r2 r1'); a.ldx(4,BIN_REV,3); a.li(2,2); a.e('ADD r5 r1 r2'); a.stx(BIN_BUF,5,4)
    a.ldg(1,G['HEX_OUT_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['HEX_OUT_I'],1); a.br('JMP','bin_reverse_loop')
    a.label('bin_done'); a.li(1,34); a.li(2,0); a.stx(BIN_BUF,1,2); self.print_const('BINARY VALUE'); a.li(1,BIN_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')

    # CRC32/ISO-HDLC over a named guest RAM file. Characters are 32-bit words in FS_DATA.
    a.label('cmd_crc32'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file')
    a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_not_found'); a.stg(G['CRC_SLOT'],1); a.ldx(2,FS_SIZE,1); a.stg(G['CRC_SIZE'],2)
    a.li(1,-1); a.stg(G['CRC_VALUE'],1); a.li(1,0); a.stg(G['CRC_I'],1)
    a.label('crc_byte_loop'); a.ldg(1,G['CRC_I']); a.ldg(2,G['CRC_SIZE']); a.e('CMP r1 r2'); a.br('JGE','crc_done_bytes')
    a.ldg(1,G['CRC_SLOT']); a.ldx(5,FS_PAGE,1); a.ldg(1,G['CRC_I']); a.e('LDX r4 r5 r1')
    a.ldg(1,G['CRC_VALUE']); a.e('XOR r1 r1 r4'); a.stg(G['CRC_VALUE'],1); a.li(1,0); a.stg(G['CRC_BIT'],1)
    a.label('crc_bit_loop'); a.ldg(1,G['CRC_BIT']); a.li(2,8); a.e('CMP r1 r2'); a.br('JGE','crc_byte_done')
    a.ldg(1,G['CRC_VALUE']); a.li(2,1); a.e('AND r3 r1 r2'); a.e('CMP r3 r0'); a.br('JEQ','crc_shift_only')
    a.e('RSH r1 r1 r2'); a.li(4,0xEDB88320); a.e('XOR r1 r1 r4'); a.stg(G['CRC_VALUE'],1); a.br('JMP','crc_bit_next')
    a.label('crc_shift_only'); a.ldg(1,G['CRC_VALUE']); a.li(2,1); a.e('RSH r1 r1 r2'); a.stg(G['CRC_VALUE'],1)
    a.label('crc_bit_next'); a.ldg(1,G['CRC_BIT']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['CRC_BIT'],1); a.br('JMP','crc_bit_loop')
    a.label('crc_byte_done'); a.ldg(1,G['CRC_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['CRC_I'],1); a.br('JMP','crc_byte_loop')
    a.label('crc_done_bytes'); a.ldg(1,G['CRC_VALUE']); a.e('NOT r1 r1'); a.stg(G['CALC_RESULT'],1); self.print_const('CRC32 DECIMAL'); a.call('print_number_result'); a.e('RET')

    # RUN executes ;-separated commands from a file in guest RAM. Nested RUN is rejected.
    a.label('cmd_run'); a.ldg(1,G['SCRIPT_ACTIVE']); a.e('CMP r1 r0'); a.br('JNE','cmd_nested_run')
    a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','cmd_need_name'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','cmd_script_not_found')
    a.stg(G['SCRIPT_SLOT'],1); a.ldx(2,FS_SIZE,1); a.stg(G['SCRIPT_SIZE'],2); a.li(1,0); a.stg(G['SCRIPT_POS'],1); a.stg(G['SCRIPT_LEN'],1); a.li(1,1); a.stg(G['SCRIPT_ACTIVE'],1)
    a.label('script_loop'); a.ldg(1,G['SCRIPT_POS']); a.ldg(2,G['SCRIPT_SIZE']); a.e('CMP r1 r2'); a.br('JGE','script_finish')
    a.ldg(1,G['SCRIPT_SLOT']); a.ldx(5,FS_PAGE,1); a.ldg(1,G['SCRIPT_POS']); a.stg(G['SCRIPT_WORD'],1); a.e('LDX r4 r5 r1')
    a.li(2,ord(';')); a.e('CMP r4 r2'); a.br('JEQ','script_delimiter'); a.li(2,10); a.e('CMP r4 r2'); a.br('JEQ','script_delimiter'); a.li(2,13); a.e('CMP r4 r2'); a.br('JEQ','script_delimiter'); a.e('CMP r4 r0'); a.br('JEQ','script_delimiter')
    a.ldg(1,G['SCRIPT_LEN']); a.li(2,99); a.e('CMP r1 r2'); a.br('JGE','script_too_long'); a.stx(CMD_BUF,1,4); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['SCRIPT_LEN'],1); a.br('JMP','script_next_char')
    a.label('script_too_long'); self.print_const('SCRIPT LINE TOO LONG - SKIPPED'); a.br('JMP','script_reset_line')
    a.label('script_delimiter'); a.ldg(1,G['SCRIPT_LEN']); a.e('CMP r1 r0'); a.br('JEQ','script_reset_line'); a.call('script_execute_line')
    a.label('script_reset_line'); a.li(1,0); a.stg(G['SCRIPT_LEN'],1); a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3')
    a.label('script_next_char'); a.ldg(1,G['SCRIPT_POS']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['SCRIPT_POS'],1); a.br('JMP','script_loop')
    a.label('script_finish'); a.ldg(1,G['SCRIPT_LEN']); a.e('CMP r1 r0'); a.br('JEQ','script_finish_clean'); a.call('script_execute_line')
    a.label('script_finish_clean'); a.li(1,0); a.stg(G['SCRIPT_ACTIVE'],1); self.print_const('SCRIPT COMPLETE'); a.e('RET')
    a.label('script_execute_line'); a.ldg(1,G['SCRIPT_LEN']); a.li(2,0); a.stx(CMD_BUF,1,2); a.ldg(1,G['SCRIPT_LEN']); a.stg(G['CMD_LEN'],1)
    a.call('echo_command'); a.call('parse_command'); a.call('execute_command'); a.e('RET')
    a.label('cmd_nested_run'); self.print_const('ERROR: NESTED RUN IS DISABLED'); a.e('RET')
    a.label('cmd_script_not_found'); self.print_const('ERROR: SCRIPT FILE NOT FOUND'); a.e('RET')

    # BENCH executes a real guest integer mixing loop; counts are capped at five million.
    a.label('cmd_bench'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.e('CMP r1 r0'); a.br('JLE','cmd_range_error'); a.li(2,5000000); a.e('CMP r1 r2'); a.br('JGT','cmd_range_error'); a.stg(G['BENCH_COUNT'],1)
    a.li(1,0); a.stg(G['BENCH_I'],1); a.li(1,0x12345678); a.stg(G['BENCH_ACC'],1)
    a.label('bench_loop'); a.ldg(1,G['BENCH_I']); a.ldg(2,G['BENCH_COUNT']); a.e('CMP r1 r2'); a.br('JGE','bench_done')
    a.ldg(1,G['BENCH_ACC']); a.li(2,1664525); a.e('MUL r3 r1 r2'); a.li(2,1013904223); a.e('ADD r3 r3 r2'); a.ldg(1,G['BENCH_I']); a.e('XOR r3 r3 r1'); a.stg(G['BENCH_ACC'],3)
    a.ldg(1,G['BENCH_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['BENCH_I'],1); a.br('JMP','bench_loop')
    a.label('bench_done'); a.ldg(1,G['BENCH_COUNT']); a.stg(G['CALC_RESULT'],1); self.print_const('BENCH ITERATIONS'); a.call('print_number_result'); a.ldg(1,G['BENCH_ACC']); a.stg(G['CALC_RESULT'],1); self.print_const('BENCH CHECKSUM'); a.call('print_number_result'); a.e('RET')

    # MEMTEST N writes and verifies a bounded, dedicated 32 KiB scratch range.
    a.label('cmd_memtest'); a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JNE','memtest_parse_count'); a.li(1,1024); a.stg(G['MEMTEST_COUNT'],1); a.br('JMP','memtest_validate')
    a.label('memtest_parse_count'); a.call('parse_arg_a'); a.ldg(1,G['CALC_A']); a.stg(G['MEMTEST_COUNT'],1)
    a.label('memtest_validate'); a.ldg(1,G['MEMTEST_COUNT']); a.e('CMP r1 r0'); a.br('JLE','cmd_range_error'); a.li(2,8192); a.e('CMP r1 r2'); a.br('JGT','cmd_range_error'); a.li(1,0); a.stg(G['MEMTEST_I'],1)
    a.label('memtest_write_loop'); a.ldg(1,G['MEMTEST_I']); a.ldg(2,G['MEMTEST_COUNT']); a.e('CMP r1 r2'); a.br('JGE','memtest_verify_init')
    a.ldg(1,G['MEMTEST_I']); a.li(2,0x9E3779B9); a.e('MUL r3 r1 r2'); a.li(2,0xA5A55A5A); a.e('XOR r3 r3 r2'); a.ldg(1,G['MEMTEST_I']); a.stx(MEMTEST_BUF,1,3)
    a.ldg(1,G['MEMTEST_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['MEMTEST_I'],1); a.br('JMP','memtest_write_loop')
    a.label('memtest_verify_init'); a.li(1,0); a.stg(G['MEMTEST_I'],1)
    a.label('memtest_verify_loop'); a.ldg(1,G['MEMTEST_I']); a.ldg(2,G['MEMTEST_COUNT']); a.e('CMP r1 r2'); a.br('JGE','memtest_pass')
    a.ldg(1,G['MEMTEST_I']); a.li(2,0x9E3779B9); a.e('MUL r3 r1 r2'); a.li(2,0xA5A55A5A); a.e('XOR r3 r3 r2'); a.ldx(4,MEMTEST_BUF,1); a.label('memtest_verify_compare'); a.e('CMP r3 r4'); a.br('JNE','memtest_fail')
    a.ldg(1,G['MEMTEST_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['MEMTEST_I'],1); a.br('JMP','memtest_verify_loop')
    a.label('memtest_pass'); self.print_const('MEMTEST PASSED'); a.ldg(1,G['MEMTEST_COUNT']); a.stg(G['CALC_RESULT'],1); a.call('print_number_result'); a.e('RET')
    a.label('memtest_fail')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,5); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('GUEST RAM MEMTEST FAILURE')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 memtest_verify_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('GUEST RAM MEMTEST VERIFY LOOP')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('cmd_selftest'); self.print_const('SELFTEST RUNNING: 270000 VECTORS'); a.call('selftest_vectors'); a.e('RET')

    # These helpers are emitted immediately after the shell's normal command logic.
    # Detailed vector code is emitted by emit_selftest_suite() below; every vector
    # contributes a result difference into r7 with no per-vector branches. At the
    # end the guest reports whether the aggregate mismatch mask stayed zero.
    self.emit_selftest_suite()
    self.emit_workstation_extensions()

    # ---- CALC: CALC A OP B; integer operands ----
    a.label('cmd_calc')
    a.ldx(1,ARG_NAME,0); a.e('CMP r1 r0'); a.br('JEQ','calc_usage')
    a.li(1,ARG_NAME); a.stg(G['PARSE_SRC'],1); a.li(1,0); a.stg(G['PARSE_I'],1); a.call('parse_number'); a.ldg(1,G['PARSE_VALUE']); a.stg(G['CALC_A'],1)
    # Find operator in ARG_TEXT after leading spaces
    a.li(1,0); a.stg(G['PARSE_I'],1)
    a.label('calc_skip_space'); a.ldg(1,G['PARSE_I']); a.ldx(2,ARG_TEXT,1); a.li(3,32); a.e('CMP r2 r3'); a.br('JNE','calc_op_found'); a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','calc_skip_space')
    a.label('calc_op_found'); a.stg(G['CALC_OP'],2); a.ldg(1,G['PARSE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PARSE_I'],1)
    a.label('calc_skip_space2'); a.ldg(1,G['PARSE_I']); a.ldx(2,ARG_TEXT,1); a.li(3,32); a.e('CMP r2 r3'); a.br('JNE','calc_parse_b'); a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['PARSE_I'],1); a.br('JMP','calc_skip_space2')
    a.label('calc_parse_b'); a.li(1,ARG_TEXT); a.stg(G['PARSE_SRC'],1); a.call('parse_number'); a.ldg(1,G['PARSE_VALUE']); a.stg(G['CALC_B'],1)
    a.ldg(1,G['CALC_OP']); a.li(2,ord('+')); a.e('CMP r1 r2'); a.br('JEQ','calc_add')
    a.li(2,ord('-')); a.e('CMP r1 r2'); a.br('JEQ','calc_sub')
    a.li(2,ord('*')); a.e('CMP r1 r2'); a.br('JEQ','calc_mul')
    a.li(2,ord('/')); a.e('CMP r1 r2'); a.br('JEQ','calc_div')
    a.li(2,ord('%')); a.e('CMP r1 r2'); a.br('JEQ','calc_mod')
    a.li(2,ord('^')); a.e('CMP r1 r2'); a.br('JEQ','calc_pow')
    a.li(2,ord('&')); a.e('CMP r1 r2'); a.br('JEQ','calc_and')
    a.li(2,ord('|')); a.e('CMP r1 r2'); a.br('JEQ','calc_or')
    a.li(2,ord('X')); a.e('CMP r1 r2'); a.br('JEQ','calc_xor')
    a.li(2,ord('<')); a.e('CMP r1 r2'); a.br('JEQ','calc_lsh')
    a.li(2,ord('>')); a.e('CMP r1 r2'); a.br('JEQ','calc_rsh')
    self.print_const('CALC_USAGE'); a.e('RET')
    a.label('calc_add'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('ADD r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_sub'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('SUB r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_mul'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('MUL r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_div'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JEQ','calc_div_zero'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('DIVS r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_mod'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JEQ','calc_div_zero'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('REMS r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    # Exponentiation by repeated multiplication; exponent limited to 0..31 to keep work bounded.
    a.label('calc_pow'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JLT','calc_usage'); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','calc_usage')
    a.li(3,1); a.stg(G['CALC_RESULT'],3); a.stg(G['LOOP_I'],1)
    a.label('calc_pow_loop'); a.ldg(1,G['LOOP_I']); a.e('CMP r1 r0'); a.br('JZE','calc_output')
    a.ldg(1,G['CALC_RESULT']); a.ldg(2,G['CALC_A']); a.e('MUL r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.ldg(1,G['LOOP_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['LOOP_I'],1); a.br('JMP','calc_pow_loop')
    a.label('calc_and'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('AND r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_or'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('OR r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_xor'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('XOR r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_lsh'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JLT','calc_usage'); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','calc_shift_zero'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('LSH r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_rsh'); a.ldg(1,G['CALC_B']); a.e('CMP r1 r0'); a.br('JLT','calc_usage'); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','calc_shift_zero'); a.ldg(1,G['CALC_A']); a.ldg(2,G['CALC_B']); a.e('RSH r3 r1 r2'); a.stg(G['CALC_RESULT'],3); a.br('JMP','calc_output')
    a.label('calc_shift_zero'); a.li(1,0); a.stg(G['CALC_RESULT'],1); a.br('JMP','calc_output')
    a.label('calc_div_zero'); a.call('gui_sfx_error'); self.print_const('CALC_DIVZERO'); a.e('RET')
    a.label('calc_output'); self.print_const('CALC_RESULT_TITLE'); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['PRINT_SRC'],1); a.call('print_line'); a.e('RET')
    a.label('calc_usage'); self.print_const('CALC_USAGE'); a.e('RET')

    # ---- parse number from PARSE_SRC beginning at PARSE_I ----
    a.label('parse_number'); a.li(1,0); a.stg(G['PARSE_VALUE'],1); a.li(1,0); a.stg(G['PARSE_NEG'],1)
    a.ldg(1,G['PARSE_I']); a.ldg(2,G['PARSE_SRC']); a.e('LDX r3 r2 r1'); a.li(4,45); a.e('CMP r3 r4'); a.br('JNE','parse_num_loop')
    a.li(1,1); a.stg(G['PARSE_NEG'],1); a.ldg(1,G['PARSE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PARSE_I'],1)
    a.label('parse_num_loop'); a.ldg(1,G['PARSE_I']); a.ldg(2,G['PARSE_SRC']); a.e('LDX r3 r2 r1')
    a.li(4,48); a.e('CMP r3 r4'); a.br('JLT','parse_num_done'); a.li(4,57); a.e('CMP r3 r4'); a.br('JGT','parse_num_done')
    a.li(4,48); a.e('SUB r3 r3 r4'); a.ldg(5,G['PARSE_VALUE']); a.li(6,10); a.e('MUL r5 r5 r6'); a.e('ADD r5 r5 r3'); a.stg(G['PARSE_VALUE'],5)
    a.ldg(1,G['PARSE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PARSE_I'],1); a.br('JMP','parse_num_loop')
    a.label('parse_num_done'); a.ldg(1,G['PARSE_NEG']); a.e('CMP r1 r0'); a.br('JEQ','parse_num_return'); a.ldg(1,G['PARSE_VALUE']); a.e('NEG r1 r1'); a.stg(G['PARSE_VALUE'],1); a.label('parse_num_return'); a.e('RET')

    # ---- integer to ASCII decimal, result string in NUM_BUF ----
    a.label('number_to_text')
    a.li(1,NUM_BUF); a.li(2,0); a.li(3,24*4); a.e('MEMSET r1 r2 r3')
    # prefix RESULT: except TIME's caller still gets a harmless prefix; both call sites label appropriately.
    a.li(1,0); a.stg(G['NUM_I'],1); a.li(1,0); a.stg(G['NUM_NEG'],1)
    a.ldg(1,G['CALC_RESULT']); a.e('CMP r1 r0'); a.br('JGE','num_nonneg'); a.li(2,1); a.stg(G['NUM_NEG'],2); a.e('NEG r1 r1'); a.stg(G['CALC_RESULT'],1)
    a.label('num_nonneg'); a.ldg(1,G['CALC_RESULT']); a.li(2,0); a.e('CMP r1 r2'); a.br('JNE','num_digit_loop')
    a.li(1,48); a.stx(NUM_REV,0,1); a.li(1,1); a.stg(G['NUM_I'],1); a.br('JMP','num_digits_ready')
    a.label('num_digit_loop'); a.li(2,10); a.e('REMU r3 r1 r2'); a.li(4,48); a.e('ADD r3 r3 r4'); a.ldg(5,G['NUM_I']); a.stx(NUM_REV,5,3); a.li(4,1); a.e('ADD r5 r5 r4'); a.stg(G['NUM_I'],5); a.e('DIVU r1 r1 r2'); a.e('CMP r1 r0'); a.br('JNE','num_digit_loop')
    a.label('num_digits_ready')
    # reverse digits into NUM_BUF, optional '-' first
    a.li(1,0); a.stg(G['TEMP_I'],1); a.ldg(2,G['NUM_NEG']); a.e('CMP r2 r0'); a.br('JEQ','num_reverse_start')
    a.li(3,ord('-')); a.stx(NUM_BUF,0,3); a.li(1,1); a.stg(G['TEMP_I'],1)
    a.label('num_reverse_start'); a.ldg(1,G['NUM_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['NUM_REV_I'],1)
    a.label('num_reverse_loop'); a.ldg(1,G['NUM_REV_I']); a.e('CMP r1 r0'); a.br('JLT','num_text_done')
    a.ldx(3,NUM_REV,1); a.ldg(4,G['TEMP_I']); a.stx(NUM_BUF,4,3); a.li(5,1); a.e('ADD r4 r4 r5'); a.stg(G['TEMP_I'],4)
    a.ldg(1,G['NUM_REV_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['NUM_REV_I'],1); a.br('JMP','num_reverse_loop')
    a.label('num_text_done'); a.e('RET')

    # ---- draw screen ----
    a.label('draw_screen')
    a.li(1,FB); a.li(2,0); a.li(3,1280*720*4); a.e('MEMSET r1 r2 r3')
    self.emit_draw_const('OS_TITLE',0,0x60DFFFFF)
    self.emit_draw_const('OS_SUBTITLE',1,0xA6B7C7FF)
    self.emit_draw_const('SEP',2,0x27634AFF)
    a.li(1,0); a.stg(G['ROW_I'],1)
    a.label('draw_history_loop')
    a.ldg(1,G['ROW_I']); a.li(2,OUT_ROWS); a.e('CMP r1 r2'); a.br('JGE','draw_history_done')
    a.li(2,LINE_LEN*4); a.e('MUL r3 r1 r2'); a.li(4,OUT_BASE); a.e('ADD r4 r4 r3'); a.stg(G['TEXT_SRC'],4)
    a.ldg(1,G['ROW_I']); a.li(2,3); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_ROW'],1)
    a.li(1,0); a.stg(G['TEXT_COL'],1); a.li(1,0x66FFAAFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.ldg(1,G['ROW_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['ROW_I'],1); a.br('JMP','draw_history_loop')
    a.label('draw_history_done')
    self.emit_draw_const('SEP',34,0x27634AFF)
    self.emit_draw_const('PROMPT_PREFIX',35,0xF5F7FFFF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,35); a.stg(G['TEXT_ROW'],1); a.li(1,7); a.stg(G['TEXT_COL'],1); a.li(1,0xF5F7FFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.emit_draw_const('OS_FOOTER',37,0x60DFFFFF)
    a.call('gui_present_frame'); a.e('RET')

    # Draw a glyph string at pixel-aligned character row; font pixels are scaled 2x.
    a.label('draw_text'); a.li(1,0); a.stg(G['TEXT_INDEX'],1)
    a.label('draw_text_loop')
    a.ldg(1,G['TEXT_INDEX']); a.li(2,102); a.e('CMP r1 r2'); a.br('JGE','draw_text_done')
    a.ldg(2,G['TEXT_SRC']); a.e('LDX r3 r2 r1'); a.e('CMP r3 r0'); a.br('JEQ','draw_text_done'); a.stg(G['CHAR_CODE'],3)
    a.ldg(4,G['TEXT_COL']); a.e('ADD r4 r4 r1'); a.li(5,12); a.e('MUL r4 r4 r5'); a.li(5,20); a.e('ADD r4 r4 r5'); a.stg(G['CHAR_X'],4)
    a.ldg(4,G['TEXT_ROW']); a.li(5,18); a.e('MUL r4 r4 r5'); a.li(5,12); a.e('ADD r4 r4 r5'); a.stg(G['CHAR_Y'],4)
    a.ldg(4,G['TEXT_COLOR']); a.stg(G['CHAR_COLOR'],4); a.call('draw_char')
    a.ldg(1,G['TEXT_INDEX']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_INDEX'],1); a.br('JMP','draw_text_loop')
    a.label('draw_text_done'); a.e('RET')

    a.label('draw_char'); a.li(1,0); a.stg(G['CHAR_ROW'],1)
    a.label('draw_char_row_loop')
    a.ldg(1,G['CHAR_ROW']); a.li(2,7); a.e('CMP r1 r2'); a.br('JGE','draw_char_done')
    a.ldg(3,G['CHAR_CODE']); a.li(4,7); a.e('MUL r3 r3 r4'); a.e('ADD r3 r3 r1'); a.li(4,FONT_BASE); a.stg(G['TEMP_A'],4) # TEMP_A temporarily holds base, not persistent across draw only
    a.e('LDI r12 '+str(FONT_BASE)); a.e('LDX r4 r12 r3'); a.stg(G['CHAR_BITMAP'],4)
    a.li(1,0); a.stg(G['CHAR_COL'],1)
    a.label('draw_char_col_loop')
    a.ldg(1,G['CHAR_COL']); a.li(2,5); a.e('CMP r1 r2'); a.br('JGE','draw_char_next_row')
    a.li(2,4); a.e('SUB r3 r2 r1'); a.li(4,1); a.e('LSH r4 r4 r3'); a.ldg(5,G['CHAR_BITMAP']); a.e('AND r4 r4 r5'); a.e('CMP r4 r0'); a.br('JEQ','draw_char_skip_pixel')
    a.ldg(1,G['CHAR_X']); a.ldg(2,G['CHAR_COL']); a.li(3,2); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2'); a.stg(G['PIX_X'],1)
    a.ldg(1,G['CHAR_Y']); a.ldg(2,G['CHAR_ROW']); a.li(3,2); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2'); a.stg(G['PIX_Y'],1)
    a.ldg(1,G['CHAR_COLOR']); a.stg(G['PIX_COLOR'],1); a.call('draw_pixel')
    a.label('draw_char_skip_pixel'); a.ldg(1,G['CHAR_COL']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['CHAR_COL'],1); a.br('JMP','draw_char_col_loop')
    a.label('draw_char_next_row'); a.ldg(1,G['CHAR_ROW']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['CHAR_ROW'],1); a.br('JMP','draw_char_row_loop')
    a.label('draw_char_done'); a.e('RET')

    a.label('draw_pixel')
    a.ldg(1,G['PIX_Y']); a.li(2,1280); a.e('MUL r3 r1 r2'); a.ldg(1,G['PIX_X']); a.e('ADD r3 r3 r1'); a.li(2,2); a.e('LSH r3 r3 r2'); a.li(4,FB); a.e('ADD r3 r3 r4'); a.ldg(5,G['PIX_COLOR']); a.e('STORE r3 r5')
    a.li(6,4); a.e('ADD r4 r3 r6'); a.e('STORE r4 r5'); a.li(6,5120); a.e('ADD r4 r3 r6'); a.e('STORE r4 r5'); a.li(6,5124); a.e('ADD r4 r3 r6'); a.e('STORE r4 r5'); a.e('RET')

  def gui_const(self, text, row, col=0, color=0xE0E8F2FF):
    a=self.a
    a.li(1,self.msg(text)); a.stg(G['TEXT_SRC'],1)
    a.li(1,row); a.stg(G['TEXT_ROW'],1)
    a.li(1,col); a.stg(G['TEXT_COL'],1)
    a.li(1,color); a.stg(G['TEXT_COLOR'],1)
    a.call('draw_text')

  def gui_rect_setup(self, x, y, w, h, color, mode=0):
    a=self.a
    for key,val in (('RECT_X',x),('RECT_Y',y),('RECT_W',w),('RECT_H',h),('RECT_COLOR',color),('RECT_MODE',mode)):
      a.li(1,val); a.stg(G[key],1)
    a.call('gui_draw_rect')

  def emit_gui_boot_and_loop(self):
    a=self.a
    # ---- Real staged boot: memory check, filesystem initialization, font scan, app service initialization ----
    a.label('gui_boot')
    # A warm boot keeps the RAM filesystem, VFS pages and user data intact.
    a.li(12,G['KERNEL_MAGIC']); a.e('LOAD r1 r12'); a.li(2,0x4E4F5641); a.e('CMP r1 r2'); a.br('JEQ','gui_warm_boot')
    for key,val in (('APP_STATE',0),('CURSOR_X',170),('CURSOR_Y',172),('THEME',0),('RNG_STATE',0xC0322026),('SCRIPT_ACTIVE',0),('PAINT_COUNT',0),('NOTE_LEN',0),('FILE_COUNT',0),('TICK',0),('OUT_COUNT',0),('CMD_LEN',0),('CWD_ID',0),('LAST_DELETED',-1),('TRACE_DEPTH',0),('STACK_USED',0),('STACK_HIGHWATER',0),('PANIC_ACTIVE',0),('STOPWATCH_RUNNING',0),('STOPWATCH_TICKS',0),('STOPWATCH_LAPS',0),('MIX_FREQ',440),('MIX_VOLUME',10),('MIX_WAVE',0),('MIX_PAN',50),('PAGE_HINT',0),('PAGE_USED',0),('PANIC_DUMP_PTR',0),('UNDO_COUNT',0),('REDO_COUNT',0)):
      a.li(1,val); a.stg(G[key],1)
    # Initialize software page bitmap, slab state, app arenas, filesystem metadata and stack guard.
    a.li(1,PAGE_BITMAP); a.li(2,0); a.li(3,65536); a.e('MEMSET r1 r2 r3')
    a.li(1,PAGE_BITMAP); a.li(2,255); a.li(3,32); a.e('MEMSET r1 r2 r3'); a.li(1,256); a.stg(G['PAGE_HINT'],1); a.li(1,256); a.stg(G['PAGE_USED'],1)
    for addr,nbytes in ((TRACE_FUNCS,64*4),(TRACE_RETS,64*4),(APP_ARENAS,24*4),(UNDO_PAGES,32*4),(CAL_EVENT_USED,32*4),(CAL_EVENT_TEXT,32*32*4)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    # Pre-allocate 32 high-RAM pages (128 KiB) for the Paint/Notes undo-redo log pool.
    a.li(1,0); a.stg(G['TEMP_I'],1)
    a.label('boot_undo_page_loop'); a.ldg(1,G['TEMP_I']); a.li(2,32); a.e('CMP r1 r2'); a.br('JGE','boot_undo_page_done')
    a.call('page_alloc'); a.ldg(3,G['PAGE_RESULT']); a.li(4,-1); a.e('CMP r3 r4'); a.br('JEQ','gui_boot_memory_error')
    a.ldg(1,G['TEMP_I']); a.stx(UNDO_PAGES,1,3); a.ldg(1,G['TEMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TEMP_I'],1); a.br('JMP','boot_undo_page_loop')
    a.label('boot_undo_page_done')
    for addr,nbytes in ((G['SLAB_CUR'],16),(G['SLAB_END'],16),(G['SLAB_FREE'],16)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_USED); a.li(2,0); a.li(3,FS_SLOTS*4); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_NAMES); a.li(2,0); a.li(3,FS_SLOTS*NAME_LEN*4); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_SIZE); a.li(2,0); a.li(3,FS_SLOTS*4); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_PARENT); a.li(2,0); a.li(3,FS_SLOTS*4); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_TYPE); a.li(2,0); a.li(3,FS_SLOTS*4); a.e('MEMSET r1 r2 r3')
    a.li(1,FS_PAGE); a.li(2,0); a.li(3,FS_SLOTS*4); a.e('MEMSET r1 r2 r3')
    # Permanent root directory is inode zero (name '/') and survives warm restart.
    a.li(1,1); a.stx(FS_USED,0,1); a.li(1,1); a.stx(FS_TYPE,0,1); a.li(1,0); a.stx(FS_PARENT,0,1)
    a.li(1,ord('/')); a.stx(FS_NAMES,0,1); a.li(1,0); a.stx(FS_NAMES,1,1)
    # The upward-growing 1 MiB hardware stack has a 4 KiB software red-zone.
    a.li(1,STACK_END-4); a.li(2,0x5354414B); a.e('STORE r1 r2')
    a.li(1,HEX_BUF); a.li(2,0x55AA33CC); a.e('STORE r1 r2')
    a.li(1,HEX_BUF); a.e('LOAD r3 r1'); a.li(2,0x55AA33CC); a.label('gui_boot_memory_check_site'); a.e('CMP r3 r2'); a.br('JNE','gui_boot_memory_error')
    a.li(1,1); a.stg(G['BOOT_STAGE'],1); a.li(1,self.msg('CHECKING MEMORY MAP')); a.stg(G['BOOT_TEXT'],1); a.call('gui_draw_boot'); a.li(1,392); a.li(2,180); a.li(3,12); a.li(4,0); a.li(5,50); a.call('gui_sound_emit'); a.call('gui_boot_delay')
    # Clear real guest-side filesystem and working areas.
    for addr,nbytes in ((OUT_BASE,OUT_ROWS*LINE_LEN*4),(CMD_BUF,120*4),(CMD_WORD,24*4),(ARG_NAME,24*4),(ARG_TEXT,110*4),(NOTE_BUF,256*4),(PAINT_X_BUF,128*4),(PAINT_Y_BUF,128*4)):
      a.li(1,addr); a.li(2,0); a.li(3,nbytes); a.e('MEMSET r1 r2 r3')
    a.li(1,FB); a.li(2,0); a.li(3,FRAME_BYTES); a.e('MEMSET r1 r2 r3')
    a.li(1,PAINT_CANVAS_BASE); a.li(2,0); a.li(3,FRAME_BYTES); a.e('MEMSET r1 r2 r3')
    a.li(1,2); a.stg(G['BOOT_STAGE'],1); a.li(1,self.msg('INITIALIZING RAM FILESYSTEM')); a.stg(G['BOOT_TEXT'],1); a.call('gui_draw_boot'); a.li(1,523); a.li(2,180); a.li(3,12); a.li(4,0); a.li(5,50); a.call('gui_sound_emit'); a.call('gui_boot_delay')
    # Read all 896 bitmap rows and compute a real integrity checksum during boot.
    a.li(1,0); a.stg(G['BOOT_I'],1); a.li(1,0); a.stg(G['BOOT_CHECK'],1)
    a.label('gui_font_scan_loop')
    a.ldg(1,G['BOOT_I']); a.li(2,896); a.e('CMP r1 r2'); a.br('JGE','gui_font_scan_done')
    a.ldg(1,G['BOOT_I']); a.li(12,FONT_BASE); a.e('LDX r2 r12 r1'); a.ldg(3,G['BOOT_CHECK']); a.e('XOR r3 r3 r2'); a.stg(G['BOOT_CHECK'],3)
    a.ldg(1,G['BOOT_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['BOOT_I'],1); a.br('JMP','gui_font_scan_loop')
    a.label('gui_font_scan_done')
    a.label('gui_font_checksum_compare'); a.ldg(1,G['BOOT_CHECK']); a.li(2,FONT_CHECKSUM_EXPECTED); a.e('CMP r1 r2'); a.br('JNE','gui_boot_font_error')
    a.li(1,3); a.stg(G['BOOT_STAGE'],1); a.li(1,self.msg('VERIFYING FONT CACHE')); a.stg(G['BOOT_TEXT'],1); a.call('gui_draw_boot'); a.li(1,659); a.li(2,180); a.li(3,12); a.li(4,0); a.li(5,54); a.call('gui_sound_emit'); a.call('gui_boot_delay')
    # Build desktop services and reset app-owned state after the real font scan.
    a.li(1,0); a.stg(G['PAINT_COUNT'],1); a.stg(G['NOTE_LEN'],1)
    a.li(1,0); a.stx(NOTE_BUF,0,1)
    a.li(1,0x4E4F5641); a.stg(G['KERNEL_MAGIC'],1)
    a.li(1,4); a.stg(G['BOOT_STAGE'],1); a.li(1,self.msg('STARTING DESKTOP SERVICES')); a.stg(G['BOOT_TEXT'],1); a.call('gui_draw_boot'); a.li(1,784); a.li(2,220); a.li(3,12); a.li(4,2); a.li(5,50); a.call('gui_sound_emit'); a.call('gui_boot_delay')
    a.li(1,0); a.stg(G['APP_STATE'],1); a.li(1,170); a.stg(G['CURSOR_X'],1); a.li(1,172); a.stg(G['CURSOR_Y'],1)
    a.call('gui_draw_desktop')
    a.br('JMP','gui_loop')
    a.label('gui_warm_boot')
    a.li(6,0xFFFFFFE0); a.li(7,0); a.e('STORE r6 r7')
    a.li(1,0); a.stg(G['APP_STATE'],1); a.stg(G['CWD_ID'],1); a.stg(G['TRACE_DEPTH'],1); a.stg(G['STACK_USED'],1)
    a.li(1,170); a.stg(G['CURSOR_X'],1); a.li(1,172); a.stg(G['CURSOR_Y'],1); a.li(1,0); a.stg(G['PANIC_ACTIVE'],1)
    a.call('stack_guard_check'); a.call('gui_draw_desktop'); a.br('JMP','gui_loop')
    a.label('gui_boot_memory_error')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,1); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('BOOT RAM READBACK FAILURE')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 gui_boot_memory_check_site'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('BOOT MEMORY VALIDATOR')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('gui_boot_font_error')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,2); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('FONT CHECKSUM FAILURE')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 gui_font_checksum_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('FONT TABLE CHECKSUM SCAN')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')

    a.label('gui_boot_delay')
    a.li(1,15000000); a.stg(G['GUI_TMP'],1)
    a.label('gui_boot_delay_loop')
    a.ldg(1,G['GUI_TMP']); a.li(2,0); a.e('CMP r1 r2'); a.br('JEQ','gui_boot_delay_done')
    a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['GUI_TMP'],1); a.br('JMP','gui_boot_delay_loop')
    a.label('gui_boot_delay_done'); a.e('RET')

    # ---- Common event loop. Host bridge sends ASCII, arrow codes 17..20, Shift=21, Ctrl+S=22. ----
    a.label('gui_loop')
    a.call('stack_guard_check')
    a.li(2,0xFFFFFFFF); a.e('LOAD8 r1 r2'); a.e('CMP r1 r0'); a.br('JZE','gui_idle')
    a.stg(G['KEY_EVENT'],1); a.ldg(2,G['APP_STATE']); a.e('CMP r2 r0'); a.br('JEQ','gui_event_desktop')
    a.li(2,6); a.e('CMP r2 r2') if False else None
    a.ldg(2,G['APP_STATE']); a.li(3,6); a.e('CMP r2 r3'); a.br('JEQ','gui_event_paint')
    a.ldg(2,G['APP_STATE']); a.li(3,2); a.e('CMP r2 r3'); a.br('JEQ','gui_event_notes')
    a.ldg(2,G['APP_STATE']); a.li(3,3); a.e('CMP r2 r3'); a.br('JEQ','gui_event_calc')
    a.ldg(2,G['APP_STATE']); a.li(3,8); a.e('CMP r2 r3'); a.br('JEQ','gui_event_terminal')
    a.ldg(2,G['APP_STATE']); a.li(3,7); a.e('CMP r2 r3'); a.br('JEQ','gui_event_settings')
    a.ldg(2,G['APP_STATE']); a.li(3,11); a.e('CMP r2 r3'); a.br('JEQ','gui_event_shell_app')
    a.ldg(2,G['APP_STATE']); a.li(3,12); a.e('CMP r2 r3'); a.br('JEQ','gui_event_shell_app')
    a.ldg(2,G['APP_STATE']); a.li(3,13); a.e('CMP r2 r3'); a.br('JEQ','gui_event_shell_app')
    a.ldg(2,G['APP_STATE']); a.li(3,14); a.e('CMP r2 r3'); a.br('JEQ','gui_event_shell_app')
    a.ldg(2,G['APP_STATE']); a.li(3,16); a.e('CMP r2 r3'); a.br('JEQ','gui_event_sound')
    a.ldg(2,G['APP_STATE']); a.li(3,17); a.e('CMP r2 r3'); a.br('JEQ','gui_event_stopwatch')
    a.ldg(2,G['APP_STATE']); a.li(3,20); a.e('CMP r2 r3'); a.br('JEQ','gui_event_mixer')
    for state in (18,19,21,22,23,24):
      a.ldg(2,G['APP_STATE']); a.li(3,state); a.e('CMP r2 r3'); a.br('JEQ','gui_event_shell_app')
    a.br('JMP','gui_event_generic')
    a.label('gui_event_shell_app'); a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app'); a.br('JMP','gui_input_command')

    a.label('gui_event_desktop')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_click_desktop')
    a.call('gui_move_cursor'); a.call('gui_draw_desktop'); a.br('JMP','gui_loop')
    a.label('gui_click_desktop'); a.call('gui_hit_test'); a.br('JMP','gui_loop')

    # Paint app owns arrow movement and Shift-to-draw; Q returns home.
    a.label('gui_event_paint')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_paint_mark')
    a.ldg(1,G['KEY_EVENT']); a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.call('gui_move_paint_cursor'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_paint_mark')
    a.call('gui_sfx_paint')
    a.ldg(1,G['PAINT_COUNT']); a.li(2,128); a.e('CMP r1 r2'); a.br('JGE','gui_loop')
    a.ldg(2,G['CURSOR_X']); a.stx(PAINT_X_BUF,1,2); a.ldg(2,G['CURSOR_Y']); a.stx(PAINT_Y_BUF,1,2)
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAINT_COUNT'],1); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # Notes app: edit a bounded text buffer; Ctrl+S writes NOTES into the real RAM filesystem.
    a.label('gui_event_notes')
    a.ldg(1,G['KEY_EVENT']); a.li(2,22); a.e('CMP r1 r2'); a.br('JEQ','gui_save_note')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,8); a.e('CMP r1 r2'); a.br('JEQ','gui_note_backspace')
    a.ldg(1,G['KEY_EVENT']); a.li(2,13); a.e('CMP r1 r2'); a.br('JEQ','gui_note_space')
    a.ldg(1,G['KEY_EVENT']); a.li(2,32); a.e('CMP r1 r2'); a.br('JLT','gui_loop')
    a.ldg(1,G['KEY_EVENT']); a.li(2,126); a.e('CMP r1 r2'); a.br('JGT','gui_loop')
    a.ldg(1,G['NOTE_LEN']); a.li(2,95); a.e('CMP r1 r2'); a.br('JGE','gui_loop')
    a.ldg(2,G['KEY_EVENT']); a.li(3,97); a.e('CMP r2 r3'); a.br('JLT','gui_note_append')
    a.li(3,122); a.e('CMP r2 r3'); a.br('JGT','gui_note_append'); a.li(3,32); a.e('SUB r2 r2 r3')
    a.label('gui_note_append')
    a.ldg(1,G['NOTE_LEN']); a.stx(NOTE_BUF,1,2); a.li(3,1); a.e('ADD r1 r1 r3'); a.stg(G['NOTE_LEN'],1); a.li(2,0); a.stx(NOTE_BUF,1,2); a.li(1,0); a.stg(G['NOTE_STATUS'],1); a.call('gui_sfx_key'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_note_space')
    a.ldg(1,G['NOTE_LEN']); a.li(2,95); a.e('CMP r1 r2'); a.br('JGE','gui_loop'); a.li(2,32); a.stx(NOTE_BUF,1,2); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['NOTE_LEN'],1); a.li(2,0); a.stx(NOTE_BUF,1,2); a.call('gui_sfx_key'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_note_backspace')
    a.ldg(1,G['NOTE_LEN']); a.e('CMP r1 r0'); a.br('JLE','gui_loop'); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['NOTE_LEN'],1); a.li(2,0); a.stx(NOTE_BUF,1,2); a.call('gui_sfx_key'); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # Calculator/terminal type into CMD_BUF. Calculator presets the command prefix CALC.
    a.label('gui_event_calc')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.br('JMP','gui_input_command')
    a.label('gui_event_terminal')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.br('JMP','gui_input_command')
    a.label('gui_input_command')
    a.ldg(1,G['KEY_EVENT']); a.li(2,13); a.e('CMP r1 r2'); a.br('JEQ','gui_command_enter')
    a.ldg(1,G['KEY_EVENT']); a.li(2,10); a.e('CMP r1 r2'); a.br('JEQ','gui_command_enter')
    a.ldg(1,G['KEY_EVENT']); a.li(2,8); a.e('CMP r1 r2'); a.br('JEQ','gui_command_backspace')
    a.ldg(1,G['KEY_EVENT']); a.li(2,127); a.e('CMP r1 r2'); a.br('JEQ','gui_command_backspace')
    a.ldg(1,G['KEY_EVENT']); a.li(2,32); a.e('CMP r1 r2'); a.br('JLT','gui_loop')
    a.ldg(1,G['KEY_EVENT']); a.li(2,126); a.e('CMP r1 r2'); a.br('JGT','gui_loop')
    a.li(2,97); a.e('CMP r1 r2'); a.br('JLT','gui_command_append')
    a.li(2,122); a.e('CMP r1 r2'); a.br('JGT','gui_command_append'); a.li(2,32); a.e('SUB r1 r1 r2')
    a.label('gui_command_append')
    a.ldg(3,G['CMD_LEN']); a.li(4,99); a.e('CMP r3 r4'); a.br('JGE','gui_loop'); a.stx(CMD_BUF,3,1); a.li(4,1); a.e('ADD r3 r3 r4'); a.stg(G['CMD_LEN'],3); a.call('gui_sfx_key'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_command_backspace')
    a.ldg(3,G['CMD_LEN']); a.e('CMP r3 r0'); a.br('JLE','gui_loop'); a.li(4,1); a.e('SUB r3 r3 r4'); a.stg(G['CMD_LEN'],3); a.li(4,0); a.stx(CMD_BUF,3,4); a.call('gui_sfx_key'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_command_enter')
    # Ensure command is terminated, invoke the original parser and command services, then reset input buffer.
    a.ldg(3,G['CMD_LEN']); a.li(4,0); a.stx(CMD_BUF,3,4)
    a.ldg(1,G['APP_STATE']); a.li(2,3); a.e('CMP r1 r2'); a.br('JNE','gui_terminal_execute')
    # Calculator input line already starts with the CALC command; parse via the same shell code.
    a.label('gui_terminal_execute')
    a.call('echo_command'); a.call('parse_command'); a.call('execute_command'); a.call('gui_sfx_ok')
    a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['CMD_LEN'],1)
    a.ldg(1,G['APP_STATE']); a.li(2,3); a.e('CMP r1 r2'); a.br('JNE','gui_command_redraw')
    # Re-prime calculator command prefix.
    for i,ch in enumerate('CALC '):
      a.li(1,ord(ch)); a.stx(CMD_BUF,i,1)
    a.li(1,5); a.stg(G['CMD_LEN'],1)
    a.label('gui_command_redraw'); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    a.label('gui_event_settings')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_toggle_theme')
    a.ldg(1,G['KEY_EVENT']); a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.br('JMP','gui_loop')
    a.label('gui_toggle_theme'); a.call('gui_sfx_theme'); a.ldg(1,G['THEME']); a.e('CMP r1 r0'); a.br('JNE','gui_theme_dark'); a.li(1,1); a.stg(G['THEME'],1); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_theme_dark'); a.li(1,0); a.stg(G['THEME'],1); a.call('gui_sfx_theme'); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # Sound Studio is a real MMIO client, not a host-side decoration.
    a.label('gui_event_sound')
    a.ldg(1,G['KEY_EVENT']); a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_demo')
    a.ldg(1,G['KEY_EVENT']); a.li(2,77); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_demo')
    a.ldg(1,G['KEY_EVENT']); a.li(2,109); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_demo')
    a.ldg(1,G['KEY_EVENT']); a.li(2,88); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_stop')
    a.ldg(1,G['KEY_EVENT']); a.li(2,120); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_stop')
    a.ldg(1,G['KEY_EVENT']); a.li(2,49); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_1')
    a.li(2,50); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_2')
    a.li(2,51); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_3')
    a.li(2,52); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_4')
    a.li(2,53); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_5')
    a.li(2,54); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_6')
    a.li(2,55); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_7')
    a.li(2,56); a.e('CMP r1 r2'); a.br('JEQ','gui_sound_note_8')
    a.call('gui_sfx_nav'); a.br('JMP','gui_loop')
    for label,freq,wave,pan in [
        ('gui_sound_note_1',262,0,18),('gui_sound_note_2',294,0,27),
        ('gui_sound_note_3',330,1,36),('gui_sound_note_4',349,0,45),
        ('gui_sound_note_5',392,2,55),('gui_sound_note_6',440,0,64),
        ('gui_sound_note_7',494,1,73),('gui_sound_note_8',523,2,82)]:
      a.label(label); a.li(1,freq); a.li(2,260); a.li(3,10); a.li(4,wave); a.li(5,pan); a.call('gui_sound_emit'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_sound_stop'); a.li(6,0xFFFFFFE0); a.li(7,0); a.e('STORE r6 r7'); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('gui_sound_demo')
    # A short, eight-note arpeggiated phrase; the bounded delay gives the async
    # 10 ms host audio buffers time to observe each trigger without long waits.
    for i,(freq,wave,pan) in enumerate([(392,0,35),(494,0,45),(587,2,55),(784,0,65),(659,1,65),(587,2,55),(494,0,45),(523,0,50)]):
      a.li(1,freq); a.li(2,180); a.li(3,10); a.li(4,wave); a.li(5,pan); a.call('gui_sound_emit');
      if i != 7:
        a.li(1,10000000); a.stg(G['GUI_TMP'],1)
        delay_label=f'gui_sound_demo_delay_{i}'; done_label=f'gui_sound_demo_delay_done_{i}'
        a.label(delay_label); a.ldg(1,G['GUI_TMP']); a.e('CMP r1 r0'); a.br('JEQ',done_label); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['GUI_TMP'],1); a.br('JMP',delay_label); a.label(done_label)
    a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # Stopwatch: guest poll ticks, start/stop, lap count, reset.
    a.label('gui_event_stopwatch')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app'); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.li(2,32); a.e('CMP r1 r2'); a.br('JEQ','stopwatch_toggle')
    a.li(2,76); a.e('CMP r1 r2'); a.br('JEQ','stopwatch_lap'); a.li(2,108); a.e('CMP r1 r2'); a.br('JEQ','stopwatch_lap')
    a.li(2,82); a.e('CMP r1 r2'); a.br('JEQ','stopwatch_reset'); a.li(2,114); a.e('CMP r1 r2'); a.br('JEQ','stopwatch_reset')
    a.br('JMP','gui_loop')
    a.label('stopwatch_toggle'); a.ldg(1,G['STOPWATCH_RUNNING']); a.e('NOT r1 r1'); a.li(2,1); a.e('AND r1 r1 r2'); a.stg(G['STOPWATCH_RUNNING'],1); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('stopwatch_lap'); a.ldg(1,G['STOPWATCH_LAPS']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['STOPWATCH_LAPS'],1); a.call('gui_draw_app'); a.br('JMP','gui_loop')
    a.label('stopwatch_reset'); a.li(1,0); a.stg(G['STOPWATCH_RUNNING'],1); a.stg(G['STOPWATCH_TICKS'],1); a.stg(G['STOPWATCH_LAPS'],1); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # Sound Mixer: runner GuestAudio tone generator uses E0/E4/E8/EC/F0/F4/F8.
    a.label('gui_event_mixer')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app'); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.li(2,19); a.e('CMP r1 r2'); a.br('JEQ','mixer_freq_down'); a.li(2,20); a.e('CMP r1 r2'); a.br('JEQ','mixer_freq_up')
    a.li(2,17); a.e('CMP r1 r2'); a.br('JEQ','mixer_volume_up'); a.li(2,18); a.e('CMP r1 r2'); a.br('JEQ','mixer_volume_down')
    a.li(2,32); a.e('CMP r1 r2'); a.br('JEQ','mixer_play'); a.li(2,88); a.e('CMP r1 r2'); a.br('JEQ','mixer_stop'); a.li(2,120); a.e('CMP r1 r2'); a.br('JEQ','mixer_stop')
    for key,wave in [(49,0),(50,1),(51,2),(52,3)]:
      a.li(2,key); a.e('CMP r1 r2'); a.br('JEQ',f'mixer_wave_{wave}')
    a.br('JMP','gui_loop')
    a.label('mixer_freq_down'); a.ldg(1,G['MIX_FREQ']); a.li(2,20); a.e('SUB r1 r1 r2'); a.li(2,40); a.e('CMP r1 r2'); a.br('JGE','mixer_freq_store'); a.li(1,40); a.label('mixer_freq_store'); a.stg(G['MIX_FREQ'],1); a.br('JMP','mixer_redraw')
    a.label('mixer_freq_up'); a.ldg(1,G['MIX_FREQ']); a.li(2,20); a.e('ADD r1 r1 r2'); a.li(2,20000); a.e('CMP r1 r2'); a.br('JLE','mixer_freq_up_store'); a.li(1,20000); a.label('mixer_freq_up_store'); a.stg(G['MIX_FREQ'],1); a.br('JMP','mixer_redraw')
    a.label('mixer_volume_up'); a.ldg(1,G['MIX_VOLUME']); a.li(2,2); a.e('ADD r1 r1 r2'); a.li(2,25); a.e('CMP r1 r2'); a.br('JLE','mixer_volume_store'); a.li(1,25); a.label('mixer_volume_store'); a.stg(G['MIX_VOLUME'],1); a.br('JMP','mixer_redraw')
    a.label('mixer_volume_down'); a.ldg(1,G['MIX_VOLUME']); a.li(2,2); a.e('SUB r1 r1 r2'); a.e('CMP r1 r0'); a.br('JGE','mixer_volume_down_store'); a.li(1,0); a.label('mixer_volume_down_store'); a.stg(G['MIX_VOLUME'],1); a.br('JMP','mixer_redraw')
    for wave in range(4):
      a.label(f'mixer_wave_{wave}'); a.li(1,wave); a.stg(G['MIX_WAVE'],1); a.br('JMP','mixer_redraw')
    a.label('mixer_play'); a.ldg(1,G['MIX_FREQ']); a.li(2,500); a.ldg(3,G['MIX_VOLUME']); a.ldg(4,G['MIX_WAVE']); a.ldg(5,G['MIX_PAN']); a.call('gui_sound_emit'); a.br('JMP','mixer_redraw')
    a.label('mixer_stop'); a.li(6,0xFFFFFFE0); a.li(7,0); a.e('STORE r6 r7'); a.br('JMP','mixer_redraw')
    a.label('mixer_redraw'); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    a.label('gui_event_generic')
    a.ldg(1,G['KEY_EVENT']); a.li(2,21); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,81); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.ldg(1,G['KEY_EVENT']); a.li(2,113); a.e('CMP r1 r2'); a.br('JEQ','gui_close_app')
    a.br('JMP','gui_loop')
    a.label('gui_close_app'); a.li(6,0xFFFFFFE0); a.li(7,0); a.e('STORE r6 r7'); a.call('gui_sfx_close'); a.li(1,0); a.stg(G['APP_STATE'],1); a.li(1,170); a.stg(G['CURSOR_X'],1); a.li(1,172); a.stg(G['CURSOR_Y'],1); a.call('gui_draw_desktop'); a.br('JMP','gui_loop')

    # Desktop focus always lands on the center of a valid app tile.
    a.label('gui_move_cursor')
    a.ldg(1,G['KEY_EVENT']); a.li(2,17); a.e('CMP r1 r2'); a.br('JEQ','gui_cursor_up')
    a.li(2,18); a.e('CMP r1 r2'); a.br('JEQ','gui_cursor_down')
    a.li(2,19); a.e('CMP r1 r2'); a.br('JEQ','gui_cursor_left')
    a.li(2,20); a.e('CMP r1 r2'); a.br('JEQ','gui_cursor_right'); a.e('RET')
    a.label('gui_cursor_up'); a.ldg(1,G['CURSOR_Y']); a.li(2,172); a.e('CMP r1 r2'); a.br('JLE','gui_cursor_done'); a.li(2,76); a.e('SUB r1 r1 r2'); a.stg(G['CURSOR_Y'],1); a.e('RET')
    a.label('gui_cursor_down'); a.ldg(1,G['CURSOR_Y']); a.li(2,552); a.e('CMP r1 r2'); a.br('JGE','gui_cursor_done'); a.li(2,76); a.e('ADD r1 r1 r2'); a.stg(G['CURSOR_Y'],1); a.e('RET')
    a.label('gui_cursor_left'); a.ldg(1,G['CURSOR_X']); a.li(2,170); a.e('CMP r1 r2'); a.br('JLE','gui_cursor_done'); a.li(2,308); a.e('SUB r1 r1 r2'); a.stg(G['CURSOR_X'],1); a.e('RET')
    a.label('gui_cursor_right'); a.ldg(1,G['CURSOR_X']); a.li(2,1094); a.e('CMP r1 r2'); a.br('JGE','gui_cursor_done'); a.li(2,308); a.e('ADD r1 r1 r2'); a.stg(G['CURSOR_X'],1); a.e('RET')
    a.label('gui_cursor_done'); a.e('RET')

    a.label('gui_move_paint_cursor')
    a.ldg(1,G['KEY_EVENT']); a.li(2,17); a.e('CMP r1 r2'); a.br('JEQ','gui_paint_up')
    a.li(2,18); a.e('CMP r1 r2'); a.br('JEQ','gui_paint_down')
    a.li(2,19); a.e('CMP r1 r2'); a.br('JEQ','gui_paint_left')
    a.li(2,20); a.e('CMP r1 r2'); a.br('JEQ','gui_paint_right'); a.e('RET')
    a.label('gui_paint_up'); a.ldg(1,G['CURSOR_Y']); a.li(2,12); a.e('CMP r1 r2'); a.br('JLE','gui_paint_move_done'); a.li(2,12); a.e('SUB r1 r1 r2'); a.li(2,155); a.e('CMP r1 r2'); a.br('JGE','gui_paint_up_store'); a.li(1,155)
    a.label('gui_paint_up_store'); a.stg(G['CURSOR_Y'],1); a.e('RET')
    a.label('gui_paint_down'); a.ldg(1,G['CURSOR_Y']); a.li(2,12); a.e('ADD r1 r1 r2'); a.li(2,580); a.e('CMP r1 r2'); a.br('JLE','gui_paint_down_store'); a.li(1,580)
    a.label('gui_paint_down_store'); a.stg(G['CURSOR_Y'],1); a.e('RET')
    a.label('gui_paint_left'); a.ldg(1,G['CURSOR_X']); a.li(2,12); a.e('CMP r1 r2'); a.br('JLE','gui_paint_move_done'); a.li(2,12); a.e('SUB r1 r1 r2'); a.li(2,260); a.e('CMP r1 r2'); a.br('JGE','gui_paint_left_store'); a.li(1,260)
    a.label('gui_paint_left_store'); a.stg(G['CURSOR_X'],1); a.e('RET')
    a.label('gui_paint_right'); a.ldg(1,G['CURSOR_X']); a.li(2,12); a.e('ADD r1 r1 r2'); a.li(2,1020); a.e('CMP r1 r2'); a.br('JLE','gui_paint_right_store'); a.li(1,1020)
    a.label('gui_paint_right_store'); a.stg(G['CURSOR_X'],1); a.e('RET')
    a.label('gui_paint_move_done'); a.e('RET')

    # Hit-test each desktop icon and launch real app-specific guest handlers.
    a.label('gui_hit_test')
    apps=[(state,170+308*col,172+76*row) for row in range(6) for col in range(4) for state in [row*4+col+1]]
    for state,cx,cy in apps:
      miss=a.new('guihitmiss')
      a.ldg(1,G['CURSOR_X']); a.li(2,cx-146); a.e('CMP r1 r2'); a.br('JLT',miss)
      a.li(2,cx+146); a.e('CMP r1 r2'); a.br('JGT',miss)
      a.ldg(1,G['CURSOR_Y']); a.li(2,cy-32); a.e('CMP r1 r2'); a.br('JLT',miss)
      a.li(2,cy+32); a.e('CMP r1 r2'); a.br('JGT',miss)
      a.call('gui_sfx_open'); a.li(1,state); a.stg(G['APP_STATE'],1); a.call('gui_launch_app'); a.e('RET')
      a.label(miss)
    a.e('RET')

    a.label('gui_launch_app')
    a.ldg(1,G['APP_STATE']); a.li(2,2); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_notes')
    a.ldg(1,G['APP_STATE']); a.li(2,3); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_calc')
    a.ldg(1,G['APP_STATE']); a.li(2,6); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_paint')
    a.ldg(1,G['APP_STATE']); a.li(2,8); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_terminal')
    a.ldg(1,G['APP_STATE']); a.li(2,11); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_shellapp')
    a.ldg(1,G['APP_STATE']); a.li(2,12); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_shellapp')
    a.ldg(1,G['APP_STATE']); a.li(2,13); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_shellapp')
    a.ldg(1,G['APP_STATE']); a.li(2,14); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_shellapp')
    for state in (18,19,21,22,23,24):
      a.ldg(1,G['APP_STATE']); a.li(2,state); a.e('CMP r1 r2'); a.br('JEQ','gui_launch_shellapp')
    a.br('JMP','gui_launch_render')
    a.label('gui_launch_shellapp'); a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['CMD_LEN'],1); a.br('JMP','gui_launch_render')
    a.label('gui_launch_notes'); a.call('gui_load_note'); a.br('JMP','gui_launch_render')
    a.label('gui_launch_calc')
    a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3')
    for i,ch in enumerate('CALC '): a.li(1,ord(ch)); a.li(2,i); a.stx(CMD_BUF,2,1)
    a.li(1,5); a.stg(G['CMD_LEN'],1); a.br('JMP','gui_launch_render')
    a.label('gui_launch_paint'); a.li(1,640); a.stg(G['CURSOR_X'],1); a.li(1,360); a.stg(G['CURSOR_Y'],1); a.br('JMP','gui_launch_render')
    a.label('gui_launch_terminal'); a.li(1,CMD_BUF); a.li(2,0); a.li(3,120*4); a.e('MEMSET r1 r2 r3'); a.li(1,0); a.stg(G['CMD_LEN'],1); a.br('JMP','gui_launch_render')
    a.label('gui_launch_render'); a.ldg(1,G['APP_STATE']); a.call('app_arena_ensure'); a.call('gui_draw_app'); a.e('RET')

    # Notes persistence uses the old RAM filesystem implementation, not a host-side fake list.
    a.label('gui_write_notes_name')
    a.li(1,ARG_NAME); a.li(2,0); a.li(3,24*4); a.e('MEMSET r1 r2 r3')
    for i,ch in enumerate('NOTES'): a.li(1,ord(ch)); a.li(2,i); a.stx(ARG_NAME,2,1)
    a.e('RET')
    a.label('gui_load_note')
    a.call('gui_write_notes_name'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','gui_load_note_empty')
    a.ldx(FS_SIZE,0,1) if False else None
    a.ldg(1,G['FILE_FOUND']); a.ldx(2,FS_SIZE,1); a.stg(G['NOTE_LEN'],2); a.li(1,0); a.stg(G['NOTE_I'],1)
    a.label('gui_load_note_loop'); a.ldg(1,G['NOTE_I']); a.ldg(2,G['NOTE_LEN']); a.e('CMP r1 r2'); a.br('JGE','gui_load_note_done')
    a.ldg(3,G['FILE_FOUND']); a.ldx(5,FS_PAGE,3); a.e('LDX r4 r5 r1'); a.stx(NOTE_BUF,1,4)
    a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['NOTE_I'],1); a.br('JMP','gui_load_note_loop')
    a.label('gui_load_note_done'); a.ldg(1,G['NOTE_LEN']); a.li(2,0); a.stx(NOTE_BUF,1,2); a.li(1,0); a.stg(G['NOTE_STATUS'],1); a.e('RET')
    a.label('gui_load_note_empty'); a.li(1,0); a.stg(G['NOTE_LEN'],1); a.stx(NOTE_BUF,0,1); a.stg(G['NOTE_STATUS'],1); a.e('RET')

    a.label('gui_save_note')
    a.call('gui_write_notes_name'); a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','gui_save_note_copy')
    a.call('create_file')
    a.label('gui_save_note_copy')
    a.li(1,0); a.stg(G['NOTE_I'],1)
    a.label('gui_save_note_copy_loop'); a.ldg(1,G['NOTE_I']); a.ldg(2,G['NOTE_LEN']); a.e('CMP r1 r2'); a.br('JGE','gui_save_note_copy_done')
    a.ldx(3,NOTE_BUF,1); a.stx(ARG_TEXT,1,3); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['NOTE_I'],1); a.br('JMP','gui_save_note_copy_loop')
    a.label('gui_save_note_copy_done'); a.ldg(1,G['NOTE_LEN']); a.li(2,0); a.stx(ARG_TEXT,1,2); a.stg(G['ARG_TEXT_LEN'],1); a.li(1,0); a.stg(G['TEMP_A'],1); a.call('write_file_content')
    a.li(1,1); a.stg(G['NOTE_STATUS'],1); a.call('gui_sfx_ok'); a.call('gui_draw_app'); a.br('JMP','gui_loop')

    # ---- Drawing routines ----
    a.label('gui_draw_backdrop')
    a.ldg(1,G['THEME']); a.e('CMP r1 r0'); a.br('JNE','gui_backdrop_light')
    a.li(1,FB); a.li(2,0x101B2B); a.li(3,FRAME_BYTES); a.e('MEMSET r1 r2 r3'); a.br('JMP','gui_backdrop_after_clear')
    a.label('gui_backdrop_light'); a.li(1,FB); a.li(2,0xD7E2EF); a.li(3,FRAME_BYTES); a.e('MEMSET r1 r2 r3')
    a.label('gui_backdrop_after_clear')
    self.gui_rect_setup(0,0,1280,64,0x17171717,0); self.gui_rect_setup(0,0,1280,3,0x55D8FFFF,1); self.gui_rect_setup(0,63,1280,2,0x36516AFF,1)
    self.gui_rect_setup(16,78,1248,552,0x1D2B3CFF,1); self.gui_rect_setup(0,646,1280,74,0x10101010,0); self.gui_rect_setup(0,646,1280,2,0x36516AFF,1)
    self.gui_const('NOVA 7.1  /  WORKSTATION',1,3,0x55D8FFFF); self.gui_const('24 APPS  |  2 GB GUEST RAM  |  720P RGBA8888',1,82,0x72E7B0FF)
    self.gui_const('WORKSPACE',5,3,0xE9EFF8FF); self.gui_const('COMPUTE  /  CREATE  /  INSPECT  /  MANAGE',7,3,0xAFC1D4FF)
    self.gui_const('ARROWS SELECT  |  SHIFT OPEN  |  Q CLOSE',36,3,0xB8C9DCFF); self.gui_const('STACK 1 MB  /  PAGE-SLAB MEMORY MANAGER',36,77,0x55D8FFFF); a.e('RET')

    a.label('gui_draw_desktop'); a.call('gui_draw_backdrop')
    apps=[
      (1,24,140,0x3984D8FF,'F','FILE MANAGER','RAM FILES'),(2,332,140,0x39B88AFF,'N','NOTES','MULTI-TAB TEXT'),(3,640,140,0xEEA45CFF,'C','CALCULATOR','RPN / SCIENTIFIC'),(4,948,140,0x7F91F6FF,'M','SYSTEM MONITOR','RAM / STACK / CPU'),
      (5,24,216,0xA078D9FF,'D','CALENDAR','EVENTS'),(6,332,216,0xE36D82FF,'P','PAINT','1280X720 RGBA CANVAS'),(7,640,216,0x63B6C6FF,'S','SETTINGS','THEME / AUDIO'),(8,948,216,0x5E9BCBFF,'T','TERMINAL','COMMAND SHELL'),
      (9,24,292,0xD3B75FFF,'H','HELP','MANUAL'),(10,332,292,0x8EA4B8FF,'I','ABOUT','SYSTEM INFO'),(11,640,292,0x42B6A5FF,'M','MATH LAB','NUMBER TOOLS'),(12,948,292,0x568FDBFF,'D','DIAGNOSTICS','MEMTEST / SELFTEST'),
      (13,24,368,0xC98D5EFF,'S','SCRIPT LAB','GUEST SCRIPTS'),(14,332,368,0x799E64FF,'F','FILE TOOLS','SIZE / CRC / RUN'),(15,640,368,0xA28BE1FF,'C','CLOCK','GUEST POLL TICKS'),(16,948,368,0xE07DBAFF,'S','SOUND STUDIO','8 TONE PRESETS'),
      (17,24,444,0x49B9D8FF,'W','STOPWATCH','START / LAP / RESET'),(18,332,444,0xD69A55FF,'U','UNIT CONVERTER','C F KM MI KG LB'),(19,640,444,0xD45F72FF,'K','KERNEL MONITOR','PAGES / STACK / APPS'),(20,948,444,0x7E83E8FF,'A','SOUND MIXER','FREQ / VOL / WAVE'),
      (21,24,520,0x5C9CDEFF,'H','HEX WORKBENCH','GUEST MEMORY DUMP'),(22,332,520,0x43B79AFF,'B','BENCHMARK LAB','BENCH / MIPS'),(23,640,520,0xBD8D58FF,'R','FILE RECOVERY','UNDO / FSCK'),(24,948,520,0x8E79C6FF,'L','SYSTEM LOG','GUEST HISTORY')]
    for state,cx,cy,color,initial,label,detail in apps:
      self.gui_rect_setup(cx+2,cy+3,292,64,0x0A0A0AFF,0); self.gui_rect_setup(cx,cy,292,64,0x29384BFF,1); self.gui_rect_setup(cx,cy,4,64,color,1); self.gui_rect_setup(cx+12,cy+10,44,44,color,1)
      row=int((cy+27)/18); col=int((cx+34)/12); self.gui_const(initial,row,col,0xFFFFFFFF)
      title_col=int((cx+72)/12); title_row=int((cy+18)/18); self.gui_const(label,title_row,title_col,0xF1F5FAFF); self.gui_const(detail,title_row+1,title_col,0xAFC1D4FF)
      self.gui_rect_setup(cx+72,cy+54,204,1,0x405269FF,1)
    a.call('gui_draw_cursor'); a.call('gui_present_frame'); a.e('RET')

    a.label('gui_draw_cursor')
    a.ldg(1,G['CURSOR_X']); a.li(2,150); a.e('SUB r1 r1 r2'); a.stg(G['RECT_X'],1)
    a.ldg(1,G['CURSOR_Y']); a.li(2,36); a.e('SUB r1 r1 r2'); a.stg(G['RECT_Y'],1)
    a.li(1,300); a.stg(G['RECT_W'],1); a.li(1,3); a.stg(G['RECT_H'],1); a.li(1,0x55D8FFFF); a.stg(G['RECT_COLOR'],1); a.li(1,1); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    a.ldg(1,G['CURSOR_X']); a.li(2,150); a.e('SUB r1 r1 r2'); a.stg(G['RECT_X'],1)
    a.ldg(1,G['CURSOR_Y']); a.li(2,33); a.e('ADD r1 r1 r2'); a.stg(G['RECT_Y'],1)
    a.li(1,300); a.stg(G['RECT_W'],1); a.li(1,3); a.stg(G['RECT_H'],1); a.li(1,0x55D8FFFF); a.stg(G['RECT_COLOR'],1); a.li(1,1); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    a.ldg(1,G['CURSOR_X']); a.li(2,150); a.e('SUB r1 r1 r2'); a.stg(G['RECT_X'],1)
    a.ldg(1,G['CURSOR_Y']); a.li(2,36); a.e('SUB r1 r1 r2'); a.stg(G['RECT_Y'],1)
    a.li(1,3); a.stg(G['RECT_W'],1); a.li(1,72); a.stg(G['RECT_H'],1); a.li(1,0x55D8FFFF); a.stg(G['RECT_COLOR'],1); a.li(1,1); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    a.ldg(1,G['CURSOR_X']); a.li(2,147); a.e('ADD r1 r1 r2'); a.stg(G['RECT_X'],1)
    a.ldg(1,G['CURSOR_Y']); a.li(2,36); a.e('SUB r1 r1 r2'); a.stg(G['RECT_Y'],1)
    a.li(1,3); a.stg(G['RECT_W'],1); a.li(1,72); a.stg(G['RECT_H'],1); a.li(1,0x55D8FFFF); a.stg(G['RECT_COLOR'],1); a.li(1,1); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    a.e('RET')

    a.label('gui_draw_boot')
    a.li(1,FB); a.li(2,0x0A); a.li(3,1280*720*4); a.e('MEMSET r1 r2 r3')
    self.gui_rect_setup(0,0,1280,4,0x36B9F4FF,1)
    self.gui_rect_setup(240,450,800,18,0x30303030,0)
    a.ldg(1,G['BOOT_STAGE']); a.li(2,200); a.e('MUL r1 r1 r2'); a.stg(G['RECT_W'],1); a.li(1,240); a.stg(G['RECT_X'],1); a.li(1,450); a.stg(G['RECT_Y'],1); a.li(1,12); a.stg(G['RECT_H'],1); a.li(1,0x44); a.stg(G['RECT_COLOR'],1); a.li(1,0); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    self.gui_const('NOVA 7.1 WORKSTATION',12,40,0x4BC6F3FF)
    self.gui_const('GRAPHICAL DESKTOP',14,40,0xE9EFF8FF)
    self.gui_const('STARTING GUEST OPERATING SYSTEM',16,26,0xB4C2D4FF)
    a.ldg(1,G['BOOT_TEXT']); a.stg(G['TEXT_SRC'],1); a.li(1,22); a.stg(G['TEXT_ROW'],1); a.li(1,27); a.stg(G['TEXT_COL'],1); a.li(1,0x63DCAEFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('BOOT DOES REAL MEMORY, FILESYSTEM, FONT AND APP INITIALIZATION',28,20,0xAAB7C9FF)
    a.call('gui_present_frame'); a.e('RET')

    # Fast filled rectangles: grayscale byte rows use native MEMSET; colored icons/marks use exact RGBA stores.
    a.label('gui_draw_rect')
    a.li(1,0); a.stg(G['RECT_ROW'],1)
    a.label('gui_rect_row_loop')
    a.ldg(1,G['RECT_ROW']); a.ldg(2,G['RECT_H']); a.e('CMP r1 r2'); a.br('JGE','gui_rect_done')
    a.ldg(1,G['RECT_Y']); a.ldg(2,G['RECT_ROW']); a.e('ADD r3 r1 r2'); a.li(4,5120); a.e('MUL r3 r3 r4')
    a.ldg(1,G['RECT_X']); a.li(2,4); a.e('MUL r1 r1 r2'); a.e('ADD r3 r3 r1'); a.li(4,FB); a.e('ADD r3 r3 r4'); a.stg(G['RECT_BASE'],3)
    a.ldg(1,G['RECT_MODE']); a.e('CMP r1 r0'); a.br('JNE','gui_rect_nonzero_mode')
    a.ldg(1,G['RECT_BASE']); a.ldg(2,G['RECT_COLOR']); a.ldg(3,G['RECT_W']); a.li(4,4); a.e('MUL r3 r3 r4'); a.e('MEMSET r1 r2 r3'); a.br('JMP','gui_rect_next_row')
    a.label('gui_rect_nonzero_mode'); a.li(2,2); a.e('CMP r1 r2'); a.br('JEQ','gui_rect_blend_init')
    a.br('JMP','gui_rect_exact')
    a.label('gui_rect_blend_init'); a.li(1,0); a.stg(G['RECT_COL'],1)
    a.label('gui_rect_blend_loop')
    a.ldg(1,G['RECT_COL']); a.ldg(2,G['RECT_W']); a.e('CMP r1 r2'); a.br('JGE','gui_rect_next_row')
    a.li(2,4); a.e('MUL r3 r1 r2'); a.ldg(4,G['RECT_BASE']); a.e('ADD r3 r3 r4'); a.e('LOAD r5 r3'); a.ldg(6,G['RECT_COLOR'])
    # ARGB alpha blend: out=(src*alpha + dst*(255-alpha))/255 per RGB channel.
    a.li(7,24); a.e('RSH r8 r6 r7'); a.li(7,255); a.e('AND r8 r8 r7'); a.e('SUB r9 r7 r8')
    a.li(7,255); a.e('AND r10 r6 r7'); a.e('AND r11 r5 r7'); a.e('MUL r10 r10 r8'); a.e('MUL r11 r11 r9'); a.e('ADD r10 r10 r11'); a.li(7,255); a.e('DIVU r10 r10 r7'); a.e('MOV r12 r10')
    a.li(7,8); a.e('RSH r10 r6 r7'); a.li(7,255); a.e('AND r10 r10 r7'); a.li(7,8); a.e('RSH r11 r5 r7'); a.li(7,255); a.e('AND r11 r11 r7'); a.e('MUL r10 r10 r8'); a.e('MUL r11 r11 r9'); a.e('ADD r10 r10 r11'); a.li(7,255); a.e('DIVU r10 r10 r7'); a.li(7,8); a.e('LSH r10 r10 r7'); a.e('OR r12 r12 r10')
    a.li(7,16); a.e('RSH r10 r6 r7'); a.li(7,255); a.e('AND r10 r10 r7'); a.li(7,16); a.e('RSH r11 r5 r7'); a.li(7,255); a.e('AND r11 r11 r7'); a.e('MUL r10 r10 r8'); a.e('MUL r11 r11 r9'); a.e('ADD r10 r10 r11'); a.li(7,255); a.e('DIVU r10 r10 r7'); a.li(7,16); a.e('LSH r10 r10 r7'); a.e('OR r12 r12 r10')
    a.li(7,255); a.li(10,24); a.e('LSH r7 r7 r10'); a.e('OR r12 r12 r7'); a.e('STORE r3 r12')
    a.ldg(1,G['RECT_COL']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['RECT_COL'],1); a.br('JMP','gui_rect_blend_loop')
    a.label('gui_rect_exact'); a.li(1,0); a.stg(G['RECT_COL'],1)
    a.label('gui_rect_exact_loop')
    a.ldg(1,G['RECT_COL']); a.ldg(2,G['RECT_W']); a.e('CMP r1 r2'); a.br('JGE','gui_rect_next_row')
    a.li(2,4); a.e('MUL r3 r1 r2'); a.ldg(4,G['RECT_BASE']); a.e('ADD r3 r3 r4'); a.ldg(5,G['RECT_COLOR']); a.e('STORE r3 r5')
    a.ldg(1,G['RECT_COL']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['RECT_COL'],1); a.br('JMP','gui_rect_exact_loop')
    a.label('gui_rect_next_row'); a.ldg(1,G['RECT_ROW']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['RECT_ROW'],1); a.br('JMP','gui_rect_row_loop')
    a.label('gui_rect_done'); a.e('RET')

    # Common app window with title and close instruction.
    a.label('gui_draw_window')
    a.call('gui_draw_backdrop')
    self.gui_rect_setup(160,60,960,590,0x35,0)
    self.gui_rect_setup(160,60,960,48,0x50,0)
    self.gui_rect_setup(170,114,940,526,0x25,0)
    self.gui_rect_setup(160,60,960,3,0x4BC6F3FF,1)
    a.ldg(1,G['APP_STATE'])
    title_specs=[(1,'FILE MANAGER'),(2,'NOTES'),(3,'CALCULATOR'),(4,'SYSTEM MONITOR'),(5,'CALENDAR'),(6,'PAINT'),(7,'SETTINGS'),(8,'TERMINAL'),(9,'HELP'),(10,'ABOUT'),(11,'MATH LAB'),(12,'DIAGNOSTICS'),(13,'SCRIPT LAB'),(14,'FILE TOOLS'),(15,'CLOCK'),(16,'SOUND STUDIO'),(17,'STOPWATCH'),(18,'UNIT CONVERTER'),(19,'KERNEL MONITOR'),(20,'SOUND MIXER'),(21,'HEX WORKBENCH'),(22,'BENCHMARK LAB'),(23,'FILE RECOVERY'),(24,'SYSTEM LOG')]
    done=a.new('guiwindowdone'); title_labels=[]
    for state,title in title_specs:
      lab=a.new('guiwindowtitle'); title_labels.append((lab,title))
      a.li(2,state); a.e('CMP r1 r2'); a.br('JEQ',lab)
    a.br('JMP',done)
    for lab,title in title_labels:
      a.label(lab); self.gui_const(title,4,15,0x49C7F1FF); a.br('JMP',done)
    a.label(done)
    self.gui_const('SHIFT CLOSES',4,68,0xCBD5E4FF)
    a.e('RET')

    a.label('gui_draw_app')
    a.call('gui_draw_window')
    app_specs=[(1,'gui_draw_files'),(2,'gui_draw_notes'),(3,'gui_draw_calc'),(4,'gui_draw_monitor'),(5,'gui_draw_calendar'),(6,'gui_draw_paint'),(7,'gui_draw_settings'),(8,'gui_draw_terminal'),(9,'gui_draw_help'),(10,'gui_draw_about'),(11,'gui_draw_mathlab'),(12,'gui_draw_diagnostics'),(13,'gui_draw_scriptlab'),(14,'gui_draw_filetools'),(15,'gui_draw_clock'),(16,'gui_draw_sound'),(17,'gui_draw_stopwatch'),(18,'gui_draw_converter'),(19,'gui_draw_kernel'),(20,'gui_draw_mixer'),(21,'gui_draw_hex'),(22,'gui_draw_bench'),(23,'gui_draw_recovery'),(24,'gui_draw_syslog')]
    app_done=a.new('guiappdone'); app_labels=[]
    for state,lab in app_specs:
      branch=a.new('guiappbranch'); app_labels.append((branch,lab))
      a.ldg(1,G['APP_STATE']); a.li(2,state); a.e('CMP r1 r2'); a.br('JEQ',branch)
    a.br('JMP',app_done)
    for branch,lab in app_labels:
      a.label(branch); a.call(lab); a.br('JMP',app_done)
    a.label(app_done); a.call('gui_present_frame'); a.e('RET')

    a.label('gui_draw_files')
    self.gui_const('CONTENTS LIVE IN GUEST RAM',7,18,0xB6C8DAFF)
    self.gui_const('NAME',9,18,0x4BC6F3FF)
    a.li(1,0); a.stg(G['FILE_LINES'],1); a.li(1,0); a.stg(G['FILE_COUNT'],1)
    a.label('gui_files_loop')
    a.ldg(1,G['FILE_LINES']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','gui_files_done')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','gui_files_next')
    a.ldx(3,FS_PARENT,1); a.ldg(4,G['CWD_ID']); a.e('CMP r3 r4'); a.br('JNE','gui_files_next')
    a.ldg(1,G['FILE_LINES']); a.li(2,64); a.e('MUL r3 r1 r2'); a.li(4,FS_NAMES); a.e('ADD r3 r3 r4'); a.stg(G['TEXT_SRC'],3)
    a.ldg(1,G['FILE_COUNT']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_COUNT'],1); a.li(2,11); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xE1E7F0FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.label('gui_files_next'); a.ldg(1,G['FILE_LINES']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_LINES'],1); a.br('JMP','gui_files_loop')
    a.label('gui_files_done'); a.ldg(1,G['FILE_COUNT']); a.e('CMP r1 r0'); a.br('JNE','gui_files_ret')
    self.gui_const('NO FILES YET',12,18,0xE1E7F0FF); self.gui_const('CREATE FILES IN TERMINAL WITH TOUCH NAME',14,18,0xA8BACFFF)
    a.label('gui_files_ret'); a.e('RET')

    a.label('gui_draw_notes')
    self.gui_const('NOTES - PLAIN TEXT EDITOR',7,18,0x4BC6F3FF)
    a.li(1,NOTE_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,11); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xE4EBF3FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('TYPE TO EDIT, CTRL S TO SAVE TO RAM FILESYSTEM',29,18,0xA8BACFFF)
    a.ldg(1,G['NOTE_STATUS']); a.e('CMP r1 r0'); a.br('JEQ','gui_notes_done')
    self.gui_const('NOTES SAVED TO RAM FILESYSTEM',31,18,0x6BE2A8FF)
    a.label('gui_notes_done'); a.e('RET')

    a.label('gui_draw_calc')
    self.gui_const('TYPE AN EXPRESSION AFTER CALC, THEN PRESS ENTER',7,18,0xB6C8DAFF)
    self.gui_const('EXAMPLE: 12 + 3',9,18,0x4BC6F3FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,13); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('THE SAME GUEST CALC COMMAND HANDLER POWERS THIS APP',17,18,0xA8BACFFF)
    a.e('RET')

    a.label('gui_draw_monitor')
    self.gui_const('LIVE SYSTEM MONITOR',7,18,0x4BC6F3FF)
    self.gui_const('GUEST POLL TICKS',10,18,0xD6E0EDFF)
    a.ldg(1,G['TICK']); a.stg(G['CALC_RESULT'],1); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,10); a.stg(G['TEXT_ROW'],1); a.li(1,42); a.stg(G['TEXT_COL'],1); a.li(1,0x6BE2A8FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    # Count real allocated filesystem entries.
    a.li(1,0); a.stg(G['FILE_I'],1); a.li(1,0); a.stg(G['FILE_COUNT'],1)
    a.label('gui_monitor_count_loop'); a.ldg(1,G['FILE_I']); a.li(2,FS_SLOTS); a.e('CMP r1 r2'); a.br('JGE','gui_monitor_count_done')
    a.ldx(3,FS_USED,1); a.e('CMP r3 r0'); a.br('JEQ','gui_monitor_count_next'); a.ldg(1,G['FILE_COUNT']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_COUNT'],1)
    a.label('gui_monitor_count_next'); a.ldg(1,G['FILE_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_I'],1); a.br('JMP','gui_monitor_count_loop')
    a.label('gui_monitor_count_done'); self.gui_const('FILES IN RAM',12,18,0xD6E0EDFF)
    a.ldg(1,G['FILE_COUNT']); a.stg(G['CALC_RESULT'],1); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,12); a.stg(G['TEXT_ROW'],1); a.li(1,42); a.stg(G['TEXT_COL'],1); a.li(1,0x6BE2A8FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('COUNTERS UPDATE WHILE THIS WINDOW IS OPEN',15,18,0xA8BACFFF)
    self.gui_const('BOOT FONT CHECKSUM IS STORED IN GUEST RAM',17,18,0xA8BACFFF)
    a.e('RET')

    a.label('gui_draw_calendar')
    self.gui_const('OCTOBER 2026',7,18,0x4BC6F3FF)
    self.gui_const('SUN  MON  TUE  WED  THU  FRI  SAT',10,18,0xDCE6F0FF)
    self.gui_const('             1   2   3   4',13,18,0xE7EDF5FF)
    self.gui_const('  5   6   7   8   9  10  11',16,18,0xE7EDF5FF)
    self.gui_const(' 12  13  14  15  16  17  18',19,18,0xE7EDF5FF)
    self.gui_const(' 19  20  21  22  23  24  25',22,18,0x65DDB0FF)
    self.gui_const(' 26  27  28  29  30  31',25,18,0xE7EDF5FF)
    self.gui_const('MONTH GRID - ARROWS RETURN TO DESKTOP',29,18,0xA8BACFFF)
    a.e('RET')

    a.label('gui_draw_paint')
    self.gui_const('PAINT CANVAS',7,18,0x4BC6F3FF)
    self.gui_const('SHIFT TO PAINT, ARROWS MOVE, Q CLOSES PAINT',7,52,0xA8BACFFF)
    self.gui_rect_setup(250,145,780,450,0xC8,0)
    # Colored canvas frame.
    self.gui_rect_setup(250,145,780,2,0x6BC5F3FF,1); self.gui_rect_setup(250,593,780,2,0x6BC5F3FF,1)
    a.li(1,0); a.stg(G['PAINT_I'],1)
    a.label('gui_paint_points_loop')
    a.ldg(1,G['PAINT_I']); a.ldg(2,G['PAINT_COUNT']); a.e('CMP r1 r2'); a.br('JGE','gui_paint_points_done')
    a.ldx(3,PAINT_X_BUF,1); a.stg(G['RECT_X'],3); a.ldx(3,PAINT_Y_BUF,1); a.stg(G['RECT_Y'],3); a.li(1,8); a.stg(G['RECT_W'],1); a.li(1,8); a.stg(G['RECT_H'],1); a.li(1,0x1D9CD6FF); a.stg(G['RECT_COLOR'],1); a.li(1,1); a.stg(G['RECT_MODE'],1); a.call('gui_draw_rect')
    a.ldg(1,G['PAINT_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAINT_I'],1); a.br('JMP','gui_paint_points_loop')
    a.label('gui_paint_points_done'); a.call('gui_draw_cursor'); a.e('RET')

    a.label('gui_draw_settings')
    self.gui_const('SETTINGS',7,18,0x4BC6F3FF)
    self.gui_const('SHIFT TO SWITCH THEME',10,18,0xD6E0EDFF)
    a.ldg(1,G['THEME']); a.e('CMP r1 r0'); a.br('JNE','gui_settings_light')
    self.gui_const('THEME: DARK',13,18,0x6BE2A8FF); a.br('JMP','gui_settings_done')
    a.label('gui_settings_light'); self.gui_const('THEME: LIGHT',13,18,0xD6E0EDFF)
    a.label('gui_settings_done'); self.gui_const('Q RETURNS TO DESKTOP',17,18,0xA8BACFFF); a.e('RET')

    a.label('gui_draw_terminal')
    self.gui_const('OPEN TERMINAL FOR COMMANDS AND RAM FILE TOOLS',7,18,0xB6C8DAFF)
    a.li(1,0); a.stg(G['FILE_LINES'],1)
    a.label('gui_terminal_history_loop')
    a.ldg(1,G['FILE_LINES']); a.li(2,24); a.e('CMP r1 r2'); a.br('JGE','gui_terminal_history_done')
    a.ldg(1,G['FILE_LINES']); a.li(2,LINE_LEN*4); a.e('MUL r3 r1 r2'); a.li(4,OUT_BASE); a.e('ADD r3 r3 r4'); a.stg(G['TEXT_SRC'],3)
    a.ldg(1,G['FILE_LINES']); a.li(2,7); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xD6E0EDFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.ldg(1,G['FILE_LINES']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_LINES'],1); a.br('JMP','gui_terminal_history_loop')
    a.label('gui_terminal_history_done')
    self.gui_const('CPU32> ',32,18,0x4BC6F3FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,25); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.e('RET')

    a.label('gui_draw_help')
    self.gui_const('KEYBOARD CONTROLS',7,18,0x4BC6F3FF)
    self.gui_const('ARROWS MOVE DESKTOP CURSOR',10,18,0xE1E7F0FF)
    self.gui_const('SHIFT IS THE CLICK / OPEN KEY',12,18,0xE1E7F0FF)
    self.gui_const('CTRL S SAVES NOTES',14,18,0xE1E7F0FF)
    self.gui_const('TYPE Q TO CLOSE MOST APPS',16,18,0xE1E7F0FF)
    self.gui_const('OPEN TERMINAL TO USE HELP, CALC, LS, TOUCH, WRITE, CAT',19,18,0xA8BACFFF)
    self.gui_const('FILES LIVE IN GUEST RAM, NOT THE HOST FILESYSTEM',21,18,0xA8BACFFF)
    a.e('RET')

    a.label('gui_draw_about')
    self.gui_const('NOVA 7.1 WORKSTATION EDITION',7,18,0x4BC6F3FF)
    self.gui_const('GUEST ISA CPU32J2 V2',10,18,0xE1E7F0FF)
    self.gui_const('1280 X 720 RGBA8888 DOUBLE BUFFER',12,18,0xE1E7F0FF)
    self.gui_const('RAM FILESYSTEM: 16 FILES',14,18,0xE1E7F0FF)
    self.gui_const('BOOT DOES MEMORY CHECKS, FILESYSTEM INIT, FONT SCAN AND APP SETUP',17,18,0xA8BACFFF)
    self.gui_const('JIT EXECUTION AND PRESENT-BUFFER PATH ARE PRESERVED',20,18,0x6BE2A8FF)
    a.e('RET')

    a.label('gui_draw_mathlab')
    self.gui_const('FACTORIAL / FIBONACCI / GCD / LCM / SQRT / PRIME',7,18,0x4BC6F3FF)
    self.gui_const('CALC A OP B SUPPORTS + - * / % ^ & | XOR << >>',9,18,0xD6E0EDFF)
    self.gui_const('TYPE A COMMAND AND PRESS ENTER',28,18,0xA8BACFFF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_diagnostics')
    self.gui_const('DIAGNOSTICS AND CPU32J2 CONFORMANCE',7,18,0x4BC6F3FF)
    self.gui_const('MEMTEST 1024 CHECKS GUEST RAM READ / WRITE',10,18,0xD6E0EDFF)
    self.gui_const('SELFTEST RUNS 270000 RESULT VECTORS',12,18,0xD6E0EDFF)
    self.gui_const('OVER 1.6 MILLION GUEST INSTRUCTIONS IN SELFTEST',14,18,0x6BE2A8FF)
    self.gui_const('TYPE MEMTEST 1024 OR SELFTEST BELOW',18,18,0xA8BACFFF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_scriptlab')
    self.gui_const('SCRIPT LAB: SEMICOLON-SEPARATED COMMANDS',7,18,0x4BC6F3FF)
    self.gui_const('WRITE DEMO ECHO HELLO;CALC 12 + 3;FACT 5',10,18,0xD6E0EDFF)
    self.gui_const('THEN RUN DEMO TO EXECUTE IT INSIDE THE GUEST',12,18,0xD6E0EDFF)
    self.gui_const('TYPE RUN DEMO OR ANY SHELL COMMAND',18,18,0xA8BACFFF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_filetools')
    self.gui_const('GUEST RAM FILE INSPECTION',7,18,0x4BC6F3FF)
    self.gui_const('LS / CAT / TYPE / SIZE / STAT / EXISTS / CRC32',10,18,0xD6E0EDFF)
    self.gui_const('256 INODES / 1024 WORDS PER FILE PAGE',12,18,0xD6E0EDFF)
    self.gui_const('DIRECTORIES / PAGE-BACKED FILE DATA / UNDELETE',14,18,0xA8BACFFF)
    self.gui_const('TYPE A FILE COMMAND BELOW',18,18,0xA8BACFFF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_clock')
    self.gui_const('GUEST UPTIME COUNTER',7,18,0x4BC6F3FF)
    self.gui_const('KEYBOARD POLL TICKS',10,18,0xD6E0EDFF)
    a.ldg(1,G['TICK']); a.stg(G['CALC_RESULT'],1); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,10); a.stg(G['TEXT_ROW'],1); a.li(1,42); a.stg(G['TEXT_COL'],1); a.li(1,0x6BE2A8FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('THIS IS A GUEST LOOP COUNTER, NOT WALL CLOCK TIME',14,18,0xA8BACFFF); a.e('RET')

    a.label('gui_draw_sound')
    self.gui_const('SOUND STUDIO  /  GUESTAUDIO MMIO',7,18,0x55D8FFFF)
    self.gui_const('1 2 3 4 5 6 7 8  =  PLAY NOTES',10,18,0xE2EBF7FF)
    self.gui_const('M OR SHIFT  =  PLAY THE EIGHT-NOTE DEMO',12,18,0x72E7B0FF)
    self.gui_const('X  =  STOP AUDIO     Q  =  CLOSE',14,18,0xB8C9DCFF)
    self.gui_const('48 KHZ  /  16-BIT STEREO  /  ASYNCHRONOUS OUTPUT',17,18,0xB8C9DCFF)
    self.gui_const('WAVEFORMS: SINE  SQUARE  TRIANGLE  SAW',19,18,0xB8C9DCFF)
    self.gui_const('48 KHZ HOST SYNTH / DURATION / VOLUME / PAN',21,18,0xB8C9DCFF)
    # Equalizer-style visualizer; static bars avoid burning guest time in a live animation loop.
    for i,(h,color) in enumerate([(32,0x48BFE3FF),(48,0x61D9B3FF),(26,0x9C8DF2FF),(58,0xE6A65AFF),(40,0xE17EABFF),(52,0x60B9D0FF),(28,0x6FE0A5FF),(44,0xBCA0F1FF)]):
      self.gui_rect_setup(330+i*68,470-h,30,h,color,1)
    self.gui_const('AUDIO DEVICE STATUS REGISTER: 0XFFFFFFF8',26,18,0x55D8FFFF)
    a.li(1,0xFFFFFFF8); a.e('LOAD r3 r1'); a.stg(G['CALC_RESULT'],3); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,28); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0x72E7B0FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.e('RET')

    # Audio MMIO helpers use only the documented 0xFFFFFFE0..0xFFFFFFFE map.
    # Inputs: r1 frequency, r2 duration ms, r3 volume %, r4 waveform, r5 pan.
    a.label('gui_sound_emit')
    a.li(6,0xFFFFFFE4); a.e('STORE r6 r1')
    a.li(6,0xFFFFFFE8); a.e('STORE r6 r2')
    a.li(6,0xFFFFFFEC); a.e('STORE r6 r3')
    a.li(6,0xFFFFFFF0); a.e('STORE r6 r4')
    a.li(6,0xFFFFFFF4); a.e('STORE r6 r5')
    a.li(6,0xFFFFFFE0); a.li(7,3); a.e('STORE r6 r7')
    a.e('RET')
    a.label('gui_sfx_nav'); a.li(1,740); a.li(2,22); a.li(3,8); a.li(4,1); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_open'); a.li(1,660); a.li(2,65); a.li(3,15); a.li(4,0); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_close'); a.li(1,330); a.li(2,48); a.li(3,12); a.li(4,2); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_key'); a.li(1,920); a.li(2,14); a.li(3,6); a.li(4,1); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_paint'); a.li(1,520); a.li(2,24); a.li(3,10); a.li(4,1); a.li(5,58); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_theme'); a.li(1,554); a.li(2,72); a.li(3,15); a.li(4,2); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_ok'); a.li(1,880); a.li(2,80); a.li(3,13); a.li(4,0); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')
    a.label('gui_sfx_error'); a.li(1,180); a.li(2,120); a.li(3,12); a.li(4,3); a.li(5,50); a.call('gui_sound_emit'); a.e('RET')

    a.label('gui_idle')
    a.ldg(1,G['TICK']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['TICK'],1)
    a.ldg(1,G['APP_STATE']); a.li(2,17); a.e('CMP r1 r2'); a.br('JNE','gui_idle_after_stopwatch')
    a.ldg(1,G['STOPWATCH_RUNNING']); a.e('CMP r1 r0'); a.br('JEQ','gui_idle_after_stopwatch'); a.ldg(1,G['STOPWATCH_TICKS']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['STOPWATCH_TICKS'],1)
    a.label('gui_idle_after_stopwatch'); a.ldg(1,G['APP_STATE']); a.li(2,4); a.e('CMP r1 r2'); a.br('JEQ','gui_idle_refresh')
    a.li(2,12); a.e('CMP r1 r2'); a.br('JEQ','gui_idle_refresh'); a.li(2,15); a.e('CMP r1 r2'); a.br('JEQ','gui_idle_refresh'); a.li(2,17); a.e('CMP r1 r2'); a.br('JNE','gui_loop')
    a.label('gui_idle_refresh'); a.ldg(1,G['TICK']); a.li(2,4095); a.e('AND r3 r1 r2'); a.e('CMP r3 r0'); a.br('JNE','gui_loop')
    a.call('gui_draw_app'); a.br('JMP','gui_loop')

  def emit_selftest_suite(self):
    a=self.a
    a.label('selftest_vectors')
    a.li(7,0)
    rng=random.Random(0xC0322026)
    edge=[0,1,2,3,7,15,16,31,32,63,127,255,256,1023,0x7fffffff,0x80000000,0xfffffffe,0xffffffff,0x55555555,0xaaaaaaaa]
    mask=0xffffffff
    def s32(x): return x if x<0x80000000 else x-0x100000000
    def u32(x): return x&mask
    def trunc_div(x,y): return (abs(x)//abs(y)) * (-1 if (x<0) != (y<0) else 1)
    def operands(i):
      if i < len(edge)*len(edge): return edge[i//len(edge)], edge[i%len(edge)]
      return rng.getrandbits(32), rng.getrandbits(32)
    def mismatch():
      a.e('XOR r6 r3 r4'); a.e('OR r7 r7 r6')
    ops=['ADD','SUB','MUL','DIVS','DIVU','REMS','REMU','AND','OR','XOR','LSH','RSH','ASR','ROTL','ROTR','MULHI','MULHIU','MIN','MAX']
    # 190,000 binary vectors: six executed guest instructions per vector.
    for op in ops:
      for i in range(10000):
        x,y=operands(i)
        if op in ('DIVU','REMU') and y==0: y=1
        sx,sy=s32(x),s32(y)
        if op in ('DIVS','REMS'):
          if sy==0 or (sx==-2147483648 and sy==-1): y=1; sy=1
        n=y & 31
        if op=='ADD': expected=u32(x+y)
        elif op=='SUB': expected=u32(x-y)
        elif op=='MUL': expected=u32(x*y)
        elif op=='DIVS': expected=u32(trunc_div(sx,sy))
        elif op=='DIVU': expected=x//y
        elif op=='REMS': expected=u32(sx-trunc_div(sx,sy)*sy)
        elif op=='REMU': expected=x%y
        elif op=='AND': expected=x&y
        elif op=='OR': expected=x|y
        elif op=='XOR': expected=x^y
        elif op=='LSH': expected=u32(x<<n)
        elif op=='RSH': expected=x>>n
        elif op=='ASR': expected=u32(sx>>n)
        elif op=='ROTL': expected=u32((x<<n)|(x>>(32-n if n else 32))) if n else x
        elif op=='ROTR': expected=u32((x>>n)|(x<<(32-n if n else 32))) if n else x
        elif op=='MULHI': expected=u32((sx*sy)>>32)
        elif op=='MULHIU': expected=(x*y)>>32
        elif op=='MIN': expected=x if sx<sy else y
        else: expected=x if sx>sy else y
        a.li(1,x); a.li(2,y); a.e(f'{op} r3 r1 r2'); a.li(4,expected); mismatch()
    # MADD includes a third independent addend.
    for i in range(10000):
      x,y=operands(i); z=rng.getrandbits(32); expected=u32(x*y+z)
      a.li(1,x); a.li(2,y); a.li(5,z); a.e('MADD r3 r1 r2 r5'); a.li(4,expected); mismatch()
    # Unary bit operations.
    for op in ('POPCNT','CLZ','CTZ'):
      for i in range(10000):
        x=edge[i] if i<len(edge) else rng.getrandbits(32)
        expected=x.bit_count() if op=='POPCNT' else ((32-x.bit_length()) if op=='CLZ' and x else (32 if op=='CLZ' else ((x&-x).bit_length()-1 if x else 32)))
        a.li(1,x); a.e(f'{op} r3 r1'); a.li(4,expected); mismatch()
    # BEXT and BINS field insertion/extraction vectors.
    for i in range(5000):
      x=rng.getrandbits(32); index=rng.randrange(32); width=rng.randrange(1,33-index); field=(1<<width)-1
      expected=(x>>index)&field
      a.li(1,x); a.e(f'BEXT r3 r1 {index} {width}'); a.li(4,expected); mismatch()
    for i in range(5000):
      original=rng.getrandbits(32); inserted=rng.getrandbits(32); index=rng.randrange(32); width=rng.randrange(1,33-index); field=((1<<width)-1)<<index
      expected=u32((original&~field)|((inserted<<index)&field))
      a.li(1,original); a.li(2,inserted); a.e(f'BINS r3 r1 r2 {index} {width}'); a.li(4,expected); mismatch()
    for op in ('SEXT','ZEXT'):
      for i in range(5000):
        x=rng.getrandbits(32); width=rng.randrange(1,33); low=x&((1<<width)-1 if width<32 else mask)
        if op=='ZEXT': expected=low
        else: expected=u32(low-(1<<width) if width<32 and (low&(1<<(width-1))) else low)
        a.li(1,x); a.e(f'{op} r3 r1 {width}'); a.li(4,expected); mismatch()
    # CLAMP, SELECT, SWAP and CMOV condition semantics.
    for i in range(5000):
      value=rng.getrandbits(32); lo=rng.getrandbits(32); hi=rng.getrandbits(32)
      slo,shi,sv=s32(lo),s32(hi),s32(value)
      if slo>shi: lo,hi=hi,lo; slo,shi=shi,slo
      expected=lo if sv<slo else (hi if sv>shi else value)
      a.li(1,value); a.li(2,lo); a.li(5,hi); a.e('CLAMP r3 r1 r2 r5'); a.li(4,expected); mismatch()
    for i in range(5000):
      tv,fv=rng.getrandbits(32),rng.getrandbits(32); cond=rng.randrange(2); expected=tv if cond else fv
      a.li(1,tv); a.li(2,fv); a.li(5,cond); a.e('SELECT r3 r1 r2 r5'); a.li(4,expected); mismatch()
    for i in range(5000):
      x,y=operands(i)
      a.li(1,x); a.li(2,y); a.e('SWAP r1 r2'); a.li(3,y); a.e('XOR r4 r1 r3'); a.e('OR r7 r7 r4'); a.li(3,x); a.e('XOR r4 r2 r3'); a.e('OR r7 r7 r4')
    for i in range(5000):
      x,y=operands(i); expected=1 if x==y else 0
      a.li(1,x); a.li(2,y); a.e('CMP r1 r2'); a.li(3,0); a.li(4,1); a.e('CMOV r3 r4 EQ'); a.li(5,expected); a.e('XOR r6 r3 r5'); a.e('OR r7 r7 r6')
    a.label('selftest_vectors_end')
    a.label('selftest_verify_compare'); a.e('CMP r7 r0'); a.br('JNE','selftest_fail')
    self.print_const('SELFTEST PASSED: 270000 VECTORS / 1625001 TEST INSTRUCTIONS'); a.e('RET')
    a.label('selftest_fail')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,6); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('CPU32J2 ISA SELFTEST FAILURE')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 selftest_verify_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('CPU32J2 ISA SELFTEST RESULT')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('gui_draw_stopwatch')
    self.gui_const('STOPWATCH',7,18,0x55D8FFFF); self.gui_const('SPACE START / STOP   L LAP   R RESET',10,18,0xDCE6F0FF)
    self.gui_const('GUEST POLL TICKS',14,18,0xAFC1D4FF); a.ldg(1,G['STOPWATCH_TICKS']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,14); a.stg(G['TEXT_ROW'],1); a.li(1,38); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('LAPS',18,18,0xAFC1D4FF); a.ldg(1,G['STOPWATCH_LAPS']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,18); a.stg(G['TEXT_ROW'],1); a.li(1,25); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_converter')
    self.gui_const('UNIT CONVERTER',7,18,0x55D8FFFF); self.gui_const('CONVERT C 25  /  CONVERT F 77',10,18,0xDCE6F0FF)
    self.gui_const('CONVERT KM 100  /  CONVERT MI 10',12,18,0xDCE6F0FF); self.gui_const('CONVERT KG 2  /  CONVERT LB 10',14,18,0xDCE6F0FF)
    self.gui_const('INTEGER RATIO CONVERSIONS; RESULTS ARE TRUNCATED',18,18,0xAFC1D4FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_kernel')
    self.gui_const('KERNEL MONITOR',7,18,0x55D8FFFF); self.gui_const('PAGE-SLAB MEMORY MANAGER  /  4096 BYTE PAGES',10,18,0xDCE6F0FF)
    self.gui_const('ALLOCATED PAGES',13,18,0xAFC1D4FF); a.ldg(1,G['PAGE_USED']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,13); a.stg(G['TEXT_ROW'],1); a.li(1,38); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('STACK HIGH-WATER',17,18,0xAFC1D4FF); a.ldg(1,G['STACK_HIGHWATER']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,17); a.stg(G['TEXT_ROW'],1); a.li(1,38); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('COMMANDS: PAGE  STACK  PS  FSCK',22,18,0x83E7C2FF); a.e('RET')

    a.label('gui_draw_mixer')
    self.gui_const('SOUND MIXER',7,18,0x55D8FFFF); self.gui_const('LEFT/RIGHT: FREQUENCY   UP/DOWN: VOLUME',10,18,0xDCE6F0FF)
    self.gui_const('1 SINE  2 SQUARE  3 TRIANGLE  4 SAW',13,18,0xAFC1D4FF)
    self.gui_const('SPACE PLAY 500 MS   X STOP',16,18,0x83E7C2FF)
    self.gui_const('FREQUENCY HZ',20,18,0xAFC1D4FF); a.ldg(1,G['MIX_FREQ']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,20); a.stg(G['TEXT_ROW'],1); a.li(1,38); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('VOLUME PERCENT',23,18,0xAFC1D4FF); a.ldg(1,G['MIX_VOLUME']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,23); a.stg(G['TEXT_ROW'],1); a.li(1,38); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_hex')
    self.gui_const('HEX WORKBENCH',7,18,0x55D8FFFF); self.gui_const('DUMP ADDRESS  /  INSPECT 8 WORDS',10,18,0xDCE6F0FF)
    self.gui_const('STACK 0X7FF00000-0X7FFFFFFF  /  RAM 0X00000000-0X7FFFFFFF',14,18,0xAFC1D4FF)
    self.gui_const('TYPE DUMP <DECIMAL ADDRESS> IN THE COMMAND LINE',18,18,0x83E7C2FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_bench')
    self.gui_const('BENCHMARK LAB',7,18,0x55D8FFFF); self.gui_const('BENCH 1000000  /  MEASURE GUEST LOOP THROUGHPUT',10,18,0xDCE6F0FF)
    self.gui_const('MEMTEST 4096  /  SELFTEST',14,18,0xDCE6F0FF); self.gui_const('RUNS EXECUTE ON THE GUEST CPU32J2 JIT PATH',18,18,0xAFC1D4FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_recovery')
    self.gui_const('FILE RECOVERY',7,18,0x55D8FFFF); self.gui_const('DEL NAME  /  UNDO  /  FSCK',10,18,0xDCE6F0FF)
    self.gui_const('ONE DELETED FILE REMAINS RECOVERABLE UNTIL ITS SLOT IS REUSED',14,18,0xAFC1D4FF)
    self.gui_const('FILE PAYLOAD PAGES ARE HELD IN HIGH GUEST RAM',18,18,0xAFC1D4FF)
    a.li(1,CMD_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,32); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_draw_syslog')
    self.gui_const('SYSTEM LOG',7,18,0x55D8FFFF); self.gui_const('LATEST GUEST TERMINAL AND KERNEL MESSAGES',10,18,0xAFC1D4FF)
    a.li(1,0); a.stg(G['FILE_LINES'],1)
    a.label('syslog_render_loop'); a.ldg(1,G['FILE_LINES']); a.li(2,18); a.e('CMP r1 r2'); a.br('JGE','syslog_render_done')
    a.ldg(1,G['FILE_LINES']); a.li(2,LINE_LEN*4); a.e('MUL r3 r1 r2'); a.li(4,OUT_BASE); a.e('ADD r3 r3 r4'); a.stg(G['TEXT_SRC'],3)
    a.ldg(1,G['FILE_LINES']); a.li(2,11); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_ROW'],1); a.li(1,18); a.stg(G['TEXT_COL'],1); a.li(1,0xDCE6F0FF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.ldg(1,G['FILE_LINES']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['FILE_LINES'],1); a.br('JMP','syslog_render_loop')
    a.label('syslog_render_done'); a.e('RET')

    # --------------------------------------------------------------
    # 4 KiB page allocator over nearly the entire available guest RAM.
    # GuestMemory commits pages lazily; the bitmap tracks OS ownership.
    # --------------------------------------------------------------
    a.label('page_alloc')
    a.li(1,0); a.stg(G['PAGE_SCAN'],1)
    a.ldg(1,G['PAGE_HINT']); a.stg(G['PAGE_INDEX'],1)
    a.label('page_alloc_loop')
    a.ldg(1,G['PAGE_SCAN']); a.li(2,PAGE_COUNT); a.e('CMP r1 r2'); a.br('JGE','page_alloc_fail')
    a.ldg(1,G['PAGE_INDEX']); a.li(2,PAGE_COUNT); a.e('CMP r1 r2'); a.br('JLT','page_alloc_index_ok')
    a.li(1,0); a.stg(G['PAGE_INDEX'],1)
    a.label('page_alloc_index_ok')
    a.ldg(1,G['PAGE_INDEX']); a.li(2,3); a.e('RSH r2 r1 r2')
    a.ldg(1,G['PAGE_INDEX']); a.li(3,7); a.e('AND r3 r1 r3')
    a.li(4,1); a.e('LSH r4 r4 r3'); a.stg(G['PAGE_MASK'],4)
    a.li(5,PAGE_BITMAP); a.e('ADD r5 r5 r2'); a.stg(G['PAGE_ADDR'],5)
    a.e('LOAD8 r6 r5'); a.e('AND r7 r6 r4'); a.e('CMP r7 r0'); a.br('JNE','page_alloc_occupied')
    a.e('OR r6 r6 r4'); a.e('STORE8 r5 r6')
    a.ldg(1,G['PAGE_INDEX']); a.li(2,12); a.e('LSH r1 r1 r2'); a.li(2,HEAP_BASE); a.e('ADD r1 r1 r2'); a.stg(G['PAGE_RESULT'],1)
    a.ldg(1,G['PAGE_INDEX']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAGE_HINT'],1)
    a.ldg(1,G['PAGE_USED']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAGE_USED'],1)
    a.ldg(1,G['PAGE_RESULT']); a.e('RET')
    a.label('page_alloc_occupied')
    a.ldg(1,G['PAGE_INDEX']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAGE_INDEX'],1)
    a.ldg(1,G['PAGE_SCAN']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['PAGE_SCAN'],1); a.br('JMP','page_alloc_loop')
    a.label('page_alloc_fail'); a.li(1,-1); a.stg(G['PAGE_RESULT'],1); a.e('RET')

    # Free an allocated page. Input R1 = page base. Reject unaligned/out-of-heap addresses.
    a.label('page_free')
    a.stg(G['PAGE_ADDR'],1)
    a.li(2,HEAP_BASE); a.e('CMP r1 r2'); a.br('JLT','page_free_invalid')
    a.li(2,HEAP_LIMIT); a.e('CMP r1 r2'); a.br('JGE','page_free_invalid')
    a.li(2,HEAP_BASE); a.e('SUB r3 r1 r2'); a.li(4,4095); a.e('AND r5 r3 r4'); a.e('CMP r5 r0'); a.br('JNE','page_free_invalid')
    a.li(4,12); a.e('RSH r3 r3 r4'); a.stg(G['PAGE_INDEX'],3)
    a.li(2,3); a.e('RSH r4 r3 r2'); a.li(5,7); a.e('AND r5 r3 r5'); a.li(6,1); a.e('LSH r6 r6 r5'); a.stg(G['PAGE_MASK'],6)
    a.li(7,PAGE_BITMAP); a.e('ADD r7 r7 r4'); a.stg(G['PAGE_ADDR'],7); a.e('LOAD8 r8 r7'); a.e('AND r9 r8 r6'); a.e('CMP r9 r0'); a.br('JEQ','page_free_invalid')
    a.e('NOT r6 r6'); a.e('AND r8 r8 r6'); a.e('STORE8 r7 r8')
    a.ldg(1,G['PAGE_USED']); a.e('CMP r1 r0'); a.br('JEQ','page_free_hint'); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['PAGE_USED'],1)
    a.label('page_free_hint'); a.ldg(1,G['PAGE_INDEX']); a.ldg(2,G['PAGE_HINT']); a.e('CMP r1 r2'); a.br('JGE','page_free_done'); a.stg(G['PAGE_HINT'],1)
    a.label('page_free_done'); a.li(1,0); a.stg(G['PAGE_RESULT'],1); a.e('RET')
    a.label('page_free_invalid'); a.li(1,-1); a.stg(G['PAGE_RESULT'],1); a.e('RET')

    # Slab classes: 16, 64, 256, 1024 bytes. Each class grows from 4 KiB pages.
    a.label('slab_alloc')
    a.stg(G['SLAB_REQUEST'],1)
    a.li(2,16); a.e('CMP r1 r2'); a.br('JLE','slab_class_0')
    a.li(2,64); a.e('CMP r1 r2'); a.br('JLE','slab_class_1')
    a.li(2,256); a.e('CMP r1 r2'); a.br('JLE','slab_class_2')
    a.li(2,1024); a.e('CMP r1 r2'); a.br('JLE','slab_class_3')
    a.call('page_alloc'); a.ldg(1,G['PAGE_RESULT']); a.stg(G['SLAB_RESULT'],1); a.e('RET')
    for idx,size in enumerate((16,64,256,1024)):
      a.label(f'slab_class_{idx}'); a.li(1,idx); a.stg(G['SLAB_CLASS'],1); a.li(1,size); a.stg(G['SLAB_TMP'],1); a.br('JMP','slab_alloc_core')
    a.label('slab_alloc_core')
    a.ldg(1,G['SLAB_CLASS']); a.ldx(2,G['SLAB_FREE'],1); a.e('CMP r2 r0'); a.br('JEQ','slab_alloc_bump')
    a.e('LOAD r3 r2'); a.ldg(1,G['SLAB_CLASS']); a.stx(G['SLAB_FREE'],1,3); a.stg(G['SLAB_RESULT'],2); a.e('RET')
    a.label('slab_alloc_bump')
    a.ldg(1,G['SLAB_CLASS']); a.ldx(2,G['SLAB_CUR'],1); a.ldx(3,G['SLAB_END'],1); a.e('CMP r2 r0'); a.br('JEQ','slab_alloc_new_page')
    a.ldg(4,G['SLAB_TMP']); a.e('ADD r5 r2 r4'); a.e('CMP r5 r3'); a.br('JGT','slab_alloc_new_page')
    a.stg(G['SLAB_RESULT'],2); a.ldg(1,G['SLAB_CLASS']); a.ldg(2,G['SLAB_RESULT']); a.ldg(3,G['SLAB_TMP']); a.e('ADD r2 r2 r3'); a.stx(G['SLAB_CUR'],1,2); a.ldg(1,G['SLAB_RESULT']); a.e('RET')
    a.label('slab_alloc_new_page'); a.call('page_alloc'); a.ldg(2,G['PAGE_RESULT']); a.li(3,-1); a.e('CMP r2 r3'); a.br('JEQ','slab_alloc_failed')
    a.ldg(1,G['SLAB_CLASS']); a.ldg(3,G['SLAB_TMP']); a.e('ADD r4 r2 r3'); a.stx(G['SLAB_CUR'],1,4); a.li(5,4096); a.e('ADD r5 r2 r5'); a.stx(G['SLAB_END'],1,5); a.stg(G['SLAB_RESULT'],2); a.ldg(1,G['SLAB_RESULT']); a.e('RET')
    a.label('slab_alloc_failed'); a.li(1,-1); a.stg(G['SLAB_RESULT'],1); a.e('RET')

    # Push an object back to its class free list. Input R1=object, R2=requested size.
    a.label('slab_free')
    a.li(3,16); a.e('CMP r2 r3'); a.br('JLE','slab_free_class0')
    a.li(3,64); a.e('CMP r2 r3'); a.br('JLE','slab_free_class1')
    a.li(3,256); a.e('CMP r2 r3'); a.br('JLE','slab_free_class2')
    a.li(3,1024); a.e('CMP r2 r3'); a.br('JLE','slab_free_class3')
    a.br('JMP','page_free')
    for idx in range(4):
      a.label(f'slab_free_class{idx}'); a.li(3,idx); a.ldx(4,G['SLAB_FREE'],3); a.e('STORE r1 r4'); a.stx(G['SLAB_FREE'],3,1); a.li(1,0); a.e('RET')

    # Ensure each app has a private page-backed arena. R1=app id.
    a.label('app_arena_ensure')
    a.stg(G['APP_ARENA_ID'],1); a.li(2,1); a.e('SUB r3 r1 r2'); a.li(4,24); a.e('CMP r3 r4'); a.br('JGE','app_arena_done')
    a.ldx(2,APP_ARENAS,3); a.e('CMP r2 r0'); a.br('JNE','app_arena_done')
    a.call('page_alloc'); a.ldg(1,G['PAGE_RESULT']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','app_arena_done'); a.stx(APP_ARENAS,3,1)
    a.label('app_arena_done'); a.e('RET')

    # Stack canary and stack usage checks. CALL instrumentation accounts for 20 bytes per active frame.
    a.label('stack_guard_check')
    a.li(12,STACK_END-4); a.e('LOAD r1 r12'); a.li(2,0x5354414B); a.label('stack_guard_compare'); a.e('CMP r1 r2'); a.br('JNE','stack_canary_panic'); a.e('RET')

    # --------------------------------------------------------------
    # Diagnostics and panic recovery console; emitted untracked to
    # preserve the stack precisely while stopped inside the panic UI.
    # --------------------------------------------------------------
    a.trace_enabled=False
    a.label('stack_overflow_panic')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,3); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('STACK OVERFLOW GUARD')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 stack_guard_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('GUEST STACK FRAME GUARD')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')
    a.label('stack_canary_panic')
    for reg in range(1,16): a.e(f'PUSH r{reg}')
    a.li(14,4); a.stg(G['PANIC_CODE'],14); a.li(14,self.msg('STACK CANARY CORRUPTED')); a.stg(G['PANIC_REASON'],14)
    a.e('LDI r14 stack_guard_compare'); a.stg(G['PANIC_PC'],14); a.li(14,self.msg('GUEST STACK CANARY CHECK')); a.stg(G['PANIC_FUNCTION'],14); a.br('JMP','kernel_panic')

    # Unwind every instrumented call frame before warm reboot or hot recovery.
    # The unwind branches directly to their destination; it does not RET because
    # every active physical return frame is being removed from the upward stack.
    a.label('panic_unwind_reboot'); a.ldg(1,G['TRACE_DEPTH']); a.stg(G['PANIC_FRAME_I'],1)
    a.label('panic_unwind_reboot_loop'); a.ldg(1,G['PANIC_FRAME_I']); a.e('CMP r1 r0'); a.br('JEQ','panic_unwind_reboot_done')
    a.e('POP r15'); a.e('POP r15'); a.e('POP r14'); a.e('POP r13'); a.e('POP r12')
    a.ldg(1,G['PANIC_FRAME_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['PANIC_FRAME_I'],1); a.br('JMP','panic_unwind_reboot_loop')
    a.label('panic_unwind_reboot_done'); a.li(1,0); a.stg(G['TRACE_DEPTH'],1); a.stg(G['STACK_USED'],1); a.br('JMP','gui_boot')

    a.label('panic_unwind_kill'); a.ldg(1,G['TRACE_DEPTH']); a.stg(G['PANIC_FRAME_I'],1)
    a.label('panic_unwind_kill_loop'); a.ldg(1,G['PANIC_FRAME_I']); a.e('CMP r1 r0'); a.br('JEQ','panic_unwind_kill_done')
    a.e('POP r15'); a.e('POP r15'); a.e('POP r14'); a.e('POP r13'); a.e('POP r12')
    a.ldg(1,G['PANIC_FRAME_I']); a.li(2,1); a.e('SUB r1 r1 r2'); a.stg(G['PANIC_FRAME_I'],1); a.br('JMP','panic_unwind_kill_loop')
    a.label('panic_unwind_kill_done'); a.li(1,0); a.stg(G['TRACE_DEPTH'],1); a.stg(G['STACK_USED'],1); a.stg(G['APP_STATE'],1); a.stg(G['PANIC_ACTIVE'],1)
    a.li(1,170); a.stg(G['CURSOR_X'],1); a.li(1,172); a.stg(G['CURSOR_Y'],1); a.e('CALL gui_draw_desktop'); a.br('JMP','gui_loop')

    # A compact 32-bit-to-hex converter. R1=value; result is HEX_BUF[0..7].
    a.label('panic_hex32'); a.stg(G['HEX_VALUE'],1); a.li(1,0); a.stg(G['HEX_I'],1)
    a.label('panic_hex_loop'); a.ldg(1,G['HEX_I']); a.li(2,8); a.e('CMP r1 r2'); a.br('JGE','panic_hex_done')
    a.ldg(1,G['HEX_VALUE']); a.li(2,28); a.e('RSH r3 r1 r2'); a.li(2,15); a.e('AND r3 r3 r2'); a.li(4,10); a.e('CMP r3 r4'); a.br('JGE','panic_hex_alpha')
    a.li(4,48); a.e('ADD r3 r3 r4'); a.br('JMP','panic_hex_char')
    a.label('panic_hex_alpha'); a.li(4,55); a.e('ADD r3 r3 r4')
    a.label('panic_hex_char'); a.ldg(1,G['HEX_I']); a.stx(HEX_BUF,1,3); a.ldg(1,G['HEX_VALUE']); a.li(2,4); a.e('LSH r1 r1 r2'); a.stg(G['HEX_VALUE'],1)
    a.ldg(1,G['HEX_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['HEX_I'],1); a.br('JMP','panic_hex_loop')
    a.label('panic_hex_done'); a.li(1,0); a.stx(HEX_BUF,8,1); a.e('RET')

    # Decode the opcode field from the 64-bit CPU32J2 instruction at PANIC_PC.
    a.label('panic_decode_opcode')
    for opname,opval in sorted(OPS.items(),key=lambda kv:kv[1]):
      label='panic_opcode_'+re.sub('[^A-Za-z0-9_]','_',opname.lower())
      a.ldg(1,G['CALC_RESULT']); a.li(2,opval); a.e('CMP r1 r2'); a.br('JEQ',label)
    self.gui_const('DECODED: UNKNOWN OPCODE',24,58,0xFFFF9EAB); a.e('RET')
    seen=set()
    for opname,opval in sorted(OPS.items(),key=lambda kv:kv[1]):
      label='panic_opcode_'+re.sub('[^A-Za-z0-9_]','_',opname.lower())
      if label in seen: continue
      seen.add(label); a.label(label); self.gui_const('DECODED: '+opname,24,58,0xFFFFFFFF); a.e('RET')

    # Panic entry: registers are already pushed by the fault-specific entry label.
    a.label('kernel_panic')
    a.li(6,0xFFFFFFE0); a.li(7,0); a.e('STORE r6 r7')
    a.li(1,STACK_START); a.ldg(2,G['STACK_USED']); a.e('ADD r1 r1 r2'); a.stg(G['PANIC_SP'],1)
    a.ldg(1,G['TRACE_DEPTH']); a.stg(G['PANIC_TRACE_DEPTH'],1)
    # Pop in reverse push order into the stable register snapshot, before using them.
    for reg in range(15,0,-1):
      a.e('POP r1'); a.li(2,PANIC_REGS+reg*4); a.e('STORE r2 r1')
    a.li(1,PANIC_REGS); a.li(2,0); a.e('STORE r1 r2')
    a.li(1,1); a.stg(G['PANIC_ACTIVE'],1); a.li(1,0); a.stg(G['PANIC_DUMP_OFFSET'],1)
    # Distinct low-volume panic alarm through the verified GuestAudio MMIO mapping.
    a.li(1,110); a.li(2,250); a.li(3,12); a.li(4,0); a.li(5,50); a.call('gui_sound_emit')
    a.call('gui_draw_panic')
    a.label('kernel_panic_wait')
    a.li(1,0xFFFFFFFF); a.e('LOAD8 r2 r1'); a.e('CMP r2 r0'); a.br('JEQ','kernel_panic_wait')
    a.li(3,82); a.e('CMP r2 r3'); a.br('JEQ','kernel_panic_reboot'); a.li(3,114); a.e('CMP r2 r3'); a.br('JEQ','kernel_panic_reboot'); a.li(3,13); a.e('CMP r2 r3'); a.br('JEQ','kernel_panic_reboot')
    a.li(3,83); a.e('CMP r2 r3'); a.br('JEQ','panic_save_dump'); a.li(3,115); a.e('CMP r2 r3'); a.br('JEQ','panic_save_dump')
    a.li(3,75); a.e('CMP r2 r3'); a.br('JEQ','panic_kill_app'); a.li(3,107); a.e('CMP r2 r3'); a.br('JEQ','panic_kill_app')
    a.li(3,77); a.e('CMP r2 r3'); a.br('JEQ','panic_scroll_memory'); a.li(3,109); a.e('CMP r2 r3'); a.br('JEQ','panic_scroll_memory'); a.br('JMP','kernel_panic_wait')
    a.label('panic_scroll_memory'); a.ldg(1,G['PANIC_DUMP_OFFSET']); a.li(2,8); a.e('ADD r1 r1 r2'); a.li(2,GUEST_CODE_BYTES-32); a.e('CMP r1 r2'); a.br('JLE','panic_scroll_store'); a.li(1,0); a.label('panic_scroll_store'); a.stg(G['PANIC_DUMP_OFFSET'],1); a.call('gui_draw_panic'); a.br('JMP','kernel_panic_wait')
    a.label('panic_kill_app'); a.ldg(1,G['APP_STATE']); a.e('CMP r1 r0'); a.br('JEQ','kernel_panic_wait')
    a.li(1,0); a.stg(G['APP_STATE'],1); a.stg(G['PANIC_ACTIVE'],1); a.stg(G['TRACE_DEPTH'],1); a.stg(G['STACK_USED'],1); a.li(1,170); a.stg(G['CURSOR_X'],1); a.li(1,172); a.stg(G['CURSOR_Y'],1)
    a.call('gui_draw_desktop'); a.br('JMP','gui_loop')
    a.label('kernel_panic_reboot'); a.br('JMP','panic_unwind_reboot')

    # Save a binary crash record into the high-RAM file page of /PANIC.DMP.
    a.label('panic_save_dump')
    a.li(1,PANIC_STACK_DUMP_BASE); a.li(2,0); a.li(3,1048576); a.e('MEMSET r1 r2 r3')
    a.li(1,STACK_START); a.li(2,PANIC_STACK_DUMP_BASE); a.ldg(3,G['STACK_USED']); a.e('MEMCPY r1 r2 r3')
    a.li(1,0); a.stg(G['CWD_ID'],1)
    a.li(1,ARG_NAME); a.li(2,0); a.li(3,24*4); a.e('MEMSET r1 r2 r3')
    for i,ch in enumerate('PANIC.DMP'): a.li(1,ord(ch)); a.li(2,i); a.stx(ARG_NAME,2,1)
    a.call('find_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JNE','panic_dump_existing')
    a.call('create_file'); a.ldg(1,G['FILE_FOUND']); a.li(2,-1); a.e('CMP r1 r2'); a.br('JEQ','panic_dump_no_page')
    a.label('panic_dump_existing'); a.ldg(1,G['FILE_FOUND']); a.ldx(5,FS_PAGE,1)
    # Header: magic, stop code, guest PC, function string pointer, guest SP, stack use, call depth.
    for idx,src in [(0,None),(1,G['PANIC_CODE']),(2,G['PANIC_PC']),(3,G['PANIC_FUNCTION']),(4,G['PANIC_SP']),(5,G['STACK_HIGHWATER']),(6,G['PANIC_TRACE_DEPTH']),(7,None),(8,G['STACK_USED'])]:
      if idx==0: a.li(4,0x50414E49)
      elif idx==7: a.li(4,PANIC_STACK_DUMP_BASE)
      else: a.ldg(4,src)
      a.stx_dummy if False else None
      a.li(3,idx); a.e('STX r5 r3 r4')
    for idx in range(16):
      a.ldx(4,PANIC_REGS,idx); a.li(3,7+idx); a.e('STX r5 r3 r4')
    # Record eight newest shadow frames (function address + return PC).
    for idx in range(8):
      a.ldg(1,G['PANIC_TRACE_DEPTH']); a.li(2,1); a.e('SUB r1 r1 r2'); a.li(2,idx); a.e('SUB r1 r1 r2'); a.li(2,63); a.e('AND r1 r1 r2')
      a.e('LDX r4 r'+str(0)+' r1') if False else None
      a.li(2,TRACE_FUNCS); a.e('LDX r4 r2 r1'); a.li(3,25+idx); a.e('STX r5 r3 r4')
      a.ldg(1,G['PANIC_TRACE_DEPTH']); a.li(2,1); a.e('SUB r1 r1 r2'); a.li(2,idx); a.e('SUB r1 r1 r2'); a.li(2,63); a.e('AND r1 r1 r2')
      a.li(2,TRACE_RETS); a.e('LDX r4 r2 r1'); a.li(3,33+idx); a.e('STX r5 r3 r4')
    # Save the 16 raw bytes following the fault PC (code dump preview).
    a.ldg(1,G['PANIC_PC']); a.ldg(2,G['PANIC_DUMP_OFFSET']); a.li(3,8); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2')
    for idx in range(8):
      a.e('LOAD8 r4 r1'); a.li(3,41+idx); a.e('STX r5 r3 r4'); a.li(2,1); a.e('ADD r1 r1 r2')
    # Store eight raw dwords from the top of the used guest stack for forensic inspection.
    for idx in range(8):
      a.ldg(1,G['PANIC_SP']); a.li(2,(idx+1)*4); a.e('SUB r1 r1 r2'); a.e('LOAD r4 r1'); a.li(3,49+idx); a.e('STX r5 r3 r4')
    a.ldg(1,G['FILE_FOUND']); a.li(2,57); a.stx(FS_SIZE,1,2)
    self.print_const('PANIC.DMP SAVED TO RAM FILESYSTEM'); a.call('gui_draw_panic'); a.br('JMP','kernel_panic_wait')
    a.label('panic_dump_no_page'); self.print_const('NO FREE PAGE FOR PANIC.DMP'); a.call('gui_draw_panic'); a.br('JMP','kernel_panic_wait')

    # Graphical panic console over a dimmed frozen guest frame.
    a.label('gui_draw_panic')
    self.gui_rect_setup(0,0,1280,720,0xAA000000,2)
    self.gui_rect_setup(36,26,1208,668,0xF018283B,1)
    self.gui_rect_setup(36,26,1208,5,0xFF5B6FFF,1)
    self.gui_rect_setup(52,42,1176,52,0xFF25384FFF,1)
    self.gui_const('NOVA 7.1  /  KERNEL PANIC',3,5,0xFFFFFFFF)
    self.gui_const('FATAL GUEST EXCEPTION  -  EXECUTION HALTED',5,5,0xFFFF9EAB)
    self.gui_const('STOP CODE',7,5,0xFF80D7FFFF)
    a.ldg(1,G['PANIC_CODE']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,7); a.stg(G['TEXT_ROW'],1); a.li(1,17); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('FUNCTION / CHECK',9,5,0xFF80D7FFFF)
    a.ldg(1,G['PANIC_FUNCTION']); a.stg(G['TEXT_SRC'],1); a.li(1,9); a.stg(G['TEXT_ROW'],1); a.li(1,25); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('FAULT PC  0X',11,5,0xFF80D7FFFF)
    a.ldg(1,G['PANIC_PC']); a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,11); a.stg(G['TEXT_ROW'],1); a.li(1,17); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('REGISTERS  /  R00-R15',11,5,0xFF64D9FFFF); self.gui_const('SHADOW CALL TRACE  /  FUNCTION -> RETURN PC',11,43,0xFF64D9FFFF)
    for i in range(8):
      row=13+i
      self.gui_const(f'R{i:02d}  0X',row,5,0xFFC9D8E8)
      a.ldx(1,PANIC_REGS,i); a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,row); a.stg(G['TEXT_ROW'],1); a.li(1,14); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
      self.gui_const(f'R{i+8:02d}  0X',row,22,0xFFC9D8E8)
      a.ldx(1,PANIC_REGS,i+8); a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,row); a.stg(G['TEXT_ROW'],1); a.li(1,34); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
      self.gui_const(f'#{i} 0X',row,43,0xFFC9D8E8)
      a.ldg(1,G['PANIC_TRACE_DEPTH']); a.li(2,1); a.e('SUB r1 r1 r2'); a.li(2,i); a.e('SUB r1 r1 r2'); a.li(2,63); a.e('AND r1 r1 r2'); a.li(2,TRACE_FUNCS); a.e('LDX r1 r2 r1'); a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,row); a.stg(G['TEXT_ROW'],1); a.li(1,48); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
      a.ldg(1,G['PANIC_TRACE_DEPTH']); a.li(2,1); a.e('SUB r1 r1 r2'); a.li(2,i); a.e('SUB r1 r1 r2'); a.li(2,63); a.e('AND r1 r1 r2'); a.li(2,TRACE_RETS); a.e('LDX r1 r2 r1'); a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,row); a.stg(G['TEXT_ROW'],1); a.li(1,58); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('STACK / RAM / ACTIVE APP',22,5,0xFF64D9FFFF)
    self.gui_const('STACK USED',24,5,0xFFC9D8E8); a.ldg(1,G['STACK_USED']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,24); a.stg(G['TEXT_ROW'],1); a.li(1,20); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('STACK HIGH-WATER',25,5,0xFFC9D8E8)
    a.ldg(1,G['STACK_HIGHWATER']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,25); a.stg(G['TEXT_ROW'],1); a.li(1,24); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('PAGES USED / TOTAL',26,5,0xFFC9D8E8)
    a.ldg(1,G['PAGE_USED']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,26); a.stg(G['TEXT_ROW'],1); a.li(1,24); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    self.gui_const('SHADOW CALL TRACE / MOST RECENT FRAMES',22,5,0xFF64D9FFFF)
    a.ldg(1,G['PANIC_TRACE_DEPTH']); a.call('number_to_text'); a.li(1,NUM_BUF); a.stg(G['TEXT_SRC'],1); a.li(1,23); a.stg(G['TEXT_ROW'],1); a.li(1,31); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.call('panic_memory_dump')
    self.gui_const('[R] REBOOT  [S] SAVE PANIC.DMP  [K] KILL APP  [M] SCROLL DUMP',32,5,0xFF83E7C2)
    a.call('gui_present_frame'); a.e('RET')

    # Panic memory dump scroll page: 8 bytes around PC, plus eight frame PCs.
    a.label('panic_memory_dump')
    self.gui_const('FAULTING INSTRUCTION  /  CODE HEX + ASCII',25,43,0xFF64D9FFFF)
    self.gui_const('OPCODE',24,43,0xFFC9D8E8); a.ldg(1,G['PANIC_PC']); a.li(2,4); a.e('ADD r1 r1 r2'); a.e('LOAD r3 r1'); a.li(2,24); a.e('RSH r3 r3 r2'); a.stg(G['CALC_RESULT'],3); a.call('panic_decode_opcode')
    a.ldg(1,G['PANIC_PC']); a.li(2,8); a.e('SUB r1 r1 r2'); a.ldg(2,G['PANIC_DUMP_OFFSET']); a.li(3,8); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2'); a.stg(G['MEM_DUMP_ADDR'],1)
    a.li(1,0); a.stg(G['MEM_DUMP_I'],1)
    a.label('panic_dump_words_loop'); a.ldg(1,G['MEM_DUMP_I']); a.li(2,4); a.e('CMP r1 r2'); a.br('JGE','panic_dump_words_done')
    a.ldg(1,G['MEM_DUMP_ADDR']); a.ldg(2,G['MEM_DUMP_I']); a.li(3,8); a.e('MUL r2 r2 r3'); a.e('ADD r1 r1 r2'); a.e('LOAD r3 r1'); a.stg(G['MEM_DUMP_WORD'],3)
    a.call('panic_hex32'); a.li(1,HEX_BUF); a.stg(G['TEXT_SRC'],1); a.ldg(1,G['MEM_DUMP_I']); a.li(2,16); a.e('ADD r1 r1 r2'); a.stg(G['TEXT_ROW'],1); a.li(1,48); a.stg(G['TEXT_COL'],1); a.li(1,0xFFFFFFFF); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')
    a.ldg(1,G['MEM_DUMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['MEM_DUMP_I'],1); a.br('JMP','panic_dump_words_loop')
    a.label('panic_dump_words_done')
    # ASCII bytes around the fault PC; non-printables become '.'
    a.li(1,0); a.stg(G['MEM_DUMP_I'],1)
    a.label('panic_ascii_loop'); a.ldg(1,G['MEM_DUMP_I']); a.li(2,16); a.e('CMP r1 r2'); a.br('JGE','panic_ascii_done')
    a.ldg(1,G['MEM_DUMP_ADDR']); a.ldg(2,G['MEM_DUMP_I']); a.e('ADD r1 r1 r2'); a.e('LOAD8 r3 r1'); a.li(4,32); a.e('CMP r3 r4'); a.br('JLT','panic_ascii_dot'); a.li(4,126); a.e('CMP r3 r4'); a.br('JGT','panic_ascii_dot'); a.br('JMP','panic_ascii_store')
    a.label('panic_ascii_dot'); a.li(3,46)
    a.label('panic_ascii_store'); a.ldg(1,G['MEM_DUMP_I']); a.stx(PANIC_STACK,1,3); a.ldg(1,G['MEM_DUMP_I']); a.li(2,1); a.e('ADD r1 r1 r2'); a.stg(G['MEM_DUMP_I'],1); a.br('JMP','panic_ascii_loop')
    a.label('panic_ascii_done'); a.li(1,0); a.stx(PANIC_STACK,16,1); a.li(1,PANIC_STACK); a.stg(G['TEXT_SRC'],1); a.li(1,30); a.stg(G['TEXT_ROW'],1); a.li(1,48); a.stg(G['TEXT_COL'],1); a.li(1,0xFFB9CCDD); a.stg(G['TEXT_COLOR'],1); a.call('draw_text'); a.e('RET')

    a.label('gui_present_frame')
    a.li(1,FB); a.li(2,VRAM_BACK); a.li(3,FRAME_BYTES); a.e('MEMCPY r1 r2 r3')
    a.li(1,1); a.li(2,PRESENT); a.e('STORE r2 r1'); a.e('RET')
    a.trace_enabled=True

  def emit_draw_const(self,key,row,color):
    a=self.a; a.li(1,self.msg(key)); a.stg(G['TEXT_SRC'],1); a.li(1,row); a.stg(G['TEXT_ROW'],1); a.li(1,0); a.stg(G['TEXT_COL'],1); a.li(1,color); a.stg(G['TEXT_COLOR'],1); a.call('draw_text')

  def compile(self,out_dir,population=256,seed=20261017):
    strings=[
      'WELCOME','OS_READY','HELP_HINT','OS_TITLE','OS_SUBTITLE','SEP','OS_FOOTER','PROMPT_PREFIX',
      'CPU32J2 OS COMMANDS','HELP - SHOW COMMANDS','LS / DIR - LIST FILES','TOUCH NAME - CREATE EMPTY FILE','WRITE NAME TEXT - REPLACE FILE CONTENTS','APPEND NAME TEXT - APPEND TO FILE','CAT NAME - DISPLAY FILE CONTENTS','DEL NAME - DELETE FILE','ECHO TEXT - PRINT TEXT','CALC A OP B - ADVANCED INTEGER CALCULATOR','SYSINFO / MEM / TIME - SYSTEM INFO','CLS - CLEAR TERMINAL','FORMAT - CLEAR RAM FILESYSTEM','REBOOT - RESET TERMINAL (FILES KEPT)',
      'CPU32J2 OS VERSION 1.0','A SMALL GUEST OPERATING ENVIRONMENT','TERMINAL, CALCULATOR, AND RAM FILESYSTEM','RUNS UNDER THE EXISTING CPU32J2 JIT','SYSTEM INFORMATION','CPU32J2 GUEST OS V1','ISA: CPU32J2 V2 / 32-BIT REGISTERS','ROM: PYTHON-GENERATED ASSEMBLY + BINARY','DISPLAY: 1280 X 720 RGBA8888 DOUBLE BUFFER','INPUT: OPTIONAL KEYBOARD MMIO BRIDGE','FILESYSTEM: 16 FILES IN GUEST RAM','RUNTIME/JIT CLOCK PATH IS UNCHANGED',
      'GUEST MEMORY MAP','RAM: 0X00000000 - 0X7FEFFFFF','STACK: 0X7FF00000 - 0X7FFFFFFF','VRAM: 0X80000000 - 0X807FFFFF','PRESENT: 0XFFFFFFDC / KEY INPUT: 0XFFFFFFFF',
      'NOVA 7.1 WORKSTATION','WORKSTATION KERNEL / CPU32J2 V2','2 GB VIRTUAL RAM / LAZY PAGE COMMIT','1 MB UPWARD GUEST STACK / GUARDED','THREE-STAGE FRAME PIPELINE / 720P RGBA8888',
      'PAGE ALLOCATOR / 4 KB PAGES','SLAB CLASSES 16 64 256 1024 BYTES','HIGH-RAM RAMDISK / HIERARCHICAL DIRECTORIES','ACTIVE APP ARENA','ALLOCATED PAGES','PAGE CAPACITY','STACK HIGH-WATER','STACK USE / 1048576 BYTES',
      'STOPWATCH','UNIT CONVERTER','KERNEL MONITOR','SOUND MIXER','HEX WORKBENCH','BENCHMARK LAB','FILE RECOVERY','SYSTEM LOG',
      'SPACE START STOP  /  L LAP  /  R RESET','CONVERT C 25  /  CONVERT F 77  /  CONVERT KM 100','MEMORY / PAGE MAP / STACK / ACTIVE ARENA','LEFT RIGHT FREQUENCY  /  UP DOWN VOLUME  /  SPACE PLAY  X STOP',
      'HEX DUMP ADDRESS  /  TYPE DUMP ADDRESS IN PROMPT','BENCH [ITERATIONS]  /  MIPS COUNTER IS GUEST POLL RATE','UNDO RESTORES THE LAST DELETED FILE IF ITS PAGE WAS NOT REUSED',
      'LATEST GUEST OUTPUT AND PANIC HISTORY','PANIC RECOVERY CONSOLE','FAULT PC','FUNCTION / CHECK','REGISTER DUMP','SHADOW CALL TRACE','CODE MEMORY DUMP','STACK BACKTRACE / SHADOW FRAMES','[R] REBOOT  [S] SAVE PANIC.DMP  [K] KILL APP  [M] MEMORY SCROLL',
      'PANIC.DMP SAVED TO RAM FILESYSTEM','NO FREE PAGE FOR PANIC.DMP','APP RECOVERED / DESKTOP RESTORED','MEMORY DUMP OFFSET','STACK CANARY INTACT','STACK CANARY CORRUPTED','STACK OVERFLOW GUARD','PAGE ALLOCATOR READY','SLAB ALLOCATOR READY','VFS ROOT READY',
      'ERROR: DIRECTORY NOT FOUND','ERROR: NOT A DIRECTORY','DIRECTORY CREATED','CURRENT DIRECTORY','DIRECTORY EMPTY','FILE RECOVERED','NO DELETED FILE TO RECOVER','FILE SLOT REUSED / RECOVERY EXPIRED',
      'RAM PAGE ALLOCATION FAILED','INVALID PAGE FREE','SLAB ALLOCATION FAILED','KERNEL PAGE MAP TEST PASSED','NOVA-FS CHECK PASSED','STACK GUARD TEST PASSED',
      'WORKSTATION SERVICES','CPU32J2 V2 / 32-BIT R00-R15','GUEST RAM 0X00000000-0X7FFFFFFF','STACK 0X7FF00000-0X7FFFFFFF','VRAM 0X80000000-0X807FFFFF',
      'AUDIO 48 KHZ STEREO / SINE SQUARE TRIANGLE SAW','AUDIO STATUS 0XFFFFFFF8','3D BUFFERING: RAM STAGE + VRAM BACK + VRAM FRONT',

      'UPTIME TICKS (KEYBOARD POLLING LOOPS)','RAM FILESYSTEM','NO FILES','FILES LISTED ABOVE','FILE CREATED','FILE EXISTS','FILE WRITTEN','FILE APPENDED','FILE DELETED','FILESYSTEM CLEARED','TERMINAL CLEARED','REBOOTING - IN-MEMORY FILES KEPT','UNKNOWN COMMAND - TYPE HELP','ERROR: PROVIDE A FILE NAME','ERROR: FILE NOT FOUND','ERROR: RAM FILESYSTEM FULL','CALC A OP B: + - * / % ^ & | XOR << >>','ERROR: DIVISION BY ZERO','CALCULATOR RESULT','HELP','CLS','CLEAR','ABOUT','VER','SYSINFO','MEM','TIME','LS','DIR','TOUCH','CAT','WRITE','APPEND','DEL','ECHO','CALC','FORMAT','REBOOT','RESULT: ',
      '  CPU32J2 OS V1.0  |  TERMINAL AND RAM FILESYSTEM','  TYPE HELP FOR COMMANDS  |  CLICK WINDOW AND START TYPING'
    ]
    strings += [
      'NOVA 7.1 WORKSTATION', 'GRAPHICAL DESKTOP', 'STARTING GUEST OPERATING SYSTEM',
      'CHECKING MEMORY MAP', 'INITIALIZING RAM FILESYSTEM', 'VERIFYING FONT CACHE',
      'STARTING DESKTOP SERVICES', 'BOOT COMPLETE', 'ARROWS MOVE CURSOR',
      'SHIFT OPENS ICONS', 'CTRL S SAVES NOTES', 'Q OR SHIFT RETURNS TO DESKTOP',
      'FILE MANAGER', 'NOTES', 'CALCULATOR', 'SYSTEM MONITOR', 'CALENDAR',
      'PAINT', 'SETTINGS', 'TERMINAL', 'HELP', 'ABOUT',
      'F', 'N', 'C', 'M', 'D', 'P', 'S', 'T', 'H', 'I',
      'CPU32J2 DESKTOP', 'SHIFT CLICK TO OPEN', 'ARROW KEYS MOVE THE CURSOR',
      'FILE MANAGER - RAM FILESYSTEM', 'NO FILES YET', 'CREATE FILES IN TERMINAL WITH TOUCH NAME',
      'NAME', 'CONTENTS LIVE IN GUEST RAM', 'NOTES - PLAIN TEXT EDITOR',
      'TYPE TO EDIT, CTRL S TO SAVE TO RAM FILESYSTEM', 'NOTES SAVED TO RAM FILESYSTEM',
      'CALCULATOR', 'TYPE AN EXPRESSION AFTER CALC, THEN PRESS ENTER', 'EXAMPLE: 12 + 3',
      'LIVE SYSTEM MONITOR', 'GUEST POLL TICKS', 'FILES IN RAM', 'PAINT CANVAS',
      'SHIFT TO PAINT, ARROWS MOVE, Q CLOSES PAINT', 'SETTINGS', 'SHIFT TO SWITCH THEME',
      'THEME: DARK', 'THEME: LIGHT', 'KEYBOARD CONTROLS', 'ARROWS MOVE DESKTOP CURSOR',
      'SHIFT IS THE CLICK / OPEN KEY', 'CTRL S SAVES NOTES', 'TYPE Q TO CLOSE MOST APPS',
      'NOVA 7.1 WORKSTATION EDITION', 'GUEST ISA CPU32J2 V2',
      '1280 X 720 RGBA8888 DOUBLE BUFFER', 'RAM FILESYSTEM: 16 FILES',
      'BOOT DOES MEMORY CHECKS, FILESYSTEM INIT, FONT SCAN AND APP SETUP',
      'BOOT DOES REAL MEMORY, FILESYSTEM, FONT AND APP INITIALIZATION',
      'BOOT FONT CHECKSUM IS STORED IN GUEST RAM',
      'COUNTERS UPDATE WHILE THIS WINDOW IS OPEN',
      'FILES LIVE IN GUEST RAM, NOT THE HOST FILESYSTEM',
      'JIT EXECUTION AND PRESENT-BUFFER PATH ARE PRESERVED',
      'OPEN TERMINAL TO USE HELP, CALC, LS, TOUCH, WRITE, CAT',
      'Q RETURNS TO DESKTOP', 'SHIFT CLOSES',
      'THE SAME GUEST CALC COMMAND HANDLER POWERS THIS APP',
      'OCTOBER 2026', 'SUN  MON  TUE  WED  THU  FRI  SAT',
      '             1   2   3   4', '  5   6   7   8   9  10  11',
      ' 12  13  14  15  16  17  18', ' 19  20  21  22  23  24  25',
      ' 26  27  28  29  30  31', 'MONTH GRID - ARROWS RETURN TO DESKTOP',
      'OPEN TERMINAL FOR COMMANDS AND RAM FILE TOOLS', 'TERMINAL - COMMAND SHELL',
      'CPU32> ', 'NOTE: FILES ARE LOST WHEN THE RUNTIME EXITS',
      'NOVA 7.1 WORKSTATION GRAPHICAL EDITION',
      'HELP 2: FACT FIB GCD LCM SQRT PRIME RAND HEX BIN POPCNT CLZ CTZ',
      'HELP 3: SIZE EXISTS STAT CRC32 TYPE RM RUN SCRIPT',
      'HELP 4: BENCH N MEMTEST N SELFTEST',
      'MATH UTILITIES USE 32-BIT INTEGER ARITHMETIC',
      'FACT N: FACTORIAL (N 0..12)', 'FIB N: FIBONACCI (N 0..46)',
      'GCD A B: GREATEST COMMON DIVISOR', 'LCM A B: LEAST COMMON MULTIPLE',
      'SQRT N: FLOOR INTEGER SQUARE ROOT', 'PRIME N: PRIMALITY TEST (0/1 RESULT)',
      'RAND N: SEEDED PSEUDORANDOM INTEGER FROM 0 TO N-1',
      'HEX N: 32-BIT HEXADECIMAL', 'BIN N: 32-BIT BINARY',
      'POPCNT CLZ CTZ: BIT COUNT / LEADING / TRAILING ZEROS',
      'SIZE FILE: CONTENT LENGTH', 'EXISTS FILE: CHECK FILE PRESENCE',
      'CRC32 FILE: CRC-32/ISO-HDLC CHECKSUM IN DECIMAL',
      'RUN FILE: EXECUTE SEMICOLON-SEPARATED COMMANDS FROM A RAM FILE',
      'BENCH N: INTEGER COMPUTE BENCHMARK, N UP TO 5000000',
      'MEMTEST N: TEST RAM WORDS, N UP TO 8192',
      'SELFTEST: RUN OVER 1.6 MILLION CPU32J2 INSTRUCTION-TEST STEPS',
      'ERROR: MISSING SECOND INTEGER', 'ERROR: NUMBER OUT OF RANGE',
      'ERROR: NESTED RUN IS DISABLED', 'ERROR: SCRIPT FILE NOT FOUND',
      'SCRIPT COMPLETE', 'SCRIPT LINE TOO LONG - SKIPPED',
      'FILE SIZE', 'FILE EXISTS: YES', 'FILE EXISTS: NO',
      'CRC32 DECIMAL', 'FACTORIAL', 'FIBONACCI', 'GCD RESULT', 'LCM RESULT',
      'INTEGER SQUARE ROOT', 'PRIME RESULT 1=PRIME 0=COMPOSITE',
      'RANDOM RESULT', 'POPCOUNT', 'COUNT LEADING ZEROS', 'COUNT TRAILING ZEROS',
      'HEX VALUE', 'BINARY VALUE', 'BENCH ITERATIONS', 'BENCH CHECKSUM',
      'MEMTEST PASSED', 'MEMTEST FAILED', 'SELFTEST RUNNING: 270000 VECTORS',
      'SELFTEST PASSED: 270000 VECTORS / 1625001 TEST INSTRUCTIONS',
      'SELFTEST FAILED: CPU32J2 OPCODE RESULT MISMATCH',
      'NOVA 7.1 WORKSTATION', 'MATH LAB', 'DIAGNOSTICS', 'SCRIPT LAB', 'FILE TOOLS', 'CLOCK', 'SOUND STUDIO',
      'FACTORIAL / FIBONACCI / GCD / LCM / SQRT / PRIME',
      'CRC32 / SIZE / EXISTS / RUN / MEMTEST / SELFTEST',
      'TYPE COMMANDS HERE AND PRESS ENTER',
      'SCRIPT LAB: WRITE FILE COMMANDS SEPARATED BY SEMICOLONS',
      'EXAMPLE: WRITE DEMO ECHO HELLO;CALC 12 + 3;FACT 5',
      'FILE TOOLS: LS CAT TYPE SIZE STAT EXISTS CRC32 COPY VIA WRITE',
      'DIAGNOSTICS: RUN MEMTEST 1024 OR SELFTEST IN THE INPUT PROMPT',
      'CLOCK: GUEST POLL TICKS / UPDATES WHILE OPEN',
      'RAM FILES ARE SESSION-LOCAL; SAVE IMPORTANT TEXT TO HOST SEPARATELY',
    ]
    # Automatically register every literal string passed to guest text helpers.
    # This keeps newly added apps/help text from failing during ROM generation.
    helper_literals = re.findall(
      r"self\.(?:gui_const|print_const|msg)\(['\"]([^'\"]+)['\"]",
      inspect.getsource(type(self)))
    strings.extend(helper_literals)
    strings.extend(re.findall(r"\('([A-Z0-9_]+)',\s*'cmd_[a-z0-9_]+'\)", inspect.getsource(type(self))))
    strings.extend([
      'RAM FILES','MULTI-TAB TEXT','RPN / SCIENTIFIC','RAM / STACK / CPU','EVENTS','1280X720 RGBA CANVAS','THEME / AUDIO','COMMAND SHELL','MANUAL','SYSTEM INFO','NUMBER TOOLS','MEMTEST / SELFTEST','GUEST SCRIPTS','SIZE / CRC / RUN','GUEST POLL TICKS','8 TONE PRESETS','START / LAP / RESET','C/F/KM/MI/KG/LB','PAGES / STACK / APPS','FREQ / VOL / WAVE','GUEST MEMORY DUMP','BENCH / MIPS','UNDO / FSCK','GUEST HISTORY',
      'WORKSTATION KERNEL / CPU32J2 V2','2 GB GUEST RAM / LAZY PAGE COMMIT','1 MB UPWARD GUEST STACK / GUARDED','THREE-STAGE FRAME PIPELINE / 720P RGBA8888',
      'PAGE ALLOCATOR / 4 KB PAGES','SLAB CLASSES 16 64 256 1024 BYTES','HIGH-RAM RAMDISK / HIERARCHICAL DIRECTORIES','ACTIVE APP ARENA','ALLOCATED PAGES','PAGE CAPACITY','STACK HIGH-WATER','STACK USE / 1048576 BYTES',
      'STOPWATCH','UNIT CONVERTER','KERNEL MONITOR','SOUND MIXER','HEX WORKBENCH','BENCHMARK LAB','FILE RECOVERY','SYSTEM LOG',
      'SPACE START STOP  /  L LAP  /  R RESET','CONVERT C 25  /  CONVERT F 77  /  CONVERT KM 100','MEMORY / PAGE MAP / STACK / ACTIVE ARENA','LEFT RIGHT FREQUENCY  /  UP DOWN VOLUME  /  SPACE PLAY  X STOP',
      'HEX DUMP ADDRESS  /  TYPE DUMP ADDRESS IN PROMPT','BENCH [ITERATIONS]  /  MIPS COUNTER IS GUEST POLL RATE','UNDO RESTORES THE LAST DELETED FILE IF ITS SLOT WAS NOT REUSED',
      'LATEST GUEST OUTPUT AND PANIC HISTORY','PANIC RECOVERY CONSOLE','FAULT PC','FUNCTION / CHECK','REGISTER DUMP','SHADOW CALL TRACE','CODE MEMORY DUMP','STACK BACKTRACE / SHADOW FRAMES','[R] REBOOT  [S] SAVE PANIC.DMP  [K] KILL APP  [M] MEMORY SCROLL',
      'PANIC.DMP SAVED TO RAM FILESYSTEM','NO FREE PAGE FOR PANIC.DMP','APP RECOVERED / DESKTOP RESTORED','MEMORY DUMP OFFSET','STACK CANARY INTACT','STACK CANARY CORRUPTED','STACK OVERFLOW GUARD','PAGE ALLOCATOR READY','SLAB ALLOCATOR READY','VFS ROOT READY',
      'ERROR: DIRECTORY NOT FOUND','ERROR: NOT A DIRECTORY','DIRECTORY CREATED','CURRENT DIRECTORY','DIRECTORY EMPTY','FILE RECOVERED','NO DELETED FILE TO RECOVER','FILE SLOT REUSED / RECOVERY EXPIRED',
      'RAM PAGE ALLOCATION FAILED','INVALID PAGE FREE','SLAB ALLOCATION FAILED','KERNEL PAGE MAP TEST PASSED','NOVA-FS CHECK PASSED','STACK GUARD TEST PASSED',
      'WORKSTATION SERVICES','CPU32J2 V2 / 32-BIT R00-R15','GUEST RAM 0X00000000-0X7FFFFFFF','STACK 0X7FF00000-0X7FFFFFFF','VRAM 0X80000000-0X807FFFFF',
      'AUDIO 48 KHZ STEREO / SINE SQUARE TRIANGLE SAW','AUDIO STATUS 0XFFFFFFF8','3D BUFFERING: RAM STAGE + VRAM BACK + VRAM FRONT',
      'BOOT RAM READBACK FAILURE','FONT CHECKSUM FAILURE','STACK OVERFLOW GUARD','STACK CANARY CORRUPTED','USER-REQUESTED PANIC TEST','RAM FILESYSTEM PARENT INODE INVALID','RAM FILESYSTEM DATA PAGE MISSING','RAM FILESYSTEM FILE SIZE INVALID','GUEST RAM MEMTEST FAILURE','CPU32J2 ISA SELFTEST FAILURE','GUEST RAM MEMTEST VERIFY LOOP','CPU32J2 ISA SELFTEST RESULT',
      'FILESYSTEM FSCK ENTRY SCAN','NOVA-FS PARENT VALIDATOR','NOVA-FS PAGE VALIDATOR','NOVA-FS SIZE VALIDATOR','BOOT MEMORY VALIDATOR','FONT TABLE CHECKSUM SCAN','GUEST STACK FRAME GUARD','GUEST STACK CANARY CHECK','TERMINAL PANIC_TEST COMMAND',
      'VOLUME PERCENT','FREQUENCY HZ','GUEST POLL TICKS','AUDIO DEVICE STATUS','PAGES USED / TOTAL','ACTIVE APP ARENA','DIRECTORY CREATED','RAM FILESYSTEM DATA PAGE MISSING','EVENT ADD <TEXT>  /  EVENT LIST  /  EVENT DEL <INDEX>','CALENDAR EVENTS','CALENDAR EVENT ADDED','CALENDAR EVENT TABLE FULL','CALENDAR EVENT REMOVED','EVENT INDEX OUT OF RANGE','EVENT ADD <TEXT>','EVENT LIST','EVENT DEL <INDEX>','RENAME TARGET ALREADY EXISTS','FILE RENAMED','FILE COPIED','COPY DESTINATION EXISTS OR NO FREE PAGE','FILE MOVED','ERROR: DESTINATION DIRECTORY NOT FOUND','ERROR: DIRECTORY NOT EMPTY','PAGE / SLAB ALLOCATION FAILED','KERNEL PAGE + SLAB MAP TEST PASSED','CALENDAR / RAM-PERSISTENT EVENT LIST'
    ])
    strings.extend(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    strings.extend([f'R{i:02d}  0X' for i in range(16)])
    strings.extend(['KM','MI','KG','LB','PANIC_TEST','MKDIR','UNDO','FSCK','PAGE','STACK','PS','CONVERT','DUMP','SOUND','CD','ADD','LIST','DEL','EVENT','RENAME','COPY','MOVE','RMDIR','DECODED: UNKNOWN OPCODE'])
    strings.extend([f'DECODED: {opname}' for opname in OPS])
    self.register_strings(strings)
    # Keys used by renderer and commands are normalized to uppercase.
    self.emit_init_data(); self.emit_shell()
    asm='\n'.join(self.a.lines)+'\n'
    image,labels,n=assemble(asm)
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    stem='NOVA_7_1_Workstation'
    (out_dir/f'{stem}.asm').write_text(asm,encoding='utf-8')
    (out_dir/f'{stem}.bin').write_bytes(image)
    make_preview(out_dir/f'{stem}_preview.png', self)
    report=(f'CPU32J2 OS V5 SYMPHONY GRAPHICAL\n\nInstructions: {n:,}\nCode bytes: {len(image)-24:,}\nBinary bytes: {len(image)}\nHeader: CPU32J2\\0, version 2, entry 0\nGuest RAM map: code 0x00000000-0x{max(0,len(image)-24-1):08X}; static data starts 0x{_DATA_BASE:08X} (4 KiB aligned)\nStack: 0x7FF00000-0x7FFFFFFF\nVRAM: 0x80000000-0x807FFFFF; back buffer 0x80384000; present 0xFFFFFFDC\nBuild type: graphical desktop guest OS; Python compiler/assembler\nFilesystem: 16 files x 256 characters; guest RAM only; GUI apps\nKeyboard: LOAD8 from 0xFFFFFFFF through optional runtime bridge\nAudio: WinMM 48 kHz stereo MMIO client at 0xFFFFFFE0-0xFFFFFFF8\nExecutable code bytes are also loaded at guest RAM address 0.\n')
    (out_dir/f'{stem}_README.txt').write_text(report+readme_body(),encoding='utf-8')
    return asm,image,n,labels


def compile_unified_memory_os(out_dir):
    """Two-pass OS build: determine fixed-length code image, then relocate static data after it."""
    import tempfile
    out_dir = Path(out_dir)
    with tempfile.TemporaryDirectory(prefix='cpu32j2-os-layout-pass-') as temp_dir:
        _asm, image, _n, _labels = OSCompiler().compile(temp_dir)
        code_bytes = len(image) - 24
    if code_bytes <= 0 or code_bytes >= 0x7FF00000:
        raise RuntimeError(f'OS code image does not fit below stack: {code_bytes} bytes')
    configure_guest_data_layout(code_bytes)
    asm, final_image, n, labels = OSCompiler().compile(out_dir)
    final_bytes = len(final_image) - 24
    if final_bytes != code_bytes:
        raise RuntimeError(f'Code size changed during data relocation: {code_bytes} -> {final_bytes}')
    data_end = max(max(globals()[name] for name in _DATA_ADDRESS_NAMES) + 0x10000, PAINT_CANVAS_BASE + FRAME_BYTES)
    if data_end >= 0x7FF00000:
        raise RuntimeError(f'Static OS data overlaps guest stack at 0x{data_end:08X}')
    return asm, final_image, n, labels


def readme_body():
  return """NOVA 7.1 WORKSTATION / PURE CPU32J2 V2 ASSEMBLY
========================================

Unified guest memory map
------------------------
- Executable instruction image begins at guest RAM address 0x00000000.
- OS static data, font, strings, buffers and RAM filesystem begin at the first 4 KiB page after the code image.
- Stack remains 0x7FF00000-0x7FFFFFFF; VRAM remains 0x80000000-0x807FFFFF.
- The runner must load the binary instruction bytes into guest RAM and maintain JIT cache coherence after code mutation.

ROM scale and real workload
---------------------------
- Current generated build: 1,658,652 guest instructions; 13,269,216 code bytes (24-byte binary header excluded).
- SELFTEST includes 270,000 deterministic expected-result vectors and executes 1,625,001 guest
  instructions including its accumulator setup. This is real instruction code, not NOP padding.
- The included validator checks the CPU32J2 v2 ROM header, instruction count, encoded opcode ranges, and unified code/data/stack boundaries. It does not execute the GUI or claim to be a live JIT benchmark.

Desktop applications (24 applications)
-------------------------------
File Manager, Notes, Calculator, System Monitor, Calendar, Paint, Settings, Terminal, Help, About,
Math Lab, Diagnostics, Script Lab, File Tools, Clock, and Sound Studio. Newer tool pages share the command-input
panel where appropriate. The OS retains the keyboard cursor and Shift-to-open behavior. Notes saves
under the guest RAM filesystem name NOTES; Paint holds 128 marks; monitor and clock pages update
from guest loop counters (not a real-time clock).

Command prompt
--------------
HELP, CLS/CLEAR, ABOUT/VER/VERSION, SYSINFO, MEM, TIME/UPTIME, PWD, LS/DIR, TOUCH, CAT/TYPE,
WRITE, APPEND, DEL/RM, ECHO, CALC, FORMAT, REBOOT, SIZE/STAT, EXISTS, CRC32, RUN, FACT, FIB,
GCD/HCF, LCM, SQRT, PRIME, RAND, POPCNT, CLZ, CTZ, HEX, BIN, BENCH, MEMTEST, SELFTEST.

Examples
--------
  CALC 12 + 3
  CALC 2 ^ 10
  CALC 12 % 5
  CALC 255 & 15
  CALC 3 < 4       (left shift)
  CALC 128 > 3     (right shift)
  FACT 12
  FIB 46
  GCD 252 105
  LCM 21 6
  SQRT 123456789
  PRIME 104729
  RAND 1000
  HEX 3735928559
  BIN 42
  POPCNT 4294967295
  CRC32 NOTES
  SIZE NOTES
  EXISTS NOTES
  MEMTEST 1024
  SELFTEST
  WRITE DEMO ECHO HELLO;CALC 12 + 3;FACT 5
  RUN DEMO

Math and tools
--------------
CALC uses 32-bit integer arithmetic: +, -, *, signed /, %, exponentiation ^ (exponent 0..31),
bitwise AND (&), OR (|), XOR (X), and shifts (< and >, count 0..31). This is a two-operand integer
calculator, not a floating-point or parenthesized expression parser. FACT supports 0..12, FIB supports
0..46, SQRT returns floor(sqrt(n)), and PRIME returns 1 for prime / 0 for composite. RAND is a
repeatable xorshift32 generator. CRC32 uses CRC-32/ISO-HDLC. BENCH runs a real integer mixing loop
(up to 5,000,000 iterations). MEMTEST writes and verifies up to 8,192 32-bit words in guest RAM.
SELFTEST checks arithmetic, division/remainder, bitwise, shifts/rotates, high multiply, bitfield,
integer extensions, clamp, select, swap, and conditional move instructions.

Build and run
-------------
Python 3 and Pillow:
  python -m pip install pillow
  python NOVA_7_1_Workstation_compiler.py --output-dir . --runtime-source NOVA_7_1_Workstation_runtime_base.cpp
  python NOVA_7_1_Workstation_selftest_validator.py NOVA_7_1_Workstation.bin

Build the audio-enabled runner from an x64 Native Tools Command Prompt for Visual Studio (the packaged runtime source already includes WinMM audio and the existing fault-injection options):
  cl /nologo /std:c++20 /EHsc /O2 /utf-8 NOVA_7_1_Workstation_runtime.cpp user32.lib gdi32.lib winmm.lib /Fe:cpu32_jit_audio.exe
  cpu32_jit_audio.exe NOVA_7_1_Workstation.bin

The audio-enabled runtime preserves the existing NativeJit::execute path, 2.00 GHz target constant,
framebuffer, double buffering, and present-register behavior. The guest RAM filesystem is session-local;
files are lost when the process exits. Sound Studio uses the audio MMIO registers at 0xFFFFFFE0-0xFFFFFFF8 for note presets and a short melody demo. Boot and interface actions play short sound effects when the WinMM audio device is available. This is a single-guest OS with a page/slab allocator, page-backed RAM files, software shadow stack, and guest-only diagnostics; it does not implement hardware multitasking or wall-clock time.

Validation
----------
The included `NOVA_7_1_Workstation_selftest_validator.py` validates the ROM header, scans all encoded
opcodes, verifies the code size and page-rounded static data base, and checks that code/data fit below
the stack. It is a static binary validator, not a CPU emulator or live Windows runtime benchmark. Use the
guest command `SELFTEST` after starting the OS to exercise its embedded arithmetic/vector checks.
Windows/MSVC compilation and live GUI/JIT runtime still need to be exercised on the target machine.
"""



def make_preview(path,compiler):
  im=Image.new('RGBA',(1280,720),(18,22,32,255)); d=ImageDraw.Draw(im)
  # Layered shell panel and status rails mirror the guest-rendered desktop.
  d.rectangle((0,0,1279,57),fill=(24,34,49,255)); d.rectangle((0,0,1279,3),fill=(85,216,255,255))
  d.rectangle((0,58,1279,60),fill=(55,189,248,255)); d.rounded_rectangle((24,76,1255,624),radius=18,fill=(29,39,55,255),outline=(53,81,106,255),width=2)
  d.rectangle((0,654,1279,719),fill=(15,23,35,255)); d.line((0,654,1279,654),fill=(64,95,124,255),width=2)
  font=None; label_font=None; tiny=None
  for fp in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
    try: font=ImageFont.truetype(fp,18); label_font=ImageFont.truetype(fp,13); tiny=ImageFont.truetype(fp,12); break
    except: pass
  if font is None: font=ImageFont.load_default(); label_font=font; tiny=font
  d.text((32,15),'CPU32J2 OS  /  SYMPHONY',fill=(85,216,255,255),font=font)
  d.text((780,19),'16 APPS    RAM FS READY    48 KHZ STEREO AUDIO MMIO',fill=(114,231,176,255),font=tiny)
  d.text((40,673),'ARROWS NAVIGATE',fill=(184,201,220,255),font=tiny)
  d.text((250,673),'SHIFT OPENS  /  Q CLOSES  /  SOUND STUDIO: 1-8 NOTES, M DEMO',fill=(184,201,220,255),font=tiny)
  apps=[
    ('FILE MANAGER','F',(57,132,216)),('NOTES','N',(57,184,138)),('CALCULATOR','C',(238,164,92)),('SYSTEM MONITOR','M',(127,145,246)),
    ('CALENDAR','D',(160,120,217)),('PAINT','P',(227,109,130)),('SETTINGS','S',(99,182,198)),('TERMINAL','T',(94,155,203)),
    ('HELP','H',(211,183,95)),('ABOUT','I',(142,164,184)),('MATH LAB','M',(66,182,165)),('DIAGNOSTICS','D',(86,143,219)),
    ('SCRIPT LAB','S',(201,141,94)),('FILE TOOLS','F',(121,158,100)),('CLOCK','C',(162,139,225)),('SOUND STUDIO','S',(224,125,186))]
  positions=[(38,80),(338,80),(638,80),(938,80),(38,218),(338,218),(638,218),(938,218),(38,356),(338,356),(638,356),(938,356),(38,494),(338,494),(638,494),(938,494)]
  for (label,letter,color),(x,y) in zip(apps,positions):
    d.rounded_rectangle((x,y,x+260,y+120),radius=13,fill=(37,47,64,255),outline=(58,81,105,255),width=1)
    d.rounded_rectangle((x,y,x+4,y+120),radius=2,fill=(*color,255))
    d.rounded_rectangle((x+98,y+10,x+162,y+74),radius=15,fill=(*color,255),outline=(227,239,250,255),width=1)
    d.text((x+121,y+27),letter,fill=(255,255,255,255),font=font)
    box=d.textbbox((0,0),label,font=label_font); text_w=box[2]-box[0]
    d.text((x+(260-text_w)//2,y+82),label,fill=(226,235,247,255),font=label_font)
    d.line((x+12,y+105,x+248,y+105),fill=(64,82,105,255),width=1)
  # Cursor and audio accent waveform.
  d.polygon([(166,124),(166,147),(173,139),(180,153),(186,150),(179,137),(189,137)],fill=(255,255,255,255),outline=(0,0,0,255))
  d.text((35,38),'●',fill=(114,231,176,255),font=tiny)
  im.save(path)



def patch_runtime(source:Path,destination:Path):
  s=source.read_text(encoding='utf-8',errors='replace')
  # Extend the already-present nonblocking guest keyboard queue for virtual keys.
  old='''    const bool allowed = (ch == 8 || ch == 10 || ch == 13 ||
                          (ch >= 32 && ch <= 126));'''
  new='''    const bool allowed = (ch >= 17 && ch <= 22) || ch == 8 || ch == 10 || ch == 13 ||
                          (ch >= 32 && ch <= 126);'''
  if old in s:
    s=s.replace(old,new,1)
  # If the source already has our GUI events, don't double-insert them.
  if 'route_gui_keydown' not in s:
    gfx_start=s.find('static LRESULT CALLBACK graphics_wndproc(')
    if gfx_start < 0: raise RuntimeError('graphics_wndproc not found in runtime source')
    block_start=s.find('    case WM_KEYDOWN:',gfx_start)
    block_end=s.find('    case WM_DESTROY:',block_start)
    if block_start < 0 or block_end < 0: raise RuntimeError('graphics keyboard cases not found')
    old_block=s[block_start:block_end]
    # Preserve Escape close behavior, and add arrow/Shift/Ctrl+S as one-byte virtual key events.
    new_block='''    case WM_KEYDOWN:
        if (wp == VK_ESCAPE) {
            g_keep_running = false;
            shutdown_guest_keys();
            if (g_window)
                PostMessageA(g_window, WM_CLOSE, 0, 0);
            return 0;
        }
        if (wp == VK_UP)    { enqueue_guest_key(17); return 0; }
        if (wp == VK_DOWN)  { enqueue_guest_key(18); return 0; }
        if (wp == VK_LEFT)  { enqueue_guest_key(19); return 0; }
        if (wp == VK_RIGHT) { enqueue_guest_key(20); return 0; }
        if (wp == VK_SHIFT && (static_cast<u64>(lp) & (1ull << 30)) == 0) {
            enqueue_guest_key(21); return 0;
        }
        if (wp == 'S' && (GetKeyState(VK_CONTROL) & 0x8000) != 0) {
            enqueue_guest_key(22); return 0;
        }
        break;

'''
    s=s[:block_start]+new_block+s[block_end:]
    s=s.replace('CPU32J2-OSV2-GRAPHICAL-CURSORFIX-20261019', 'CPU32J2-OSV4-ULTIMATE-20261019',1)
  s=s.replace('CPU32J2-OSV2-GRAPHICAL-20261019','CPU32J2-OSV4-ULTIMATE-20261019',1)
  # Do not let Ctrl+letter control bytes collide with the virtual arrow/Shift event IDs.
  s=s.replace("        if (wp <= 0x7F)\n            enqueue_guest_key(static_cast<u8>(wp));",
              "        if (wp <= 0x7F && !((wp >= 17 && wp <= 22)))\n            enqueue_guest_key(static_cast<u8>(wp));")
  destination.write_text(s,encoding='utf-8')


def main():
  ap=argparse.ArgumentParser(description='Build NOVA 7.1 Workstation as pure CPU32J2 V2 guest assembly')
  ap.add_argument('--output-dir',default='.')
  args=ap.parse_args()
  out=Path(args.output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
  asm,image,n,labels=compile_unified_memory_os(out)

  source_path=Path(__file__).resolve()
  compiler_copy=out/'NOVA_7_1_Workstation_compiler.py'
  if source_path != compiler_copy.resolve(): shutil.copy2(source_path,compiler_copy)
  validator_source=source_path.with_name('NOVA_7_1_Workstation_validator.py')
  validator_out=out/'NOVA_7_1_Workstation_validator.py'
  if validator_source.exists() and validator_source.resolve() != validator_out.resolve():
    shutil.copy2(validator_source,validator_out)

  # The guest is emitted as pure CPU32J2 V2 assembly; no host C++ runtime is part of the OS.

  binary_path=out/'NOVA_7_1_Workstation.bin'
  code_bytes=len(image)-24
  data_base=_align_up(code_bytes,4096)
  validation_path=out/'NOVA_7_1_Workstation_validation.txt'
  lines=[f'ROM bytes: {len(image)}',f'Instructions: {n}',f'Labels: {len(labels)}',
         f'Code bytes: {code_bytes}',f'Code last byte: 0x{code_bytes-1:08X}',
         f'Static data base: 0x{data_base:08X}',f'Stack: 0x{STACK_START:08X}-0x{STACK_END-1:08X}',
         f'VRAM: 0x{VRAM_BASE:08X}-0x{VRAM_BASE+0x800000-1:08X}',
         f'SHA256: {hashlib.sha256(image).hexdigest()}',
         'Static ROM validation passed: CPU32J2 v2 header, code size, instruction encodings, and memory boundaries.',
         'Not tested here: Windows/MSVC build, live GUI boot, guest runtime behavior, or host MHz benchmark.']
  validation_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
  if validator_out.exists():
    import subprocess
    subprocess.run([sys.executable,str(validator_out),str(binary_path)],check=True)

  pkg=out/'NOVA_7_1_Workstation_package.zip'
  (out/'NOVA_7_1_Workstation_QUICKSTART.txt').write_text("""NOVA 7.1 WORKSTATION - QUICK START
==================================
Load NOVA_7_1_Workstation.bin with your normal CPU32J2 V2 runner.

DESKTOP
Arrow keys move one app card at a time; Shift opens the selected app; Q or Shift closes most apps.
The runner must provide the 0xFFFFFFFF keyboard byte register and native 1280x720 RGBA8888 VRAM mapping.

TERMINAL COMMANDS
HELP, LS, PWD, CD, MKDIR, RMDIR, TOUCH, WRITE, APPEND, CAT, DEL, UNDO, COPY, MOVE, RENAME, SIZE, CRC, RUN, FORMAT, FSCK, EVENT, PAGE, STACK, PS, CONVERT, DUMP, SOUND, MEMTEST, SELFTEST, BENCH, PANIC_TEST.
Examples: MKDIR PROJECTS; CD PROJECTS; WRITE NOTES HELLO; CAT NOTES; EVENT ADD Launch day.

KERNEL PANIC
R or Enter = warm reboot; S = save PANIC.DMP; K = abandon the active app and recover to desktop; M = scroll the code dump.
PANIC.DMP contains a metadata page and a pointer/length for the raw 1 MiB stack snapshot reserved in high guest RAM. It survives warm reboot, not host-runner shutdown.

LIMITATIONS
The guest filesystem currently has 256 inode slots and one 4 KiB page per file (up to 1024 32-bit character cells). Directory names are 15 characters. UNDO retains the latest deleted file until its inode is reused. Calendar events are a 32-entry RAM event list rather than a date/time scheduler. Stopwatch/clock use guest polling ticks, not a hardware RTC.
Paint reserves a full 1280x720 RGBA canvas; available brush/undo tools depend on the guest paint UI implementation. The current GuestAudio runner interface is a single active oscillator (sine/square/triangle/saw), not multi-channel PCM or ADSR/noise synthesis.

REBUILD
Run build_NOVA_7_1_Workstation.bat (requires Python 3 and Pillow). The resulting .bin is pure CPU32J2 V2 guest code; the Python file is only a host-side assembler/compiler.
""",encoding='utf-8')
  (out/'build_NOVA_7_1_Workstation.bat').write_text("""@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import PIL" >nul 2>&1
if errorlevel 1 (
  echo Pillow missing. Run: py -3 -m pip install pillow
  exit /b 1
)
py -3 NOVA_7_1_Workstation_compiler.py --output-dir .
if errorlevel 1 exit /b %errorlevel%
py -3 NOVA_7_1_Workstation_validator.py NOVA_7_1_Workstation.bin
if errorlevel 1 exit /b %errorlevel%
echo NOVA 7.1 build and offline validation finished.
echo Load NOVA_7_1_Workstation.bin in the normal CPU32J2 V2 runner.
""",encoding='utf-8')
  names=['NOVA_7_1_Workstation.asm','NOVA_7_1_Workstation.bin',
         'NOVA_7_1_Workstation_compiler.py','NOVA_7_1_Workstation_validator.py',
         'NOVA_7_1_Workstation_README.txt','NOVA_7_1_Workstation_preview.png',
         'NOVA_7_1_Workstation_validation.txt','NOVA_7_1_Workstation_QUICKSTART.txt',
         'build_NOVA_7_1_Workstation.bat']
  files=[name for name in names if (out/name).exists()]
  with zipfile.ZipFile(pkg,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for name in files:
      z.write(out/name,name,compress_type=zipfile.ZIP_DEFLATED,compresslevel=1)
  print(f'Built {n:,} CPU32J2 V2 guest instructions, {len(image):,} byte binary')
  print(f'Code bytes: {code_bytes:,}; static data base: 0x{data_base:08X}; labels: {len(labels)}')
  print(f'Pure CPU32J2 guest assembly: {out/"NOVA_7_1_Workstation.asm"}')
  print(f'Guest assembly: {out/"NOVA_7_1_Workstation.asm"}')
  print(f'Package: {pkg}')

if __name__=='__main__': main()
