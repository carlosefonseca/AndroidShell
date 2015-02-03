#!/usr/bin/env python3

# coding: utf-8

from sys import exit
import os
import json
import argparse
import subprocess
import threading
import glob
import IPython
import BewareAppManager
import requests
from GradleParser import GradleParser
from copy import deepcopy
import time

filename = ".adb"
full_config = None
config = None
flavor = None
flavorname = None
path = None  # path for config file
dirname = None  # "dirname" for config file
pkg = None
args = None
release_notes_file = ".releasenotes"


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


def find_dot_adb(curr=os.getcwd()):
    path_join = os.path.join(curr, filename)
    f = None
    if os.path.exists(path_join):
        try:
            f = open(path_join)
        except:
            pass

    if not f:
        if curr != "/":
            return find_dot_adb(os.path.dirname(curr))
        else:
            return None
    else:
        return f


def read_dot_adb(f):
    global full_config
    global flavor
    global flavorname
    j = json.load(f)
    full_config = j
    if ("_f" in j):
        try:
            flavorname = j["_f"]
            flavor = get_flavor(j, flavorname)
            return flavor
        except:
            print("Flavor '%s' doesn't exist!" % flavorname)
    else:
        if (len(j) > 1):
            print("Select a flavor")
        elif (len(j) == 1):
            return j.values()[0]
        elif "package" in j:
            return j
        else:
            print("No flavors!")


def load_config(args=None):
    global config
    global pkg
    global path
    global dirname
    f = find_dot_adb()
    if not f:
        print(".adb not found.")
        exit(1)
    config = read_dot_adb(f)
    pkg = config["package"]
    if not pkg: pkg = config["package"]
    path = f.name
    dirname = os.path.dirname(path)


def load_all_config():
    global config
    global pkg
    global path
    f = find_dot_adb()
    if not f:
        print(".adb not found.")
        exit(1)
    j = json.load(f)
    dirname = os.path.dirname(f.name)
    return f, j


def set_flavor(f, flavor, j):
    j["_f"] = flavor
    json.dump(j, open(f.name, "w+"), indent=2, sort_keys=True)


"""
Run the following on bash:  $(<this-script> f --env)
and it will export the env vars for the current flavor
"""


def get_flavor_env(args):
    load_config(args)
    # print(" && ".join(["export %s=\"%s\""%(k,v) for k,v in config["env"].items()]))
    # if "env" in config:
    #     [
    #         print("export %s=%s" % (k, v))
    #         for k, v in config["env"].items()]


def choose_gradle_flavor(flavors):
    keys = list(flavors.keys())
    keys.sort()
    for i,v in enumerate(keys):
        print(str(i).rjust(3)+" "+v)
    r = request_user("Flavor: ")
    new_flavor_name = None
    if r.isnumeric() and int(r) < len(keys) and int(r) >= 0:
        new_flavor_name = keys[int(r)]
    else:
        for k in keys:
            if k.startswith(r):
                new_flavor_name = k
                break
    if new_flavor_name is not None:
        print()
        print(new_flavor_name +"   >   "+ (",    ".join([k+": "+v for k,v in flavors[new_flavor_name].items()])))
        return new_flavor_name, flavors[new_flavor_name]
    else:
        print("WRONG!")
        return None

def flavor(args):
    if args.add:
        return add_flavor(args)
    if args.env:
        return get_flavor_env(args)

    f, j = load_all_config()

    if "_gradle" in j:
        flavors = GradleParser(folder=os.path.join(os.path.dirname(f.name), j["_gradle"])).flavors()
        #print(flavors)
        # for ff in flavors:
            # print(j["_f"] +"   >   "+ (",    ".join([k+": "+v for k,v in ff.items()])))

        if args.dump:
            print(json.dumps(flavors, indent=2))
            return

        flavor = args.name
        if not flavor:
            if args.x:
                name, _ = choose_gradle_flavor(flavors)
                set_flavor(f, name, j)
                return

            if "_f" not in j:
                if len(flavors) == 1:
                    set_flavor(f, flavors.keys()[0], j)
                else:
                    print("No flavor set. Choose from these:")
                    name, _ = choose_gradle_flavor(flavors)
                    set_flavor(f, name, j)
                    return

            flavor = flavors[j["_f"]]
            print(j["_f"] +"   >   "+ (",    ".join([k+": "+v for k,v in flavor.items()])))

        elif flavor in j:
            set_flavor(f, flavor, j)
            print("Selected flavor: " + flavor)
        else:
            keys = list(flavors.keys())
            for k in keys:
                if k.startswith(flavor):
                    set_flavor(f, k, j)
                    print("Selected flavor: " + k)
                    return

            print("Flavor '%s' doesn't exist!" % flavor)


    else:

        flavor = args.name
        if not flavor:
            if "_f" not in j:
                if len(j.keys()) == 1:
                    set_flavor(f, list(j.keys())[0], j)
                else:
                    print("No flavor set. Choose from these: %s" % ", ".join(j.keys()))
                    return
            # print("Current flavor: %s  on file: %s" % (j["_f"], f.name))
            print("Current flavor: %s   [ %s ]" % (j["_f"], ", ".join([k for k in j.keys() if not k.startswith("_") and k != j["_f"]])))
            return

        if flavor in j:
            set_flavor(f, flavor, j)
            print("Selected flavor: " + flavor)
        else:
            print("Flavor '%s' doesn't exist!" % flavor)


def call(args, split=True):
    if split:
        if type(args) == str:
            args = args.split(" ")
        else:
            args = [item.split(" ") for item in args]
            args = [item for sublist in args for item in sublist]
    #print(args)
    print(" $ " + " ".join(args))
    return subprocess.call(args)


def edit(file, sublime=False):
    if sublime:
        call("subl -W "+file)
    else:
        call("open -e -n -W "+file)


def create_config(args):
    config = dict()
    config["package"] = request_user("Package name:")
    config["activity"] = request_user("First activity package.name:")
    config["dbname"] = request_user("Database file name:")
    json.dump(config, open(filename, "w+"), indent=2)
    print("Saved on " + os.path.abspath(filename))


def add_flavor(args):
    f, j = load_all_config()
    n = request_user("Flavor name: ")
    c = dict()
    c["package"] = request_user("Package name:")
    c["activity"] = request_user("First activity package.name:")
    c["dbname"] = request_user("Database file name:")
    j[n] = c
    json.dump(j, open(f.name, "w+"), indent=2)
    print("Saved on " + f.name)


def start(args):
    load_config(args)
    adb_start(pkg, config["activity"])

def debug(args):
    load_config(args)
    adb_start(pkg, config["activity"], debug=True)

def close(args):
    load_config(args)
    adb_force_stop(pkg)

def clear(args):
    load_config(args)
    adb_clear(pkg)

def clear_start(args):
    load_config(args)
    adb_clear(pkg)
    adb_start(pkg, config["activity"])

def restart(args):
    load_config(args)
    adb_force_stop(pkg)
    adb_start(pkg, config["activity"])

def install_start(args):
    load_config(args)
    install(args)
    adb_start(pkg, config["activity"])

def uninstall(args):
    load_config(args)
    adb_uninstall(pkg)

# ADB WRAPPER

def adb_uninstall(pkg):
    adb("uninstall %s" % pkg, all=args.all)

def adb_clear(pkg):
    adb("shell pm clear " + pkg)

def adb_start(pkg, activity, debug=False):
    adb("shell am start%s -n %s/%s -a android.intent.action.MAIN -c android.intent.category.LAUNCHER" % (" -D" if debug else "", pkg, activity))    

def adb_force_stop(pkg):
    adb("shell am force-stop %s" % pkg)

def adb_install(apk_file):
    adb("install -r "+apk_file)

def adb_pull(path):
    adb('pull %s' % path)

def adb_ls(path):
    return [x.decode() for x in subprocess.check_output(["adb", "shell", "ls", path]).split()]

devices = None

def adb(cmd, all=None):
    global devices
    if not all: all = args.all
    if type(cmd) == str:
        cmd = cmd.split(" ")
    else:
        cmd = [item.split(" ") for item in cmd]
        cmd = [item for sublist in cmd for item in sublist]

    if all:
        if not devices: devices = adb_device_list()
        [call(["adb", "-s", d] + cmd) for d in devices]

    else:
        call(["adb"] + cmd)

def adb_device_list():
    return [d.split("\t")[0] for d in subprocess.check_output(["adb", "devices"]).decode("ascii").split("\n")[1:-2]]


def install(args):
    load_config(args)
    if 'ANDROID_SERIAL' in os.environ:
        print("ANDROID_SERIAL: "+os.environ['ANDROID_SERIAL'])

    flavors = args.flavors if len(args.flavors) != 0 else [flavorname]

    if (args.deployed):
        uploads = {}
        folder = BewareAppManager.get_user_data().storage_folder
        for flavor in flavors:
            fconfig = full_config[flavor]
            pck = fconfig["package"]
            spck=shorten_bam_name(pck)
            apks = glob.glob(os.path.join(folder,"%s*apk" % spck))
            apks.sort()
            f = apks[-1]
            uploads[pck] = f

        for k,v in uploads.items():
            print("%s - %s" % (k.rjust(30),v)) 

        for k,v in uploads.items():
            adb_install(v)
        return

    gradle_install(flavors)
    
def gradle_install(flavors):
    gradle_cmd = "./gradlew --daemon instal%sDebug" % ("Debug assemble".join([f.title() for f in flavors]))
    call(gradle_cmd)    


def opendb(args):
    pulldb(args, open=True)

def pulldb(args, open=False):
    load_config(args)

    dbn = args.name if args.name else config["dbname"]
    dbnf = dbn if dbn.endswith(".db") else dbn+".db"

    if open: call("pkill Base")
    call("rm " + dbn)

    # trying direct pull
    success = call("adb pull /data/user/0/%s/databases/%s %s" % (pkg, dbn, dbnf)) == 0 and os.path.exists(dbnf)
    if success:
        call("adb pull /data/user/0/%s/databases/%s-journal %s-journal" % (pkg, dbn, dbnf)) == 0 and os.path.exists(dbnf)

    else:
        # trying copy as root
        call("adb shell rm /sdcard/%s" % dbn)
        call("adb shell rm /sdcard/%s-journal" % dbn)
        call("adb shell su -c cp /data/user/0/%s/databases/%s /sdcard/" % (pkg, dbn))
        call("adb shell su -c cp /data/user/0/%s/databases/%s-journal /sdcard/" % (pkg, dbn))
        success = call("adb pull /sdcard/%s %s" % (dbn, dbnf)) == 0
        if success:
            call("adb pull /sdcard/%s-journal %s-journal" % (dbn, dbnf))

        else:
            # trying alternative root
            call("adb shell rm /sdcard/%s" % dbn)
            call("adb shell rm /sdcard/%s-journal" % dbn)
            call(["adb", "shell", "su -c 'cp /data/user/0/%s/databases/%s /sdcard/'" % (pkg, dbn)], split=False)
            call(["adb", "shell", "su -c 'cp /data/user/0/%s/databases/%s-journal /sdcard/'" % (pkg, dbn)], split=False)
            success = call("adb pull /sdcard/%s %s" % (dbn, dbnf)) == 0
            if success:
                call("adb pull /sdcard/%s-journal %s-journal" % (dbn, dbnf))

            else:
                # trying run-as
                call("adb shell rm /sdcard/" + dbn)
                call("adb shell run-as \"%s\" cp databases/%s /sdcard/" % (pkg, dbn))
                call("adb shell run-as \"%s\" cp databases/%s-journal /sdcard/" % (pkg, dbn))
                success = call("adb pull /sdcard/%s %s" % (dbn, dbnf)) == 0
                if success:
                    call("adb pull /sdcard/%s-journal %s-journal" % (dbn, dbnf))

    if success:
        call("sqlite3 %s vacuum" % dbnf)
        if open: call(["open", dbnf])
    else:
        print("Failed to pull file :(")
        exit(1)


def request_user(prompt, options=None, default=None):
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

def get_flavor(json, name):
    if "_default" in json:
        f = deepcopy(json["_default"])
        f.update(json[name])
        return f
    else:
        return json[name]

def publish(args):
    load_config(args)
    uploads = {}
    for flavor in args.flavors:
        fconfig = full_config[flavor]
        pck = fconfig["package"]
        #print(pck)
        spck=shorten_bam_name(pck)
        # print(spck)
        apks = glob.glob("/Users/carlos/MEOCloud/APKs/*%s*apk" % spck)
        apks.sort()
        f = apks[-1]
        #print(f)
        uploads[pck] = f

    for k,v in uploads.items():
        print("%s - %s" % (k.rjust(30),v)) 
    r = BewareAppManager.user_request("Correct? yN ", "yn", "n")

    if r == "y":
        successes = {}
        errors = {}
        for k,v in uploads.items():
            if args.skip_upload or call(["/Users/carlos/Beware/AndroidShell/publish/publish_apk.py", k, v, "production"]) == 0:
                successes[k]=v
            else:
                errors[k] = v

        if not args.skip_slack:
            for k,v in successes.items():
                (p,vn,vc,n,i) = BewareAppManager.get_apk_build_info(v)
                slack("<https://play.google.com/store/apps/details?id=%s|%s> %s (%s) Publicada!" % (k,n,vn,vc), "#"+config["slack"], username="Google Play", icon_emoji=":google_play:")
            
        for k,v in errors.items():
            print("ERROR UPLOADING: "+v)


def slack(text, channel, username=None, icon_emoji=None):
    try:
        data = {"text":text,"channel":channel}
        if username:
            data["username"]=username
        if icon_emoji:
            data["icon_emoji"]=icon_emoji

        try:
            slack_url = BewareAppManager.get_user_data().slack_url
        except:
            slack_url = None

        if not slack_url:
            print("slack_url is not configured on %s."%BewareAppManager.get_bam_file())
            return False

        r = requests.post(
            url=slack_url,
            data = json.dumps(data)
        )
        print('Response HTTP Status Code : {status_code}'.format(status_code=r.status_code))
        print('Response HTTP Response Body : {content}'.format(content=r.content))
        return True
    except requests.exceptions.RequestException as e:
        print('HTTP Request failed')
        return False



def deploy(args):
    load_config(args)

    gitout = gitstatus()
    if len(gitout):
        print("⚠️  Git: " + gitout.strip())
        r = BewareAppManager.user_request("Continue? [Yes]/No/Tower/Sourcetree ", "ynts", "y")
        if r == "n":
            return
        elif r == "t":
            call(["gittower", "."])
            BewareAppManager.user_request("Continue? ")
        elif r == "s":
            call(["stree"])
            BewareAppManager.user_request("Continue? ")
    
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(processes=1)

    if not args.no_compile:
        if len(args.flavors) == 0: print("Building ALL flavors.")

        if ("debug_only" in config and config["debug_only"]):
            gradle_cmd = "%s/gradlew --daemon assemble%sDebug" % (
                dirname, "Debug assemble".join([x.title() for x in args.flavors]))
        else:
            gradle_cmd = "%s/gradlew --daemon assemble%sRelease" % (
                dirname, "Release assemble".join([x.title() for x in args.flavors]))

        async_result = pool.apply_async(call, (gradle_cmd,))

    redmine_project = config["redmine"] if "redmine" in config else None

    if redmine_project is not None:
        r = BewareAppManager.user_request("Fetch Release Notes from Redmine? Y/[N] ", "yn", "n")
        if r == "y":

            import redmine_release_notes

            with open(release_notes_file, "w+") as f:
                f.write(redmine_release_notes.process(redmine_project, slack=True))

    edit(release_notes_file)

    if not args.no_compile:
        if async_result.get() != 0:
            print("Build failed.")
            return 1

    flavored_files = {}
    if "singleflavor" in full_config:
        flavor = full_config["singleflavor"]
        fconfig = full_config[flavor]

        if ("debug_only" in fconfig and fconfig["debug_only"]):
            flavored_files[flavor] = glob.glob("*/build/outputs/apk/%s-debug.apk" % flavor)
        else:

            if len(glob.glob("*/build/outputs/apk")) > 0:
                flavored_files[flavor] = glob.glob("*/build/outputs/apk/%s-release.apk" % flavor)
                if len(flavored_files[flavor]) == 0:
                    flavored_files[flavor] = glob.glob("*/build/outputs/apk/%s-release-unsigned.apk" % flavor)
            elif len(glob.glob("build/outputs/apk")) > 0:
                flavored_files[flavor] = glob.glob("build/outputs/apk/%s-release.apk" % flavor)
                if len(flavored_files[flavor]) == 0:
                    flavored_files[flavor] = glob.glob("build/outputs/apk/%s-release-unsigned.apk" % flavor)
    else:

        if len(args.flavors) == 0: args.flavors = "*"

        for flavor in args.flavors:
            fconfig = full_config[flavor]

            if ("debug_only" in fconfig and fconfig["debug_only"]):
                flavored_files[flavor] = glob.glob("*/build/outputs/apk/*-%s-debug.apk" % flavor)
            else:

                if len(glob.glob("*/build/outputs/apk")) > 0:
                    flavored_files[flavor] = glob.glob("*/build/outputs/apk/*-%s-release.apk" % flavor)
                    if len(flavored_files[flavor]) == 0:
                        flavored_files[flavor] = glob.glob("*/build/outputs/apk/*-%s-release-unsigned.apk" % flavor)
                elif len(glob.glob("build/outputs/apk")) > 0:
                    flavored_files[flavor] = glob.glob("build/outputs/apk/*-%s-release.apk" % flavor)
                    if len(flavored_files[flavor]) == 0:
                        flavored_files[flavor] = glob.glob("build/outputs/apk/*-%s-release-unsigned.apk" % flavor)

    release_notes = open(os.path.join(dirname, release_notes_file)).read()
    something_was_uploaded = False
    uploaded=[]
    mails=None
    i = len(flavored_files)
    for fn, ff in flavored_files.items():
        if len(ff) > 1:
            print("??? " + fn + " " + str(ff))
            return
        elif len(ff) == 1:
            i-=1
            print()
            success, bam_name = uploadBAM3(ff[0], fn, release_notes, i == 0, args.dry_run)
            if not success:
                print(Color.RED + "ERROR" + Color.END)
                return
            else:
                flavr = get_flavor(full_config, fn)
                if "mailto" in flavr:
                    mails=flavr["mailto"]
                uploaded.append(bam_name)
                something_was_uploaded = True

    if not something_was_uploaded:
        print(Color.RED + "Nothing was uploaded!"+Color.END)


    print()
    if args.no_mail or not mails:
        print(Color.BOLD + "Skipping emails" + Color.END)
    else:
        BewareAppManager.mail_multiple(to=mails, apps=uploaded, dry_run=args.dry_run)

    print(Color.BOLD +"\nRemember to let it upload…"+ Color.END)

    # if "slack" in config and config["slack"]:
    #     print()
    #     drytxt = ("[dry-run]" if args.dry_run else "")
    #     print(Color.BOLD + "Posting release notes to Slack " + drytxt + Color.END)
    #     release_notes = "\n".join(">" + l for l in release_notes.splitlines())
    #     BewareAppManager.postslack(config["slack"], release_notes, args.dry_run)


def uploadBAM3(f, flavor, release_notes=None, post_slack_release_notes=False, dry_run=False):
    if not release_notes: release_notes = open(os.path.join(dirname, release_notes_file)).read()
    config = get_flavor(full_config, flavor)
    print("Uploading " + Color.YELLOW + f + Color.END + " for flavor " + Color.GREEN + flavor + Color.END)
    mail = config["mailto"] if "mailto" in config else None
    name = config["bam_name"] if "bam_name" in config else None
    slack = config["slack"] if "slack" in config else None
    return BewareAppManager.deploy("dev", build_file=f, dry_run=dry_run,
                                   release_notes=release_notes,
                                   #send_mail=mail, 
                                   post_slack=slack,
                                   post_slack_release_notes=post_slack_release_notes,
                                   bam_name=name,
                                   auto_create=True)


def pull_sdcard_files(args):
    load_config(args)
    # call('adb shell ls /sdcard/Android/data/%s/files | tr \'\\r\' \'\\0\' | xargs -I § adb pull "/sdcard/Android/data/%s/files/§"' % (pkg, pkg))
    path = "/sdcard/Android/data/%s/files" % pkg
    files = adb_ls(path)
    for f in files:
        adb_pull("%s/%s" % (path, f))


def gitstatus():
    args = "git diff --shortstat"
    return subprocess.check_output(args.split(" ")).decode()


def no_sub_parser(args):
    f = find_dot_adb()
    edit(f.name, sublime=True)


def move_run(args):
    load_config(args)
    name = config["bam_name"] if "bam_name" else shorten_bam_name(pck)
    BewareAppManager.move(from_channel=args.from_channel, to_channel=args.to_channel, version=args.version,
                          identifier=name)

def open_play(args):
    load_config(args)

    if len(args.flavors) > 0:
        for flavor in args.flavors:
            f = get_flavor(full_config, flavor)
            devacc = f["gplay_dev_acc"]
            call(["open","https://play.google.com/apps/publish/?dev_acc=%s#ApkPlace:p=%s" % (devacc, f["package"])])
            time.sleep(0.1)
    else:
        call(["open","https://play.google.com/apps/publish/?dev_acc=%s#ApkPlace:p=%s" % (config["gplay_dev_acc"], pkg)])


# also in BewareAppManager
def shorten_bam_name(name):
    return name.replace("pt.beware.", "").replace("com.xtourmaker", "xtourmaker")

def cd_assets_folder(args):
    load_config(args)
    p = os.path.join(dirname,full_config["_gradle"],"src",flavorname,"assets")
    # call("cd "+p)
    if args.no_cd:
        print(p)
    else:
        print("cd "+p)
    os.makedirs(p,exist_ok=True)
    os.chdir(p)

def interpret(args):
    load_config(args)
    print("pkg: " + pkg)
    import IPython

    IPython.embed()

def loadadb2(args):
    load_all_config()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ADB Helper.")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Runs the commands on all connected devices. Only for some commands that use adb (marked with *).")
    parser.add_argument('--dry-run', action='store_true', help='Don\'t make changes.')
    subparsers = parser.add_subparsers()

    parser_config = subparsers.add_parser('config', help='Create a config file on this folder.')
    parser_config.set_defaults(func=create_config)

    parser_flavor = subparsers.add_parser('flavor', aliases=['f'],
                                          help='Flavor of the app. No arguments to output the current one; a name change to that flavor; --add to add a new flavor to the .adb file; --env to print an export string for the enviroment variables for the current flavor.')
    parser_flavor.add_argument('--add', action='store_true')
    parser_flavor.add_argument('--env', action='store_true')
    parser_flavor.add_argument('-x', action='store_true')
    parser_flavor.add_argument('--dump', action='store_true')
    parser_flavor.add_argument('name', nargs='?')
    parser_flavor.set_defaults(func=flavor)

    parser_clear = subparsers.add_parser('clear', aliases=['c'], help='Clears the app data. *')
    parser_clear.set_defaults(func=clear)

    parser_clear_start = subparsers.add_parser('clear-start', aliases=['cs'],
                                               help='Clears the app data and restarts it. *')
    parser_clear_start.set_defaults(func=clear_start)

    parser_debug = subparsers.add_parser('debug', aliases=['d'], help='Starts the app in Debug mode.')
    parser_debug.set_defaults(func=debug)

    parser_start = subparsers.add_parser('start', aliases=['s'], help='Starts the app. *')
    parser_start.set_defaults(func=start)

    parser_close = subparsers.add_parser('close', aliases=['fc'],
                                         help='Force closes the app. Only works on some devices. *')
    parser_close.set_defaults(func=close)

    parser_restart = subparsers.add_parser('restart', aliases=['r'], help="Force closes and starts the app.")
    parser_restart.set_defaults(func=restart)

    parser_install = subparsers.add_parser('install', aliases=['i'], help='Installs the app. *')
    parser_install.add_argument("flavors", nargs="*")
    parser_install.add_argument("--deployed", "-d", action='store_true')
    parser_install.set_defaults(func=install)

    parser_uninstall = subparsers.add_parser('uninstall', aliases=['u'], help='Uninstalls the app. *')
    parser_uninstall.set_defaults(func=uninstall)

    parser_install_start = subparsers.add_parser('install-start', aliases=['is'], help='Installs and starts the app. *')
    parser_install_start.add_argument("flavors", nargs="*")
    parser_install_start.add_argument("--deployed", "-d", action='store_true')
    parser_install_start.set_defaults(func=install_start)

    # create the parser for the "move" command
    parser_move = subparsers.add_parser("move", help="Move a version from one channel to another.")
    parser_move.add_argument("from_channel")
    parser_move.add_argument("to_channel")
    parser_move.add_argument("version", nargs="?", default=None)
    parser_move.add_argument("-identifier", nargs="?", default=None)
    parser_move.set_defaults(func=move_run)

    parser_pulldb = subparsers.add_parser('pulldb', aliases=['p'], help='Pulls a db from a device.')
    parser_pulldb.add_argument("--name", "-n", help="File name of the database to pull.")
    parser_pulldb.set_defaults(func=pulldb)

    parser_opendb = subparsers.add_parser('opendb', aliases=['db'], help='Pulls and opens a db from a device.')
    parser_opendb.add_argument("--name", "-n", help="File name of the database to open.")
    parser_opendb.set_defaults(func=opendb)

    parser_pullsd = subparsers.add_parser('pullsd', aliases=['psd'],
                                          help='Pulls all files from the app\'s data folder on the sdcard.')
    parser_pullsd.set_defaults(func=pull_sdcard_files)

    parser_deploy = subparsers.add_parser('deploy',
                                          help="Compiles as release, asks for release notes and uploads to TestFlight. Accepts a list of flavors, otherwise compiles all.")
    parser_deploy.add_argument("flavors", nargs="*")
    parser_deploy.add_argument("--no-compile", "-nc", action='store_true')
    parser_deploy.add_argument("--no-mail", "-nm", action='store_true')
    parser_deploy.set_defaults(func=deploy)

    parser_publish = subparsers.add_parser('publish', help="Publish to Google Play and post to Slack.")
    parser_publish.add_argument("flavors", nargs="*")
    parser_publish.add_argument("--skip-upload", "-nu", action='store_true', help="Skips the upload to Google Play.")
    parser_publish.add_argument("--skip-slack", "-ns", action='store_true', help="Skips the post to Slack.")
    parser_publish.set_defaults(func=publish)

    parser_open_play = subparsers.add_parser('play', help="Opens Google Play page for app(s).")
    parser_open_play.add_argument("flavors", nargs="*")
    parser_open_play.set_defaults(func=open_play)

    parser_assets = subparsers.add_parser('assets', help="cd's into the assets folder of the current flavor.")
    parser_assets.add_argument("--no-cd", action='store_true')
    parser_assets.set_defaults(func=cd_assets_folder)

    parser_repl = subparsers.add_parser("repl", help="Starts a shell.")
    parser_repl.set_defaults(func=interpret)

    args = parser.parse_args()
    # print(args)
    if "func" in args.__dict__:
        args.func(args)
    else:
        no_sub_parser(args)
