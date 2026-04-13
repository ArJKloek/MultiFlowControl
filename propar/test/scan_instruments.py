import propar
import sys
import glob


def find_usb_serial_ports():
    """Return a list of likely USB serial ports on Linux/Raspberry Pi."""
    candidates = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return sorted(candidates)


def scan_port(comport):
    print(f"\nScanning {comport}...")
    print("-" * 60)
    try:
        local = propar.instrument(comport)
        nodes = local.master.get_nodes()

        if not nodes:
            print("  No instruments found.")
            return

        print(f"  Found {len(nodes)} instrument(s):\n")
        for node in nodes:
            print(f"    Address  : {node['address']}")
            print(f"    Type     : {node.get('type', 'Unknown')}")
            print(f"    Serial   : {node.get('serial', 'Unknown')}")
            print(f"    Channels : {node.get('channels', 1)}")
            print()

        print("  Reading user tags:")
        for node in nodes:
            address = node['address']
            channels = node.get('channels', 1)
            for ch in range(1, channels + 1):
                instr = propar.instrument(comport, address=address, channel=ch)
                tag = instr.readParameter(115)  # User tag (FlowDDE 115)
                measure = instr.measure
                channel_info = f" ch{ch}" if channels > 1 else ""
                print(f"    Node {address}{channel_info}: tag={tag!r}, measure={measure}")

    except Exception as e:
        print(f"  Error on {comport}: {e}")


# Determine which ports to scan
if len(sys.argv) > 1:
    # Ports passed as arguments: python scan_instruments.py /dev/ttyUSB0 /dev/ttyUSB1
    ports = sys.argv[1:]
else:
    ports = find_usb_serial_ports()
    if not ports:
        print("No USB serial ports found. Trying COM1 as fallback.")
        ports = ['COM1']

print(f"Found {len(ports)} USB serial port(s): {', '.join(ports)}")

for port in ports:
    scan_port(port)

print("\nDone.")
