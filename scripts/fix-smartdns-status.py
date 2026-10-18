#!/usr/bin/env python3
"""Fix LuCI SmartDNS treating the [false] service status as true."""
import re
import sys
from pathlib import Path


def fix(source):
    # Normalize at the renderer boundary, including already-patched callers.
    signature = r'(function\s+smartdnsRenderStatus\s*\(isRunning\)\s*\{)'
    if not re.search(signature, source):
        raise ValueError('Unrecognized SmartDNS status renderer')
    marker = '// Normalize service RPC status: arrays are truthy even for [false].'
    if marker not in source:
        source = re.sub(signature, lambda m: m[0] + '\n\t' + marker +
                        '\n\tisRunning = (Array.isArray(isRunning) ? isRunning[0] : isRunning) === true;', source, count=1)
    return source


def main():
    root = Path(sys.argv[1])
    files = {p.resolve() for folder in ('feeds', 'package')
             for p in (root / folder).rglob('smartdns.js')}
    if not files:
        raise SystemExit('SmartDNS LuCI source not found after feeds installation')
    for path in sorted(files):
        source = path.read_text()
        updated = fix(source)
        if updated != source:
            path.write_text(updated)
            print('Fixed:', path)
        else:
            print('Status normalization already installed:', path)

if __name__ == '__main__':
    main()
