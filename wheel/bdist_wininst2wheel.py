#!/usr/bin/env python
import os.path
import re
import sys
import tempfile
import zipfile
import wheel.bdist_wheel
import distutils.dist
from distutils.archive_util import make_archive
from shutil import rmtree

egg_info_re = re.compile(r'''(?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>.+?))?(-(?P<arch>.+?))?.egg''', re.VERBOSE)

bdist_wininst_info_re = re.compile(r'''^(?P<name>.+?)-(?P<ver>.+)\.
    (?P<arch>\w+-\w+)-(?P<pyver>py\d.+).exe''', re.VERBOSE)

def bdist_wininst2wheel(path):
    info = bdist_wininst_info_re.match(os.path.basename(path)).groupdict()
    dist_info = "%(name)s-%(ver)s" % info
    datadir = "%s.data/" % dist_info
    
    # rewrite paths to trick ZipFile into extracting an egg
    # XXX grab wininst .ini
    bdw = zipfile.ZipFile(path)
    root_is_purelib = True
    for zipinfo in bdw.infolist():
        if zipinfo.filename.startswith('PLATLIB'):
            root_is_purelib = False
            break
    if root_is_purelib:
        paths = {'purelib':''}
    else:
        paths = {'platlib':''}
    for zipinfo in bdw.infolist():
        key, basename = zipinfo.filename.split('/', 1)
        key = key.lower()
        basepath = paths.get(key, None)
        if basepath is None:
            basepath = datadir + key.lower() + '/'
        oldname = zipinfo.filename
        newname = basepath + basename
        zipinfo.filename = newname
        del bdw.NameToInfo[oldname]
        bdw.NameToInfo[newname] = zipinfo
    dir = tempfile.mkdtemp(suffix="_b2w")
    bdw.extractall(dir)
    
    # egg2wheel
    abi = 'noabi'
    pyver = info['pyver'].replace('.', '')
    arch = (info['arch'] or 'noarch').replace('.', '_').replace('-', '_')
    if arch != 'noarch':
        # assume all binary eggs are for CPython
        pyver = 'cp' + pyver[2:]
    wheel_name = '-'.join((
            dist_info,
            pyver,
            abi,
            arch
            ))
    bw = wheel.bdist_wheel.bdist_wheel(distutils.dist.Distribution())
    bw.root_is_purelib = root_is_purelib
    dist_info_dir = os.path.join(dir, '%s.dist-info' % dist_info)
    bw.egg2dist(os.path.join(dir, "%(name)s-%(ver)s-%(pyver)s.egg-info" % info),
                dist_info_dir)
    bw.write_wheelfile(dist_info_dir, packager='egg2wheel')
    bw.write_record(dir, dist_info_dir)
    filename = make_archive(wheel_name, 'zip', root_dir=dir)
    os.rename(filename, filename[:-3] + 'whl')
    rmtree(dir)
    

if __name__ == "__main__":
    bdist_wininst2wheel(sys.argv[1])
    
        