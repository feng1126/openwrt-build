#!/usr/bin/env python3
"""Integrate pinned Airoha PON drivers/userspace into official OpenWrt 6.18."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / 'patches/pon'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    source = parser.parse_args().source.resolve()
    manifest = json.loads((BUNDLE / 'sources.json').read_text())
    for name, expected in manifest['sha256'].items():
        if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f'PON bundle checksum mismatch: {name}')
    if 'KERNEL_PATCHVER:=6.18' not in (source / 'target/linux/airoha/Makefile').read_text():
        raise SystemExit('PON port requires Airoha Linux 6.18; review this source branch')
    # Validate all replacements before changing the tree. Fail on upstream drift.
    for name, expected in manifest['overlay_base_sha256'].items():
        target = source / name
        actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        if actual != expected:
            raise SystemExit(f'PON overlay base changed: {name}; rebase the port first')
    patch = BUNDLE / '001-xg040gmd-pon-board.patch'
    command = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(patch)]
    subprocess.run(command + ['--dry-run'], cwd=source, check=True)
    packages = source / 'package/custom/pon'
    if packages.exists():
        raise SystemExit(f'PON packages already installed: {packages}')
    subprocess.run(command, cwd=source, check=True)
    for name in manifest['overlay_base_sha256']:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BUNDLE / 'overlay' / name, target)
    shutil.copytree(REPO / 'local_packages/pon', packages)
    for name, upstream in manifest['upstream'].items():
        label = 'openwrt PON reference base' if name == 'openwrt' else name
        print(f'{label}: {upstream["url"]} @ {upstream["commit"]}')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    print(f'Actual OpenWrt build source: {actual}')
    print('PON port installed for Nokia XG-040G-MD UBI. Configure the line in LuCI.')


if __name__ == '__main__':
    main()
