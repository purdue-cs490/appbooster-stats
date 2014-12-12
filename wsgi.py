import os
import re
import time

import cherrypy

CGROUP = '/sys/fs/cgroup'
CGROUP_MEMORY_ROOT = os.path.join(CGROUP, 'memory')
CGROUP_CPU_ROOT = os.path.join(CGROUP, 'cpuacct')
CGROUP_MEMORY_SYSTEMD_ROOT = os.path.join(CGROUP_MEMORY_ROOT, 'system.slice')
CGROUP_CPU_SYSTEMD_ROOT = os.path.join(CGROUP_CPU_ROOT, 'system.slice')
DOCKER_SERVICE_REGEX = '^docker-%s.*\.scope$'
CGROUP_MEMSW_USAGE = 'memory.memsw.usage_in_bytes'
CGROUP_CPU_STAT = 'cpuacct.usage'
CGROUP_CPU_MEASURE_INTERVAL = 0.25


class Responder(object):

    @cherrypy.expose
    def index(self):
        return 'Welcome to AppBooster app stats server!'

    #def _parse_cpuacct_stat(self, stat):
        #stats = {}
        #for st in stat.split('\n'):
            #if st:
                #key, value = st.split()
                #stats[key] = int(value)

        #return stats


    def read_usage(self, path):
        with open(path, 'rb') as usage:
            return long(usage.read())


    def fill_stats(self, appid, resp_obj):
        docker_service_name_re = re.compile(DOCKER_SERVICE_REGEX % appid, re.IGNORECASE)
        service_names = []

        # Memory stats
        for service in os.listdir(CGROUP_MEMORY_SYSTEMD_ROOT):
            if docker_service_name_re.match(service):
                service_names.append(service)

        service_names_len = len(service_names)
        if service_names_len != 1:
            resp_obj['error'] = '%d memory matches found for appid %d' % (service_names_len, appid)
            return resp_obj

        service_name = service_names[0]
        service_memory_root = os.path.join(CGROUP_MEMORY_SYSTEMD_ROOT, service_name)
        memsw_usage_in_bytes_path = os.path.join(service_memory_root, CGROUP_MEMSW_USAGE)
        with open(memsw_usage_in_bytes_path, 'r') as memsw_usage_in_bytes_file:
            memsw_usage_in_bytes = long(memsw_usage_in_bytes_file.read())

        resp_obj['stats']['memory'] = {
            'memsw': {
                'usage_in_bytes': memsw_usage_in_bytes,
            },
        }

        # Cpu stats
        del service_names[:]
        for service in os.listdir(CGROUP_CPU_SYSTEMD_ROOT):
            if docker_service_name_re.match(service):
                service_names.append(service)

        service_names_len = len(service_names)
        if service_names_len != 1:
            resp_obj['error'] = '%d cpuacct matches found for appid %d' % (service_names_len, appid)
            return resp_obj

        service_name = service_names[0]
        service_cpu_root = os.path.join(CGROUP_CPU_SYSTEMD_ROOT, service_name)
        cpuacct_usage_path = os.path.join(service_cpu_root, CGROUP_CPU_STAT)
        start_cpu_usage = self.read_usage(cpuacct_usage_path)
        time.sleep(CGROUP_CPU_MEASURE_INTERVAL)
        end_cpu_usage = self.read_usage(cpuacct_usage_path)

        usage = (end_cpu_usage - start_cpu_usage) / (10**9 * CGROUP_CPU_MEASURE_INTERVAL)

        resp_obj['stats']['cpu'] = {
            'cpuacct': {
                'usage_percent': usage,
            },
        }

        return resp_obj

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stats(self, appid):
        resp_obj = {
            'error': None,
            'stats': {},
        }

        if not appid:
            resp_obj['error'] = 'appid parameter needed'
            return resp_obj

        self.fill_stats(appid, resp_obj)

        return resp_obj


application = cherrypy.tree.mount(Responder())


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 17999, application, True)
