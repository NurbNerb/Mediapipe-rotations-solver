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

Takes MediaPipe world-landmark positions and outputs per-bone rotations for a humanoid
rig, hips to fingertips, in real time inside TouchDesigner. It's a single Python file with
no external libraries, and it runs in a Script CHOP.

Paste it into a Script CHOP and click **Setup Parameters** to populate the controls, wire
your input CHOPs, pick a rig, and drive a skeleton.

The solver produces accurate rotations, but you will usually need to add a few small bind
offsets to match a Mixamo rig exactly. See [Tuning notes](#tuning-notes).

---

## Summary

- **In:** a CHOP of MediaPipe world landmarks — channels named `left_shoulder:x/y/z`,
  `right_elbow:x/y/z`, and so on (optional `:v` confidence per joint). Optional 21-point
  hand CHOPs.
- **Out:** rig rotation channels — `mixamorig_LeftArm:rx/ry/rz`, `…:tx/ty/tz`, etc.
- **How:** landmarks → direction vectors → quaternions → parent-relative locals → Euler in
  your rig's rotation order, smoothed with a One Euro filter throughout.
- **Requirements:** none to install. It uses TouchDesigner's built-in Python.

---

## How the math works

MediaPipe gives you points in space. A rig needs angles at joints. The script converts
between the two.

1. **A bone is a direction.** Each bone points from its start joint to its end joint, so
   subtracting two landmarks gives the direction it should aim (`elbow - shoulder` is where
   the upper arm points). The solve works entirely from positions.

2. **Direction to rotation, two methods.**
   - *Swing-only* (`quat_from_two_vecs`): the shortest rotation from a bone's rest direction
     to its measured direction. Used for bones that only need to point — upper arms,
     forearms, thighs, calves. The 180° case falls back to a chosen perpendicular axis.
   - *Full frame* (`quat_from_frame_vecs`): used where roll matters — hips, chest, head,
     hands, feet. It takes a primary direction plus a secondary reference, builds an
     orthonormal forward/up/right basis with cross products, builds the same basis for the
     rest pose, and converts the rotation between them to a quaternion.

3. **World space, then unwound to local.** Each bone is solved in world orientation, then
   made parent-relative: `local = parent_world⁻¹ · child_world`. The hierarchy is solved in
   order (hips → spine → neck → head, shoulders → arms → forearms → hands → fingers,
   hips → legs → feet → toes) so every child unwinds against a parent already solved.

4. **Spine is distributed.** Torso rotation between hips and chest is split across
   Spine/Spine1/Spine2 with slerp at ⅓, ⅔, and full, so no single joint takes the whole bend.

5. **Euler output in a selectable order.** The final local quaternion is decomposed to
   `rx/ry/rz` in a rotation order you pick (XYZ … ZYX) to match your downstream Bone COMPs,
   with gimbal-lock singularities handled.

6. **Bind offsets are a change of basis.** Rig-specific corrections are applied as a
   conjugation `q_bind · q · q_bind⁻¹` rather than a static pre-multiply, so a correct 90°
   value fixes a bone across its whole range.

7. **Double-cover handling.** `q` and `-q` are the same rotation, so a shortest-path check
   (`dot < 0 → negate`) runs before every blend to avoid limbs flipping.

### Smoothing

Rotations are smoothed with a One Euro filter, which measures each bone's angular velocity
and adjusts: less smoothing when moving fast (lower latency), more when nearly still (less
jitter). Root position uses a simple exponential lag. Filter input and output are checked
for NaN; a bad frame resets that bone's filter state instead of latching the error.

---

## Features

| Feature | Description |
|---|---|
| One Euro rotation filter | Per-bone jitter/latency trade-off |
| Confidence-driven smoothing | Low-visibility joints (`:v`) are smoothed more |
| Two-bone leg IK + ground contact | Law-of-cosines knee solve, floor estimation, foot pin / anti-slide |
| Predictive lookahead | Velocity + acceleration extrapolation to offset end-to-end latency |
| Bone-length depth fit | Learns rest bone lengths to recover depth from a single camera |
| Turn continuity gate | Rejects single-frame torso flips from MediaPipe front/back ambiguity |
| Facing-flip lock / back-facing fix | Holds orientation through profile and away-from-camera turns |
| Occlusion repair | Coasts hidden joints instead of snapping |
| Arm anti-clip | Torso-capsule pushout so arms don't sink into the chest |
| Shoulder placement offsets | Rotate the shoulder to fix a bind pose; the arm is cancelled so it doesn't move |
| Multi-person | `p1…pN` channel sets with `pN_present` flags |
| Hands + fingers | Optional 21-landmark hand CHOPs; FRAME or angle-based CURL finger solve |

Rig targets: Mixamo, HumanIK, Unreal (UE4), and Custom.

Three modes on one operator:

- **MOCAP** — live MediaPipe capture (the default).
- **ANIM** — pass a CHOP animation source through the same channel plumbing.
- **SKELETON** — read rotations from TD Bone COMPs and re-emit them. *Work in progress, not functional yet.*

---

## Quick start

1. Create a Script CHOP, paste this file into its DAT, and click **Setup Parameters**. The
   controls populate across the parameter pages.
2. Wire your inputs:

   | Input | Feed it |
   |---|---|
   | 0 | MediaPipe world landmarks as `name:x/y/z` channels (`:v` optional) |
   | 1 | Optional left-hand CHOP, 21 landmarks |
   | 2 | Optional right-hand CHOP, 21 landmarks |

3. On the **Coords** page, set **Invert X** and **Invert Y** to on (−1) and leave Z at +1.
   MediaPipe's body comes in upside-down and mirrored; this aligns it to the orientation a
   3D rig expects.
4. On the **Retargeter** page, pick your **Target Rig Type**, leave **Mode** on `MOCAP`, and
   make sure **Enable Retargeter System** is on.
5. Click **Load Optimized Filter Presets** for reasonable smoothing defaults, then drive a rig.

### Input data

MediaPipe's JSON provides two landmark sets, and this tool uses both:

- **`$.worldLandmarks`** — metric 3D positions. Use these for all limb rotations. If you do
  not feed world landmarks, you will get no rotation output.
- **`$.landmarks`** — screen-space (normalized) positions. Use these only for the hips root
  position, wired to the Screen-Space Landmark CHOP on the **RootPos** page.

Confidence/visibility must arrive as a `:v` suffix on each joint (for example
`left_elbow:v`) for the confidence-driven features to use it.

Landmark names follow standard MediaPipe Pose naming (`left_shoulder`, `right_hip`, `nose`,
`left_ear`, `left_foot_index`, and so on). Channel names are case-insensitive, and the
separator before the axis is flexible (`left_wrist:x`, `left_wrist_x`, `0:tx` all resolve).

### Output format

Each solved bone writes `rig_bone:rx/ry/rz` in degrees, plus `:tx/ty/tz` for the root and,
when **LimbXYZ** is on, for the tracked limb joints. Example (Mixamo):

```
mixamorig_LeftForeArm:rx   mixamorig_LeftForeArm:ry   mixamorig_LeftForeArm:rz
mixamorig_Hips:tx          mixamorig_Hips:ty          mixamorig_Hips:tz
```

Multi-person prefixes every channel: `p1_mixamorig_LeftArm:rx`, `p2_…`, plus `p1_present`.

---

## Tuning notes

- **Output Rotate Order** must match the rotate order of your downstream Bone COMPs. Test it
  against a pose bent on two axes at once; a single-axis pose decodes the same in every order
  and won't reveal a mismatch.
- If an arm is still rotated wrong after picking a rig, adjust that bone's bind offset in 90°
  steps on one axis until it lines up. These are discrete corrections, not fine adjustments.
- For Mixamo shoulders, the usual fix is Left Shoulder Y = +90 and Right Shoulder Y = −90.
  It is applied as a placement offset that the arm cancels, so nothing downstream moves.
- If a limb disappears, it is usually a NaN latched in the filter state. The bone re-inits on
  its own; enable **Debug Limb Angles** to write per-bone solved-vs-written values to the
  `LIMBS` table, and check the `LOG` table.

---

## Notes

- Single Python file, no external dependencies (uses `math` and `re` only).
- Add a rig by adding one entry to the rig mapping. The math core (`quat_*`,
  `*_from_*_vecs`, the One Euro filter) is plain standard-library Python.

---

## License

_Add your license here (MIT is a common choice)._
