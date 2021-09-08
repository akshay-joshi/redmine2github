from __future__ import print_function
from jinja2 import Environment, PackageLoader

import os
import sys
import json
import time
import re

import csv
import requests
import pygithub3

if __name__ == '__main__':
    SRC_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(SRC_ROOT)

try:
    from settings.base import get_github_auth, get_github_golden_auth, \
        REDMINE_SERVER, USE_IMPORT_API, REDMINE_CATEGORY_MAP, \
        REDMINE_STATUS_MAP, REDMINE_USER_MAP, REDMINE_VERSION_MAP, \
        REDMINE_PRIORITY_MAP, REDMINE_CF_MAP, REDMINE_TRACKER_MAP

    from utils.msg_util import *
    from github_issues.md_translate import translate_for_github
    from github_issues.milestone_helper import MilestoneHelper
    from github_issues.label_helper import LabelHelper

    from github_golden_commet import GitHubIssueImporter
except Exception as e:
    raise


class GithubIssueMaker:
    """
    Given a Redmine issue in JSON format, create a GitHub issue.
    These issues should be moved from Redmine in order of issue.id.
    This will allow mapping of Redmine issue ID's against newly created
    Github issued IDs.  e.g., can translate related issues numbers, etc.
    """
    ISSUE_STATE_CLOSED = ['Rejected', 'Closed', 'Resolved',
                          'Cannot Reproduce']

    def __init__(self, user_map_helper=None, label_mapping_filename=None,
                 milestone_mapping_filename=None, use_import_api=False):
        self.github_conn = None
        self.comments_service = None
        self.milestone_manager = MilestoneHelper(milestone_mapping_filename)
        self.label_helper = LabelHelper(label_mapping_filename)
        self.jinja_env = Environment(loader=PackageLoader('github_issues',
                                                          'templates'))
        self.user_map_helper = user_map_helper
        self.use_import_api = use_import_api

        self.redmine_category_map = self.read_csv_kvmap(REDMINE_CATEGORY_MAP)
        self.redmine_status_map = self.read_csv_kvmap(REDMINE_STATUS_MAP)
        self.redmine_user_map = self.read_csv_kvmap(REDMINE_USER_MAP)
        self.redmine_version_map = self.read_csv_kvmap(REDMINE_VERSION_MAP)
        self.redmine_priority_map = self.read_csv_kvmap(REDMINE_PRIORITY_MAP)
        self.redmine_cf_map = self.read_csv_kvmap(REDMINE_CF_MAP)
        self.redmine_tracker_map = self.read_csv_kvmap(REDMINE_TRACKER_MAP)

    def get_comments_service(self):
        if self.comments_service is None:
            self.comments_service = \
                pygithub3.services.issues.Comments(**get_github_auth())

        return self.comments_service

    def get_github_conn(self):
        if self.github_conn is None:
            self.github_conn = pygithub3.Github(**get_github_auth())
        return self.github_conn

    def get_github_golden_conn(self):
        if self.github_conn is None:
            self.github_conn = GitHubIssueImporter(
                self, **get_github_golden_auth())
        return self.github_conn

    def read_csv_kvmap(self, file_path):
        msgt('Loading cvs map: %s' % file_path)
        kv_map = {}
        if not os.path.exists(file_path):
            return kv_map

        with open(file_path, 'rU') as csvfile:
            map_reader = csv.reader(csvfile, delimiter=',')
            row_num = 0
            for row in map_reader:
                row_num += 1
                if row_num == 1 or len(row) == 0 or row[0].startswith('#'):
                    continue
                kv_map[row[0]] = row[1]

        # print(kv_map)
        return kv_map

    def format_name_for_github(self, author_name, include_at_sign=True):
        """
        (1) Try the user map
        (2) If no match, return the name
        """
        if not author_name:
            return None

        if self.user_map_helper:
            github_name = self.user_map_helper.get_github_user(
                author_name, include_at_sign)
            if github_name is not None:
                return github_name
        return author_name

    def get_redmine_assignee_name(self, redmine_issue_dict):
        """
        If a redmine user has a github account mapped, add the person as
        the assignee

        "assigned_to": {
            "id": 4,
            "name": "Philip Durbin"
        },
        /cc @kneath @jresig
        """
        if not type(redmine_issue_dict) is dict:
            return None

        redmine_name = redmine_issue_dict.get('assigned_to', {}).get(
            'name', None)
        if redmine_name is None:
            return None

        return redmine_name

    def get_assignee(self, redmine_issue_dict):
        """
        If a redmine user has a github account mapped, add the person as the
        assignee

        "assigned_to": {
            "id": 4,
            "name": "Philip Durbin"
        },
        /cc @kneath @jresig
        """
        if not type(redmine_issue_dict) is dict:
            return None

        redmine_name = redmine_issue_dict.get('assigned_to', {}).get(
            'name', None)
        if redmine_name is None:
            return None

        github_username = self.format_name_for_github(redmine_name,
                                                      include_at_sign=False)

        return github_username

    # TODO: search references in description text and also correct them
    def update_github_issue_with_related(self, redmine_json_fname,
                                         redmine2github_issue_map):
        """
        Update a GitHub issue with related tickets as specfied in Redmine

        - Read the current github description
        - Add related notes to the bottom of description
        - Update the description

        "relations": [
              {
                  "delay": null,
                  "issue_to_id": 4160,
                  "issue_id": 4062,
                  "id": 438,
                  "relation_type": "relates"
              },
              {
                  "delay": null,
                  "issue_to_id": 3643,
                  "issue_id": 4160,
                  "id": 439,
                  "relation_type": "relates"
              }
          ],
          "id": 4160,
        """
        if not os.path.isfile(redmine_json_fname):
            msgx('ERROR.  update_github_issue_with_related. file not '
                 'found: %s' % redmine_json_fname)

        # msg('issue map: %s' % redmine2github_issue_map)

        json_str = open(redmine_json_fname, 'rU').read()
        rd = json.loads(json_str)       # The redmine issue as a python dict
        # msg('rd: %s' % rd)

        # if rd.get('relations', None) is None:
        #    msg('no relations')
        #    return

        redmine_issue_num = rd.get('id', None)
        if redmine_issue_num is None:
            return

        github_issue_num = redmine2github_issue_map.get(
            str(redmine_issue_num), None)
        if github_issue_num is None:
            msg('Redmine issue not in nap')
            return

        # Related tickets under 'relations'
        #
        github_related_tickets = []
        original_related_tickets = []
        irelations = rd.get('relations', None)
        if irelations is not None:
            for rel in irelations:
                issue_to_id = rel.get('issue_to_id', None)
                if issue_to_id is None:
                    continue
                if rd.get('id') == issue_to_id:
                    # skip relations pointing to this ticket
                    issue_to_id = rel.get('issue_id', None)

                original_related_tickets.append((issue_to_id,
                                                 rel.get('relation_type',
                                                         '')))
                related_github_issue_num = \
                    redmine2github_issue_map.get(str(issue_to_id), None)
                msg(related_github_issue_num)
                if related_github_issue_num:
                    github_related_tickets.append((related_github_issue_num,
                                                   rel.get('relation_type',
                                                           '')))

        github_related_tickets.sort(key=lambda tup: tup[0])
        original_related_tickets.sort(key=lambda tup: tup[0])
        #
        # end: Related tickets under 'relations'

        # Related tickets under 'children'
        #
        # "children": [{ "tracker": {"id": 2, "name": "Feature"    },
        # "id": 3454, "subject": "Icons in results and facet"    }, ...]
        #
        github_child_tickets = []
        original_child_tickets = []

        child_ticket_info = rd.get('children', [])
        if child_ticket_info:
            for ctick in child_ticket_info:

                child_id = ctick.get('id', None)
                if child_id is None:
                    continue

                original_child_tickets.append(child_id)
                child_github_issue_num = redmine2github_issue_map.get(
                    str(child_id), None)

                msg(child_github_issue_num)
                if child_github_issue_num:
                    github_child_tickets.append(child_github_issue_num)
            original_child_tickets.sort()
            github_child_tickets.sort()
        #
        # end: Related tickets under 'children'

        update_issue = False
        try:
            issue = self.get_github_conn().issues.get(number=github_issue_num)
            # time.sleep(1)
            time.sleep(0.5)
            updated_description, update_issue = \
                self.fix_issue_references(issue.body,
                                          redmine2github_issue_map)
            if issue.comments > 0:
                comments = self.get_github_conn().issues.comments.list(
                    number=github_issue_num)
                # time.sleep(1)
                time.sleep(0.5)
                for page in comments:
                    for comm in page:
                        updated_cbody, did_match = \
                            self.fix_issue_references(
                                comm.body, redmine2github_issue_map)
                        if did_match is True:
                            self.get_github_conn().issues.comments.update(
                                id=comm.id, message=updated_cbody)
                            msg('Comment updated!')
                            # time.sleep(1)
                            time.sleep(0.5)
        except pygithub3.exceptions.NotFound:
            msg('Issue not found!')
            return

        #
        # Update github issue with related and child tickets
        #
        #
        if len(original_related_tickets) > 0 or \
                len(original_child_tickets) > 0:
            update_issue = True
            # Format related ticket numbers
            #
            original_issues_formatted = \
                ["""[%s](%s)""" % (x, self.format_redmine_issue_link(x))
                 for x, r in original_related_tickets]
            original_issues_str = ', '.join(original_issues_formatted)

            related_issues_formatted = \
                ['#%d (%s)' % (x, r) for x, r in github_related_tickets]
            related_issue_str = ', '.join(related_issues_formatted)
            msg('Redmine related issues: %s' % original_issues_str)
            msg('Github related issues: %s' % related_issue_str)

            # Format children ticket numbers
            #
            original_children_formatted = \
                ["""[%s](%s)""" % (x, self.format_redmine_issue_link(x))
                 for x in original_child_tickets]
            original_children_str = ', '.join(original_children_formatted)

            github_children_formatted = \
                ['#%d' % x for x in github_child_tickets]
            github_children_str = ', '.join(github_children_formatted)
            msg('Redmine sub-issues: %s' % original_children_str)
            msg('Github sub-issues: %s' % github_children_str)

            template = self.jinja_env.get_template('related_issues.md')
            template_params = {'original_description': issue.body,
                               'original_issues': original_issues_str,
                               'related_issues': related_issue_str,
                               'child_issues_original': original_children_str,
                               'child_issues_github': github_children_str}

            updated_description = template.render(template_params)

        if update_issue is True:
            issue = self.get_github_conn().issues.update(
                number=github_issue_num, data={'body': updated_description})
            time.sleep(1)
            msg('Issue updated!')  # ' % issue.body)

    def fix_issue_references(self, text, redmine2github_issue_map):
        # msg('fix_issue_references')
        result = text
        did_match = False

        # search comment references
        matches = re.findall(r'#[0-9]+(?:(?:-[0-9]+)|(?:#note-[0-9]+))', text)
        for match in matches:
            issue_id = re.search(r'#[0-9]+', match)
            msgt('Match (1st) found: %s' % issue_id.group(0))
            comm_nbr = re.search(r'-[0-9]+', match)
            git_issue = \
                redmine2github_issue_map.get(issue_id.group(0)[1:], None)
            comments = \
                self.get_github_conn().issues.comments.list(number=git_issue)

            i = 1
            url = None
            cni = int(comm_nbr.group(0)[1:])
            for page in comments:
                for comm in page:
                    if i == cni:
                        repl = comm.html_url
                        if repl is not None:
                            result = re.sub(match, repl, text)
                            did_match = True
                    i += 1

        # search issue references
        matches = re.findall(r'#[0-9]+', result)
        for match in matches:
            msgt('Match (2nd) found: %s' % match[1:])
            repl = redmine2github_issue_map.get(match[1:], None)
            if repl is not None:
                result = re.sub(match, '#' + str(repl), result)
                did_match = True

        return result, did_match

    def format_redmine_issue_link(self, issue_id):
        if issue_id is None:
            return None

        return os.path.join(REDMINE_SERVER, 'issues', '%d' % issue_id)

    def close_gitgub_issue_using_api(self, github_issue_id):
        """
        This function is used to close the issue while migrating using
        REST API.
        """
        issue_exists = \
            self.get_github_golden_conn().issues.does_issue_exist(
                github_issue_id)
        if issue_exists:
            status = \
                self.get_github_golden_conn().issues.update_issue(
                    github_issue_id, {'state': 'closed'})
            return status
        return False

    def close_github_issue(self, github_issue_num):
        if not github_issue_num:
            return False
        msgt('Close issue: %s' % github_issue_num)

        try:
            issue = self.get_github_conn().issues.get(number=github_issue_num)
        except pygithub3.exceptions.NotFound:
            msg('Issue not found!')
            return False

        if issue.state in self.ISSUE_STATE_CLOSED:
            msg('Already closed')
            return True

        updated_issue = \
            self.get_github_conn().issues.update(number=github_issue_num,
                                                 data={'state': 'closed'})
        if not updated_issue:
            msg('Failed to close issue')
            return False

        if updated_issue.state in self.ISSUE_STATE_CLOSED:
            msg('Issue closed')
            return True

        msg('Failed to close issue')
        return False

    def make_github_issue(self, redmine_json_fname, **kwargs):
        """
        Create a GitHub issue from JSON for a Redmine issue.

        - Format the GitHub description to include original
        - redmine info: author, link back to redmine ticket, etc
        - Add/Create Labels
        - Add/Create Milestones
        """
        if not os.path.isfile(redmine_json_fname):
            msgx('ERROR.  make_github_issue. file not found: %s'
                 % redmine_json_fname)

        include_comments = kwargs.get('include_comments', True)
        include_assignee = kwargs.get('include_assignee', True)
        include_attachments = kwargs.get('include_attachments', True)

        json_str = open(redmine_json_fname, 'rU').read()
        rd = json.loads(json_str)       # The redmine issue as a python dict

        # msg(json.dumps(rd, indent=4))
        msg('Attempt to create issue: [#%s][%s]' %
            (rd.get('id'), rd.get('subject').encode('utf-8')))

        # (1) Format the github issue description
        #
        #
        template = self.jinja_env.get_template('description.md')

        author_name = rd.get('author', {}).get('name', None)
        author_github_username = self.format_name_for_github(author_name)
        attachments = []

        if include_attachments:
            attachments = rd.get('attachments')

        affected_version = None

        redmine_category = None
        cat_fld = rd.get('category', None)
        if cat_fld is not None:
            redmine_category = cat_fld.get('name', None)
            if redmine_category is not None:
                redmine_category = redmine_category.lower().replace(' ', '_')

        desc_dict = {'description': translate_for_github(rd.get('description', 'no description')),
                     'redmine_link': self.format_redmine_issue_link(rd.get('id')),
                     'redmine_issue_num': rd.get('id'),
                     'start_date': rd.get('start_date', None),
                     'created_on': rd.get('created_on', None),
                     'affected_version': affected_version,
                     'category': redmine_category,
                     'author_name': author_name,
                     'author_github_username': author_github_username,
                     'redmine_assignee': self.get_redmine_assignee_name(rd),
                     'attachments': attachments}

        description_info = template.render(desc_dict)
        description_info = \
            '**This issue has been migrated from Redmine.**\n\n' + \
            description_info

        #
        # (2) Create the dictionary for the GitHub issue--for the github API
        #
        # self.label_helper.clear_labels(151)
        github_issue_dict = {'title': rd.get('subject'),
                             'body': description_info}

        if self.use_import_api is True:
            if 'created_on' in rd and rd['created_on'] is not None:
                github_issue_dict['created_at'] = rd['created_on']
            if 'closed_on' in rd and rd['closed_on'] is not None:
                github_issue_dict['closed_at'] = rd['closed_on']
            if 'updated_at' in rd and rd['updated_on'] is not None:
                github_issue_dict['updated_at'] = rd['updated_on']
            if 'status' in rd and rd['status'] is not None and \
                    'name' in rd['status'] and \
                    rd['status']['name'] is not None:
                if rd['status']['name'] == 'In Progress' or \
                        rd['status']['name'] == 'Open' or \
                        rd['status']['name'] == 'In Testing' or \
                        rd['status']['name'] == 'Waiting for upstream':
                    github_issue_dict['closed'] = False
                else:
                    github_issue_dict['closed'] = True

        # milestone_number = self.milestone_manager.get_create_milestone(rd)
        # if milestone_number:
        #     github_issue_dict['milestone'] = milestone_number

        if include_assignee:
            assignee = self.get_assignee(rd)
            if assignee:
                github_issue_dict['assignee'] = assignee

        msg(github_issue_dict)

        if include_comments:
            journals = rd.get('journals', None)

        #
        # (3) Create the issue on github
        #
        if self.use_import_api is True:
            issue_obj = \
                self.get_github_golden_conn().issues.create(
                    github_issue_dict, journals, attachments)
        else:
            issue_obj = \
                self.get_github_conn().issues.create(github_issue_dict)

        msgt('Github issue created: %s' % issue_obj.number)
        msg('issue id: %s' % issue_obj.id)
        msg('issue url: %s' % issue_obj.html_url)

        # Map the redmine labels to the github labels
        label_names = self.label_helper.get_label_names_based_on_map(rd)
        self.label_helper.add_labels_to_issue(issue_obj.id, label_names)

        # Map the new github Issue number to the redmine issue number
        #
        # redmine2github_id_map.update({ rd.get('id', 'unknown') :
        # issue_obj.number })

        # print( redmine2github_id_map)

        #
        # (4) Add the redmine comments (journals) as github comments
        #
        if journals and self.use_import_api is not True:
            self.add_comments_for_issue(issue_obj.number, journals,
                                        attachments)

        #
        #   (5) Should this issue be closed?
        #
        if self.is_redmine_issue_closed(rd) and \
                self.use_import_api is not True:
            self.close_github_issue(issue_obj.number)
        elif self.is_redmine_issue_closed(rd) and self.use_import_api:
            self.close_gitgub_issue_using_api(issue_obj.id)
        return issue_obj.id

    def is_redmine_issue_closed(self, redmine_issue_dict):
        """
        "status": {
            "id": 5,
            "name": "Completed"
        },
        """
        if not type(redmine_issue_dict) == dict:
            return False

        status_info = redmine_issue_dict.get('status', None)
        if not status_info:
            return False

        if 'name' in status_info and \
                status_info.get('name', None) in self.ISSUE_STATE_CLOSED:
            return True

        return False

    def map_property_ids(self, prop, name, value):
        res = value
        if name == 'category_id' and value in self.redmine_category_map:
            res = self.redmine_category_map[value]
        elif name == 'priority_id' and value in self.redmine_priority_map:
            res = self.redmine_priority_map[value]
        elif name == 'status_id' and value in self.redmine_status_map:
            res = self.redmine_status_map[value]
        elif name == 'fixed_version_id' and value in self.redmine_version_map:
            res = self.redmine_version_map[value]
        elif name == 'assigned_to_id' and value in self.redmine_user_map:
            res = self.redmine_user_map[value]
        elif name == 'tracker_id' and value in self.redmine_tracker_map:
            res = self.redmine_tracker_map[value]
        return res

    def map_property_names(self, name):
        if name in self.redmine_cf_map:
            return self.redmine_cf_map[name]
        return name

    def process_journals(self, journals, attachments):
        if journals is None:
            msg('no journals')
            return

        comments = []
        comment_template = self.jinja_env.get_template('comment.md')

        for j in journals:
            notes = j.get('notes', None)
            if not notes:
                notes = ''

            author_name = j.get('user', {}).get('name', None)
            author_github_username = self.format_name_for_github(author_name)
            comment_attachments = []
            comment_details = []

            # Find attachments that were added with this comment
            for d in j.get('details'):
                if d.get('property') == 'attachment':
                    attachment = \
                        next((x for x in attachments
                              if str(x.get('id')) == d.get('name')), None)

                    if attachment is not None:
                        comment_attachments.append(attachment)

                detail = {}
                prop = d.get('property')
                name = d.get('name')
                old_value = d.get('old_value')
                new_value = d.get('new_value')
                if prop == 'cf':
                    name = self.map_property_names(name)
                if prop == 'relation':
                    if new_value:
                        new_value = '#' + new_value
                    if old_value:
                        old_value = '#' + old_value
                if old_value is not None and new_value is not None:
                    detail['old_value'] = \
                        self.map_property_ids(prop, name, old_value)
                    detail['new_value'] = \
                        'to ' + self.map_property_ids(prop, name, new_value)
                    action = 'was changed from '
                    if detail['old_value'] is None or \
                            detail['old_value'] == '':
                        action = 'was changed '
                elif old_value is None and new_value is not None:
                    detail['new_value'] = \
                        'as ' + self.map_property_ids(prop, name, new_value)
                    action = 'was configured '
                elif old_value is not None and new_value is None:
                    detail['old_value'] = \
                        self.map_property_ids(prop, name, old_value)
                    action = 'removed '

                detail['name'] = name
                detail['action'] = action
                comment_details.append(detail)

            note_dict = {'description': translate_for_github(notes),
                         'note_date': j.get('created_on', None),
                         'author_name': author_name,
                         'author_github_username': author_github_username,
                         'attachments': comment_attachments,
                         'details': comment_details}
            comment_info = comment_template.render(note_dict)

            comment_data = {}
            if 'note_date' in note_dict and \
                    note_dict['note_date'] is not None:
                comment_data['created_at'] = note_dict['note_date']
            comment_data['body'] = comment_info
            comments.append(comment_data)

        return comments

    def add_comments_for_issue(self, issue_num, journals, attachments):
        """
        Add comments
        """
        comments = self.process_journals(journals, attachments)

        for comm in comments:
            comment_obj = None
            try:
                comment_obj = \
                    self.get_comments_service().create(
                        issue_num, comm['body'])
                msgt('sleep 1 second....')
                time.sleep(1)
            except requests.exceptions.HTTPError as e:
                msgt('Error creating comment: %s' % e.message)
                continue

            if comment_obj:
                dashes()
                msg('comment created')

                msg('comment id: %s' % comment_obj.id)
                msg('api issue_url: %s' % comment_obj.issue_url)
                msg('api comment url: %s' % comment_obj.url)
                msg('html_url: %s' % comment_obj.html_url)
                # msg(dir(comment_obj))


if __name__ == '__main__':
    issue_filename = '/Users/rmp553/Documents/iqss-git/redmine2github/' \
                     'working_files/redmine_issues/2014-0702/04156.json'
    gm = GithubIssueMaker()
    for x in range(100, 170):
        gm.close_github_issue(x)
    # gm.make_github_issue(issue_filename, {})

    sys.exit(0)
