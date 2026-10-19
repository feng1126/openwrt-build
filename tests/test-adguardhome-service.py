#!/usr/bin/env python3
"""Exercise USB startup safety and fw4 rule generation without a live router."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INIT = ROOT / 'local_packages/luci-app-adguardhome/root/etc/init.d/AdGuardHome'


class AdGuardHomeServiceTest(unittest.TestCase):
    def run_shell(self, body):
        # Only replace the absolute reload command; never touch the host firewall.
        script = INIT.read_text().replace('/etc/init.d/firewall reload', 'firewall_reload')
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / 'service'
            path.write_text(script)
            return subprocess.run(['sh', '-c', '. "$1"\n' + body, 'test', str(path)],
                                  text=True, capture_output=True, check=True).stdout

    def test_missing_disk_stops_before_loading_or_creating_config(self):
        result = self.run_shell('''
grep() { return 1; }
logger() { echo "storage unavailable"; }
config_load() { echo "UNEXPECTED_CONFIG_LOAD"; }
if start_service; then exit 1; fi
''')
        self.assertIn('storage unavailable', result)
        self.assertNotIn('UNEXPECTED_CONFIG_LOAD', result)

    def test_redirect_uses_fw4_for_both_ip_families_and_dns_protocols(self):
        result = self.run_shell('''
uci() { printf '%s\\n' "$*"; }
firewall_reload() { echo RELOAD; }
AdGuardHome_PORT=1745
set_firewall
''')
        for setting in ('target=DNAT', 'src=lan', 'family=any', 'proto=tcp udp',
                        'src_dport=53', 'dest_port=1745'):
            self.assertIn('set firewall.adguardhome_redirect.' + setting, result)
        self.assertIn('commit firewall', result)
        self.assertEqual(result.count('RELOAD'), 1)
        self.assertNotIn('iptables', result)


if __name__ == '__main__':
    unittest.main()
