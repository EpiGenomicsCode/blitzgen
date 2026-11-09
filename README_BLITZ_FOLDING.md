# BlitzGen folding: Blitz K8 / K16

Fork of [BoltzGen](https://github.com/HannesStark/boltzgen) with the **folding /
structure-prediction** step wired to a distilled Boltz-2 student.

**Default since 2026-10-21: Blitz K16** ([EpiGenomicsCode/Blitz](https://github.com/EpiGenomicsCode/Blitz)),
16-step deterministic student.

### Nomenclature

This fork previously called the 8-step arm the "MSCD Arm C student"
(`boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt`). That is the **same artifact Blitz
releases as K8** -- its schedule reproduces Blitz's K8 sigma tuple bit for bit -- and
the names are now unified:

| use this | formerly |
|---|---|
| `blitz-k16`, `fold_blitz_k16.yaml`, artifact key `folding` (default) | -- (new) |
| `blitz-k8`, `fold_blitz_k8.yaml`, artifact key `folding-blitz-k8` | MSCD Arm C student, `fold_mscd_student.yaml` |
| `fold.yaml`, artifact key `folding-boltz2` | Boltz-2 teacher, unchanged |

The old hardcoded Delta path for K8 has been removed; set `BLITZGEN_FOLDING_CKPT_K8`
if you need that arm.

---

## Defaults

| | |
|---|---|
| Folding checkpoint | `blitz-boltz2-k16.ckpt`, located via `$BLITZGEN_FOLDING_CKPT`, else `artifacts/` searched upward from the CWD |
| Folding config | `fold_blitz_k16.yaml` -- **16 steps, sigma_min 0.01** |
| Seed | `--seed`, default 42 (see REPRODUCIBILITY.md -- necessary, not sufficient) |
| Rollback: Blitz K8 | `--folding_checkpoint $(...)/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt --folding_config fold_blitz_k8.yaml` |
| Rollback: Boltz-2 teacher | `--folding_checkpoint 'huggingface:boltzgen/boltzgen-1:boltz2_conf_final.ckpt' --folding_config fold.yaml` |

There is no portable default path for a 2 GB checkpoint. In a container, set it:

```bash
export APPTAINERENV_BLITZGEN_FOLDING_CKPT=/path/to/blitz-boltz2-k16.ckpt
```

### The pairing matters

K16 weights **must** run on the K16 schedule. Pairing `blitz-boltz2-k16.ckpt` with
`fold_blitz_k8.yaml` (8 steps, sigma_min 0.004) runs 16-step weights on an
8-step schedule at the wrong sigma_min. Nothing errors, the structures look
plausible, and the sampler is simply wrong. The default config moved together with
the default checkpoint for exactly this reason.

### Schedule equivalence (why no new sampler code was needed)

Blitz hardcodes a sigma tuple in absolute units; BoltzGen's `sample_schedule_af3`
generates the same curve analytically and multiplies by `sigma_data`. With
`sigma_max=160, sigma_min=0.01, rho=40, sigma_data=16, N=16` the two agree to
~1e-13. For K8 (`sigma_min=0.004, N=8`) they agree **bit for bit**.

### What is NOT reproduced: Blitz steering

BoltzGen has no potentials module and no guidance update, so Blitz's FK steering
and terminal clean projection are absent. This costs the published
physical-validity gain (violation rate 26.7% vs teacher 30.3%); it does not affect
whether the checkpoint runs, and Blitz K8 ran the same way for the NOTCH1
campaigns. Measured on 20 paired designs, K16 under `fold_blitz_k16.yaml` tracks
the Boltz-2 teacher closely:

| metric | teacher | K16 | shift | spearman |
|---|---|---|---|---|
| `design_to_target_iptm` | 0.197 | 0.205 | -0.004 | +0.88 |
| `complex_plddt` | 0.502 | 0.501 | +0.002 | +0.96 |
| `min_interaction_pae` | 10.92 | 10.07 | +0.37 | +0.89 |

so filter thresholds derived against the teacher carry over without rescaling.

**Full K16 steering policy**, for whoever ports it: `fk_steering=True`,
`num_particles=1` (so FK resampling is inert -- there is no particle population to
select between), `fk_lambda=4.0`, `fk_resampling_interval=3`,
`physical_guidance_update=True`, `contact_guidance_update=True`, `num_gd_steps=20`,
terminal clean projection scale `2/27` with 10 GD steps. Per-potential guidance
weights are **retuned for 16 steps**, not the Boltz-2 defaults: VDWOverlap 0.675,
SymmetricChainCOM 0.5, Connections 0.15, StereoBond 0.05, PlanarBond 0.05,
ChiralAtom scheduled 2.651 -> 0.194 across the 15 inner steps, PoseBusters
scheduled 0.634 -> 0.040 with a terminal override to 0.135 below 3/32.

---

## 1. Install

```bash
git clone git@github.com:EpiGenomicsCode/blitzgen.git
cd blitzgen

conda create -n bg python=3.12 -y
conda activate bg
pip install -e .
```

GPU recommended (same as upstream BoltzGen).

---

## 2. Checkpoints

The folding weights are **not** in git (≈1.9 GiB `.ckpt`). Place the export here (or pass an absolute path):

```text
# legacy K8 filename; the CLI no longer hardcodes this path:
/work/nvme/bgqi/vmathew/boltz_data/boltzgen_artifacts/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt
```

**Provenance**

| | |
|---|---|
| K8 source training ckpt | `mscdV2C/mscd-step=2000.ckpt` (BoltzMSCDistiller) |
| Weights | **RAW** (not EMA / PHEMA) |
| Structure fingerprint | `f8d1667b2a7e9846` |
| Export recipe | teacher trunk+confidence + `student.structure_module` → Lightning `Boltz` keys |
| Sidecar | same path + `.json` next to the `.ckpt` |

On machines outside Delta, copy the `.ckpt` (+ `.json`) and pass:

```bash
--folding_checkpoint /path/to/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt
```

Or change the default path in `src/boltzgen/cli/boltzgen.py` (`_MSCD_STUDENT_FOLDING`).

Download other artifacts (design / inverse-fold / moldir) as usual:

```bash
boltzgen download all
# or selectively:
boltzgen download design-diverse inverse-fold moldir
```

You do **not** need HF `folding` if you use the local student ckpt.

---

## 3. Run a design

Pipeline steps: `design` → `inverse_folding` → **`folding`** (student) → optional `design_folding` / `affinity` → `analysis` → `filtering`.

```bash
boltzgen run example/vanilla_protein/1g13prot.yaml \
  --output workbench/mscd_student_smoke \
  --protocol protein-anything \
  --num_designs 2 \
  --folding_checkpoint /path/to/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt
```

With this fork, omitting `--folding_checkpoint` uses the MSCD student default path above (must exist on disk).

**Student fold knobs** (already in `src/boltzgen/resources/config/fold_blitz_k8.yaml`):

- `sampling_steps=8`
- `recycling_steps=5`
- `override.diffusion_process_args`: `rho=40`, `sigma_min=0.004`, `sigma_max=160`, `sigma_data=16`, `step_scale=1.5`, `gamma_0=0`, `exp_exact_step=true`, `sampling_schedule=af3`

Override example:

```bash
boltzgen run example/vanilla_protein/1g13prot.yaml \
  --output workbench/mscd_student_smoke \
  --protocol protein-anything \
  --num_designs 2 \
  --folding_checkpoint /path/to/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt \
  --config folding trainer.devices=1
```

### Folding-only (after design + inverse fold exist)

```bash
boltzgen run example/vanilla_protein/1g13prot.yaml \
  --output workbench/mscd_student_smoke \
  --steps folding \
  --reuse \
  --folding_checkpoint /path/to/boltz2_mscd_armC_step2000_raw_S1.5exp.ckpt
```

### Roll back to stock Boltz-2 folding

```bash
boltzgen run ... \
  --folding_checkpoint 'huggingface:boltzgen/boltzgen-1:boltz2_conf_final.ckpt' \
  --config folding recycling_steps=3 sampling_steps=200
```

(Stock `fold.yaml` remains in-tree; this fork’s CLI prefers `fold_blitz_k8.yaml` for folding steps.)

---

## 4. Sanity checks

```bash
# unit tests (exp_exact algebra + wiring)
cd blitzgen
PYTHONPATH=src python -m pytest tests/test_exp_exact_step.py -v
```

Optional parity smoke (needs the export ckpt; GPU preferred):

```bash
# from boltz_training workspace helpers (if present):
python scripts/boltzgen_student_parity_smoke.py --allow-cpu-load
```

Expected: fingerprint `f8d1667b2a7e9846`, schedule matches Arm C grid, `strict=True` load OK.

---

## 5. Sampler note: Blitz K8 (why these knobs)

Winning bench tag: `b2269_armC_k8_s0.004_r40_S1.5_exp`

- Deterministic: `gamma_0=0` (no AF3 churn)
- Update: **exp-exact**  
  `x_next = D + (σ_next/σ_cur)^S · (x − D)` with `S=1.5`
- Do **not** point `--folding_checkpoint` at the raw MSCD *training* ckpt (`teacher.*` / `student.*` prefixes). Use the **exported** folding ckpt only.

---

## License / attribution

BoltzGen upstream: [HannesStark/boltzgen](https://github.com/HannesStark/boltzgen).  
MSCD student training and export: Lai lab / EpiGenomicsCode distillation stack.


---

## 6. End-to-end check (design → fold) & savings

Interactive smoke on DeltaAI GH200 (`example/vanilla_protein/1g13prot.yaml`, 2 designs; shared design+ifold; `--use_kernels false`):

| Folding arm | config | sampling_steps | recycle | step wall | predict only (2 designs) | ≈ s/design predict |
|---|---|---:|---:|---:|---:|---:|
| **MSCD student** | `fold_blitz_k8.yaml` | **8** | 5 | **31.3 s** | **7.0 s** | **~3.5 s** |
| Boltz-2 teacher | `fold.yaml` | 200 | 3 | 47.8 s | 23.3 s | ~11.7 s |

**Folding savings (this smoke):**
- Predict-phase: **~3.3× faster** (11.7 → 3.5 s/design); **~70% less** fold-predict time
- Full folding step wall: **34% less** (47.8 → 31.3 s) — load/setup still dominates at n=2; predict ratio is the scalable saving
- Sampler steps: **25× fewer** (200 → 8); wall speedup is smaller because trunk/confidence/IO remain

Confidence on the same designs was close (e.g. design_0 iptm 0.428 MSCD vs 0.430 Boltz-2). Coordinates differ (different sampler), as expected.

CLI extras used in that check:
- `--folding_config fold.yaml` for stock Boltz-2 folding
- `--folding_checkpoint` for either student export or `boltz2_conf.ckpt`
- `use_trifast` is stripped automatically when loading Boltz-2 conf hparams into boltzgen modules

