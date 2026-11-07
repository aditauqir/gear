Implemented only new files in the allowed directories.

- Files: `swarm/monitors/{__init__,public,claims,saydo_rules,anomaly,evaluation}.py` and `tests/monitors/test_watchtower.py`.
- Public API: `public_trace(events)`, `promise_vs_action(events, k=2)`, `message_anomaly(events)`, and `evaluate(scores, truth_labels)`.
- Detectors return per-agent, per-turn `MonitorScore` records using whitelisted visible traffic. Evaluation returns AUROC per monitor against `tampered_turn` labels, with a sklearn fallback.
- Verification: **48 tests passed** with the requested command; Ruff passed. No commit made.