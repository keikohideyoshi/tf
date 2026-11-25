#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$(realpath -- "$0")")"
mkdir -p ~/.local/share/applications
python - <<'PY'
from pathlib import Path
p=Path.cwd(); esc=lambda s:s.replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`').replace('%','%%')
(Path.home()/'.local/share/applications/tf-nexus.desktop').write_text(f'[Desktop Entry]\nType=Application\nName=TF Nexus\nExec="{esc(str(p/"start.sh"))}"\nIcon={p}/assets/portal.svg\nTerminal=false\nCategories=Game;Utility;\n')
PY
