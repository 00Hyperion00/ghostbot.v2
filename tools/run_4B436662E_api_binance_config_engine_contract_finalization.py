
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tradebot.full_repo_regression_stabilization_62E import build_phase62e_report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_phase62e_report(ROOT)
    out = ROOT / args.reports_dir
    out.mkdir(parents=True, exist_ok=True)
    name = "4B436662E_api_binance_config_engine_contract_finalization_" + ("ready" if report.get("ok") else "blocked") + ".json"
    path = out / name
    report["report_path"] = str(path)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 2
if __name__ == "__main__":
    raise SystemExit(main())
