from os.path import abspath, dirname, join
import sys

PROJECT_ROOT = dirname(dirname(dirname(abspath(__file__))))
sys.path.append(PROJECT_ROOT)

#
#   Redmine API information
#
REDMINE_SERVER = 'https://redmine.postgresql.org'
# Found in project url: http://redmine.my-org.edu/projects/PROJ_ID
REDMINE_PROJECT_ID = 'PROJ_ID'

# See http://www.redmine.org/projects/redmine/wiki/Rest_api#Authentication
# "You can find your API key on your account page..."
REDMINE_API_KEY = '<Redmine Key>'

GITHUB_SERVER = 'https://api.github.com'
GITHUB_LOGIN = '<github login>'
GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN = '<github token>'

GITHUB_TARGET_REPOSITORY = '<github repo>'
GITHUB_TARGET_USERNAME = '<github login>'

USE_IMPORT_API = True

WORKING_FILES_DIRECTORY = join(PROJECT_ROOT, 'working_files')
REDMINE_ISSUES_DIRECTORY = join(WORKING_FILES_DIRECTORY, 'redmine_issues')
SETTINGS_DIRECTORY = join(PROJECT_ROOT, 'src', 'settings')

# JSON file mapping { redmine issue # : github issue # }
REDMINE_TO_GITHUB_MAP_FILE = join(WORKING_FILES_DIRECTORY,
                                  'redmine2github_issue_map.json')

# (optional) csv file mapping Redmine users to github users.
# Manually created.  Doesn't check for name collisions
# example, see settings/sample_user_map.csv
USER_MAP_FILE = join(WORKING_FILES_DIRECTORY, 'redmine2github_user_map.csv')

# (optional) csv file mapping Redmine status, tracker, priority, and custom
# fields names to github labels.
# Manually created.  Doesn't check for name collisions
#   example, see settings/sample_label_map.csv
LABEL_MAP_FILE = join(WORKING_FILES_DIRECTORY, 'redmine2github_label_map.csv')

# (optional) csv file mapping Redmine "target version" to GitHub milestones.
# Manually created.  Doesn't check for name collisions
#   example, see settings/sample_milestone_map.csv
MILESTONE_MAP_FILE = join(WORKING_FILES_DIRECTORY,
                          'redmine2github_milestone_map.csv')

REDMINE_CATEGORY_MAP = join(SETTINGS_DIRECTORY, 'issue_categories_map.csv')
REDMINE_STATUS_MAP = join(SETTINGS_DIRECTORY, 'issue_statuses_map.csv')
REDMINE_USER_MAP = join(SETTINGS_DIRECTORY, 'users_map.csv')
REDMINE_VERSION_MAP = join(SETTINGS_DIRECTORY, 'versions_map.csv')
REDMINE_PRIORITY_MAP = join(SETTINGS_DIRECTORY, 'priority_map.csv')
REDMINE_CF_MAP = join(SETTINGS_DIRECTORY, 'cf_map.csv')
REDMINE_TRACKER_MAP = join(SETTINGS_DIRECTORY, 'tracker_map.csv')
REDMINE_ISSUES_STATUS = '*'  # values 'open', 'closed', '*'


def get_github_auth():
    return dict(login_or_token=GITHUB_LOGIN,
                password=GITHUB_PASSWORD_OR_PERSONAL_ACCESS_TOKEN)
