#!/usr/bin/python3
# Program to extract files from a raw disk image of an Intel ISIS-II disk
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

import os


def hex_dump(b):
    for i in range(0, len(b), 16):
        print('%04x:' % i, end = '')
        for j in range(16):
            if i+j < len(b):
                print(' %02x' % b[i+j], end='')
            else:
                print('   ', end='')
        print()


tracks_per_disk = 77
sectors_per_track = 26
bytes_per_sector = 128

def load_image(fn):
    image = [None] * tracks_per_disk
    with open(fn, 'rb') as f:
        for track in range(tracks_per_disk):
            image[track] = [None] * sectors_per_track
            for sector in range(sectors_per_track):
                image[track][sector] = f.read(bytes_per_sector)
        pos = f.tell()
        f.seek(0, 2)
        eof = f.tell()
        assert pos == eof
    return image

# Note that sector numbers are based at 1 rather than zero
def get_sector(image, addr):
    return image[addr[0]][addr[1]-1]


def get_file_given_link_addr(image, link_addr):
    expected_prev_link_addr = (0, 0)
    eof_reached = False
    data = bytearray()

    while link_addr != (0, 0):
        link_block = get_sector(image, link_addr)
        prev_link_addr = (link_block[1], link_block[0])
        next_link_addr = (link_block[3], link_block[2])
        assert prev_link_addr == expected_prev_link_addr
        for i in range(4, bytes_per_sector, 2):
            data_block_addr = (link_block[i+1], link_block[i])
            if eof_reached:
                assert data_block_addr == (0, 0)
            elif data_block_addr == (0, 0):
                eof_reached = True
            else:
                data += get_sector(image, data_block_addr)
        expected_prev_link_addr = link_addr
        link_addr = next_link_addr

    return data


# system files
# locations of bootstrap blocks are assumed
# locations of link blocks of system files are assumed
#
#             Link   Data
# Filename    Block  Blocks        Contents
# ----------  -----  ------------  --------
# ISIS.T0     00,24  00,01..00,23  bootstrap
# ISIS.LAB    00,25  00,26         disk label
# ISIS.DIR    01,01  01,02..01,26  directory
# ISIS.MAP    02,01  02,02..02,03  allocation bit map
# ISIS.BIN    02,04


fn = '9500007-07_ISIS-II_OPERATING_SYSTEM_DISKETTE_Ver_4.3.bin'
dump_dir = '9500007-07'

if not os.path.isdir(dump_dir):
    os.mkdir(dump_dir)

image = load_image(fn)

dir_link_addr = (1, 1)
dir = get_file_given_link_addr(image, dir_link_addr)
for i in range(len(dir)//16):
    dir_entry = dir[i*16:i*16+16]
    if dir_entry[0] == 0x7f:
        continue # unused entry
    elif dir_entry[0] == 0xff:
        continue # deleted entry
    else:
        assert(dir_entry[0] == 0x00)
    basename = dir_entry[1:7].decode('ascii').rstrip('\0')
    extension = dir_entry[7:10].decode('ascii').rstrip('\0')
    filename = basename
    if extension != '':
        filename += '.' + extension
    filename = filename.lower()
    assert dir_entry[10] & 0x78 == 0
    attributes = (' F' [(dir_entry[10] >> 7) & 1] +
                  ' P' [(dir_entry[10] >> 2) & 1] +
                  ' S' [(dir_entry[10] >> 1) & 1] +
                  ' I' [(dir_entry[10] >> 0) & 1])
    file_length = (dir_entry[12] + 256 * dir_entry[13]) * bytes_per_sector -bytes_per_sector + dir_entry[11]
    link_addr = (dir_entry[15], dir_entry[14])
    print('%-10s %s %d %s' % (filename, attributes, file_length, str(link_addr)))
    #hex_dump(dir_entry)

    file_data = get_file_given_link_addr(image, link_addr)
    #print('file length, dir: %d  based on link blocks: %d' % (file_length, len(file_data)))
    assert len(file_data) >= file_length
    file_data = file_data[:file_length]
    with open(os.path.join(dump_dir, filename), 'wb') as f:
        f.write(file_data)
