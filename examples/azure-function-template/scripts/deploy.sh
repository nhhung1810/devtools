#!/bin/bash

# Can run zsh script/deploy.sh for extra feats.
# Remove this if use with other people
ntfy_noti() {
    curl -d "$1" ntfy.sh/yauangon
}

SUBSCRIPTION=""
FUNCTION_APP_NAME=""


# Remember to run az-login first
az account set --subscription $SUBSCRIPTION
pushd functions
echo "Start"
func azure functionapp publish $FUNCTION_APP_NAME
if [ $? -eq 0 ]
then
    echo "😀 Successfully deploy Az Function"
    ntfy_noti "😀 Successfully deploy Az Function"
else
    echo "🚨 Fail deploy Az Function"
    ntfy_noti "🚨 Fail deploy Az Function"
fi
popd
exit 0
