#!/usr/bin/python3
import requests
import urllib.parse
import getpass
import sys
import os, errno
import re
import shutil
import zipfile
import json

###########
# UTILITY #
###########

headers = {
    "accept": "*/*",
    "user-agent": "curl/7.58.0",
    "accept-language": "en-GB,enq=0.5"
}

def name_url(url):
    name = url.split('/')[-1]
    name = urllib.parse.unquote(name)

    return name

def ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        print('Installing %s -> %s ...' % (s, d))
        if os.path.isdir(s):
            if os.path.exists(d):
                copytree(s, d, symlinks, ignore)
                continue
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

###############
# DOWNLOADING #
###############

def hit_file(url, target, file_name):
    ensure_dir(target)

    original_name = file_name
    file_name = name_url(url)

    if file_name == 'download':
        file_name = original_name

    r = requests.get(url, headers=headers, stream=True, allow_redirects=False)
    if 'location' in r.headers:
        return hit_file(urllib.parse.urljoin(url, r.headers['location']), target, file_name)

    if r.status_code == 404:
        print('Could not find resource at %s!' % (url))
        return None

    if not 'content-length' in r.headers:
        print('Could not determine content size!')
        return None

    size = int(r.headers['content-length'].strip())
    bytesdl = 0

    write_to = os.path.join(target, file_name)

    if os.path.exists(write_to):
        return None

    print('Hitting file %s' % (url))

    with open(write_to, 'wb') as handle:
        for block in r.iter_content(1024):
            handle.write(block)
            bytesdl += len(block)

            sys.stdout.write('\rDownloading %s - %s MB of %s MB' % (
                file_name, str(round(bytesdl / 1024 / 1024, 2))[:4],
                str(round(size / 1024 / 1024, 2))[:4]))
            sys.stdout.flush()

    sys.stdout.write('\rDownloaded file successfully!' + ' ' * (len(file_name) + 10) + '\n')
    sys.stdout.flush()
    return file_name

def curse_file(project_id, file_id, path):
    append = ""

    # Numeric IDs need a "/download" appended to the URI.
    if file_id.isdigit():
        append = "/download"

    return hit_file('https://minecraft.curseforge.com/projects/%s/files/%s%s' % (project_id, file_id, append), path, file_id + '.jar')

########################
# MODPACK ABSTRACTION  #
########################

""" Final message """
def modpack_finish(manifest, minecraft):
    print('Installation complete!')
    print('\n\n\n****************************\n\n\n')
    if 'minecraft' in manifest:
        mver = manifest['minecraft']['version']
        print('This modpack requires Minecraft Version %s!' % (mver))
        if 'modLoaders' in manifest['minecraft']:
            for k in manifest['minecraft']['modLoaders']:
                if "forge" in k['id']:
                    print('\nThis modpack also requires Forge, version %s minimum!' % (k['id']))
                    print('You can find Forge for Minecraft %s at http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_%s.html' % (mver, mver))
                else:
                    print('\nThis modpack also requires %s.' % (k['id']))

    print('\nNow, create a new profile on the Minecraft Launcher with the required versions and the correct game path.')
    print('The game was installed at "%s"' % (os.path.abspath(minecraft)))
    print('That\'s everything!')

""" Download using a manifest """
def commit_download(manifest, mp_dir):
    if "manifestType" in manifest:
        if not manifest["manifestType"] == "minecraftModpack":
            raise ValueError("This is not a valid modpack!")

    name    = manifest['name']
    version = manifest['version']
    author  = manifest['author']

    overrides = None

    print('Starting installation of modpack %s, version %s - created by %s' % (name, version, author))

    # Installation path
    minecraft = os.path.join(mp_dir, 'minecraft')
    mods = os.path.join(minecraft, 'mods')
    ensure_dir(mods)

    if not 'files' in manifest:
        raise ValueError('No files defined in manifest.json!')

    if 'overrides' in manifest:
        overrides = os.path.join(mp_dir, manifest['overrides'])

    skipped = 0
    index = 0

    # Download all files
    for file in manifest['files']:
        index += 1
        print('Downloading file %d out of %d..' % (index, len(manifest['files'])))
        try:
            f = curse_file(str(file['projectID']), str(file['fileID']), mods)
        except Exception as e:
            print('File was skipped due to errors.')
            skipped += 1
            continue

        if not f:
            print('File was skipped.')
            skipped += 1

    print('Finished downloading files. %d total, %d skipped.' % (index - skipped, skipped))

    if overrides:
        print('Installing game files..')
        copytree(overrides, minecraft)

    modpack_finish(manifest, minecraft)

"""Create a manifest out of a list of mods."""
def mod_list_manifest(file):
    # Install a manifest.json directly
    if ".json" in file:
        pathof = "Modpack"
        with open(file, "r") as mf:
            manifest = json.load(mf)

            if "name" in manifest:
                pathof = manifest["name"]

            commit_download(manifest, pathof)
        return

    # Parse Arguments
    arguments = {}
    files = []

    with open(file, "r") as f:
        for line in f:
            line = re.sub(r'\n', '', line)
            if "=" in line:
                data = line.split("=")
                arguments[data[0]] = data[1]
            elif "curseforge" in line:
                srch = re.search(r'/projects/([a-zA-Z0-9_-]+)', line)
                if srch:
                    project_id = srch.group(1)
                    file_id    = "latest"
   
                    if "/files/" in line:
                        srch = re.search(r'files/([a-zA-Z0-9_-]+)', line)
                        if srch:
                            file_id = srch.group(1)

                    files.append({
                        "projectID": project_id,
                        "fileID":    file_id
                    })

    # MC version check
    if not "minecraft" in arguments:
        raise ValueError("Missing minecraft version in the mod list file!")

    # Default values
    if not "name" in arguments:
        arguments["name"] = "My Modpack"

    if not "author" in arguments:
        arguments["author"] = getpass.getuser()

    if not "version" in arguments:
        arguments["version"] = "1.0.0"

    mp_dir = os.path.join('packs', arguments["name"])
    ensure_dir(mp_dir)

    overrides = None
    if "overrides_url" in arguments:
        print("Downloading overrides..")
        fnam = hit_file(arguments["overrides_url"], mp_dir, "overrides.zip")

        if fnam:
            zip_ref = zipfile.ZipFile(fnam, 'r')
            zip_ref.extractall(mp_dir)
            zip_ref.close()
            os.remove(fnam)
            overrides = "overrides"
        else:
            print("Failed to download overrides from URL!")

    elif "overrides" in arguments:
        overrides = arguments["overrides"]

    print("Generating manifest.json ...")

    # Generate a manifest
    manifest = {
        "minecraft": {
            "version": arguments["minecraft"],
            "modLoaders": [],
        },
        "manifestType": "minecraftModpack",
        "manifestVersion": 1,
        "name": arguments["name"],
        "version": arguments["version"],
        "author": arguments["author"],
        "files": files,
    }

    # Ensure existence of overrides
    if overrides and os.path.exists(overrides):
        manifest["overrides"] = overrides

    # Add forge as mod loader
    if "forge" in arguments:
        manifest["minecraft"]["modLoaders"].append({
            "primary": True,
            "id": arguments["forge"],
        })

    # Save manifest
    with open(os.path.join(mp_dir, "manifest.json"), "w") as mf:
        json.dump(manifest, mf, indent=4, sort_keys=True)

    # Start downloading mods
    commit_download(manifest, mp_dir)

#################
# CURSE MODPACK #
#################

""" Download a CurseForge modpack """
def download_modpack(url):
    f = hit_file(url, '.', 'pack.zip')
    if not f:
        raise ValueError('Failed to download modpack!')

    mp_name = re.sub(r'\.zip', '', f)
    mp_dir = os.path.join('packs', mp_name)
    ensure_dir(mp_dir)

    # Extract
    zip_ref = zipfile.ZipFile(f, 'r')
    zip_ref.extractall(mp_dir)
    zip_ref.close()
    os.remove(f)

    # Load the manifest from file
    with open(os.path.join(mp_dir, 'manifest.json')) as json_data:
        manifest = json.load(json_data)

    # Start the actual downloading
    commit_download(manifest, mp_dir)

#######################
# Handle Command Args #
#######################

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError('Please specify an url.')

    mppath = sys.argv[1]
    argccip = ".ccip" in mppath

    if argccip:
        print("Detected: Installation file")
        import xml.etree.ElementTree
        e = xml.etree.ElementTree.parse(mppath).getroot()
        if e.find('project') == None:
            raise AttributeError('Unrecognized ccip file.')
        else:
            r = e.find('project')
            proj_id = r.get('id')
            proj_file = r.get('file')

            download_modpack('https://minecraft.curseforge.com/projects/%s/files/%s/download' % (proj_id, proj_file))
    elif "curseforge" in mppath:
        if not '/files' in mppath:
            mppath += '/files/latest'

        print("Detected: CurseForge URL")

        download_modpack(mppath)
    else:
        print("Detected: File path")

        mod_list_manifest(mppath)
