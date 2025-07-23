#!/usr/bin/env python

from tol_jira_auth import ToLJiraAuth
import yaml
from yaml.loader import SafeLoader
import xml.etree.ElementTree as ElementTree
from typing import Dict, List, Tuple
import requests
from requests.auth import HTTPBasicAuth
from ena_datasource import EnaDataSource

def get_yaml_attachment(issue):
    for attachment in issue.fields.attachment:
        if attachment.filename.endswith('.yaml'):
            yaml_data = yaml.load(attachment.get(), Loader=SafeLoader)
            return yaml_data

def get_jira_biosample(issue):
    yaml_data = get_yaml_attachment(issue)
    return yaml_data["biosample"]

def get_jira_taxid(issue):
    yaml_data = get_yaml_attachment(issue)
    return yaml_data["taxid"]

def get_jira_species(issue):
    yaml_data = get_yaml_attachment(issue)
    return yaml_data["species"]

def update_yaml(jira, issue, new_taxid, new_biosampleid):

    for attachment in issue.fields.attachment:
        if attachment.filename.endswith('.yaml'):
            yaml_data = yaml.load(attachment.get(), Loader=SafeLoader)

            yaml_data["biosample"] = new_biosampleid
            yaml_data["taxid"] = new_taxid

            with open(attachment.filename, 'w') as w:
                yaml.dump(yaml_data, w, default_flow_style=False)


            jira.delete_attachment(attachment.id)

            with open(attachment.filename, 'rb') as r:
                jira.add_attachment(issue=issue, attachment=r)

def main():
    # Find all open jira tickets with taxid and without biosampleid

    tja = ToLJiraAuth()
    jql_request = f"project = DS AND 'Species Name' ~ 'Wolbachia'"
    # query to look for taxid_pending label

    results = tja.auth_jira.search_issues(jql_request)

    fail_summary = {}
    successes = {}

    for result in results:
        fails = []
        issue = tja.auth_jira.issue(result)

        # if not get_jira_biosample(issue):
        # Check ENA for if taxid exists for sample
        species_name = get_jira_species(issue)
        species_name = species_name.replace(" ","%20")
        response = requests.get(f"https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/{species_name}")

        result = response.json()
        result_dict = result[0]
        # Run biosample generation
        taxid = result_dict["taxId"]
        print(taxid)

        # If ticket yaml has taxid and no biosample, submit to create one.
        # if not jira_biosample_id:
        #     if jira_taxid:

        update_yaml(tja.auth_jira, issue, "test_biosample", taxid)
        # remove taxid_pending label

if __name__ == "__main__":
    main()
