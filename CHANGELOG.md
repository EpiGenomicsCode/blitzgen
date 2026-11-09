# Changelog

BlitzGen versions are independent of upstream BoltzGen's. The upstream base is
recorded in `FORK.md` and tagged `upstream-base`.

## 0.1.0 — unreleased

First published version. Forked from BoltzGen `a3149cf` (2026-05-28, upstream
0.3.2). **0.x on purpose — see `ROADMAP.md`.**

The folding arm, seeding and sampler work below predate this release; they were
developed in an unversioned working tree through 2026 and are committed here as
a single reviewable change on top of the upstream base.

### Folding
- Blitz K16 (16-step deterministic distilled Boltz-2 student) is the default
  `folding` artifact, located via `$BLITZGEN_FOLDING_CKPT` rather than a baked
  absolute path.
- `--folding_config` selects the folding recipe, defaulting K16 → K8 → stock.
  Default checkpoint and default recipe move together: K16 weights on the K8
  schedule mis-sample silently.
- Boltz-2 teacher and Blitz K8 remain addressable as `folding-boltz2` and
  `folding-blitz-k8`.

### Reproducibility
- `--seed` (default 42) propagated to every Predict step.
- `--deterministic` forces deterministic GPU kernels. Needed *in addition* to
  the seed: seeded-only runs of identical inputs diverged by up to 31.7 Å
  across 20 designs.

### Sampler
- `exp_exact_step`, off by default, behind an attribute or
  `$BOLTZ_EXP_EXACT_STEP`. Covered by `tests/test_exp_exact_step.py`.

### Loading
- `_strip_trifast` drops the `use_trifast` hparam that `boltz2_conf`
  checkpoints carry and boltzgen trunk modules reject.

### Packaging — new in this release
- Distribution renamed `boltzgen` → `blitzgen`. The import package and the
  `boltzgen` command are unchanged; a `blitzgen` command is added.
- Version corrected from `1.0.0` to `0.1.0`.
- `cuequivariance_ops_*` moved from hard dependencies to `[cu12]` / `[cu13]`
  extras. **Behaviour change:** a bare `pip install blitzgen` no longer pulls
  them. They are not on the critical path — `libcue_ops.so` is never loaded —
  and the previous hard `cu13` pin made the package uninstallable on CUDA 12
  hosts. `cuequivariance_torch`, which is on the critical path, stays required.
- `README.md` now leads with BlitzGen as a pipeline of replaceable components,
  with a component table and the naming convention (role-first artifact keys,
  `<framework>-<base>-<variant>` checkpoints), above upstream's README rather
  than as an annotation on it. The previous fork banner was stale: it pointed
  at a `README_MSCD_STUDENT.md` that no longer exists and described the 8-step
  K8 arm that K16 replaced.
- Redacted a plaintext Hugging Face token from upstream's `README.md`
  `--models_token` documentation. Upstream's to rotate, already public there,
  but not something to republish under a new remote. See `FORK.md`.
- Fixed a comment naming `BOLTZGEN_FOLDING_CKPT`; the variable the code reads
  is `BLITZGEN_FOLDING_CKPT`.
