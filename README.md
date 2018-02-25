# Download CurseForge Minecraft Mod Packs on Linux
**Requires Python 3.**

All you have to do is `python install_pack.py https://minecraft.curseforge.com/projects/MODPACK_NAME_HERE` and follow the instructions! This script will automatically
* Download the latest version of the modpack (unless `/files/:fileId` with a custom ID is appended to the url)
* Download all the mods listed in `manifest.json` one after another
* Apply any and all `overrides`
* Create a ready-to-use directory for the official Minecraft Launcher!

Please note that the link must be a [CurseForge](https://minecraft.curseforge.com/) project.

## Installing Twitch Client files
You can also pass one of those `ccip` files to this script! These files can be obtained when pressing the 'Install' button on [CurseForge](https://www.curseforge.com/minecraft/modpacks)

Example: `python install_pack.py pokemon-adventure-v-1-2-1.ccip`
