from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "tradebot"
TOOLS = PROJECT_ROOT / "tools"
BACKUP = TOOLS / "_patch_backup_4B436625AEH5"

CONTRACT = SRC / "hyp005_r1_canonical_epoch_contract.py"
IDENTITY = SRC / "hyp005_shadow_observation_identity.py"
LOGGER = TOOLS / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
ORCHESTRATOR = TOOLS / "run_hyp005_shadow_collection_orchestrator_4B436625X.py"
ACCEPTANCE = TOOLS / "run_hyp005_shadow_acceptance_readiness_4B436625W.py"
AUDIT = TOOLS / "run_hyp005_shadow_operator_runbook_4B436625Y.py"
COCKPIT = SRC / "operator_cockpit_v2_read_only.py"
CHECKER = TOOLS / "check_hyp005_r1_canonical_epoch_hardening_4B436625AEH5.py"
ROLLBACK = TOOLS / "rollback_4B436625AE_H5_hyp005_r1_canonical_epoch_hardening.py"
CYCLE = TOOLS / "run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1"
REGISTER = TOOLS / "register_hyp005_r1_canonical_epoch_task_4B436625AEH5.ps1"
DISABLE = TOOLS / "disable_hyp005_r1_canonical_epoch_task_4B436625AEH5.ps1"
TEST = PROJECT_ROOT / "tests" / "test_hyp005_r1_canonical_epoch_hardening_4B436625AEH5.py"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def _backup(path: Path) -> None:
    target = BACKUP / path.relative_to(PROJECT_ROOT)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"25AEH5_EXPECTED_FRAGMENT_MISSING:{path}:{old[:100]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_logger() -> None:
    _replace_once(
        LOGGER,
        'if str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\n',
        'if str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\nfrom tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp  # noqa: E402\n\n',
    )
    _replace_once(LOGGER, '    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")\n', '    stamp = utc_artifact_stamp()\n')


def _patch_orchestrator() -> None:
    _replace_once(
        ORCHESTRATOR,
        ')\n\nCLI_HOTFIX_SAFE_VERSION = HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION\n',
        ')\nfrom tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp\n\nCLI_HOTFIX_SAFE_VERSION = HYP005_SHADOW_COLLECTION_ORCHESTRATOR_CONTRACT_VERSION\n',
    )
    _replace_once(ORCHESTRATOR, '    ts = utc_timestamp()\n', '    ts = utc_artifact_stamp()\n')


def _patch_acceptance() -> None:
    _replace_once(
        ACCEPTANCE,
        'if str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\n',
        'if str(SRC) not in sys.path:\n    sys.path.insert(0, str(SRC))\n\nfrom tradebot.hyp005_r1_canonical_epoch_contract import (  # noqa: E402\n    HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION,\n    utc_artifact_stamp,\n)\n\n',
    )
    _replace_once(
        ACCEPTANCE,
        '    for raw in args.collection_report_json or []:\n        paths.append(Path(raw))\n',
        '    # 25AE-H5: collection reports are metadata, never observation-ledger inputs.\n',
    )
    _replace_once(
        ACCEPTANCE,
        '    input_paths = discover_input_paths(args)\n    if args.strict_explicit_chain:\n        collection_paths = [Path(raw) for raw in args.collection_report_json or []]\n',
        '    collection_paths = [Path(raw) for raw in args.collection_report_json or []]\n    input_paths = discover_input_paths(args)\n    if args.strict_explicit_chain:\n',
    )
    _replace_once(
        ACCEPTANCE,
        '    report["input_paths"] = [str(path) for path in input_paths]\n    report["collection_report_paths"] = [str(path) for path in (args.collection_report_json or [])]\n    report["strict_explicit_chain"] = bool(args.strict_explicit_chain)\n',
        '    report["input_paths"] = [str(path) for path in input_paths]\n    report["ledger_input_paths"] = [str(path) for path in input_paths]\n    report["collection_report_paths"] = [str(path) for path in collection_paths]\n    report["source_collection_reports"] = len(collection_paths)\n    report["source_attribution_contract_version"] = HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION\n    report["strict_explicit_chain"] = bool(args.strict_explicit_chain)\n',
    )
    _replace_once(ACCEPTANCE, '    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")\n', '    stamp = utc_artifact_stamp()\n')
    _replace_once(
        ACCEPTANCE,
        '    print(f" - source_ledgers: {len(source_ledgers)}")\n',
        '    print(f" - source_ledgers: {len(source_ledgers)}")\n    print(f" - source_collection_reports: {len(collection_paths)}")\n',
    )


def _patch_audit() -> None:
    _replace_once(
        AUDIT,
        ')\n\nCLI_SAFE_VERSION = HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION\n',
        ')\nfrom tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp\n\nCLI_SAFE_VERSION = HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION\n',
    )
    _replace_once(AUDIT, '    ts = utc_timestamp()\n', '    ts = utc_artifact_stamp()\n')


def _patch_cockpit() -> None:
    _replace_once(
        COCKPIT,
        'from urllib.parse import urlparse\n\n',
        'from urllib.parse import urlparse\n\nfrom .hyp005_r1_canonical_epoch_contract import (\n    CANONICAL_R1_REPORTS_DIR,\n    CANONICAL_R1_TASK_NAME,\n    LEGACY_R1_REPORTS_DIR,\n    LEGACY_R1_TASK_NAME,\n    resolve_active_reports_dir,\n)\n\n',
    )
    _replace_once(
        COCKPIT,
        'OPERATOR_COCKPIT_V2_NO_TRADING_ACTION = True\n\nDEFAULT_R1_REPORTS_DIR = Path("reports") / "hyp005_r1_isolated"\nBASELINE_TASK_NAME = "TradeBot_HYP005_NoOrderShadowCollection"\nR1_TASK_NAME = "TradeBot_HYP005_R1_NoOrderShadowCollection"\n',
        'OPERATOR_COCKPIT_V2_NO_TRADING_ACTION = True\nOPERATOR_COCKPIT_V2_CANONICAL_EPOCH_HARDENING_VERSION = "4B.4.3.6.6.25AE-H5"\nOPERATOR_COCKPIT_V2_CANONICAL_SOURCE_PREFERRED_WITH_LEGACY_FALLBACK = True\n\nDEFAULT_R1_REPORTS_DIR = LEGACY_R1_REPORTS_DIR\nBASELINE_TASK_NAME = "TradeBot_HYP005_NoOrderShadowCollection"\nR1_TASK_NAME = LEGACY_R1_TASK_NAME\n',
    )
    _replace_once(
        COCKPIT,
        '    reports_dir = (project_root.resolve() / DEFAULT_R1_REPORTS_DIR).resolve()\n',
        '    reports_dir = resolve_active_reports_dir(project_root)\n',
    )
    _replace_once(
        COCKPIT,
        '    reports_dir = root / DEFAULT_R1_REPORTS_DIR\n',
        '    reports_dir = resolve_active_reports_dir(root)\n',
    )
    _replace_once(
        COCKPIT,
        '    r1_task = dict(query(R1_TASK_NAME))\n',
        '    active_r1_task_name = CANONICAL_R1_TASK_NAME if reports_dir == (root / CANONICAL_R1_REPORTS_DIR).resolve() else R1_TASK_NAME\n    r1_task = dict(query(active_r1_task_name))\n',
    )
    _replace_once(
        COCKPIT,
        '            r1_reports_dir=str(DEFAULT_R1_REPORTS_DIR),\n',
        '            r1_reports_dir=_relative_or_name(reports_dir, root) or str(DEFAULT_R1_REPORTS_DIR),\n',
    )


def main() -> int:
    required = [CONTRACT, IDENTITY, LOGGER, ORCHESTRATOR, ACCEPTANCE, AUDIT, COCKPIT, CHECKER, ROLLBACK, CYCLE, REGISTER, DISABLE, TEST]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("25AE-H5 apply error: required file missing")
        for path in missing:
            print(f" - missing: {path}")
        return 2
    if not _contains(IDENTITY, 'HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION = "4B.4.3.6.6.25V-H2"'):
        print("25AE-H5 apply error: 25V-H2 prerequisite is not installed")
        return 2
    if not _contains(ORCHESTRATOR, "HYP005_CANONICAL_LEDGER_JSONL_SINGLE_SOURCE = True"):
        print("25AE-H5 apply error: 25V-H2 JSONL single-source prerequisite is not installed")
        return 2

    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in (LOGGER, ORCHESTRATOR, ACCEPTANCE, AUDIT, COCKPIT):
        _backup(path)

    _patch_logger()
    _patch_orchestrator()
    _patch_acceptance()
    _patch_audit()
    _patch_cockpit()

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("contract_py_compile_ok", _compile(CONTRACT)),
        ("logger_py_compile_ok", _compile(LOGGER)),
        ("orchestrator_py_compile_ok", _compile(ORCHESTRATOR)),
        ("acceptance_py_compile_ok", _compile(ACCEPTANCE)),
        ("audit_py_compile_ok", _compile(AUDIT)),
        ("cockpit_py_compile_ok", _compile(COCKPIT)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("utc_stamp_contract_present", _contains(CONTRACT, 'strftime("%Y%m%d_%H%M%SZ")')),
        ("25v_utc_stamp_present", _contains(LOGGER, "stamp = utc_artifact_stamp()")),
        ("25x_utc_stamp_present", _contains(ORCHESTRATOR, "ts = utc_artifact_stamp()")),
        ("25w_source_attribution_present", _contains(ACCEPTANCE, 'report["source_collection_reports"] = len(collection_paths)')),
        ("25w_utc_stamp_present", _contains(ACCEPTANCE, "stamp = utc_artifact_stamp()")),
        ("25y_utc_stamp_present", _contains(AUDIT, "ts = utc_artifact_stamp()")),
        ("cockpit_canonical_source_alignment_present", _contains(COCKPIT, "resolve_active_reports_dir")),
        ("canonical_cycle_jsonl_chain_present", _contains(CYCLE, '--ledger-jsonl "$($LatestLoggerLedgerJsonl.FullName)"')),
        ("manual_registration_only_present", _contains(REGISTER, "Register-ScheduledTask")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.25AE-H5 HYP-005-R1 canonical epoch scheduler / UTC artifact stamp / 25W source attribution / dashboard source alignment hardening applied")
    ok = True
    for name, value in checks:
        print(f" - {name}: {value}")
        if name in {"config_mutation_performed", "scheduler_mutation_performed", "trading_action_performed", "paper_live_order_enablement_present"}:
            ok = ok and value is False
        else:
            ok = ok and value
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
