"""Baseline: Chebyshev expansion of the Fermi-Dirac function.

This is the conventional linear-scaling approach: f(H) is expanded in
Chebyshev polynomials of the scaled Hamiltonian and applied with the
three-term recurrence (one sparse matrix-block product per degree).  It is
accurate for kT > 0, but the degree it needs grows like (spectral width) / kT,
so it becomes unusable at low temperature and cannot represent kT = 0 at all.

Replace this file with your own implementation.  The grader imports
`fermi_dirac_operator` from this module.
"""
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

MAX_DEGREE = 200_000


def _fermi(x, kT):
    return 0.5 * (1.0 - np.tanh(0.5 * x / kT))


def fermi_dirac_operator(H, kT, mu):
    """Return a LinearOperator applying 1 / (1 + exp((H - mu) / kT))."""
    H = sp.csr_matrix(H, dtype=np.float64)
    n = H.shape[0]
    if kT <= 0:
        raise NotImplementedError("the Chebyshev baseline cannot represent kT = 0")

    d = H.diagonal()
    rad = np.asarray(abs(H).sum(axis=1)).ravel() - np.abs(d)
    a, b = float((d - rad).min()), float((d + rad).max())
    center, radius = 0.5 * (a + b), 0.5 * (b - a)

    # Degree from the Bernstein ellipse through the Matsubara pole mu + i pi kT.
    xp = complex((mu - center) / radius, math.pi * kT / radius)
    rho = abs(xp + np.sqrt(xp - 1.0) * np.sqrt(xp + 1.0))
    degree = int(math.ceil(math.log(1e9) / math.log(max(rho, 1.0 / rho)))) + 8
    if degree > MAX_DEGREE:
        raise RuntimeError(f"kT = {kT:g} needs a Chebyshev degree of about {degree}")

    # Chebyshev coefficients c_k = (2/m) sum_j f(x_j) cos(k theta_j) by FFT.
    m = 2 * (degree + 1)
    theta = np.pi * (np.arange(m) + 0.5) / m
    fx = _fermi(center + radius * np.cos(theta) - mu, kT)
    k = np.arange(degree + 1)
    c = np.real(np.fft.rfft(np.concatenate([fx, fx[::-1]]))[: degree + 1]
                * np.exp(-0.5j * np.pi * k / m)) / m
    c[0] *= 0.5

    def matmat(X):
        X = np.asarray(X, dtype=np.float64)
        t_prev = X
        t_cur = (H @ X - center * X) / radius
        Y = c[0] * t_prev + c[1] * t_cur
        for ck in c[2:]:
            t_prev, t_cur = t_cur, 2.0 * (H @ t_cur - center * t_cur) / radius - t_prev
            Y += ck * t_cur
        return Y

    def matvec(x):
        return matmat(np.asarray(x).reshape(-1, 1)).ravel()

    return spla.LinearOperator((n, n), matvec=matvec, matmat=matmat, dtype=np.float64)
