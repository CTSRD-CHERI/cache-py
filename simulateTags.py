#!/usr/bin/env python

#-
# Copyright (c) 2017 Jonathan Woodruff
# Copyright (c) 2017 Alexandre Joannou
# All rights reserved.
# 
# This software was developed by SRI International and the University of
# Cambridge Computer Laboratory (Department of Computer Science and
# Technology) under DARPA contract HR0011-18-C-0016 ("ECATS"), as part of the
# DARPA SSITH research programme.
#
# @BERI_LICENSE_HEADER_START@
#
# Licensed to BERI Open Systems C.I.C. (BERI) under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  BERI licenses this
# file to you under the BERI Hardware-Software License, Version 1.0 (the
# "License"); you may not use this file except in compliance with the
# License.  You may obtain a copy of the License at:
#
#   http://www.beri-open-systems.org/legal/license-1-0.txt
#
# Unless required by applicable law or agreed to in writing, Work distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations under the License.
#
# @BERI_LICENSE_HEADER_END@
#

import argparse
import sys
import csv
import TagCache

################################
# Parse command line arguments #
################################

parser = argparse.ArgumentParser(description='script simulating the cheri tags cache')

def auto_int (x):
    return int(x,0)

#parser.add_argument('input', type=str, nargs='+', metavar='INPUT',
parser.add_argument('input', type=str, metavar='INPUT',
                    help="INPUT memory trace to replay for the simulation (in csv format)")
parser.add_argument('-v', '--verbose', action='store_true', default=False,
                    help="turn on output messages")
parser.add_argument('--report-periods', type=auto_int, default=100000, metavar='REPORTPERIODS',
                    help="specify REPORTPERIODS, the desired number of report periods before terminating the simulation (default=100000)")
parser.add_argument('--tag-cache-size', type=auto_int, default=2**16, metavar='TAGCACHESIZE',
                    help="specify TAGCACHESIZE, the desired tag cache size in bytes (default=2**15)")
parser.add_argument('--tag-cache-assoc', type=auto_int, default=4, metavar='TAGCACHEASSOC',
                    help="specify TAGCACHEASSOC, the desired tag cache associativity (default=4)")
parser.add_argument('--tag-cache-line-size', type=auto_int, default=1024, metavar='TAGCACHELINESIZE',
                    help="specify TAGCACHELINESIZE, the desired tag cache line size in bits (default=1024)")
parser.add_argument('--tag-cache-struct', type=auto_int, nargs='+', default=[0,256], metavar='TAGCACHESTRUCT',
                    help="specify TAGCACHESTRUCT, the list of branching factors describing the tags tree from leaf to root (default=[0,256])")
parser.add_argument('--tag-cache-count-spatial-temporal', action='store_true',
                    help="Turns on keeping track of spatial and temporal hits in the cache (slows down simulation)")
parser.add_argument('--memory-start-addr', type=auto_int, default=0x80000000, metavar='MEMSTARTADDR',
                    help="specify MEMSTARTADDR, the address at which memory starts (default=0x80000000)")
parser.add_argument('--memory-size', type=auto_int, default=2**30, metavar='MEMSIZE',
                    help="specify MEMSIZE, the desired memory size in bytes (default=2**29)")
parser.add_argument('--report-period', type=auto_int, default=100000, metavar='REPORTPERIOD',
                    help="specify REPORTPERIOD, the number of requests to replay between each report statement")
parser.add_argument('--tag-cache-create-destroy-empty', action='store_true', default=False,
                    help="turn on optimisation that a first write of a clean node will not read from memory, and the last clear will not write back")
parser.add_argument('--tag-cache-non-dirty-writes', action='store_true', default=False,
                    help="turn on optimisation keeping line non dirty if writing the same data over again")
#parser.add_argument('--ptr-size', type=int, default=64, metavar='PTR_SZ',
#                    help="pointer size in bits (default 64)")

args = parser.parse_args()

if args.verbose:
    def verboseprint(msg):
        print(msg)
else:
    verboseprint = lambda *a: None

#
infile = csv.reader(open(args.input))

########################################
# Replay traces and simulate tag cache #
########################################

# instanciating tag cache memory model for simulation

verboseprint("setting up tag cache model with following parameters:")
verboseprint("cachesize=%d bytes"%args.tag_cache_size)
verboseprint("cacheassoc=%d"%args.tag_cache_assoc)
verboseprint("cachelinesize=%d bits"%args.tag_cache_line_size)
verboseprint("tablestruct=%s"%args.tag_cache_struct)
verboseprint("memstart=0x%x"%args.memory_start_addr)
verboseprint("memsize=%d bytes"%args.memory_size)
verboseprint("tag cache create/destroy empty nodes without touching memory={}".format(args.tag_cache_create_destroy_empty))
tagmem = TagCache.Mem(  cachesize=args.tag_cache_size,
                        cacheassoc=args.tag_cache_assoc,
                        cachelinesize=args.tag_cache_line_size,
                        tablestruct=args.tag_cache_struct,
                        memstart=args.memory_start_addr,
                        memsize=args.memory_size,
                        spatial_temporal=args.tag_cache_count_spatial_temporal,
                        emptyLeafOpt=args.tag_cache_create_destroy_empty,
                        non_dirty_writes=args.tag_cache_non_dirty_writes,
                        verbose=args.verbose)

reports = 0
# simulation loop
for i, line in enumerate(infile):
    # only consider 64 bytes requests
    if (line[2] == "64"):
        data = []
        if (line[0]=="W"):
            data = TagCache.str2ba(line[3])
        tagmem.putReq(TagCache.Request( line[0]=="W",
                                        int(line[1],16),
                                        data))
    # display report messages periodically
    if (i%args.report_period)==0:
        reports += 1
        tagmem.report()

    if reports > args.report_periods:
        exit()
