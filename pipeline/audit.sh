#!/bin/bash
# Auto-audit compact : poids, nb fichiers, LOC — garder une direction claire.
cd "$(dirname "$0")/.."
echo "— poids : $(du -sh --exclude=.git . | cut -f1) (hors .git) ; .git $(du -sh .git | cut -f1)"
echo "— fichiers : $(find . -path ./.git -prune -o -type f -print | wc -l)"
echo "— LOC python pipeline : $(cat pipeline/run.py pipeline/bx/*.py pipeline/gvl/*.py 2>/dev/null | wc -l)"
echo "— LOC tests+logs : $(cat research/tests/*.py 2>/dev/null | wc -l) py, $(du -sh research/logs 2>/dev/null | cut -f1) logs"
echo "— renders : $(ls renders/*.png 2>/dev/null | wc -l) png ($(du -sh renders | cut -f1)), blends : $(ls renders/*.blend* 2>/dev/null | wc -l)"
echo "— specs : $(wc -l specs/*.json | tail -1 | awk '{print $1}') lignes"
# PNG non référencés dans CLAUDE.md/HANDOFF.md/NEXT.md = candidats purge (règle COMPACITÉ)
stale=$(for p in renders/*.png; do s=$(basename "$p" | grep -o 'step_[0-9]*' | head -1); [ -n "$s" ] && ! grep -q "$s" CLAUDE.md HANDOFF.md NEXT.md 2>/dev/null && echo "$p"; done)
[ -n "$stale" ] && echo "— renders NON référencés (à purger ?) : $(echo "$stale" | xargs -n1 basename | tr '\n' ' ')"
# agents : model sonnet obligatoire (sinon ils héritent du modèle cher de l'orchestrateur)
grep -L "^model:" .claude/agents/*.md 2>/dev/null | sed 's/^/— AGENT SANS model: (coûteux !) : /'
