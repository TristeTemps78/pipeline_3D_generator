# Convergence Analysis — Two Research Documents on the Headless Claude+Blender Creature Pipeline

Source: two research documents (2026-07-07) on turning the parametric blockout into a
film-quality biological mesh, fully headless via `bpy`, LLM-driven, token-frugal.

- **Doc 1** — "Headless Claude + Blender Pipeline for Film-Quality Creatures" (Skin-modifier oriented)
- **Doc 2** — "Architecting a Headless Procedural Pipeline" (Voxel-remesh oriented)

## 1. Where the documents CONVERGE (adopt without debate)

Both documents independently arrive at the same five solutions. These are the
high-confidence pieces; each was tested in `research/tests/` before being built
into the pipeline architecture (`pipeline/bx/`).

| # | Converging solution | Doc 1 | Doc 2 | Test | Pipeline module |
|---|---|---|---|---|---|
| C1 | **Pre-render BVH validation**: self-intersection via `BVHTree.FromBMesh(bm).overlap()`, pairwise inter-object overlap, ground-contact ray casts — numeric text feedback at zero render cost. World-space transform of the BMesh is mandatory. | §C | "Pre-Render Geometric Validation" | `t3_bvh_checks.py` | `bx/validate.py` |
| C2 | **Multi-view clay contact sheet**: 4 views (front/side/top/¾) stitched into ONE PNG via numpy `hstack`/`vstack` → one vision-token expenditure per iteration instead of four. | §C | "Context-Compressed Multi-View Rendering" | `t6_t7_feedback.py` | `bx/feedback.py` |
| C3 | **Silhouette-based proportion grounding**: binary silhouette masks compared numerically. Doc 2's IoU formulation (`|A∩B| / |A∪B|`, target > 0.85) is the concrete, scriptable version of Doc 1's reference-image alignment — adopted as the metric. | §D | "Proportional Grounding via IoU" | `t6_t7_feedback.py` | `bx/feedback.py` |
| C4 | **Real geometric micro-detail via Displace modifiers** on a subdivided mesh (layered: macro folds / medium scales / fine wrinkles), never shader-only displacement, never sculpt brushes. | §B | "detail must alter the true silhouette" | `t4_t5_detail.py` | `bx/detail.py` |
| C5 | **Explicit scales via Geometry Nodes**: `Distribute Points on Faces` + `Instance on Points`, density and scale driven by masks/curvature (Doc 2 adds the Edge Angle → curvature field refinement). | §B | "Algorithmic Geometric Detailing" | `t4_t5_detail.py` | `bx/detail.py` |

Shared principles under all five: **no manual sculpting, no `bpy.ops.sculpt`**;
everything stays parameter-driven from the JSON spec; **metaballs rejected** by both;
validate mathematically *before* spending a render.

## 2. Where the documents DIVERGE (decided empirically)

The single watertight organic body — the "largest realism jump per iteration" in both docs —
is the one point of direct contradiction:

| | Doc 1 | Doc 2 |
|---|---|---|
| Method | **Skin modifier** on an armature-like edge graph (+ Subsurf) | **Join + Remesh modifier (VOXEL)** + volume-preserving smooth (Laplacian / Corrective) |
| Rejects | Boolean+Remesh ("unpredictable topology, destroys proportions") | Skin ("topological twisting, unpredictable branching at complex junctions") |
| Fit with current pipeline | Replaces the whole body generator (edge graph instead of ring lofts/tubes) | Fuses the *existing* loft/tube primitives — keeps `bx.ops`/`bx.organic` unchanged upstream |
| Voxel size / radii control | per-vertex radii (2 axes) — coarse volumes only | `voxel_size = clamp(bbox_diag / target_res, 0.0005, 0.05)` — resolution scale-invariant |

Both were implemented in `bx/fuse.py` (`skin_body()` and `voxel_fuse()`) and benchmarked
head-to-head in `t1_skin_body.py` vs `t2_voxel_fuse.py` on the same quadruped target,
measuring watertightness, non-manifold edges, self-intersecting triangles, poly count and wall time.

## 3. Test results (bpy 5.0.1 headless, pip module, Cycles CPU)

Raw JSON logs in `research/logs/`, clay renders in `research/renders/`. bpy 5.0.1 (pip module), Cycles CPU.

### Divergence resolved — Voxel Remesh wins decisively (T1 vs T2)

Same quadruped target, measured with `bx.validate.geometry_report`:

| Metric | T1 Skin modifier (doc 1) | T2 Voxel fuse (doc 2) |
|---|---|---|
| Watertight | ❌ **false** (4 non-manifold edges) | ✅ **true** |
| Single connected body | ✅ true | ✅ true |
| Self-intersecting triangles | **26** | **0** |
| Faces | 3 632 | 26 372 |
| Build/fuse time | 0.015 s | ~3.1 s |

The Skin modifier produces a lighter mesh fast, but leaves non-manifold edges and
self-intersections at limb junctions — exactly the "twisting/branching artifacts" doc 2
warned about — which then break the BVH watertight guarantee the whole downstream pipeline
depends on. Voxel fuse turns a 22-island, 904-self-intersection raw blockout into **one
watertight manifold with zero self-intersections**, and its output survives the displace
and scale passes still watertight (T4). **Decision: `voxel_fuse` is the default `bx.fuse`
path**; `skin_body` is kept in the module as a lightweight blockout alternative.

Corner case found & fixed during T2: the voxel remesh does **not** bridge gaps between
primitives — a 5 cm neck→head gap left the head as a separate island. Added an `islands`
(connected-components) count to `geometry_report` so this is caught numerically, not visually.

### Converging solutions — all validated against known-good/known-bad controls

| Test | Result | Verdict |
|---|---|---|
| **C1** T3 self-intersection | clean sphere = 0 tris, overlapping join = 155 tris | ✅ discriminates |
| **C1** T3 pair overlap | separated = 0, interpenetrating = 106 | ✅ discriminates |
| **C1** T3 ground contact | grounded/floating/clipping → correct status + signed gap (0.0 / +0.35 / −0.30) | ✅ all correct |
| **C4** T4 displace layers | mean vertex offset **0.036** (max 0.092), faces 26k→105k, stays watertight & single-body | ✅ real geometry change |
| **C5** T5 geonodes scales | ~1 579 scale instances realized, curvature-driven density | ✅ instancing works |
| **C2** T6 contact sheet | 4 views → one **768×576** PNG (numpy hstack/vstack) | ✅ single-PNG |
| **C3** T7 IoU | identical silhouettes = **1.000**, 1.9× stretched = **0.791** (< 0.85 target) | ✅ metric discriminates |

End-to-end through `run.py` on `specs/creature_fused_demo.json`: `validate` reports the fused
body watertight / single-body / 0 self-intersections (only the open ground plane flags, as
expected); `forge --sheet` emits one clay contact-sheet PNG of the fused, displaced, scaled
creature. See `renders/step_024.png`.

## 4. Resulting architecture

```
pipeline/bx/
  validate.py   C1  geometry_report / self-intersections / pair overlap / ground contact
  fuse.py       divergence point: skin_body() + voxel_fuse() — winner per §3
  detail.py     C4+C5  displace layers + geometry-nodes scale instancing
  feedback.py   C2+C3  ortho silhouettes, contact sheet, IoU scoring
```

Ordered integration plan (merged from both docs' phase plans):

1. **GROUND** — reference silhouette → IoU target (`feedback.iou`), adjust spec numerically.
2. **BUILD** — existing parametric assembly (`bx.organic`), unchanged.
3. **VALIDATE** — `validate.scene_report()` before any render: watertight, self-intersections,
   pairwise clipping, ground contact. Text deltas back into the spec. Zero render cost.
4. **FUSE** — hand-off point from parametric to mesh level: one continuous watertight body.
5. **DETAIL** — displace layers, then geonodes scales (curvature-driven density).
6. **CRITIQUE** — one clay contact sheet PNG (4 views) + IoU score per iteration.
