# Status

**BlitzGen is 0.x and in progress. This is not BlitzGen 1.0.**

That needs saying plainly because the pre-publication tree carried
`version = "1.0.0"` in `pyproject.toml`. It was wrong in both directions: the
project had made no 1.0 commitment, and the number also read as *BoltzGen*
1.0 while the tree was actually sitting on upstream 0.3.2. The version is now
`0.1.0` and will stay in 0.x until the trunk question below is settled.

What 0.x means here: no API stability between releases, and default
checkpoints, default configs and CLI flags may change. Pin a tag.

## Where things stand

BlitzGen is a pipeline of replaceable components (see the table in `README.md`).
Status is therefore per component, not global:

| component | status |
|---|---|
| **folding — sampler** | **Settled.** Blitz K16 is the default and has run production campaigns. |
| **folding — trunk** | **Under investigation — PairMixer.** See below. |
| design, inverse folding | Upstream BoltzGen's, unmodified. No work planned. |
| analysis, filtering | Upstream BoltzGen's, unmodified. |
| Blitz FK steering | Not ported. See `FORK.md`. |
| upstream sync | Base is 2026-05-28; upstream has moved a long way. See `FORK.md`. |

Only one component is in flux. That is the whole argument for the framework
framing: a pipeline whose stages are named by role rather than by vendor can
have one stage replaced without the project, the CLI or the configs changing
shape around it.

The folding arm being settled is what makes a 0.1.0 worth publishing at all.
K16 under `fold_blitz_k16.yaml` tracks the Boltz-2 teacher closely enough that
filter thresholds derived against the teacher carry over without rescaling —
measured on 20 paired designs, Spearman +0.88 to +0.96 on the three metrics
that drive filtering (`README_BLITZ_FOLDING.md` has the table).

## The open question: PairMixer in the trunk

Today BlitzGen replaces only the **structure module** — the distilled student
swaps in for the teacher's sampler, and the trunk (pairformer, templates, MSA)
is Boltz-2's, run at full cost. Folding is ~3.3× faster in the predict phase,
but trunk and I/O now dominate the step wall, which is why 25× fewer sampler
steps buys 34% rather than 25×.

We are investigating replacing the trunk's pairformer with **PairMixer**. If it
lands it changes:

- the trunk, which every step depends on — not just folding
- the checkpoint format and export recipe
- the measured teacher-tracking above, which would need re-measuring, because
  it is a property of the *pair* (trunk, sampler), not of K16 alone
- probably the filter thresholds that currently carry over unrescaled

That is a 1.0-sized change, and it is the reason 1.0 is not being claimed now.
A trunk swap landing right after a 1.0 would make the version number a lie.

What it is *not* is a naming problem. PairMixer would arrive as `trunk-pairmixer`
beside `trunk-boltz2`, the way `folding-blitz-k8` sits beside `folding-boltz2`
today. Component names carry provenance; the project name does not. A project
named after its current components -- `blitz-boltzgen`, say -- would need
renaming on every swap, and would spawn a new name per combination.

## Before 1.0

- [ ] Resolve the PairMixer trunk question either way
- [ ] Rebase onto a current upstream, or decide explicitly not to and say why
- [ ] K16 verified on a non-Ampere card (sm_75); `cuequivariance` triton kernel
      support there is currently **unknown**
- [ ] Port Blitz FK steering, or document permanently that it is out of scope
- [ ] Decide whether `exp_exact_step` becomes the default or is removed
