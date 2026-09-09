# Volvo upstream integration — 2026-09-09

The local `volvo` branch incorporates upstream openpilot `master` at
`d70df6736625c88d87fe301b93359d117ea9221e` (187 upstream commits since the
fork's base). This is the current development branch, not a prebuilt release.
The original checkout is preserved as `backup/volvo-before-upstream-20260909`.

The openpilot merge is `f4c486421`. Its opendbc dependency is the local merge
`1fc68e39d76659efa181376c02e4496c023748ac`, incorporating upstream's pinned
`b4ef5e1cf406ff143fa67bdbfb154739d43279c9` while preserving the Volvo port.
Both merges are local; nothing has been pushed or installed on a vehicle.
The opendbc merge must be made available in the fork before publishing a
parent revision that references it.

## Compatibility changes

- Preserve the Volvo V60 fingerprint and `adi6409/opendbc` submodule URL.
- Retain both Volvo and upstream MG in the platform registry.
- Align Volvo's schema enum and C safety registration with upstream's
  reserved Volvo ID 36. Upstream assigns ID 35 to BYD. Existing Volvo safety
  checks and controller limits are preserved. Vehicle software and panda
  firmware must use the matching merged dependency; old cached CarParams
  and historical logs require care because the numeric mapping changed.
- Supply upstream's required firmware response format using the format of
  the Volvo firmware entry already present in the fork.

## Stop-and-go findings

The update includes upstream commit `3d09a47a4`, "cruise planner: fix decel
jerk from cruise." It resets cruise acceleration with the planner state
and applies cruise jerk limiting in experimental mode as well. This may
help transitions, but no route replay establishes that it fixes the
reported behavior.

The existing Volvo controller switches between stock ACC acceleration and
openpilot acceleration during takeoff. Investigation should compare pedal
state, planner targets, actual acceleration, stock ACC requests, and the
transmitted commands around the reported events. No custom tuning or
Kapara profile was added, and no safety limits were relaxed.

## Validation

- Volvo safety suite: 32 tests ran, 24 passed and 8 skipped by the suite.
- Volvo CAN helpers and upstream Volvo interface test: 4 passed.
- Firmware response format validation across the database: 1 passed.
- Longitudinal control state transitions: 2 passed.
- Merged cereal schemas and Volvo CarParams loaded successfully; Volvo's
  safety-model value is 36.
- Ruff passed for the changed platform registry and Volvo values module.
- Native parameter library and message IPC extension compiled on macOS.
- The longitudinal MPC build stopped at an upstream build command that
  does not quote the space in `/Volumes/Extreme SSD`. Planner simulations,
  a full device build, and hardware validation are therefore outstanding.

Validation used a temporary environment at `/tmp/openpilot-volvo-validation`
with the repository's frozen dependency lock. Test and build logs are in
`/tmp/openpilot-*.log`. The integration is not validated for vehicle use.
