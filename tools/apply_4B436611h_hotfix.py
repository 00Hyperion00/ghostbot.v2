from __future__ import annotations

import re
from pathlib import Path

DASHBOARD = Path('src/tradebot/ui/dashboard.py')

if not DASHBOARD.exists():
    raise SystemExit(f'ERROR: {DASHBOARD} not found. Run this script from the project root.')

text = DASHBOARD.read_text(encoding='utf-8')

# 1) Normalize prior accidental double prefix typos first.
double_before = text.count('safe_obj_safe_obj_getattr')
while 'safe_obj_safe_obj_getattr' in text:
    text = text.replace('safe_obj_safe_obj_getattr', 'safe_obj_getattr')

# 2) Convert any remaining raw Tk button getattr calls. The negative lookbehind avoids
#    touching already-safe safe_obj_getattr(...) calls.
button_pattern = re.compile(r"(?<!safe_obj_)getattr\(self,\s*'(?P<name>btn_[^']+)'\s*,\s*None\)")
button_names: list[str] = []

def _replace_button_getattr(match: re.Match[str]) -> str:
    name = match.group('name')
    button_names.append(name)
    return f"safe_obj_getattr(self, '{name}', None)"

text = button_pattern.sub(_replace_button_getattr, text)

# 3) Extra direct safeguard for the observed failing line.
safe_mode_before = text.count("getattr(self, 'btn_safe_mode_toggle', None)")
text = text.replace(
    "getattr(self, 'btn_safe_mode_toggle', None)",
    "safe_obj_getattr(self, 'btn_safe_mode_toggle', None)",
)

DASHBOARD.write_text(text, encoding='utf-8')

remaining_double = text.count('safe_obj_safe_obj_getattr')
remaining_raw_button = len(button_pattern.findall(text))
remaining_safe_mode = text.count("getattr(self, 'btn_safe_mode_toggle', None)")

print('4B.4.3.6.6.11h hotfix applied')
print(f' - dashboard.double_safe_getattr_replaced: {double_before}')
print(f' - dashboard.raw_button_getattr_converted: {",".join(sorted(set(button_names))) or "-"}')
print(f' - dashboard.direct_safe_mode_getattr_replaced: {safe_mode_before}')
print(f' - dashboard.remaining_double_safe_getattr: {remaining_double}')
print(f' - dashboard.remaining_raw_button_getattr: {remaining_raw_button}')
print(f' - dashboard.remaining_btn_safe_mode_toggle_getattr: {remaining_safe_mode}')

if remaining_double or remaining_raw_button or remaining_safe_mode:
    raise SystemExit('ERROR: dashboard still contains unsafe/double getattr patterns')
