#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
# git-meta --- Handle file metadata in git

"""

# Copyright © 2014 Sébastien Gross <seb•ɑƬ•chezwam•ɖɵʈ•org>
# Created: 2014-02-26
# Last changed: 2014-03-03 14:26:03

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.


__author__ = "Sébastien Gross"
__copyright__ = """Copyright © 2014 Sébastien Gross <seb•ɑƬ•chezwam•ɖɵʈ•org>"""

import os, sys, subprocess
import pipes
from stat import *
import pwd
import grp
import json
import argparse
import pprint
import datetime

def run(cmd):
    """run cmd"""
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    proc.wait()
    out, err = proc.communicate()
    rc = proc.returncode
    if rc == 0:
        return out
    else:
        sys.stdout.write("Failed (%s): %s\n" %
                         (rc, ' '.join(pipes.quote(arg) for arg in cmd)))
        sys.stderr.write(err)
        sys.exit(1)

def get_file_stats(f, args):
    st = os.stat(f)
    ret = { 'mode': st.st_mode, 'mtime': st.st_mtime }
    if args['numeric_owner'] is True:
        ret['uid'] = st.st_uid
        ret['gid'] = st.st_gid
    elif args['owner'] is True:
        ret['uid'] = pwd.getpwuid(st.st_uid).pw_name,
        ret['gid'] =  grp.getgrgid(st.st_gid).gr_name
    return ret
    

def git_get_files_attributs(args):
    """ """
    out = run(['git', 'ls-files', '-z'])
    files=out.split('\0')
    files.sort()
    rows = {}
    for f in files:
        if not(os.path.isfile(f)):
            continue
        rows[f] = get_file_stats(f, args)
        while not (f == '' or f == '.'):
            if not rows.has_key(f):
                rows[f] = get_file_stats(f, args)
            f = os.path.dirname(f)
    metadata = open(args['data'], 'w')
    json.dump(rows, metadata, indent=0)
    metadata.close()

def load_metadata(args):
    """Load metada from file"""
    p = open(args['data'], 'r')
    ret = json.load(p)
    p.close()
    return ret

def dump_database(args):
    data = load_metadata(args)
    entries = data.keys()
    entries.sort()
    print('%s %s %s %s %s' %( 'mode'.center(6), 'mtime'.center(19), 'uid'.center(6), 'gid'.center(6), 'file' ))
    for entry in entries:
        row = ['%.6o' % data[entry]['mode']]
        if data[entry].has_key('mtime'):
            row.append(datetime.datetime.fromtimestamp(data[entry]['mtime']).strftime('%Y-%m-%d %H:%M:%S'))
        if data[entry].has_key('uid'):
            row.append('%6s' % data[entry]['uid'])
        if data[entry].has_key('gid'):
            row.append('%6s' % data[entry]['gid'])
        if os.path.isfile(entry):
            row.append(entry)
        else:
            row.append('%s/' % entry)
        print ' '.join(row)

def git_set_file_attributs(args):
    data = load_metadata(args)
    for file in data.keys():
        if args['verbose']: sys.stdout.write('%s:' % file)
        if (args['skip_perms'] is False) or not(data[file].has_key('mode')):
            if args['verbose']: sys.stdout.write(' mode:%6o' % data[file]['mode'])
            os.chmod(file, data[file]['mode'])
        if (args['skip_mtime'] is False)  or not(data[file].has_key('mtime')):
            if args['verbose']: sys.stdout.write(' mtime:%s' % datetime.datetime.fromtimestamp(data[file]['mtime']).strftime('%Y-%m-%d %H:%M:%S'))
            os.utime(file, (data[file]['mtime'], data[file]['mtime']))
        uid = -1
        gid = -1
        if (args['skip_user'] is False) or not(data[file].has_key('uid')) or \
           (args['skip_group'] is False) or not(data[file].has_key('gid')):
            if (args['skip_user'] is False) or not(data[file].has_key('uid')):
                if isinstance(data[file]['uid'], int):
                    uid = data[file]['uid']
                else:
                    uid = pwd.getpwnam(data[file]['uid']).pw_uid
            if (args['skip_group'] is False) or not(data[file].has_key('gid')):
                if isinstance(data[file]['gid'], int):
                    gid = data[file]['gid']
                else:
                    gid = grp.getgrnam(data[file]['gid']).gr_gid
            if args['verbose']: sys.stdout.write(' user:%s group:%s' % (uid, gid))
            os.chown(file, uid, gid)
        if args['verbose']: sys.stdout.write('\n')


def parse_cmd_line():
    """Parse command line arguments"""
    args = argparse.ArgumentParser(description="Command line parser")

    args.add_argument('--data', help='Path to database', metavar='PATH',
                      default='.gitmeta')
    args.add_argument('-f', '--force', help='Force to commit',
                      default=False, action='store_true')
    args.add_argument('-O', '--owner', help='Add symbolic owner',
                      default=False, action='store_true')
    args.add_argument('-o', '--numeric-owner', help='Add numeric owner',
                      default=False, action='store_true')
    args.add_argument('-a', '--add-to-git', help='Commit database to git',
                      default=False, action='store_true')
    args.add_argument('-U', '--skip-user', help='Skip user during restore',
                      default=False, action='store_true')
    args.add_argument('-G', '--skip-group', help='Skip group during restore',
                      default=False, action='store_true')
    args.add_argument('-P', '--skip-perms', help='Skip perms during restore',
                      default=False, action='store_true')
    args.add_argument('-M', '--skip-mtime', help='Skip mtime during restore',
                      default=False, action='store_true')
    args.add_argument('-v', '--verbose', help='Show operations',
                      default=False, action='store_true')


    sp_cmd = args.add_subparsers(help='Command', dest='cmd')

    sp_cmd.add_parser('init', help='Setup hooks in .git directory')
    sp_cmd.add_parser('get', help='Store metadata')
    sp_cmd.add_parser('set', help='Restore metadata')
    sp_cmd.add_parser('dump', help='Dump metadata')

    return args.parse_args().__dict__


def git_init_hooks():
    """Initialize git hooks"""
    out = run(['git', 'rev-parse', '--git-dir'])
    dir = out.split('\n')[0]
    f = open('%s/hooks/pre-commit' % dir, 'w')
    f.write( "#!/bin/sh\n\n"
    "git meta -a get || true\n")
    f.close()
    f = open('%s/hooks/post-merge' % dir, 'w')
    f.write( "#!/bin/sh\n\n"
    "git meta -a set || true\n")
    f.close()

def __init__():
    args = parse_cmd_line()
    if args['cmd'] == 'get':
        git_get_files_attributs(args)
    elif args['cmd'] == 'dump':
        dump_database(args)
    elif args['cmd'] == 'set':
        git_set_file_attributs(args)
    elif args['cmd'] == 'init':
        git_init_hooks()
if __name__ == "__main__":
    __init__()