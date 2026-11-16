#!/bin/bash
cd "$(dirname "$0")"
exec > >(tee tap_log.txt) 2>&1
python3 -u sp_tap.py
