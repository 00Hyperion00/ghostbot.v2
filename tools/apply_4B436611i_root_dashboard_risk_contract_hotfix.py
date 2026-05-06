from __future__ import annotations

import re
from pathlib import Path

PHASE = '4B.4.3.6.6.11i'
DASHBOARD = Path('src/tradebot/ui/dashboard.py')
ENGINE = Path('src/tradebot/engine.py')


def _read(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f'ERROR: {path} not found. Run this script from the project root.')
    return path.read_text(encoding='utf-8')


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def _normalize_safe_getattr_symbols(text: str) -> tuple[str, int]:
    # Collapse any accidental chain such as safe_obj_safe_obj_getattr or
    # safe_obj_safe_obj_safe_obj_getattr into the one valid function name.
    pattern = re.compile(r'\bsafe_obj_(?:safe_obj_)+getattr\b')
    total = 0
    while True:
        text, count = pattern.subn('safe_obj_getattr', text)
        total += count
        if count == 0:
            return text, total


def patch_dashboard() -> dict[str, object]:
    text = _read(DASHBOARD)
    before_double = len(re.findall(r'\bsafe_obj_(?:safe_obj_)+getattr\b', text))
    text, normalized_double = _normalize_safe_getattr_symbols(text)

    # Root fix: in DashboardApp tests/probes, normal getattr(self, ...) can call
    # tkinter.__getattr__ and recurse through self.tk. Convert every raw literal
    # self getattr to the project-safe object dictionary accessor. Negative
    # lookbehind prevents already-safe safe_obj_getattr(...) from being touched.
    raw_self_pattern = re.compile(r'(?<!safe_obj_)getattr\(self,\s*')
    text, raw_self_converted = raw_self_pattern.subn('safe_obj_getattr(self, ', text)
    text, normalized_after_convert = _normalize_safe_getattr_symbols(text)

    # Dashboard contract text compatibility: risk execution tests expect the
    # partial TP state to be rendered explicitly, not only as part of the
    # composite Partial TP line.
    partial_line_added = 0
    if 'Partial TP done' not in text:
        risk_exec_needle = "        f'Risk exec       : {risk_exec.get(\"status\") or \"-\"} / {risk_exec.get(\"exit_signal\") or \"-\"}',\n"
        partial_line = (
            "        f'Partial TP done : {bool(risk_exec.get(\"partial_tp_done\") "
            "or protective.get(\"partial_tp_triggered\") "
            "or risk_exec.get(\"partial_tp_triggered\"))}',\n"
        )
        if risk_exec_needle in text:
            text = text.replace(risk_exec_needle, partial_line + risk_exec_needle, 1)
            partial_line_added = 1
        else:
            # Fallback for slightly different formatting: insert before the
            # final Risk exit line inside build_position_management_text.
            fallback_needle = "        f'Risk exit       : {risk_exec.get(\"exit_action\") or \"NONE\"} / {risk_exec.get(\"exit_reason\") or protective.get(\"last_exit_reason\") or \"-\"}',\n"
            if fallback_needle in text:
                text = text.replace(fallback_needle, partial_line + fallback_needle, 1)
                partial_line_added = 1

    _write(DASHBOARD, text)

    remaining_double = len(re.findall(r'\bsafe_obj_(?:safe_obj_)+getattr\b', text))
    remaining_raw_self = len(raw_self_pattern.findall(text))
    remaining_btn_getattr = len(re.findall(r"(?<!safe_obj_)getattr\(self,\s*'btn_[^']+'\s*,", text))

    if remaining_double or remaining_raw_self or remaining_btn_getattr:
        samples = re.findall(r"(?<!safe_obj_)getattr\(self,\s*'[^']+'\s*,[^\n]*", text)[:20]
        raise SystemExit(
            'ERROR: dashboard still contains unsafe getattr patterns:\n'
            f' remaining_double={remaining_double}\n'
            f' remaining_raw_self={remaining_raw_self}\n'
            f' remaining_btn_getattr={remaining_btn_getattr}\n'
            f' samples={samples}'
        )
    if 'Partial TP done' not in text:
        raise SystemExit('ERROR: dashboard position text still does not contain Partial TP done')

    return {
        'dashboard.double_safe_getattr_before': before_double,
        'dashboard.double_safe_getattr_replaced': normalized_double + normalized_after_convert,
        'dashboard.raw_self_getattr_converted': raw_self_converted,
        'dashboard.partial_tp_done_line_added': partial_line_added,
        'dashboard.remaining_double_safe_getattr': remaining_double,
        'dashboard.remaining_raw_self_getattr': remaining_raw_self,
        'dashboard.remaining_raw_button_getattr': remaining_btn_getattr,
    }


def patch_engine() -> dict[str, object]:
    text = _read(ENGINE)
    suggested_close_added = 0

    if 'suggested_close_pct' not in text:
        # The risk execution snapshot already exposes suggested_exit_qty.
        # Add a stable alias for tests/dashboard: partial exit uses configured
        # close pct, full exit uses 100, no-exit uses 0.
        pattern = re.compile(r"(?P<indent>\s*)'suggested_exit_qty':\s*requested_exit_qty,\n")

        def repl(match: re.Match[str]) -> str:
            nonlocal suggested_close_added
            suggested_close_added += 1
            indent = match.group('indent')
            return (
                match.group(0)
                + f"{indent}'suggested_close_pct': (float(risk_plan.partial_tp_close_pct or 0.0) "
                "if exit_action == 'PARTIAL_EXIT' else "
                "(100.0 if exit_action == 'FULL_EXIT' else 0.0)),\n"
            )

        text = pattern.sub(repl, text, count=1)
        if suggested_close_added == 0:
            raise SystemExit("ERROR: could not locate suggested_exit_qty in engine risk snapshot")
        _write(ENGINE, text)

    if 'suggested_close_pct' not in text:
        raise SystemExit('ERROR: engine risk snapshot still lacks suggested_close_pct')

    return {
        'engine.suggested_close_pct_added': suggested_close_added,
        'engine.suggested_close_pct_present': True,
    }


def main() -> None:
    results = {}
    results.update(patch_dashboard())
    results.update(patch_engine())
    print(f'{PHASE} root dashboard/risk contract hotfix applied')
    for key, value in results.items():
        print(f' - {key}: {value}')


if __name__ == '__main__':
    main()
