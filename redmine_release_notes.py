#!/usr/bin/env python3

import requests
import os

def outputTicket(ticket, slack=False):
    if slack:
        return " <http://89.152.250.165:8281/redmine/issues/%d|#%d> - %s\n" % (ticket["id"], ticket["id"], ticket["subject"])
    else:            
        return " #%d - %s\n" % (ticket["id"], ticket["subject"])


def process(project, slack=False):
    try:
        a = open(os.path.join(os.path.expanduser("~"), ".redmine")).read().strip()
    except:
        print("Please place your Redmine API key from http://192.168.75.45:8281/redmine/my/account on ~/.redmine")
        return

    headers = {"Authorization":"Basic "+a}

    # assigned to: me
    # status: resolved
    # sort: tracker:desc (Feature, Bug), priority:desc (High, Low)
    try:
        j = requests.get('http://192.168.75.45:8281/redmine/projects/%s/issues.json?assigned_to_id=me&status_id=3&sort=tracker:desc,priority:desc' % project, headers=headers, timeout=5).json()
    except Exception as e:
        j = requests.get('http://89.152.250.165:8281/redmine/projects/%s/issues.json?assigned_to_id=me&status_id=3&sort=tracker:desc,priority:desc' % project, headers=headers).json()

    issues = j["issues"]

    feat = [x for x in issues if x["tracker"]["id"] == 2]
    bugs = [x for x in issues if x["tracker"]["id"] == 1]
    othr = [x for x in issues if x["tracker"]["id"] > 2]

    out = ""

    if len(feat) > 0:
        out+="Funcionalidades implementadas:\n"

        for i in feat:
            out += outputTicket(i, slack)

    if len(bugs) > 0:
        out+="Bugs corrigidos:\n"

        for i in bugs:
            out += outputTicket(i, slack)

    if len(othr) > 0:
        out+="Outros Tickets:\n"

        for i in othr:
            out += outputTicket(i, slack)

    return out.strip()

if __name__ == '__main__':

    import argparse

    argparser = argparse.ArgumentParser(description="Retrieves 'Resolved' tickets from a Redmine project and formats them for release notes.")
    argparser.add_argument('project_name', help='Redmine\'s project name')
    argparser.add_argument('--slack', action='store_true', help='Creates slack style URL\'s for tickets.')

    args = argparser.parse_args()
    print(process(args.project_name, slack=args.slack))