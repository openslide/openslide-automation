#!/usr/bin/python
#
# resubmit-changes - Re-notify Buildbot of most recent repo push
#
# Copyright (c) 2014 Benjamin Gilbert
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

import getpass
import github3
import sys

ORGANIZATION = 'openslide'

code_2fa = None


def get_2fa_code():
    global code_2fa
    if code_2fa is None:
        code_2fa = raw_input('2FA code: ')
    return code_2fa


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print >>sys.stderr, 'Usage: %s repo-names' % sys.argv[0]
        sys.exit(1)

    username = raw_input('GitHub username: ')
    password = getpass.getpass('GitHub password: ')
    gh = github3.login(username, password, two_factor_callback=get_2fa_code)

    for repo_name in sys.argv[1:]:
        repo = gh.repository(ORGANIZATION, repo_name)
        for hook in repo.iter_hooks():
            if hook.name == 'web':
                hook.test()
