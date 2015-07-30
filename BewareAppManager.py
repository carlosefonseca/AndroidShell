#!/usr/bin/env python3
# coding=utf-8

# Should work with python 2.6+ and python 3+

import codecs
import json
import os
import re
import shutil
import subprocess
from zipfile import ZipFile
import requests
import argparse
from unidecode import unidecode

try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin

ANDROID_STUDIO_APP_SDK = "/Applications/Utilities/sdk"

BAM_FILE = ".bam"

user_data = None


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


########################################################################################################################
#       config file
########################################################################################################################
def save_data(params):
    if params.__class__ == App:
        params = params.__dict__
    json.dump(params, file(BAM_FILE, "w+"), indent=2)


def old_get_data():
    if os.path.exists(BAM_FILE):
        return App(json.load(open(BAM_FILE)))
    else:
        print("App not configured. Use 'create-config' first.")
        return None

def get_bam_file():
    return os.path.expanduser("~/" + BAM_FILE);

def create_user_data():
    u = UserBam()
    u.storage_folder = user_request("Path to the folder that will hold your apps: ")
    u.base_url = user_request("Public URL for the folder: ")
    email_name = user_request("Sender name for sending emails: ")
    email = user_request("Sender email: ")
    u.frm = "%s <%s>" % (email_name, email)
    if not u.base_url.endswith("/"):
        u.base_url += "/"
    u.slack_url = user_request("Slack incomming web hook url (https://my.slack.com/services): ")
    json.dump(u.__dict__, open(get_bam_file(), "w+"), sort_keys=True, indent=2)
    return u


def load_user_data():
    global user_data
    user_data = get_user_data()


def get_user_data():
    userbam = os.path.expanduser("~/" + BAM_FILE)
    if os.path.exists(userbam):
        try:
            return UserBam(dict=json.load(open(userbam)))
        except:
            return None
    else:
        return None


class UserBam:
    def __init__(self, dict=None):
        self.storage_folder = None
        self.base_url = None
        self.frm = None
        self.slack_url=None
        if dict:
            self.__dict__ = dict


########################################################################################################################
#       User Input
########################################################################################################################
def get_release_notes(name="release_notes", initial_text=None):
    if "EDITOR" in os.environ:
        fn = "/tmp/%s" % name
        if initial_text is not None:
            codecs.open(fn, "w+", "utf-8").write(initial_text)
        editor__split = os.environ["EDITOR"].split()
        editor__split.append(fn)
        subprocess.call(editor__split)
        return open(fn).read()
    else:
        raise Exception("No $EDITOR… what should I do?")


try:
    input = raw_input
except NameError:
    pass


def user_request(prompt, options=None, default=None):
    if not options:
        t = ""
        while len(t) == 0:
            t = input(prompt).strip()
    else:
        t = "qazwsx"
        opts = [x.strip().lower() for x in options]
        opts.append("")
        while t not in opts:
            t = input(prompt).strip().lower()
        if default is not None and len(t) == 0:
            t = default
    return t


########################################################################################################################
#       network
########################################################################################################################
base_url = 'http://bwappmanager.herokuapp.com/api/v1/'
# base_url = 'http://0.0.0.0:5000/api/v1/'


def request(endpoint, params=None, log=False, dry_run=False, log_errors=True, do_indent=False):
    # print("-> " + endpoint)
    if dry_run:
        print("%sWould request: %s" % ((indent("") if do_indent else ""), endpoint))
        if params:
            json_dumps = json.dumps(params, indent=2)
            print(indent(json_dumps) if do_indent else json_dumps)
        return 200, True

    if endpoint.startswith("http"):
        url = endpoint
    else:
        url = base_url + endpoint

    if log: print(indent(url) if do_indent else url)
    j = t = None
    if params:
        print("params")
        print(params)
        req = requests.post(url, params)
        t = req.text
        print("t")
        print(t)
    else:
        req = requests.get(url)
        try:
            j = req.json()
        except:
            t = req.text
    if j:
        if log or (log_errors and req.status_code >= 400):
            try:
                json_dumps = json.dumps(j, indent=2, ensure_ascii=False)
                print(indent(json_dumps) if do_indent else json_dumps)
            except Exception as e:
                raise e
        return req.status_code < 400, j
    elif t is not None:
        if log or (log_errors and req.status_code >= 400):
            try:
                print(indent(t) if do_indent else t)
            except Exception as e:
                raise e
        return req.status_code < 400, t


########################################################################################################################
#       VERSION
########################################################################################################################


def get_apk_build_info(build):
    if "ANDROID_HOME" in os.environ:
        home = os.environ["ANDROID_HOME"]
        aapt = subprocess.check_output(["find", home, "-name", "aapt"]).decode().split("\n")[0]
        if len(aapt) == 0: raise Exception("Could not find aapt inside $ANDROID_HOME.")
    elif os.path.exists(ANDROID_STUDIO_APP_SDK):
        aapt = subprocess.check_output(["find", ANDROID_STUDIO_APP_SDK, "-name", "aapt"]).decode().split("\n")[0]
        if len(aapt) == 0: raise Exception("Could not find aapt inside %s." % ANDROID_STUDIO_APP_SDK)
    else:
        raise Exception("Please set $ANDROID_HOME.")

    cmd = [aapt, "dump", "badging", build]
    #print(cmd)
    data = subprocess.check_output(cmd).decode()
    #print(data)
    splits = data.split()[1:4]
    #print(splits)
    #print(splits)
    #print(re.search("'(.+)'", splits[0]).group(1))
    #print(re.search("'(.+)'", splits[1]).group(1))
    #print(re.search("'(.+)'", splits[2]).group(1))
    infos = [re.search("'(.+)'", s).group(1) for s in splits]
    name = get_app_name(data)

    s = re.search("application-icon-480:'([^']*)'", data)
    iconName = None
    if s:
        iconName = s.group(1)

    return infos[0], infos[2], infos[1], name, iconName


def get_app_name(data):
    for y in [x for x in data.split("\n") if x.startswith("application")]:
        try:
            return re.search("label='([^']+)'", y).group(1)
        except:
            pass


def get_ipa_build_version(build):
    pl = None
    zipfile = ZipFile(build)
    for f in zipfile.namelist():
        if ".app/Info.plist" in f:
            pl = f
            break

    p = subprocess.Popen(["plutil", "-convert", "json", "-", "-o", "-"], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    j = json.loads(p.communicate(input=zipfile.read(pl))[0])
    return j["CFBundleShortVersionString"], j["CFBundleVersion"]


class App:
    def __init__(self, dict=None):
        self.name = self.identifier = self.client = self.platform = self.build = self.folder = self.url = None
        self.frm = self.to = None
        if dict:
            self.__dict__ = dict


########################################################################################################################
#       METHODS
########################################################################################################################
def request_app_data():
    d = App()
    d.name = user_request("App name:")
    d.identifier = user_request("App identifier:")
    d.client = user_request("Client:")
    d.platform = user_request("Platform [android]:", ["android", "ios"], "android")
    d.build = user_request("Path to file to deploy:")
    d.folder = user_request("Path to online folder:")
    d.url = user_request("Public URL for the folder:")
    if not d.url.endswith("/"):
        d.url += "/"

    return d


def create(dry_run=False):
    data = get_data()
    if data:
        c = user_request("Use existing config file to create Application on the site? [Y/n] ", options=["y", "n"],
                         default="y")
        if c == "y":
            params = data
        else:
            params = create_config()
    else:
        params = create_config()

    return request(endpoint=params.identifier + "/",
                   params={k: getattr(params, k) for k in ["name", "client", "platform"]},
                   log=True,
                   dry_run=dry_run)[0]


def create_config(params=None):
    if not params:
        params = request_app_data()
    save_data(params)
    return params


def indent(txt, arrow=False):
    if arrow:
        space = "--> "
        txt = Color.BOLD + txt + Color.END
    else:
        space = "    "
    return space + re.sub("\n", "\n" + space, txt)

def describe_file(build_file, bam_name=None):
    file = build_file
    platf = None
    if file[-3:] == "apk":
        platf = "android"
        v_package, v_name, v_code, b_name, iconName = get_apk_build_info(file)
    elif file[-3:] == "ipa":
        platf = "ios"
        v_package, v_name, v_code = get_ipa_build_version(file)
    else:
        raise Exception("Unknown file type")
    version = "%s (%s)" % (v_name, v_code)
    machine_name = shorten_bam_name(v_package) if not bam_name else bam_name
    return machine_name, b_name, platf, version

def is_version_of_build_allowed(channel="dev", build_file=None, bam_name=None, verbose=False):
    machine_name, b_name, platf, version = describe_file(build_file, bam_name)
    return is_version_allowed(channel, machine_name, version, verbose)

def is_version_allowed(channel="dev", machine_name=None, version=None, verbose=False):
    success, app = request(endpoint=machine_name, log_errors=False, do_indent=True, log=False)
    if success:
        if verbose: print("App version: "+version)
        online_version = app["latest_releases"][channel]["version"]
        if verbose: print("BAM version: "+online_version)
        return version != online_version
    else:
        print("App doesn't exist")
        return True

def get_version(channel="dev", machine_name=None):
    success, app = request(endpoint=machine_name, log_errors=True, do_indent=True, log=False)
    if success:
        return app["latest_releases"][channel]["version"]
    else:
        return None


def deploy(channel="dev", build_file=None, dry_run=False, release_notes=None, send_mail=None, post_slack=None, post_slack_release_notes=False, bam_name=None, auto_create=False):
    if not user_data:
        load_user_data()
    drytxt = "[dry-run]" if dry_run else ""
    # if dry_run: print(indent("<deploy dry-run>"))
    # data = get_data()
    # if data:
    # file = data.build if build_file is None else build_file
    
    machine_name, b_name, platf, version = describe_file(build_file, bam_name)

    print(indent("Deploying %s %s %s %s" % (b_name, version, channel, drytxt), True))

    # print("BAM NAME:"+str(bam_name))
    machine_name = shorten_bam_name(v_package) if not bam_name else bam_name

    success, app = request(endpoint=machine_name, log_errors=False, do_indent=True)
    if not success:
        print("")
        if auto_create or user_request(indent("App %s/%s doesn't exist. Create? [y/n] " % (b_name, machine_name)), "yn", "y") == "y":
            # name = user_request("Name? [%s] " % v_name, default=v_name)
            print(indent("Creating '%s'" % b_name))
            success, r = request(endpoint=machine_name + "/",
                                 params={"name": unidecode(b_name), "client": "", "platform": platf},
                                 log=True,
                                 dry_run=dry_run, do_indent=True)
            print(indent(json.dumps(r, indent=2, ensure_ascii=False)))
            if not success:
                print("error")
                return False
        else:
            return False

    # App exists on server
    if not release_notes:
        release_notes = get_release_notes(machine_name)
    # print(indent(release_notes))

    # Destination for the build file
    build_file_name = "%s-%s%s" % (machine_name, v_code, os.path.splitext(file)[1])
    dst = os.path.join(user_data.storage_folder, build_file_name)
    # dstIcon = os.path.join(user_data.storage_folder, machine_name+os.path.splitext(os.path.basename(iconName))[1])

    # Create a release on the server
    url = machine_name + "/" + channel
    data = {"version": version, "build": int(v_code), "url": urljoin(user_data.base_url, build_file_name),
            "release_notes": release_notes}

    print("")
    drytxt = "[dry-run]" if dry_run else ""
    print(indent("Creating release on server… " + drytxt, True))
    success = request(url, data, True, dry_run=dry_run, do_indent=True)[0]
    print(indent("Success" if success else "Failure!"))
    if success:
        # Copy the built file
        print("")
        print(indent("Copying %s -> %s %s" % (file, dst, drytxt), True))
        if not dry_run:
            shutil.copy(file, dst)
            extractIcon2(file, machine_name, iconName)
            # extractFromZip(file, iconName, dstIcon)

        if send_mail:
            print("")
            mail(frm=user_data.frm, to=send_mail, app=machine_name, channel=channel, dry_run=dry_run, do_indent=True)
        if post_slack:
            print("")
            slackbot(app=machine_name, channel=channel, slack=post_slack, release_notes=post_slack_release_notes, dry_run=dry_run, do_indent=True)
    else:
        print("URL: "+url)
        print("Data: "+str(data))
    return success, machine_name

def extractIconCMD(args):
    extractIcon(args.file, args.bamName)

def extractIcon(file, bamName=None):
    if not user_data:
        load_user_data()
    machine_name = None
    if file[-3:] == "apk":
        platf = "android"
        v_package, v_name, v_code, b_name, iconName = get_apk_build_info(file)
        machine_name = shorten_bam_name(v_package) if not bamName else bamName
    # elif file[-3:] == "ipa":
    #     platf = "ios"
    #     v_package, v_name, v_code = get_ipa_build_version(file)
    else:
        raise Exception("Unknown file type")

    extractIcon2(file, machine_name, iconName)
    # dstIcon = os.path.join(user_data.storage_folder, machine_name+os.path.splitext(os.path.basename(iconName))[1])
    # extractFromZip(file, iconName, dstIcon)

def extractIcon2(file, machine_name, iconName):
    if not user_data:
        load_user_data()

    dstIcon = os.path.join(user_data.storage_folder, machine_name+os.path.splitext(os.path.basename(iconName))[1])
    extractFromZip(file, iconName, dstIcon)
    return dstIcon


def shorten_bam_name(name):
    name = name.replace("pt.beware.", "")
    name = name.replace("com.xtourmaker", "xtourmaker")
    return name

def extractFromZip(zipFile, path, dest):
    fileData = ZipFile(zipFile).read(path)
    with open(dest, 'wb') as f:
        f.write(fileData)


def move(from_channel, to_channel, version=None, identifier=None, dry_run=False):
    # if not identifier:
    # data = get_data()
    # if data:
    # identifier = data.identifier

    if not identifier:
        raise Exception("No identifier!")

    rr = request("%s/releases/%s" % (identifier, from_channel), log=True)
    r = rr[1]
    #print next([x for x in r[from_channel] if x["version"] == version])
    #print r[from_channel]
    if not version:
        release = r[from_channel][0]
    else:
        release = [x for x in r[from_channel] if x["version"] == version][0]
    print("Version: " + release["version"])
    print("URL: " + release["url"])
    print("Release Notes: " + release["release_notes"])

    print()

    change = user_request("Do you want to change the release notes? [Y/n] ", ["y", "yes", "n", "no"], "y")[0]
    if change == "y":
        release["release_notes"] = get_release_notes(identifier, release["release_notes"])

    return request(identifier + "/" + to_channel, release, True, dry_run=dry_run)[0]


def mail(frm=None, to=None, app=None, channel="dev", dry_run=False, do_indent=False):
    if dry_run:
        print(indent("Sending Email [dry-run]", True))
    else:
        print(indent("Sending Email", True))

    if not user_data:
        load_user_data()

    if frm is None:
        frm = user_data.frm

    if (frm is None or to is None or app is None) and data is None:
        return "Data missing"

    p = {
        "from": frm or data.frm,
        "to": to or data.to
    }

    return request("mail/%s/%s/" % (app, channel), params=p, log=True, dry_run=dry_run, do_indent=do_indent)[0]


def mail_multiple(frm=None, to=None, apps=None, channel="dev", dry_run=False):
    if dry_run:
        print(Color.BOLD + "Sending Email [dry-run]" + Color.END)
    else:
        print(Color.BOLD + "Sending Email" + Color.END)

    if not user_data:
        load_user_data()

    if frm is None:
        frm = user_data.frm

    if (frm is None or to is None or apps is None) and data is None:
        return "Data missing"

    if type(apps) == str:
        app_names = apps
    elif type(apps) == list:
        app_names = " ".join(apps)

    p = {
        "from": frm or data.frm,
        "to": to or data.to,
        "apps" : app_names,
        "channel" : channel
    }

    return request("mailmultiple", params=p, log=True, dry_run=dry_run)[0]


def slackbot(app=None, channel="dev", slack=None, release_notes=False, dry_run=False, do_indent=False):
    if dry_run:
        print(indent("Posting Slackbot message [dry-run]", True))
    else:
        print(indent("Posting Slackbot message", True))

    if (slack is None or app is None) and data is None:
        return "Data missing"

    return \
        request("slackbot/%s/%s/%s%s" % (app, channel, slack, "?releasenotes" if release_notes else ""), params=None, log=True, dry_run=dry_run,
                do_indent=do_indent)[0]


def postslack(channel, text, dry_run=False):
    if dry_run:
        print("Would post to slackbot.")
    else:
        requests.post(
            "https://beware.slack.com/services/hooks/slackbot?token=ReAe4bznlc2GPREyVtHFZUK0&channel=%23" + channel,
            text.encode('utf-8'))


#     ____   __  __   ____      _       ___   _   _   _____
#    / ___| |  \/  | |  _ \    | |     |_ _| | \ | | | ____|
#   | |     | |\/| | | | | |   | |      | |  |  \| | |  _|
#   | |___  | |  | | | |_| |   | |___   | |  | |\  | | |___
#    \____| |_|  |_| |____/    |_____| |___| |_| \_| |_____|
#


def create_run(args):
    create(args.dry_run)


def create_config_run(args):
    create_config()


def move_run(args):
    move(args.from_channel, args.to_channel, args.version, args.identifier, dry_run=args.dry_run)


def deploy_run(args):
    deploy(args.channel, build_file=args.file, dry_run=args.dry_run, send_mail=args.mail, post_slack=args.slack)


def version_release_notes(j):
    return j["version"] + "\n" + j["release_notes"] + "\n"


def releases_run(args):
    j = request(args.app + "/releases/" + (args.channel or ""))[1]

    if "release_notes" in j:
        print(version_release_notes(j))
    else:
        for i in list(j.items()):
            print("==============================")
            print(i[0])
            print("==============================")
            if type(i[1]) == list:
                for j in i[1]:
                    print(version_release_notes(j))
            elif type(i[1]) == dict:
                print(version_release_notes(i[1]))


def mail_run(args):
    mail(args.frm, args.to, args.app, args.channel, dry_run=args.dry_run)


def mail_multiple_run(args):
    mail_multiple(args.frm, args.to, args.apps, args.channel, dry_run=args.dry_run)


def slack_run(args):
    slackbot(app=args.app, channel=args.channel, slack=args.slack_channel, release_notes=args.release_notes, dry_run=args.dry_run)


def interpret(args):
    import IPython

    IPython.embed()


#                    _
#    _ __ ___   __ _(_)_ __
#   | '_ ` _ \ / _` | | '_ \
#   | | | | | | (_| | | | | |
#   |_| |_| |_|\__,_|_|_| |_|
#

if __name__ == "__main__":
    # check for user settings
    user_data = get_user_data()
    if not user_data:
        # create user settings
        u = user_request("Create user data now? [Y/n]", "yn", "y")
        if u == "y":
            user_data = create_user_data()
    else:





        # create app
        # create config file
        # create new version <channel>
        # copy version to channel

        #parser = argparse.ArgumentParser(description='…')
        #parser.add_argument("command", choices=["create", "create-config", "deploy", "move"])
        #
        #args = parser.parse_args()



        # create the top-level parser
        parser = argparse.ArgumentParser(description="Beware App Manager command line interface.")
        parser.add_argument('--dry-run', action='store_true', help='Don\'t make changes.')
        subparsers = parser.add_subparsers(help='sub-command help')

        # create the parser for the "create" command
        parser_create = subparsers.add_parser('create',
                                              help='Create a new app on the server and a config file on this folder.')
        parser_create.set_defaults(func=create_run)

        # create the parser for the "config" command
        parser_config = subparsers.add_parser('config', help='Create a config file on this folder.')
        parser_config.set_defaults(func=create_config_run)

        # create the parser for the "move" command
        parser_move = subparsers.add_parser("move", help="Move a version from one channel to another.")
        parser_move.add_argument("from_channel")
        parser_move.add_argument("to_channel")
        parser_move.add_argument("version", nargs="?", default=None)
        parser_move.add_argument("-identifier", nargs="?", default=None)
        parser_move.set_defaults(func=move_run)

        # create the parser for the "deploy" command
        parser_deploy = subparsers.add_parser("deploy", help="Deploy a new app version.")
        parser_deploy.add_argument("channel")
        parser_deploy.add_argument('file', help='The file to upload.')
        parser_deploy.add_argument('--mail', help='Send the release to the configured emails.')
        parser_deploy.add_argument('--slack', help='Post a message to a Slack channel.')
        parser_deploy.set_defaults(func=deploy_run)

        # create the parser for the "releases" command
        parser_releases = subparsers.add_parser("releases", help="Display release notes for release.")
        parser_releases.add_argument("app")
        parser_releases.add_argument("channel", nargs="?")
        parser_releases.set_defaults(func=releases_run)

        # create the parser for the "mail" command
        parser_mail = subparsers.add_parser("mail", help="Send an email with the details of a release.")
        parser_mail.add_argument("frm", nargs="?")
        parser_mail.add_argument("to", nargs="?")
        parser_mail.add_argument("apps", nargs="?")
        parser_mail.add_argument("channel")
        parser_mail.set_defaults(func=mail_multiple_run)

        # create the parser for the "slack" command
        parser_slack = subparsers.add_parser("slack", help="Send a message to Slack with a release.")
        parser_slack.add_argument("app", nargs="?")
        parser_slack.add_argument("channel")
        parser_slack.add_argument("--slack_channel", "-s", nargs="?")
        parser_slack.add_argument('--release_notes', action='store_true', help='Also post the release notes.')
        parser_slack.set_defaults(func=slack_run)

        parser_repl = subparsers.add_parser("repl", help="Starts a shell.")
        parser_repl.set_defaults(func=interpret)

        parser_icon = subparsers.add_parser("icon", help="Extracts the icon from an app package into the deploy folder.")
        parser_icon.add_argument("file", help="apk file to extract from")
        parser_icon.add_argument("bamName", nargs="?")
        parser_icon.set_defaults(func=extractIconCMD)

        args = parser.parse_args()
        print(args)
        args.func(args)

        # parse some argument lists
        #Namespace(bar=12, foo=False)
        #parser.parse_args(['--foo', 'b', '--baz', 'Z'])
        #Namespace(baz='Z', foo=True)


        #if ()


