
from jira import JIRA

# JIRA_URL = 'https://e8storage.atlassian.net'
# JIRA_USER = 'jirabot'
# JIRA_PASSWORD = 'la93G!s6V'

class JiraUtils(object):
    def __init__(self, url, user, password):
        self.jira = JIRA(options={'server': url},basic_auth=(user, password))

    def get_issue(self, key):
        issues = self.jira.search_issues('key = {}'.format(key))
        if not issues:
            return None
        return issues[0]

    def get_status(self, key):
        issue = self.get_issue(key)
        if not issue:
            None
        return issue.fields.status.name
