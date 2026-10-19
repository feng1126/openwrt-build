"""Compile and execute the patched status switch against old/new ucode enums."""
from pathlib import Path
import subprocess
import tempfile

patch = Path(__file__).resolve().parents[1] / 'patches/uhttpd/950-handle-unknown-ucode-status.patch'
# Reconstruct the affected original context and exercise the actual patch.
lines = patch.read_text().splitlines(True)
context = ''.join(line[1:] for line in lines if line[:1] in (' ', '-') and not line.startswith('---'))
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / 'ucode.c'
    source.write_text(context)
    subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=root, check=True)
    body = source.read_text().split('\n\t}', 1)[0] + '\n\t}\n'
    for extra in ('', 'STATUS_BREAK,'):
        program = '''#include <stdio.h>
#include <stdlib.h>
typedef enum { STATUS_OK, STATUS_EXIT, %s ERROR_COMPILE, ERROR_RUNTIME } state;
int main(int argc, char **argv) {
state status = (state)atoi(argv[1]); int exitcode = 0;
switch (status) {
case STATUS_OK: break;
case STATUS_EXIT: exit(exitcode ? exitcode : 1);
case ERROR_COMPILE: exit(1);
%s
return 0;
}
''' % (extra, body)
        (root / 'test.c').write_text(program)
        subprocess.run(['cc', '-Wall', '-Werror=switch', str(root / 'test.c'), '-o', str(root / 'test')], check=True)
        assert subprocess.run([str(root / 'test'), '0']).returncode == 0
        assert subprocess.run([str(root / 'test'), '99'], stderr=subprocess.DEVNULL).returncode == 2
        if extra:
            assert subprocess.run([str(root / 'test'), '2'], stderr=subprocess.DEVNULL).returncode == 2
print('PASS: old/new enums compile; unknown and break statuses fail safely')

# A future upstream fix must retire our fallback instead of causing a patch failure.
import runpy
helper = runpy.run_path(str(patch.parents[2] / 'scripts/fix-uhttpd-ucode-status.py'))
old_source = 'switch (status) {\ncase STATUS_OK: break;\n' + context
new_source = 'switch (status) {\ncase STATUS_OK:\ndefault: break;\n}\n'
assert helper['needs_patch'](old_source)
assert not helper['needs_patch'](new_source)
with tempfile.TemporaryDirectory() as directory:
    tree = Path(directory)
    helper['install'](tree, old_source)
    output = tree / 'package/network/services/uhttpd/patches' / patch.name
    assert output.exists()
    helper['install'](tree, new_source)
    assert not output.exists()
print('PASS: upstream fix detection and stale patch removal')
