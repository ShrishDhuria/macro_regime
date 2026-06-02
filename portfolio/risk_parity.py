"""Equal Risk Contribution (risk parity) and volatility targeting."""
from __future__ import annotations
import numpy as np


def solve_erc(cov: np.ndarray, max_iter: int = 200, tol: float = 1e-9) -> np.ndarray:
    """Maillard-Roncalli-Teiletche (2010) iterative ERC solver. Long-only, sums to 1."""
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(max_iter):
        sigma_w = cov @ w
        rc = w * sigma_w
        target = rc.mean()
        rc_safe = np.maximum(rc, 1e-12)
        w_new = w * np.sqrt(target / rc_safe)
        w_new = np.maximum(w_new, 1e-6)
        w_new = w_new / w_new.sum()
        if np.max(np.abs(w_new - w)) < tol:
            return w_new
        w = w_new
    return w


def safe_erc(cov: np.ndarray) -> np.ndarray:
    try:
        np.linalg.cholesky(cov)
        return solve_erc(cov)
    except np.linalg.LinAlgError:
        n = cov.shape[0]
        return np.ones(n) / n


def vol_target_scale(weights, cov, target_vol_annual=0.10, max_leverage=1.5, min_exposure=0.30):
    port_var = float(weights @ cov @ weights)
    if port_var <= 0:
        return weights
    port_vol_annual = np.sqrt(52 * port_var)
    scale = float(np.clip(target_vol_annual / port_vol_annual, min_exposure, max_leverage))
    return weights * scale
