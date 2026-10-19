#!/usr/bin/env python3
"""Install the fallback only when the selected upstream source still needs it."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'patches/uhttpd/950-handle-unknown-ucode-status.patch'

def needs_patch(source):
    match = re.search(r'switch\s*\(status\)\s*\{(.*?)\n\s*\}', source, re.S)
    if not match:
        raise ValueError('Cannot locate uhttpd VM status switch; review upstream changes')
    body = match.group(1)
    return not re.search(r'\bdefault\s*:|\bcase\s+STATUS_BREAK\s*:', body)

def install(tree, source):
    output = tree / 'package/network/services/uhttpd/patches' / PATCH.name
    if not needs_patch(source):
        output.unlink(missing_ok=True)
        print('uhttpd upstream already handles VM statuses; compatibility patch skipped')
        return
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, 'ucode.c').write_text(source)
        subprocess.run(['patch', '--dry-run', '--batch', '--fuzz=0', '-p1', '-i', str(PATCH)], cwd=directory, check=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(PATCH.read_bytes())
    print('Verified and installed uhttpd compatibility patch')

if __name__ == '__main__':
    tree = Path(sys.argv[1])
    makefile = (tree / 'package/network/services/uhttpd/Makefile').read_text()
    version = re.search(r'^PKG_SOURCE_VERSION\s*:?=\s*([0-9a-f]{40})\s*$', makefile, re.M)
    if not version:
        raise SystemExit('Cannot determine uhttpd source revision')
    revision = version.group(1)
    print('Checking uhttpd source revision:', revision)
    with urlopen(f'https://raw.githubusercontent.com/openwrt/uhttpd/{revision}/ucode.c', timeout=45) as response:
        source = response.read().decode()
    install(tree, source)
