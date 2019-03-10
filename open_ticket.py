#!/usr/bin/python

import os
import sys
from jira import JIRA
import tarfile
import argparse
import webbrowser

JIRA_URL = 'https://e8storage.atlassian.net'
JIRA_USER = 'yoni'
JIRA_PASSWORD = 'QUACKQUACKQUACK'



def tar_artifacts(name, path):
    with tarfile.open(name, "w:gz") as tar:
        tar.add(path)

def create_issue(test_name, path, subject):
    attachment_name = test_name + ".tar.gz"
    tar_artifacts(attachment_name, path)

    jira = JIRA(options={'server': JIRA_URL},basic_auth=(JIRA_USER, JIRA_PASSWORD))
    issue_dict = {
        'project': {'key': 'CORE'},
        'summary': subject,
        'description': 'Artifacts attached',
        'issuetype': {'name': 'Bug'},
    }
    new_issue = jira.create_issue(fields=issue_dict)
    jira.add_attachment(issue=new_issue, attachment=attachment_name)

    print 'new issues created ' + new_issue.key
    webbrowser.open('https://e8storage.atlassian.net/browse/' + new_issue.key)

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
    artifacts_path = args.artifacts_dir
    subject = args.subject if args.subject != None else '{} failed on nightly run'.format(test_name)
    #tar_artifacts(test_name+".tar.gz", artifacts_path)

    create_issue(test_name, artifacts_path, subject)

if __name__ == '__main__':
    main()
