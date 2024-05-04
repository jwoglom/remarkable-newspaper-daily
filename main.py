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
    a.add_argument('--max-days', type=int, default=7, help='Maximum number of days for each source to keep')
    a.add_argument('--folder', default='Newspapers', help='Folder title to write to')
    a.add_argument('--only-front', action="store_true", help='Only fetch front page')
    a.add_argument('--dry-run', action="store_true", help='Dry run only, do not upload')
    a.add_argument('--skip-fetch', action="store_true", help='Skip fetching as dry run')
    a.add_argument('--date', default=None, help='override the current day used to fetch newspapers, in YYYYMMDD format')
    a.add_argument('--register-device-token', help='For initial authentication: device token')
    a.add_argument('--relogin-command', help='Command to run when relogin is required to remarkable (e.g. send a notification)', default=None)
    return a.parse_args()


def main(args):
    try:
        rm = Client()
    except Exception as e:
        if args.relogin_command:
            subprocess.run(['/bin/bash', '-c', args.relogin_command])
        raise e
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
            if args.relogin_command:
                subprocess.run(['/bin/bash', '-c', args.relogin_command])
            exit(1)

    # From here, use the go client

    day = datetime.now()
    date = '{}{}{}'.format(day.year, '%02d'%day.month, '%02d'%day.day)
    if args.date:
        date = args.date

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
        if not args.skip_fetch:
            pdf = src.get_pdf()
            if pdf:
                pdfs[src.name_prefix] = pdf

    for key, val in pdfs.items():
        if args.dry_run:
            print("Would write to reMarkable", key, val)
            continue

        print("Writing to reMarkable", key, val)

        write = subprocess.run(["rmapi", "-ni", "put", val, args.folder], capture_output=True)
        if write.returncode != 0:
            print("Couldn't write file:", write.stdout, write.stderr)
            exit(write.returncode)

    if args.max_days > -1:
        date_to_files = collections.defaultdict(set)
        for pfx, sfxs in dates_for.items():
            for sfx in sfxs:
                date_to_files[sfx].add(pfx)
        
        max_count_for_paper = max([len(i) for i in dates_for.values()])
        if max_count_for_paper > args.max_days:
            print(f'{max_count_for_paper=}')

            all_dates = list(sorted(date_to_files.keys()))
            dates_to_delete = all_dates[:len(all_dates)-args.max_days]
            items_to_delete = []
            for sfx in dates_to_delete:
                for pfx in date_to_files[sfx]:
                    items_to_delete.append(pfx+" "+sfx)

            would = 'would delete' if args.dry_run else 'deleting'
            print("Since there are {} dates and max_days={}, {} {} dates: {}".format(max_count_for_paper, args.max_days, would, len(items_to_delete), dates_to_delete))
            print("Deleting items: {}".format(items_to_delete))

            if not args.dry_run:
                for item in items_to_delete:
                    rm = subprocess.run(["rmapi", "-ni", "rm", args.folder+"/"+item], capture_output=True)
                    if rm.returncode != 0:
                        print("Couldn't delete file:", rm.stdout, rm.stderr)
                        exit(write.returncode)
                    else:
                        print("Deleted: {}".format(item))






if __name__ == '__main__':
    args = parse_args()
    main(args)