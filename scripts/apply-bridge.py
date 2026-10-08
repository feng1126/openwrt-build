#!/usr/bin/env python3
"""Install pinned AN7581 bridge flow offload and its correctness fixes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    source = parser.parse_args().source.resolve()
    bundle = Path(__file__).resolve().parents[1] / 'patches/bridge'
    manifest = json.loads((bundle / 'sources.json').read_text())
    if 'KERNEL_PATCHVER:=6.18' not in (source / 'target/linux/airoha/Makefile').read_text():
        raise SystemExit('Bridge port requires the validated Airoha Linux 6.18 base')
    package_patch = bundle / '001-bridge-conntrack-package.patch'
    if hashlib.sha256(package_patch.read_bytes()).hexdigest() != manifest['package_patch_sha256']:
        raise SystemExit('Bridge package patch checksum mismatch')
    command = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(package_patch)]
    subprocess.run(command + ['--dry-run'], cwd=source, check=True)
    for name, expected in manifest['sha256'].items():
        patch = bundle / 'overlay' / name
        if hashlib.sha256(patch.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Bridge bundle checksum mismatch: {name}')
        target = source / name
        if target.exists() and target.read_bytes() != patch.read_bytes():
            raise SystemExit(f'Conflicting bridge overlay: {name}')
    for name in manifest['sha256']:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bundle / 'overlay' / name, target)
    subprocess.run(command, cwd=source, check=True)
    print(f'Bridge offload: {manifest["upstream"]} @ {manifest["commit"]}')


if __name__ == '__main__':
    main()
