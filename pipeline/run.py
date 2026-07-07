"""Entrée du pipeline : python3 pipeline/run.py forge <spec.json> [--fast]
Construit la scène depuis la spec, rend une image, met à jour l'état de session."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

from bx import core, organic  # noqa: E402

STATE = os.path.join(ROOT, 'pipeline', 'state', 'session.json')


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"step": 0, "spec": None, "last_render": None, "feedback": []}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, 'w') as f:
        json.dump(st, f, indent=1)


def forge(spec_path, fast=False):
    with open(spec_path) as f:
        spec = json.load(f)
    st = load_state()
    st['step'] += 1
    n = organic.build(spec)
    out = os.path.join(ROOT, 'renders', f"step_{st['step']:03d}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    res, samples = ((640, 480), 16) if fast else ((1152, 864), 48)
    core.render(out, res=res, samples=samples)
    blend = os.path.join(ROOT, 'renders', 'scene.blend')
    core.save_blend(blend)
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(f"OK objets={n} rendu={out}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'forge'
    if cmd == 'forge':
        forge(sys.argv[2], fast='--fast' in sys.argv)
    else:
        sys.exit(f"commande inconnue: {cmd}")
