#!/bin/sh

echo "Running dummy job with vars:" >&2
echo "Variable SRC_PATH = ${SRC_PATH}" >&2
echo "Variable DST_PATH = ${DST_PATH}" >&2
read data
echo "read in data: ${data}" >&2
if [ $# -eq 0 ]; then
    echo "No args!" >&2
    exit 1
elif [ $1 = "list" ]; then
    echo '{"Code": 0, "id": "1.0", "Listing": {"root": [{"st_size": 123, "name": "frank.txt"}]}}'
elif [ $1 = "remove" ]; then
    echo "rm ${SRC_PATH}" >&2
elif [ $1 = "copy" ]; then
    echo "cp ${SRC_PATH} ${DST_PATH}" >&2
else
    echo "Unknown job type!" >&2
    exit 1
fi

/bin/sleep 5
exit 0
