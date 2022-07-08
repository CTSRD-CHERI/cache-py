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

import re
import os
import os.path as op
import subprocess as sub
from collections import defaultdict
from doit.task import clean_targets
from doit.action import CmdAction
#import multiprocessing as mp
#from doit.tools import run_once

################################################################################
# conf and variables
################################################################################

# directories
cdir         = op.abspath(op.curdir)
allptrs_dir  = op.join(cdir,"allptrs")
codeptrs_dir = op.join(cdir,"codeptrs")
zeroes_dir   = op.join(cdir,"zeroes")

allptrs_out_dir  = op.join(cdir,"allptrs-out")
codeptrs_out_dir = op.join(cdir,"codeptrs-out")
zeroes_out_dir   = op.join(cdir,"zeroes-out")
outputDirs = [allptrs_out_dir,codeptrs_out_dir,zeroes_out_dir]

# tools
usepypy = True
pypy = op.join("pypy")
tagSim = op.join(cdir,"simulateTags.py")

# confs
class SimConf:
    def __init__(self,
                    inputFile, outputDir,
                    bench, tags_kind,
                    cacheSize, cacheLineSize,
                    cacheAssoc, cacheStruct, cacheOpt):
        self.inputFile     = inputFile
        self.outputDir     = outputDir
        self.bench         = bench
        self.tags_kind     = tags_kind
        self.cacheSize     = cacheSize
        self.cacheLineSize = cacheLineSize
        self.cacheAssoc    = cacheAssoc
        self.cacheStruct   = cacheStruct
        self.cacheOpt      = cacheOpt
    def __str__(self):
        s = "{:s} {:s}".format(self.bench,self.tags_kind)
        s += ", cachesize: {:d} bytes".format(self.cacheSize)
        s += ", linesize: {:d} bits".format(self.cacheLineSize)
        s += ", assoc: {:d}".format(self.cacheAssoc)
        s += ", struct: {:s}".format(self.cacheStruct)
        s += ", {:s}".format(self.cacheOpt)
        s += "\n\tinput file: {:s}".format(self.inputFile)
        s += "\n\toutput file: {:s}".format(self.outputFile())
        return s
    def __lt__(a,b):
        if not isinstance(b, SimConf):
            return False
        if a.inputFile < b.inputFile:
            return True
        if a.outputDir < b.outputDir:
            return True
        if a.bench < b.bench:
            return True
        if a.tags_kind < b.tags_kind:
            return True
        if a.cacheSize < b.cacheSize:
            return True
        if a.cacheLineSize < b.cacheLineSize:
            return True
        if a.cacheAssoc < b.cacheAssoc:
            return True
        if a.cacheStruct < b.cacheStruct:
            return True
        if a.cacheOpt < b.cacheOpt:
            return True
        return False
    def outputFile(self):
        fname = op.basename(self.inputFile)
        fname += "-{:d}".format(self.cacheSize)
        fname += "-{:d}".format(self.cacheLineSize)
        fname += "-{:d}".format(self.cacheAssoc)
        fname += "-{:s}".format("_".join(map(str,self.cacheStruct)))
        fname += "-{:s}".format(self.cacheOpt)
        return op.join(self.outputDir,fname)
    def taskName(self):
        return op.join(op.basename(self.outputDir),op.basename(self.outputFile()))

inputs = []
inputs.append(("ffmpeg-small","allptrs",op.join(allptrs_dir,"ffmpeg-small-tags.txt")))
inputs.append(("ffmpeg-big","allptrs",op.join(allptrs_dir,"ffmpeg-big-tags.txt")))
inputs.append(("octane-small","allptrs",op.join(allptrs_dir,"octane-small-tags.txt")))
inputs.append(("octane-big","allptrs",op.join(allptrs_dir,"octane-big-tags.txt")))
inputs.append(("ffmpeg-small","codeptrs",op.join(codeptrs_dir,"ffmpeg-small-codetags.txt")))
inputs.append(("ffmpeg-big","codeptrs",op.join(codeptrs_dir,"ffmpeg-big-codetags.txt")))
inputs.append(("octane-small","codeptrs",op.join(codeptrs_dir,"octane-small-codetags.txt")))
inputs.append(("octane-big","codeptrs",op.join(codeptrs_dir,"octane-big-codetags.txt")))
inputs.append(("ffmpeg-small","zeroes",op.join(zeroes_dir,"ffmpeg-small-zerotags.txt")))
inputs.append(("ffmpeg-big","zeroes",op.join(zeroes_dir,"ffmpeg-big-zerotags.txt")))
inputs.append(("octane-small","zeroes",op.join(zeroes_dir,"octane-small-zerotags.txt")))
inputs.append(("octane-big","zeroes",op.join(zeroes_dir,"octane-big-zerotags.txt")))

cacheSizes = []
cacheSizes.append(4096)
cacheSizes.append(8192)
cacheSizes.append(16384)
cacheSizes.append(32768)
cacheSizes.append(65536)
cacheSizes.append(131072)
cacheSizes.append(262144)
cacheSizes.append(524288)
cacheSizes.append(1048576)


cacheLineSizes = []
cacheLineSizes.append(8)
cacheLineSizes.append(16)
cacheLineSizes.append(32)
cacheLineSizes.append(64)
cacheLineSizes.append(128)
cacheLineSizes.append(256)
cacheLineSizes.append(512)
cacheLineSizes.append(1024)
cacheLineSizes.append(2048)
cacheLineSizes.append(4096)
cacheLineSizes.append(8192)

cacheAssocs = []
cacheAssocs.append(1)
cacheAssocs.append(2)
cacheAssocs.append(4)
cacheAssocs.append(8)

cacheStruct = []
cacheStruct.append([0])
cacheStruct.append([0,8])
cacheStruct.append([0,16])
cacheStruct.append([0,32])
cacheStruct.append([0,64])
cacheStruct.append([0,128])
cacheStruct.append([0,256])
cacheStruct.append([0,512])
cacheStruct.append([0,1024])
cacheStruct.append([0,2048])
cacheStruct.append([0,8,32])

cacheOpt = []
cacheOpt.append("no-opt")
cacheOpt.append("non-dirty-writes")
cacheOpt.append("create-destroy-empty")
cacheOpt.append("all-opt")

simConfs = [SimConf(ac,b,aa,ab,c,d,e,f,g)
              # sources
              for (aa,ab,ac) in inputs
              for b in outputDirs
              for c in cacheSizes
              for d in cacheLineSizes
              for e in cacheAssocs
              for f in cacheStruct
              for g in cacheOpt
              if ("allptrs" == ab and "allptrs" in b)
                 or ("codeptrs" == ab and "codeptrs" in b)
                 or ("zeroes" == ab and "zeroes" in b)
              # filters (iccd paper)
              if
                # first graph
                ("allptrs" == ab and d == 512 and e == 8 and len(f) == 1 and g == "no-opt")
                # second graph
                or ("allptrs" == ab and "octane-big" == aa and c == 262144 and e == 8 and len(f) == 1 and g == "no-opt")
                ## third graph
                or ((("big" in aa and c == 262144) or ("small" in aa and c == 32768)) and d == 512 and e == 8 and ((len(f) == 1 and "allptrs" == ab)or (len(f) == 2 and f[1] == 512)) and g != "create-destroy-empty")
                ## fourth graph
                or ("octane-big" == aa and c == 262144 and d == 512 and e == 8 and len(f) < 3 and g == "no-opt")
          ]

################################################################################
# Show configuration task #
################################################################################
def task_show_conf():
    """prints configuration info"""

    def show_conf ():
        print(">>>>> {:d} simulation(s) <<<<<".format(len(simConfs)))
        for simConf in simConfs:
            print(simConf)
        print(">>>>> {:d} simulation(s) <<<<<".format(len(simConfs)))
        return True

    return {
        'actions': [(show_conf)],
        'verbosity':2
    }

################################################################################
# Run simulations #
################################################################################
def task_run_sim () :
    """runs the simulation for the given parameters"""

    def run_sim (simConf):
        if usepypy:
            run_cmd = [pypy, tagSim]
        else:
            run_cmd = [tagSim]
        run_cmd += ["--tag-cache-struct"]+[x for x in map(str,simConf.cacheStruct)]
        run_cmd += ["--tag-cache-size",str(simConf.cacheSize)]
        run_cmd += ["--tag-cache-assoc",str(simConf.cacheAssoc)]
        run_cmd += ["--tag-cache-line-size",str(simConf.cacheLineSize)]
        if simConf.cacheOpt == "all-opt" or simConf.cacheOpt == "non-dirty-writes":
            run_cmd += ["--tag-cache-non-dirty-writes"]
        if simConf.cacheOpt == "all-opt" or simConf.cacheOpt == "create-destroy-empty":
            run_cmd += ["--tag-cache-create-destroy-empty"]
        run_cmd += ["--tag-cache-count-spatial-temporal"]
        run_cmd += [simConf.inputFile]

        if not op.exists(simConf.outputDir):
            os.makedirs(simConf.outputDir)
        of = open(simConf.outputFile(), 'w')
        ef = open(simConf.outputFile()+".err", 'w')
        a = sub.Popen(run_cmd, stdout=of, stderr=ef)
        a.wait()

    for simConf in simConfs:
        yield {
            'name'    : simConf.taskName(),
            'actions' : [(run_sim,[simConf])],
            'file_dep': [simConf.inputFile],
            'targets' : [simConf.outputFile(),simConf.outputFile()+".err"],
            'clean'   : [clean_targets],
            'verbosity':2
        }

################################################################################
# Gather simulation results #
################################################################################
def task_gather_results () :
    """gather simulation results"""

    def gather_results (sims):
        data = []
        regexAll = "\d*:\s*HitRate:\s*(\d*\.\d*),\s*totalAccesses:\s*(\d*),\s*hits:\s*(\d*),(.*),\s*misses:\s*(\d*),\s*writebacks:\s*(\d*)\s*,\s*totalMemTransactions:\s*(\d*)\s*$"
        regexSpatialHits  = "\s*spatialHits\[(\d*)\]:\s*(\d*)"
        regexTemporalHits = "\s*temporalHits\[(\d*)\]:\s*(\d*)"
        selectAll = re.compile(regexAll)
        selectSpatialHit  = re.compile(regexSpatialHits)
        selectTemporalHit = re.compile(regexTemporalHits)
        structSize = max(map(len,cacheStruct))
        for sim in sorted(sims):
            for line in reversed(open(sim.outputFile()).readlines()):
                match = selectAll.search(line)
                if match:
                    hitGroups = match.group(4).split(',')
                    hits = defaultdict(lambda: defaultdict(int))
                    for h in hitGroups:
                        spatialHit  = selectSpatialHit.search(h)
                        temporalHit = selectTemporalHit.search(h)
                        if spatialHit:
                            hits['spatial'][int(spatialHit.group(1))] = int(spatialHit.group(2))
                        if temporalHit:
                            hits['temporal'][int(temporalHit.group(1))] = int(temporalHit.group(2))
                    entry = [sim.bench, sim.tags_kind]
                    entry += [sim.cacheSize,sim.cacheLineSize,sim.cacheAssoc,"_".join(map(str,sim.cacheStruct)),sim.cacheOpt]
                    entry += [float(match.group(1)),int(match.group(2)),int(match.group(3))]
                    for i in range(0,structSize):
                        entry += [hits['spatial'][i],hits['temporal'][i]]
                    entry += [int(match.group(5)),int(match.group(6)),int(match.group(7))]
                    data.append(entry)
                    break

        with open(sims[0].inputFile+"-results.csv",'w') as outfile:
            header = "bench,tags-kind,cache-size,cache-line-size,cache-assoc,cache-struct,cache-optimization,cache-hit-rate,cache-accesses,cache-hits,"
            for i in range(0,structSize):
                header += "cache-spatial-hits[{:d}],cache-temporal-hits[{:d}],".format(i,i)
            header += "cache-misses,cache-writebacks,total-mem-transactions\n"
            outfile.write(header)
            outfile.write('\n'.join(map(lambda vs: ','.join(map(str,vs)),data)))
            outfile.close()

    for inputFile in set([s.inputFile for s in simConfs]):
        sims = [s for s in simConfs if s.inputFile == inputFile]
        yield {
            'name'    : inputFile,
            'actions' : [(gather_results,[sims])],
            'file_dep': [s.outputFile() for s in sims],
            'targets' : [inputFile+"-results.csv"],
            'clean'   : [clean_targets],
            'verbosity':2
        }
