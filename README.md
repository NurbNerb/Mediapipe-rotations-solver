<!-- ══════════════════════════════════════════════════════════════════════ -->

```
 ___     _                     _           
| _ \___| |_ __ _ _ _ __ _ ___| |_ ___ _ _ 
|   / -_)  _/ _` | '_/ _` / -_)  _/ -_) '_|
|_|_\___|\__\__,_|_| \__, \___|\__\___|_|  
                     |___/    for TouchDesigner


        .-.                                            o
       (o o)             MediaPipe  ──►  Bones         /|\
        |=|             ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄        o─┼─o
       /|.|\             points in ──► angles out       │
      / | | \            two-bone leg IK · ground        o
        | |              no numpy · just math + re      ╱ ╲
       /   \                                           o   o
      /     \                                          │   │
     /       \                                         o   o
       you                ──────────►               the skeleton
```

<!-- ══════════════════════════════════════════════════════════════════════ -->

# MediaPipe → Rig Retargeter (pure-Python, TouchDesigner Script CHOP)

![python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![deps](https://img.shields.io/badge/dependencies-0-brightgreen)
![stdlib](https://img.shields.io/badge/imports-math%20%2B%20re-blue)
![touchdesigner](https://img.shields.io/badge/TouchDesigner-Script%20CHOP-orange)
![rigs](https://img.shields.io/badge/rigs-Mixamo%20%7C%20HumanIK%20%7C%20UE4%20%7C%20Custom-purple)
![status](https://img.shields.io/badge/single%20file-drop%20in-ff69b4)

Feed it MediaPipe **world**-landmark positions and get back clean per-bone **rotations**
for a humanoid rig — hips to fingertips, in real time, inside TouchDesigner. It's one
Python file, no external libraries, and it drops straight into a `Script CHOP`.

It's just a script: read it, fork it, tune it. Paste it into a Script CHOP, click
**Setup Parameters** to populate all the controls, wire two or three CHOPs, pick a rig,
and drive a skeleton — no build step, no external process.

> **Note:** the solver outputs **accurate** rotations out of the box, but expect to add a
> few small bind offsets to match a Mixamo rig *perfectly* — see [Tuning notes](#tuning-notes-aka-things-that-will-bite-you).

---

## TL;DR

- **In:** a CHOP of MediaPipe world landmarks — channels named `left_shoulder:x/y/z`,
  `right_elbow:x/y/z`, … (optional `:v` confidence per joint). Optional 21-point hand CHOPs.
- **Out:** rig rotation channels — `mixamorig_LeftArm:rx/ry/rz`, `…:tx/ty/tz`, etc.
- **How:** landmarks → direction vectors → quaternions → parent-relative locals →
  Euler in your rig's rotation order, One-Euro-smoothed the whole way.
- **Cost:** zero pip installs. It runs on TD's built-in Python.

---

## The math, without the lecture

MediaPipe hands you **dots in space**. A rig wants **angles at joints**. The whole script
is the bridge between those two facts.

**1. A bone is just an arrow.** Every bone points from its start joint to its end joint,
so subtract two landmarks and you have the direction it should aim: `elbow - shoulder`
is where the upper arm points. That's the entire input to the solve — positions only.

**2. Turn an arrow into a rotation — two flavors.**

- *Swing-only* (`quat_from_two_vecs`): the shortest twist that rotates a bone's rest
  direction onto its measured direction. Perfect for bones that only need to *point* —
  upper arms, forearms, thighs, calves. (The degenerate "pointing exactly backwards"
  case gets a hand-picked perpendicular axis so it never blows up.)
- *Full frame* (`quat_from_frame_vecs`): when **roll matters** — hips, chest, head,
  hands, feet — one direction isn't enough. Take a primary axis plus a secondary
  reference (e.g. spine-up + shoulder-right), Gram-Schmidt them into a clean
  forward/up/right basis via cross products, build the same basis for the rest pose,
  and the rotation between the two bases *is* the orientation. Basis → matrix →
  quaternion.

**3. Everyone lives in world space, then gets grounded.** Each bone is solved in world
orientation and then **unwound against its parent**: `local = parent_world⁻¹ · child_world`.
That's what a rig's local rotation channels actually want. The hierarchy is walked in
order — hips → spine → neck → head, shoulders → arms → forearms → hands → fingers,
hips → legs → feet → toes — so every child unwinds against a parent that's already solved.

**4. The spine doesn't snap.** Torso twist between hips and chest is spread across
Spine/Spine1/Spine2 with slerp at ⅓, ⅔, and full, so no single joint takes the whole bend.

**5. Quaternions are honest; Euler is what rigs eat.** The final local quaternion is
decomposed to `rx/ry/rz` in a **selectable rotation order** (XYZ … ZYX) to match whatever
order your downstream Bone COMPs use, with the gimbal-lock singularities handled.

**6. Bind fixes are a change of basis, not a nudge.** Rig-specific offsets (Mixamo's
rolled arm axes, etc.) are applied as a **conjugation** `q_bind · q · q_bind⁻¹` rather than
a static pre-multiply — so one correct 90° value fixes the bone across its *whole* range
instead of one lucky pose.

**7. Quaternion double-cover is respected everywhere.** `q` and `-q` are the same
rotation, so the shortest-path check (`dot < 0 → negate`) is enforced before every blend.
That's the difference between a limb that eases and a limb that flips inside-out.

### Smoothing is the secret sauce

Naive lag makes you choose between jitter and latency. This uses a **One Euro filter** on
rotations instead: it measures the bone's angular velocity (from the delta quaternion),
then **raises the cutoff when you move fast** (stay responsive) and **drops it when you
hold still** (kill the shakes). Position gets a simple exponential lag. And every filter
in/out is NaN-guarded — one bad frame **heals** the bone's state so it re-inits cleanly
instead of latching a NaN and making the limb quietly vanish.

---

## What's in the box

Beyond the core solve, the toggles you'll actually reach for:

| Capability | What it does |
|---|---|
| **One Euro rotation filter** | Adaptive jitter/latency trade-off, per bone |
| **Confidence-driven smoothing** | Low-visibility joints (`:v`) get smoothed harder automatically |
| **Two-bone leg IK + ground contact** | Analytic law-of-cosines knee solve, floor estimation, foot pin / anti-slide |
| **Predictive lookahead** | Velocity+acceleration extrapolation to cancel end-to-end latency |
| **Bone-length depth fit** | Learns rest bone lengths to recover believable monocular depth |
| **Turn continuity gate** | Rejects 1-frame torso pops from MediaPipe's front/back ambiguity |
| **Facing-flip lock / back-facing fix** | Holds orientation through profile and away-from-camera turns |
| **Occlusion repair** | Coasts hidden joints instead of snapping |
| **Arm anti-clip** | Torso-capsule pushout so arms don't sink into the chest |
| **Shoulder placement offsets** | Rotate the shoulder to fix a bind mesh, with an *exact* cancel on the arm (the quats telescope, so the arm/forearm/hand chain never moves) |
| **Multi-person** | `p1…pN` channel sets, encounter-ordered, with `pN_present` flags |
| **Hands + fingers** | Optional 21-landmark hand CHOPs; FRAME or angle-based CURL finger solve |

Rig targets out of the box: **Mixamo, HumanIK, Unreal (UE4), and Custom**.

Three modes on one operator:

- **MOCAP** — live MediaPipe capture (the default path)
- **ANIM** — pass a CHOP animation source through the same channel plumbing
- **SKELETON** — read rotations straight off TD Bone COMPs and re-emit them *(work in progress — not functional yet)*

---

## Quick start

1. Create a `Script CHOP`, paste this file into its DAT, and click **Setup Parameters** —
   every control populates across the parameter pages.
2. Wire your inputs:

   | Input | Feed it |
   |---|---|
   | **0** | MediaPipe **world** landmarks as `name:x/y/z` channels (`:v` optional) |
   | **1** | *(optional)* Left-hand CHOP, 21 landmarks |
   | **2** | *(optional)* Right-hand CHOP, 21 landmarks |

3. On the **Coords** page, **invert X and Y (set both to −1) and leave Z at +1.** MediaPipe's
   body arrives upside-down and mirrored; this flips it into the orientation a 3D rig expects.
4. On the **Retargeter** page: pick your **Target Rig Type**, leave **Mode** on `MOCAP`, and
   make sure **Enable Retargeter System** is on.
5. Hit **Load Optimized Filter Presets** for sane smoothing defaults, and drive a rig.

### Feeding it the right data (read this — it's the #1 gotcha)

MediaPipe's JSON gives you two landmark sets, and you need both, for different jobs:

- **`$.worldLandmarks`** — metric 3D positions. **Use these for all limb rotations.**
  ⚠️ If you don't feed world landmarks, you get **no angle output at all.**
- **`$.landmarks`** — screen-space (normalized) positions. Use these only for the **hips
  root position** — wire them to the Screen-Space Landmark CHOP on the **RootPos** page.

Confidence/visibility must arrive as a **`:v`** suffix on each joint (e.g. `left_elbow:v`)
for the confidence-driven features to see it.

Landmark names follow standard MediaPipe Pose naming (`left_shoulder`, `right_hip`,
`nose`, `left_ear`, `left_foot_index`, …). Channel names are case-insensitive and the
separator before the axis is flexible (`left_wrist:x`, `left_wrist_x`, `0:tx` all resolve).

### Output format

Each solved bone writes `rig_bone:rx/ry/rz` (degrees), plus `:tx/ty/tz` for the root and,
when **LimbXYZ** is on, for the tracked limb joints. Example (Mixamo):

```
mixamorig_LeftForeArm:rx   mixamorig_LeftForeArm:ry   mixamorig_LeftForeArm:rz
mixamorig_Hips:tx          mixamorig_Hips:ty          mixamorig_Hips:tz
```

Multi-person prefixes everything: `p1_mixamorig_LeftArm:rx`, `p2_…`, plus `p1_present`.

---

## Tuning notes (a.k.a. things that will bite you)

- **The one setting that matters most: `Output Rotate Order`.** It has to match the
  rotate order of your downstream Bone COMPs. Cycle it against a *combined* pose (bend on
  two axes at once) — a single-axis pose decodes identically in every order and will lie to you.
- **Arm still rotated after picking a rig?** The bind offsets are discrete. Nudge that
  bone's offset in **90° steps on one axis** until it locks. It's a pick, not a fine hunt.
- **Mixamo shoulders:** the classic fix is `Left Shoulder Y = +90`, `Right Shoulder Y = -90`
  — applied as a placement offset that the arm cancels exactly, so nothing downstream drifts.
- **Limb vanished?** Usually a latched NaN in the filter state; here the bone self-heals, but
  the `LOG` and `LIMBS` debug DATs (toggle **Debug Limb Angles**) show you exactly what each
  bone solved vs. what it wrote.

---

## Why you might like it

- **Readable.** It's plain functions and comments, not a compiled black box. Every trick
  above is a few lines you can lift into your own project.
- **Hackable.** Add a rig by adding one dict entry. Change a solve by editing one section.
- **Portable-ish.** The math core (`quat_*`, `*_from_*_vecs`, the One Euro filter) is pure
  stdlib — copy it out and it runs anywhere Python does.

---

## License

_Add your license of choice here (MIT is a friendly default for something this reusable)._

---

<sub>Built for live performance / virtual production work in TouchDesigner. If it saves you a
weekend of quaternion debugging, that's the whole point.</sub>
