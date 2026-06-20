4B.4.3.6.6.30D-H2 Operator Approval Evidence Repo Hygiene Hotfix

Apply:
  cd C:\Users\muhas\OneDrive\Masaüstü\trade_botV2
  Expand-Archive -Path "$env:USERPROFILE\Downloads\trade_botV2_4B436630D_H2_operator_approval_evidence_repo_hygiene_hotfix_patch.zip" -DestinationPath . -Force
  python tools/apply_4B436630D_H2_operator_approval_evidence_repo_hygiene.py

Verify:
  $env:PYTHONPATH="src"
  python tools/check_4B436630D_H2_operator_approval_evidence_repo_hygiene.py --once-json
  python tools/check_4B436630D_operator_approval_evidence_capture.py --once-json
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"
  python -m pytest -q tests/test_paper_transition_approval_evidence_capture_4B436630D.py tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py tests/test_paper_transition_approval_evidence_capture_4B436630D_H2.py
  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests

Run evidence reports after H2:
  $env:PYTHONPATH="src"
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening
  python tools/run_4B436630D_operator_approval_evidence_capture.py --reports-dir .\reports\production_hardening --operator-id operator-30d --confirmation-token CONFIRM_PAPER_TRANSITION_CANDIDATE --freeze-token FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE --issue-approval --freeze-runtime-envelope --verify-final-risk-cap

Expected report names include decision suffixes:
  *_input_required.json
  *_ready.json

Commit:
  git status --short
  git add -A
  git commit -m "4B.4.3.6.6.30D-H2 operator approval evidence repo hygiene hotfix"
  git tag -a 4B.4.3.6.6.30D-H2 -m "Accepted operator approval evidence repo hygiene hotfix"
  git push origin main
  git push origin 4B.4.3.6.6.30D-H2

This patch does not enable paper orders, runtime overlays, training/reload, or live-real.
