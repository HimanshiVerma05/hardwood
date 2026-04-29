#!/usr/bin/env python3
#
#  SPDX-License-Identifier: Apache-2.0
#
#  Copyright The original authors
#
#  Licensed under the Apache Software License version 2.0, available at http://www.apache.org/licenses/LICENSE-2.0
#

"""
Drives `hardwood dive` for an asciinema demo. Wrap with:

    asciinema rec dive-demo.cast \
        --rows 40 --cols 120 --idle-time-limit 2 \
        -c "tools/dive-demo.py s3://test-bucket/overture_places.zstd.parquet"

Requires `pexpect` (pip install pexpect). AWS credentials for the S3
bucket must be available to the default credentials provider chain
(environment, profile, or instance role).

The `hardwood` binary is resolved in this order:
  1. $HARDWOOD_BIN (absolute path or PATH-resolvable name)
  2. ./bin/hardwood relative to the repo root (../ from this script)
  3. `hardwood` on $PATH

Demo flow:
  Overview -> Footer & indexes (linger) -> back ->
  Row groups -> 5th row group -> Column chunks -> websites ->
  Dictionary -> back -> Pages -> first data page (header modal) ->
  jump to Overview -> Data preview -> 5th row (row modal) -> quit.
"""
import os
import shutil
import sys
from pathlib import Path

import pexpect

ESC = "\x1b"
ENTER = "\r"
TAB = "\t"
DOWN = "\x1b[B"
UP = "\x1b[A"

SHORT = 0.5
READ = 1.6
LOAD = 2.5

# Leaf-column index of the `websites` column chunk on the ColumnChunks
# screen, counted from 0. ColumnChunks has no search, so we navigate by
# pressing Down this many times. The exact value depends on the schema:
# leaves are listed in schema order including struct/list expansions
# (e.g. `bbox.xmin`, `sources.list.element.dataset`, ...). Verify once
# interactively against the file and update.
WEBSITES_COLUMN_INDEX = 22


def pace(child, d):
    """Wait `d` seconds while draining the child PTY.

    `logfile_read = sys.stdout` only mirrors bytes that pexpect actually
    reads, so a plain `time.sleep` would leave the buffer un-drained and
    the parent terminal blank. `expect(TIMEOUT)` makes pexpect read in
    the background until the timeout fires.
    """
    try:
        child.expect(pexpect.TIMEOUT, timeout=d)
    except pexpect.EOF:
        pass


def send(child, keys, delay=SHORT):
    child.send(keys)
    pace(child, delay)


def repeat(child, keys, n, delay=SHORT):
    for _ in range(n):
        send(child, keys, delay)


def resolve_hardwood():
    override = os.environ.get("HARDWOOD_BIN")
    if override:
        if os.path.isabs(override) and os.path.isfile(override) and os.access(override, os.X_OK):
            return override
        found = shutil.which(override)
        if found:
            return found
        sys.exit(f"HARDWOOD_BIN={override!r} is not an executable file or on $PATH")
    repo_bin = Path(__file__).resolve().parent.parent / "bin" / "hardwood"
    if repo_bin.is_file() and os.access(repo_bin, os.X_OK):
        return str(repo_bin)
    found = shutil.which("hardwood")
    if found:
        return found
    sys.exit("could not find `hardwood`; set HARDWOOD_BIN or add it to $PATH")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: dive-demo.py <parquet-uri>")
    target = sys.argv[1]
    hardwood = resolve_hardwood()

    child = pexpect.spawn(
        hardwood,
        ["dive", "--file", target],
        dimensions=(40, 120),
        encoding="utf-8",
        env=os.environ.copy(),
        timeout=60,
    )
    child.logfile_read = sys.stdout

    # Wait for the footer fetch + Overview render to settle.
    pace(child, LOAD)

    # --- Overview -> Footer & indexes (menu index 2) ---
    # Overview opens with MENU pane focused, selection 0 (Schema).
    repeat(child, DOWN, 2, SHORT)        # Schema -> Row groups -> Footer & indexes
    send(child, ENTER, READ)             # push Footer screen
    pace(child, 2.0)                     # linger 2s
    send(child, ESC, SHORT)              # pop -> Overview (selection still on "Footer & indexes")

    # --- Overview -> Row groups -> 5th row group -> Column chunks ---
    send(child, UP, SHORT)               # selection 2 -> 1 (Row groups)
    send(child, ENTER, READ)             # push RowGroups, selection 0
    repeat(child, DOWN, 4, SHORT)        # 1st -> 5th row group
    send(child, ENTER, READ)             # push RowGroupDetail (MENU pane, COLUMN_CHUNKS selected)
    send(child, ENTER, READ)             # push ColumnChunks, selection 0

    # --- Walk to the websites column chunk and drill in ---
    repeat(child, DOWN, WEBSITES_COLUMN_INDEX, 0.08)
    send(child, ENTER, READ)             # push ColumnChunkDetail (FACTS pane focused)

    # --- Dictionary view ---
    send(child, TAB, SHORT)              # FACTS -> MENU
    repeat(child, DOWN, 3, SHORT)        # PAGES -> COLUMN_INDEX -> OFFSET_INDEX -> DICTIONARY
    send(child, ENTER, READ * 2)         # dictionary fetch
    pace(child, READ)                    # linger on dictionary

    # --- Back to ColumnChunkDetail, switch to Pages, open first data page ---
    send(child, ESC, SHORT)              # Dictionary -> ColumnChunkDetail (MENU, sel=DICTIONARY)
    repeat(child, UP, 3, SHORT)          # DICTIONARY -> PAGES
    send(child, ENTER, READ)             # push Pages, selection 0
    send(child, DOWN, SHORT)             # 0 = dictionary page, 1 = first data page
    send(child, ENTER, READ * 2)         # open page-header modal on the data page
    pace(child, READ)

    # --- Jump to root, drill into Data preview ---
    # `o` clears the stack to Overview but does NOT reset menuSelection,
    # which is currently 1 (Row groups, set when we entered RowGroups
    # earlier). Step down 2 to reach "Data preview" (index 3).
    send(child, "o", READ)
    repeat(child, DOWN, 2, SHORT)        # Row groups -> Footer & indexes -> Data preview
    send(child, ENTER, READ * 2)         # push DataPreview (initial page load)

    # --- 5th row -> open row modal ---
    repeat(child, DOWN, 4, SHORT)        # selectedRow 0 -> 4 (5th row)
    send(child, ENTER, READ * 2)         # open the row detail modal
    pace(child, READ)

    # --- Quit ---
    send(child, "q", 0.3)
    child.expect(pexpect.EOF, timeout=15)


if __name__ == "__main__":
    main()
