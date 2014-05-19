AndroidShell
============

A set of very useful commands for doing all things Android Development related.

Notes:

* This is highly tailored for MY needs, but go ahead and adapt it.
* There are references to an AppManager which is a home-made service that isn't open source yet. It deploys APK's to a server. Replace that with what you have or remove the deploy stuff altoguether.

Stuff
-----

AndroidShell.sh contains some functions for defining current Android device, download of files and adb stuff.

AndroidShell.py contains stuff mostly tied to projects.


Project setup
-------------

We use projects with different flavors and this helps.

Create a .adb file, like the one on the repo, on your project dir and specify your stuff for each flavor. Currently there's package name, first activity name, database name and some environment variables.

Here's the list of commands for the python file:

    config              Create a config file on this folder.
    flavor (f)          Flavor of the app.
   						No arguments to output the current one;
  						a name change to that flavor;
 						--add to add a new flavor to the .adb file;
 						--env to print an export string for the enviroment variables for the current flavor.
    clear (c)           Clears the app data. *
    clear-start (cs)    Clears the app data and restarts it. *
    debug (d)           Starts the app in Debug mode.
    start (s)           Starts the app. *
    close (fc)          Force closes the app. Only works on some devices. *
    restart (r)         Force closes and starts the app.
    install (i)         Installs the app. *
    uninstall (u)       Uninstalls the app. *
    install-start (is)  Installs and starts the app. *
    pulldb (p)          Pulls a db from a device.
    pullsd (psd)        Pulls all files from the app's data folder on the
                        sdcard.

Options before the command:

	--all, -a           Runs the commands on all connected devices.
						Only for some commands that use adb (marked with *).
    --dry-run           Don't make changes (mostly on the deploy).