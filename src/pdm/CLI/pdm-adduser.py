""" Register a new user with the pdm
"""
__author__ = 'martynia'

import requests
import argparse
from flask import request

def add_user(user):

    res = requests.post('http://localhost:5000/users/api/v1.0/users', json=user)

    if res.status_code  == 201:
        print " user created OK "
        print res.json()[0]

    else:
        print " user creation failed "
        print res.status_code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
    parser.add_argument('-u', '--username', required=True)
    parser.add_argument('-n', '--name')
    parser.add_argument('-s', '--surname')
    parser.add_argument('-e', '--email')
    args = parser.parse_args()
    if args.verbose:
        print "verbosity turned on"

    if args.surname:
        surnaem =  args.surname
    else:
        surname = raw_input("Please enter your surname: ")

    if args.name:
        name = args.name
    else:
        name = raw_input("Please enter your given name: ")

    if args.email:
        email = args.email
    else:
        email = raw_input("Please enter your email address: ")

    from getpass import getpass
    password = getpass()

    User = request.db.tables.User
    user  = User(username = args.username, name = name, surname = surname,
                 email = email, state = 0, password = password)

    print "%s added. " % user

if __name__ == "__main__":

    main()

