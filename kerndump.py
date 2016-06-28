#!/usr/bin/python3
# Program to decode Intel ISIS-II operating system ISIS.BIN and ISIS.OV0
# files.
#
# Copyright 2015 Eric Smith <spacewar@gmail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys


def hex_dump(b, addr=0):
    for i in range(0, len(b), 16):
        print('%04x:' % (addr + i), end = '')
        for j in range(16):
            if i+j < len(b):
                print(' %02x' % b[i+j], end='')
            else:
                print('   ', end='')
        print()


def get_1b(f):
    b = f.read(1)
    if len(b):
        return b[0]
    else:
        return None

def get_2b(f):
    b = f.read(2)
    if len(b):
        return b[0] + 256 * b[1]
    else:
        return None


# This is the format used for ISIS.BIN and ISIS.OV0
def get_record(f):
    rec_length = get_2b(f)
    if rec_length is None:
        return None
    load_addr = get_2b(f)
    if rec_length == 0:
        print("end record, addr %04x" % load_addr)
        pos = f.tell()
        f.seek(0, 2)
        last = f.tell()
        print("leftover %d bytes" % (last - pos))
        return None
    data = f.read(rec_length)
    print("addr %04x, end %04x, length %d" % (load_addr, load_addr+rec_length-1, rec_length))
    #hex_dump(data, addr = load_addr)
    return load_addr, data


fn = sys.argv[1]

if len(sys.argv) >= 3:
    outf = open(sys.argv[2], "wb")
else:
    outf = None

prev_addr = 0
with open(fn, "rb") as f:
    while True:
        r = get_record(f)
        if r is None:
            break
        addr, data = r
        assert addr >= prev_addr

        if outf is not None:
            if addr > prev_addr:
                outf.write(bytearray(addr - prev_addr))
            outf.write(data)

        prev_addr = addr + len(data)

