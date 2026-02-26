# Wacom Pen Button Remapper

ADVISORY: THIS IS COMPLETELY VIBE-CODED. BUT IT DID MAKE THE THINKPAD YOGA 4TH GEN STYLUS ERASER USABLE IN RNOTE.

Remaps the Wacom stylus eraser proximity event (`BTN_TOOL_RUBBER`) to a standard button press (`BTN_STYLUS2`).

## Problem

Some Wacom pen-enabled devices (e.g. Lenovo Yoga with built-in Wacom digitizer) implement the first stylus button as an eraser proximity sensor (`BTN_TOOL_RUBBER`) rather than a normal button press. This causes issues because:

- The button triggers a tool type change (pen → eraser) instead of a button press
- GNOME/Mutter intercepts tool type changes differently than button presses
- Apps like [Rnote](https://github.com/flxzt/rnote) can't map it as a configurable stylus button

## Solution

A Python evdev script that:

1. Grabs the raw Wacom pen input device exclusively
2. Creates a virtual device (`Wacom Pen Remapped`) that mirrors the original
3. Converts `BTN_TOOL_RUBBER` proximity events into `BTN_STYLUS2` button presses
4. Defers `BTN_TOOL_PEN` leave events by one frame to handle the case where `BTN_TOOL_PEN=0` and `BTN_TOOL_RUBBER=1` arrive in separate sync frames
5. Forwards all other events unchanged

## Requirements

- Python 3
- [python-evdev](https://python-evdev.readthedocs.io/) (`pip install evdev`)
- Root access (for grabbing input devices and creating UInput devices)

## Installation

```bash
# Copy the script
sudo cp wacom-remap.py /usr/local/bin/wacom-remap.py
sudo chmod +x /usr/local/bin/wacom-remap.py

# Install the systemd user service
cp wacom-remap.service ~/.config/systemd/user/wacom-remap.service
systemctl --user enable --now wacom-remap.service
```
Then in your drawing app, map "Stylus button 2" to the desired action (e.g. eraser).

## Tested on

- Lenovo Yoga with Wacom pen and multitouch sensor (056a:51b9)
- Fedora with GNOME 49 / Mutter 49
- Rnote 0.13.1 (Flatpak)
