#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
read -r -e -p 'A meglévő TF Nexus könyvtára: ' target
target=${target/#\~/$HOME}
[[ -f "$target/main.py" && -f "$target/config.json" ]] || { echo 'Nem található a Nexus.'; exit 1; }
exec 9>"$target/.nexus.lock"
flock -n 9 || { echo 'Előbb zárd be a Nexust.'; exit 1; }
backup="$target/backup-1.2-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
for f in main.py config.json rounds.py pantheon.py bookmarks.py README.md; do
    if [[ -f "$target/$f" ]]; then cp -a "$target/$f" "$backup/"; fi
done
cp main.py rounds.py pantheon.py bookmarks.py "$target/"
mkdir -p "$target/assets/pantheon"
cp assets/pantheon/*.svg "$target/assets/pantheon/"
cp README.md "$target/README.md"
echo "Frissítve. Mentés: $backup"
