# 4B.4.3.6.6.25K-H1 Walk-Forward DataFrame Split Hotfix

This hotfix repairs the 25K HYP-003 robustness/walk-forward gate.

## Problem

In some Python/numpy/pandas environments, `np.array_split()` applied directly to a pandas `DataFrame` returns `numpy.ndarray` chunks. The 25K code expected each chunk to be a DataFrame and called `.empty`, causing:

```text
AttributeError: 'numpy.ndarray' object has no attribute 'empty'
```

## Fix

- Add `_ensure_edges_dataframe()` defensive conversion.
- Add `_split_dataframe()` that splits DataFrame row positions and uses `.iloc` to preserve DataFrame chunks.
- Update `split_walk_forward()` and `recent_window_segments()` to use DataFrame-safe splitting.
- Keep all training/paper/live/reload/order guardrails unchanged.

## Validation

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"

python -m pytest -q `
tests/test_hyp003_robustness_walkforward_hotfix_25KH1.py `
tests/test_hyp003_robustness_walkforward_4B436625K.py
```

Expected:

```text
8 passed
```

Paper/live remain blocked.
