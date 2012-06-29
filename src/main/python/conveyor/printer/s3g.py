# vim:ai:et:ff=unix:fileencoding=utf-8:sw=4:ts=4:
# conveyor/src/main/python/conveyor/printer/s3g.py
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

import logging
import os.path
import s3g
import serial
import time

import conveyor.event
import conveyor.task

class S3gPrinter(object):
    def __init__(self, profile, device, baudrate):
        self._baudrate = baudrate
        self._device = device
        self._log = logging.getLogger(self.__class__.__name__)
        self._pollinterval = 5.0
        self._profile = profile

    def _gcodelines(self, gcodepath):
        startgcode = self._profile.values['print_start_sequence']
        if None is not startgcode:
            for data in startgcode:
                yield data
        with open(gcodepath, 'r') as gcodefp:
            for data in gcodefp:
                yield data
        endgcode = self._profile.values['print_end_sequence']
        if None is not endgcode:
            for data in endgcode:
                yield data

    def _countgcodelines(self, gcodepath):
        lines = 0
        bytes = 0
        for data in self._gcodelines(gcodepath):
            lines += 1
            bytes += len(data)
        return (lines, bytes)

    def _genericprint(self, job, task, writer, polltemperature):
        gcodepath = job.gcodepath;
        parser = s3g.Gcode.GcodeParser()
        parser.state.profile = self._profile
        parser.state.SetBuildName(str(job.name))
        self._log.info("the build name is : %s", parser.state.values['build_name'])
        parser.s3g = s3g.s3g()
        parser.s3g.writer = writer
        if polltemperature:
            platformtemperature = parser.s3g.GetPlatformTemperature(0)
            toolheadtemperature = parser.s3g.GetToolheadTemperature(0)
            now = time.time()
            polltime = now + self._pollinterval
        totallines, totalbytes = self._countgcodelines(gcodepath)
        currentbyte = 0
        for currentline, data in enumerate(self._gcodelines(gcodepath)):
            currentbyte += len(data)
            if polltemperature:
                now = time.time()
                if polltime <= now:
                    platformtemperature = parser.s3g.GetPlatformTemperature(0)
                    toolheadtemperature = parser.s3g.GetToolheadTemperature(0)
                    self._log.info('platform temperature: %r', platformtemperature)
                    self._log.info('toolhead temperature: %r', toolheadtemperature)
                    polltime = now + self._pollinterval
            data = data.strip()
            data = str(data)
            self._log.info('gcode: %s', data)
            parser.ExecuteLine(data)
            progress = {
                'currentline': currentline,
                'totallines': totallines,
                'currentbyte': currentbyte,
                'totalbytes': totalbytes,
            }
            if polltemperature:
                progress['platformtemperature'] = platformtemperature
                progress['toolheadtemperature'] = toolheadtemperature
            task.heartbeat(progress)

    def _openserial(self):
        serialfp = serial.Serial(self._device, self._baudrate, timeout=0.1)

        # begin baud rate hack
        #
        # There is an interaction between the 8U2 firmware and
        # PySerial where PySerial thinks the 8U2 is already running
        # at the specified baud rate and it doesn't actually issue
        # the ioctl calls to set the baud rate. We work around it
        # by setting the baud rate twice, to two different values.
        # This forces PySerial to issue the correct ioctl calls.
        serialfp.baudrate = 9600
        serialfp.baudrate = self._baudrate
        # end baud rate hack

        return serialfp

    def print(self, job):
        gcodepath = job.gcodepath
        self._log.debug('gcodepath=%r', gcodepath)
        def runningcallback(task):
            try:
                with self._openserial() as serialfp:
                    writer = s3g.Writer.StreamWriter(serialfp)
                    self._genericprint(job, task, writer, True)
            except Exception as e:
                self._log.exception('unhandled exception')
                task.fail(e)
            else:
                task.end(None)
        task = conveyor.task.Task()
        task.runningevent.attach(runningcallback)
        return task

    def printtofile(self, job):
        gcodepath = job.gcodepath
        s3gpath = job.s3gpath;
        self._log.debug('gcodepath=%r', gcodepath)
        def runningcallback(task):
            try:
                with open(s3gpath, 'w') as s3gfp:
                    writer = s3g.Writer.FileWriter(s3gfp)
                    self._genericprint(job, task, writer, False)
            except Exception as e:
                self._log.exception('unhandled exception')
                task.fail(e)
            else:
                task.end(None)
        task = conveyor.task.Task()
        task.runningevent.attach(runningcallback)
        return task
