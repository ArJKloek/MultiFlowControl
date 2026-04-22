# MultiFlowControl

MultiFlowControl is a PyQt5 desktop application for scanning and operating Bronkhorst FLOW-BUS instruments (for example DMFC and DMFM devices) over serial ports.

## Current Status

This repository contains a working scanner and instrument control dialogs, plus early-stage placeholders for graphing and logging.

Implemented:
- Scan available serial ports and discover nodes
- Open one control window per selected node
- Show live measurement values with periodic polling
- Edit user tag and setpoint values on supported devices
- List/select available fluids when reported by the instrument

Not fully implemented yet:
- Graph view behavior (dialog loads, no plotting logic yet)
- Logging backend (menu actions only toggle UI state)

## Requirements

- Python 3.10+ (recommended)
- Windows, Linux, or another OS supported by PyQt5 and pyserial
- A supported Bronkhorst instrument connected over serial

Python dependencies are listed in requirements.txt:
- PyQt5>=5.15,<6
- pyserial>=3.5

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app from repository root:

```bash
python main.py
```

Primary entrypoint: `main.py`  
Compatibility launcher: `backend/qt5_app.py`

## Operator Workflow (High Level)

1. Open scanner from the main window.
2. Click Scan to discover nodes on available serial ports.
3. Select one or more rows (or leave unselected to connect all found rows).
4. Click Connect to open instrument windows.
5. In each instrument window:
   - Verify identity (address, type, serial)
   - Adjust setpoint (controller-capable devices)
   - Monitor live measurements
   - Reload parameters when needed

## Maintainer Notes

- Poll interval is 100 ms (`backend/constants.py`).
- Device communication uses the local `propar` package and parameter numbers (DDE IDs).
- DMFM devices are treated as meter-only dialogs.

For operational details and troubleshooting, see docs/MAINTAINER_GUIDE.md.

For feature progress planning and weekly implementation tracking, see docs/BUILD_FORM.md.

## Troubleshooting (Quick)

- No instruments found:
  - Check cable, power, and serial permissions.
  - Confirm the instrument is visible as a serial port.
  - On Windows, verify COM port availability.
- Scan or read/write errors:
  - Retry scan after reconnecting hardware.
  - Check that no other process owns the same COM port.
- Unexpected values:
  - Use Reload in the channel dialog.
  - Verify selected fluid and instrument capacity/unit.

## Scope Boundary

This README is intentionally focused on running and operating the current application state. It does not document internal architecture in depth or contribution workflows yet.
