#!/bin/bash
cd "$(dirname "$0")"
exec > >(tee mouse_log.txt) 2>&1
python3 -m pip install --user --quiet pygame pyobjc-framework-Quartz pyobjc-framework-Cocoa
python3 -u pad_mouse.py
