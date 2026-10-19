#!/usr/bin/env python3
"""Create missing /etc ZeroTier state directories at service startup."""
import argparse
from pathlib import Path
import subprocess

OLD = '''\t\tif [ ! -d "${config_path}" ]; then
\t\t\techo "ZeroTier config_path does not exist: ${config_path}" 1>&2
\t\t\treturn
\t\tfi'''

NEW = '''\t\tif [ ! -d "${config_path}" ]; then
\t\t\t# Create persistent /etc state on every start, not just first boot.
\t\t\tcase "${config_path}" in
\t\t\t\t/etc/*)
\t\t\t\t\tmkdir -p "${config_path}" || return 1
\t\t\t\t\tchmod 700 "${config_path}" || return 1
\t\t\t\t\t;;
\t\t\t\t*)
\t\t\t\t\techo "ZeroTier config_path does not exist: ${config_path}" 1>&2
\t\t\t\t\treturn 1
\t\t\t\t\t;;
\t\t\tesac
\t\tfi'''


def patch(text):
    if text.count(NEW) == 1:
        return text
    if text.count(OLD) != 1:
        raise ValueError('ZeroTier startup guard changed upstream; review before building')
    return text.replace(OLD, NEW)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    package = args.source / 'feeds/packages/net/zerotier'
    candidates = [package / 'files/etc/init.d/zerotier', package / 'files/zerotier.init']
    matches = [path for path in candidates if path.is_file()]
    if len(matches) != 1:
        raise SystemExit('Expected one ZeroTier init script in installed packages feed')
    path = matches[0]
    try:
        result = patch(path.read_text())
    except ValueError as error:
        raise SystemExit(str(error)) from error
    subprocess.run(['sh', '-n'], input=result, text=True, check=True)
    path.write_text(result)
    print(f'ZeroTier startup directory fix applied: {path}')


if __name__ == '__main__':
    main()
