import os
import re

import cherrypy

CGROUP = '/sys/fs/cgroup'
CGROUP_MEMORY_SYSTEMD_ROOT = os.path.join(CGROUP, 'memory', 'system.slice')
DOCKER_SERVICE_REGEX = '^docker-%s.*\.scope$'
CGROUP_MEMSW_USAGE = 'memory.memsw.usage_in_bytes'


class Responder(object):

    @cherrypy.expose
    def index(self):
        return 'Welcome to AppBooster app stats server!'

    def memory_stats(self, appid, resp_obj):
        docker_service_name_re = re.compile(DOCKER_SERVICE_REGEX % appid, re.IGNORECASE)
        service_names = []
        for service in os.listdir(CGROUP_MEMORY_SYSTEMD_ROOT):
            if docker_service_name_re.match(service):
                service_names.append(service)

        service_names_len = resp_obj['matches'] = len(service_names)
        if service_names_len != 1:
            resp_obj['error'] = '%d matches found for appid %d' % (service_names_len, appid)
            return resp_obj

        service_name = service_names[0]
        service_memory_root = os.path.join(CGROUP_MEMORY_SYSTEMD_ROOT, service_name)
        memsw_usage_in_bytes_path = os.path.join(service_memory_root, CGROUP_MEMSW_USAGE)
        with open(memsw_usage_in_bytes_path, 'r') as memsw_usage_in_bytes_file:
            memsw_usage_in_bytes = long(memsw_usage_in_bytes_file.read())

        resp_obj['stats']= {
            'memory': {
                'memsw': {
                    'usage_in_bytes': memsw_usage_in_bytes,
                },
            },
        }
        return resp_obj

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stats(self, appid):
        resp_obj = {
            'error': None,
            'matches': 0,
            'stats': {},
        }

        if not appid:
            resp_obj['error'] = 'appid parameter needed'
            return resp_obj

        self.memory_stats(appid, resp_obj)

        return resp_obj


application = cherrypy.tree.mount(Responder())


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 17999, application, True)
