#!/usr/bin/env python
""" Decorators for framework/FlaskWrapper. """

import json
import functools
from flask import Response, request

def export_inner(obj, ename, methods=None, redir=None):
    """ Inner function for export decorators.
        Obj is the object to export,
        See the export_ext function for further more details on the other
        parameters.
    """
    if not methods:
        methods = ["GET"]
    obj.is_exported = True
    if not hasattr(obj, 'exportables'):
        obj.exportables = []
    # (name, methods, auth)
    obj.exportables.append((ename, methods, redir))
    return obj

def export(obj):
    """ Class/Function decorator.
        Export a class or function via the GET method on the web-server.
        The export name will be the __name__ value of the object.
    """
    return export_inner(obj, obj.__name__)

def export_ext(ename, methods=None, redir=None):
    """ Class/Function decorator.
        Export a class or function via the web-server with extra options.
        ename - Export name of the item. This may be a relative name to inherit
                from the parent object, or absolute for an absolute path on the
                webserver.
        methods - A list of flask-style method names, i.e. ["GET", "POST"]
                  to allow access to this object. Defaults to GET only if set
                  to None.
        redir - An optional URL to redirect the user to on auth failure.
                Generally used for redirecting users back to the login page.
                The URL encoded resource string will be substituted into the
                %(return_to)s template if present.
        Note: If export_ext is used multiple times on the same function, the
              redir parameter is used from the first one (you should set it
              the same on all export_ext for a given function to avoid
              problems).
    """
    return functools.partial(export_inner, ename=ename,
                             methods=methods, redir=redir)

def startup(obj):
    """ Funciton decorator.
        Marks a function to be called at start-up on the webserver.
        The function will be called at the end of daemonisation before
        requests are accepted. The function is run in the application context
        (so flask.current_app is available, but not flask.request).
        The function should take a single parameter, which will recieve a
        dictionary of config options from the config file. If the application
        uses any keys, they should be removed from the dictionary.
    """
    obj.is_startup = True
    return obj

def startup_test(obj):
    """ Funciton decorator.
        Marks a function to be called at start-up on the webserver, but
        only if the service is running in test mode. Generally functions
        marked with this should pre-load a basic set of service test data.
        The function should take no parameters.
    """
    obj.is_test_func = True
    return obj

def db_model(db_obj):
    """ Attaches a non-instantiated class as the database model for this class.
        The annotated class should be exported with the export decorator.
        The database class should have an __init__ which takes a single model
        parameter. All database classes should be defined within __init__ and
        use the model parameter as the base class.
    """
    def attach_db(obj):
        """ Attches the db_obj to the db_model parameter of obj.
            Returns obj.
        """
        if hasattr(obj, 'db_model'):
            obj.db_model.append(db_obj)
        else:
            obj.db_model = [db_obj]
        return obj
    return attach_db

def decode_json_data(func):
    """Decorator to automatically decode json data."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # pylint: disable=missing-docstring
        """ Decode request.data """
        if not isinstance(request.data, dict):
            request.data = json.loads(request.data)
        return func(*args, **kwargs)
    return wrapper
