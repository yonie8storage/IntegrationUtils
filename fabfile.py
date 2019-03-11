import os
from fabric.contrib.files import *
from fabric.api import *
import json
from collections import namedtuple
import csv
import humanfriendly
import datetime

from jira import JIRA
from hosts import HOSTS

env.user = 'yoni'
LOGS_DIR_ON_SERVER='/home/yoni/integration/_{}_logs'
REMOTE_E8_REPO_PATH = '/home/yoni/integration/'
CANDIDATE_BRANCH_NAME = 'yoni/team_y_nightly'


def allow_single(with_parallel):
    def decorator(f):
        globals()["{}_single".format(f.func_name)] = f
        f = roles("hosts")(f)
        if with_parallel:
            f = parallel(f)
        return f
    return decorator

def host_index_of_type():
    type = HOSTS[env.host]['type']
    host_list = [h for h,d in HOSTS.iteritems() if d['type'] == type]
    return host_list.index(env.host)

def host_index():
    host_list = [h for h,d in HOSTS.iteritems()]
    return host_list.index(env.host)

def count_hosts_of_type():
    type = HOSTS[env.host]['type']
    return len([h for h,d in HOSTS.iteritems() if d['type'] == type])

def count_hosts():
    return len(h)

JIRA_URL = 'https://e8storage.atlassian.net'
JIRA_USER = 'jirabot'
JIRA_PASSWORD = 'la93G!s6V'

env.roledefs = {"hosts" : [h for h in HOSTS]}
env.warn_only = True

ErrorEntry = namedtuple('ErrorEntry', 'testName comment artifacts issues')
IssueEntry = namedtuple('IssueEntry', 'key status assignee')

build_script = \
    """
        set -x
        set -e

        pushd {}
        sudo git clean -xdf
        git lfs pull
        ./build/build_in_mock.sh
        ./build/build_in_mock.sh {}
        popd
    """

warmup_cmd = \
    """
        set -x
        set -e

        cd {}
        screen -S {}-nightly -L -d -m sudo tools/e8slash run -vvv -k \"tag:integration_warmup and {} tag:deploy\" -l ../_{}_logs --default-test-timeout-secs 7200 --split-buckets {} --run-bucket {} --clean-after-test
    """

test_cmd = \
    """
        set -x
        set -e

        cd {}
        screen -S team_y-mytest -L -d -m sudo tools/e8slash run -vvv -k \"{}\" -l ../_{}_logs --default-test-timeout-secs 7200 --split-buckets {} --run-bucket {} --clean-after-test
    """

@parallel
@allow_single(with_parallel=True)
def build_candidate(repo_path=REMOTE_E8_REPO_PATH):
    formatted_script = build_script.format(os.path.join(repo_path, 'E8'),
                                           '' if HOSTS[env.host]['type'] == 'non-deploy' else 'hot_upgrade_targets full_disk_images')
    output = run('{}'.format(formatted_script))
    if not os.path.exists(env.host):
        os.makedirs(env.host)
    with open('{}/{}'.format(env.host,'build.txt'), "a+") as output_file:
        output_file.write(output)

@parallel
@allow_single(with_parallel=True)
def run_tests(team, repo_path=REMOTE_E8_REPO_PATH, print_only=False):
    num_buckets = count_hosts_of_type()
    if team not in HOSTS[env.host]['team']:
        return

    formatted_cmd = warmup_cmd.format(os.path.join(repo_path, 'touchstone'),
                                      team,
                                      '' if HOSTS[env.host]['type'] == 'deploy' else 'not',
                                      env.host,
                                      num_buckets,
                                      host_index_of_type()+1)
    print formatted_cmd
    if not print_only:
        run('{}'.format(formatted_cmd), pty=False)

@parallel
@allow_single(with_parallel=True)
def run_test(name, use_buckets=True,repo_path=REMOTE_E8_REPO_PATH):
    print "use_buckets = {}".format(use_buckets)
    if use_buckets == True:
        num_buckets = count_hosts()
        bucket_idx = host_index()+1
    else:
        num_buckets = 1
        bucket_idx = 1
    print "num_buckets = {}, bucket_idx = {}".format(num_buckets, bucket_idx)

    formatted_cmd = test_cmd.format(repo_path+'/touchstone',
                                    name,
                                    env.host,
                                    num_buckets,
                                    bucket_idx)
    print formatted_cmd
    run('{}'.format(formatted_cmd), pty=False)

@runs_once
def start_warmup(branch_name=CANDIDATE_BRANCH_NAME):
    execute(partial(prepare_candidate_ts_single, branch_name), hosts=['gemini'])
    execute(partial(prepare_candidate_e8_single, branch_name), hosts=['gemini'])
    execute(verify_vft_single, hosts=['polaris'])
    execute(build_candidate_single, hosts=['polaris'])
    execute(run_tests, hosts=HOSTS.keys())
    now = datetime.datetime.now()
    print "I'm done and it's already " + str(now)

def _get_latest_data(logs_dir=LOGS_DIR_ON_SERVER):
    with hide('running', 'stdout', 'stderr', 'warnings'):
        logs_dir_on_server = logs_dir.format(env.host)
        latest_log = run('ls -tr {} | tail -n1'.format(logs_dir_on_server))
        session_log = 'session_{}-e8report.json'.format(latest_log)
        remote_log_dir = '{}/{}'.format(logs_dir_on_server, latest_log)
        try:
            get('{}/{}'.format(remote_log_dir, session_log))
            with open('{}/{}'.format(env.host, session_log)) as data_file:
                return remote_log_dir, json.load(data_file)
        except ValueError:
            print "Oops!  no session file found. Try again..."
            return [None, None]


def _issue_entry(issue):
    return IssueEntry(
        issue.key,
        '\'{}\''.format(issue.fields.status.name),
        issue.fields.assignee.name if issue.fields.assignee != None
        else 'Unassigned'
        )

def _check_know_issues(errors):
    jira = JIRA(options={'server': JIRA_URL},basic_auth=(JIRA_USER, JIRA_PASSWORD))
    result = []
    for error in errors:
        test_name = error['address'].split('.')[-1].split('(')[0]
        issues = jira.search_issues('text ~ \\"{}\\" and status != Done and project = CORE'.format(test_name))
        issues_entry = [_issue_entry(issue) for issue in issues]
        error_entry = ErrorEntry(test_name, "", "", issues_entry)
        result.append(error_entry)
        print error['status'] + \
            ": " + \
            test_name + \
            " ", \
            ['({}, {}, {})'.format(iss.key,
                                   iss.fields.status.name,
                                   iss.fields.assignee.name if iss.fields.assignee != None else 'Unassigned') \
                for iss in issues]
    return result

@parallel
@roles("hosts")
def artifacts(repo_path=REMOTE_E8_REPO_PATH):
    try:
        remote_log_dir, data = _get_latest_data(repo_path + '/_{}_logs')
        if not data:
            print "{} - No artifacts found".format(env.host)
            return
        errors = [s for s in data['statuses'] if s['status'] in ["error", "failure"]]
        for error in errors:
            with hide('running', 'stdout', 'stderr', 'warnings'):
                test_name = error['address'].split('.')[-1].split('(')[0]
                test_dir = run('ls {} | grep {} | grep {}'.format(
                    remote_log_dir,
                    test_name,
                    error['run_id']))
                get('{}/{}'.format(remote_log_dir, test_dir))
    except ValueError:
        print "Seems like there is no session running"



@allow_single(with_parallel=False)
def progress(check_know_issues=True, repo_path=REMOTE_E8_REPO_PATH):
    try:
        remote_log_dir, data = _get_latest_data(repo_path + '/_{}_logs')
        if not data:
            print "{} - No artifacts found".format(env.host)
            return
        print('{}:'.format(env.host))
        print('started: {}'.format(json.dumps(data['stopwatch']['start_time_str'])))
        dur_str = humanfriendly.format_timespan(int(json.dumps(data['stopwatch']['duration']))/1000) if data['stopwatch'].has_key('duration') else 'still running'
        print('duration: {}'.format(dur_str))
        print('{}'.format(json.dumps(data['counters'], indent=4, sort_keys=True)))
        print('--------------------------')
        if check_know_issues:
            check_issues()
    except ValueError:
        print "Seems like there is no session running"

@parallel
@allow_single(with_parallel=True)
def check_issues():
    remote_log_dir, data = _get_latest_data()
    if not data:
            print "{} - No artifacts found".format(env.host)
            return
    errors = [s for s in data['statuses'] if s['status'] in ["error", "failure"]]
    issues = _check_know_issues(errors)
    print ""

@parallel
@allow_single(with_parallel=False)
def status(repo_path=REMOTE_E8_REPO_PATH):
    progress(check_know_issues=False, repo_path=repo_path)

@allow_single(with_parallel=True)
def magic(repo_path=REMOTE_E8_REPO_PATH):
    progress(check_know_issues=True, repo_path=repo_path)
    artifacts(repo_path)

@allow_single(with_parallel=True)
def getntp():
    run('timedatectl')

@allow_single(with_parallel=True)
@roles("hosts")
def summary():
    execute(magic)

@roles("hosts")
def running_qemus():
    with quiet():
        running_qemus = run('ps -ef | grep x86 | grep -v -e grep -e TMPDIR | grep -v e8slash | grep "/home/[a-z]*.*/E8_qemu/x86_64" -o | grep "/home/[a-z]*" -o | cut -d "/" -f 3 | uniq -c')
        if running_qemus:
            print '{0: >8} - {1}'.format(env.host, running_qemus)
