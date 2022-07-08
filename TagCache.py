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

import math
from collections import defaultdict

# util functions to turn a string of '0' and '1' into a bytearray and vice versa
def str2ba (bastr):
    # for some reason, the for loop version is faster then the map version
    a = [0]*8
    for i,c in enumerate(bastr):
        if c != '0':
            a[i] = 1
    return bytearray(a)
    #return bytearray(map(lambda c: 0 if c == '0' else 1, bastr))
def ba2str (ba):
    return ''.join(map(lambda x: '0' if x == 0 else '1', ba))

# Cache class
class Cache:
    """A cache model"""

    # internall cache record type
    class Record:
        """content of the tagCache"""
        def __init__ (self, linesize=1024, dataLineAccessed=set(), valid=False, dirty=False, tableaddr=(0,0)):
            self.valid            = valid
            self.dirty            = dirty
            self.tableaddr        = tableaddr # tuple (tablelvl, lineNumber)
            self.dataLineAccessed = dataLineAccessed

        def __str__ (self):
            return ("valid:%s, dirty:%s, addr:(lvl:%d,lineNumber:0x%x(%d)), temporal_hit:%s" % (self.valid,self.dirty,self.tableaddr[0],self.tableaddr[1],self.tableaddr[1],self.temporal_hits))

    # Cache constructor
    def __init__ (
            self,
            size=2**15, # size in bytes
            assoc=4,
            linesize=1024, # size in bits
            spatial_temporal=False,
            verbose=False):
        # attributes
        self.size             = size
        self.assoc            = assoc
        self.linesize         = linesize
        self.spatial_temporal = spatial_temporal
        self.verbose          = verbose
        # derived attributes
        self.waysize = self.size / self.assoc
        self.waylines = int(self.waysize / (self.linesize / 8))
        self.cache = [[Cache.Record(self.linesize) for y in range(self.assoc)] for z in range(self.waylines)]
        # private way counter for replacement policy
        self.__nextWay = 0
        # counters for statistics
        self.reportIndex      = 0
        self.cacheHits        = 0
        self.temporalHits     = defaultdict(lambda: 0)
        self.spatialHits      = defaultdict(lambda: 0)
        self.cacheMisses      = 0
        self.cacheWritebacks  = 0

    # private print method
    def __print(self,msg):
        if self.verbose:
            print(msg)
        else:
            return None

    # private helper method for cache hit/miss
    # returns a tuple (hit,way,record)
    def __hit(self, lvl, lineNumber):
        lookup = (False,0,None)
        for w, r in enumerate(self.cache[lineNumber%self.waylines]):
            if r.valid and (lvl,lineNumber) == r.tableaddr:
                lookup = (True,w,r)
        return lookup

    # private helper method for replacement policy
    def __replace_way(self, lvl, lineNumber):
        # TODO LRU / random / pseudo-random...
        # We implement a global way counter
        self.__nextWay += 1
        return self.__nextWay % self.assoc

    # private helper method for cache fill
    # XXX We curently do not model the layout of tables in actual memory
    # XXX This means that we neglect effects of how these tables alias with each other
    # XXX In the current model, each level of the table conceptually starts on a cache size aligned address
    def __fill(self, lvl,lineNumber):
        # first look for empty entry and fill it if found
        # for w, r in enumerate(self.cache[lineNumber%self.waylines]):
        #     if not r.valid:
        #         break
        # # if we reach this point, we need to call a replacement policy
        # else:
        #     w = self.__replace_way(lvl,lineNumber)
        w = self.__replace_way(lvl,lineNumber)
        # track writeback
        if self.cache[lineNumber%self.waylines][w].dirty:
            self.cacheWritebacks += 1
        #if (lineNumber%self.waylines == 1):
            self.__print("filled line %x, way %d" % (lineNumber%self.waylines,w))
        # fill the cache entry
        rec = Cache.Record (self.linesize, set(), True, False, (lvl,lineNumber))
        self.cache[lineNumber%self.waylines][w] = rec
        return rec

    # top-level tag-cache access method
    def access(self, lvl, bitAddr, write, dataLineAddr, countAccess, create):
        lineNumber = bitAddr >> int(math.log(self.linesize,2))
        self.__print("cache access: bitAddr %x, lineNumber %x" % (bitAddr,lineNumber))
        hit, way, r = self.__hit(lvl,lineNumber)
        if not hit:
            r = self.__fill(lvl,lineNumber)
            if create==False:
                self.cacheMisses += 1
        else:
            self.cacheHits += 1
            if countAccess:
                if self.spatial_temporal:
                    if dataLineAddr >> 6 in r.dataLineAccessed:
                        self.temporalHits[lvl] += 1
                    else:
                        self.spatialHits[lvl] += 1
                        r.dataLineAccessed.add(dataLineAddr >> 6)
        if write:
            r.dirty = True

    def clean(self, lvl, bitAddr):
        lineNumber = bitAddr >> int(math.log(self.linesize,2))
        hit, way, r = self.__hit(lvl,lineNumber)
        if hit:
            r.dirty = False

    # public reporting function
    def report_str (self, lvls):
        if (self.cacheHits != 0):
            self.reportIndex += 1
            rptstr =  "{:d}: HitRate: {:6f}".format(self.reportIndex, float(self.cacheHits)/float(self.cacheHits+self.cacheMisses))
            rptstr += ", totalAccesses: {:d}".format(self.cacheMisses+self.cacheWritebacks)
            rptstr +=  ", hits: {:d}".format(self.cacheHits)
            for lvl in range(0,lvls):
                rptstr += ", spatialHits[{:d}]: {:d}, temporalHits[{:d}]: {:d}".format(lvl,self.spatialHits[lvl], lvl, self.temporalHits[lvl])
            rptstr += ", misses: {:d}, writebacks: {:d}".format(self.cacheMisses, self.cacheWritebacks)
            return rptstr

# TagCache request type
class Request:
    """tagCache request format"""
    def __init__ (self, write=False, addr=0x00000000, tags=bytearray()):
        self.write = write
        self.addr  = addr
        self.tags  = tags

    def __str__ (self):
        return ("write:%s, addr:0x%x, tags:%s" % (self.write,self.addr,ba2str(self.tags)))

# Memory model
class Mem:
    """ a class to model a parameterizable tagCache"""

    # Mem constructor
    def __init__ (
            self,
            cachesize=2**16, # size in bytes
            cacheassoc=4,
            cachelinesize=1024, # size in bits
            tablestruct=[0,256],
            memstart=2**31, # offset in bytes (byte address)
            memsize=2**29, # size in bytes
            spatial_temporal=False,
            emptyLeafOpt=False,
            non_dirty_writes=False,
            verbose=False):
        """simulator constructor"""

        # assertions to ensure correct operation
        if len(tablestruct) > 1:
            assert tablestruct[1] >= 8, "Leaf grouping factors below 8 are not guaranteed to be garbage collected"

        # debug value
        self.reqFilter     = 0x8254800
        self.reqFilterMask = 0xFFF0000 #0xFFFF800

        # arguments attributes
        self.tablestruct      = tablestruct
        self.memstart         = memstart
        self.memsize          = memsize
        self.verbose          = verbose
        self.emptyLeafOpt     = emptyLeafOpt
        self.non_dirty_writes = non_dirty_writes
        self.totalMemTransactions = 0
        # cache
        self.cache       = Cache (cachesize, cacheassoc, cachelinesize, spatial_temporal, verbose)

        ##################
        # table memories #
        ##################
        # backing memories
        # 1 byte of bytearray per tag bit to store ==> divide by 8 to get actual memory footprint
        # one tuple per table : (bytearray, shiftAddr)
        self.tables = [(None,0)] * len(self.tablestruct)
        # histogram to record hits in each level of the table
        self.tableHits = [0] * len(self.tablestruct)
        # leaf level of the tag table
        # "3" is the shift value for the leaf, that is, 1 tag for each 8 bytes (64-bit pointers) TODO make this parameterizable ?
        self.tables[0] = (bytearray(int(memsize/8)),3)
        s = len(self.tables[0][0])
        self.__print("table lvl %d size = 0x%x(%d) bits, 0x%x(%d) bytes, addrShift: %d" % (0,s,s,int(s/8),int(s/8), self.tables[0][1]))
        # other levels of the tag table
        rest = self.tablestruct[1:]
        for (lvl,gf) in enumerate(rest):
            self.tables[lvl+1] = (bytearray(int(len(self.tables[lvl][0])/gf)),(self.tables[lvl][1]+int(math.log(gf,2))))
            s = len(self.tables[lvl+1][0])
            self.__print("table lvl %d size = 0x%x(%d) bits, 0x%x(%d) bytes, addrShift: %d" % (lvl+1,s,s,int(s/8),int(s/8),self.tables[lvl+1][1]))

    # private print method
    def __print(self,msg):
        if self.verbose:
            print(msg)
        else:
            return None

    def __filterPrint(self, addr, msg):
        #self.__print("addr: %x, filterMask: %x, filter: %x, combo: %x, == %d" % (addr, self.reqFilterMask, self.reqFilter, addr & self.reqFilterMask, (addr & self.reqFilterMask) == self.reqFilter))
        if ((addr & self.reqFilterMask) == (self.reqFilter & self.reqFilterMask)):
            self.__print(msg)

    # private helper method for lookup addresses
    # returns a list of tuples (lvl, bitAddr)
    def __get_lookup_addr(self, addr):
        addrs = []
        for lvl in range(len(self.tables)):
            bitAddr         = addr >> self.tables[lvl][1]
            addrs.append((lvl, bitAddr))
        return addrs

    # public report function
    def report (self):
        print(self.tableHits)
        print("{}, totalMemTransactions: {:d}".format(self.cache.report_str(len(self.tables)),self.totalMemTransactions))
    # memory request interface
    def putReq (self, req):
        self.totalMemTransactions += 1
        #self.__print("putting request %s" % str(req))
        req.addr = req.addr - self.memstart
        responseLevel = len(self.tables) - 1
        keepGoing = True
        createNext = False

        #self.__filterPrint(req.addr, "Request: %s" % (req))
        # only consider in range accesses
        if req.addr < self.memsize:
            lookupAddrs = self.__get_lookup_addr(req.addr)
            if req.write: # write access
                # track if write data actually changed the value
                doCacheUpdate = False
                # descend the table from root to leaf
                zeroTags = all(v==0 for v in req.tags)
                for lvl, bitAddr in lookupAddrs[:0:-1]: # Iterate backward through the table, dropping the first element
                    table = self.tables[lvl][0]
                    createMe = createNext
                    createNext = False
                    if keepGoing:
                        if zeroTags and table[bitAddr] == 0:
                            self.cache.access(lvl, bitAddr, False, req.addr, True, createMe)
                            keepGoing = False
                            #self.__filterPrint(req.addr, "addr: %x stopped write in upper level %d, table index %x" % (req.addr, lvl, bitAddr))
                        else:
                            doCacheUpdate = False
                            if table[bitAddr] != 1:
                                doCacheUpdate = True
                                createNext = self.emptyLeafOpt
                            self.cache.access(lvl, bitAddr, doCacheUpdate, req.addr, False, createMe)
                            #self.__filterPrint(req.addr, "addr: %x performed write (writeDifferent: %r) in upper level %d, table index %x" % (req.addr, doCacheUpdate, lvl, bitAddr))
                            table[bitAddr] = 1
                            responseLevel -= 1
                if keepGoing:
                    lvl, bitAddr = lookupAddrs[0]
                    createMe = createNext
                    # when non dirty write optimisation is active, we make sure that we default to not updating the cache
                    doCacheUpdate = not self.non_dirty_writes
                    if self.tables[0][0][bitAddr:bitAddr+len(req.tags)] != req.tags:
                        doCacheUpdate = True
                        self.tables[0][0][bitAddr:bitAddr+len(req.tags)] = req.tags
                        #groupStr = ba2str(self.tables[0][0][bitAddr:bitAddr+len(req.tags)])
                        #self.__filterPrint(req.addr, "addr: %x wrote leaf level, writeDifferent: %r table index %x <- %s" % (req.addr, doCacheUpdate, bitAddr, groupStr))
                    self.cache.access(lvl, bitAddr, doCacheUpdate, req.addr, True, createMe)
                # Clean up the table
                # from leaf back to root
                clearNext = False
                # NB: we drop the leaf grouping factor and artificially append a 1 to have a vector of appropriate size.
                #     This extra 1 is not actually used.
                if zeroTags and doCacheUpdate:
                    for (groupFactor,(lvl,(table,addrShift))) in zip(self.tablestruct[1:]+[1],enumerate(self.tables)):
                        entAddr = (req.addr>>addrShift)
                        if clearNext:
                            table[entAddr] = 0
                        groupAddr = entAddr - (entAddr%groupFactor)
                        if (groupFactor != 1) and all(v==0 for v in table[groupAddr:groupAddr+groupFactor]):
                            clearNext = True
                            if self.emptyLeafOpt:
                                self.cache.clean(lvl,entAddr)
                            #groupStr = ba2str(table[groupAddr:groupAddr+groupFactor])
                            #self.__filterPrint(req.addr, "addr: %x garbage collected %x : %s, checked %d addresses" % (req.addr, groupAddr,groupStr,groupFactor))
                        #else:
                        #    if (groupFactor != 1):
                                #groupStr = ba2str(table[groupAddr:groupAddr+groupFactor])
                                #self.__filterPrint(req.addr, "addr: %x did not collect %x : %s, checked %d addresses" % (req.addr, groupAddr,groupStr,groupFactor))
                        #self.__print("groupFactor: %d, addr: %x, entryAddr: %x, groupAddr: %x, group: %s" % (len(table[groupAddr:groupAddr+groupFactor]), req.addr, entAddr, groupAddr, ba2str(table[groupAddr:groupAddr+groupFactor])))

            else: # read access
                for (lvl, bitAddr) in lookupAddrs[::-1]: # Iterate backward through the table, dropping the first element
                    table = self.tables[lvl][0]
                    if keepGoing:
                        # block just for debugging output
                        myGroup = 1
                        if (lvl < len(self.tablestruct)-1):
                            myGroup = self.tablestruct[lvl+1]
                        groupBase = bitAddr - (bitAddr%myGroup)
                        #groupStr = ba2str(table[groupBase:groupBase+myGroup])
                        if table[bitAddr] == 0 or lvl == 0:
                            #self.__filterPrint(req.addr, "addr: %x satisfied read in level %d, table index %x : %s" % (req.addr, lvl, bitAddr, groupStr))
                            keepGoing = False
                        else:
                            responseLevel -= 1
                            #self.__filterPrint(req.addr, "addr: %x read 1 in level %d, table index %x : %s" % (req.addr, lvl, bitAddr, groupStr))
                        self.cache.access(lvl, bitAddr, False, req.addr, not keepGoing, False)
            self.tableHits[responseLevel] += 1
            #self.__print (responseLevel)

        else:
            print ("memory out-of-range access")
