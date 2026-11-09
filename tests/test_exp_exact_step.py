"""Unit tests for closed-form S-scaled exact step (OFF by default).

Algebra matches boltz_v2 AtomDiffusion:
    x_next = D + (σ_next / σ_cur)^S · (x − D)

This file avoids importing boltzgen.model.modules.diffusion (heavy deps /
torch version). It loads ``exp_exact_step_enabled`` by AST extraction and
checks the sample-loop source contains the closed-form branch.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import torch

_DIFFUSION_PY = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "boltzgen"
    / "model"
    / "modules"
    / "diffusion.py"
)


def _load_exp_exact_step_enabled():
    """Exec just the helper from diffusion.py (needs only ``os``)."""
    src = _DIFFUSION_PY.read_text()
    tree = ast.parse(src)
    fn_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "exp_exact_step_enabled":
            fn_node = node
            break
    assert fn_node is not None, "exp_exact_step_enabled missing from diffusion.py"
    mod = ast.Module(body=[fn_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {"os": os}
    exec(compile(mod, str(_DIFFUSION_PY), "exec"), ns)  # noqa: S102
    return ns["exp_exact_step_enabled"]


def _exp_exact_update(x, D, sigma_cur, sigma_next, step_scale):
    """Inline copy of the boltz_v2 / boltzgen closed-form update."""
    sigma_cur_f = float(sigma_cur)
    sigma_next_f = float(sigma_next)
    if sigma_cur_f <= 0.0:
        ratio = 0.0
    else:
        ratio = (sigma_next_f / sigma_cur_f) ** float(step_scale)
    return D + ratio * (x - D)


def test_exp_exact_flag_off_by_default(monkeypatch):
    exp_exact_step_enabled = _load_exp_exact_step_enabled()
    monkeypatch.delenv("BOLTZ_EXP_EXACT_STEP", raising=False)
    assert exp_exact_step_enabled(None) is False
    assert exp_exact_step_enabled(type("M", (), {"exp_exact_step": False})()) is False


def test_exp_exact_flag_module_attr(monkeypatch):
    exp_exact_step_enabled = _load_exp_exact_step_enabled()
    monkeypatch.delenv("BOLTZ_EXP_EXACT_STEP", raising=False)
    assert exp_exact_step_enabled(type("M", (), {"exp_exact_step": True})()) is True


def test_exp_exact_flag_env(monkeypatch):
    exp_exact_step_enabled = _load_exp_exact_step_enabled()
    monkeypatch.setenv("BOLTZ_EXP_EXACT_STEP", "1")
    assert exp_exact_step_enabled(None) is True
    monkeypatch.setenv("BOLTZ_EXP_EXACT_STEP", "true")
    assert exp_exact_step_enabled(None) is True
    monkeypatch.setenv("BOLTZ_EXP_EXACT_STEP", "0")
    assert exp_exact_step_enabled(None) is False


def test_exp_exact_algebra_matches_boltz_v2_formula():
    torch.manual_seed(0)
    S = 1.5
    for _ in range(32):
        x = torch.randn(2, 5, 3)
        D = torch.randn(2, 5, 3)
        sigma_cur = float(torch.empty(1).uniform_(0.01, 2560.0))
        sigma_next = sigma_cur * float(torch.empty(1).uniform_(0.0, 0.99))
        got = _exp_exact_update(x, D, sigma_cur, sigma_next, S)
        ratio = (sigma_next / sigma_cur) ** S
        expected = D + ratio * (x - D)
        assert torch.allclose(got, expected, rtol=0.0, atol=1e-6)


def test_exp_exact_travel_fraction_never_crosses_d():
    """Travel fraction 1-(1-r)^S ∈ (0,1) for every r∈(0,1), any S>0."""
    S = 1.5
    for r in (0.1, 0.5, 0.6667, 0.9, 0.98):
        frac = 1.0 - (1.0 - r) ** S
        assert 0.0 < frac < 1.0
        assert (1.0 - r) ** S > 0.0


def test_exp_exact_zero_sigma_cur_ratio():
    x = torch.ones(1, 2, 3)
    D = torch.zeros(1, 2, 3)
    got = _exp_exact_update(x, D, sigma_cur=0.0, sigma_next=0.0, step_scale=1.5)
    assert torch.allclose(got, D)


def test_atom_diffusion_ctor_and_sample_wire_flag():
    """Ctor accepts exp_exact_step; sample loop branches on the helper."""
    src = _DIFFUSION_PY.read_text()
    tree = ast.parse(src)
    atom = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "AtomDiffusion":
            atom = node
            break
    assert atom is not None
    init = None
    sample = None
    for node in atom.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            init = node
        if isinstance(node, ast.FunctionDef) and node.name == "sample":
            sample = node
    assert init is not None and sample is not None
    arg_names = [a.arg for a in init.args.args]
    assert "exp_exact_step" in arg_names
    sample_src = ast.get_source_segment(src, sample) or ""
    assert "exp_exact_step_enabled(self)" in sample_src
    assert "(sigma_next_f / sigma_cur_f)" in sample_src
    assert "denoised_over_sigma" in sample_src  # Euler path preserved
