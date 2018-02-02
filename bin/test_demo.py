#!/usr/bin/env python

import os
import sys
TOP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMP_PATH = os.path.join(TOP_PATH, "src")
sys.path.append(IMP_PATH)

from pdm.utils.config import ConfigSystem
from pdm.demo.DemoClient import DemoClient

def show_turtles(client):
    turtles = client.get_turtles()
    print "Server Turtles: %s" % ', '.join(turtles.values())

def main():

    if len(sys.argv) != 2:
        print "Usage: test_demo.py <conf_file>"
        sys.exit(1)

    # We load a config so that the client can find the server
    # via the [location] block
    conf_file = sys.argv[1]
    ConfigSystem.get_instance().setup(conf_file)
    os.chdir(os.path.dirname(conf_file))
    # Create a client and run the hello function
    client = DemoClient()
    print "Hello Returned: %s" % client.hello().strip()

    # Now do Turtle stuff
    show_turtles(client)
    print "Adding Turtle..."
    my_id = client.add_turtle("New Turtle")['id']
    print "New turtle is ID: %u" % my_id
    show_turtles(client)
    print "Modifying turtle with ID %u" % my_id
    mt = client.modify_turtle(my_id, "My Lovely Turtle")
    print "Modified turtle: %" % mt
    show_turtles(client)

    print "Deleting new turtle."""
    client.del_turtle(my_id)
    show_turtles(client)


    # Do Token Demo
    print "\n\nTOKEN DEMO\n"
    token = client.get('get_token')
    print "Got Token: %s" % token

    # Try a request without a token
    try:
        res = client.get('verify_token')
        print "Tokenless request accepted!!! %s" % res
    except:
        print "No token request rejected as expected. :-)"
  
    # Try a request with the wrong token
    try:
        client.set_token('WRONGTOKEN')
        res = client.get('verify_token')
        print "Invalid token accepted!!! %s" % res
    except:
        print "Wrong token rejected, as expected. :-)"

    # Try a request with the correct token
    client.set_token(token)
    res = client.get('verify_token')
    print "Verify real token: %s" % res


if __name__ == '__main__':
    main()

