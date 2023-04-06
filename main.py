#!/usr/bin/env python3
import argparse

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
    
    day = datetime.now()

    pdfs = {}
    for name in args.sources:
        src = sources[name](day, args.only_front)
        pdfs[src.name()] = src.get_pdf()
    
    print("Would add:", pdfs)
        
        

if __name__ == '__main__':
    args = parse_args()
    main(args)