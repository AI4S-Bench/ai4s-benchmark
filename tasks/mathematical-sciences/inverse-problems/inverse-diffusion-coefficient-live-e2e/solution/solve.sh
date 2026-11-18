#!/bin/sh
set -eu
python - <<'PY'
import csv
import numpy as np
from scipy.optimize import least_squares
from forward import basis_field, solve

with open('/workspace/observations.csv', newline='') as file:
    observations = [(int(row['step']), int(row['index']), float(row['temperature'])) for row in csv.DictReader(file)]

def residual(params):
    states = solve(basis_field(*params))
    return np.array([states[step][index - 1] - target for step, index, target in observations])

fit = least_squares(residual, [0.3, 0.1, 0.05], bounds=([0.05, -0.3, -0.3], [0.8, 0.5, 0.5]), xtol=1e-12, ftol=1e-12, gtol=1e-12)
with open('/workspace/estimate.csv', 'w', newline='') as file:
    csv.writer(file).writerows([[value] for value in basis_field(*fit.x)])
PY
