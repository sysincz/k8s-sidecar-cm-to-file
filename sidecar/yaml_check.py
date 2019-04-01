#!/usr/bin/env python

import sys
import yaml
import argparse

parser=argparse.ArgumentParser()

parser.add_argument('--file', help='File path to yml', type= str,required=True)

args=parser.parse_args()


def main(str):

    with open(str) as stream:
        try:
            yaml.load(stream)
            return 0
        except yaml.YAMLError as exc:
            print(exc)
            return 1

if __name__ == "__main__":
    sys.exit(main(args.file))


