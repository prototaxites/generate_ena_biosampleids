#!/usr/bin/env python

import pandas as pd
import uuid
import optparse
import datetime
import re
import json
import tempfile
import uuid
import xml.etree.ElementTree as ElementTree
from typing import Dict, List, Tuple
import requests
from requests.auth import HTTPBasicAuth
from ena_datasource import EnaDataSource


def log(message):
    # curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_obj = open(log_file, 'a')
    # file_obj.write(f"({curr_time}) {message}\n")
    file_obj.write(f"{message}\n")
    file_obj.close()

def ena_checklist_to_dict(checklist_path):

    with open(checklist_path) as f:
        xml_content = f.read()
        # print(xml_content)

def copy_checklist_items(field_dict, parent_dict, child_dict):

    for parent_key, parent_val in parent_dict.items():
        if parent_key not in child_dict.keys():

            # if parent_key == "sex":
            #     child_dict["host sex"] = parent_val
            # elif parent_key == "lifestage":
            #     child_dict["host life stage"] = parent_val
            if parent_key == "organism":
                continue
                # Needed to prevent rendering errors on the website.
            else:
                child_dict[parent_key] = parent_val

    mandatory_missing = []
    recommended_missing = []
    optional_missing = []

    for field_key, field_val in field_dict.items():
        if field_key not in child_dict.keys():
            if field_val[0] in ["mandatory"]:

                # Is valid alternative to collected by"
                if field_key == "collected_by":
                    continue
                      
                # Will be added later
                if field_key == "sample derived from":
                    continue

                mandatory_missing.append(field_key)

            elif field_val in ["recommended"]:
                recommended_missing.append(field_key)

            elif field_val in ["optional"]:
                optional_missing.append(field_key)

    if mandatory_missing:
        log("Missing mandatory fields:")
        for field in mandatory_missing:
            log(field)
        log("")

    return child_dict

def validate_samples_with_checklist(field_dict, samples_dict):

    invalid_text = []
    invalid_option = []
    
    validation_status = True

    for sample_key, sample_val in samples_dict.items():
        value_dict = sample_val
        invalid_text = []
        invalid_option = []
        for value_key, value_val in value_dict.items():

            if value_key in field_dict.keys():

                if field_dict[value_key][1] == 'restricted text':
                    pattern = re.compile(field_dict[value_key][2])

                    if not pattern.match(str(value_val[0])):
                        invalid_text.append(f"   {value_key} is set to invalid '{value_val[0]}'. Required regex is: {field_dict[value_key][2]}")

                elif field_dict[value_key][1] == 'text choice':
                    if value_val[0] not in field_dict[value_key][2]:
                        invalid_option.append(f"   {value_key} is set to invalid option '{value_val[0]}'. Valid options are: {field_dict[value_key][2]}")


        if invalid_text or invalid_option:
            log("================")
            log(f"{sample_key} - {sample_val['taxon_id'][0]} - {sample_val['tolid'][0]}")
            for field in invalid_text:
                log(field)
            for field in invalid_option:
                log(field)
            log("================")

        if invalid_text:
            validation_status = False

        if invalid_option:
            validation_status = False
    
    return validation_status

def main():

    parser = optparse.OptionParser()
    parser.add_option('-a', '--api_credentials', 
                  dest="api", 
                  default="",
                  )
    parser.add_option('-p', '--project_name', 
                  dest="proj", 
                  default="",
                  ) 
    parser.add_option('-d', '--data_csv', 
                dest="data", 
                default="default.csv",
                )      
    parser.add_option('-o', '--output_file', 
            dest="output", 
            default="",
            )           

    (options, args) = parser.parse_args()

    global project_name
    project_name = options.proj

    output_file_name = options.output

    global log_file 
    log_file = f'cobiont_{project_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    with open(options.api) as json_file:
        enviromment_params = json.load(json_file)

    # TODO: Check credentials in valid format.

    # Check connection to local tol-sdk
    ena_datasource = EnaDataSource(enviromment_params['credentials'])

    # Import cobiont csv
    df_cobionts = pd.read_csv(options.data)

    primary_samples_dict = {}

    tol_validation_passed = True

    # Currently provided inputs: host_biospecimen,cobiont_taxname,cobiont_taxid

    for index, cobiont in df_cobionts.iterrows():

        # Get Host data from ENA
        host_sample_dict = ena_datasource.get_biosample_data_biosampleid(cobiont["host_biospecimen"])

        cobiont_uuid = f"{uuid.uuid4()}-{project_name}-cobiont"
        # print("sex")
        # print(host_sample_dict["sex"])
        # print("lifestage")
        # print(host_sample_dict["lifestage"])

    #         sex = "NOT_COLLECTED"
    # lifestage = "NOT_COLLECTED"
    # symbiont = "SYMBIONT"
        # Create cobiont sample dictionary
        cobiont_dict = {
            'title': [cobiont_uuid, None],
            'taxon_id': [cobiont["cobiont_taxid"], None],
            'scientific_name': [cobiont["cobiont_taxname"], None],
            'host scientific name': host_sample_dict["scientific_name"],
            'host taxid': host_sample_dict["taxon_id"],
            'ENA-CHECKLIST': ['ERC000053', None],
            'tolid': [cobiont["cobiont_tolid"], None],
            'symbiont': ['Y', None],
            'sample derived from': [cobiont["host_biospecimen"], None]
        }

        log("Check checklist")
        # Download tol checklist
        tol_field_dict = ena_datasource.get_xml_checklist('ERC000053')

        log("Copy checklist items")
        # Copy extra host fields, extract data from fields required to populate tol checklist
        primary_sample_dict = copy_checklist_items(tol_field_dict, host_sample_dict, cobiont_dict)

        # Add to sample list
        primary_samples_dict[cobiont_uuid] = primary_sample_dict

    # Validate
    log("Validate checklist items")
    tol_validation_passed = validate_samples_with_checklist(tol_field_dict, primary_samples_dict)

        # Check validation - if fails do not submit:
    if tol_validation_passed:

        # Submit manifest of all primary metagenomes.
        ## Submit to Enadatasource,
        ## 1. converts to xml, (creates sample id - UUID)
        ## 2. submits to ena
        ## 3. intepret response xml, appends biosampleid to sample dict
        log(f"Generate ENA IDs for primary samples")
        primary_submission_success, primary_submission_dict = ena_datasource.generate_ena_ids_for_samples(uuid.uuid4(), primary_samples_dict)

        if not primary_submission_success:
            log(f"ENA generation failed.")
            for val in primary_submission_dict.values():
                log(val)
        else:
            log(f"ENA generation succeeded")
            cobiont_biosample_dict = primary_submission_dict[cobiont_uuid]

            samples = []

            for cobiont_biosample_dict in primary_submission_dict.values():
                samples.append(["cobiont", cobiont_biosample_dict["tolid"][0], cobiont_biosample_dict["biosample_accession"][0]])
            
            
            cols=['Type', 'ToLID', 'Biosample Accession']
            
            output_df = pd.DataFrame(samples, columns = cols)
            log(f"Output biosamples")
            output_df.to_csv(output_file_name,index=False)


if __name__ == "__main__":
    main()
