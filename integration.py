import os
import paramiko
import json
import humanfriendly
import shutil
from termcolor import colored
import commands

class style:
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

class IntegrationUtils(object):
    def __init__(self, directory, hosts):
        self._hosts = hosts
        self._dir = directory

    def _exec_local_cmd(self, cmd):
        (status, output) = commands.getstatusoutput(cmd)
        if status:
            raise Exception(output)
        return output.splitlines()

    def _get_latest_data(self):
        hosts_session = dict()
        for host in self._hosts:
            logs_dir_on_server = '{}/_{}_logs'.format(self._dir, host)
            latest_session = self._exec_local_cmd('ls -tr {} | tail -n1'.format(logs_dir_on_server))[0]
            session_id = 'session_{}-e8report.json'.format(latest_session)
            session_dir = os.path.join(logs_dir_on_server, latest_session)
            session_log_path = os.path.join(session_dir, session_id)
            if not os.path.exists(host):
                os.mkdir(host)
            try:
                with open(os.path.join(host, session_log_path)) as data_file:
                    hosts_session[host] = (session_dir, json.load(data_file))
            except Exception:
                print colored(style.UNDERLINE + "{}".format(host) + style.END)
                print " Oops!  no session file found. Try again later..."
                continue
        return hosts_session, session_dir

    @staticmethod
    def _print_counters(session_data):
        counters = session_data['counters']
        if counters['ended'] == counters['filtered']:
            print colored(style.BOLD + "ended {}/{}".format(counters['ended'], counters['filtered']) + style.END)
        else:
            print "ended {}/{}".format(counters['ended'], counters['filtered'])
        print "succeed",
        print colored(counters['succeed'], 'green'),
        print "error",
        print colored(counters['error'], 'red' if counters['error'] else 'white'),
        print "failure",
        print colored(counters['failure'], 'red' if counters['failure'] else 'white')

    @staticmethod
    def _session_summary(session_data):
        print('started: {}'.format(json.dumps(session_data['stopwatch']['start_time_str'])))
        is_done = session_data['stopwatch'].has_key('duration')
        dur_str = humanfriendly.format_timespan(
            int(json.dumps(session_data['stopwatch']['duration']))/1000) \
                if is_done else 'still running'
        print('duration:'),
        print colored('{}'.format(dur_str), 'white' if is_done else 'yellow')
        IntegrationUtils._print_counters(session_data)
        print ""
        return is_done

    def get_latest_results(self):
        hs, session_dir = self._get_latest_data()
        print colored(style.BOLD + "Session summary: " + style.END, 'green')
        print colored(style.BOLD + "===========================" + style.END, 'green')
        is_done = True
        for host in hs.iterkeys():
            print colored(style.UNDERLINE + host + style.END)
            is_done = self._session_summary(hs[host][1]) and is_done
        if is_done:
            print colored(style.BOLD + "All runs are complete" + style.END, 'green')
        return is_done

    @staticmethod
    def _get_artifacts_of_errors(session_data, artifacts_dir):
        error_dirs = []
        errors = [s for s in session_data['statuses'] if s['status'] in ["error", "failure"]]
        if not len(errors):
            return
        for error in errors:
            test_artifacts_dir = [d for d in os.listdir(artifacts_dir) if d.endswith(error['run_id'])][0]
            error_dirs.append(test_artifacts_dir)
        return error_dirs

    def get_artifacts_of_errors(self):
        hs, session_dir = self._get_latest_data()
        for host in hs.iterkeys():
            errors = self._get_artifacts_of_errors(hs[host][1], hs[host][0])
            if errors:
                print colored(style.UNDERLINE + host + style.END)
                for error in errors:
                    print os.path.join(session_dir, error)

