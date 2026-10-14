#!/usr/bin/env python3
"""Exercise the driver's actual TX DDMI fallback without touching hardware."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[1]
s=(r/'local_packages/pon/airoha-pon-frontends/src/airoha-en7572.c').read_text()
code=s[s.index('static void en7572_apply_tx_ddmi_fallback'):s.index('/* EN7572 reads use')]
pre=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8; typedef uint32_t u32;
#define U32_MAX UINT32_MAX
#define EN7572_BOB_A0_BASE 0
#define EN7572_BOB_A2_BASE 256
#define EN7572_BOB_TSSI_CAL_1 0xb4
#define dev_warn(...) ((void)0)
struct device { int unused; };
struct en7572 { u8 *bob; bool bob_a2_valid, tx_ddmi_a0_fallback; };
static u32 get_unaligned_le32(const u8 *p) {
 return (u32)p[0] | (u32)p[1]<<8 | (u32)p[2]<<16 | (u32)p[3]<<24;
}
'''
main=r'''
int main(void) {
 u8 data[512], saved[512]; struct en7572 en={.bob=data};
 memset(data,255,sizeof(data)); memcpy(saved,data,sizeof(data));
 en7572_apply_tx_ddmi_fallback(0,&en);
 assert(!en.tx_ddmi_a0_fallback && !memcmp(saved,data,sizeof(data)));
 en.bob_a2_valid=true; en7572_apply_tx_ddmi_fallback(0,&en);
 assert(!en.tx_ddmi_a0_fallback && !memcmp(saved,data,sizeof(data)));
 data[256+0xb4]=17; memcpy(saved,data,sizeof(data));
 en.bob_a2_valid=false; en7572_apply_tx_ddmi_fallback(0,&en);
 assert(!en.tx_ddmi_a0_fallback && !memcmp(saved,data,sizeof(data)));
 en.bob_a2_valid=true; en7572_apply_tx_ddmi_fallback(0,&en);
 assert(en.tx_ddmi_a0_fallback && data[0xb4]==17);
 memcpy(saved+0xb4,saved+256+0xb4,4);
 assert(!memcmp(saved,data,sizeof(data)));
 memset(data,255,sizeof(data)); data[0xb4]=23;
 en.tx_ddmi_a0_fallback=false; memcpy(saved,data,sizeof(data));
 en7572_apply_tx_ddmi_fallback(0,&en);
 assert(!en.tx_ddmi_a0_fallback && !memcmp(saved,data,sizeof(data)));
 return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='en7572-test-') as d:
 p=Path(d)/'test.c';out=Path(d)/'test';p.write_text(pre+code+main)
 subprocess.run(['gcc','-std=gnu11','-Wall','-Werror',str(p),'-o',str(out)],check=True)
 subprocess.run([str(out)],check=True)
print('PASS: native TX calibration preserved, invalid sources rejected, valid fallback changes only four bytes')
