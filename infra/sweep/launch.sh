#!/usr/bin/env bash
# Launch one sweep driver in the background (plan/SWEEP_PLAN.md). Usage:
#   infra/sweep/launch.sh <tag> <grid_driver args...>
# The OpenRouter key is read from the key file inside the command and never echoed.
set -euo pipefail
cd "$(dirname "$0")/../.."
tag=$1; shift
K="/home/iraj/projects/swarm_data?/.planAdemoenv"
OPENROUTER_API_KEY="$(cat "$K")" PYTHONNOUSERSITE=1 setsid nohup conda run -n swarm --no-capture-output \
  python infra/grid_driver.py --ledger-stop 7.80 --log runs/sweep_driver.log "$@" \
  > "runs/sweep_driver_$tag.out" 2>&1 < /dev/null &
echo "driver $tag pid $!"
