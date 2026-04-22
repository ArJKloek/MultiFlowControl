# Build Form

Use this form to track what is implemented, what is in progress, and what comes next.

## 1. Reusable Template

### Project Info
- Version:
- Date:
- Owner:
- Goal of this version:

### Already Implemented
- [x] GUI startup via `main.py` and main window with menu actions
- [x] Serial port scanning and node discovery
- [x] Scanner dialog with node table (Port, Address, Type, Serial, Channels, Id)
- [x] Connect flow from scanner to channel dialog per selected node
- [x] DMFM (meter-only) vs DMFC (controller) dialog mode detection
- [x] Live polling of measurement values every 100 ms
- [x] Setpoint controls with percent slider, percent spinbox, and flow spinbox (cross-synced)
- [x] Fluid list loading from device and fluid selection/switching
- [x] User tag read/write
- [x] Reload button to refresh all parameters from device
- [x] Advanced settings toggle (show/hide advanced frame)
- [x] Status/error messages in channel dialog

### In Progress
- [ ] Feature:Adding logging
	- Current state: not working yet
	- Missing:
- [ ] Feature:
	- Current state:
	- Missing:

### Planned Next
1. Logging for instruments
2. Error logging
3. 

### Blockers / Risks
- 
- 

### Done Criteria
- [ ]
- [ ]
- [ ]

### Notes / Decisions
- 
- 

---

## 2. Current Example (MultiFlowControl)

### Project Info
- Version: v0.1
- Date: 2026-04-19
- Owner: MultiFlowControl team
- Goal of this version: deliver a stable scan-to-connect-to-control workflow for Bronkhorst serial instruments.

### Already Implemented
- [x] GUI startup via `main.py` and main window actions
- [x] Serial scanning and node discovery
- [x] Connect flow from scanner to channel dialog(s)
- [x] Live polling and measurement display
- [x] Setpoint controls for controller-capable devices
- [x] Fluid list loading and fluid selection behavior

### In Progress
- [ ] Feature: Logging
	- Current state: Start/Stop menu actions exist and toggle UI state.
	- Missing: data capture loop, persistent file output, session metadata.
- [ ] Feature: Graphing
	- Current state: graph dialog opens with placeholder status text.
	- Missing: real-time plotting, signal pipeline, chart controls/history.

### Planned Next
1. Implement logging backend first (CSV output and basic session handling).
2. Connect live measurement stream to graph dialog for real-time plotting.
3. Improve user-facing status/error messages and add inline help text.

### Blockers / Risks
- Serial port contention with other software can break read/write reliability.
- Device-specific parameter support can vary between instrument types.
- Multi-channel behavior is not fully exposed in main window workflow yet.

### Done Criteria
- [ ] Logging writes measurement data to file during active sessions.
- [ ] Graph dialog shows live measurement values over time.
- [ ] Core workflow is documented and reproducible: scan, connect, control.

### Notes / Decisions
- Logging is prioritized before graph polishing.
- Keep first logging release simple (CSV only) before adding formats/options.
