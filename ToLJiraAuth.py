# Required environment installs
#   pip install jira
#   pip install python-dotenv

from jira import JIRA
# from dotenv import load_dotenv
import netrc

class ToLJiraAuth:

    @property
    def auth_jira(self):
        return self._auth_jira

    @property
    def jira_path(self):
        return self._jira_path

    def __init__(self, username = "", password = ""):
        # Set up environment
        # load_dotenv()
        self._jira_path = "jira.sanger.ac.uk"
        
        # Attempt method, based on provided parameters
        if not (username or password):
            self.authorise_netrc_token()
        elif username and password:
            self.authorise_login(username, password)
        elif password:
            print("a")
            self.authorise_token(password)
        else:
            print(f"No suitable credentials provided for access.")
    
    def authorise_login(self, username, password):
        # Confirm authorised params
        try:
            self._auth_jira = JIRA({'server': "https://" + self.jira_path}, basic_auth=(username, password))
        except:
            print(f"Unable to authenticate access to {self.jira_path} using provided username and password.")

    def authorise_token(self, password):
        # Confirm authorised params
        try:
            self._auth_jira = JIRA({'server': "https://" + self.jira_path}, token_auth=(password))
        except:
            print(f"Unable to authenticate access to {self.jira_path} using provided token.")

    def authorise_netrc_token(self):
        my_netrc = netrc.netrc()

        # jira path used as hostname.
        try:
            jira_password = my_netrc.authenticators(self.jira_path)[2]
        except:
            print(f"Personal Access Token for specified host ({self.jira_path}) could not be read from .netrc.")

        # Confirm authorised params
        try:
            self._auth_jira = JIRA({'server': "https://" + self.jira_path}, token_auth=(jira_password))
        except:
            print(f"Unable to authenticate access to {self.jira_path} using .netrc token.")