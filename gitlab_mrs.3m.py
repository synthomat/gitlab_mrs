#!/usr/local/bin/python3
import json
import http.client
import textwrap
from pathlib import Path
import os
import sys

# <bitbar.title>GitLab Merge Requests</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Anton Zering</bitbar.author>
# <bitbar.author.github>synthomat</bitbar.author.github>
# <bitbar.desc>Shows a summary of open Merge Requests on a GitLab instance</bitbar.desc>
# <bitbar.image>http://www.hosted-somewhere/pluginimage</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>http://url-to-about.com/</bitbar.abouturl>

token_file_name = ".gitlab_mrs"
token_file_path = os.path.join(Path.home(), token_file_name)


def error(*msg):
    print("Gitlab MRs Error | color=red")
    [print(m) for m in msg]


class Config:
    __tpl = """{
    "gitlab_host": "your.gitlab.host",
    "gitlab_token": "PRIVATE_TOKEN"
}"""

    def __init__(self, path):
        self.path = path
        self.gitlab_host = ""
        self.gitlab_token = ""

        self.check_config()

        with open(token_file_path, "r") as f:
            tkf = json.load(f)
            self.gitlab_host = tkf.get("gitlab_host")
            self.gitlab_token = tkf.get("gitlab_token")

    def check_config(self):
        err = False
        if not os.path.exists(token_file_path):
            err = True
            self.create_template()
        elif open(self.path, "r").read() == self.__tpl:
            err = True

        if err:
            error("Please update the config in %s|color=red" % self.path)
            sys.exit(1)

    def create_template(self):
        with open(self.path, "w") as f:
            f.write(self.__tpl)


class MiniGitLab:
    def __init__(self, config):
        self.host = config.gitlab_host
        self.token = config.gitlab_token
        self.api_root = "/api/v4"
        self.conn = http.client.HTTPSConnection(self.host)

    def _req(self, path, method='GET'):
        url = self.api_root + path
        headers = {"Private-Token": self.token}
        self.conn.request(method, url, headers=headers)
        resp = self.conn.getresponse()

        if resp.status >= 400:
            print("ERROR")
            return

        return json.loads(resp.read())

    def get_mrs(self, state='opened', scope='assigned_to_me'):
        mrs = self._req("/merge_requests?state=%s&scope=%s" % (state, scope))
        return mrs

    def get_project(self, id):
        return self._req("/projects/%d" % id)

    def get_me(self):
        return self._req("/user")

    def get_projects(self, ids=[]):
        projects = []

        for iid in ids:
            project = self.get_project(iid)
            projects.append(project)

        return projects


def extract_keys(dic, keys=[]):
    return {k: dic[k] for k in keys}


def to_mini_project(project):
    return extract_keys(project,
                        ['id', 'name', 'name_with_namespace', 'web_url'])


def to_mini_mr(mr):
    return extract_keys(
        mr,
        ['id', 'project_id', 'title', 'web_url', 'author', 'user_notes_count'])


def main():
    gitlab = MiniGitLab(Config(token_file_path))
    mrs = gitlab.get_mrs(scope='all')
    mini_mrs = list(map(lambda mr: to_mini_mr(mr), mrs))

    project_ids = list(set(map(lambda mr: mr['project_id'], mini_mrs)))

    mini_projects = list(
        map(lambda p: to_mini_project(p), gitlab.get_projects(project_ids)))

    mrs_by_project_id = {}
    comment_counts = 0

    for mr in mini_mrs:
        pid = mr['project_id']

        if pid not in mrs_by_project_id:
            mrs_by_project_id[pid] = []

        mrs_by_project_id[pid].append(mr)
        comment_counts += mr['user_notes_count']

    for mp in mini_projects:
        mp['merge_requests'] = mrs_by_project_id[mp['id']]

    project_count = len(mini_projects)
    mr_count = len(mini_mrs)
    print("🧰 %d MRs in %d Prj" % (mr_count, project_count))
    print("---")
    print("Gitlab Merge Requests (%d notes)|color=blue" % comment_counts)
    for p in sorted(mini_projects, key=lambda p: p['name_with_namespace']):
        print("%s [%d mrs]|href=%s" % (p['name_with_namespace'],
                                       len(p['merge_requests']), p['web_url']))

        for mr in p['merge_requests']:
            title = textwrap.shorten(mr['title'], width=40, placeholder="…")
            text = "--%s (%s) (%d notes)" % (title, mr['author']['username'],
                                             mr['user_notes_count'])
            print("%s|href=%s" % (text, mr['web_url']))


if __name__ == '__main__':
    main()
