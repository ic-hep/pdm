""" Job management interface.  Build and submit jobs to a worker queue """
__author__ = 'martynia'


from flask import request, jsonify, abort


def list_directory():
    """
    Trigger directory listing operation.
    :return: json doc containing directory listing
    """
    pass

def copy():
    """
    Copy files or directories
    :return:
    """
    pass

def remove():
    """
    Remove files or directories
    :return:
    """
    pass
