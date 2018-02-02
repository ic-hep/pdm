#!/bin/bash

pylint src/pdm | tee pylint.log

# Get the score (as an int)
SCORE=`grep 'Your code has been rated at' pylint.log \
        | grep -oP '[-0-9]+' | head -n 1`
rm -f pylint.log

echo "Detected pylint score (int): ${SCORE}"
if [ "${SCORE}" -lt "7" ]; then
  echo "Pylint score is too low."
  exit 1
fi
exit 0

