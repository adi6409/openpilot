# Volvo ESR simulation-input vehicle test runbook

This branch automatically starts a bounded radar simulation when openpilot
requests sustained braking while stock ACC is active. The one-shot diagnostic
trigger remains available for a controlled experiment.

Below 30 km/h, it may also show a conservative moving lead while stock ACC
is available but not enabled, so the driver can press SET. That pre-SET lead
retires when SET is pressed, stock ACC enables, a pedal is pressed, a native
lead appears, the radar phase is lost, or its 15-second window expires.

## Preconditions

Install the root openpilot build and the matching signed Panda firmware as one
versioned deployment. Before driving, verify:

- Volvo safety is selected and the Panda has no faults;
- the car is stationary, controls are disallowed, and the services are healthy;
- the running controller imports `opendbc.car.volvo.virtual_target`;
- the local source hashes and Panda firmware hash match the deployed files.

No supplied historical route contains a real `0x5C0` experiment, so this test
must be treated as the first production-ESR acceptance test.

## Trigger

On a controlled straight road with a safety driver ready to brake, engage stock
ACC and wait until the vehicle is between 4.5 and 17.5 m/s. Keep both pedals
clear. The effective on-wire `FSM3` request must be at or below -0.72 m/s².

From an SSH shell on the device, set the development-only parameter once:

```sh
cd /data/openpilot
python -m openpilot.common.params VolvoRadarSimulationTrigger 1
```

The controller consumes and clears the parameter. Normal automatic braking
uses the same speed, pedal, stock ACC, Panda lease, and phase gates.

## Required evidence

Save the complete route and verify all of the following from the same time
window:

- host `sendcan` contains the `0x5C1` authorization and `0x5C0` lifecycle;
- Panda-returned bus-1 traffic contains the accepted `0x5C0` lifecycle;
- the physical ESR sweep, selectors, native bus-2 `FSM0/FSM1/FSM3/FSM4`,
  speed, pedals, brake command, pressure, and ACC state are present;
- no userspace `TargetN`, `FSM0`, `FSM1`, or `FSM4` spoofing is present;
- the lifecycle counters report authorization, attempted/retired frames,
  Panda-returned frames, adoption evidence, physical response, and any safety
  cancel.

If the radar does not return or coherently select the simulated target, stop
the test. Do not compensate by reintroducing downstream fused-message or
`TargetN` spoofing.

The first run is radar-only evidence collection. Do not use a successful
dashboard lead indication as proof of brake authority or collision safety.
