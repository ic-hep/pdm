#!/bin/bash
# Run the full DemoService test server & client
# Expects to be run with CWD in top of repo.

# Try to make sure everything gets killed on unexpected exit.
trap 'if [ "x$(jobs -p)" != "x" ]; then kill $(jobs -p); fi' EXIT

# Check the test CA is built
if [ ! -d etc/certs ]; then
  pushd etc
  ./build_ca.sh
  popd
fi

# Now start the server
echo -e "\n***\nStarting Server...\n***\n" >&2
python bin/test_server.py etc/demo.conf &
SERVER_PID=$!
# Wait a few seconds for server to start-up
sleep 5

# Run the client
echo -e "\n***\nStarting Client...\n***\n" >&2
RET=0
python bin/test_demo.py etc/demo.conf
if [ "$?" -ne "0" ]; then
  echo -e "\n\nERROR: Test client finished with errors." >&2
  RET=1
else
  echo -e "\n\nSUCCESS: Test client finished without errors." >&2
fi

# Shutdown server as gracefully as possible
kill $SERVER_PID
wait $SERVER_PID
exit $RET

