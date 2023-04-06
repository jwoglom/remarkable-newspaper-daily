#!/usr/bin/env python3
import argparse
import subprocess
import collections

# https://github.com/subutux/rmapy/pull/35
import rmapy.const
rmapy.const.AUTH_BASE_URL = "https://webapp-prod.cloud.remarkable.engineering"
rmapy.const.BASE_URL = "https://internal.cloud.remarkable.com"
rmapy.const.DEVICE_TOKEN_URL = rmapy.const.AUTH_BASE_URL + "/token/json/2/device/new"
rmapy.const.USER_TOKEN_URL = rmapy.const.AUTH_BASE_URL + "/token/json/2/user/new"

from rmapy.api import Client

from sources.wapo import WapoSource
from sources.nyt import NytSource

from datetime import datetime

sources = {
    "wapo": WapoSource,
    "nyt": NytSource
}

def parse_args():
    a = argparse.ArgumentParser(description="Writes daily newspaper PDFs to reMarkable cloud")
    a.add_argument('--sources', nargs='+', choices=list(sources.keys()), help='Sources to utilize')
    a.add_argument('--max-days', type=int, default=1, help='Maximum number of days for each source to keep')
    a.add_argument('--folder', default='Newspapers', help='Folder title to write to')
    a.add_argument('--only-front', action="store_true", help='Only fetch front page')
    a.add_argument('--register-device-token', help='For initial authentication: device token')
    return a.parse_args()
    

def main(args):
    rm = Client()
    if not rm.is_auth():
        print("Not authenticated")
        if args.register_device_token:
            print("Using --register-device-token: '%s'" % args.register_device_token)
            rm.register_device(args.register_device_token)
            rm.renew_token()
            if rm.is_auth():
                print("Success!")
            else:
                print("Error -- still not authenticated")
                exit(1)
        else:
            print("Please authenticate with --register-device-token")
            print("Receive a token at https://my.remarkable.com/device/desktop/connect")
            exit(1)
    
    # From here, use the go client
    
    day = datetime.now()
    date = '{}{}{}'.format(day.year, '%02d'%day.month, '%02d'%day.day)

    source_prefixes = []
    for name in args.sources:
        src = sources[name](date, args.only_front)
        source_prefixes.append(src.name_prefix)

    ls = subprocess.run(["rmapi", "-ni", "ls", args.folder], capture_output=True)
    if ls.returncode != 0 and "directory doesn't exist" in str(ls.stderr):
        print("Creating folder", args.folder)
        mk = subprocess.run(["rmapi", "mkdir", args.folder], capture_output=True)
        if mk.returncode != 0:
            print("Couldn't create directory:", mk.stdout, mk.stderr)
            exit(mk.returncode)
    elif ls.returncode != 0:
        print("Couldn't ls:", ls.stdout, ls.stderr)
        exit(ls.returncode)

    files = ls.stdout.decode().splitlines()
    files = list(map(lambda x: x.split('\t'), files))
    files = list(filter(lambda x: x[0] == '[f]', files))
    files = list(map(lambda x: x[1], files))
    print("Files on reMarkable in %s: %s" % (args.folder, files))

    dates_for = collections.defaultdict(set)
    for f in files:
        for pfx in source_prefixes:
            if f.startswith(pfx):
                sfx = f[len(pfx)+1:]
                dates_for[pfx].add(sfx)

    pdfs = {}
    for name in args.sources:
        src = sources[name](date, args.only_front)
        if src.name_prefix in dates_for:
            if date in dates_for[src.name_prefix]:
                print("Skipping because already present on reMarkable for {}: {}".format(date, src.name_prefix))
                continue
        pdfs[src.name_prefix] = src.get_pdf()

    for key, val in pdfs.items():
        print("Writing to reMarkable", key, val)

        write = subprocess.run(["rmapi", "-ni", "put", val, args.folder], capture_output=True)
        if write.returncode != 0:
            print("Couldn't write file:", write.stdout, write.stderr)
            exit(write.returncode)

    
        
        

if __name__ == '__main__':
    args = parse_args()
    main(args)