#!/usr/bin/env python3

import os
import json
import argparse
import subprocess
import threading
import glob
import IPython
import BewareAppManager

filename = ".adb"
config = None
path = None  # path for config file
dirname = None  # "dirname" for config file
pkg = None
args = None
release_notes_file = ".releasenotes"


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
    j = json.load(f)
    if ("_f" in j):
        try:
            return j[j["_f"]]
        except:
            print("Flavor '%s' doesn't exist!" % j["_f"])
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
    try:
        pkg = args.package
    except:
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
    [
    print("export %s=%s" % (k, v))
    for k, v in config["env"].items()]


def flavor(args):
    if args.add:
        return add_flavor(args)
    if args.env:
        return get_flavor_env(args)

    f, j = load_all_config()

    flavor = args.name
    if not flavor:
        if "_f" not in j:
            if len(j.keys()) == 1:
                set_flavor(f, list(j.keys())[0], j)
            else:
                print("No flavor set. Choose from these: %s" % ", ".join(j.keys()))
                return
        # print("Current flavor: %s  on file: %s" % (j["_f"], f.name))
        print("Current flavor: %s" % j["_f"])
        return

    if flavor in j:
        set_flavor(f, flavor, j)
        print("Selected flavor: " + flavor)
    else:
        print("Flavor '%s' doesn't exist!" % flavor)


def call(args):
    # print("CALL: " + str(args))
    if type(args) == str:
        args = args.split(" ")
    else:
        args = [item.split(" ") for item in args]
        args = [item for sublist in args for item in sublist]
        # print(" ")
    # print(args)
    # print(" ")
    print(" $ " + " ".join(args))
    return subprocess.call(args)


# def create_config_set(args)

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


def clear(args):
    load_config(args)
    adb("shell pm clear " + config["package"])


def clear_start(args):
    load_config(args)
    adb_list(["shell pm clear " + config["package"],
              "shell am start -n \"%s/%s\" -a android.intent.action.MAIN -c android.intent.category.LAUNCHER" % (
                  pkg, config["activity"])])


def debug(args):
    load_config(args)
    call("adb shell am start -D -n \"%s/%s\" -a android.intent.action.MAIN -c android.intent.category.LAUNCHER" % (
        pkg, config["activity"]))


def start(args):
    load_config(args)
    adb("shell am start -n \"%s/%s\" -a android.intent.action.MAIN -c android.intent.category.LAUNCHER" % (
        pkg, config["activity"]))


def close(args):
    load_config(args)
    adb("shell am force-stop \"%s\"" % pkg)


def adb_list(cmds, all=None):
    if not all: all = args.all

    if all:
        devices = [d.split("\t")[0] for d in
                   subprocess.check_output(["adb", "devices"]).decode("ascii").split("\n")[1:-2]]
        for d in devices:
            for c in cmds:
                call(["adb", "-s", d, c])
    else:
        for c in cmds:
            call("adb " + c)


def adb(cmd, all=None):
    if not all: all = args.all
    if type(cmd) == str:
        cmd = cmd.split(" ")
    else:
        cmd = [item.split(" ") for item in cmd]
        cmd = [item for sublist in cmd for item in sublist]

    if all:
        devices = [d.split("\t")[0] for d in
                   subprocess.check_output(["adb", "devices"]).decode("ascii").split("\n")[1:-2]]
        [call(["adb", "-s", d] + cmd) for d in devices]

    else:
        call(["adb"] + cmd)


def install(args):
    load_config(args)
    s = "find %s -path */build/apk/*.apk" % dirname
    x = subprocess.check_output(s.split(" ")).strip().decode()
    adb("install -r %s" % x)


def install_start(args):
    install(args)
    start(args)


def uninstall(args):
    load_config(args)
    adb("uninstall %s" % pkg, all=args.all)


def pulldb(args):
    load_config(args)

    dbn = args.name if args.name else config["dbname"]

    call("pkill Base")
    call("rm " + dbn)

    # trying direct pull
    success = call("adb pull /data/user/0/%s/databases/%s" % (pkg, dbn)) == 0 and os.path.exists(dbn)
    if success:
        call("adb pull /data/user/0/%s/databases/%s-journal" % (pkg, dbn)) == 0 and os.path.exists(dbn)

    else:
        # trying copy as root
        call("adb shell rm /sdcard/%s" % dbn)
        call("adb shell rm /sdcard/%s-journal" % dbn)
        call("adb shell su -c cp /data/user/0/%s/databases/%s /sdcard/" % (pkg, dbn))
        call("adb shell su -c cp /data/user/0/%s/databases/%s-journal /sdcard/" % (pkg, dbn))
        success = call("adb pull /sdcard/" + dbn) == 0
        if success:
            call("adb pull /sdcard/%s-journal" % dbn)

        else:
            # trying run-as
            call("adb shell rm /sdcard/" + dbn)
            call("adb shell run-as \"%s\" cp databases/%s /sdcard/" % (pkg, dbn))
            call("adb shell run-as \"%s\" cp databases/%s-journal /sdcard/" % (pkg, dbn))
            success = call("adb pull /sdcard/" + dbn) == 0
            if success:
                call("adb pull /sdcard/%s-journal" % dbn)

    if success:
        call("sqlite3 %s vacuum" % dbn)
        call(["open", dbn])
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


def deploy(args):
    load_config(args)

    if not args.no_compile:
        if len(args.flavors) == 0: print("Building ALL flavors.")

        gradle_cmd = "%s/gradlew assemble%sRelease" % (
            dirname, "Release assemble".join([x.title() for x in args.flavors]))

        gradle_thread = threading.Thread(target=call, args=(gradle_cmd,))
        gradle_thread.daemon = True
        gradle_thread.start()

    call("s -w " + release_notes_file)

    if not args.no_compile:
        gradle_thread.join()

    gitout = gitstatus()
    if len(gitout):
        print("⚠️  Git: " + gitout)

    if len(args.flavors) == 0: args.flavors = "*"

    files_list = [glob.glob("*/build/apk/*-%s-release.apk" % f) for f in args.flavors]
    files = [item for _sublist in files_list for item in _sublist]

    if len(files) == 0:
        files_list = [glob.glob("*/build/apk/*%s-debug-unaligned.apk" % f) for f in args.flavors]
        files = [item for _sublist in files_list for item in _sublist]

        print("No release apk found.")
        if len(files) > 0:
            print("Found the following debug apk%s:" % ("'s" if len(files) > 1 else ""))
            for item in files: print("- " + os.path.basename(item))
            if BewareAppManager.user_request("Upload %s? [Y/n] " % ("them" if len(files) > 1 else "it"), "yn",
                                             "y") == "n":
                files = None

    elif len(files) > 1:
        print("Files to upload:")
        [
        print("- " + os.path.basename(item))
        for item in files]

    for f in files:
        print("Uploading now: %s" % os.path.basename(f))
        upload(f)


def upload(file, list=None):
    if os.path.exists(os.path.join(dirname, ".bam2")):
        uploadBAM2(file)
    elif os.path.exists(os.path.join(dirname, ".bam")):
        uploadBAM(file)
    else:
        uploadTF(file, list)


"""
requires the following env vars:
export TF_LIST="Distribution list name"
export TF_TOKEN="API TOKEN"
export TF_TEAM_TOKEN="TEAM TOKEN"
"""


def uploadTF(file, list=None):
    if not list: list = os.environ["TF_LIST"]
    subprocess.call(["curl", "http://testflightapp.com/api/builds.json", "-#",
                     "-F", "file=@" + file,
                     "-F", "notes=@" + release_notes_file,
                     "-F", "api_token=" + os.environ["TF_TOKEN"],
                     "-F", "team_token=" + os.environ["TF_TEAM_TOKEN"],
                     "-F", "notify=True",
                     "-F", "replace=True",
                     "-F", "distribution_lists=" + list], stdout=subprocess.PIPE)


def uploadBAM(f):
    if BewareAppManager.deploy("dev", build_file=f, dry_run=False,
                               release_notes=open(os.path.join(dirname, release_notes_file)).read()):
        BewareAppManager.mail(channel="dev", dry_run=False)
        BewareAppManager.slackbot(channel="dev")


def uploadBAM2(f):
    BewareAppManager.deploy("dev", build_file=f, dry_run=True,
                            release_notes=open(os.path.join(dirname, release_notes_file)).read(),
                            send_mail=config["mailto"], post_slack=config["slack"])


def gitstatus():
    args = "git diff --shortstat"
    return subprocess.check_output(args.split(" ")).decode()


def no_sub_parser(args):
    f = find_dot_adb()
    call("s " + f.name)


def interpret(args):
    import IPython

    IPython.embed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ADB Helper.")
    parser.add_argument("--all", "-a", action="store_true",
                        help="Runs the commands on all connected devices. Only for some commands that use adb (marked with *).")
    parser.add_argument("--package", "-p", help="Specify the package name to use.")
    subparsers = parser.add_subparsers()

    parser_config = subparsers.add_parser('config', help='Create a config file on this folder.')
    parser_config.set_defaults(func=create_config)

    parser_flavor = subparsers.add_parser('flavor', aliases=['f'],
                                          help='Flavor of the app. No arguments to output the current one; a name change to that flavor; --add to add a new flavor to the .adb file; --env to print an export string for the enviroment variables for the current flavor.')
    parser_flavor.add_argument('--add', action='store_true')
    parser_flavor.add_argument('--env', action='store_true')
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

    parser_install = subparsers.add_parser('install', aliases=['i'], help='Installs the app. *')
    parser_install.set_defaults(func=install)

    parser_uninstall = subparsers.add_parser('uninstall', aliases=['u'], help='Uninstalls the app. *')
    parser_uninstall.set_defaults(func=uninstall)

    parser_install_start = subparsers.add_parser('install-start', aliases=['is'], help='Installs and starts the app. *')
    parser_install_start.set_defaults(func=install_start)

    parser_pulldb = subparsers.add_parser('pulldb', aliases=['p'], help='Pulls a db from a device.')
    parser_pulldb.add_argument("--name", "-n", help="File name of the database to pull.")
    parser_pulldb.set_defaults(func=pulldb)

    parser_deploy = subparsers.add_parser('deploy',
                                          help="Compiles as release, asks for release notes and uploads to TestFlight. Accepts a list of flavors, otherwise compiles all.")
    parser_deploy.add_argument("flavors", nargs="*")
    parser_deploy.add_argument("--no-compile", "-nc", action='store_true')
    parser_deploy.set_defaults(func=deploy)

    parser_repl = subparsers.add_parser("repl", help="Starts a shell.")
    parser_repl.set_defaults(func=interpret)

    args = parser.parse_args()
    # print(args)
    if "func" in args.__dict__:
        args.func(args)
    else:
        no_sub_parser(args)


