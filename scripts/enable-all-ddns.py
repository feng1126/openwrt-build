#!/usr/bin/env python3
"""Select every real ddns-scripts package from the current feeds metadata."""
import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--metadata", default="tmp/.packageinfo")
    parser.add_argument("--config", default=".config")
    args = parser.parse_args()
    packages = sorted(set(re.findall(
        r"^Package:\s*(ddns-scripts(?:[-_][A-Za-z0-9_.+-]+)?)\s*$",
        Path(args.metadata).read_text(), re.M)))
    required = {"ddns-scripts", "ddns-scripts-cloudflare", "ddns-scripts-services"}
    if not required.issubset(packages):
        raise SystemExit("Missing DDNS package metadata; update/install feeds and run make defconfig first")
    path = Path(args.config)
    lines = path.read_text().splitlines()
    wanted = [f"CONFIG_PACKAGE_{name}=y" for name in packages]
    if args.check:
        missing = sorted(set(wanted) - set(lines))
        if missing:
            raise SystemExit("DDNS packages removed/disabled by defconfig:\n" + "\n".join(missing))
        print(f"Verified all {len(packages)} DDNS packages are built into firmware")
    else:
        pattern = re.compile(r"^(?:# )?CONFIG_PACKAGE_ddns-scripts(?:[-_][A-Za-z0-9_.+-]+)?(?:=| is not set)")
        lines = [line for line in lines if not pattern.match(line)]
        path.write_text("\n".join(lines + wanted) + "\n")
        print(f"Enabled {len(packages)} DDNS packages: " + ", ".join(packages))


if __name__ == "__main__":
    main()
