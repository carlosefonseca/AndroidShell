#!/usr/bin/env python3

import os
import json
#import argparse
#import subprocess
#import threading
#import glob
#import IPython
#import BewareAppManager
#import requests
import re

class GradleParser:
    path = None
    def __init__(self, path=None, folder=None):
        if path is None:
            if folder is not None:
                path = os.path.join(folder, "build.gradle")
            else:
                raise Exception("Path or folder required")
        self.path = path

    # def default(self):
        

    def flavors(self):
        txt = open(self.path).read()
        match = re.search("productFlavors\s*{\s+((?:(?:[^{}]*)+{(?:[^{}]+)})+)\s*(?://.*)?\s*}", txt)
        block = match.group(1)
        block = block.replace("applicationId", "package")

        fall = re.findall("\s*([^\s{]+)\s*{\s*([^}]+)}\s*", block)

        flavors = {}
        # for fl in fall:
        #     flavors[fl[0]] = {"pkg" : re.search("applicationId '([^']+)'", fl[1]).group(1)}
        #     appid = re.search("APPID[^\d]+(\d+)", fl[1])
        #     if appid is not None:
        #         flavors[fl[0]]["appId"] = appid.group(1)
        #     re.search("CustomerId[^\]+\\\"([^\]+)", fl[1])
        # return flavors

        for fl in fall:
            # print(fl[0])
            matches = re.findall(r"^\s*(?:(?:buildConfigField[^,]+,[^\w]+(\w+)[^\w]+([^\\\"]+))|(\w+)[^\w]+([^'\"]+))", fl[1], re.M)
            l = [f for m in matches for f in m if len(f) > 0]
            d = dict(zip(l[::2], l[1::2]))
            # print(d)
            flavors[fl[0]] = d
            # print(re.findall(r"^\s*(?:(?:buildConfigField[^,]+,[^\w]+(\w+)[^\w]+([^\\\"]+))|(\w+)[^\w]+([^'\"]+))", fl[1], re.M))
            # print("")
        return flavors

#                    _
#    _ __ ___   __ _(_)_ __
#   | '_ ` _ \ / _` | | '_ \
#   | | | | | | (_| | | | | |
#   |_| |_| |_|\__,_|_|_| |_|
#

if __name__ == "__main__":
    g = GradleParser(folder="/Users/carlos/Beware/WDAAProject/WDAA")
    print(g.flavors())
