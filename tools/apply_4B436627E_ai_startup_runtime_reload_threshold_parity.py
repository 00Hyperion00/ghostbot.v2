from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "tradebot"
AI = SRC / "ai"
TOOLS = PROJECT_ROOT / "tools"
PAYLOAD = TOOLS / "_patch_payload"
BACKUP = TOOLS / "_patch_backup_4B436627E"
CREATED_MARKER = BACKUP / ".created_files.txt"

CONTRACT_TARGET = AI / "decision_contract.py"
CONTRACT_PAYLOAD = PAYLOAD / "decision_contract_4B436627E.py"
CONFIG = SRC / "config.py"
PROVIDER = AI / "provider.py"
ENGINE = SRC / "engine.py"
API = SRC / "api.py"
SERVICE = AI / "service.py"
CLI = SRC / "cli.py"
MAIN = PROJECT_ROOT / "main.py"
CHECKER = TOOLS / "check_ai_startup_reload_threshold_parity_4B436627E.py"
ROLLBACK = TOOLS / "rollback_4B436627E_ai_startup_runtime_reload_threshold_parity.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_ai_startup_reload_threshold_parity_4B436627E.py"

ACTIVE_FILES = [CONFIG, PROVIDER, ENGINE, API, SERVICE, CLI, MAIN]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _created(path: Path) -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    relative = path.relative_to(PROJECT_ROOT).as_posix()
    current = set(CREATED_MARKER.read_text(encoding="utf-8").splitlines()) if CREATED_MARKER.exists() else set()
    current.add(relative)
    CREATED_MARKER.write_text("\n".join(sorted(item for item in current if item)) + "\n", encoding="utf-8")


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"27E_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:100]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _restore_on_failure() -> None:
    for source in sorted(path for path in BACKUP.rglob("*") if path.is_file() and path != CREATED_MARKER and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}):
        relative = source.relative_to(BACKUP)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if CREATED_MARKER.exists():
        for raw in CREATED_MARKER.read_text(encoding="utf-8").splitlines():
            target = PROJECT_ROOT / raw.strip()
            if raw.strip() and target.exists():
                target.unlink()


def _patch() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in ACTIVE_FILES:
        if not path.exists():
            raise RuntimeError(f"27E_REQUIRED_ACTIVE_FILE_MISSING:{path}")
        _backup(path)
    if not CONTRACT_TARGET.exists():
        CONTRACT_TARGET.parent.mkdir(parents=True, exist_ok=True)
        _created(CONTRACT_TARGET)
    shutil.copy2(CONTRACT_PAYLOAD, CONTRACT_TARGET)

    _replace(CONFIG,
        '    ai_indecision_margin: float = 0.08\n',
        '    ai_indecision_margin: float = 0.08\n    ai_threshold_profile: str = "runtime_settings"\n')

    _replace(PROVIDER,
        'from ..models import Candle, SignalDecision\n',
        'from ..models import Candle, SignalDecision\nfrom .decision_contract import AIDecisionContract, build_decision_contract, decision_contract_from_provider\n')
    _replace(PROVIDER,
        '''    def __init__(self, model_path: str, threshold: float = 0.60) -> None:\n        self.model_path = model_path\n        self.threshold = threshold\n        self.buy_threshold = 0.64\n        self.sell_threshold = 0.57\n        self.hold_band_low = 0.45\n        self.hold_band_high = 0.55\n        self.indecision_margin = 0.08\n''',
        '''    def __init__(\n        self,\n        model_path: str,\n        threshold: float = 0.60,\n        buy_threshold: float = 0.64,\n        sell_threshold: float = 0.57,\n        hold_band_low: float = 0.45,\n        hold_band_high: float = 0.55,\n        indecision_margin: float = 0.08,\n        threshold_profile: str = "runtime_settings",\n    ) -> None:\n        self.model_path = model_path\n        self._apply_decision_contract(build_decision_contract(\n            threshold=threshold,\n            buy_threshold=buy_threshold,\n            sell_threshold=sell_threshold,\n            hold_band_low=hold_band_low,\n            hold_band_high=hold_band_high,\n            indecision_margin=indecision_margin,\n            threshold_profile=threshold_profile,\n        ))\n''')
    _replace(PROVIDER,
        '''    @property\n    def threshold_config(self) -> dict[str, float]:\n''',
        '''    def _apply_decision_contract(self, contract: AIDecisionContract) -> None:\n        validated = contract.validate()\n        self.threshold = float(validated.threshold)\n        self.buy_threshold = float(validated.buy_threshold)\n        self.sell_threshold = float(validated.sell_threshold)\n        self.hold_band_low = float(validated.hold_band_low)\n        self.hold_band_high = float(validated.hold_band_high)\n        self.indecision_margin = float(validated.indecision_margin)\n        self.threshold_profile = str(validated.threshold_profile)\n\n    @property\n    def decision_contract(self) -> AIDecisionContract:\n        return decision_contract_from_provider(self)\n\n    def decision_contract_snapshot(self) -> dict[str, Any]:\n        return self.decision_contract.snapshot()\n\n    @property\n    def threshold_config(self) -> dict[str, float]:\n''')
    _replace(PROVIDER,
        "            'threshold_config': self.threshold_config,\n",
        "            'threshold_config': self.threshold_config,\n            'threshold_profile': self.threshold_profile,\n            'decision_contract': self.decision_contract_snapshot(),\n")
    _replace(PROVIDER,
        '''        indecision_margin: float | None = None,\n    ) -> bool:\n        candidate_path = model_path or self.model_path\n        try:\n            candidate = self._load_candidate(candidate_path)\n''',
        '''        indecision_margin: float | None = None,\n        threshold_profile: str | None = None,\n    ) -> bool:\n        candidate_path = model_path or self.model_path\n        try:\n            candidate_contract = build_decision_contract(\n                threshold=threshold,\n                buy_threshold=buy_threshold,\n                sell_threshold=sell_threshold,\n                hold_band_low=hold_band_low,\n                hold_band_high=hold_band_high,\n                indecision_margin=indecision_margin,\n                threshold_profile=threshold_profile,\n                fallback=self.decision_contract,\n            )\n            candidate = self._load_candidate(candidate_path)\n''')
    _replace(PROVIDER,
        '''        if threshold is not None:\n            self.threshold = float(threshold)\n        if buy_threshold is not None:\n            self.buy_threshold = float(buy_threshold)\n        if sell_threshold is not None:\n            self.sell_threshold = float(sell_threshold)\n        if hold_band_low is not None:\n            self.hold_band_low = float(hold_band_low)\n        if hold_band_high is not None:\n            self.hold_band_high = float(hold_band_high)\n        if indecision_margin is not None:\n            self.indecision_margin = float(indecision_margin)\n        self._commit_candidate(candidate)\n''',
        '''        self._apply_decision_contract(candidate_contract)\n        self._commit_candidate(candidate)\n''')

    _replace(ENGINE,
        'from .ai.provider import XGBoostSignalProvider\n',
        'from .ai.provider import XGBoostSignalProvider\nfrom .ai.decision_contract import decision_contract_from_settings\n')
    _replace(ENGINE,
        "        self.ai_provider = XGBoostSignalProvider(settings.ai_model_path, threshold=settings.ai_confidence_threshold) if settings.ai_provider_enabled and settings.ai_provider_mode == 'local_xgboost' else None\n",
        "        startup_ai_contract = decision_contract_from_settings(settings)\n        self.ai_provider = XGBoostSignalProvider(settings.ai_model_path, **startup_ai_contract.threshold_kwargs()) if settings.ai_provider_enabled and settings.ai_provider_mode == 'local_xgboost' else None\n")

    _replace(API,
        'from .ai.provider import XGBoostSignalProvider\n',
        'from .ai.provider import XGBoostSignalProvider\nfrom .ai.decision_contract import AIDecisionContractError, assert_startup_reload_parity, decision_contract_from_payload, decision_contract_from_settings\n')
    _replace(API,
        '    indecision_margin: float | None = None\n',
        '    indecision_margin: float | None = None\n    threshold_profile: str | None = None\n')
    _replace(API,
        '''def _threshold_payload(settings: Any, payload: AIReloadPayload) -> dict[str, float | None]:\n    return {\n        'threshold': payload.threshold if payload.threshold is not None else getattr(settings, 'ai_confidence_threshold', 0.60),\n        'buy_threshold': payload.buy_threshold if payload.buy_threshold is not None else getattr(settings, 'ai_buy_threshold', 0.64),\n        'sell_threshold': payload.sell_threshold if payload.sell_threshold is not None else getattr(settings, 'ai_sell_threshold', 0.57),\n        'hold_band_low': payload.hold_band_low if payload.hold_band_low is not None else getattr(settings, 'ai_hold_band_low', 0.45),\n        'hold_band_high': payload.hold_band_high if payload.hold_band_high is not None else getattr(settings, 'ai_hold_band_high', 0.55),\n        'indecision_margin': payload.indecision_margin if payload.indecision_margin is not None else getattr(settings, 'ai_indecision_margin', 0.08),\n    }\n''',
        '''def _threshold_payload(settings: Any, payload: AIReloadPayload) -> dict[str, float | str]:\n    startup_contract = decision_contract_from_settings(settings)\n    requested_contract = decision_contract_from_payload(payload, fallback=startup_contract)\n    assert_startup_reload_parity(startup_contract, requested_contract)\n    return startup_contract.threshold_kwargs()\n''')
    _replace(API,
        "            provider = XGBoostSignalProvider(model_path, threshold=float(thresholds['threshold'] or 0.60))\n",
        "            provider = XGBoostSignalProvider(model_path, **thresholds)\n")
    _replace(API,
        "        thresholds = _threshold_payload(engine.settings, payload)\n        _safe_engine_log(engine, 'info', 'AI_RELOAD_REQUESTED', 'AI model reload talebi alındı', {'model_path': payload.model_path})\n",
        "        try:\n            thresholds = _threshold_payload(engine.settings, payload)\n        except AIDecisionContractError as exc:\n            result_payload = {'ok': False, 'reload_ok': False, 'model_path': payload.model_path, 'reason_code': str(exc), 'reload_performed': False}\n            _safe_engine_log(engine, 'warn', 'AI_RELOAD_BLOCKED_DECISION_CONTRACT', 'AI model reload karar kontratı nedeniyle engellendi', result_payload)\n            return result_payload\n        _safe_engine_log(engine, 'info', 'AI_RELOAD_REQUESTED', 'AI model reload talebi alındı', {'model_path': payload.model_path, 'decision_contract_version': '4B.4.3.6.6.27E'})\n")
    _replace(API,
        "            engine.settings.ai_indecision_margin = float(thresholds['indecision_margin'] or 0.08)\n",
        "            engine.settings.ai_indecision_margin = float(thresholds['indecision_margin'] or 0.08)\n            engine.settings.ai_threshold_profile = str(thresholds['threshold_profile'])\n")

    _replace(SERVICE,
        'from .provider import XGBoostSignalProvider\n',
        'from .provider import XGBoostSignalProvider\nfrom .decision_contract import AIDecisionContractError, assert_startup_reload_parity, build_decision_contract, decision_contract_from_payload, decision_contract_from_provider\n')
    _replace(SERVICE,
        '''class ConfigUpdate(BaseModel):\n    threshold: float | None = None\n    model_path: str | None = None\n''',
        '''class ConfigUpdate(BaseModel):\n    threshold: float | None = None\n    buy_threshold: float | None = None\n    sell_threshold: float | None = None\n    hold_band_low: float | None = None\n    hold_band_high: float | None = None\n    indecision_margin: float | None = None\n    threshold_profile: str | None = None\n    model_path: str | None = None\n''')
    _replace(SERVICE,
        '''    async def update_config(config: ConfigUpdate) -> dict:\n        provider.reload(model_path=config.model_path, threshold=config.threshold)\n        payload = {'ok': True, 'model_path': provider.model_path, 'threshold': provider.threshold, 'available': provider.available}\n''',
        '''    async def update_config(config: ConfigUpdate) -> dict:\n        startup_contract = decision_contract_from_provider(provider)\n        try:\n            requested_contract = decision_contract_from_payload(config, fallback=startup_contract)\n            assert_startup_reload_parity(startup_contract, requested_contract)\n        except AIDecisionContractError as exc:\n            raise HTTPException(status_code=409, detail=str(exc)) from exc\n        reload_ok = provider.reload(model_path=config.model_path, **startup_contract.threshold_kwargs())\n        payload = {'ok': bool(reload_ok), 'model_path': provider.model_path, 'threshold': provider.threshold, 'available': provider.available}\n''')
    _replace(SERVICE,
        '''    provider = XGBoostSignalProvider(\n        os.getenv('TRADEBOT_AI_MODEL_PATH', 'models/xgboost_trade_model.json'),\n        threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),\n    )\n''',
        '''    provider = XGBoostSignalProvider(\n        os.getenv('TRADEBOT_AI_MODEL_PATH', 'models/xgboost_trade_model.json'),\n        threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),\n        buy_threshold=float(os.getenv('TRADEBOT_AI_BUY_THRESHOLD', '0.64')),\n        sell_threshold=float(os.getenv('TRADEBOT_AI_SELL_THRESHOLD', '0.57')),\n        hold_band_low=float(os.getenv('TRADEBOT_AI_HOLD_BAND_LOW', '0.45')),\n        hold_band_high=float(os.getenv('TRADEBOT_AI_HOLD_BAND_HIGH', '0.55')),\n        indecision_margin=float(os.getenv('TRADEBOT_AI_INDECISION_MARGIN', '0.08')),\n        threshold_profile=os.getenv('TRADEBOT_AI_THRESHOLD_PROFILE', 'runtime_settings'),\n    )\n''')

    _replace(CLI,
        "    ai_p.add_argument('--threshold', type=float, default=0.60)\n",
        "    ai_p.add_argument('--threshold', type=float, default=0.60)\n    ai_p.add_argument('--buy-threshold', type=float, default=0.64)\n    ai_p.add_argument('--sell-threshold', type=float, default=0.57)\n    ai_p.add_argument('--hold-band-low', type=float, default=0.45)\n    ai_p.add_argument('--hold-band-high', type=float, default=0.55)\n    ai_p.add_argument('--indecision-margin', type=float, default=0.08)\n    ai_p.add_argument('--threshold-profile', default='runtime_settings')\n")
    _replace(CLI,
        "        provider = XGBoostSignalProvider(args.model_path, threshold=args.threshold)\n",
        "        provider = XGBoostSignalProvider(args.model_path, threshold=args.threshold, buy_threshold=args.buy_threshold, sell_threshold=args.sell_threshold, hold_band_low=args.hold_band_low, hold_band_high=args.hold_band_high, indecision_margin=args.indecision_margin, threshold_profile=args.threshold_profile)\n")

    _replace(MAIN,
        "    threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),\n",
        "    threshold=float(os.getenv('TRADEBOT_AI_THRESHOLD', '0.60')),\n    buy_threshold=float(os.getenv('TRADEBOT_AI_BUY_THRESHOLD', '0.64')),\n    sell_threshold=float(os.getenv('TRADEBOT_AI_SELL_THRESHOLD', '0.57')),\n    hold_band_low=float(os.getenv('TRADEBOT_AI_HOLD_BAND_LOW', '0.45')),\n    hold_band_high=float(os.getenv('TRADEBOT_AI_HOLD_BAND_HIGH', '0.55')),\n    indecision_margin=float(os.getenv('TRADEBOT_AI_INDECISION_MARGIN', '0.08')),\n    threshold_profile=os.getenv('TRADEBOT_AI_THRESHOLD_PROFILE', 'runtime_settings'),\n")


def main() -> int:
    required = [CONTRACT_PAYLOAD, CHECKER, ROLLBACK, TEST_FILE, *ACTIVE_FILES]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("27e_apply_error: required file missing")
        for path in missing:
            print(f" - missing: {path}")
        return 2
    try:
        _patch()
    except Exception as exc:
        _restore_on_failure()
        print(f"27e_apply_error: {exc}")
        return 3

    checks = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("training_performed", False),
        ("reload_performed", False),
        ("trading_action_performed", False),
        ("decision_contract_module_py_compile_ok", _compile(CONTRACT_TARGET)),
        ("provider_py_compile_ok", _compile(PROVIDER)),
        ("engine_py_compile_ok", _compile(ENGINE)),
        ("api_py_compile_ok", _compile(API)),
        ("service_py_compile_ok", _compile(SERVICE)),
        ("cli_py_compile_ok", _compile(CLI)),
        ("main_py_compile_ok", _compile(MAIN)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("decision_contract_version_present", 'AI_DECISION_CONTRACT_VERSION = "4B.4.3.6.6.27E"' in CONTRACT_TARGET.read_text(encoding="utf-8")),
        ("startup_full_contract_wired", "startup_ai_contract = decision_contract_from_settings(settings)" in ENGINE.read_text(encoding="utf-8")),
        ("runtime_reload_parity_gate_present", "assert_startup_reload_parity(startup_contract, requested_contract)" in API.read_text(encoding="utf-8")),
        ("standalone_service_parity_gate_present", "assert_startup_reload_parity(startup_contract, requested_contract)" in SERVICE.read_text(encoding="utf-8")),
        ("provider_contract_snapshot_present", "decision_contract_snapshot" in PROVIDER.read_text(encoding="utf-8")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27E AI startup / runtime reload threshold parity / decision contract consistency hardening applied")
    ok = True
    false_expected = {"config_mutation_performed", "scheduler_mutation_performed", "training_performed", "reload_performed", "trading_action_performed", "paper_live_order_enablement_present"}
    for name, value in checks:
        print(f" - {name}: {value}")
        ok = ok and ((value is False) if name in false_expected else bool(value))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
