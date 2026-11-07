# One-time manual steps (after signing out and back in)

## A. Unreal Engine 5.8
1. Open Epic Games Launcher, sign in.
2. Unreal Engine > Library > "+" next to Engine Versions > choose 5.8.
3. Install > accept terms > location: D:\gitlink\Engines
4. Options: untick Android, iOS, Linux, TVOS > Apply > Install.
5. Launcher settings: set the Vault cache location to D:\gitlink\cache\Vault.

## B. Meta Quest Link
1. Install the Meta Quest Link PC app from meta.com.
2. In the app: Settings > General > OpenXR Runtime > set Meta Quest Link as active.
3. Connect the Quest 3 with a USB-C cable and enable Link in the headset.

## C. Create the Unreal project (only time the New Project window is needed)
1. Launch Unreal 5.8 from the launcher.
2. Games > Virtual Reality > project type C++ > no starter content.
3. Location: D:\gitlink\ToolShed    Name: ToolShedGame
4. Create. When the editor opens, close it.
5. Tell GPT: "project created". GPT commits it with Git LFS.
