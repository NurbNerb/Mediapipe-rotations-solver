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



       MediaPipe → Rig Retargeter (pure-Python, TouchDesigner Script CHOP)



       Feed it MediaPipe World landmark positions, get back clean per-bone rotations for a humanoid rig — hips to fingertips, in real time, inside TouchDesigner. It's one Python file, no external libraries, and it drops straight into a Script CHOP. Invert x y landmarks to -1 to align mediapipe body to match 3d rig orientation. 

TL;DR
In: a CHOP of MediaPipe world landmarks — channels named left_shoulder:x/y/z, right_elbow:x/y/z, … (optional :v confidence per joint). Optional 21-point hand CHOPs.
Out: rig rotation channels — mixamorig_LeftArm:rx/ry/rz, …:tx/ty/tz, etc.
How: landmarks → direction vectors → quaternions → parent-relative locals → Euler in your rig's rotation order, One-Euro-smoothed the whole way.
Cost: zero pip installs. It runs on TD's built-in Python.


One Euro rotation filter --	Adaptive jitter/latency trade-off, per bone
Confidence-driven smoothing --	Low-visibility joints (:v) get smoothed harder automatically
Two-bone leg IK + ground contact --	Analytic law-of-cosines knee solve, floor estimation, foot pin / anti-slide
Predictive lookahead  --	Velocity+acceleration extrapolation to cancel end-to-end latency
Bone-length depth fit  --	Learns rest bone lengths to recover believable monocular depth
Turn continuity gate --	Rejects 1-frame torso pops from MediaPipe's front/back ambiguity
Facing-flip lock / back-facing fix --	Holds orientation through profile and away-from-camera turns
Occlusion repair --	Coasts hidden joints instead of snapping
Arm anti-clip --	Torso-capsule pushout so arms don't sink into the chest
Multi-person --	p1…pN channel sets, encounter-ordered, with pN_present flags
Hands + fingers --	Optional 21-landmark hand CHOPs; FRAME or angle-based CURL finger solve

Rig targets out of the box: Mixamo, HumanIK, Unreal (UE4), and Custom.

Three modes on one operator:

MOCAP — live MediaPipe capture (the default path)
ANIM — pass a CHOP animation source through the same channel plumbing 
SKELETON — read rotations straight off TD Bone COMPs and re-emit them (NOT WORKING YET)


Create a Script CHOP and paste this file into its DAT (or point it at the file).
Wire your MediaPipe world landmarks as name:x/y/z channels, Visibility needs to be renamed to (:v) 
Mediapipes default body comes in upside down and revered. So Be sure to invert on x and Y -1 and leave Z on +1. This ensures your mediapipe body aligns with the orientation a 3d rig is expecting. Also the json output from mediapipe outputs $.landmarks and $.worldLandmakrs. We use screen space landmarks ( $.landmakrs) for hips root position. Then we use $.worldLandmarks for the rest of the limbs. WARNING IF YOU DO NOT USE WORLD LANDMAKRS ($.worldLandmarks) YOU WILL NOT GET THE ANGLES OUTPUT. 

On the Retargeter page: pick your Target Rig Type, leave Mode on MOCAP, make sure Enable Retargeter System is on.
Hit Load Optimized Filter Presets for sane smoothing defaults and drive a rig.

Landmark names follow standard MediaPipe Pose naming (left_shoulder, right_hip, nose, left_ear, left_foot_index, …). Channel names are case-insensitive and the separator before the axis is flexible (left_wrist:x, left_wrist_x, 0:tx all resolve).

Each solved bone writes rig_bone:rx/ry/rz (degrees), plus :tx/ty/tz for the root and, when LimbXYZ is on, for the tracked limb joints. Example (Mixamo):

mixamorig_LeftForeArm:rx   mixamorig_LeftForeArm:ry   mixamorig_LeftForeArm:rz
mixamorig_Hips:tx          mixamorig_Hips:ty          mixamorig_Hips:tz

Multi-person prefixes everything: p1_mixamorig_LeftArm:rx, p2_…, plus p1_present.
