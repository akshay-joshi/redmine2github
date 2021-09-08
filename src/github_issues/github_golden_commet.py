import requests
import json
import time

from jinja2 import Environment, PackageLoader

if __name__ == '__main__':
    SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(SRC_ROOT)

try:
    from utils.msg_util import *
    from github_issues.md_translate import translate_for_github
except Exception as e:
    raise


class Issue:
    """ Data needed to represent an issue internally"""

    def __init__(self, issue_number, issue_id, issue_url):
        self.id = issue_id
        self.number = issue_number
        self.html_url = issue_url


class GitHubIssueHelper:
    """ Use GitHub's issue import api to create issues without triggering
        api abuse limits so easily
    """

    def __init__(self, gim=None, **config):
        self._user = config['user']
        self._repo = config['repo']
        self._token = config['password']

        self._auth = (self._user, self._token)
        self.issue_url = 'https://api.github.com/repos/%s/%s/issues' % \
                         (self._user, self._repo)
        self.get_issue_url = 'https://github.com/%s/%s/issues' % \
                             (self._user, self._repo)
        self.headers = {'Accept': 'application/vnd.github.v3+json'}

        self.jinja_env = Environment(loader=PackageLoader('github_issues',
                                                          'templates'))

        self.imported = 0
        self.gim = gim

    def create(self, issue_dict, journals, attachments):
        issue_data = {}
        issue_data['issue'] = issue_dict
        issue_data['comments'] = self.gim.process_journals(journals,
                                                           attachments)
        response = self.create_issue(issue_data)

        return response

    def check_import_loop(self, import_response, check_interval):
        check_data = json.loads(import_response)
        response = None

        while response is None:
            try:
                time.sleep(check_interval)
                msg('Checking issue import status')
                req = requests.get(check_data['url'], auth=self._auth,
                                   headers=self.headers)
                if req.status_code in [200, 201]:
                    resp_data = json.loads(req.text)
                    if 'status' in resp_data and \
                            resp_data['status'] == 'pending':
                        msg('import still processing ...')
                    elif 'status' in resp_data and \
                            resp_data['status'] == 'imported':
                        self.imported += 1
                        issue_url = json.loads(req.text)['issue_url']
                        issue_id = int(issue_url.split('/')[-1])
                        response = Issue(self.imported, issue_id, issue_url)
                    else:
                        print(resp_data)
                else:
                    print(req.status_code)
                    print(req.text)
            except Exception as e:
                print(e)

        return response

    def create_issue(self, issue_data):
        """
        This method is used to post the Rest API request to create the issue.
        """
        response = None
        req = requests.post(self.issue_url,
                            data=json.dumps(issue_data['issue']),
                            auth=self._auth, headers=self.headers)
        if req.status_code in [200, 201]:
            self.imported += 1
            issue_url = json.loads(req.text)['url']
            issue_id = int(issue_url.split('/')[-1])
            response = Issue(self.imported, issue_id, issue_url)
            # Add Comments using comments REST API
            self.add_comments(json.loads(req.text)['comments_url'],
                              issue_data['comments'])
        elif req.status_code in [202]:
            response = self.check_import_loop(req.text, 1)
        # In case of validation failed if specific user does not exist then
        # delete the assignee and try to recreate the issue.
        elif req.status_code in [422] and req.text.find('Validation Failed'):
            if 'assignee' in issue_data['issue']:
                del issue_data['issue']['assignee']
                # Recreate the issue again without assignee.
                response = self.create_issue(issue_data)
        else:
            print(req.status_code)
            print(req.text)

        return response

    def add_comments(self, comments_url, issue_data_comments):
        """
        This function is used to iterate through all the comments and add
        the comments using comments REST API.
        """
        for comment in issue_data_comments:
            com_req = requests.post(comments_url,
                                    data=json.dumps(comment),
                                    auth=self._auth, headers=self.headers)

            if com_req.status_code not in [200, 201]:
                print(com_req.status_code)
                print(com_req.text)

    def does_issue_exist(self, issue_number):
        """
        This function is used to check the specific issue is exists or not
        """
        get_url = self.get_issue_url + "/" + str(issue_number)
        req = requests.get(get_url, auth=self._auth, headers=self.headers)
        if req.status_code in [200, 201]:
            return True
        else:
            print(req.status_code)
            print(req.text)

        return False

    def update_issue(self, issue_number, update_data):
        """
        This function is used to update the issue using patch call to the
        appropriate REST API.
        """
        update_url = self.issue_url + "/" + str(issue_number)
        req = requests.patch(update_url, data=json.dumps(update_data),
                             auth=self._auth, headers=self.headers)
        if req.status_code in [200, 201]:
            return True
        else:
            print(req.status_code)
            print(req.text)

        return False


class GitHubIssueImporter:
    """ doc """

    def __init__(self, user_map_helper=None, **config):
        self._user = config['login']
        self._repo = config['repo']
        self._token = config['password']

        self.issues = GitHubIssueHelper(user_map_helper, **config)
