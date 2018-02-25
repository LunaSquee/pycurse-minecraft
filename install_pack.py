#!/usr/bin/python2
import requests
import urllib.parse
import sys
import os, errno
import re
import shutil
import zipfile
import json

headers = {
    "accept": "*/*",
    "user-agent": "curl/7.58.0",
    "accept-language": "en-GB,enq=0.5"
}

def name_url(url):
    name = url.split('/')[-1]
    name = urllib.parse.unquote(name)

    return name

def project_by_id(pid):
    r = requests.get('https://mods.curse.com/project/' + pid, headers=headers, allow_redirects=False)

    if not 'location' in r.headers:
        return None

    loc = r.headers['location']
    name = name_url(loc)
    name = re.sub(r'^\d+-', '', name)

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

def hit_file(url, target, file_name):
    print('Hitting file %s' % (url))
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

    size = int(r.headers['content-length'].strip())
    bytesdl = 0

    write_to = os.path.join(target, file_name)

    if os.path.exists(write_to):
        print('File found - skipping download..')
        return None

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
    return hit_file('https://minecraft.curseforge.com/projects/%s/files/%s/download' % (project_id, file_id), path, file_id + '.jar')

def modpack_finish(manifest, minecraft):
    if 'minecraft' in manifest:
        mver = manifest['minecraft']['version']
        print('This modpack requires Minecraft Version %s!' % (mver))
        if 'modLoaders' in manifest['minecraft']:
            for k in manifest['minecraft']['modLoaders']:
                try:
                    f = k['id'].index('forge')
                except ValueError:
                    f = None

                if f == 0:
                    print('\nThis modpack also requires Forge, version %s minimum!' % (k['id']))
                    print('You can find Forge for Minecraft %s at http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_%s.html' % (mver, mver))
                else:
                    print('\nThis modpack also requires %s.' % (k['id']))

    print('\nNow, create a new profile on the Minecraft Launcher with the required versions and the correct game path.')
    print('The game was installed at %s' % (os.path.abspath(minecraft)))
    print('That\'s everything!')

def modpack_step(mp_name, mp_dir):
    with open(os.path.join(mp_dir, 'manifest.json')) as json_data:
        manifest = json.load(json_data)

    name = manifest['name']
    version = manifest['version']
    author = manifest['author']

    overrides = None

    print('Starting setup of modpack %s, version %s - created by %s' % (name, version, author))

    if not 'files' in manifest:
        raise ValueError('No files defined in manifest.json!')

    if 'overrides' in manifest:
        overrides = os.path.join(mp_dir, manifest['overrides'])

    minecraft = os.path.join(mp_dir, 'minecraft')
    mods = os.path.join(minecraft, 'mods')
    ensure_dir(mods)

    skipped = 0
    index = 0

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

    print('Installation complete!')

    modpack_finish(manifest, minecraft)

def download_modpack(url):
    f = hit_file(url, '.', 'pack.zip')
    if not f:
        raise ValueError('Failed to download modpack!')

    mp_name = re.sub(r'\.zip', '', f)
    mp_dir = os.path.join('packs', mp_name)

    ensure_dir(mp_dir)

    zip_ref = zipfile.ZipFile(f, 'r')
    zip_ref.extractall(mp_dir)
    zip_ref.close()
    os.remove(f)

    modpack_step(mp_name, mp_dir)

# Handle Command Args

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError('Please specify an url.')

    mppath = sys.argv[1]

    try:
        argccip = mppath.index('.ccip')
    except ValueError:
        argccip = False

    if argccip:
        import xml.etree.ElementTree
        e = xml.etree.ElementTree.parse(mppath).getroot()
        if e.find('project') == None:
            raise AttributeError('Unrecognized ccip file.')
        else:
            r = e.find('project')
            proj_id = r.get('id')
            proj_file = r.get('file')
            download_modpack('https://minecraft.curseforge.com/projects/%s/files/%s/download' % (proj_id, proj_file))
    else:
        try:
            mppath.index('/files')
        except ValueError:
            mppath += '/files/latest'

        download_modpack(mppath)
