# Prompt de réflexion « tout le projet » (fin de boucle 10, step_118)

> **What's the issue we are running into?**
> We are building a GENERIC text→3D creature pipeline: Python + headless Blender only, a JSON
> spec as the single source of truth, LLM agents that write small spec patches and generic
> builder extensions, then judge renders against reference images in a measured loop. The test
> bench is a GoT-style dragon. After 10 feedback loops the model still reads as a KIT OF PARTS —
> tubes, lofts and blobs attached at single points — instead of one continuous, sculpted,
> imposing organism. The latest user feedback makes the pattern explicit: every remaining defect
> is the same defect at a different scale.
> - The wing meets the body at ONE point; it should grow out of the flank along a whole
>   attachment line, fully fused like a fish fin, while keeping the dragon wingspan.
> - The head is not imposing: chin too small, nostrils wrong, skull should be squarer and much
>   more massive, with MUCH more relief — ridge lines running along the body with spikes on them.
> - Eyes are uniformly colored balls; they need real anatomy (socket, lids, iris/pupil,
>   specular life), detail and contrast.
> - The folded legs visually disappeared in the flight pose (plus a real builder bug: toes are
>   placed at absolute ground height).
>
> **What we are working with that works:**
> - Spec-driven generic builders (superellipse lofts for body/head, limbs, a new
>   variable-thickness membrane wing with battens) — everything parametric, nothing hardcoded.
> - The measured loop: renders compared to references (edge-density / color metrics), ≤3 cheap
>   iterations per loop, HQ renders only for presentation.
> - Scale armor as live instances (19.5k plates, near-zero memory, per-instance variation).
> - Cheap orchestration: an orchestrator delegates numbered contracts to smaller agents; all
>   state lives in files so ephemeral sessions can resume.
> - An SDF fusion layer in Geometry Nodes, validated headless (T10) but NOT yet wired in.
> - Camera / lights / materials in the spec; look patches are one-line diffs.
>
> **What doesn't work:**
> 1. CONTINUITY. No generic way to fuse parts into one surface, or to attach a part along a
>    curve/patch of another part (wing↔flank, brow↔horn, chin↔jaw). Everything meets at points;
>    seams and "glued-on" reads everywhere.
> 2. RELIEF LANGUAGE. Detail is added as MORE primitives (blobs/tubes), which plateaus
>    (edge-density 0.195 vs 0.33 target) and gets buried under the armor. We lack surface-level
>    operations: ridge/crest lines drawn ON a surface with spike trains riding them, carving
>    (nostrils), displacement of hero zones, curvature-driven masks.
> 3. PERCEPTION BANDWIDTH. The agents are nearly blind: one render per iteration judged by two
>    coarse global metrics. No multi-view sheet, no per-part silhouette/IoU, no curvature or
>    relief statistics — anatomy errors survive many loops, and every loop costs tokens. This
>    is also a "communicating with Blender" problem: we write scenes easily but read almost
>    nothing back.
> 4. SPEC ALTITUDE. The JSON speaks in raw points/radii. Intent like "membrane attached along
>    the flank from shoulder to hip" or "supraorbital ridge flowing into the horn" is not
>    expressible; agents emulate it with coordinates and the result drifts.
> 5. LOOK DEPTH. One flat material per part; no composite sub-materials (an eye is
>    cornea+iris+pupil+wet highlight), no macro texture contrast — "uniform balls" is the symptom.
>
> **What we need to solve** (goal: a text/image brief converges to a precise, complex, imposing
> creature in FEW measured loops):
> - A generic FUSION mechanism (probably wiring the validated SDF layer): fuse-groups declared
>   in the spec, smooth unions with controllable fillet radius, details (armor) re-skinned on
>   the fused surface.
> - Attachment-along-curve as a first-class spec concept (any part can anchor to a parametric
>   curve on another part's surface) — this is what "wing glued to the body like a fin" needs.
> - A RELIEF vocabulary in the spec: ridge lines with spike trains, carve/boolean features,
>   displacement zones — surface operations, not new blobs. This is what "lines coming out of
>   the body with spikes on them", the square massive skull, and real nostrils need.
> - A composite EYE builder + material (anatomy + shader), reusable for any creature.
> - Richer machine perception per iteration: fixed multi-view contact sheet, per-part ID/clay
>   masks, per-part IoU vs reference silhouettes, curvature/relief metrics — one iteration
>   should carry 5-10× more signal for the same token cost.
>
> **How can we solve this/these issues?** Concretely:
> (a) Do we wire the SDF layer now and make it the BACKBONE (organic parts become SDF
>     primitives fused per group, meshed once, detailed after), or keep the current meshes and
>     add fusion only at the joints that hurt (wing root, head features)?
> (b) What is the right minimal relief vocabulary (ridge+spikes, carve, displace, …) to cover
>     "ridge lines with spikes" body-wide without exploding the spec?
> (c) How would you structure attachment-along-curve generically (UV curve on parent loft?
>     projected 3D curve? shrinkwrap)?
> (d) Which perception upgrades give the most convergence per token?
> (e) Priorities given each loop is expensive: wing-to-flank fusion, square imposing skull
>     re-block, real eyes, visible folded legs — in what order?
> Plus: any budget / realism / timeline constraints on your side that should drive the choices?
