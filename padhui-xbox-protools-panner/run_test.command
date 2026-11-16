#!/bin/bash
cd "$(dirname "$0")"
exec > >(tee run_log.txt) 2>&1
echo "== python: $(which python3) $(python3 --version)"
python3 -m pip install --user --quiet mido python-rtmidi pygame || python3 -m pip install --user --break-system-packages --quiet mido python-rtmidi pygame
python3 -c "import mido,rtmidi;print('deps ok')"
python3 -u pad_hui.py --sim
