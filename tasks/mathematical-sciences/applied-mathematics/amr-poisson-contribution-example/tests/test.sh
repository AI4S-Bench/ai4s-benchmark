#!/usr/bin/env sh
set -eu

test "$(cat /workspace/result.txt)" = "AMR Poisson task scaffold ready"

