#!/bin/bash

echo "travis_fold:start:pylint"
pylint src/pdm | tee pylint.log
echo "travis_fold:end:pylint"

# Get the score (as an int)
SCORE=`grep 'Your code has been rated at' pylint.log \
        | grep -oP '[-0-9]+' | head -n 1`
rm -f pylint.log

echo "Detected pylint score (int): ${SCORE}"
if [ "${SCORE}" -lt "9" ]; then
  echo "Pylint score is too low."
  exit 1
fi
exit 0

