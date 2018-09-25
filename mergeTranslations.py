#!/usr/bin/env python

import sys
import json


def merge(a, b, path=None, replace=True):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            elif replace:
                a[key] = b[key] 
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

def test():
    # works
    print(merge({1:{"a":"A"},2:{"b":"B"}}, {2:{"c":"C"},3:{"d":"D"}}))
    # has conflict
    print(merge({1:{"a":"A"},2:{"b":"B"}}, {1:{"a":"A"},2:{"b":"C"}}))

#reduce(merge, [dict1, dict2, dict3...])


#for f in sys.argv[1:]:
#   print(f)

dicts = [json.load(open(f)) for f in sys.argv[1:]]

#print(dicts)

if (len(dicts) == 1):
    print(json.dumps(dicts[0], indent=2, sort_keys=True))
else:
    x = reduce(merge, dicts)
    print(json.dumps(x, indent=2, sort_keys=True))
