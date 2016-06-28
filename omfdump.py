#!/usr/bin/python3
# Program to decode Intel absolute OMF files
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


def hex_dump(b):
    for i in range(0, len(b), 16):
        print('%04x:' % i, end = '')
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
    return b[0] + 256 * b[1]


# record types
#   0x02 - header
#              name length byte
#              name
#              0x00 0x00
#   0x04 - module end
#              module type byte - 0x01 for main, 0x00 not main
#              segment ID byte
#              offset word
#   0x06 - content
#              segment ID byte
#              offset word
#              data
#   0x0e - end of file

def get_record(f):
    rec_type = get_1b(f)
    if rec_type is None:
        return False
    rec_length = get_2b(f)
    data = f.read(rec_length-1)
    checksum = get_1b(f)
    expected_checksum = ((((rec_type + (rec_length & 0xff) + (rec_length >> 8) + sum(data)) & 0xff) ^ 0xff) + 1) & 0xff
    print("type %02x length %d - " % (rec_type, rec_length), end='')
    if rec_type == 0x02:
        print("header")
        name_len = data[0]
        name = data[1:1+name_len].decode('ascii')
        assert name_len+3 == len(data)
        assert data[-2] == 0x00 and data[-1] == 0x00
        print("name: '%s'" % name)
    elif rec_type == 0x04:
        print("module end")
        hex_dump(data)
    elif rec_type == 0x06:
        print("content")
    elif rec_type == 0x0e:
        print("end of file")
        assert len(data) == 0
    else:
        print("unknown")
    assert checksum == expected_checksum
    return True


fn = sys.argv[1]

with open(fn, "rb") as f:
    while True:
        if not get_record(f):
            break
