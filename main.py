#!/usr/bin/env python3
"""Entry point for news-image-20261120 v12.

Standard library only: copy the pre-rendered front page into the
output directory the harness provides. No drawing, no network, no
clock -- the same bytes are written on every run.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "."
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(HERE, "entry.png")
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(src, dst)
    print("copied entry.png ->", dst)


if __name__ == "__main__":
    sys.exit(main())
