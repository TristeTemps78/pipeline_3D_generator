#!/usr/bin/env bash
# Bootstrap d'un conteneur neuf pour la pipeline (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY' || pip install --quiet bpy
import bpy  # noqa: F401
print("bpy déjà présent :", bpy.app.version_string)
PY

python3 -c "import bpy; print('bpy OK', bpy.app.version_string)"
echo "Prêt. Commandes : python3 pipeline/run.py forge|compare|validate|sheet <spec> ..."
