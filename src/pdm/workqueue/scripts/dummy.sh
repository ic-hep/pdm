#!/bin/sh

echo "Running dummy job with vars:"
echo "Variable SRC_PATH = ${SRC_PATH}"
echo "Variable DST_PATH = ${DST_PATH}"
read data
if [ $# -eq 0 ]; then
    echo "No args!"
    exit 1
elif [ $1 = "list" ]; then
    echo "read in data: ${data}" >&2
    echo '{"root": [{"name": "frank.txt", "st_size": 123}]}'
elif [ $1 = "remove" ]; then
    echo "rm ${SRC_PATH}"
elif [ $1 = "copy" ]; then
    echo "cp ${SRC_PATH} ${DST_PATH}"
else
    echo "Unknown job type!"
    exit 1
fi

/bin/sleep 5
exit 0
