#!/usr/bin/env bash

# This script contains Android related stuff, independent of the AndroidShell.py


# Presents a list of connected devices and asks the user to select one.
# If there's only one, that one will be automatically selected.
# The selected device id will to stored on the ANDROID_SERIAL env var so that call to adb will go directly to that device.
# Because this uses export, this script should be on you .bash_profile or some other file that gets sourced.
setandroid() {
    # print device list
    setAndroid.rb
    # get device count
    n=$(setAndroid.rb simple | wc -l)
    if [ $n -eq 1 ]; then
        # if only one device, does not ask user
        number=1
    else
        # if more than one device, ask the user for which one
        read -p "Device: " number
    fi

    # if is number and within range
    if [[ "$number" =~ ^[0-9]+$ ]] && [ "$number" -ge 1 -a "$number" -le $n ]; then
        # obtains the device id, stores in env
        export ANDROID_SERIAL=$(setAndroid.rb ${number})
        # obtains the device model, stores in env
        export ANDROID_MODEL=$(setAndroid.rb model)
        # prints the current env
        env | grep ANDROID_SERIAL
        return 0
    fi
    echo "invalid"
    return 1
}

# downloadFilesOfPackage fbooking -> lists files
# downloadFilesOfPackage fbooking 1 -> downloads file at index 1
# downloadFilesOfPackage fbooking 1 3 -> downloads files between index 1 and 3
function downloadAndroidFile {
    if [[ -z $3 ]]; then
        if [[ -z $2 ]]; then
            if [[ -z $1 ]]; then
                echo "androidDownloadFile package <#firstFile> [<end>]"
            else
    			adb shell ls /mnt/sdcard/Android/data/$1/cache | tail -r -n 140 | perl -pe 's/\x0D\x0A/\n/g' | awk -v d=$(date +%s) 'BEGIN {x=1;print "N\tSecs\tFilename"} {print x "\t" d-substr($0,0,10) "\t" $0 ; x++}'
            fi
        else
            D="/mnt/sdcard/Android/data/$1/cache"
            if [[ $2 -lt 0 ]]; then
                A=$(adb shell ls $D | tail -r -n 50 | tr '\r' '\0')
                echo -e $A | xargs -0 -P 1 -I {} echo -e {}
            else
                if [[ $2 -ge 2 ]]; then
                    A=$(adb shell ls $D | grep "14*" |  tail -r -n $2 | tail -n 1 | tr '\r' '\0')
                else
                    A=$(adb shell ls $D | grep "14*" |  tail -n 1 | tr '\r' '\0')
                fi
                echo $A
                adb pull $D/$A
                open $A
            fi
        fi
    else
        for (( i=$2 ; i<=$3 ; i++ ))
        do
            echo $i
            downloadAndroidFile $1 $i
        done
    fi
}

function ceftimestamp {
    date +"%F_%H.%M.%S"
}

# runs an adb command on all devices
# ex: adball install -r somefile.apk
function adball {
    adb devices | grep -v List | grep device | perl -p -e 's/(\w+)\s.*/\1/' | xargs -I § adb -s § "$@"
}

# screencapture current device
function adbscreen {
    A="screen-$(ceftimestamp)"
    adb shell screencap -p | perl -pe 's/\x0D\x0A/\x0A/g' > $A.png
}

# screencapture current device and view file
function adbscreenopen {
    A="screen-$(ceftimestamp)"
    adb shell screencap -p | perl -pe 's/\x0D\x0A/\x0A/g' > $A.png && open $A.png
}

# screencapture all devices
function adbscreenall {
    adb devices | grep -v List | grep device | perl -p -e 's/(\w+)\s.*/\1/' | xargs -I § sh -c 'adb -s "$1" shell screencap -p | perl -pe "s/\x0D\x0A/\x0A/g" > "screen_$1.png" && open "screen_$1.png"' -- §
}

adbscreendesk () {
    A="screen-$(ceftimestamp)"
    adb shell screencap -p | perl -pe 's/\x0D\x0A/\x0A/g' > $A.png && mv $A.png ~/Desktop/
}

incVersionCode () {
    if [[ -z $1 ]]; then
        echo "Increments the versionCode on a AndroidManifest file."
        echo "Usage: incVersionCode path/to/AndroidManifest.xml"
        echo
        echo "Found these AndroidManifest files:"
        find . -name "AndroidManifest.xml" -path "*/src/*"
    else
        perl -i -pe 's/(?<=versionCode=")(\d+)/$1+1/ge' WDAA/src/main/AndroidManifest.xml
    fi
}