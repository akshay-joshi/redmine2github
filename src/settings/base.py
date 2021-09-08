import settings.local as config

#
#   Redmine API information
#   https://redmine.hmdc.harvard.edu
#
REDMINE_SERVER = config.REDMINE_SERVER
REDMINE_PROJECT_ID = config.REDMINE_PROJECT_ID
REDMINE_API_KEY = config.REDMINE_API_KEY


#
#   GitHub API information
#   https://github.com/blog/1509-personal-api-tokens
#
GITHUB_SERVER = config.GITHUB_SERVER
GITHUB_LOGIN = config.GITHUB_LOGIN
GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN = \
    config.GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN

GITHUB_TARGET_REPOSITORY = config.GITHUB_TARGET_REPOSITORY
GITHUB_TARGET_USERNAME = config.GITHUB_TARGET_USERNAME

USE_IMPORT_API = config.USE_IMPORT_API

#
#  Working files directory
#
WORKING_FILES_DIRECTORY = config.WORKING_FILES_DIRECTORY
REDMINE_ISSUES_DIRECTORY = config.REDMINE_ISSUES_DIRECTORY

# JSON file mapping { redmine issue # : github issue # }
REDMINE_TO_GITHUB_MAP_FILE = config.REDMINE_TO_GITHUB_MAP_FILE

# (optional) csv file mapping Redmine users to github users.
# Manually created.  Doesn't check for name collisions
#   example, see settings/sample_user_map.csv
USER_MAP_FILE = config.USER_MAP_FILE

# (optional) csv file mapping Redmine status, tracker, priority, and
# custom fields names to github labels.
# Manually created.  Doesn't check for name collisions
#   example, see settings/sample_label_map.csv
LABEL_MAP_FILE = config.LABEL_MAP_FILE

# (optional) csv file mapping Redmine "target version" to GitHub milestones.
# Manually created.  Doesn't check for name collisions
#   example, see settings/sample_milestone_map.csv
MILESTONE_MAP_FILE = config.MILESTONE_MAP_FILE

REDMINE_CATEGORY_MAP = config.REDMINE_CATEGORY_MAP
REDMINE_STATUS_MAP = config.REDMINE_STATUS_MAP
REDMINE_USER_MAP = config.REDMINE_USER_MAP
REDMINE_VERSION_MAP = config.REDMINE_VERSION_MAP
REDMINE_PRIORITY_MAP = config.REDMINE_PRIORITY_MAP
REDMINE_CF_MAP = config.REDMINE_CF_MAP
REDMINE_TRACKER_MAP = config.REDMINE_TRACKER_MAP
REDMINE_ISSUES_STATUS = config.REDMINE_ISSUES_STATUS


def get_gethub_issue_url(issue_id=None):
    """
    Used by the "redmine_issue_updater" to add links back to the original
    redmine tickets
    """
    issue_url = 'https://github.com/%s/%s/issues' % \
                (GITHUB_TARGET_USERNAME, GITHUB_TARGET_REPOSITORY)

    if issue_id:
        return '%s/%s' % (issue_url, issue_id)
    return issue_url


def get_github_auth():
    return dict(login_or_token=GITHUB_LOGIN,
                password=GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN)


def get_github_golden_auth():
    return dict(login=GITHUB_LOGIN,
                password=GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN,
                repo=GITHUB_TARGET_REPOSITORY, user=GITHUB_TARGET_USERNAME)
