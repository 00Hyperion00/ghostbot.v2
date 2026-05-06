from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()
ENGINE = ROOT / 'src' / 'tradebot' / 'engine.py'
OBS_TEST = ROOT / 'tests' / 'test_runtime_observability_event_audit.py'


def _replace_method_body(text: str, method_name: str, transform) -> tuple[str, bool]:
    marker = f"    async def {method_name}"
    start = text.find(marker)
    if start == -1:
        marker = f"    def {method_name}"
        start = text.find(marker)
    if start == -1:
        return text, False
    next_match = re.search(r"\n    (?:async def|def) ", text[start + 1:])
    end = start + 1 + next_match.start() if next_match else len(text)
    original = text[start:end]
    updated = transform(original)
    return text[:start] + updated + text[end:], updated != original


def patch_engine() -> dict[str, object]:
    if not ENGINE.exists():
        raise FileNotFoundError(f'Missing {ENGINE}')
    text = ENGINE.read_text(encoding='utf-8')

    def transform(method: str) -> str:
        updated = method
        # The idempotent-start tests build a partially initialized engine; recovery must not
        # assume symbol_rules has already been attached as an instance attribute.
        if "symbol_rules = getattr(self, 'symbol_rules', None)" not in updated:
            updated = updated.replace(
                '        now = utc_ms()\n',
                "        now = utc_ms()\n        symbol_rules = getattr(self, 'symbol_rules', None)\n",
                1,
            )
        # Keep the change local to the recovery method. Do not globally rewrite engine.py.
        updated = updated.replace('self.symbol_rules.', 'symbol_rules.')
        updated = updated.replace('self.symbol_rules else', 'symbol_rules else')
        updated = updated.replace('self.symbol_rules:', 'symbol_rules:')
        updated = updated.replace('if self.symbol_rules', 'if symbol_rules')
        updated = updated.replace('and self.symbol_rules', 'and symbol_rules')
        return updated

    text, changed = _replace_method_body(text, '_startup_reconcile_persistent_state', transform)
    if not changed:
        raise RuntimeError('Could not patch _startup_reconcile_persistent_state; method not found or unchanged')

    # Defensive validation: method must no longer use raw self.symbol_rules.
    method_start = text.find('    async def _startup_reconcile_persistent_state')
    if method_start == -1:
        method_start = text.find('    def _startup_reconcile_persistent_state')
    method_end_match = re.search(r"\n    (?:async def|def) ", text[method_start + 1:])
    method_end = method_start + 1 + method_end_match.start() if method_end_match else len(text)
    method = text[method_start:method_end]
    if 'self.symbol_rules' in method:
        raise RuntimeError('Unsafe self.symbol_rules access remains inside startup recovery method')
    if "symbol_rules = getattr(self, 'symbol_rules', None)" not in method:
        raise RuntimeError('Safe symbol_rules guard was not inserted')

    ENGINE.write_text(text, encoding='utf-8')
    return {
        'method_found': True,
        'safe_symbol_rules_guard': True,
        'remaining_self_symbol_rules_in_recovery': method.count('self.symbol_rules'),
    }


def patch_observability_tests() -> dict[str, object]:
    if not OBS_TEST.exists():
        return {'exists': False, 'version_replacements': 0, 'remaining_11_contract_assertions': 0}
    text = OBS_TEST.read_text(encoding='utf-8')
    before = text.count('4B.4.3.6.6.11')
    text = text.replace('4B.4.3.6.6.11', '4B.4.3.6.6.12')
    OBS_TEST.write_text(text, encoding='utf-8')
    after = text.count('4B.4.3.6.6.11')
    return {
        'exists': True,
        'version_replacements': before,
        'remaining_11_contract_assertions': after,
    }


def main() -> None:
    engine_report = patch_engine()
    obs_report = patch_observability_tests()
    if obs_report.get('remaining_11_contract_assertions'):
        raise RuntimeError('Old 4B.4.3.6.6.11 contract assertions remain in test_runtime_observability_event_audit.py')
    print('4B.4.3.6.6.12a restart recovery compatibility hotfix applied')
    print(f' - engine: {engine_report}')
    print(f' - runtime_observability_tests: {obs_report}')


if __name__ == '__main__':
    main()
