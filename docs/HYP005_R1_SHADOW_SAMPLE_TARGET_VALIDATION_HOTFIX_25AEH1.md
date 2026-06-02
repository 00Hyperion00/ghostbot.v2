# 4B.4.3.6.6.25AE-H1 — HYP-005-R1 Shadow Sample Target Validation / Scheduler Pack Generation Hotfix

## Purpose

This hotfix repairs the 25AE scheduler pack validator for real 25AD planning reports.

25AD stores the authoritative `shadow_sample_target` under `refined_candidate_spec.shadow_sample_target`. The original 25AE validator checked only the optional top-level field. A valid R1 plan therefore printed `shadow_sample_target: 30` but incorrectly returned `R1_SHADOW_SAMPLE_TARGET_NOT_30` and did not generate a scheduler pack directory.

## Fix

- Resolve the authoritative target from `refined_candidate_spec.shadow_sample_target` first.
- Keep backward compatibility with top-level `shadow_sample_target` and `limits.revalidation_sample_target`.
- Normalize JSON scalar forms such as `30` and `"30"` safely.
- Reject invalid, missing, lossy, or non-numeric values.
- Preserve the baseline-task-disabled guard.
- Preserve fresh namespace isolation: `HYP005_R1`.
- Preserve the eight-symbol refined set.
- Preserve manual Windows Task Scheduler registration.

## Safety

Paper/live remain blocked. Training, model reload, POST requests, order actions, automatic Windows task mutation, legacy baseline observation reuse, and automatic scheduler registration remain prohibited.
