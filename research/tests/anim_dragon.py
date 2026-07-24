"""OUTIL b30 : HARNAIS DE RENDU du Colosse pour le JEU aval — repond a ses 5 retours.

    bash pipeline/blender_py.sh research/tests/anim_dragon.py [state|all] [--hq]
    states : idle | alert | roar | fly | spawn | all

CE QUE LE JEU DEMANDAIT (et qu'on livre ici), point par point :
 1. FILM TRANSPARENT, sans decor -> `settings['transparent']` (alpha natif RGBA), le `ground`
    est RETIRE de la scene, encodage VP9 `yuva420p` (l'alpha survit) — zero detourage.
 2. BOUCLES SUR PLACE, pas de fly-by : la camera est FIXE (aucune traversee), le sujet reste
    CENTRE a echelle CONSTANTE (camera ORTHO), et 1re image = derniere (`t = i/N`) pour les
    clips loop. Le vol est un HOVER stationnaire (ailes qui cyclent, pattes repliees) : il
    sert IDLE-en-vol + FLY_ACROSS + RECEDE d'un coup.
 3. Rendu PAR ETAT MOTEUR, carre 576², + un `render.json` a cote : {fps, frames, facing,
    loop, scale, anchor} par etat + le MAPPING des 8 etats moteur vers les clips. `forge.py`
    du jeu le consomme tel quel (plus de duree devinee, plus de mapping a la main).
 4. Param COULEUR de materiau : `VARIANTS` re-teinte la hide (base + patina) -> une famille de
    Colosses (venins differents) a moindre cout. Rendu de la variante passee en 3e arg.
 5. Polish : cadrage carre a MARGE CONSTANTE (ortho fixe), fps DECLARE, orientation
    documentee (`facing:"left"` : la bete regarde -Y = ecran-GAUCHE en vue de profil),
    eclairage cle NEUTRE et homogene (pas de rim dur qui blanchit les ailes).

Meme doctrine que anim_wyvern.py : SANS armature. Le mouvement est une fonction du temps
appliquee aux PARAMETRES (la spec), et la scene est reconstruite image par image
(`core.reset()` + `organic.build()`). ~2-4 s/image en EEVEE.
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
SPEC = os.path.join(ROOT, 'specs', 'dragon.json')
OUT = os.path.join(ROOT, 'renders', 'anim', 'dragon')

RES = 576                    # carre, contrat du jeu
FACING = 'left'              # la bete regarde l'ecran-GAUCHE (vue 3/4 avant, cote +X)

# Reperes anatomiques (unites monde, cf. gen_dragon_trace.py : S=0.01, X0=560, Y0=660).
SPAN = 6.10                  # demi-envergure (x max d'une aile construite)
SHOULDER_Z = 3.25            # axe de battement (parallele a Y, a z=SHOULDER_Z)
NECK_Y0, HEAD_Y = -2.34, -5.00
HIP_Y, TAIL_Y = 1.20, 5.14
FOOT_Z = 0.10

# --- ETATS MOTEUR -> parametres de mouvement ---------------------------------------------
# beat = amplitude de battement d'aile (deg) ; wing_base = diedre STATIQUE (ailes relevees) ;
# bob = montee/descente du corps ; head_up/tail_up = offsets statiques (posture) ;
# neck_wave/tail_wave = ondes ; tuck = repli des pattes (vol) ; grounded = pieds au sol ;
# lift = fonction(t) d'altitude (spawn/roar, non cyclique).
# ortho/zc (b32, « echelle par etat » actee par l'utilisateur) : CADRAGE PAR ETAT — serre
# au sol (idle/alert : plus grand a l'ecran, marge basse reduite), large quand les ailes
# balaient (fly/roar). render.json declare scale+anchor PAR ETAT, le forge.py du jeu
# compense la difference d'echelle entre clips.
STATES = {
    # 4 de base + ROAR (minimum demande), + fly (hover) + spawn.
    'idle':  {'frames': 48, 'fps': 24, 'loop': True,  'beat': 7.0,  'wing_base': -0.05,
              'bob': 0.05, 'head_up': 0.0,  'tail_up': 0.0,  'neck_wave': 0.05,
              'tail_wave': 0.10, 'tail_swing': 0.06, 'tuck': 0.0, 'grounded': True,
              'ortho': 12.0, 'zc': 5.2, 'ty': 0.45},
    'alert': {'frames': 48, 'fps': 24, 'loop': True,  'beat': 10.0, 'wing_base': 0.55,
              'bob': 0.03, 'head_up': 0.55, 'tail_up': 0.30, 'neck_wave': 0.03,
              'tail_wave': 0.05, 'tail_swing': 0.10, 'tuck': 0.0, 'grounded': True,
              'ortho': 12.0, 'zc': 5.2, 'ty': 0.45},
    'roar':  {'frames': 44, 'fps': 24, 'loop': False, 'beat': 16.0, 'wing_base': 0.85,
              'bob': 0.0,  'head_up': 0.35, 'tail_up': 0.35, 'neck_wave': 0.0,
              'tail_wave': 0.04, 'tail_swing': 0.05, 'tuck': 0.0, 'grounded': True,
              'roar': True, 'ortho': 12.5, 'zc': 5.4, 'ty': 0.1},
    'fly':   {'frames': 36, 'fps': 24, 'loop': True,  'beat': 34.0, 'wing_base': 0.12,
              'bob': 0.24, 'head_up': 0.10, 'tail_up': -0.10, 'neck_wave': 0.14,
              'tail_wave': 0.30, 'tail_swing': 0.10, 'tuck': 1.0, 'grounded': False,
              'ortho': 13.5, 'zc': 4.4, 'ty': 0.35},
    'spawn': {'frames': 40, 'fps': 24, 'loop': False, 'beat': 28.0, 'wing_base': 0.10,
              'bob': 0.0,  'head_up': 0.0,  'tail_up': 0.0,  'neck_wave': 0.05,
              'tail_wave': 0.10, 'tail_swing': 0.05, 'tuck': 0.4, 'grounded': True,
              'spawn': True, 'ortho': 12.5, 'zc': 5.0, 'ty': 0.1},
}

# Mapping des 8 etats du MOTEUR de jeu -> clip rendu (plusieurs etats partagent un clip :
# le JS du jeu deplace/redimensionne le wrapper a l'ecran, donc FLY_ACROSS/RECEDE/FLY_AWAY
# reutilisent le meme HOVER stationnaire ; PERCH reutilise idle).
ENGINE_MAP = {'SPAWN': 'spawn', 'IDLE': 'idle', 'ALERT': 'alert', 'ROAR': 'roar',
              'FLY_AWAY': 'fly', 'FLY_ACROSS': 'fly', 'RECEDE': 'fly', 'PERCH': 'idle'}

# Param COULEUR (retour nº4) : re-teinte hide.base + hide.patina_color -> famille de venins.
VARIANTS = {
    'poison':  {'base': [0.026, 0.030, 0.022], 'patina': [0.11, 0.22, 0.09]},   # vert (defaut)
    'plague':  {'base': [0.030, 0.028, 0.020], 'patina': [0.22, 0.20, 0.05]},   # jaune-peste
    'venom':   {'base': [0.028, 0.022, 0.032], 'patina': [0.18, 0.07, 0.22]},   # violet
    'blight':  {'base': [0.020, 0.030, 0.030], 'patina': [0.07, 0.22, 0.20]},   # cyan-cadavre
}


# ------------------------------------------------------------------- outils mouvement
def _ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def _span(y, y0, y1):
    if y1 == y0:
        return 0.0
    return max(0.0, min(1.0, (y - y0) / (y1 - y0)))


def _rot_beat(p, ang):
    """Rotation d'un point d'aile autour de l'axe parallele a Y a z=SHOULDER_Z (battement
    up/down). Le mirror_x de la spec s'occupe de l'aile opposee."""
    x, z = p[0], p[2] - SHOULDER_Z
    c, s = math.cos(ang), math.sin(ang)
    return [x * c - z * s, p[1], x * s + z * c + SHOULDER_Z]


# MACHOIRE (b32) : la gueule est une peau FERMEE (pas de rig) — l'ouverture est une
# rotation des points SOUS la ligne de levre autour d'une charniere parallele a X.
# Ligne de levre (LIP de gen_dragon_parts, monde) : z 1.84-1.92 sur y [-5.00, -3.46].
JAW_HINGE_Y, JAW_HINGE_Z = -3.42, 1.92
JAW_LIP_Z = 1.90             # frontiere haut/bas de gueule (leg. au-dessus de la levre)


def jaw_angle(t, cfg):
    """Ouverture (rad) pendant le roar : fermee -> ouverture FRANCHE sur la detente ->
    tenue -> retombee. Synchronisee avec lift() (detente a t 0.30-0.55)."""
    if not cfg.get('roar'):
        return 0.0
    amax = math.radians(34.0)
    if t < 0.28:
        return 0.0
    if t < 0.45:
        return amax * _ease((t - 0.28) / 0.17)
    if t < 0.75:
        return amax
    return amax * (1.0 - _ease((t - 0.75) / 0.25))


def _jaw(p, ang):
    """Rotation autour de la charniere, ponderee : pleine sous la levre, nulle au-dessus
    (le crane ne bouge pas), fondue vers la gorge (la peau s'etire, elle ne dechire pas)."""
    if ang <= 0.0:
        return p
    x, y, z = p
    wz = 1.0 - _ease(_span(z, JAW_LIP_Z - 0.10, JAW_LIP_Z + 0.03))   # 1 sous la levre
    wy = _ease(_span(y, JAW_HINGE_Y, JAW_HINGE_Y - 0.35))            # 0 a la gorge
    w = wz * wy
    if w <= 0.0:
        return p
    a = ang * w
    dy, dz = y - JAW_HINGE_Y, z - JAW_HINGE_Z
    c, s = math.cos(a), math.sin(a)
    # rotation qui ABAISSE l'avant (dy<0) : z' = z_h + dy*sin + dz*cos decroit avec a
    return [x, JAW_HINGE_Y + dy * c - dz * s, JAW_HINGE_Z + dy * s + dz * c]


def lift(t, cfg):
    """Altitude non cyclique : spawn (surgit et se pose) / roar (se cabre)."""
    if cfg.get('spawn'):
        # surgit bas + ramasse -> se detend et se pose
        if t < 0.35:
            return -0.55 * (1.0 - _ease(t / 0.35))
        return 0.0
    if cfg.get('roar'):
        # se ramasse -> DETENTE (le rugissement) -> retombe
        if t < 0.30:
            return -0.18 * _ease(t / 0.30)
        if t < 0.55:
            return -0.18 + 0.55 * _ease((t - 0.30) / 0.25)
        return 0.37 * (1.0 - _ease((t - 0.55) / 0.45))
    return 0.0


def warp(p, t, cfg):
    """Champ de deplacement applique a TOUT point (cristaux/crocs/oeil suivent gratuitement)."""
    x, y, z = p
    ph = 2.0 * math.pi * t
    # le corps monte pendant la DESCENTE des ailes (portance) : dephasage d'un quart de cycle
    body = cfg['bob'] * math.sin(ph - math.pi / 2.0)
    neck = _span(y, NECK_Y0, HEAD_Y) ** 1.5
    tail = _span(y, HIP_Y, TAIL_Y) ** 1.5
    dz = (body
          + cfg['head_up'] * neck + cfg['tail_up'] * tail
          + cfg['neck_wave'] * neck * math.sin(ph - 1.15)
          + cfg['tail_wave'] * tail * math.sin(ph - 1.55)
          + lift(t, cfg))
    dy = cfg['tail_swing'] * tail * math.sin(ph - 2.10)
    # PIEDS AU SOL : tant que grounded, on attenue le deplacement vertical vers le bas du
    # modele -> la bete ne flotte pas au-dessus de son ancre (mais lift() passe, lui).
    if cfg['grounded']:
        anchor = _span(z, FOOT_Z, FOOT_Z + 1.7)          # 0 au pied, 1 en haut
        dz = lift(t, cfg) + (dz - lift(t, cfg)) * anchor
    return [x, y + dy, z + dz]


def wing_angle(t, reach, cfg):
    """Battement d'un point d'aile. reach = 0 a l'epaule, 1 a la pointe. RETARD vers la
    pointe + descente motrice plus ample : le fouette d'une aile souple."""
    base = cfg['wing_base'] * (0.25 + 0.75 * reach)
    if cfg['beat'] <= 0.0:
        return base
    lag = 0.16 * reach
    s = math.sin(2.0 * math.pi * (t - lag))
    s = s * (1.0 + 0.30 * max(0.0, -s))
    return base + math.radians(cfg['beat']) * s * (0.25 + 0.75 * reach)


LEG_COLS_Y = (-1.55, 1.30)   # centres des colonnes fore/hind (trace : x_img ~404/690)


def _leg_gate(y):
    """Poids 1 sur une colonne de patte, 0 au-dela de 0.75 u — depuis la soudure b31 les
    pattes vivent DANS body_cage, le repli ne peut plus cibler un id de part."""
    d = min(abs(y - LEG_COLS_Y[0]), abs(y - LEG_COLS_Y[1]))
    return max(0.0, min(1.0, (1.1 - d) / 0.6))   # plateau ±0.5 (tout le pied a poids 1)


def apply_pose(spec, t, cfg):
    """Deforme une COPIE de la spec pour l'instant t (aucun bpy : listes de nombres)."""
    tuck = cfg['tuck']
    jaw = jaw_angle(t, cfg)
    for part in spec['parts']:
        pid = part.get('id', '')
        is_wing = pid.startswith('wing')
        is_foot = pid.startswith(('leg_', 'toe_', 'claw_'))

        def move(p):
            q = list(p)
            if is_wing:
                reach = min(1.0, abs(q[0]) / SPAN)
                q = _rot_beat(q, wing_angle(t, reach, cfg))
            elif jaw > 0.0:
                q = _jaw(q, jaw)
            if tuck > 0.0:
                # repli des pattes SOUS le ventre en vol (poids 1 au pied, 0 vers la hanche)
                g = 1.0 if is_foot else (_leg_gate(q[1]) if pid == 'body_cage' else 0.0)
                if g > 0.0:
                    w = (1.0 - _span(q[2], FOOT_Z, 2.0)) * g
                    q[2] += 1.35 * tuck * w
                    q[1] += 0.55 * tuck * w
            return warp(q, t, cfg)

        if 'verts' in part:
            part['verts'] = [move(v) for v in part['verts']]
        if 'pos' in part:
            part['pos'] = move(part['pos'])
    return spec


# ------------------------------------------------------------------- scene neutre + camera
def neutralize_scene(spec, cfg):
    """Eclairage NEUTRE et homogene (contrat nº5) + retrait du sol + camera fixe ORTHO de
    profil (facing left). On ecrase le low-key dramatique du hero : un sprite de jeu doit
    etre lisible, a plat, sans rim dur qui blanchit les ailes translucides."""
    spec['parts'] = [p for p in spec['parts'] if p.get('id') != 'ground']
    sc = spec.setdefault('scene', {})
    sc['world'] = {'color': [0.05, 0.05, 0.05], 'color_top': [0.06, 0.06, 0.06],
                   'strength': 0.55, 'visible_strength': 0.0}      # ambiance douce neutre
    sc['sun'] = {'direction': [-0.35, 0.55, -0.75], 'energy': 3.0,
                 'color': [1.0, 1.0, 1.0], 'angle_deg': 8.0}       # cle douce, quasi frontale
    sc['area_lights'] = [
        {'loc': [-6.0, -5.0, 5.0], 'target': [0.0, 0.0, 2.2], 'energy': 500,
         'size': 8.0, 'color': [1.0, 1.0, 1.0]},                  # key large et douce
        {'loc': [-6.0, 5.0, 3.0], 'target': [0.0, 0.0, 2.2], 'energy': 220,
         'size': 8.0, 'color': [0.96, 0.97, 1.0]},                # fill (pas de noir mort)
    ]
    # Vue 3/4 AVANT depuis le cote +X (-> la tete, en -Y, tombe a l'ecran-GAUCHE) et un peu
    # en hauteur : montre les ailes DEPLOYEES (que le pur profil rendait en tranche) et le
    # crane dur. Camera FIXE (aucun fly-by), ORTHO (echelle constante).
    sc['camera'] = {'loc': [12.0, -12.0, 5.0],
                    'target': [0.0, cfg.get('ty', -0.2), cfg['zc']], 'lens': 50}
    sc.pop('shots', None)
    return spec


def tint(spec, variant):
    v = VARIANTS.get(variant)
    if not v:
        return spec
    p = spec['materials']['hide']['p']
    p['base'] = list(v['base'])
    p['patina_color'] = list(v['patina'])
    return spec


def set_ortho(cfg):
    cam = bpy.context.scene.camera
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = cfg['ortho']


# ------------------------------------------------------------------------ encodage
def encode_webm(frames_dir, out_webm, fps):
    """VP9 alpha (yuva420p) depuis la sequence PNG RGBA. Ce build de Blender n'a pas la
    sortie FFMPEG -> binaire ffmpeg externe (present en local)."""
    import shutil
    import subprocess
    ff = shutil.which('ffmpeg')
    files = sorted(f for f in os.listdir(frames_dir) if f.endswith('.png'))
    if not files or not ff:
        print(f'  (pas d encodage : ffmpeg={bool(ff)}, images={len(files)})')
        return None
    src = os.path.join(frames_dir, 'f%04d.png')
    subprocess.run([ff, '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', src,
                    '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '30',
                    '-an', out_webm], check=True)
    return out_webm


# ---------------------------------------------------------------------------- rendu
def clip_name(state, variant):
    """poison = la variante par defaut, garde le nom b30 (ne casse pas le jeu)."""
    return f'dragon_{state}.webm' if variant == 'poison' else f'dragon_{state}_{variant}.webm'


def render_state(base, state, hq, variant):
    cfg = STATES[state]
    n = cfg['frames']
    res = (RES, RES)
    settings = {'engine': 'EEVEE', 'samples': 48 if hq else 24, 'transparent': True}
    fdir = os.path.join(OUT, state)
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    for i in range(n):
        # boucle PARFAITE : pour un cycle, t = i/N (la derniere image ne repete pas la 1re)
        t = (i / n) if cfg['loop'] else (i / (n - 1))
        spec = copy.deepcopy(base)
        neutralize_scene(spec, cfg)
        tint(spec, variant)
        apply_pose(spec, t, cfg)
        organic.build(spec)
        set_ortho(cfg)
        core.render(os.path.join(fdir, f'f{i:04d}.png'), res=res, settings=settings)
        print(f'  {state} {i + 1}/{n}', flush=True)
    webm = encode_webm(fdir, os.path.join(OUT, clip_name(state, variant)), cfg['fps'])
    print(f'OK {state} [{variant}] -> {webm}')
    return cfg


def write_sidecar(done, variant):
    """render.json : metadonnees par etat + mapping des 8 etats moteur. Consommable tel quel
    par le forge.py du jeu. `anchor` = position verticale des PIEDS dans le cadre (fraction
    du bas) ; `scale` = unites monde par cadre — PAR ETAT depuis b32 (cadrage par etat,
    acte avec l'utilisateur : le jeu compense via scale/anchor). Les runs par variante
    FUSIONNENT dans le meme fichier (cle `variants`)."""
    path = os.path.join(OUT, 'render.json')
    doc = {}
    if os.path.exists(path):
        with open(path) as f:
            doc = json.load(f)
    states_meta = doc.get('states', {})
    for state, cfg in done.items():
        # pieds a z~FOOT_Z ; le cadre couvre [zc - ortho/2, zc + ortho/2] verticalement.
        anchor = round((FOOT_Z - (cfg['zc'] - cfg['ortho'] / 2.0)) / cfg['ortho'], 4)
        states_meta[state] = {'clip': clip_name(state, 'poison'), 'fps': cfg['fps'],
                              'frames': cfg['frames'], 'loop': cfg['loop'],
                              'facing': FACING, 'size': [RES, RES],
                              'scale': round(cfg['ortho'], 3), 'anchor': [0.5, anchor]}
    variants = doc.get('variants', {})
    variants[variant] = {st: clip_name(st, variant) for st in done}
    doc.update({
        'unit': 'square RGBA VP9 (yuva420p), centered, per-state scale (see states)',
        'facing': FACING, 'fps': 24, 'size': [RES, RES],
        'states': states_meta, 'variants': variants,
        'engine_map': {k: v for k, v in ENGINE_MAP.items() if v in states_meta}})
    doc.pop('ortho_units', None)
    doc.pop('foot_anchor', None)
    with open(path, 'w') as f:
        json.dump(doc, f, indent=1)
    print('render.json ->', path)


if __name__ == '__main__':
    which = ARGV[0] if ARGV and not ARGV[0].startswith('-') else 'all'
    hq = '--hq' in ARGV
    variant = next((a for a in ARGV if a in VARIANTS), 'poison')
    base = json.load(open(SPEC))
    os.makedirs(OUT, exist_ok=True)
    # PROBE : une seule image (pour caler camera/cadrage/facing vite).
    # `probe [state] [t]` — t optionnel (defaut 0.25 ; 0.55 = gueule ouverte du roar).
    if which == 'probe':
        st = ARGV[1] if len(ARGV) > 1 and ARGV[1] in STATES else 'fly'
        tp = next((float(a) for a in ARGV[2:] if a.replace('.', '', 1).isdigit()), 0.25)
        cfg = STATES[st]
        spec = copy.deepcopy(base)
        neutralize_scene(spec, cfg)
        tint(spec, variant)
        apply_pose(spec, tp, cfg)
        organic.build(spec)
        set_ortho(cfg)
        core.render(os.path.join(OUT, '_probe.png'), res=(RES, RES),
                    settings={'engine': 'EEVEE', 'samples': 32, 'transparent': True})
        print('probe ->', os.path.join(OUT, '_probe.png'))
        sys.exit(0)
    todo = list(STATES) if which == 'all' else [which]
    done = {}
    for st in todo:
        done[st] = render_state(base, st, hq, variant)
    write_sidecar(done, variant)
