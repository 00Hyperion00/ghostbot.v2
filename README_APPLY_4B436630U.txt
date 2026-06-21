4B.4.3.6.6.30U Paper Promotion Review

Scope:
- Consume 30T paper soak evidence window.
- Produce promotion readiness review evidence.
- Verify risk acceptance gates.
- Keep exchange submit blocked.
- Keep live-real blocked.

Apply:
cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2

Expand-Archive `
  -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630U_paper_promotion_review_patch.zip" `
  -DestinationPath . `
  -Force

python tools/apply_4B436630U_paper_promotion_review.py

Check:
$env:PYTHONPATH="src"
python tools/check_4B436630U_paper_promotion_review.py `
  --once-json
python tools/check_4B436630T_paper_soak_evidence_window.py `
  --once-json

Test:
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
$env:PYTHONPATH="src"
python -m pytest -q `
  tests/test_paper_promotion_review_4B436630U.py

python -m compileall -q `
  -x '(_patch_backup|_patch_payload|legacy_patches)' `
  src tools tests

Evidence:
$env:PYTHONPATH="src"
python tools/run_4B436630U_paper_promotion_review.py `
  --reports-dir .\reports\production_hardening

Expected decision:
PAPER_PROMOTION_REVIEW_READY_RISK_ACCEPTANCE_GATES_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL

Commit:
git status --short
git add -A
git commit -m "4B.4.3.6.6.30U paper promotion review"
git tag -a 4B.4.3.6.6.30U `
  -m "Accepted paper promotion review"
git push origin main
git push origin 4B.4.3.6.6.30U

Risk note:
30U is not live-real. It does not submit orders. It only produces promotion review evidence and keeps exchange submit/live-real blocked.
