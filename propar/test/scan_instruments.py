import propar
import sys
import glob
import time
from datetime import datetime

MEASURE_INTERVAL = 1.0  # seconds between measurements


def find_usb_serial_ports():
    """Return a list of likely USB serial ports on Linux/Raspberry Pi."""
    candidates = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return sorted(candidates)


def scan_port(comport):
    """Scan a single port and return a list of instrument instances with metadata."""
    instruments = []
    print(f"\n  Scanning {comport}...")
    try:
        local = propar.instrument(comport)
        nodes = local.master.get_nodes()

        if not nodes:
            print(f"  No instruments found on {comport}.")
            return instruments

        print(f"  Found {len(nodes)} node(s) on {comport}:")
        for node in nodes:
            address  = node['address']
            channels = node.get('channels', 1)
            dev_type = node.get('type', 'Unknown')
            serial   = node.get('serial', 'Unknown')
            print(f"    Address={address}  Type={dev_type}  Serial={serial}  Channels={channels}")

            for ch in range(1, channels + 1):
                instr = propar.instrument(comport, address=address, channel=ch)
                tag   = instr.readParameter(115)  # User tag
                label = tag if tag else f"Node{address}"
                if channels > 1:
                    label += f"-ch{ch}"
                instruments.append({
                    'instrument': instr,
                    'label':      label,
                    'port':       comport,
                    'address':    address,
                    'channel':    ch,
                })
                print(f"      ch{ch}: label={label!r}")

    except Exception as e:
        print(f"  Error scanning {comport}: {e}")

    return instruments


def measure_loop(instruments):
    """Continuously read and print measurements from all instruments."""
    print("\n" + "=" * 70)
    print("Starting continuous measurement. Press Ctrl+C to stop.")
    print("=" * 70)

    # Build header
    labels = [i['label'] for i in instruments]
    col_w  = max(len(l) for l in labels + ['Timestamp']) + 2
    header = f"{'Timestamp':<22}" + "".join(f"{l:>{col_w}}" for l in labels)
    print(header)
    print("-" * len(header))

    while True:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row = f"{timestamp:<22}"
        for item in instruments:
            try:
                value = item['instrument'].setpoint
                row += f"{str(value):>{col_w}}"
            except Exception:
                row += f"{'ERR':>{col_w}}"
        print(row)
        time.sleep(MEASURE_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────────────

if len(sys.argv) > 1:
    ports = sys.argv[1:]
else:
    ports = find_usb_serial_ports()
    if not ports:
        print("No USB serial ports found. Trying COM1 as fallback.")
        ports = ['COM1']

print(f"USB serial port(s) to scan: {', '.join(ports)}")

all_instruments = []
for port in ports:
    all_instruments.extend(scan_port(port))

if not all_instruments:
    print("\nNo instruments found on any port. Exiting.")
    sys.exit(1)

print(f"\nTotal instruments found: {len(all_instruments)}")

try:
    measure_loop(all_instruments)
except KeyboardInterrupt:
    print("\nMeasurement stopped.")
