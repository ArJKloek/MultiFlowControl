# MultiFlowControl Maintainer Operating Guide

This guide is for maintainers who support users and validate behavior against the current codebase.

## 1. Runtime Entry and Window Flow

- App startup begins in `main.py`, creating `QApplication` and showing `MainWindow`.
- `MainWindow` (`backend/main_window.py`) provides menu actions:
  - Open scanner
  - Show graph
  - Start/Stop logging
- Scanner flow:
  - `NodeViewerDialog` (`backend/node_viewer.py`) scans ports and lists discovered nodes.
  - Accepted selections create one `FlowChannelDialog` per selected node (currently channel=1).

## 2. Scanner Behavior

### 2.1 Port Discovery

`discover_serial_ports()` in `backend/utils.py` resolves ports in this order:
1. `pyserial` discovered ports
2. Linux fallback list (`/dev/ttyUSB*`, `/dev/ttyACM*`) if present
3. Static fallback `COM1`

Implication: Seeing `COM1` in logs does not always mean actual detection succeeded.

### 2.2 Node Table

Columns in `NodeViewerDialog`:
- Port: serial path/name
- Address: FLOW-BUS node address
- Type: reported instrument type string
- Serial: reported serial number
- Channels: reported channel count
- Id: reported node id field

Selection behavior:
- If the user selects rows, only those rows are connected.
- If no row is selected, all discovered rows are connected.

## 3. Channel Dialog Behavior

`FlowChannelDialog` (`backend/flow_channel.py`) loads one of two UIs based on device type text:
- `flowchannel_meter.ui` if type includes `DMFM` (meter-only treatment)
- `flowchannel.ui` otherwise (controller-style controls)

### 3.1 Parameter Reads/Writes

Communication is done via `propar.instrument(...).readParameter()` and `.writeParameter()`.

Common parameters used:
- p8: measured percentage raw
- p9: setpoint raw (controllers)
- p21: capacity
- p24: selected fluid index
- p25: fluid name
- p91: model
- p115: user tag
- p129: unit
- p205: measured flow
- p238: fluid properties flags

### 3.2 Setpoint Synchronization

For non-DMFM dialogs:
- Slider percent, numeric percent, and numeric flow controls are cross-synced.
- Writing setpoint uses p9 with 0..32000 scaling from 0..100%.
- During active user edit (focus/slider drag), automatic UI overwrite from polling is suppressed.

### 3.3 Live Polling

- Poll timer interval is `POLL_INTERVAL_MS` (100 ms currently).
- Poll refresh reads measurement and setpoint values and updates widgets.
- Polling is stopped in `closeEvent`.

### 3.4 Fluid Loading

Fluid list loading procedure:
1. Read original p24.
2. Iterate candidate fluid indices 0..8 by writing p24.
3. Read p25 and p238.
4. Keep items whose p238 bitmask indicates enabled/usable fluid.
5. Restore original p24 and selection.

Impact:
- Fluid loading performs temporary writes to p24.
- Status messages may show multiple write operations while populating the list.

## 4. Main Window Feature State

`backend/main_window.py` status by action:
- Open scanner: implemented
- Show graph: opens dialog only
- Start logging / Stop logging: toggles action state and status bar text only

`backend/graph_dialog.py` currently sets static status text and close behavior; no plotting pipeline yet.

## 5. Operational Troubleshooting

### 5.1 Scan Finds Nothing

Checklist:
- Confirm instrument power and bus wiring
- Confirm serial adapter is recognized by OS
- Verify user permissions for serial device
- Ensure no other software has the port open
- Retry scan after reconnecting adapter

### 5.2 Read/Write Failures in Channel Dialog

Symptoms appear in status field as read/write failures with parameter IDs.

Likely causes:
- Port dropped or unstable physical connection
- Address mismatch or wrong node selected
- Concurrent access to same serial port
- Unsupported parameter for the connected instrument

### 5.3 Inconsistent UI Values

- Use Reload to refresh static fields and limits.
- Verify capacity and unit values read from the instrument.
- Confirm fluid selection did not change unexpectedly.

## 6. Known Limitations

- Graphing is placeholder-level.
- Logging backend is not implemented.
- Channel handling in main window is currently fixed to channel 1 when opening dialogs.
- Error messaging is direct and technical; no user-friendly translation layer yet.

## 7. Fast Code Map

- Startup: `main.py`
- Main shell/actions: `backend/main_window.py`
- Scanner/discovery: `backend/node_viewer.py`, `backend/utils.py`
- Channel control/polling: `backend/flow_channel.py`
- Graph placeholder: `backend/graph_dialog.py`
- Poll constants/ui roots: `backend/constants.py`

## 8. Suggested Next Documentation Additions

1. Add an architecture note for data/control flow between dialogs.
2. Add a parameter reference appendix from `propar/parameters.py` for the IDs used by this app.
3. Add release notes section tracking what is fully implemented versus placeholder.
