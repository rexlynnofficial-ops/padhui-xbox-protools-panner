#!/bin/bash
cd "$(dirname "$0")"
rm -f pstop
exec > >(tee pad_log.txt) 2>&1
python3 -u pad_sp.py
