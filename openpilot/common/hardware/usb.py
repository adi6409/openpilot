import ctypes
import fcntl
import os
from pathlib import Path

CHESTNUT_FW_VERSION = "bef953a4"
CHESTNUT_USB_IDS = ((0xADD1, 0x0001), (0x3801, 0x0001))
USB_DEVICES_PATH = Path("/sys/bus/usb/devices")
USBDEVFS_CONTROL = 0xC0185500
PCIE_LTSSM_REG = 0xB450  # 0x78 = L0, link to the GPU is up


class _Ctrl(ctypes.Structure):
  _fields_ = [("request_type", ctypes.c_uint8), ("request", ctypes.c_uint8),
              ("value", ctypes.c_uint16), ("index", ctypes.c_uint16),
              ("length", ctypes.c_uint16), ("timeout", ctypes.c_uint32),
              ("data", ctypes.c_void_p)]


def chestnut_status(busnum: int, devnum: int) -> tuple[int, bool]:
  # EP0 reads of supply voltage and PCIe LTSSM state, only answered by the custom firmware
  try:
    fd = os.open(f"/dev/bus/usb/{busnum:03d}/{devnum:03d}", os.O_RDWR)
  except OSError:
    return 0, False
  try:
    # hw_status_t: voltage u16, current s16, plus firmware-version-dependent extras
    status = (ctypes.c_ubyte * 16)()
    fcntl.ioctl(fd, USBDEVFS_CONTROL, _Ctrl(0xC0, 0xC0, 0, 0, 16, 100, ctypes.cast(status, ctypes.c_void_p)))
    ltssm = (ctypes.c_ubyte * 1)()
    fcntl.ioctl(fd, USBDEVFS_CONTROL, _Ctrl(0xC0, 0xE4, PCIE_LTSSM_REG, 0, 1, 100, ctypes.cast(ltssm, ctypes.c_void_p)))
    return int.from_bytes(bytes(status[:2]), "little"), ltssm[0] == 0x78
  except OSError:
    return 0, False
  finally:
    os.close(fd)


def get_usb_topology() -> set[str]:
  try:
    return set(os.listdir(USB_DEVICES_PATH))
  except OSError:
    return set()


def read(path: Path) -> str | None:
  try:
    return path.read_text().strip()
  except OSError:
    return None


def read_int(path: Path, base: int = 10) -> int:
  try:
    return int(path.read_text(), base)
  except (OSError, ValueError, TypeError):
    return 0


def usb_devices() -> list[Path]:
  try:
    devices = (d for d in USB_DEVICES_PATH.glob("*") if (d / "idVendor").exists())
    return sorted(devices, key=lambda p: p.name)
  except OSError:
    return []


def controller(device: Path) -> Path | None:
  try:
    return next((parent for parent in device.resolve().parents if parent.name.endswith(".ssusb")), None)
  except OSError:
    return None


def get_usb_state() -> list[dict]:
  devices = []
  for device in usb_devices():
    vendor_id = read_int(device / "idVendor", 16)
    product_id = read_int(device / "idProduct", 16)
    ctrl = controller(device)
    devices.append({
      "busnum": read_int(device / "busnum"),
      "devnum": read_int(device / "devnum"),
      "vendorId": vendor_id,
      "productId": product_id,
      "speedMbps": read_int(device / "speed"),
      "manufacturer": read(device / "manufacturer") or "",
      "product": read(device / "product") or "",
      "linkErrorCount": read_int(ctrl / "portli", 0) & 0xFFFF if ctrl is not None else 0,
    })
  return devices


def set_usb_state(device_state, devices: list[dict]) -> None:
  entries = device_state.usbState.init('devices', len(devices))

  chestnut_present = False
  for entry, device in zip(entries, devices, strict=True):
    entry.busnum = device["busnum"]
    entry.devnum = device["devnum"]
    entry.vendorId = device["vendorId"]
    entry.productId = device["productId"]
    entry.speedMbps = device["speedMbps"]
    entry.manufacturer = device["manufacturer"]
    entry.product = device["product"]
    entry.linkErrorCount = device["linkErrorCount"]

    if (entry.vendorId, entry.productId) in CHESTNUT_USB_IDS:
      chestnut_present = True

  device_state.chestnutPresent = chestnut_present
