# Azure function starter template

You can either use VSCode Extension or other source to getting start. This is my examples for a multi-purpose, include azure function and maybe other works.

For usage with vscode tasks, rename the .vscode-example fo .vscode, and maybe put the .vscode to the root of project. This feature is not test.

Install the [azure development core tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python) to deployment from command line. You can also install via VSCode command pallette.

For deployment, run 

```[bash]
# Login to your account
az login
# Open the scripts/deploy.sh and modify 2 variables, then run
bash scripts/deploy.sh

# If you can not login, consider find an access token (ask other contributor if they can do that for you)

```