# 4B.4.3.6.6.37K — Promotion Gate Isolation

This patch declares the promotion-governance baseline for P0-10.

It separates:
- shadow observation
- paper candidate
- live-real candidate
- exchange submit

Rules:
- no phase can auto-promote to another phase
- shadow-to-paper requires explicit approval
- paper-to-live requires explicit approval
- live-to-submit requires explicit approval
- all P0 gaps closed does not imply paper/live/submit approval
- no runtime promotion state is mutated by this patch

Safety:
- no order submit
- no network request
- no paper/live unlock
- no runtime overlay
- no phase transition
- no destructive report cleanup
