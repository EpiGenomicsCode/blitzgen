# What this fork changes

BlitzGen is a pipeline of replaceable components (see `README.md`), and upstream
[HannesStark/boltzgen](https://github.com/HannesStark/boltzgen) supplies most of
them: design, inverse folding, analysis and filtering are upstream's, unmodified.
What this fork changes is the folding stage, plus the plumbing needed to swap a
component at all — `--folding_config`, `--seed`.

So it is deliberately a *small* fork: 12 files modified, 4 added, about 300
lines. Keeping it small is the point — upstream moves, and a fork that cannot be
rebased is a dead end.

## Upstream base

| | |
|---|---|
| base commit | [`a3149cf`](https://github.com/HannesStark/boltzgen/commit/a3149cf) "fix small writer bug" |
| base date | 2026-05-28 |
| upstream version there | 0.3.2 |
| git tag here | `upstream-base` |

The first commit of this repository is that upstream tree, unmodified. So:

```sh
git diff upstream-base..HEAD          # exactly what BlitzGen changes
git diff upstream-base..HEAD --stat   # the same, summarised
```

> **One byte of upstream is changed by that first commit.** Upstream's README
> documents `--models_token` with a real-looking Hugging Face token as its
> default value, in plaintext; it is replaced here with `hf_<REDACTED>`. It is
> upstream's token to rotate, not ours, and it is already public in their
> repository — but republishing it under a new remote trips secret scanning and
> push protection, and a credential does not belong in a tree we chose to copy.
> The EpiGenomicsCode fork had already redacted it, which is why it appears in
> the base commit rather than as a fork change.

> The base was recovered by content, not read off a branch point — the working
> tree this repository was built from carried no git history. Every file was
> hashed and matched against all 266 upstream commits; `a3149cf` is the latest
> commit at which no upstream file is missing from the fork and only 12 differ.
> The next candidates forward differ in 13. It is the best-supported base, not
> a recorded one.

## Rebasing onto upstream

```sh
git remote add upstream https://github.com/HannesStark/boltzgen.git
git fetch upstream
git rebase --onto upstream/main upstream-base
```

Upstream has moved a long way since the base: `esmfold2`, SolubleMPNN inverse
folding, `_vendor/`, `docs/`, `scripts/`, and roughly forty new tests. None of
that is here. A rebase is real work, not a formality — budget for it.

## The changes

### Folding arm — Blitz K16

`src/boltzgen/cli/boltzgen.py`, `src/boltzgen/resources/config/fold_blitz_k16.yaml`,
`fold_blitz_k8.yaml`

The default `folding` artifact becomes **Blitz K16**
([EpiGenomicsCode/Blitz](https://github.com/EpiGenomicsCode/Blitz)) — a 16-step
deterministic distilled Boltz-2 student. The checkpoint is found via
`$BLITZGEN_FOLDING_CKPT`, else by searching `artifacts/` upward from the working
directory. There is no good universal location for a 2 GB file, and the previous
default was an absolute path on one cluster's scratch.

Boltz-2 teacher and Blitz K8 remain addressable as `folding-boltz2` and
`folding-blitz-k8`.

New `--folding_config` selects the recipe, defaulting K16 → K8 → stock. It
exists because **the pairing is load-bearing**: K16 weights run on the K8
schedule put 16-step weights through 8 steps at the wrong `sigma_min`. Nothing
raises, the structures look plausible, and the sampler is simply wrong. The
default checkpoint and the default recipe therefore move together.

No new sampler code was needed. Blitz hardcodes a sigma tuple in absolute units;
BoltzGen's `sample_schedule_af3` generates the same curve analytically. At
`sigma_max=160, sigma_min=0.01, rho=40, sigma_data=16, N=16` they agree to
~1e-13; for K8 they agree bit for bit.

### Reproducibility — `--seed`, `--deterministic`

`src/boltzgen/cli/boltzgen.py`, `src/boltzgen/task/predict/predict.py`,
and a `seed` / `deterministic` field in the five predict configs

`--seed` (default 42) reaches every Predict step. `--deterministic` forces
deterministic GPU kernels.

Both halves are needed. Seeding alone left two runs of identical inputs **31.7 Å**
apart across 20 designs: non-deterministic kernels perturb step 1 at ~1e-7 and
sixteen diffusion steps amplify it. `--deterministic` costs throughput, so it is
opt-in, and it cannot set `CUBLAS_WORKSPACE_CONFIG=:4096:8` for itself — that
has to be in the environment before CUDA initialises.

### `exp_exact_step`

`src/boltzgen/model/modules/diffusion.py`, `tests/test_exp_exact_step.py`

Closed-form S-scaled exact step, **off by default**, behind an attribute or
`$BOLTZ_EXP_EXACT_STEP`:

```
x_next = D + (sigma_next / sigma_cur)^S * (x - D)
```

The travel fraction `1 - (1-r)^S` stays in `(0,1)` for every `r < 1`, so the
iterate never crosses `D` and there is no ψ-pole.

### Checkpoint loading — `_strip_trifast`

`src/boltzgen/model/models/boltz.py`

`boltz2_conf` checkpoints carry a `use_trifast` hparam that boltzgen's trunk
modules reject. It is stripped from `template_args`, `msa_args` and
`pairformer_args`, handling OmegaConf `DictConfig` as well as plain dicts.

### Packaging

`pyproject.toml`

- Distribution renamed `boltzgen` → **`blitzgen`**; the import package stays
  `boltzgen`, so upstream configs, docs and examples work unchanged.
- Version **0.1.0**. The pre-publication tree claimed `1.0.0` while sitting on
  upstream 0.3.2; that was wrong twice over. See `ROADMAP.md`.
- `blitzgen` console script added alongside `boltzgen`.
- `cuequivariance_ops_*` moved to `[cu12]` / `[cu13]` extras. They are
  CUDA-major-specific and **not** on the critical path — `libcue_ops.so` is
  never loaded in this pipeline; `cuequivariance_torch`'s triton kernels are
  what actually run, and that stays a hard dependency. A hard `cu13` pin made
  the package uninstallable on the CUDA 12 hosts it is meant to run on.

### Housekeeping

`src/boltzgen/task/predict/writer.py` closes the files it writes.

## What is NOT reproduced from Blitz

BoltzGen has no potentials module and no guidance update, so Blitz's FK steering
and terminal clean projection are absent. That costs the published
physical-validity gain (violation rate 26.7% vs teacher 30.3%). It does not
affect whether the checkpoint runs. The full steering policy is written down in
`README_BLITZ_FOLDING.md` for whoever ports it.
