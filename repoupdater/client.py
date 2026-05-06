import os
import sys

from github import Github


ERROR_MSG = """
Error: missing environment variable ORG_TOKEN. You need a Personal
Access Token (Classic), with admin:org and all repo permissions.

https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token
"""


def github_client():
    token = os.environ.get("ORG_TOKEN")
    if not token:
        sys.exit(ERROR_MSG)
    return Github(token)


def get_org(org):
    return github_client().get_organization(org)
