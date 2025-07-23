import netrc
import sys
from jira import JIRA

class tol_jira_auth:

    @property
    def auth_jira(self):
        return self._auth_jira

    @property
    def jira_path(self):
        return self._jira_path

    def __init__(self, username: str = "", password: str = ""):
        """Class to authenticate access to JIRA and return JIRA object.
        Attempts three different methods depending on parameters provided."""

        self._jira_path = "jira.sanger.ac.uk"

        # Attempt method, based on provided parameters
        if not (username or password):
            self.authorise_netrc_token()
        elif username and password:
            self.authorise_login(username, password)
        elif password:
            self.authorise_token(password)
        else:
            print(f"No suitable credentials provided for access.")
            sys.exit(1)

    def authorise_login(self, username: str, password: str) -> JIRA:
        """Attempt JIRA authentication using username and password."""

        print(f"""Attempting to authenticate access to {self.jira_path} using
              provided username and password.""")
        return JIRA({'server': "https://" + self.jira_path}, basic_auth=(username, password))

    def authorise_token(self, password: str) -> JIRA:
        """Attempt JIRA authentication using provided personal access token."""

        print(f"Attempting to authenticate access to {self.jira_path} using provided token.")
        return JIRA({'server': "https://" + self.jira_path}, token_auth=password)

    def authorise_netrc_token(self) -> JIRA:
        """Attempt JIRA authentication using personal access token stored in users .netrc."""
        my_netrc = netrc.netrc()

        print(f"""Attempting to read Personal Access Token for specified host
              ({self.jira_path}) from .netrc.""")
        jira_password = my_netrc.authenticators(self.jira_path)[2]

        print(f"Attempting to authenticate access to {self.jira_path} using .netrc token.")
        return JIRA({'server': "https://" + self.jira_path}, token_auth=jira_password)
