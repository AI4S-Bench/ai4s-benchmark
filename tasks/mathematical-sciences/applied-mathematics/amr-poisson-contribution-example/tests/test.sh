#!/usr/bin/env sh
set -eu

# Harbor scores the trial from /logs/verifier/reward.txt and ignores this script's exit code.
# The agent can also write /logs/verifier, and Harbor reads reward.json first, so clear both.
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
if [ "$(cat /workspace/result.txt 2>/dev/null)" = "AMR Poisson task scaffold ready" ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

