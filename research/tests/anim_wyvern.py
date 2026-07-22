"""OUTIL b28 : ANIMATIONS de la wyverne des glaces — rendu d'une sequence + MP4.

    bash pipeline/blender_py.sh research/tests/anim_wyvern.py <motion> [frames] [--hq]
    motions : flap | flight | turntable | takeoff | all

POURQUOI PAS D'ARMATURE. Le modele est fait de ~90 objets separes (chaque cristal, croc,
griffe et panneau de membrane en est un) : les peser sur un squelette serait long et
fragile. Mais tout, ici, sort de PARAMETRES — une aile, ce sont six points de controle.
Animer revient donc a faire de ces points une fonction du temps et a RECONSTRUIRE la
scene image par image (`core.reset()` + `organic.build()`). C'est brutal mais ca coute
~2 s par image, ca ne demande aucun rig, et ca reste dans la doctrine du projet : la spec
pilote tout.

Le mouvement s'exprime donc en deux blocs seulement :
  - `warp(p, t, motion)` : deplacement applique a TOUT point du modele (respiration,
    onde du cou et de la queue, montee du corps) — les cristaux dorsaux, les crocs et
    l'oeil suivent gratuitement, puisqu'ils sont dans le champ de deplacement ;
  - une rotation d'aile a part, autour de l'axe d'epaule, avec un RETARD croissant vers
    la pointe : c'est ce retard qui fait le fouette d'une aile souple. Sans lui, une
    aile rigide qui monte et descend lit « oiseau en carton ».
"""
import copy
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

import bpy  # noqa: E402
from bx import core, organic  # noqa: E402

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SPEC = os.path.join(ROOT, 'specs', 'wyvern.json')
OUT = os.path.join(ROOT, 'renders', 'anim')

# Reperes anatomiques (unites monde), lus du document de design via la spec construite.
SHOULDER_Y, SHOULDER_Z = -0.15, 2.28   # axe de battement
NECK_Y0, HEAD_Y = 0.30, -3.30          # base du cou -> bout du museau
HIP_Y, TAIL_Y = 1.80, 4.25             # bassin -> bout de la queue
FOOT_Z = 0.05


# --------------------------------------------------------------------- outils
def _rot_y(p, oy, oz, ang):
    """Rotation autour de l'axe Y passant par (0, oy, oz) : c'est l'axe d'epaule,
    donc le plan de battement. Le miroir X de la spec s'occupe de l'aile opposee."""
    c, s = math.cos(ang), math.sin(ang)
    x, y, z = p[0], p[1] - oy, p[2] - oz
    return [x * c + z * s, y + oy, -x * s + z * c + oz]


def _ease(u):
    """Lissage cubique 0->1 (demarrages et arrets sans a-coup)."""
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def _span(y, y0, y1):
    """0 a y0, 1 a y1, borne — sert a ponderer une onde le long du corps."""
    if y1 == y0:
        return 0.0
    return max(0.0, min(1.0, (y - y0) / (y1 - y0)))


# ------------------------------------------------------------- champs de mouvement
def grounded(t, motion):
    """La bete touche-t-elle encore le sol ? (0 = en l'air, 1 = posee)"""
    if motion == 'flight':
        return 0.0
    if motion == 'takeoff':
        return 1.0 - _ease((t - 0.42) / 0.14)
    return 1.0


def warp(p, t, motion):
    """Deplacement applique a TOUT point du modele (hors rotation d'aile)."""
    x, y, z = p
    dz = dy = 0.0
    # PIEDS COLLES AU SOL : sans ca, la respiration du corps souleve aussi les pattes
    # et la bete flotte a 8 cm au-dessus de son ombre a chaque battement. On attenue
    # donc le deplacement vertical vers le bas du modele, tant qu'elle est posee.
    anchor = 1.0 - grounded(t, motion) * (1.0 - _span(z, FOOT_Z, FOOT_Z + 1.30))
    if motion in ('flap', 'flight', 'takeoff'):
        ph = 2.0 * math.pi * t
        # Le corps monte pendant la DESCENTE des ailes (la portance arrive quand
        # l'aile pousse l'air vers le bas), d'ou le dephasage d'un quart de cycle.
        body = 0.085 * math.sin(ph - math.pi / 2.0)
        # Cou et queue : meme onde, mais RETARDEE et amplifiee vers les extremites.
        # C'est ce retard qui fait la souplesse ; en phase, la bete semble d'un bloc.
        neck = _span(y, NECK_Y0, HEAD_Y) ** 1.6
        tail = _span(y, HIP_Y, TAIL_Y) ** 1.6
        dz = (body * anchor
              + 0.30 * neck * math.sin(ph - math.pi / 2.0 - 1.15)
              + 0.42 * tail * math.sin(ph - math.pi / 2.0 - 1.55))
        dy = 0.10 * tail * math.sin(ph - 2.10)      # la queue balaie aussi en longueur
    if motion == 'takeoff':
        dz += takeoff_lift(t)
    return [x, y + dy, z + dz]


def wing_angle(t, reach, motion):
    """Angle de battement d'un point d'aile. `reach` = 0 a l'epaule, 1 a la pointe.

    Deux choses font la difference entre une aile vivante et une planche qui pivote :
    le RETARD (la pointe est en retard d'environ un huitieme de cycle sur l'epaule) et
    l'ASYMETRIE (la descente motrice est plus rapide et plus ample que la remontee, qui
    est une recuperation). Le sinus est donc biaise vers le bas."""
    if motion == 'turntable':
        return 0.0
    lag = 0.17 * reach
    ph = 2.0 * math.pi * (t - lag)
    s = math.sin(ph)
    s = s * (1.0 + 0.30 * max(0.0, -s))          # descente plus ample que la remontee
    amp = math.radians(40.0 if motion != 'takeoff' else 55.0)
    return amp * s * (0.25 + 0.75 * reach)       # l'epaule bouge peu, la pointe beaucoup


def takeoff_lift(t):
    """Decollage : accroupi -> detente -> montee. Non cyclique."""
    if t < 0.30:
        return -0.42 * _ease(t / 0.30)                       # il se ramasse
    if t < 0.48:
        return -0.42 + 0.42 * _ease((t - 0.30) / 0.18)       # detente des pattes
    return 3.4 * _ease((t - 0.48) / 0.52) ** 1.6             # il quitte le sol


def leg_crouch(t, motion):
    """Facteur d'ecrasement de la patte (1 = tendue). Le pied reste au sol : on
    comprime la patte VERS le pied, sinon elle s'enfonce dans le decor."""
    if motion != 'takeoff':
        return 1.0
    if t < 0.30:
        return 1.0 - 0.30 * _ease(t / 0.30)
    if t < 0.48:
        return 0.70 + 0.42 * _ease((t - 0.30) / 0.18)        # detente : elle sur-tend
    return 1.12 - 0.30 * _ease((t - 0.48) / 0.30)            # puis se replie en vol


def apply_pose(spec, t, motion):
    """Deforme une COPIE de la spec pour l'instant t. Aucune connaissance de bpy ici :
    on ne touche que des listes de nombres, donc c'est testable a sec."""
    wing_span = 4.6
    # Le battement SUR PLACE se fait pattes plantees (menace, echauffement) : ne
    # replier qu'en vol reel. Round 1 repliait aussi en `flap` -> pattes detachees.
    tuck = _span(t, 0.48, 0.80) if motion == 'takeoff' else (
        1.0 if motion == 'flight' else 0.0)
    crouch = leg_crouch(t, motion)
    for part in spec['parts']:
        pid = part.get('id', '')
        if pid == 'ground':
            continue
        is_wing = pid.startswith('wing_')
        is_leg = pid.startswith(('leg', 'toe_', 'claw_'))

        def move(p):
            q = list(p)
            if is_wing:
                reach = min(1.0, abs(q[0]) / wing_span)
                q = _rot_y(q, SHOULDER_Y, SHOULDER_Z, wing_angle(t, reach, motion))
            if is_leg:
                # repli des pattes en vol + ecrasement au decollage
                q[2] = FOOT_Z + (q[2] - FOOT_Z) * crouch
                if tuck:
                    # poids 1 au pied, 0 a la hanche : la patte se replie vers
                    # l'arriere et remonte sous le ventre, la hanche ne bouge pas.
                    w = 1.0 - _span(q[2], FOOT_Z, 1.60)
                    q[1] += 0.95 * tuck * w
                    q[2] += 0.60 * tuck * w
            return warp(q, t, motion)

        if 'verts' in part:
            part['verts'] = [move(v) for v in part['verts']]
        if 'pos' in part:
            part['pos'] = move(part['pos'])
    return spec


# ----------------------------------------------------------------------- prises
def camera_for(motion, t, spec):
    """Cadrage par motion. Le turntable est le seul ou la CAMERA tourne ; au decollage
    elle PANORAMIQUE vers le haut, sinon la bete sort du cadre des la montee."""
    if motion == 'turntable':
        a = 2.0 * math.pi * t
        r, h = 14.5, 2.8
        return {'loc': [r * math.cos(a), r * math.sin(a) - 0.3, h],
                'target': [0.0, 0.2, 1.6], 'lens': 50}
    if motion == 'flight':
        return {'loc': [7.5, -15.0, 5.0], 'target': [0.0, 0.0, 6.0], 'lens': 50}
    if motion == 'takeoff':
        rise = max(0.0, takeoff_lift(t))
        return {'loc': [6.2, -13.4, 1.6 + 0.30 * rise],
                'target': [0.0, -0.3, 1.9 + 0.80 * rise], 'lens': 44}
    # battement sur place : cadre large, l'envergure doit tenir tout le cycle
    return {'loc': [6.0, -12.0, 2.4], 'target': [0.0, -0.3, 2.2], 'lens': 42}


def scene_for(motion, spec, t):
    """Variantes de scene : en vol, le sol descend tres bas (la bete est en l'air) et
    le fond s'eclaircit vers le haut — on lit l'altitude par le ciel, pas par le sol."""
    if motion in ('flight', 'takeoff'):
        for part in spec['parts']:
            if part.get('id') == 'ground':
                part['z'] = -14.0 if motion == 'flight' else 0.0
    if motion == 'flight':
        # traversee : la bete file vers -Y, le cadre reste fixe
        shift = 9.0 - 18.0 * t
        for part in spec['parts']:
            if part.get('id') == 'ground':
                continue
            if 'verts' in part:
                part['verts'] = [[v[0], v[1] + shift, v[2] + 5.6] for v in part['verts']]
            if 'pos' in part:
                p = part['pos']
                part['pos'] = [p[0], p[1] + shift, p[2] + 5.6]
    return spec


# ---------------------------------------------------------------------- rendu
def encode(frames_dir, out_mp4, fps):
    """MP4 + GIF depuis la sequence PNG.

    Ce build de Blender est compile SANS sortie FFMPEG (l'enum file_format ne propose
    que des images) : on passe donc par le binaire ffmpeg. La sequence PNG est de toute
    facon conservee — c'est elle, et pas la video, qu'on reimporte proprement dans un
    autre projet."""
    import shutil
    import subprocess
    ff = shutil.which('ffmpeg')
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith('.png'))
    if not files or not ff:
        print(f'  (pas d encodage : ffmpeg={bool(ff)}, images={len(files)})')
        return None
    src = os.path.join(frames_dir, 'f%04d.png')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(fps),
                    '-i', src, '-c:v', 'libx264', '-crf', '18',
                    '-pix_fmt', 'yuv420p', out_mp4], check=True)
    gif = out_mp4.replace('.mp4', '.gif')
    pal = os.path.join(frames_dir, '_pal.png')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-i', src,
                    '-vf', 'fps=%d,scale=560:-1:flags=lanczos,palettegen' % fps, pal],
                   check=True)
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(fps),
                    '-i', src, '-i', pal, '-lavfi',
                    'fps=%d,scale=560:-1:flags=lanczos[v];[v][1:v]paletteuse' % fps,
                    '-loop', '0', gif], check=True)
    os.remove(pal)
    print(f'  GIF -> {gif}')
    return out_mp4


def run(motion, frames, hq=False):
    base = json.load(open(SPEC))
    res = (1280, 720) if hq else (768, 432)
    settings = {'engine': 'EEVEE', 'samples': 48 if hq else 24}
    fdir = os.path.join(OUT, motion)
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    cyclic = motion in ('flap', 'turntable')
    for i in range(frames):
        # boucle PARFAITE : pour un cycle, la derniere image ne doit pas repeter la
        # premiere -> t = i/N (et non i/(N-1)).
        t = i / frames if cyclic else i / (frames - 1)
        spec = copy.deepcopy(base)
        apply_pose(spec, t, motion)
        scene_for(motion, spec, t)
        spec.setdefault('scene', {})['camera'] = camera_for(motion, t, spec)
        organic.build(spec)
        core.render(os.path.join(fdir, f'f{i:04d}.png'), res=res, settings=settings)
        print(f'  {motion} {i + 1}/{frames}', flush=True)
    mp4 = encode(fdir, os.path.join(OUT, f'wyvern_{motion}.mp4'), 24)
    print(f'OK {motion} -> {mp4}')


if __name__ == '__main__':
    motion = ARGV[0] if ARGV else 'flap'
    n = int(ARGV[1]) if len(ARGV) > 1 and ARGV[1].isdigit() else 0
    hq = '--hq' in ARGV
    defaults = {'flap': 32, 'flight': 48, 'turntable': 48, 'takeoff': 44}
    todo = list(defaults) if motion == 'all' else [motion]
    for m in todo:
        run(m, n or defaults[m], hq)
