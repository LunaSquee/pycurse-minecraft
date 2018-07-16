# Download CurseForge Minecraft Mod Packs on Linux
**Requires Python 3.**

All you have to do is `python install_pack.py https://minecraft.curseforge.com/projects/MODPACK_NAME_HERE` and follow the instructions! This script will automatically
* Download the latest version of the modpack (unless `/files/:fileId` with a custom ID is appended to the url)
* Download all the mods listed in `manifest.json` one after another
* Apply any and all `overrides`
* Create a ready-to-use directory for the official Minecraft Launcher!

Please note that the link must be a [CurseForge](https://minecraft.curseforge.com/) project.

## Installing from Files
Simplest way to create a modpack is using regular text files. This method also generates a `manifest.json` file automatically! Example modpack definition:
```
name=Example Pack
minecraft=1.12.2
forge=forge-14.23.4.2705
https://minecraft.curseforge.com/projects/chisel
https://minecraft.curseforge.com/projects/jei
https://minecraft.curseforge.com/projects/iron-chests/files/2573525
... list of urls ...
```

You can also install a `manifest.json` file directly.

### Examples
* `python install_pack.py pokemon-adventure-v-1-2-1.ccip`
* `python install_pack.py my-mods.txt`
* `python install_pack.py manifest.json`
