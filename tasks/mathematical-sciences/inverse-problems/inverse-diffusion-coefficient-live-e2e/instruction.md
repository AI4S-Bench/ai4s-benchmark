# Inverse diffusion coefficient

The temperature follows `u_t = (D(x) u_x)_x` on `0 < x < 1`, with zero
Dirichlet boundary conditions. The initial field is
`sin(pi*x) + 0.25*sin(3*pi*x)`. The unknown diffusivity is constrained to
`D(x) = a + b*x + c*sin(pi*x)` and is positive over the domain.

`/workspace/forward.py` provides the exact finite-difference forward model used
to generate `/workspace/observations.csv`. Each row gives time step, grid
index, and a noisy temperature. The grid has 20 interior cells; one implicit
step is 0.01 time units. Noise standard deviation is 0.0002. There are no
external data dependencies.

Estimate the coefficient from the observations. Write `/workspace/estimate.csv`
as exactly 20 rows, one `D(x)` value per interior grid cell, with no header.
All values must be finite and strictly positive. The verifier compares the
field with an unseen reference and checks prediction error at held-out sensors.
You may use NumPy and SciPy, which are already installed.
