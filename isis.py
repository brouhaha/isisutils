#!/usr/bin/python3
# Program to list directory or extract files from an ImageDisk image
# of an Intel ISIS-II disk
#
# Copyright 2015, 2016 Eric Smith <spacewar@gmail.com>
# All rights reserved.

#    This program is free software: you can redistribute it and/or
#    modify it under the terms of version 3 of the GNU General Public
#    License as published by the Free Software Foundation.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

import argparse
import fnmatch
import os

from imagedisk import ImageDisk


def hex_dump(b):
    for i in range(0, len(b), 16):
        print('%04x:' % i, end = '')
        for j in range(16):
            if i+j < len(b):
                print(' %02x' % b[i+j], end='')
            else:
                print('   ', end='')
        print()


cylinders = 77
bytes_per_sector = 128


def load_raw_image(f):
    imd = ImageDisk()
    raw_image = f.read()
    if len(raw_image) == 256256:
        # IBM 3740 single-density FM format
        sectors_per_track = 26
        mode = 0x00
    elif len(raw_image) == 512512:
        # Intel SBC 202 double-density M2FM format
        sectors_per_track = 52
        mode = 0x03  # ImageDisk doesn't (yet?) have a defined mode for
                     # Intel M2FM
    else:
        raise Exception("unrecognized raw image size")
    offset = 0
    for track in range(cylinders):
        for sector in range(sectors_per_track):
            data = raw_image[offset:offset + bytes_per_sector]
            imd.write_sector(mode, track, 0, sector + 1, data)
            offset += bytes_per_sector
    return imd;


# Note that sector numbers are based at 1 rather than zero
def get_sector(imd, addr):
    return imd.read_sector(addr[0], 0, addr[1])


def get_file_given_link_addr(imd, link_addr):
    expected_prev_link_addr = (0, 0)
    eof_reached = False
    data = bytearray()

    while link_addr != (0, 0):
        link_block = get_sector(imd, link_addr)
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
                data += get_sector(imd, data_block_addr)
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


parser = argparse.ArgumentParser(description = 'List directory or extract files from Intel ISIS-II floppy disk image')

action_parser = parser.add_mutually_exclusive_group()
action_parser.add_argument('-v', '--dir', dest='dir', action='store_true', help = 'show directory')
action_parser.add_argument('-x', '--extract', dest='extract', action='store_true', help = 'extract files')

parser.add_argument('-d', '--destdir', type = str, help = 'destination directory')

parser.add_argument('-r', '--raw', action = 'store_true', help = 'use a raw binary file rather than an ImageDisk image')
parser.add_argument('image',   type=argparse.FileType('rb'), help = 'floppy image')

parser.add_argument('pattern', type = str, nargs = '?', help = 'filename pattern')

args = parser.parse_args()

if (args.destdir is not None) and not os.path.isdir(args.destdir):
    os.mkdir(args.destdir)

if args.raw:
    imd = load_raw_image(args.image)
else:
    imd = ImageDisk(args.image)

dir_link_addr = (1, 1)
dir = get_file_given_link_addr(imd, dir_link_addr)
if args.dir:
    print('filename   attr length link block')
    print('---------- ---- ------ ----------')
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
    attributes = ('.F' [(dir_entry[10] >> 7) & 1] +
                  '.P' [(dir_entry[10] >> 2) & 1] +
                  '.S' [(dir_entry[10] >> 1) & 1] +
                  '.I' [(dir_entry[10] >> 0) & 1])
    file_length = (dir_entry[12] + 256 * dir_entry[13]) * bytes_per_sector - bytes_per_sector + dir_entry[11]
    link_addr = (dir_entry[15], dir_entry[14])

    if args.pattern is not None:
        if not fnmatch.fnmatch(filename, args.pattern):
            continue

    if args.dir:
        print('%-10s %s %6d (%3d,%3d)' % (filename, attributes, file_length, link_addr[0], link_addr[1]))
        continue

    if args.extract:
        file_data = get_file_given_link_addr(imd, link_addr)
        #print('file length, dir: %d  based on link blocks: %d' % (file_length, len(file_data)))
        assert len(file_data) >= file_length
        file_data = file_data[:file_length]
        if args.destdir is not None:
            path = os.path.join(args.destdir, filename)
        else:
            path = filename
        with open(path, 'wb') as f:
            f.write(file_data)

