#!/usr/bin/env bash
# run.py via le Blender INSTALLÉ (local Windows : pas de wheel bpy pip — ARM64/Py3.14).
# Usage : bash pipeline/blender_run.sh <cmd> <spec> [flags]   (mêmes args que run.py)
# Le bpy vient du Python embarqué de Blender ; natif ARM64 = plus rapide que le conteneur.
BLENDER="${BLENDER:-C:/Program Files/Blender Foundation/Blender 5.1/blender.exe}"
exec "$BLENDER" --background --python "$(dirname "$0")/run.py" -- "$@"
