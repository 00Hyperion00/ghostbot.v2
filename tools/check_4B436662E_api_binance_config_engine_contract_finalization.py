
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tradebot.full_repo_regression_stabilization_62E import build_phase62e_report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    parser.parse_args(argv)
    report = build_phase62e_report(ROOT)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 2
if __name__ == "__main__":
    raise SystemExit(main())
