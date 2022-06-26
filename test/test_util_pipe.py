# -*- coding: utf-8 -*-
#
# Picard, the next-generation MusicBrainz tagger
#
# Copyright (C) 2022 skelly37
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import concurrent.futures
from platform import python_version
from random import randint

from test.picardtestcase import PicardTestCase

from picard import log
from picard.util import pipe


def pipe_listener(pipe_handler):
    IGNORED_OUTPUT = {pipe.Pipe.MESSAGE_TO_IGNORE, pipe.Pipe.NO_RESPONSE_MESSAGE, ""}
    received = ""

    while not received:
        for message in pipe_handler.read_from_pipe():
            if message not in IGNORED_OUTPUT:
                received = message
                break

    log.debug("returning: %r", received)
    return received


def pipe_writer(pipe_handler, to_send):
    if not to_send:
        return False

    while not pipe_handler.send_to_pipe(to_send):
        pass

    return True


class TestPipe(PicardTestCase):
    # we don't need any strong and secure random numbers, just anything that is different on each run
    NAME = str(randint(0, 99999999))    # nosec
    VERSION = python_version()

    def test_invalid_args(self):
        # Pipe should be able to make args iterable (last argument)
        self.assertRaises(pipe.PipeErrorInvalidArgs, pipe.Pipe, self.NAME, self.VERSION, 1)
        self.assertRaises(pipe.PipeErrorInvalidAppData, pipe.Pipe, 21, self.VERSION, None)
        self.assertRaises(pipe.PipeErrorInvalidAppData, pipe.Pipe, self.NAME, 21, None)

    def test_pipe_protocol(self):
        to_send = {
            "it", "tests", "picard", "pipe",
            "test", "number", "two",
            "my_music_file.mp3", "last-case",
            TestPipe.NAME, TestPipe.VERSION
        }

        pipe_listener_handler = pipe.Pipe(self.NAME, self.VERSION)
        if pipe_listener_handler.path_was_forced:
            pipe_writer_handler = pipe.Pipe(self.NAME, self.VERSION, args=None, forced_path=pipe_listener_handler.path)
        else:
            pipe_writer_handler = pipe.Pipe(self.NAME, self.VERSION)

        __pool = concurrent.futures.ThreadPoolExecutor()
        for count in range(100):
            for message in to_send:
                for iteration in range(20):
                    log.debug("No. %d attempt to send: %r", iteration+1, message)
                    plistener = __pool.submit(pipe_listener, pipe_listener_handler)
                    pwriter = __pool.submit(pipe_writer, pipe_writer_handler, message)
                    to_break = False
                    try:
                        self.assertEqual(plistener.result(timeout=6.5), message,
                                        "Data is sent and read correctly")
                        log.debug("Sent correctly!")
                        to_break = True
                    except concurrent.futures._base.TimeoutError:
                        pipe_writer_handler.send_to_pipe(pipe_writer_handler.MESSAGE_TO_IGNORE)

                    try:
                        pwriter.result(timeout=0.01)
                    except concurrent.futures._base.TimeoutError:
                        pipe_listener_handler.read_from_pipe()

                    if to_break:
                        break
