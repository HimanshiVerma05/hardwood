#!/usr/bin/env python3
#
#  SPDX-License-Identifier: Apache-2.0
#
#  Copyright The original authors
#
#  Licensed under the Apache Software License version 2.0, available at http://www.apache.org/licenses/LICENSE-2.0
#

"""
Rewrite an asciinema cast in place: convert dive's two indexed accent
colors (`33` / `34`) into truecolor RGB so the rendered cast matches
what a `$COLORTERM=truecolor` recording would produce.

Mapping (matches `dive/internal/Theme.java`):
  ANSI 34 (blue)   -> Solarized blue   #268bd2
  ANSI 33 (yellow) -> Solarized yellow #b58900

Other SGR parameters (bold `1`, dim `2`, reset `0`) are left untouched.
Extended-color sequences (`38;5;N`, `38;2;R;G;B`, and `48;...`) are
skipped over so their numeric arguments are not misread as fg codes.
"""
import json
import re
import sys

ACCENT = (38, 139, 210)        # #268bd2
SELECTION = (181, 137, 0)      # #b58900

SGR = re.compile(r'\x1b\[([0-9;]*)m')


def rewrite_params(params: str) -> str:
    if not params:
        return params
    parts = params.split(';')
    out = []
    i = 0
    while i < len(parts):
        p = parts[i]
        # Skip extended fg/bg color introducers so their args (which can
        # contain 33 / 34) aren't reinterpreted as standalone codes.
        if p in ('38', '48') and i + 1 < len(parts):
            mode = parts[i + 1]
            if mode == '5' and i + 2 < len(parts):
                out.extend(parts[i:i + 3])
                i += 3
                continue
            if mode == '2' and i + 4 < len(parts):
                out.extend(parts[i:i + 5])
                i += 5
                continue
        if p == '34':
            r, g, b = ACCENT
            out.extend(['38', '2', str(r), str(g), str(b)])
        elif p == '33':
            r, g, b = SELECTION
            out.extend(['38', '2', str(r), str(g), str(b)])
        else:
            out.append(p)
        i += 1
    return ';'.join(out)


def transform(payload: str) -> str:
    return SGR.sub(lambda m: f'\x1b[{rewrite_params(m.group(1))}m', payload)


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: cast-truecolor.py <in.cast> <out.cast>")
    with open(sys.argv[1], 'r', encoding='utf-8') as src, \
         open(sys.argv[2], 'w', encoding='utf-8') as dst:
        header = src.readline()
        dst.write(header)
        for line in src:
            if not line.strip():
                dst.write(line)
                continue
            ev = json.loads(line)
            if isinstance(ev, list) and len(ev) >= 3 and ev[1] == 'o':
                ev[2] = transform(ev[2])
            dst.write(json.dumps(ev, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    main()
