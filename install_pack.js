#!/usr/bin/env node
'use strict'
const cprog = require('child_process')
const url = require('url')
const fs = require('fs')
const path = require('path')

let currentPWD = path.resolve(__dirname)

function rmdir (d) {
  if (fs.existsSync(d)) {
    fs.readdirSync(d).forEach(function(file) {
      var C = d + '/' + file
      if (fs.statSync(C).isDirectory()) rmdir(C)
      else fs.unlinkSync(C)
    })
    fs.rmdirSync(d)
  }
}

let overrides = '/overrides'
let manifest

function HTTPRequest(link, callback) {
  let parsed = url.parse(link)
  let opts = {
    host: parsed.hostname,
    port: parsed.port,
    path: parsed.path,
    'headers':{
      'User-Agent': 'curl/7.53.1',
      'Accept': '*/*',
      'Accept-Language': 'en-GB,enq=0.5'
    }
  }

  const httpModule = parsed.protocol === 'https:' ? require('https') : require('http')

  httpModule.get(opts, function (res) {
    let data = ''
    res.on('data', function (chunk) {
      data += chunk
    })

    res.on('end', function () {
      callback(null, data, res)
    })

  }).on('error', function (e) {
    callback(e.message, null, null)
  })
}

function determineProjectByID (id, cb) {
  HTTPRequest('https://mods.curse.com/project/' + id, (error, data, response) => {
    if (!response.headers.location || error !== null) return cb('noloc', null)

    let projectName = response.headers.location.split('/')
    projectName = projectName[projectName.length - 1]
    projectName = decodeURIComponent(projectName.replace(/^\d+-/g, ''))

    if (projectName) return cb(null, projectName)

    cb('failed', null)
  })
}

function progress_bar (barsize, percentage) {
  let bar = ''
  let cnt = Math.floor(barsize * percentage)

  for(let i=1; i<barsize; i++) {
    if(i<=cnt)
      bar += '#'
    else
      bar += '-'
  }

  return '['+bar+'] '+Math.floor(percentage * 100)+'%'
}

function overrideLine (text) {
  process.stdout.clearLine()
  process.stdout.cursorTo(0)
  process.stdout.write(text)
}

function hitFile (link, target, fname, cb) {
  let parsed = url.parse(link)
  let opts = {
    host: parsed.hostname,
    port: parsed.port,
    path: parsed.path,
    'headers':{
      'User-Agent': 'curl/7.53.1',
      'Accept': '*/*',
      'Accept-Language': 'en-GB,enq=0.5'
    }
  }

  let originalFname = fname
  fname = parsed.path.split('/')
  fname = fname[fname.length - 1]
  fname = decodeURIComponent(fname)

  const httpModule = parsed.protocol === 'https:' ? require('https') : require('http')

  let mb
  let mbtotal

  console.log('Hitting ' + link)

  httpModule.get(opts, function(res) {
    let len = res.headers['content-length']

    if (res.headers.location) {
      hitFile(url.resolve(link, res.headers.location), target, originalFname, cb)
      return
    }

    if (res.statusCode === 404) {
      return cb('Failed download of ' + originalFname, null)
    }

    let exists = false

    try {
      exists = fs.existsSync(target + fname)
    } catch (e) {
      exists = false
    }

    if (exists) return cb(null, fname)

    let fileee = fs.createWriteStream(target + fname)
    res.on('data', function (data) {
      fileee.write(data)
      let progress = (fileee.bytesWritten / len).toFixed(2)
      mb = (fileee.bytesWritten / 1024 / 1024).toFixed(1)
      mbtotal = (len / 1024 / 1024).toFixed(1)
      overrideLine('Downloading ' + fname + ' ' + mb + 'MB of ' + mbtotal + 'MB ' + progress_bar(10, progress))
    }).on('end', function () {
      overrideLine('Downloading ' + fname + ' ' + mbtotal + 'MB - DONE')
      process.stdout.write('\n')
      cb(null, fname)
    }).on('error', function (err) {
      process.stdout.write('\n')
      cb(err, null)
    })
  })
}

function curseFile (projectId, fileId, vpath, cb) {
  determineProjectByID(projectId, (err, project) => {
    if (err) return cb(err, null)
    hitFile('https://minecraft.curseforge.com/projects/' + project + '/files/' + fileId + '/download', vpath, fileId + '.jar',
      (err, filename) => {
        if (err) return cb(err, null)
        cb(null, filename)
      })
  })
}

function makeDir (dirPath, cb) {
  if (!fs.existsSync(dirPath)) {
    try {
      fs.mkdirSync(dirPath);
    } catch(e) {
      if ( e.code != 'EEXIST' ) return cb(e.code, null)
    }
  }
}

function patchDirs(dir, patch) {
  fs.readdirSync(patch).forEach(function(file) {
    if (fs.existsSync(dir + '/' + file)) {
      if (fs.statSync(dir + '/' + file).isDirectory()) {
        return patchDirs(dir + '/' + file, patch + '/' + file)
      }
      fs.unlinkSync(dir + '/' + file)
    }
    fs.renameSync(patch + '/' + file, dir + '/' + file)
  })
}

function modpackStep2 (fpathc, name, cb) {
  if (fs.existsSync(fpathc + overrides)) {
    fs.readdirSync(fpathc + overrides).forEach(function(file) {
      var C = fpathc + overrides + '/' + file
      if (fs.existsSync(fpathc + '/minecraft/' + file) && fs.statSync(fpathc + '/minecraft/' + file).isDirectory()) {
        patchDirs(fpathc + '/minecraft/' + file, C)
        return
      } else if (fs.existsSync(fpathc + '/minecraft/' + file)) {
        fs.unlinkSync(fpathc + '/minecraft/' + file)
      }
      fs.renameSync(C, fpathc + '/minecraft/' + file)
    })
  }
  console.log('* Cleaning up..')
  rmdir(fpathc + overrides)

  cb(null, 'Modpack downloaded successfully.')

  console.log('\nThis modpack requires Minecraft Version ' + manifest.minecraft.version)
  if (manifest.minecraft.modLoaders.length) {
    for (let i in manifest.minecraft.modLoaders) {
      let ml = manifest.minecraft.modLoaders[i]
      console.log('You\'ll also need: ' + ml.id + ' or later!')
      if (ml.id.indexOf('forge') === 0) {
        console.log('Forge can be downloaded from http://files.minecraftforge.net/maven/net/minecraftforge/forge/index_' + manifest.minecraft.version + '.html')
      }
    }
  }
  console.log('\nYour game is installed at `' + fpathc + '/minecraft`')
  console.log('Create a new profile on the Minecraft Launcher using this path and the mod loaders specified beforehand.')
}

function modpackStep1 (fpathc, name, cb) {
  console.log('* Checking for manifest.json')

  try {
    manifest = require(fpathc + '/manifest.json')
  } catch (e) {
    cb('no manifest', null)
    return
  }

  let zipname = name
  name = manifest.name || zipname

  console.log('Starting setup of modpack ' + name + ' version ' + manifest.version + ' by ' + manifest.author + '..')
  
  if (name !== zipname) {
    if (fs.existsSync(currentPWD + '/' + name)) {
      console.log('Found an exising installation, checking for version..')
      let manifestExisting = require(currentPWD + '/' + name + '/manifest.json')
      if (manifestExisting.version !== manifest.version) {
        console.log('This is a new version, removing old..')
        rmdir(currentPWD + '/' + name + '/mods')
        console.log('Updating..')
      } else {
        console.log('Version is current, verifying installation..')
      }
      patchDirs(currentPWD + '/' + name, currentPWD + '/' + zipname)
      rmdir(currentPWD + '/' + zipname)
    } else {
      fs.renameSync(currentPWD + '/' + zipname, currentPWD + '/' + name)
    }
    fpathc = currentPWD + '/' + name
  }

  console.log('* Getting mod list..')
  if (!manifest.files) {
    return cb('No files in manifest', null)
  }

  console.log('* Starting downloads..')

  if (manifest.overrides != null) {
    overrides = '/' + manifest.overrides
  } 

  makeDir(fpathc + '/minecraft', cb)
  makeDir(fpathc + '/minecraft/mods', cb)

  let files = manifest.files

  function downloadNext (index) {
    let file = files[index]

    curseFile(file.projectID, file.fileID, fpathc + '/minecraft/mods/', (err, filePath) => {
      if (err) return cb(err, null)

      console.log('[' + (index + 1) + '/' + files.length + '] ' + filePath + ' OK')

      if (index === files.length - 1) {
        console.log('* Applying patches..')
        modpackStep2(fpathc, name, cb)
        return
      }

      downloadNext(index + 1)
    })
  }

  downloadNext(0)
}

function downloadModpackFile (url, cb) {
  makeDir(currentPWD + '/packs', cb)
  hitFile(url + '/files/latest', '', 'download', (err, filename) => {
    if (err) return cb(err, null)

    if (filename.indexOf('.zip') === -1) {
      return cb('Unsupported archive: Most likely not a mod pack.', null)
    }

    let mpName = filename.replace('.zip', '')
    let mpDir = currentPWD + '/packs/' + mpName

    makeDir(mpDir, cb)

    console.log('* Extracting archive..')

    cprog.exec('unzip -q -o "' + filename + '" -d "' + mpDir + '"', (err, stdout, stderr) => {
      if (err) return cb(err, null)
      currentPWD = currentPWD + '/packs'
      fs.unlinkSync(filename)
      modpackStep1(mpDir, mpName, cb)
    })
  })
}

if (process.argv[2] != null) {
  downloadModpackFile(process.argv[2], (err, msg) => {
    if (err) {
      console.error('An error occured: ' + err)
      return
    }
    console.log(msg)
  })
}
