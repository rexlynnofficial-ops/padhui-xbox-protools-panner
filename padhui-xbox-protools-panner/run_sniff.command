#!/bin/bash
cd "$(dirname "$0")"
exec > >(tee sniff_log.txt) 2>&1
python3 -u sp_sniff.py
