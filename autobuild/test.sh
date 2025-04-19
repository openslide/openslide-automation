#!/bin/bash
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

set -euxo pipefail

export OPENSLIDE_TEST_CACHE="/cache"
SRC="/src"
BUILD="/build"
OUT="/out"

# build
cd "$SRC"
git rev-parse HEAD
# disable werror for libdicom 1.2.0
# https://github.com/ImagingDataCommons/libdicom/pull/100
if ! meson setup "$BUILD" --werror -Dlibdicom:werror=false; then
    cat "$BUILD/meson-logs/meson-log.txt"
    exit 1
fi
cd "$BUILD"
meson compile

# smoke tests
if ! meson test; then
    cat meson-logs/testlog.txt
    exit 1
fi
cat meson-logs/testlog.txt

# unpack
test/driver unfreeze
test/driver unpack nonfrozen

# test
test/driver run
test/driver valgrind
test/driver mosaic "$OUT/mosaic.png"
