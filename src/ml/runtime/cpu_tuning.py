"""CPU runtime tuning helpers.

Call early (before heavy imports) to pin thread counts and optionally
set environment variables for deterministic performance.
"""
from __future__ import annotations
import os
import torch
from typing import Optional

_DEF_ENV = {
    # Disable OpenMP nested parallelism overhead if not needed
    "OMP_NUM_THREADS": None,  # set dynamically from n_threads if provided
    "MKL_NUM_THREADS": None,
    "NUMEXPR_NUM_THREADS": None,
}


def set_cpu_threads(n_threads: int, set_env: bool = True) -> None:
    """Set PyTorch intra/inter op threads plus common BLAS env vars.

    Parameters
    ----------
    n_threads: Total threads to use (will apply to intra + inter)
    set_env: Whether to also set OMP/MKL/NUMEXPR env variables
    """
    if n_threads < 1:
        return
    torch.set_num_threads(n_threads)
    torch.set_num_interop_threads(max(1, n_threads // 2))
    if set_env:
        for key in _DEF_ENV.keys():
            os.environ[key] = str(n_threads)


def recommend_threads() -> int:
    """Return a heuristic recommended thread count (half logical cores)."""
    try:
        import multiprocessing
        cores = multiprocessing.cpu_count()
        return max(1, cores // 2)
    except Exception:
        return 4

__all__ = ["set_cpu_threads", "recommend_threads"]
