
import json

def main() -> int:
    print(json.dumps({"ok": True, "patch_id": "4B436662E", "rollback": "Use git checkout or .patch_backup/4B436662E for manual restore."}, sort_keys=True))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
