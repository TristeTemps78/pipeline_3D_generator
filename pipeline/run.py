"""Entrée du pipeline. Commandes :
  forge <spec.json> [--fast] [--clay] [--sheet]  build + rendu (ou planche-contact) ;
        [--shot <id>]                            si spec scene.shots : 1 PNG par shot
                                                  (step_XXX_<id>.png, cadrage auto par
                                                  pièce via frame_part), --shot = 1 seul
  validate <spec.json> [--pairs a:b,c:d]         sanity checks BVH, AUCUN rendu (C1)
  sheet <spec.json> [--fast]                     planche-contact clay 4 vues, 1 PNG (C2)
  sheet4 <spec.json> [--fast]                    planche-contact clay 6 vues : profil/face/
                                                  dessus ortho + hero + silhouette + ID par
                                                  pièce (couleurs plates), cadrage auto bbox (axe 5)
  inspect <spec.json>                            JSON compact par pièce (bbox/dims/objets/verts),
                                                  AUCUN rendu (axe 5)
  clayhero <spec.json> [--fast]                  clay + caméra hero (géométrie seule, cadrage macro)
  compare <spec.json> <ref.png> [--fast]         réf | rendu rim-lit + deltas couleur/bords (I2)
Construit la scène depuis la spec, met à jour l'état de session.
Étapes fuse/detail (fusion voxel + displace + écailles) pilotées par la spec — cf.
research/convergence.md (solutions convergentes des deux docs, testées dans research/tests/)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))

from bx import core, organic, validate, feedback  # noqa: E402

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


def _load(spec_path):
    with open(spec_path) as f:
        return json.load(f)


def _next_out(st, ext='png'):
    out = os.path.join(ROOT, 'renders', f"step_{st['step']:03d}.{ext}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    return out


def _save_scene():
    """Garde les 2 DERNIERS modèles ouvrables dans Blender local (demande utilisateur) :
    scene.blend (courant) + scene_prev.blend (précédent), rotation avant chaque save."""
    path = os.path.join(ROOT, 'renders', 'scene.blend')
    if os.path.exists(path):
        os.replace(path, os.path.join(ROOT, 'renders', 'scene_prev.blend'))
    core.save_blend(path)


def _shot_camera(spec, shot, res):
    """Caméra d'un shot (`scene.shots`, mécanisme générique multi-prises) :
    - sans `frame_part` : caméra par défaut de la scène (cadrage « héros » actuel) ;
    - avec `frame_part`: cadrage AUTO sur la bbox monde du groupe de pièces (préfixe,
      cf. feedback.part_bbox) — distance déduite de la focale et du rayon bbox, la
      DIRECTION de visée vient de `dir` (vecteur cible→caméra) ou, à défaut, de la
      caméra par défaut (même point de vue, juste recentré/rapproché). `margin`
      multiplie la distance (1 = bbox tangente au cadre). Zéro constante objet."""
    cam = spec.get('scene', {}).get('camera', {})
    base_loc = tuple(cam.get('loc', (9, -11, 3.5)))
    base_tgt = tuple(cam.get('target', (0, 0, 2)))
    lens = shot.get('lens', cam.get('lens', 45))
    part = shot.get('frame_part')
    if not part:
        core.camera(base_loc, target=base_tgt, lens=lens)
        return
    bb = feedback.part_bbox(spec, part)
    if bb is None:
        raise SystemExit(f"shot '{shot.get('id')}' : frame_part '{part}' introuvable")
    center, radius = bb
    d = shot.get('dir') or [base_loc[i] - base_tgt[i] for i in range(3)]
    norm = sum(c * c for c in d) ** 0.5 or 1.0
    d = [c / norm for c in d]
    # champ le plus serré (capteur 36mm horizontal, vertical = ratio de rendu)
    tan_h = 18.0 / lens
    tan_v = tan_h * (res[1] / res[0])
    dist = radius * shot.get('margin', 1.3) / min(tan_h, tan_v)
    tgt = tuple(center[i] + shot.get('target_offset', (0, 0, 0))[i] for i in range(3))
    core.camera(tuple(tgt[i] + d[i] * dist for i in range(3)), target=tgt, lens=lens)


def forge(spec_path, fast=False):
    spec = _load(spec_path)
    st = load_state()
    st['step'] += 1
    n = organic.build(spec)
    out = _next_out(st)
    if '--sheet' in sys.argv:
        core.clay()
        tgt = spec.get('scene', {}).get('camera', {}).get('target', (0, 0, 1.5))
        res = (384, 288) if fast else (576, 432)
        feedback.contact_sheet(out, res=res, samples=(10 if fast else 24), target=tuple(tgt))
    else:
        if '--clay' in sys.argv:
            core.clay()
        res, samples = ((640, 480), 16) if fast else ((1152, 864), 48)
        # scene.render (perf générique) : appliqué au rendu FINAL seulement — en
        # --fast on garde les réglages d'itération (déjà minimaux).
        rset = None if fast else spec.get('scene', {}).get('render')
        shots = spec.get('scene', {}).get('shots')
        only = None
        if '--shot' in sys.argv:
            only = sys.argv[sys.argv.index('--shot') + 1]
        if shots:
            outs = []
            for shot in shots:
                sid = shot.get('id', 'shot')
                if only and sid != only:
                    continue
                _shot_camera(spec, shot, res)
                o = out.replace('.png', f'_{sid}.png')
                core.render(o, res=res, samples=samples, settings=rset)
                outs.append(o)
            out = outs[0] if outs else out
        else:
            core.render(out, res=res, samples=samples, settings=rset)
    _save_scene()
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(f"OK objets={n} rendu={out}")


def do_validate(spec_path):
    """C1 : rapport géométrique sans dépenser un seul rendu."""
    spec = _load(spec_path)
    organic.build(spec)
    pairs = []
    for a in sys.argv:
        if a.startswith('--pairs'):
            val = a.split('=', 1)[1] if '=' in a else sys.argv[sys.argv.index(a) + 1]
            pairs = [tuple(p.split(':')) for p in val.split(',')]
    rep = validate.scene_report(check_pairs=pairs)
    print(json.dumps(rep, indent=1))
    bad = [o for o in rep['objects'] if not o['watertight'] or o['self_intersecting_tris']]
    clip = [g for g in rep['ground'] if g.get('status') in ('floating', 'clipping')]
    hits = [p for p in rep['pairs'] if p['overlapping_tris'] > 0]
    print(f"\n=> {len(bad)} mesh non étanches/auto-intersectés, "
          f"{len(clip)} objets mal posés, {len(hits)} paires en collision.")


def do_compare(spec_path, ref_path, fast=False):
    """Inversion I2 : rendu macro rim-lit d'une région côte à côte avec la réf + deltas.
    Région via spec['scene']['hero'] = {'cam':[...], 'target':[...], 'lens':..}."""
    spec = _load(spec_path)
    st = load_state()
    st['step'] += 1
    organic.build(spec)
    hero = spec.get('scene', {}).get('hero', {})
    tgt = tuple(hero.get('target', spec.get('scene', {}).get('camera', {}).get('target', (0, 0, 2))))
    core.rim_setup(target=tgt, **spec.get('scene', {}).get('rim', {}))
    out = _next_out(st)
    res = (560, 560) if fast else (900, 900)
    rep = feedback.compare_sheet(out, ref_path, tuple(hero.get('cam', (5, -6, 3))), tgt,
                                 res=res, samples=(20 if fast else 40),
                                 lens=hero.get('lens', 70))
    _save_scene()
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(json.dumps({'sheet': rep['sheet'], 'ref': rep['ref'], 'render': rep['render']}, indent=1))


def do_clayhero(spec_path, fast=False):
    """Clay + caméra hero : juge la GÉOMÉTRIE seule dans le cadrage macro de `compare`,
    sans matériaux ni rim. C'est le rendu de validation entre deux éditions d'écailles/reliefs."""
    spec = _load(spec_path)
    st = load_state()
    st['step'] += 1
    organic.build(spec)
    core.clay()
    hero = spec.get('scene', {}).get('hero', {})
    tgt = tuple(hero.get('target', spec.get('scene', {}).get('camera', {}).get('target', (0, 0, 2))))
    core.camera(tuple(hero.get('cam', (5, -6, 3))), target=tgt, lens=hero.get('lens', 70))
    out = _next_out(st)
    res, samples = ((560, 560), 12) if fast else ((900, 900), 24)
    core.render(out, res=res, samples=samples)
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(f"OK clay hero -> {out}")


def do_sheet(spec_path, fast=False):
    spec = _load(spec_path)
    st = load_state()
    st['step'] += 1
    organic.build(spec)
    core.clay()
    out = _next_out(st)
    tgt = spec.get('scene', {}).get('camera', {}).get('target', (0, 0, 1.5))
    res = (384, 288) if fast else (576, 432)
    path, views = feedback.contact_sheet(out, res=res, samples=(10 if fast else 24),
                                         target=tuple(tgt))
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(f"OK planche-contact {views} -> {path}")


def do_sheet4(spec_path, fast=False):
    """Axe 5 doctrine : 5-10x le signal visuel d'un seul rendu — 6 vues cadrées auto
    (bbox globale) + passe ID par pièce, en UN PNG. Clay (comme `sheet`) : on juge la
    géométrie/les proportions/les pièces, pas le matériau final."""
    spec = _load(spec_path)
    st = load_state()
    st['step'] += 1
    organic.build(spec)
    core.clay()
    out = _next_out(st)
    path, legend, colors = feedback.sheet4(out, spec, fast=fast)
    st.update(spec=os.path.relpath(spec_path, ROOT), last_render=os.path.relpath(out, ROOT))
    save_state(st)
    print(f"OK sheet4 {legend} -> {path}")
    print(json.dumps({'legend': legend, 'id_colors': colors}, indent=1))


def do_inspect(spec_path):
    """Axe 5 doctrine : introspection scène sans dépenser un rendu. JSON par pièce de
    spec (nb objets, bbox, dimensions) + compteurs globaux, sur stdout."""
    spec = _load(spec_path)
    organic.build(spec)
    rep = feedback.inspect_report(spec)
    print(json.dumps(rep, indent=1))
    print(f"\n=> {rep['totals']['objects']} objets, "
          f"~{rep['totals']['verts_est']} sommets, {len(rep['parts'])} groupes de pièces.")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'forge'
    fast = '--fast' in sys.argv
    if cmd == 'forge':
        forge(sys.argv[2], fast=fast)
    elif cmd == 'validate':
        do_validate(sys.argv[2])
    elif cmd == 'sheet':
        do_sheet(sys.argv[2], fast=fast)
    elif cmd == 'sheet4':
        do_sheet4(sys.argv[2], fast=fast)
    elif cmd == 'inspect':
        do_inspect(sys.argv[2])
    elif cmd == 'clayhero':
        do_clayhero(sys.argv[2], fast=fast)
    elif cmd == 'compare':
        do_compare(sys.argv[2], sys.argv[3], fast=fast)
    else:
        sys.exit(f"commande inconnue: {cmd}")
