import propar
import sys

# COM port to scan - change this to match your setup
COMPORT = 'COM1'

if len(sys.argv) > 1:
    COMPORT = sys.argv[1]

print(f"Scanning for instruments on {COMPORT}...")
print("-" * 60)

try:
    # Create an instrument instance to establish a master on the port
    local = propar.instrument(COMPORT)

    # Scan the network for all connected nodes
    nodes = local.master.get_nodes()

    if not nodes:
        print("No instruments found.")
    else:
        print(f"Found {len(nodes)} instrument(s):\n")
        for node in nodes:
            print(f"  Address  : {node['address']}")
            print(f"  Type     : {node.get('type', 'Unknown')}")
            print(f"  Serial   : {node.get('serial', 'Unknown')}")
            print(f"  Channels : {node.get('channels', 1)}")
            print()

        # Create an instrument instance for each found node and read user tag
        print("-" * 60)
        print("Reading user tags:")
        for node in nodes:
            address = node['address']
            channels = node.get('channels', 1)
            for ch in range(1, channels + 1):
                instr = propar.instrument(COMPORT, address=address, channel=ch)
                tag = instr.readParameter(115)  # User tag (FlowDDE 115)
                measure = instr.measure
                channel_info = f" ch{ch}" if channels > 1 else ""
                print(f"  Node {address}{channel_info}: tag={tag!r}, measure={measure}")

except Exception as e:
    print(f"Error: {e}")
    print(f"Make sure the instrument is connected on {COMPORT} and the port is available.")
    sys.exit(1)
