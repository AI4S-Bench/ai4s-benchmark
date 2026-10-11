#!/bin/sh
set -eu
mkdir -p /logs/verifier
python - <<'PY'
import csv
import math
from pathlib import Path
from forward import OBS_STEPS, SENSORS, basis_field, solve

reward = 0.0
try:
    with open('/workspace/estimate.csv', newline='') as file:
        rows = list(csv.reader(file))
    estimate = [float(row[0]) for row in rows if len(row) == 1]
    truth = basis_field(0.28, 0.18, 0.08)
    if len(rows) == len(estimate) == len(truth) and all(math.isfinite(x) and x > 0 for x in estimate):
        relative = math.sqrt(sum((a-b)**2 for a,b in zip(estimate, truth)) / sum(x*x for x in truth))
        observed = solve(estimate)
        expected = solve(truth)
        prediction = math.sqrt(sum((observed[t][i-1]-expected[t][i-1])**2 for t in OBS_STEPS for i in SENSORS) / (len(OBS_STEPS)*len(SENSORS)))
        reward = min(max(1-relative/0.12, 0), max(1-prediction/0.015, 0))
        print(f'relative_error={relative:.6f} prediction_rmse={prediction:.6f} reward={reward:.6f}')
except (FileNotFoundError, ValueError, IndexError) as exc:
    print(f'invalid solution: {exc}')
Path('/logs/verifier/reward.txt').write_text(f'{reward:.6f}\n')
PY
