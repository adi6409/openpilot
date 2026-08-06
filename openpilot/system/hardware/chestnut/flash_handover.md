# Chestnut flasher — production validation record

Status: validated 2026-08-05 on the 10-eGPU rack (final results at the bottom).

## What ships

- `flash.py` — minimal data-USB-only flasher, stdlib only, runs as root (self-execs sudo)
- `firmware_wrapped.bin` — pinned `bef953a4` (`fix-usb-serdes-tuning`, "usb: use stable SerDes tuning values"),
  9207 bytes, sha256 `88a4c169234cd858ca70d268a2bb7bab68cba87c07f88685d11c3bfcb49c43d0`, byte-reproducible with sdcc
- `test_flash.py` — image validation, pin consistency, corruption rejection
- hardwared `Chestnut` class — spawns the flasher offroad-only when the enumerated Chestnut product string
  mismatches `custom bef953a4-CLEAN`, max 3 attempts per boot, subprocess so hardwared never blocks

## Two flash paths, one script

1. **Running custom firmware** (product `custom <hash>-CLEAN`): EP0 E4/E5 SPI protocol. Reads and preserves the
   per-device 0x100 config (backed up to `/data/asm_flash_backups/<hostname>.config.bin`, existing backup is
   canonical), programs only changed 4K sectors, verifies per page, per sector, and with a final triple
   stable-read of the span.
2. **ROM bootloader fallback** (an interrupted flash leaves an invalid image; the ASM2464 mask ROM then
   enumerates with config-page-0 IDs `add1:0001` and the misleading product string `USB 3.2 PCIe TinyEnclosure`):
   the E4/E5 protocol stalls here. The flasher detects this state and uses the ROM's BOT vendor protocol
   (`E1 50` config pages, `E3 50/D0` image, `E8 51` commit) with the config restored from the backup.
   Two hard-won requirements: a USB port reset first (fresh link train, otherwise every bulk transfer stalls on
   the comma xHCI — this is why stock flashing was previously believed impossible from the comma), and no
   zero-length `E3 D0` (its CSW errors; part2 is only sent when the image exceeds 0xFF00).

After either path: VBUS cycle activation. Bus-powered Chestnuts hard-reset and re-enumerate with the new
firmware, verified by product string; externally powered ones are reported honestly ("activates on its next
power cycle") and reruns converge as no-ops. After a stock recovery the script falls through to a full E4/E5
readback verification of the flashed image.

## Safety model

- modeld is `only_onroad` and only claims the Chestnut when the product string matches the pin; the flasher only
  runs on mismatch: mutual exclusion by product string, no lock contention by construction
- all retry loops share a 600 s budget (`FLASH_BUDGET`), then exit nonzero for the next attempt to converge
- SIGINT/SIGTERM/SIGHUP deferred only during the destructive window; SIGKILL mid-program is a validated
  recovery case (ROM fallback path)
- worst interruption case converges unattended: kill/disconnect mid-program → next power cycle boots ROM
  fallback → hardwared sees mismatch offroad → flasher recovers over data USB → activation → verify

## Rack validation (2026-08-05, all 10 devices, serdes fleet)

- normal transitions old `1c3a5754` ↔ new `bef953a4` with VBUS activation and full verification
- link-cut (usbfs deauthorize) mid-program: in-process reconnect recovery to `VERIFY OK`
- SIGKILL mid-program + power cycle → ROM fallback → unattended data-USB recovery → activation → `VERIFY OK`
- externally powered units (`d05bb90f`, `de2e7866`): same matrix with FTDI power cycles standing in for real
  power cycles (test rig only; the flasher itself used only data USB)
- forced verify passes on the whole fleet; final fleet state `custom bef953a4-CLEAN` at 5 Gb/s

## Car power classes (simulated with the rack's Tapo GPU outlets)

- The ASM stays enumerated on comma VBUS when external GPU power is off: ignition-switched 12V ports do not hide
  the chestnut offroad, flashing works in both car classes.
- On standard chestnuts the VBUS cycle resets the ASM regardless of external power, so activation is fully
  automatic in both classes.
- The two back-powered test boards (`d05bb90f`, `de2e7866`) ride through VBUS cycles; for that hardware the
  flasher reports deferred activation and hardwared raises the `Offroad_ChestnutPowerCycle` alert until the
  product string matches after a real power cycle.

Campaign logs: rack PC `~/chestnut_campaign_*/`, `~/external*.log`, mirrored to
`chestnut-rack-validation-20260805/` in this repo.
