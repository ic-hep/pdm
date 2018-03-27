#!/bin/sh

echo "Running dummy job with vars:"
echo "Variable SRC_PATH = ${SRC_PATH}"
echo "Variable DST_PATH = ${DST_PATH}"

if [ $# -eq 0 ]; then
    echo "No args!"
    exit 1
elif [ $1 = "list" ]; then
    echo "-rwx------. 1 arichard res0 155 Mar 26 11:14 copy.sh"
    echo "-rwx------. 1 arichard res0 404 Mar 27 13:38 dummy.sh"
    echo "-rwx------. 1 arichard res0 120 Mar 26 11:14 list.sh"
    echo "-rwx------. 1 arichard res0 114 Mar 26 11:14 remove.sh"
elif [ $1 = "remove" ]; then
    echo "rm ${SRC_PATH}"
elif [ $1 = "copy" ]; then
    echo "cp ${SRC_PATH} ${DST_PATH}"
else
    echo "Unknown job type!"
    exit 1
fi

sleep 5
exit 0
