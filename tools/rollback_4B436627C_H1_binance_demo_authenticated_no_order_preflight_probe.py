from __future__ import annotations
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; TARGET=ROOT/'src'/'tradebot'/'binance_demo_authenticated_no_order_preflight.py'; BACKUP_DIR=ROOT/'tools'/'_patch_backup_4B436627CH1'; BACKUP=BACKUP_DIR/'src'/'tradebot'/TARGET.name; CREATED=BACKUP_DIR/'.demo_authenticated_probe_created'
def main()->int:
    restored=removed=0
    if BACKUP.exists(): TARGET.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(BACKUP,TARGET); restored=1
    elif CREATED.exists(): TARGET.unlink(missing_ok=True); removed=1
    else: print('4B436627CH1_rollback_error: backup marker missing'); return 2
    print('4B.4.3.6.6.27C-H1 Binance Demo authenticated no-order preflight probe rolled back'); print(f' - restored_files: {restored}'); print(f' - removed_created_files: {removed}'); print(' - config_mutation_performed: False'); print(' - scheduler_mutation_performed: False'); print(' - trading_action_performed: False'); return 0
if __name__=='__main__': raise SystemExit(main())
