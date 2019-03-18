#!/usr/bin/python

import os
import sys
from jira import JIRA
import tarfile
import argparse
import webbrowser
import re
import json
from collections import namedtuple
from termcolor import colored
from distutils.dir_util import copy_tree


JIRA_URL = 'https://e8storage.atlassian.net'
JIRA_USER = 'yoni'
JIRA_PASSWORD = 'GitAt5WX'
MAX_TAR_SIZE_BYTE = (50 << 20)

IssueEntry = namedtuple('IssueEntry', 'key status assignee')
ErrorEntry = namedtuple('ErrorEntry', 'testName comment artifacts issues')
jira = None

class style:
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def tar_artifacts(name, path):
    if os.path.exists(name):
        return

    with tarfile.open(name, "w:gz") as tar:
        tar.add(path)

def _is_logger_line(line):
    if re.match(r'^\[.*\]', line):
        return True
    return False

def _get_e8report_data(test_dir):
    test_dir_contents = os.listdir(test_dir)
    test_dir_contents.sort()
    (artifacts_dir, log, e8report) = test_dir_contents
    with open(os.path.join(test_dir, e8report)) as json_report:
        report_data = json.load(json_report)
    return report_data

def _get_trace_back(report_data):
    strace = ''
    if 'stacktrace' in report_data['errors'][0].keys():
        strace += report_data['errors'][0]['stacktrace']
    else:
        strace += report_data['errors'][0]['message']
    return strace

def create_issue(test_name, test_dir, ignore_if_to_large=False, subject=None, link_to_artifacts=None):
    attachment_name = test_name + ".tar.gz"
    tar_artifacts(attachment_name, test_dir)
    tar_size = os.stat(attachment_name).st_size
    no_artifacts = False
    if tar_size > MAX_TAR_SIZE_BYTE:
        print "{} is {} MB, that's too big".format(attachment_name, tar_size >> 20)
        no_artifacts = True
        if not ignore_if_to_large:
            sys.exit()

    global jira
    if jira == None:
        jira = JIRA(options={'server': JIRA_URL},basic_auth=(JIRA_USER, JIRA_PASSWORD))
    report_data = _get_e8report_data(test_dir)
    message = report_data['errors'][0]['message']
    tmp_subject = subject if subject != None else 'PHYSICAL-2U: {} - {}'.format(test_name, message)
    if len(tmp_subject) > 255 or '\n' in tmp_subject:
        subject = subject if subject != None else 'PHYSICAL-2U: {} failed'.format(test_name)
    else:
        subject = tmp_subject
    tb = _get_trace_back(report_data)
    e8_version = report_data['versions']['version_e8']
    e8_hash = report_data['versions']['hash_e8']
    ts_hash = report_data['versions']['hash_ts']
    issue_dict = {
        'project': {'key': 'CORE'},
        'summary': subject,
        'issuetype': {'name': 'Bug'},
    }
    new_issue = jira.create_issue(fields=issue_dict)
    if not no_artifacts:
        jira.add_attachment(issue=new_issue, attachment=attachment_name)

    print 'New issues created: {}\nPress Enter to continue\n'.format(new_issue.key)

    if link_to_artifacts != None:
        new_issue_artifacts_dir = os.path.join(link_to_artifacts, new_issue.key)
        copy_tree(test_dir,
                  os.path.join(new_issue_artifacts_dir, os.path.basename(test_dir)))
    else:
        new_issue_artifacts_dir = test_dir

    desc = '*artifacts*\n'
    desc += new_issue_artifacts_dir
    desc += '\n*E8 hash* - {}'.format(e8_hash)
    desc += '\n*touchstone hash* - {}'.format(ts_hash)
    desc += '' if no_artifacts else '\n*Artifacts are also attached*\n'
    desc += '\n{noformat}\n' + ('').join(tb) + '{noformat}\n'

    # Change the issue description without sending updates
    new_issue.update(description=desc)

    webbrowser.open('https://e8storage.atlassian.net/browse/' + new_issue.key)
    raw_input('New issues created: {}\nPress Enter to continue\n'.format(new_issue.key))
    return new_issue.key

def _assigne_name(issue):
    if issue.fields.assignee == None:
        return 'Unassigned'
    try:
        return issue.fields.assignee.name
    except TypeError:
        return issue.fields.assignee._session['name']

def _issue_entry(issue):
    return IssueEntry(
        issue.key,
        '\'{}\''.format(issue.fields.status.name),
        _assigne_name(issue))

def check_issue(test_name):
    global jira
    if jira == None:
        jira = JIRA(options={'server': JIRA_URL},basic_auth=(JIRA_USER, JIRA_PASSWORD))
    issues = jira.search_issues('text ~ \\"{}\\" and status != Done and project = CORE'.format(test_name))
    if len(issues) == 0:
        print "No jira issues found"
        return None
    issues_entry = [_issue_entry(issue) for issue in issues]
    error_entry = ErrorEntry(test_name, "", "", issues_entry)
    issue_keys = []
    for iss in issues:
        print '({}, {}, {})'.format(
                iss.key,
                iss.fields.status.name,
                _assigne_name(iss))

        print colored(style.UNDERLINE + '/'.join([JIRA_URL, 'browse', iss.key]) + style.END, 'blue')
        issue_keys.append(iss.key)
    return issue_keys

def main():
    parser = argparse.ArgumentParser(description='Automatic ticket opener')
    parser.add_argument("test_name",
                        help="Name of failed test")
    parser.add_argument("artifacts_dir",
                        help="Directory to compress and attach to the ticket")
    parser.add_argument('-s',
                        dest="subject",
                        required=False,
                        help="Ticket subject")
    args = parser.parse_args()

    test_name = args.test_name
    artifacts_dir = args.artifacts_dir
    link_to_artifacts=None
    create_issue(test_name, artifacts_dir, subject, link_to_artifacts)

if __name__ == '__main__':
    main()
