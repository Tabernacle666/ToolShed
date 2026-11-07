# Decisions
- One repo (ToolShed) holds tools, docs, tasks and the Unreal project (ToolShedGame/).
- Everything lives on D:\gitlink. Engine: Unreal 5.8, launcher build.
- VR: OpenXR over Quest Link, forward shading + MSAA + instanced stereo. Nanite off for VR (not supported in stereo).
- Input: reach amplifier (1:1 near the body, amplified toward the edge of reach) + tool rotation and throw gain.
