"""Harnais commun des tests de convergence : chemins, logs JSON, rendu clay rapide.
Chaque test écrit research/logs/<test>.json + renders éventuels dans research/renders/."""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

import bpy  # noqa: E402
from bx import core  # noqa: E402

LOGS = os.path.join(ROOT, 'research', 'logs')
RENDERS = os.path.join(ROOT, 'research', 'renders')
os.makedirs(LOGS, exist_ok=True)
os.makedirs(RENDERS, exist_ok=True)


def log(test, data):
    data = {'test': test, 'bpy': bpy.app.version_string,
            'date': time.strftime('%Y-%m-%d %H:%M:%S'), **data}
    path = os.path.join(LOGS, f'{test}.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=1)
    print(f'LOG → {path}')
    print(json.dumps(data, indent=1))
    return data


def clay_render(name, cam_loc=(9, -7, 4), target=(0, 0, 1.5), res=(640, 480), samples=16):
    core.clay()
    core.camera(cam_loc, target=target)
    out = os.path.join(RENDERS, f'{name}.png')
    core.render(out, res=res, samples=samples)
    return out


class timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.dt = round(time.perf_counter() - self.t0, 3)
