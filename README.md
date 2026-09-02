<!-- ══════════════════════════════════════════════════════════════════════ -->

```
 ___     _                     _           
| _ \___| |_ __ _ _ _ __ _ ___| |_ ___ _ _ 
|   / -_)  _/ _` | '_/ _` / -_)  _/ -_) '_|
|_|_\___|\__\__,_|_| \__, \___|\__\___|_|  
                     |___/    for TouchDesigner


        .-.                                              o
       (o o)  MediaPipe──►Stabiliser──►Solver──►Bones   /|\
        |=|          ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄            o─┼─o
       /|.|\          points in ──► angles out           │
      / | | \         two-bone leg IK · ground           o
        | |           no numpy · just math + re         ╱ ╲
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

- **In:** a CHOP of MediaPipe world landmarks - channels named `left_shoulder:x/y/z`,
  `right_elbow:x/y/z`, and so on (optional `:v` confidence per joint). Optional 21-point
  hand CHOPs.
- **Out:** rig rotation channels - `mixamorig_LeftArm:rx/ry/rz`, `…:tx/ty/tz`, etc.
- **How:** landmarks → direction vectors → quaternions → parent-relative locals → Euler in
  your rig's rotation order, smoothed with a One Euro filter throughout.
- **Requirements:** none to install. It uses TouchDesigner's built-in Python.

---

## How the math works

https://www.youtube.com/watch?v=f42N2yAaEkE (old setup video video)
https://www.youtube.com/watch?v=QUO4OK8BsUc&t=7s  (test videos)
https://www.patreon.com/Nurbs863/posts/retargeter-v2-to-166712796   Full retargeter component 
MediaPipe gives you points in space. A rig needs angles at joints. The script converts
between the two.

1. **A bone is a direction.** Each bone points from its start joint to its end joint, so
   subtracting two landmarks gives the direction it should aim (`elbow - shoulder` is where
   the upper arm points). The solve works entirely from positions.

2. **Direction to rotation, two methods.**
   - *Swing-only* (`quat_from_two_vecs`): the shortest rotation from a bone's rest direction
     to its measured direction. Used for bones that only need to point - upper arms,
     forearms, thighs, calves. The 180° case falls back to a chosen perpendicular axis.
   - *Full frame* (`quat_from_frame_vecs`): used where roll matters - hips, chest, head,
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

- **MOCAP** - live MediaPipe capture (the default).
- **ANIM** - pass a CHOP animation source through the same channel plumbing.
- **SKELETON** - read rotations from TD Bone COMPs and re-emit them. *Work in progress, not functional yet.*

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

- **`$.worldLandmarks`** - metric 3D positions. Use these for all limb rotations. If you do
  not feed world landmarks, you will get no rotation output.
- **`$.landmarks`** - screen-space (normalized) positions. Use these only for the hips root
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

## Joint rotation math

Every bone is solved the same way:

1. Get a direction by subtracting two landmark positions.
2. Convert that direction (plus a roll reference where needed) into a world-space quaternion.
3. Make it parent-relative: `q_local = quat_mult(quat_inv(parent_world), child_world)`.
4. Convert to Euler and write it with `set_rotation()`.

Only step 2 changes between bones, and only in which vectors it's given.

---

### Core builders

```python
# Shortest rotation from rest direction v1 to measured direction v2.
# Used for bones that only need to point: arms, forearms, thighs, calves.
def quat_from_two_vecs(v1, v2):
    v1 = vec_norm(v1); v2 = vec_norm(v2)
    if vec_len(v1) < 0.001 or vec_len(v2) < 0.001: return [1,0,0,0]
    d = vec_dot(v1, v2)
    if d >= 0.9999: return [1,0,0,0]                    # already aligned
    if d <= -0.9999:                                    # 180 deg: pick a perpendicular axis
        axis = vec_norm(vec_cross([1,0,0], v1))
        if vec_len(axis) < 0.001: axis = vec_norm(vec_cross([0,1,0], v1))
        return [0, axis[0], axis[1], axis[2]]
    axis = vec_cross(v1, v2)
    s = math.sqrt((1 + d) * 2); invs = 1.0 / s
    return [s * 0.5, axis[0]*invs, axis[1]*invs, axis[2]*invs]


# Full orientation from a primary direction + a secondary reference, matched to a rest basis.
# Used where roll matters: hips, chest, head, hands, feet.
def quat_from_frame_vecs(primary_dir, secondary_dir, primary_rest, secondary_rest):
    fwd = vec_norm(primary_dir)
    up  = vec_norm(vec_sub(secondary_dir, vec_scale(fwd, vec_dot(secondary_dir, fwd))))
    if vec_len(up) < 1e-6:
        up = vec_norm(vec_cross(fwd, [0,0,1] if abs(fwd[2]) < 0.9 else [1,0,0]))
    right = vec_norm(vec_cross(fwd, up))
    pr = vec_norm(primary_rest)
    sr = vec_norm(vec_sub(secondary_rest, vec_scale(pr, vec_dot(secondary_rest, pr))))
    rr = vec_norm(vec_cross(pr, sr))
    m = [[fwd[i]*pr[j] + right[i]*rr[j] + up[i]*sr[j] for j in range(3)] for i in range(3)]
    return quat_norm(mat3_to_quat(m))
```

World-to-local is always `quat_mult(quat_inv(parent_world), child_world)`, and each write is
`set_rotation(scriptOp, bone, *quat_to_euler(q_local), smooth)`.

---

### Shared torso vectors

```python
hip_center   = vec_scale(vec_add(l_hip, r_hip), 0.5)
chest_center = vec_scale(vec_add(l_sho, r_sho), 0.5)
spine_vec    = vec_sub(chest_center, hip_center)   # up the torso
hip_right    = vec_sub(r_hip, l_hip)               # across the pelvis
sho_right    = vec_sub(r_sho, l_sho)               # across the chest
```

---

### Hips (root, no parent)

```python
hip_right_n = vec_norm(hip_right)
world_up    = [0, 1, 0]
hip_up      = vec_norm(vec_sub(world_up, vec_scale(hip_right_n, vec_dot(world_up, hip_right_n))))
q_hips_world = quat_from_frame_vecs(hip_up, hip_right, [0,1,0], [1,0,0])
set_rotation(scriptOp, 'Hips', *quat_to_euler(q_hips_world), Rotationsmooth)
```

Rest basis: up = +Y, right = +X. No unwind - Hips is the world root.

---

### Spine / Spine1 / Spine2

```python
q_chest_world = quat_from_frame_vecs(spine_vec, sho_right, [0,1,0], [1,0,0])
q_torso_rel   = quat_mult(quat_inv(q_hips_world), q_chest_world)   # hips -> chest

q_spine_local  = quat_slerp([1,0,0,0], q_torso_rel, 1.0/3.0)
q_spine2_accum = quat_slerp([1,0,0,0], q_torso_rel, 2.0/3.0)
q_spine1_local = quat_mult(quat_inv(q_spine_local),  q_spine2_accum)
q_spine2_local = quat_mult(quat_inv(q_spine2_accum), q_torso_rel)

set_rotation(scriptOp, 'Spine',  *quat_to_euler(q_spine_local),  Rotationsmooth)
set_rotation(scriptOp, 'Spine1', *quat_to_euler(q_spine1_local), Rotationsmooth)
set_rotation(scriptOp, 'Spine2', *quat_to_euler(q_spine2_local), Rotationsmooth)

q_chest_accum = quat_mult(q_hips_world, q_torso_rel)   # world chest, reused below
```

The full hips-to-chest rotation is split three ways with slerp at 1/3, 2/3, and 1.

---

### Neck / Head

```python
ear_center   = vec_scale(vec_add(l_ear, r_ear), 0.5)
head_up      = vec_sub(nose, ear_center)
ear_right    = vec_sub(r_ear, l_ear)
q_head_world = quat_from_frame_vecs(head_up, ear_right, [0,1,0], [1,0,0])

q_neck_full  = quat_mult(quat_inv(q_chest_accum), q_head_world)
q_neck_local = quat_slerp([1,0,0,0], q_neck_full, 0.4)            # neck takes 40%
set_rotation(scriptOp, 'Neck', *quat_to_euler(q_neck_local), Rotationsmooth)

q_neck_world = quat_mult(q_chest_accum, q_neck_local)
q_head_local = quat_mult(quat_inv(q_neck_world), q_head_world)    # head takes the rest
set_rotation(scriptOp, 'Head', *quat_to_euler(q_head_local), Rotationsmooth)
```

---

### Shoulders (clavicles)

```python
# LEFT
q_lsh_world = quat_from_frame_vecs(vec_sub(l_sho, chest_center), [0,-1,0], [-1,0,0], [0,-1,0])
q_lsh_local = quat_slerp([1,0,0,0], quat_mult(quat_inv(q_chest_accum), q_lsh_world), 0.5)
set_rotation(scriptOp, 'LeftShoulder', *quat_to_euler(q_lsh_local), Armsmooth)

# RIGHT (rest primary flips to +X)
q_rsh_world = quat_from_frame_vecs(vec_sub(r_sho, chest_center), [0,-1,0], [1,0,0], [0,-1,0])
q_rsh_local = quat_slerp([1,0,0,0], quat_mult(quat_inv(q_chest_accum), q_rsh_world), 0.5)
set_rotation(scriptOp, 'RightShoulder', *quat_to_euler(q_rsh_local), Armsmooth)
```

The 0.5 slerp keeps the clavicle from over-rotating. Shoulder placement offsets are applied
after the arm is solved, and cancelled on the arm, so the arm chain doesn't move.

---

### Upper arms

Solved against the chest frame, not the shoulder - so the shoulder's own rotation isn't baked
into the arm's world frame.

```python
# LEFT
arm_dir_world = vec_sub(landmarks['left_elbow'], l_sho)
arm_local     = _quat_rotate_vec(quat_inv(q_chest_accum), arm_dir_world)
q_larm_local  = quat_from_two_vecs([-1,0,0], arm_local)          # rest arm = -X
q_larm_world  = quat_mult(q_chest_accum, q_larm_local)           # keep for forearm
set_rotation(scriptOp, 'LeftArm', *quat_to_euler(q_larm_local), Armsmooth)

# RIGHT (rest arm = +X)
arm_dir_world = vec_sub(landmarks['right_elbow'], r_sho)
arm_local     = _quat_rotate_vec(quat_inv(q_chest_accum), arm_dir_world)
q_rarm_local  = quat_from_two_vecs([1,0,0], arm_local)
q_rarm_world  = quat_mult(q_chest_accum, q_rarm_local)
set_rotation(scriptOp, 'RightArm', *quat_to_euler(q_rarm_local), Armsmooth)
```

---

### Forearms

```python
# LEFT
fa_dir_world = vec_sub(landmarks['left_wrist'], landmarks['left_elbow'])
fa_local     = _quat_rotate_vec(quat_inv(q_larm_world), fa_dir_world)
q_lfa_local  = quat_from_two_vecs([-1,0,0], fa_local)
q_lfa_world  = quat_mult(q_larm_world, q_lfa_local)              # keep for hand
set_rotation(scriptOp, 'LeftForeArm', *quat_to_euler(q_lfa_local), Armsmooth)

# RIGHT (rest = +X)
fa_dir_world = vec_sub(landmarks['right_wrist'], landmarks['right_elbow'])
fa_local     = _quat_rotate_vec(quat_inv(q_rarm_world), fa_dir_world)
q_rfa_local  = quat_from_two_vecs([1,0,0], fa_local)
q_rfa_world  = quat_mult(q_rarm_world, q_rfa_local)
set_rotation(scriptOp, 'RightForeArm', *quat_to_euler(q_rfa_local), Armsmooth)
```

---

### Hands

From the hand CHOP. Indices: 0 = wrist, 5 = index MCP, 9 = middle MCP, 17 = pinky MCP.

```python
# LEFT
hand_dir   = vec_sub(l_hand_lms[9], l_hand_lms[0])              # wrist -> middle knuckle
hand_right = vec_sub(l_hand_lms[17], l_hand_lms[5])            # index -> pinky span
q_lhand_world = quat_from_frame_vecs(hand_dir, hand_right, [-1,0,0], [0,0,1])
q_lhand_local = quat_mult(quat_inv(q_lfa_world), q_lhand_world)
set_rotation(scriptOp, 'LeftHand', *quat_to_euler(q_lhand_local), Handsmooth)

# RIGHT (span reversed, rest primary +X)
hand_dir   = vec_sub(r_hand_lms[9], r_hand_lms[0])
hand_right = vec_sub(r_hand_lms[5], r_hand_lms[17])
q_rhand_world = quat_from_frame_vecs(hand_dir, hand_right, [1,0,0], [0,0,1])
q_rhand_local = quat_mult(quat_inv(q_rfa_world), q_rhand_world)
set_rotation(scriptOp, 'RightHand', *quat_to_euler(q_rhand_local), Handsmooth)
```

If no hand CHOP is wired, the wrist orientation falls back to the body pose's wrist / index /
pinky landmarks using the same frame math.

---

### Fingers (FRAME mode)

Each phalanx is a full frame off the palm normal, chained so each joint unwinds against the
previous one.

```python
palm_fwd   = vec_sub(idx_mcp, wrist)
palm_right = vec_sub(idx_mcp, pnk_mcp) if side == 'Left' else vec_sub(pnk_mcp, idx_mcp)
palm_normal  = vec_norm(vec_cross(palm_fwd, palm_right))
rest_primary = [-1,0,0] if side == 'Left' else [1,0,0]

for finger in (Thumb, Index, Middle, Ring, Pinky):
    # phalanx 1: MCP -> PIP, parent = hand world
    q_p1_world = quat_from_frame_vecs(vec_sub(pip, mcp), palm_normal, rest_primary, [0,0,1])
    q_p1_local = quat_mult(quat_inv(q_hand_world_parent), q_p1_world)
    set_rotation(scriptOp, f'{side}Hand{finger}1', *quat_to_euler(q_p1_local), Handsmooth)

    # phalanx 2: PIP -> DIP, parent = phalanx 1 world
    q_p2_world = quat_from_frame_vecs(vec_sub(dip, pip), palm_normal, rest_primary, [0,0,1])
    q_p2_local = quat_mult(quat_inv(q_p1_world), q_p2_world)
    set_rotation(scriptOp, f'{side}Hand{finger}2', *quat_to_euler(q_p2_local), Handsmooth)

    # phalanx 3: DIP -> TIP, parent = phalanx 2 world
    q_p3_world = quat_from_frame_vecs(vec_sub(tip, dip), palm_normal, rest_primary, [0,0,1])
    q_p3_local = quat_mult(quat_inv(q_p2_world), q_p3_world)
    set_rotation(scriptOp, f'{side}Hand{finger}3', *quat_to_euler(q_p3_local), Handsmooth)
```

CURL mode instead solves each joint as a single-axis hinge from the flexion angle
`_joint_flex_deg(a, b, c)` plus a spread term, and doesn't need the world parent frame.

---

### Legs and feet (FK)

```python
# UPPER LEG: vertical -> hip -> knee
leg_dir = vec_sub(landmarks['left_knee'], l_hip)
q_lul   = quat_from_two_vecs([0,-1,0], leg_dir)                  # rest leg = -Y (down)
set_rotation(scriptOp, 'LeftUpLeg', *quat_to_euler(q_lul), Rotationsmooth)

# CALF: knee -> ankle, unwound into thigh space
calf_dir      = vec_sub(landmarks['left_ankle'], landmarks['left_knee'])
calf_local    = _quat_rotate_vec(quat_inv(q_lul), calf_dir)
q_lcalf_local = quat_from_two_vecs([0,-1,0], calf_local)
q_lleg_world  = quat_mult(q_lul, q_lcalf_local)                  # keep for foot
set_rotation(scriptOp, 'LeftLeg', *quat_to_euler(q_lcalf_local), Rotationsmooth)

# FOOT: heel -> toe (forward), heel -> ankle (up)
foot_fwd = vec_sub(landmarks['left_foot_index'], landmarks['left_heel'])
foot_up  = vec_sub(landmarks['left_ankle'],      landmarks['left_heel'])
q_lfoot_world = quat_from_frame_vecs(foot_fwd, foot_up, [0,0,-1], [0,1,0])
q_lfoot_local = quat_mult(quat_inv(q_lleg_world), q_lfoot_world)
set_rotation(scriptOp, 'LeftFoot', *quat_to_euler(q_lfoot_local), Rotationsmooth)

# TOE: ankle -> toe, unwound into foot space
toe_dir = vec_sub(landmarks['left_foot_index'], landmarks['left_ankle'])
q_ltoe_world = quat_from_frame_vecs(toe_dir, foot_up, [0,0,-1], [0,1,0])
q_ltoe_local = quat_mult(quat_inv(q_lfoot_world), q_ltoe_world)
set_rotation(scriptOp, 'LeftToe', *quat_to_euler(q_ltoe_local), Rotationsmooth)
```

Right leg is identical with `right_*` landmarks. Foot/toe rest basis is forward = -Z, up = +Y.

---

### Legs (two-bone IK path, optional)

When Leg IK is on, the knee is solved analytically so the ankle lands exactly, instead of
being taken straight from tracking.

```python
# Law of cosines. R = hip, T = ankle, L1 = thigh, L2 = calf, pole = knee-forward hint.
def _two_bone_ik(R, T, L1, L2, pole):
    to_t = vec_sub(T, R)
    d = vec_len(to_t)
    d = max(abs(L1 - L2) + 1e-4, min(L1 + L2 - 1e-4, d))        # keep reachable
    n = vec_scale(to_t, 1.0 / vec_len(to_t))
    b = vec_sub(pole, vec_scale(n, vec_dot(pole, n)))           # bend axis, perpendicular to R->T
    if vec_len(b) < 1e-5:
        b = vec_cross(n, [1,0,0])
        if vec_len(b) < 1e-5: b = vec_cross(n, [0,0,1])
    b = vec_norm(b)
    cos_a = max(-1.0, min(1.0, (L1*L1 + d*d - L2*L2) / (2.0 * L1 * d)))
    a = math.acos(cos_a)
    return vec_add(R, vec_add(vec_scale(n, L1*math.cos(a)), vec_scale(b, L1*math.sin(a))))
```

The returned knee position feeds the same `quat_from_two_vecs([0,-1,0], dir)` thigh/calf solve
above. IK only changes where the knee is, not how the rotation is built. `Legikweight` blends
FK and IK; ground contact then pins the foot and estimates the floor.

---

### Rest vectors

| Bone | primary rest | secondary rest | builder |
|---|---|---|---|
| Hips | +Y | +X | frame |
| Spine chain | +Y | +X | frame, then slerp-split |
| Neck / Head | +Y | +X | frame |
| Shoulder L / R | -X / +X | -Y | frame, slerp 0.5 |
| Arm L / R | -X / +X | - | two-vec |
| ForeArm L / R | -X / +X | - | two-vec |
| Hand L / R | -X / +X | +Z | frame |
| Finger phalanx | -X / +X | +Z | frame, chained |
| UpLeg / Leg | -Y | - | two-vec |
| Foot / Toe | -Z | +Y | frame |

Left vs right is only the sign of the primary rest vector (and the hand-span direction). The
math is otherwise mirror-identical.
