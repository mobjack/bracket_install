#! /bin/sh
EXITCODE=0
# Check if tools/venv has been configured
if [ -d ./venv ]; then
    venv_check="OK"
else
    printf 'Python3 venv not found, attempting to install\n'
    `python3 -m venv venv/`
    if [ $? != 0 ] ; then
        venv_check="Failed"
        EXITCODE=1
    else
        venv_check="Installed"
    fi
fi

# Check for other commands
for pkg in ansible gcloud
do
    printf "${pkg}"
    check_cmd=`which ${pkg} > /dev/null ; echo $?`
    if [ $check_cmd == 0 ] ; then
        printf "\t-->${pkg} Installed\tOK\n"
    else
        printf "\t-->${pkg} Installed\tFailed\n"
        EXITCODE=1
    fi

done

printf "If any checks failed please install manually.\n\n"
printf "Now activate the python3 venv, run this command in your shell\n"
printf "  source ./tools/venv/bin/activate\n"
printf '\n'

exit ${EXITCODE}