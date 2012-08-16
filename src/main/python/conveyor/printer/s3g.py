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
import makerbot_driver
import os.path
import serial
import threading
import time

import conveyor.event
import conveyor.task

class S3gDetectorThread(conveyor.stoppable.StoppableThread):
    def __init__(self, config, server):
        conveyor.stoppable.StoppableThread.__init__(self)
        self._available = {}
        self._config = config
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._detector = makerbot_driver.MachineDetector()
        self._log = logging.getLogger(self.__class__.__name__)
        self._server = server
        self._stop = False

    def _runiteration(self):
        available = self._detector.get_available_machines().copy()
        self._log.debug('available = %r', available)
        old_keys = set(self._available.keys())
        new_keys = set(available.keys())
        detached = old_keys - new_keys
        attached = new_keys - old_keys
        for portname in detached:
            self._server.removeprinter(portname)
        if len(attached) > 0:
            profiledir = self._config['common']['profiledir']
            factory = makerbot_driver.BotFactory(profiledir)
            for portname in attached:
                s3g, profile = factory.build_from_port(portname, True)
                fp = s3g.writer.file
                printer = S3gPrinter(portname, fp, profile)
                self._server.appendprinter(portname, printer)
        self._available = available

    def run(self):
        while not self._stop:
            try:
                self._runiteration()
            except:
                self._log.error('unhandled exception', exc_info=True)
            if not self._stop:
                with self._condition:
                    self._condition.wait(10.0)

    def stop(self):
        with self._condition:
            self._stop = True
            self._condition.notify_all()

class S3gPrinterThread(conveyor.stoppable.StoppableThread):
    def __init__(self, fp, profile):
        conveyor.stoppable.StoppableThread.__init__(self)
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._fp = fp
        self._profile = profile
        self._stop = False

    def run(self):
        try:
            while not self._stop:
                pass
        except:
            pass

    def stop(self):
        with self._condition:
            self._stop = True
            self._condition.notify_all()

class S3gPrinter(object):
    def __init__(self, devicename, fp, profile):
        self._devicename = devicename
        self._fp = fp
        self._log = logging.getLogger(self.__class__.__name__)
        self._pollinterval = 5.0
        self._profile = profile

    def _gcodelines(self, gcodepath, skip_start_end):
        if not skip_start_end:
            startgcode = self._profile.values['print_start_sequence']
            if None is not startgcode:
                for data in startgcode:
                    yield data
        with open(gcodepath, 'r') as gcodefp:
            for data in gcodefp:
                yield data
        if not skip_start_end:
            endgcode = self._profile.values['print_end_sequence']
            if None is not endgcode:
                for data in endgcode:
                    yield data

    def _countgcodelines(self, gcodepath, skip_start_end=False):
        lines = 0
        bytes = 0
        for data in enumerate(self._gcodelines(gcodepath, skip_start_end)):
            lines += 1
            bytes += len(data)
        return (lines, bytes)

    def _genericprint(self, task, writer, polltemperature, gcodepath, skip_start_end):
        parser = makerbot_driver.Gcode.GcodeParser()
        parser.state.profile = self._profile
        parser.state.set_build_name(str('xyzzy'))
        parser.s3g = makerbot_driver.s3g()
        parser.s3g.writer = writer
        now = time.time()
        polltime = now + self._pollinterval
        if polltemperature:
            platformtemperature = parser.s3g.get_platform_temperature(0)
            toolheadtemperature = parser.s3g.get_toolhead_temperature(0)
        totallines, totalbytes = self._countgcodelines(gcodepath, skip_start_end)
        currentbyte = 0
        for currentline, data in enumerate(self._gcodelines(gcodepath, skip_start_end)):
            currentbyte += len(data)
            now = time.time()
            if polltemperature:
                if polltime <= now:
                    platformtemperature = parser.s3g.get_platform_temperature(0)
                    toolheadtemperature = parser.s3g.get_toolhead_temperature(0)
                    self._log.info('platform temperature: %r', platformtemperature)
                    self._log.info('toolhead temperature: %r', toolheadtemperature)
            data = data.strip()
            self._log.info('gcode: %r', data)
            data = str(data)
            parser.execute_line(data)
            progress = {
                'currentline': currentline,
                'totallines': totallines,
                'currentbyte': currentbyte,
                'totalbytes': totalbytes,
            }
            if polltime <= now:
                polltime = now + self._pollinterval
                if polltemperature:
                    progress['platformtemperature'] = platformtemperature
                    progress['toolheadtemperature'] = toolheadtemperature
                task.heartbeat(progress)

    def print(self, gcodepath, skip_start_end):
        self._log.debug('gcodepath=%r', gcodepath)
        def runningcallback(task):
            try:
                writer = makerbot_driver.Writer.StreamWriter(self._fp)
                self._genericprint(task, writer, True, gcodepath, skip_start_end)
            except Exception as e:
                self._log.exception('unhandled exception')
                task.fail(e)
            else:
                task.end(None)
        task = conveyor.task.Task()
        task.runningevent.attach(runningcallback)
        return task

    def printtofile(self, gcodepath, s3gpath, skip_start_end):
        self._log.debug('gcodepath=%r', gcodepath)
        def runningcallback(task):
            try:
                with open(s3gpath, 'w') as s3gfp:
                    writer = makerbot_driver.Writer.FileWriter(s3gfp)
                    self._genericprint(task, writer, False, gcodepath, skip_start_end)
            except Exception as e:
                self._log.exception('unhandled exception')
                task.fail(e)
            else:
                task.end(None)
        task = conveyor.task.Task()
        task.runningevent.attach(runningcallback)
        return task
