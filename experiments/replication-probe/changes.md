# changes.md — experiments/replication-probe/

NOT A LANE — hand-authored speed-experiment baseline (see REPORT.md banner).
No source code, prompts, or pipeline files were touched. Writes confined to this folder.

## 2026-07-03

- Created `tokens.css` + `replica.html`: one-shot hand-authored replica of the remote.com
  homepage top (banner, nav, hero, logo strip, accordion, infra split, CTA band, workflow
  cards) under a hard ~5-minute budget. Actual replication window: 17:28:01–17:31:14 WEST
  (3m13s). One sanity screenshot + one small fix (hero gradient stop) inside the window.
- Converted the ground-truth webp to `gt-full.png` + 3 study slices (setup phase artifact).
- Shot the replica with the repo Playwright env (pattern from `experiments/hubspot-validation/shoot.py`;
  needed `PLAYWRIGHT_BROWSERS_PATH` unset under the agent sandbox): `shots/replica-full.png`,
  `shots/replica-viewport.png`, `shots/sanity.png`, small variants, `shots/side-by-side.png`.
- Judging (post-clock): spot-checked saved CSS in `screenshots/remote/*_files/` (read-only rg)
  and diffed guessed tokens against the measured `runs/remote/brand/brand.yaml` (present by
  judging time; read-only). Verdict + classification table in `REPORT.md`.
- Verification: `rg` spot-checks over saved module/template CSS; visual side-by-side composite.
- Follow-up: none planned — this folder is a frozen baseline for the speed-vs-fidelity comparison.
