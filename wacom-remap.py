#!/usr/bin/env python3
"""
Wacom Pen Eraser Button Remapper
Converts eraser proximity events to BTN_STYLUS2 button presses.
Defers pen proximity leave by one frame to correctly handle the case
where BTN_TOOL_PEN=0 and BTN_TOOL_RUBBER=1 arrive in separate frames.
"""

import evdev
from evdev import InputDevice, UInput, ecodes
import sys

def find_wacom_pen():
    devices = [InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if 'pen' in device.name.lower() and 'wacom' in device.name.lower():
            return device
    return None

def remap_pen_buttons():
    pen = find_wacom_pen()
    if not pen:
        print("Error: Wacom pen device not found!")
        sys.exit(1)

    print(f"Found pen device: {pen.name}")

    pen.grab()

    capabilities = pen.capabilities(absinfo=True)
    if ecodes.EV_SYN in capabilities:
        del capabilities[ecodes.EV_SYN]
    if ecodes.EV_KEY in capabilities:
        key_events = list(capabilities[ecodes.EV_KEY])
        if ecodes.BTN_STYLUS2 not in key_events:
            key_events.append(ecodes.BTN_STYLUS2)
        capabilities[ecodes.EV_KEY] = key_events

    try:
        ui = UInput(capabilities, name="Wacom Pen Remapped", vendor=pen.info.vendor,
                    product=pen.info.product, version=pen.info.version)
    except Exception as e:
        print(f"Error creating UInput device: {e}")
        pen.ungrab()
        sys.exit(1)

    eraser_active = False
    suppress_next_pen_enter = False
    # Deferred pen leave: held for one frame to check if eraser follows
    pending_pen_leave = False
    pending_pen_leave_ready = False  # True after one SYN_REPORT has passed

    try:
        for event in pen.read_loop():
            # --- Handle BTN_TOOL_PEN=0: defer it ---
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOOL_PEN and event.value == 0:
                pending_pen_leave = True
                pending_pen_leave_ready = False
                continue

            # --- Handle BTN_TOOL_PEN=1 ---
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOOL_PEN and event.value == 1:
                if suppress_next_pen_enter:
                    # After eraser release: pen never left on virtual device, skip
                    suppress_next_pen_enter = False
                    pending_pen_leave = False
                    continue
                if pending_pen_leave:
                    # Pen left and re-entered without eraser: cancel both
                    pending_pen_leave = False
                    pending_pen_leave_ready = False
                    continue
                # Normal pen enter
                ui.write(event.type, event.code, event.value)
                continue

            # --- Handle BTN_TOOL_RUBBER ---
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOOL_RUBBER:
                if event.value == 1 and not eraser_active:
                    # Eraser button pressed: cancel deferred pen leave, emit button
                    pending_pen_leave = False
                    pending_pen_leave_ready = False
                    ui.write(ecodes.EV_KEY, ecodes.BTN_STYLUS2, 1)
                    ui.syn()
                    eraser_active = True
                elif event.value == 0 and eraser_active:
                    # Eraser button released
                    ui.write(ecodes.EV_KEY, ecodes.BTN_STYLUS2, 0)
                    ui.syn()
                    eraser_active = False
                    suppress_next_pen_enter = True
                continue

            # --- Handle SYN_REPORT: flush deferred pen leave if one frame passed ---
            if event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if pending_pen_leave and pending_pen_leave_ready:
                    # One full frame passed with no BTN_TOOL_RUBBER: real pen leave
                    ui.write(ecodes.EV_KEY, ecodes.BTN_TOOL_PEN, 0)
                    ui.syn()
                    pending_pen_leave = False
                    pending_pen_leave_ready = False
                elif pending_pen_leave:
                    # First SYN_REPORT after pen leave: wait one more frame
                    pending_pen_leave_ready = True
                ui.write(event.type, event.code, event.value)
                continue

            # --- Forward everything else ---
            ui.write(event.type, event.code, event.value)

    except KeyboardInterrupt:
        print("\nStopping remapper...")
    finally:
        pen.ungrab()
        ui.close()

if __name__ == "__main__":
    remap_pen_buttons()
