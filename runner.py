#!/usr/bin/python

import sys
import os
import argparse
import git
import datetime
import json
from collections import namedtuple
from termcolor import colored
from subprocess import call
from functools import partial
from integration import *

from hosts import HOSTS
from jira_utils import JiraUtils
from jira import JIRA, JIRAError


JIRA_URL = 'https://e8storage.atlassian.net'
JIRA_USER = 'jirabot@e8storage.com'
# Password for browser login if needed: 'la93G!s6V'
JIRA_TOKEN = 'Bn20J2d1i8lwSKyiiBRK54C0'  # For API access

class style:
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

LogEntry = namedtuple('LogEntry', ['email', 'hash', 'message'])

class IntegrationRunner(object):
    def __init__(self, conf):
        if not 'directory' in conf:
            conf['directory'] = raw_input("Enter path where E8 and touchstone are found: ")
        self._directory = conf['directory']

        if not 'user' in conf:
            conf['user'] = raw_input("Enter user name: ")
        self._user = conf['user']

        if not 'team' in conf:
            team_input = "None"
            while team_input not in ['null', 'y']:
                team_input = raw_input("Enter team [y or null]: ")
            conf['team'] = 'team_' + team_input
        self._team = conf['team']

        self._e8_repo = git.Git(os.path.join(self._directory, 'E8'))
        self._ts_repo = git.Git(os.path.join(self._directory, 'touchstone'))
        if not 'tested' in conf['branches']:
            conf['branches']['tested'] = self._team
        self._branch = conf['branches']['tested']

        if not 'tmp' in conf['branches']:
            conf['branches']['tmp'] = os.path.join(conf['user'],'tmp_integration')
        self._tmp_branch = conf['branches']['tmp']
        self._master_branch = conf['branches']['master']
        self._integ_branch = conf['branches']['integration']
        self._hosts = [h for h,v in HOSTS.iteritems() if conf['team'] in v['team']]

        self._integ_utils = IntegrationUtils(self._directory, self._hosts)
        self._build_server = conf['build_server']
        if not 'ssh_key' in conf:
            conf['ssh_key'] = '~/.ssh/id_rsa_qemu'
        self._ssh_key = conf['ssh_key']

    @staticmethod
    def git_log(repo, oldest_commit='HEAD~30', newest_commit='HEAD'):
        log = repo.log('--pretty=format:%ae, %h, %s', '{}...{}'.format(newest_commit, oldest_commit)).split('\n')
        if not log[0]:
            return []
        return [LogEntry(*commit.split(',',2)) for commit in log]

    @staticmethod
    def print_log(repo, branch, depth=30):
        jira = JiraUtils(JIRA_URL, JIRA_USER, JIRA_TOKEN)
        log = IntegrationRunner.git_log(repo, '{}~{}'.format(branch, depth), branch)
        longest_name = max([len(c.email.split('@')[0]) for c in log])
        width_str = '{{0: <{}}}'.format(longest_name)
        for commit in log:
            print colored(style.BOLD + commit.hash + style.END, 'magenta'),
            print colored(width_str.format(commit.email.split('@')[0]), 'cyan'),
            if commit.message.split(':')[0].lstrip(' ').startswith('CORE'):
                try:
                    ticket_key = commit.message.split(':')[0].split(',')[0]
                    status = jira.get_status(ticket_key)
                except JIRAError:
                    print colored(style.BOLD + "commit {} was not found in jira".format(ticket_key) + style.END, 'red')
                    raise JIRAError
                print colored(style.BOLD + '{0: <12}'.format(status) + style.END, 'yellow'),
            else:
                print colored('{0: <12}'.format("No Ticket"), 'yellow'),
            print colored(style.BOLD + commit.message + style.END, 'white')

    @staticmethod
    def orig(branch):
        return 'origin/' + branch

    def get_candidates(self, repo, branch='HEAD'):
        intersection_commit = repo.merge_base(branch, self.orig(self._master_branch))
        return IntegrationRunner.git_log(repo, intersection_commit, branch)

    def integrating(self, repo, branch='HEAD'):
        candidates = self.get_candidates(repo, branch)
        integrating_candidate = self.get_candidates(repo, self.orig(self._integ_branch))
        latest_master = self.git_log(repo,
                                     self.orig(self._master_branch)+'~40',
                                     self.orig(self._master_branch))
        not_in_master = [can for can in candidates if can.message not in [lm.message for lm in latest_master]]
        return [ (can, can.message in [x.message for x in integrating_candidate]) for can in not_in_master ]

    @staticmethod
    def print_candidates(candidates):
        if not candidates:
            print colored(style.BOLD + 'No candidates found' + style.BOLD, 'green')
            return

        longest_name = max([len(c[0].email.split('@')[0]) for c in candidates])
        width_str = '{{0: <{}}}'.format(longest_name)
        jira = JiraUtils(JIRA_URL, JIRA_USER, JIRA_TOKEN)
        for c in candidates:
            if (c[1]):
                print colored(style.BOLD + 'INTEGRATING    ' + style.BOLD, 'green'),
            else:
                print colored(style.BOLD + 'NOT INTEGRATING' + style.BOLD, 'yellow'),
            print colored(style.BOLD + c[0].hash + style.END, 'magenta'),
            print colored(width_str.format(c[0].email.split('@')[0]), 'cyan'),
            if c[0].message.split(':')[0].lstrip(' ').startswith('CORE'):
                try:
                    ticket_key = c[0].message.split(':')[0].split(',')[0]
                    status = jira.get_status(ticket_key)
                except JIRAError:
                    print colored(style.BOLD + "commit {} was not found in jira".format(ticket_key) + style.END, 'red')
                    continue
                print colored('{0: <12}'.format(status), 'green' if status in ['In Test', 'Integrating'] else 'red'),
            else:
                print colored('{0: <12}'.format("No Ticket"), 'yellow'),
            print colored(style.BOLD + c[0].message + style.END, 'white')

    def show_candidates(self, branch=None):
        if not branch:
            branch = self.orig(self._branch)
        self._e8_repo.fetch()
        print colored(style.BOLD + 'E8' + style.BOLD)
        self.print_candidates(self.integrating(self._e8_repo, branch))
        print ""
        self._ts_repo.fetch()
        print colored(style.BOLD + 'touchstone' + style.BOLD)
        self.print_candidates(self.integrating(self._ts_repo, branch))

    def _prepare_repo_for_integration(self, repo, branch):
        repo.fetch()
        repo.checkout('-B', self._tmp_branch)
        repo.reset('--hard', self.orig(branch))
        repo.rebase(self.orig(self._master_branch))
        repo.push('-f', 'origin', self._tmp_branch)

    def prepare_for_integration(self, branch=None):
        if not branch:
            branch = self._branch
        print colored(style.BOLD + "Preparing branch {} on E8 ".format(self._tmp_branch) + style.BOLD, 'green')
        self._prepare_repo_for_integration(self._e8_repo, branch)
        print colored(style.BOLD + "Preparing branch {} on touchstone ".format(self._tmp_branch) + style.BOLD, 'green')
        self._prepare_repo_for_integration(self._ts_repo, branch)
        print colored(style.UNDERLINE + "\nCandidates".format(self._tmp_branch) + style.UNDERLINE, 'green')
        self.show_candidates(self._tmp_branch)

    def _get_integ_utils(self, directory, hosts):
        if not directory and not hosts:
            return self._integ_utils

        if not directory:
            directory = self._directory
        if not hosts:
            hosts = self._hosts
        return IntegrationUtils(directory, hosts)

    def verify_vft(self):
        with open(os.path.join(self._directory, 'E8/version/version_for_touchstone'), 'r') as vft:
            e8_vft = (vft.read().split('\n')[0])
        with open(os.path.join(self._directory, 'touchstone/version/version_for_touchstone'), 'r') as vft:
            ts_vft = (vft.read().split('\n')[0])
        if (e8_vft != ts_vft):
            print colored(style.BOLD + "BAD version_for_touchstone E8 - {}, touchstone - {}".format(e8_vft, ts_vft) + style.BOLD, 'red')
            return False
        print colored(style.BOLD + 'version for touchtone {} matches!'.format(e8_vft) + style.BOLD, 'green')
        return True

    def status(self, directory=None, hosts=None, print_ok_session=True):
        integ = self._get_integ_utils(directory, hosts)
        is_done = integ.get_latest_results()
        return is_done

    def failed_tests(self, directory=None, hosts=None):
        integ = self._get_integ_utils(directory, hosts)
        total_errors = integ.get_artifacts_of_errors()
        if total_errors:
            print colored(style.BOLD + "A total of {} tests failed".format(total_errors) + style.END, 'red')

    def fab(self, cmd):
        call(['fab','-u', self._user, '-i', self._ssh_key] + cmd.split())

    def start_warmup(self, tested_branch=None):
        self.prepare_for_integration(tested_branch)
        print ""
        assert self.verify_vft(), "bad version for touchstone"
        self.fab('-H {} build_candidate_single:repo_path={}'.format(
            self._build_server, self._directory))
        self.fab('run_tests:team={},repo_path={}'.format(
            self._team, self._directory))

    def stop_warmup(self):
        self.fab('stop_run:team={},directory={}'.format(self._team, self._directory))

def parse_args():
    parser = argparse.ArgumentParser(description='Integration util')
    parser.add_argument('-f', '--conf', help='json config file')
    return parser.parse_args()

def main():
    args = parse_args()
    os.system('clear')
    print colored('Welcome to the integration runner', 'green')

    if not args.conf:
        pathname = os.path.dirname(sys.argv[0])
        conf_path = os.path.join(os.path.abspath(pathname), 'conf.json')
    else:
        conf_path = args.conf
    print 'Loading ' + conf_path
    with open(conf_path, 'r') as conf_file:
        integration_conf = json.load(conf_file)
    ig = IntegrationRunner(integration_conf)

    with open(conf_path, 'w') as fp:
        json.dump(integration_conf, fp)
    import IPython; IPython.embed()

if __name__ == '__main__':
    main()
