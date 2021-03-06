#!/usr/bin/env python
""" Clients for DemoService application. """

from pdm.framework.RESTClient import RESTClient

class DemoClient(RESTClient):
    """ A client class for DemoService. """

    def __init__(self):
        """ Load config & configure client. """
        super(DemoClient, self).__init__('demo')

    def hello(self):
        """ Call the hello function on the server and return the result.
        """
        return self.get('hello')

    def get_turtles(self):
        """ Returns a dict of turtles.
            Key is ID (tid) and value is turtle name.
        """
        return self.get('turtles')

    def del_turtle(self, tid):
        """ Deletes a turtle by ID.
            Returns None
        """
        target = 'turtles/%u' % tid
        return self.delete(target)

    def add_turtle(self, tname):
        """ Adds a turtle.
            Returns integer turtle ID.
        """
        new_turtle = {'name': tname}
        return self.post('turtles', new_turtle)

    def modify_turtle(self, tid, tname):
        """
        Modifies a turtle (change name)
        :param tname: new name
        :param tid: turtle id
        :return: modified turtle
        """
        target = 'turtles/%u' % tid
        return self.put(target, {'name': tname})
