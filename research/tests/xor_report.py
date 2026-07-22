"""OUTIL : analyse NUMERIQUE de la planche renders/silh.png (ref | rendu | XOR).

Lecon b24 (payee cher) : sur une vignette de 256 px, l'oeil ne sait pas dire OU la
silhouette perd des points. Les composantes connexes du XOR, elles, le disent — chaque
passe guidee par ce rapport a valu +0.013 a +0.017 d'IoU. L'outil etait refait a la main
a chaque session ; il est desormais committe.

Usage :  python3 research/tests/xor_report.py [renders/silh.png] [--top N]

Sortie : pour chaque poche, MANQUE (la ref est pleine, le rendu vide -> il faut AJOUTER
de la matiere) ou EXCES (l'inverse -> il faut EN ENLEVER), son aire en % de la ref, sa
bbox et son centre en coordonnees NORMALISEES (0..1, origine en haut a gauche de la bbox
de la silhouette) — donc directement lisibles comme « avant/arriere » et « haut/bas ».
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def tiles(path):
    """Decoupe la planche en 3 vignettes (separateurs gris a 0.5)."""
    a = np.array(Image.open(path).convert('L'), dtype=np.float32) / 255.0
    sep = np.abs(a.mean(axis=0) - 0.5) < 0.1          # colonnes de separation
    cuts, run = [], None
    for x, s in enumerate(sep):
        if s and run is None:
            run = x
        elif not s and run is not None:
            cuts.append((run, x))
            run = None
    bounds, prev = [], 0
    for a0, a1 in cuts:
        bounds.append((prev, a0))
        prev = a1
    bounds.append((prev, a.shape[1]))
    return [a[:, x0:x1] > 0.5 for x0, x1 in bounds[:3]]


def pockets(mask, label, ref_area, top, h, w):
    lab, n = ndimage.label(mask)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        out.append((len(ys), label, xs.min() / w, xs.max() / w, ys.min() / h, ys.max() / h))
    out.sort(reverse=True)
    for area, lb, x0, x1, y0, y1 in out[:top]:
        if area / ref_area < 0.001:
            continue
        print(f"  {lb:7s} {100 * area / ref_area:5.2f} %  "
              f"x[{x0:.2f}..{x1:.2f}] y[{y0:.2f}..{y1:.2f}]  "
              f"centre ({(x0 + x1) / 2:.2f}, {(y0 + y1) / 2:.2f})")
    return sum(o[0] for o in out)


def main():
    argv = sys.argv[1:]
    top = 8
    if '--top' in argv:
        i = argv.index('--top')
        top = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = args[0] if args else os.path.join(root, 'renders', 'silh.png')

    ref, ren, _ = tiles(path)
    h, w = ref.shape
    inter, union = (ref & ren).sum(), (ref | ren).sum()
    print(f"{os.path.relpath(path, root)}  vignettes {w}x{h}  IoU = {inter / union:.4f}")
    print("  x : 0 = museau, 1 = bout de la queue | y : 0 = haut, 1 = sol")
    miss = pockets(ref & ~ren, 'MANQUE', ref.sum(), top, h, w)
    exc = pockets(ren & ~ref, 'EXCES', ref.sum(), top, h, w)
    print(f"  total MANQUE {100 * miss / ref.sum():.2f} %   "
          f"total EXCES {100 * exc / ref.sum():.2f} %  (de l'aire de la ref)")


if __name__ == '__main__':
    main()
