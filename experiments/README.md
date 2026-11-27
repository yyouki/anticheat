# Non-production experiments

This directory is intentionally separate from include/ac.inc. Nothing here is compiled into the production framework.

| Experiment | Reason for isolation | Promotion gate |
| --- | --- | --- |
| C/C++ native module | Adds ABI, platform binaries and crash surface | Measured Pawn bottleneck, fuzz tests, OS/architecture matrix, parity tests and rollback |
| Rust sidecar or FFI | Adds toolchain, ABI and deployment complexity | Stable bounded-latency protocol, resource limits, memory-safety review and cross-platform CI |
| ML behavioural model | Risks dataset bias, drift and opaque verdicts | Labelled representative desktop/mobile/network data, held-out evaluation, calibration and explainability |
| Packet polling | Risks extra per-player CPU and false positives | Verified packet-loss source, bounded sample frequency, cost benchmark and jitter tests |
| Pathfinding | Map geometry, interiors and dynamic objects create legal exceptions | Authoritative map model, route corpus, CPU bound and full legitimate-transition allowlist |
| Client memory checks | Offsets vary across client versions and architectures | Version-specific profiles, negative tests, mobile support and safe handling of missing responses |

A result is not production-ready until the review, runtime, false-positive, performance and adversarial gates pass.
