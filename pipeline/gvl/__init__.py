import json
import os

from . import laws

_VOCAB = None


def vocab(key=None):
    """Charge vocabulary.json (cache). vocab('growth.horn_spiral') → entrée."""
    global _VOCAB
    if _VOCAB is None:
        with open(os.path.join(os.path.dirname(__file__), "vocabulary.json")) as f:
            _VOCAB = json.load(f)
    return _VOCAB[key] if key else _VOCAB


def apply_law(key, **overrides):
    """Résout une clé vocab vers sa fonction de loi, params fusionnés avec overrides."""
    e = vocab(key)
    p = dict(e.get("p", {}))
    p.update(overrides)
    return getattr(laws, e["law"])(**p)
