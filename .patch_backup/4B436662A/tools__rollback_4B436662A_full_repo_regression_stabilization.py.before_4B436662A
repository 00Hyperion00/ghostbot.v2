
from __future__ import annotations
import json, shutil
from pathlib import Path
PATCH_ID='4B436662A'; ROOT=Path(__file__).resolve().parents[1]; BACKUP=ROOT/'.patch_backup'/PATCH_ID
def main():
    restored=[]
    if BACKUP.exists():
        for b in BACKUP.glob(f'*.before_{PATCH_ID}'):
            rel=b.name.replace(f'.before_{PATCH_ID}','').replace('__','/'); t=ROOT/rel; t.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(b,t); restored.append(rel)
    print(json.dumps({'patch_id':PATCH_ID,'restored':restored,'ok':True},ensure_ascii=False)); return 0
if __name__=='__main__': raise SystemExit(main())
