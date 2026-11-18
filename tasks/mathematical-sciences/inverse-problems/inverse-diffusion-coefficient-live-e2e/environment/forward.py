"""Deterministic implicit finite-difference heat solver used by the task."""

import math

N = 20
DT = 0.01
SENSORS = (4, 8, 12, 16)
OBS_STEPS = (5, 10, 15, 20)


def solve(diffusivity, steps=20):
    """Return temperature after every time step on the interior grid."""
    if len(diffusivity) != N or any(not math.isfinite(d) or d <= 0 for d in diffusivity):
        raise ValueError("diffusivity must contain 20 finite positive values")
    dx = 1 / (N + 1)
    edges = [diffusivity[0]]
    edges += [(diffusivity[i - 1] + diffusivity[i]) / 2 for i in range(1, N)]
    edges += [diffusivity[-1]]
    scale = DT / dx**2
    lower = [-scale * edges[i] for i in range(1, N)]
    upper = [-scale * edges[i + 1] for i in range(N - 1)]
    diagonal = [1 + scale * (edges[i] + edges[i + 1]) for i in range(N)]
    u = [math.sin(math.pi * (i + 1) * dx) + 0.25 * math.sin(3 * math.pi * (i + 1) * dx) for i in range(N)]
    states = {}
    for step in range(1, steps + 1):
        c = upper.copy()
        d = diagonal.copy()
        rhs = u.copy()
        for i in range(1, N):
            factor = lower[i - 1] / d[i - 1]
            d[i] -= factor * c[i - 1]
            rhs[i] -= factor * rhs[i - 1]
        u[-1] = rhs[-1] / d[-1]
        for i in range(N - 2, -1, -1):
            u[i] = (rhs[i] - c[i] * u[i + 1]) / d[i]
        states[step] = u.copy()
    return states


def basis_field(a, b, c):
    return [a + b * (i + 1) / (N + 1) + c * math.sin(math.pi * (i + 1) / (N + 1)) for i in range(N)]
