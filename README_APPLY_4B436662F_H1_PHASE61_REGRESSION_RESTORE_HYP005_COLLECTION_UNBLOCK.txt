4B.4.3.6.6.62F-H1
Phase61 Regression Restore / HYP005 Collection Unblock Hotfix

Apply:
  python tools/apply_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py

Check:
  python tools/check_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py --once-json

Run:
  python tools/run_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py --reports-dir .\reports\recovery --once-json

Full pytest must pass before commit/tag.
