#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
from enum import IntEnum


def enum(*values, **kwargs):
    names = kwargs.get('names')
    if names:
        return collections.namedtuple('Enum', names)(*values)
    return collections.namedtuple('Enum', values)(*values)

NODE_ROLE = enum(
    'master',
    'slave',
    'k8s',
    'k8s_scale',
)

NETWORK_TYPE = enum(
    'private',
    'public'
)

SNAPSHOT = enum(
    'underlay',
    'k8s_deployed',
    'ccp_deployed',
    'os_deployed',
    'os_deployed_stacklight'
)

LOG_LEVELS = enum(
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL',
    'DEBUG',
    'NOTE'
)


class ExitCodes(IntEnum):
    EX_OK = 0  # successful termination
    EX_INVALID = 0xDEADBEEF  # uint32 debug value. Impossible for POSIX
    EX_ERROR = 1  # general failure
    EX_BUILTIN = 2  # Misuse of shell builtins (according to Bash)
    EX_USAGE = 64  # command line usage error
    EX_DATAERR = 65  # data format error
    EX_NOINPUT = 66  # cannot open input
    EX_NOUSER = 67  # addressee unknown
    EX_NOHOST = 68  # host name unknown
    EX_UNAVAILABLE = 69  # service unavailable
    EX_SOFTWARE = 70  # internal software error
    EX_OSERR = 71  # system error (e.g., can't fork)
    EX_OSFILE = 72  # critical OS file missing
    EX_CANTCREAT = 73  # can't create (user) output file
    EX_IOERR = 74  # input/output error
    EX_TEMPFAIL = 75  # temp failure; user is invited to retry
    EX_PROTOCOL = 76  # remote error in protocol
    EX_NOPERM = 77  # permission denied
    EX_CONFIG = 78  # configuration error
    EX_NOEXEC = 126  # If a command is found but is not executable
    EX_NOCMD = 127  # If a command is not found


class HttpCodes(enumerate):
    OK = '200'


class Namespace(enumerate):
    BASE_NAMESPACE = 'ccp'
