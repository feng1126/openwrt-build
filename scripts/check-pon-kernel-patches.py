#!/usr/bin/env python3
"""Apply the complete OpenWrt 6.18 patch series to a fresh, minimal kernel tree."""
import argparse
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile


def check(source, archive, work, log):
    patches = []
    for directory in ('generic/backport', 'generic/pending', 'generic/hack', 'airoha/patches'):
        patches.extend(sorted((source / 'target/linux' / (directory + '-6.18')).glob('*.patch')))
    if not patches:
        raise SystemExit('No kernel patches found')
    paths = set()
    for patch in patches:
        paths.update(re.findall(r'^(?:---|\+\+\+) [ab]/([^\t\n ]+)',
                               patch.read_text(errors='replace'), re.M))
    if any(Path(name).is_absolute() or '..' in Path(name).parts for name in paths):
        raise SystemExit('Unsafe kernel patch path')
    with tarfile.open(archive, 'r:xz') as kernel:
        for member in kernel:
            name = member.name.partition('/')[2]
            if name in paths and member.isfile():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(kernel.extractfile(member).read())
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as output:
        for patch in patches:
            output.write('APPLY ' + str(patch.relative_to(source)) + '\n')
            output.flush()
            result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                     '-p1', '-i', str(patch)], cwd=work,
                                    stdout=output, stderr=subprocess.STDOUT)
            if result.returncode:
                output.flush()
                print(log.read_text()[-6000:])
                raise SystemExit('Kernel patch check failed: ' + patch.name)
    print(f'PASS: {len(patches)} kernel patches applied with fuzz=0; log: {log}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--kernel-tar', type=Path)
    parser.add_argument('--work-dir', type=Path)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    version_file = source / 'target/linux/generic/kernel-6.18'
    match = re.search(r'^LINUX_VERSION-6\.18\s*=\s*(\.\d+)\s*$',
                      version_file.read_text(), re.M)
    if not match:
        raise SystemExit('Unsupported kernel version definition')
    archive = (args.kernel_tar or source / 'dl' / ('linux-6.18' + match[1] + '.tar.xz')).resolve()
    if args.work_dir:
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=False)
        check(source, archive, work, args.log.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='pon-kernel-check-') as directory:
            check(source, archive, Path(directory), args.log.resolve())


if __name__ == '__main__':
    main()
