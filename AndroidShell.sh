#!/usr/bin/env bash


# Presents a list of connected devices, renamed according to the list and asks the user to select one.
# If there's only one, that one will be automatically selected.
# The selected device id will to stored on the ANDROID_SERIAL env var so that call to adb will go directly to that device.
# Because this uses export, this script should be on you .bash_profile or some other file that gets sourced.
function setandroid {
    adb devices | sed '${/^$/d;}' | awk 'BEGIN {
            array["410013c...	device"] = "Tab 3";
			array["4df1c17...	device"] = "Galaxy S3"; 
			array["S566085...	device"] = "Galaxy GIO"; 
			array["373049A...	device"] = "Galaxy S";
			array["78F5FD0...	device"] = "Huawei";
            x=0 }{ if ($0 in array) a = array[$0]; else a = $0;
            if (x == 0) print a ; else print x "  " a; x++ }'
    n=`adb devices | wc -l | awk {'print $1'}`
    if [ $n -eq 3 ]; then
        number=1
    else
        read -p "Device: " number
    fi
    ID=`adb devices | sed -n "$((number+1))p" | perl -p -e 's/([^\s]+)\s+.*/\1/'`
    export ANDROID_SERIAL=$ID
    env | grep ANDROID_SERIAL
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
    			adb shell ls /mnt/sdcard/Android/data/$1/cache | grep "13*" | tail -r -n 140 | perl -pe 's/\x0D\x0A/\n/g' | awk -v d=$(date +%s) 'BEGIN {x=1;print "N\tSecs\tFilename"} {print x "\t" d-substr($0,0,10) "\t" $0 ; x++}'
            fi
        else
            D="/mnt/sdcard/Android/data/$1/cache"
            if [[ $2 -lt 0 ]]; then
                A=$(adb shell ls $D | grep "13*" | tail -r -n 50 | tr '\r' '\0')
                echo -e $A | xargs -0 -P 1 -I {} echo -e {}
            else
                if [[ $2 -ge 2 ]]; then
                    A=$(adb shell ls $D | grep "13*" |  tail -r -n $2 | tail -n 1 | tr '\r' '\0')
                else
                    A=$(adb shell ls $D | grep "13*" |  tail -n 1 | tr '\r' '\0')
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

# runs an adb command on all devices
# ex: adball install -r somefile.apk
function adball {
    adb devices | grep -v List | grep device | perl -p -e 's/(\w+)\s.*/\1/' | xargs -I § adb -s § "$@"
}

