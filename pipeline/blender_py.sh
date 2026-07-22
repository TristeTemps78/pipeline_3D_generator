#!/usr/bin/env bash
# Lance un script Python ARBITRAIRE dans le Blender installe (pendant de blender_run.sh,
# qui lui est cable sur run.py). Sert aux outils qui pilotent leur propre boucle de
# rendu — typiquement l'animation, qui construit et rend N images d'affilee.
# Usage : bash pipeline/blender_py.sh <script.py> [args...]
BLENDER="${BLENDER:-C:/Program Files/Blender Foundation/Blender 5.1/blender.exe}"
script="$1"; shift
exec "$BLENDER" --background --python "$script" -- "$@"
