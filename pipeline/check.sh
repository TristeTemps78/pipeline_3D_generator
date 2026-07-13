#!/bin/bash
# QA statique en UNE commande, sans bpy ni rendu (~5 s) : à lancer avant tout commit.
# 1. compile tout le Python ; 2. cohérence des specs (shots, matériaux, builders, lois GVL) ;
# 3. audit compact (poids, renders orphelins, agents sans model:).
set -e
cd "$(dirname "$0")/.."

python3 -m py_compile pipeline/run.py pipeline/bx/*.py pipeline/gvl/*.py research/tests/*.py
echo "✓ py_compile"

python3 - <<'EOF'
import json, re, sys, glob
mat_defs = set(re.findall(r'^def (\w+)\(', open('pipeline/bx/materials.py').read(), re.M))
law_defs = set(re.findall(r'^def (\w+)\(', open('pipeline/gvl/laws.py').read(), re.M))
errs = []
for sp in sorted(glob.glob('specs/*.json')):
    s = json.load(open(sp))
    ids = [p.get('id') or f"{p['type']}_{i}" for i, p in enumerate(s.get('parts', []))]
    mats = set(s.get('materials', {}).keys())
    for name, m in s.get('materials', {}).items():
        if m.get('builder') and m['builder'] not in mat_defs:
            errs.append(f"{sp}: builder '{m['builder']}' absent de bx/materials.py")
    for shot in s.get('scene', {}).get('shots', []) or []:
        fp = shot.get('frame_part')
        if fp and not any(i == fp or i.startswith(fp + '_') for i in ids):
            errs.append(f"{sp}: shot '{shot.get('id')}' frame_part '{fp}' ne matche aucun id de parts")
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == 'law' and isinstance(v, str) and v not in law_defs:
                    errs.append(f"{sp}: loi GVL '{v}' absente de gvl/laws.py")
                if k.endswith('mat') and isinstance(v, str) and v not in mats:
                    errs.append(f"{sp}: matériau '{v}' (clé {k}) absent de la section materials")
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(s.get('parts'))
if errs:
    print('\n'.join('✗ ' + e for e in errs)); sys.exit(1)
print(f"✓ specs cohérentes ({len(glob.glob('specs/*.json'))} fichiers)")
EOF

bash pipeline/audit.sh
