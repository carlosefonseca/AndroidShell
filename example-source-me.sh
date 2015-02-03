#!/usr/bin/env bash

# source this file to have nice access to the cool stuff

# Add something like this to your bash profile
# alias cdSHORTPROJECTNAME="cd ~/PROJECT_PATH && . source-me.sh"

if [ ! -d "AndroidShell" ]; then
    git submodule add https://github.com/carlosefonseca/AndroidShell.git
fi

# some bash functions not related to AndroidShell.py, including setandroid, incVersionCode, adbscreen
source AndroidShell/AndroidShell.sh

export PATH="$(pwd)/AndroidShell:$PATH"

# Shortcut for the most used commands
alias A="AndroidShell.py"
alias AF="A f"

