#!/usr/bin/env python3

from argparse import ArgumentParser
from contextlib import nullcontext
from getpass import getpass
from datetime import datetime
import subprocess
import os
import sys
import json

import requests
import tzlocal


_default_keys = ['~/.ssh/id_rsa']


def parse_args():
    for key in _default_keys:
        real_path = os.path.expanduser(key)
        if os.path.isfile(real_path):
            keydefault = { 'default': real_path }
            break
    else:
        keydefault = { 'required': True }

    parser = ArgumentParser(description='Approve or reject corpus download')
    parser.add_argument('-a', '--approve', dest='approve', action='store_const', const=True,
            help='(non-interactive mode) approve the listed requests')
    parser.add_argument('-r', '--reject', dest='approve', action='store_const', const=False,
            help='(non-interactive mode) reject the listed requests')
    parser.add_argument('-i', '--interactive', action='store_true',
            help='enable interactive mode')
    parser.add_argument('-k', '--key', action='store', **keydefault,
            help='the path to the private key')
    parser.add_argument('-p', '--passphrase', default='', action='store',
            help='the passphrase for the private key')
    parser.add_argument('-o', '--output', action='store',
            help='output file to write JSONL to')
    parser.add_argument('-O', '--append', action='store',
            help='output file to append JSONL to')
    parser.add_argument('files', nargs='+',
            help='encrypted files')

    args = parser.parse_args()

    if args.append:
        if args.output:
            print("Error: choose -o/--output or -O/--append", file=sys.stderr)
            sys.exit(1)
        args.output = args.append

    return args


def check_passphrase(args):
    while True:
        cmd = [
            "ssh-keygen", "-P", args.passphrase, "-yf", args.key
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 255:
            prompt = f"Enter pass phrase for {os.path.expanduser(args.key)}:"
            args.passphrase = getpass(prompt)
        else:
            return


tz = tzlocal.get_localzone()
def format_date(ts):
    local_time = datetime.fromtimestamp(unix_timestamp, tz)
    return local_time.strftime("%Y-%m-%d %H:%M:%S.%f%z (%Z)")


approve_strings = {
    False: 'rejected',
    True: 'approved',
    None: '',
}
def main(args):
    keyarg = ["-inkey", args.key] if args.key else []
    passarg = ["-passin", f"pass:{args.passphrase}"] if args.passphrase else []

    mode = 'at' if args.append else 'wt'
    output_context = open(args.output, mode, encoding='utf-8') if args.output else nullcontext(sys.stdout)
    with output_context as output:
        for file in args.files:
            if file.endswith('.jsonl.enc'):
                cmd = [
                    "openssl", "smime",
                    "-decrypt", "-binary", "-inform", "DER",
                    "-in", file,
                    *keyarg, *passarg,
                ]
                result = subprocess.run(cmd, stdin=subprocess.PIPE, capture_output=True)
                try:
                    result.check_returncode()
                    raw_data = result.stdout.decode('utf-8')
                except subprocess.CalledProcessError:
                    print(f'Error: {file}:', file=sys.stderr)
                    print(result.stderr.decode('utf-8'), file=sys.stderr)
                    continue
            else:
                try:
                    with open(file, 'rt', encoding='utf-8') as r:
                        raw_data = r.read()
                except FileNotFound:
                    print(f'Error: {file} not found', file=sys.stderr)

            for line in raw_data.splitlines():
                data = json.loads(line)

                send = False
                if args.approve is not None:
                    send = True
                    data["approved"] = args.approve

                if args.interactive:
                    print(f'Corpus:   {data["corpus"]}')
                    print(f'Name:     {data["name"]}')
                    print(f'Org:      {data["org"]}')
                    print(f'Email:    {data["email"]}')
                    if 'requested_at' in data:
                        print(f'Req:      {format_date(data["requested_at"])}')
                    if 'responded_at' in data:
                        print(f'Req:      {format_date(data["responded_at"])}')
                    if 'error' in data:
                        print(f'Error:    {data["error"]}')
                    approved = data.get('approved')
                    approve_str = approve_strings[approved]
                    if args.approve is None:
                        # interactive prompt
                        default = '' if approved is None else f'[{approve_str}]  '
                        approve_input = input(f'Approve?  {default}').strip().lower()
                        if approve_input:
                            send = True
                            approved = any(approve_input.startswith(s) for s in ['yes', 'approved'])
                    else:
                        # already got it from command line
                        print(f'Approved: {approve_str}')
                    print()

                else:
                    # not interactive - just JSON
                    if args.approve is not None:
                        send = True
                        approved = args.approve

                if send:
                    url = data['response_url']
                    new_data = {
                        **data,
                        'approved': approved,
                    }
                    if 'error' in new_data:
                        del new_data['error']

                    try:
                        response = requests.post(url, json=new_data)
                        if response.ok:
                            data = response.json()
                        else:
                            code = response.status_code
                            error = f'{code} {responses[code]}'
                            print(f'Error: {file}: {error}', file=sys.stderr)
                            data['error'] = error
                    except requests.exceptions.ConnectionError as x:
                        error = 'cannot connect'
                        print(f'Error: {file}: {error}', file=sys.stderr)
                        data['error'] = error

                if args.output or not args.interactive:
                    print(json.dumps(data), file=output)


if __name__ == '__main__':
    args = parse_args()
    if any(file.endswith('.jsonl.enc') for file in args.files):
        check_passphrase(args)
    main(args)
