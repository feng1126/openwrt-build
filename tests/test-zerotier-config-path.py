#!/usr/bin/env python3
"""Exercise the startup guard without modifying the host's /etc directory."""
import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fix', ROOT / 'scripts/fix-zerotier-config-path.py')
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

INIT = '''start_service() {
    [ "$enabled" = 1 ] || return 0
    if [ -n "${config_path}" ]; then
GUARD
        if [ "$copy_config_path" = 1 ]; then
            cp -r "$config_path" "$runtime"
        else
            ln -s "$config_path" "$runtime"
        fi
    fi
    mkdir -p "$runtime/networks.d"
    printf '%s' "$secret" > "$runtime/identity.secret"
}
start_service
'''.replace('GUARD', fix.OLD)


class StartupTests(unittest.TestCase):
    def run_start(self, root, path, copy='1', enabled='1'):
        text = fix.patch(INIT).replace('/etc/*)', f'"{root}/etc/"*)')
        env = {**os.environ, 'config_path': str(path), 'runtime': str(root / 'runtime'),
               'copy_config_path': copy, 'enabled': enabled, 'secret': 'existing-test-identity'}
        return subprocess.run(['sh'], input=text, text=True, env=env, capture_output=True)

    def test_missing_etc_directory_copy_and_link(self):
        for copy in ('0', '1'):
            with self.subTest(copy=copy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / 'etc/zerotier state'
                result = self.run_start(root, path, copy)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
                self.assertEqual((root / 'runtime/identity.secret').read_text(), 'existing-test-identity')

    def test_existing_custom_state_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'mnt/zerotier'
            path.mkdir(parents=True)
            (path / 'moon.json').write_text('existing-controller-config')
            self.assertEqual(self.run_start(root, path).returncode, 0)
            self.assertEqual((path / 'moon.json').read_text(), 'existing-controller-config')
            self.assertEqual((root / 'runtime/moon.json').read_text(), 'existing-controller-config')

    def test_missing_external_mount_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'mnt/zerotier'
            self.assertNotEqual(self.run_start(root, path).returncode, 0)
            self.assertFalse(path.exists())

    def test_disabled_service_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'etc/zerotier'
            self.assertEqual(self.run_start(root, path, enabled='0').returncode, 0)
            self.assertFalse(path.exists())

    def test_empty_config_path_uses_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.run_start(root, '').returncode, 0)
            self.assertTrue((root / 'runtime/identity.secret').exists())

    def test_idempotence_and_upstream_drift(self):
        self.assertEqual(fix.patch(fix.patch(INIT)), fix.patch(INIT))
        with self.assertRaises(ValueError):
            fix.patch('different upstream implementation')


if __name__ == '__main__':
    unittest.main()
