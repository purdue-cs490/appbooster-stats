import os

import cherrypy


CGROUP = '/sys/fs/cgroup'

class Responder(object):

    @cherrypy.expose
    def index(self):
        return 'Test'


application = cherrypy.tree.mount(Responder())


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8080, application, True)
