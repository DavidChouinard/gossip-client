#!/bin/sh
# your repository folder
cd "/opt/recap-client/"

# fetch changes, git stores them in FETCH_HEAD
git fetch

# check for remote changes in origin repository
newUpdatesAvailable=`git diff HEAD FETCH_HEAD`
if [ "$newUpdatesAvailable" != "" ]
then
        service recap stop

        git merge FETCH_HEAD

        service recap start

        echo "--> installing new required system packages"

        xargs apt-get install -y < "pkglist"

        echo "--> installing new required python modules"

        pip install -r "requirements.txt"

        echo "--> latest update installed"

        if [ -e "update/post-update.sh" ]
        then
            . "update/post-update.sh"
        fi
else
        echo "--> no updates available"
fi
