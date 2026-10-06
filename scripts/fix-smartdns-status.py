#!/usr/bin/env python3
"""Fix LuCI SmartDNS treating the [false] service status as true."""
import re
import sys
from pathlib import Path


def fix(source):
    if not re.search(r'function\s+smartdnsServiceStatus\s*\([^)]*\)\s*\{\s*return\s+Promise\.all\s*\(', source):
        return source
    return re.sub(r'smartdnsRenderStatus\(\s*res\s*\)', 'smartdnsRenderStatus(res[0] === true)', source)


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
        elif re.search(r'smartdnsRenderStatus\(\s*res\s*\)', source) and 'Promise.all([getServiceStatus()])' in source:
            raise SystemExit('Unrecognized SmartDNS status code: ' + str(path))
        else:
            print('No legacy array-status call:', path)

if __name__ == '__main__':
    main()
