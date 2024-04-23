#!/bin/bash
source /software/treeoflife/miniconda3/etc/profile.d/conda.sh
conda activate we_jira
/nfs/treeoflife-01/teams/tola/users/we3/source/generate_ena_biosampleids/check_jira_issues.py
