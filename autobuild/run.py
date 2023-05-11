#!/usr/bin/python3
#
# Copyright (c) 2023 Benjamin Gilbert
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, version 2.1.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program. If not, see
# <http://www.gnu.org/licenses/>.
#

from datetime import datetime
import json
import os
from pathlib import Path
import requests
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.parse import urljoin

BASEURL = os.getenv('AUTOBUILD_BASEURL')
DISCORD = os.getenv('AUTOBUILD_DISCORD')
REPO = "https://github.com/openslide/openslide"
CONTAINER = 'openslide-builder'
PRUNE_DAYS = 60

STATEDIR = Path.home() / 'state'
SRCDIR = STATEDIR / 'src'
CACHEDIR = STATEDIR / 'cache'
LOGDIR = STATEDIR / 'logs'
TMPDIR = STATEDIR / 'tmp'

class Skip(Exception):
    pass


def setup():
    # create dirs
    for subdir in SRCDIR, CACHEDIR, LOGDIR, TMPDIR:
        subdir.mkdir(parents=True, exist_ok=True)

    # prune
    threshold = time.time() - PRUNE_DAYS * 86400
    for path in LOGDIR.iterdir():
        if path.stat().st_mtime < threshold:
            path.unlink()

    # rebuild container
    subprocess.run(
        [
            'podman', 'build', '--pull', '-t', CONTAINER,
            Path(__file__).parent,
        ],
        check=True
    )

    # fetch
    if (SRCDIR / '.git').exists():
        subprocess.run(
            ['git', 'fetch', 'origin', 'main'], cwd=SRCDIR, check=True
        )
        old = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=SRCDIR, check=True, stdout=subprocess.PIPE
        ).stdout
        new = subprocess.run(
            ['git', 'rev-parse', 'FETCH_HEAD'],
            cwd=SRCDIR, check=True, stdout=subprocess.PIPE
        ).stdout
        if old == new and not os.getenv('AUTOBUILD_FORCE', ''):
            raise Skip
        subprocess.run(
            ['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=SRCDIR, check=True
        )
    else:
        subprocess.run(['git', 'clone', REPO, SRCDIR], check=True)


def report(ok, log_url=None, mosaic_url=None):
    if ok:
        title = 'Build succeeded'
        color = 0x417505
        image = {
            'url': mosaic_url,
        }
    else:
        title = 'Build failed'
        color = 0xd0021b
        image = None

    requests.post(f'{DISCORD}?wait=true', json.dumps({
        'embeds': [
            {
                'title': title,
                'color': color,
                'image': image,
                'url': log_url,
            },
        ],
        'allowed_mentions': {
            'parse': [],
        },
    }), headers={
        'Content-Type': 'application/json',
    }).raise_for_status()


def run():
    setup()

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    mosaic_url = None
    with TemporaryDirectory(dir=TMPDIR) as tmpdir:
        tmpdir = Path(tmpdir)
        logpath = tmpdir / 'log'
        with open(logpath, 'wb+') as log:
            try:
                subprocess.run(
                    [
                        'podman', 'run', '--rm',
                        '--security-opt', 'label=disable',
                        '-v', f'{SRCDIR}:/src',
                        '-v', f'{CACHEDIR}:/cache',
                        '-v', f'{tmpdir}:/out',
                        CONTAINER,
                    ],
                    check=True,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )

                filename = f'{stamp}-mosaic.png'
                (tmpdir / 'mosaic.png').rename(LOGDIR / filename)
                mosaic_url = urljoin(BASEURL, filename)

                ok = True
            except subprocess.CalledProcessError:
                ok = False
 
            log.seek(0)
            filename = f'{stamp}-log.html'
            with open(LOGDIR / filename, 'wb') as out:
                subprocess.run(
                    ['aha', '-t', f'Build logs {stamp}'],
                    stdin=log, stdout=out, check=True
                )
            log_url = urljoin(BASEURL, filename)

    return (ok, log_url, mosaic_url)


def main():
    try:
        ok, log_url, mosaic_url = run()
    except Skip:
        return
    except Exception:
        report(False)
        raise
    else:
        report(ok, log_url, mosaic_url)


if __name__ == '__main__':
    main()
