# coding=utf-8
"""
Cmd2 functional testing based on transcript

Copyright 2016 Federico Ceratto <federico.ceratto@gmail.com>
Released under MIT license, see LICENSE file
"""
import argparse
import os
import sys
import re
import random

from unittest import mock
import pytest

import cmd2
from .conftest import run_cmd, StdOut, normalize

class CmdLineApp(cmd2.Cmd):

    MUMBLES = ['like', '...', 'um', 'er', 'hmmm', 'ahh']
    MUMBLE_FIRST = ['so', 'like', 'well']
    MUMBLE_LAST = ['right?']

    def __init__(self, *args, **kwargs):
        self.multilineCommands = ['orate']
        self.maxrepeats = 3
        self.redirector = '->'

        # Add stuff to settable and/or shortcuts before calling base class initializer
        self.settable['maxrepeats'] = 'Max number of `--repeat`s allowed'

        super().__init__(*args, **kwargs)
        self.intro = 'This is an intro banner ...'

    speak_parser = argparse.ArgumentParser()
    speak_parser.add_argument('-p', '--piglatin', action="store_true", help="atinLay")
    speak_parser.add_argument('-s', '--shout', action="store_true", help="N00B EMULATION MODE")
    speak_parser.add_argument('-r', '--repeat', type=int, help="output [n] times")

    @cmd2.with_argparser_and_unknown_args(speak_parser)
    def do_speak(self, opts, arg):
        """Repeats what you tell me to."""
        arg = ' '.join(arg)
        if opts.piglatin:
            arg = '%s%say' % (arg[1:], arg[0])
        if opts.shout:
            arg = arg.upper()
        repetitions = opts.repeat or 1
        for i in range(min(repetitions, self.maxrepeats)):
            self.poutput(arg)
            # recommend using the poutput function instead of
            # self.stdout.write or "print", because Cmd allows the user
            # to redirect output

    do_say = do_speak  # now "say" is a synonym for "speak"
    do_orate = do_speak  # another synonym, but this one takes multi-line input

    mumble_parser = argparse.ArgumentParser()
    mumble_parser.add_argument('-r', '--repeat', type=int, help="output [n] times")
    @cmd2.with_argparser_and_unknown_args(mumble_parser)
    def do_mumble(self, opts, arg):
        """Mumbles what you tell me to."""
        repetitions = opts.repeat or 1
        arg = arg.split()
        for i in range(min(repetitions, self.maxrepeats)):
            output = []
            if random.random() < .33:
                output.append(random.choice(self.MUMBLE_FIRST))
            for word in arg:
                if random.random() < .40:
                    output.append(random.choice(self.MUMBLES))
                output.append(word)
            if random.random() < .25:
                output.append(random.choice(self.MUMBLE_LAST))
            self.poutput(' '.join(output))


class DemoApp(cmd2.Cmd):
    hello_parser = argparse.ArgumentParser()
    hello_parser.add_argument('-n', '--name', help="your name")
    @cmd2.with_argparser_and_unknown_args(hello_parser)
    def do_hello(self, opts, arg):
        """Says hello."""
        if opts.name:
            self.stdout.write('Hello {}\n'.format(opts.name))
        else:
            self.stdout.write('Hello Nobody\n')


@pytest.fixture
def _cmdline_app():
    c = CmdLineApp()
    c.stdout = StdOut()
    return c


@pytest.fixture
def _demo_app():
    c = DemoApp()
    c.stdout = StdOut()
    return c


def _get_transcript_blocks(transcript):
    cmd = None
    expected = ''
    for line in transcript.splitlines():
        if line.startswith('(Cmd) '):
            if cmd is not None:
                yield cmd, normalize(expected)

            cmd = line[6:]
            expected = ''
        else:
            expected += line + '\n'
    yield cmd, normalize(expected)


def test_base_with_transcript(_cmdline_app):
    app = _cmdline_app
    transcript = """
(Cmd) help

Documented commands (type help <topic>):
========================================
alias  help     load    orate  pyscript  say  shell      speak  
edit   history  mumble  py     quit      set  shortcuts  unalias

(Cmd) help say
usage: speak [-h] [-p] [-s] [-r REPEAT]

Repeats what you tell me to.

optional arguments:
  -h, --help            show this help message and exit
  -p, --piglatin        atinLay
  -s, --shout           N00B EMULATION MODE
  -r REPEAT, --repeat REPEAT
                        output [n] times

(Cmd) say goodnight, Gracie
goodnight, Gracie
(Cmd) say -ps --repeat=5 goodnight, Gracie
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
(Cmd) set maxrepeats 5
maxrepeats - was: 3
now: 5
(Cmd) say -ps --repeat=5 goodnight, Gracie
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
(Cmd) history
-------------------------[1]
help
-------------------------[2]
help say
-------------------------[3]
say goodnight, Gracie
-------------------------[4]
say -ps --repeat=5 goodnight, Gracie
-------------------------[5]
set maxrepeats 5
-------------------------[6]
say -ps --repeat=5 goodnight, Gracie
(Cmd) history -r 4
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
OODNIGHT, GRACIEGAY
(Cmd) set prompt "---> "
prompt - was: (Cmd)
now: --->
"""

    for cmd, expected in _get_transcript_blocks(transcript):
        out = run_cmd(app, cmd)
        assert out == expected


class TestMyAppCase(cmd2.cmd2.Cmd2TestCase):
    CmdApp = CmdLineApp
    CmdApp.testfiles = ['tests/transcript.txt']


def test_comment_stripping(_cmdline_app):
    out = run_cmd(_cmdline_app, 'speak it was /* not */ delicious! # Yuck!')
    expected = normalize("""it was delicious!""")
    assert out == expected


def test_argparser_correct_args_with_quotes_and_midline_options(_cmdline_app):
    out = run_cmd(_cmdline_app, "speak 'This is a' -s test of the emergency broadcast system!")
    expected = normalize("""THIS IS A TEST OF THE EMERGENCY BROADCAST SYSTEM!""")
    assert out == expected


def test_argparser_options_with_spaces_in_quotes(_demo_app):
    out = run_cmd(_demo_app, "hello foo -n 'Bugs Bunny' bar baz")
    expected = normalize("""Hello Bugs Bunny""")
    assert out == expected


def test_commands_at_invocation():
    testargs = ["prog", "say hello", "say Gracie", "quit"]
    expected = "This is an intro banner ...\nhello\nGracie\n"
    with mock.patch.object(sys, 'argv', testargs):
        app = CmdLineApp()
        app.stdout = StdOut()
        app.cmdloop()
        out = app.stdout.buffer
        assert out == expected

def test_invalid_syntax(_cmdline_app, capsys):
    run_cmd(_cmdline_app, 'speak "')
    out, err = capsys.readouterr()
    expected = normalize("""ERROR: Invalid syntax: No closing quotation""")
    assert normalize(str(err)) == expected


@pytest.mark.parametrize('filename, feedback_to_output', [
    ('bol_eol.txt', False),
    ('characterclass.txt', False),
    ('dotstar.txt', False),
    ('extension_notation.txt', False),
    # ('from_cmdloop.txt', True),
    ('multiline_no_regex.txt', False),
    ('multiline_regex.txt', False),
    ('regex_set.txt', False),
    ('singleslash.txt', False),
    ('slashes_escaped.txt', False),
    ('slashslash.txt', False),
    ('spaces.txt', False),
    # ('word_boundaries.txt', False),
    ])
def test_transcript(request, capsys, filename, feedback_to_output):
    # Create a cmd2.Cmd() instance and make sure basic settings are
    # like we want for test
    app = CmdLineApp()
    app.feedback_to_output = feedback_to_output

    # Get location of the transcript
    test_dir = os.path.dirname(request.module.__file__)
    transcript_file = os.path.join(test_dir, 'transcripts', filename)

    # Need to patch sys.argv so cmd2 doesn't think it was called with
    # arguments equal to the py.test args
    testargs = ['prog', '-t', transcript_file]
    with mock.patch.object(sys, 'argv', testargs):
        # Run the command loop
        app.cmdloop()

    # Check for the unittest "OK" condition for the 1 test which ran
    expected_start = ".\n----------------------------------------------------------------------\nRan 1 test in"
    expected_end = "s\n\nOK\n"
    out, err = capsys.readouterr()
    assert err.startswith(expected_start)
    assert err.endswith(expected_end)


@pytest.mark.parametrize('expected, transformed', [
    # strings with zero or one slash or with escaped slashes means no regular
    # expression present, so the result should just be what re.escape returns.
    # we don't use static strings in these tests because re.escape behaves
    # differently in python 3.7 than in prior versions
    ( 'text with no slashes', re.escape('text with no slashes') ),
    ( 'specials .*', re.escape('specials .*') ),
    ( 'use 2/3 cup', re.escape('use 2/3 cup') ),
    ( '/tmp is nice', re.escape('/tmp is nice') ),
    ( 'slash at end/', re.escape('slash at end/') ),
    # escaped slashes
    ( 'not this slash\/ or this one\/', re.escape('not this slash/ or this one/' ) ),
    # regexes
    ( '/.*/', '.*' ),
    ( 'specials ^ and + /[0-9]+/', re.escape('specials ^ and + ') + '[0-9]+' ),
    ( '/a{6}/ but not \/a{6} with /.*?/ more', 'a{6}' + re.escape(' but not /a{6} with ') + '.*?' + re.escape(' more') ),
    ( 'not \/, use /\|?/, not \/', re.escape('not /, use ') + '\|?' + re.escape(', not /') ),
    # inception: slashes in our regex. backslashed on input, bare on output
    ( 'not \/, use /\/?/, not \/', re.escape('not /, use ') + '/?' + re.escape(', not /') ),
    ( 'lots /\/?/ more /.*/ stuff', re.escape('lots ') + '/?' + re.escape(' more ') + '.*' + re.escape(' stuff') ),
    ])
def test_parse_transcript_expected(expected, transformed):
    app = CmdLineApp()

    class TestMyAppCase(cmd2.cmd2.Cmd2TestCase):
        cmdapp = app

    testcase = TestMyAppCase()
    assert testcase._transform_transcript_expected(expected) == transformed
