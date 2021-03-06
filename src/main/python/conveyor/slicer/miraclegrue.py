# vim:ai:et:ff=unix:fileencoding=utf-8:sw=4:ts=4:
# conveyor/src/main/python/conveyor/slicer/miraclegrue.py
#
# conveyor - Printing dispatch engine for 3D objects and their friends.
# Copyright © 2012 Matthew W. Samsonoff <matthew.samsonoff@makerbot.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, print_function, unicode_literals)

import json
import os
import tempfile

import conveyor.event
import conveyor.machine.s3g # TODO: aww, bad coupling
import conveyor.slicer

class MiracleGrueSlicer(conveyor.slicer.SubprocessSlicer):
    def __init__(
        self, profile, inputpath, outputpath, with_start_end, slicer_settings,
        material, task, slicerpath, configpath):
            conveyor.slicer.SubprocessSlicer.__init__(
                self, profile, inputpath, outputpath, with_start_end,
                slicer_settings, material, task, slicerpath)

            self._tmp_startpath = None
            self._tmp_endpath = None
            self._tmp_configpath = None

            self._configpath = configpath

    def _getname(self):
        return 'Miracle Grue'

    def _prologue(self):
        if self._with_start_end:
            driver = conveyor.machine.s3g.S3gDriver()
            startgcode, endgcode, variables = driver._get_start_end_variables(
                profile, slicer_settings, material)
            with tempfile.NamedTemporaryFile(suffix='.gcode', delete=False) as startfp:
                self._tmp_startpath = startfp.name
                for line in startgcode:
                    print(line, file=startfp)
            with tempfile.NamedTemporaryFile(suffix='.gcode', delete=False) as endfp:
                self._tmp_endpath = endfp.name
                for line in endgcode:
                    print(line, file=endfp)
        config = self._getconfig()
        s = json.dumps(config)
        self._log.debug('miracle grue configuration: %s', s)
        with tempfile.NamedTemporaryFile(suffix='.config', delete=False) as configfp:
            self._tmp_configpath = configfp.name
            json.dump(config, configfp, indent=8)

    def _getconfig(self):
        with open(self._configpath, 'r') as fp:
            config = json.load(fp)
        config['infillDensity'] = self._slicer_settings.infill
        config['numberOfShells'] = self._slicer_settings.shells
        config['rapidMoveFeedRateXY'] = self._slicer_settings.travel_speed
        config['doRaft'] = self._slicer_settings.raft
        config['doSupport'] = self._slicer_settings.support
        config['doFanCommand'] = 'PLA' == self._material
        config['layerHeight'] = self._slicer_settings.layer_height
        config['defaultExtruder'] = self._slicer_settings.extruder
        config['extrusionProfiles']['insets']['feedrate'] = self._slicer_settings.print_speed
        config['extrusionProfiles']['infill']['feedrate'] = self._slicer_settings.print_speed
        return config

    def _getexecutable(self):
        return self._slicerpath

    def _getarguments(self):
        for iterable in self._getarguments_miraclegrue():
            for value in iterable:
                yield value

    def _getarguments_miraclegrue(self):
        yield (self._getexecutable(),)
        yield ('-c', self._tmp_configpath,)
        yield ('-o', self._outputpath,)
        if None is not self._tmp_startpath:
            yield ('-s', self._tmp_startpath,)
        if None is not self._tmp_endpath:
            yield ('-e', self._tmp_endpath,)
        yield ('-j',)
        yield (self._inputpath,)

    def _readpopen(self):
        while True:
            line = self._popen.stdout.readline()
            if '' == line:
                break
            else:
                self._slicerlog.write(line)
                try:
                    dct = json.loads(line)
                except ValueError:
                    pass
                else:
                    if (isinstance(dct, dict) and 'progress' == dct.get('type')
                        and 'totalPercentComplete' in dct):
                            percent = int(dct['totalPercentComplete'])
                            self._setprogress_ratio(percent, 100)

    def _epilogue(self):
        if None is not self._tmp_startpath:
            os.unlink(self._tmp_startpath)
        if None is not self._tmp_endpath:
            os.unlink(self._tmp_endpath)
        if None is not self._tmp_configpath:
            os.unlink(self._tmp_configpath)
