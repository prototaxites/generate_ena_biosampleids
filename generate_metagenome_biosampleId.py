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

            if parent_key == "sex":
                child_dict["host sex"] = parent_val
            elif parent_key == "lifestage":
                child_dict["host life stage"] = parent_val
            elif parent_key == "organism":
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

    # Import primary metagenomes summary
    df_primary = pd.read_csv(options.data)

    primary_samples_dict = {}

    tol_validation_passed = True
    binned_validation_passed = True
    mag_validation_passed = True


    # Loop through each primary metagenome.
    for index, primary_metagenome in df_primary.iterrows():

        # Get Host data from ENA
        host_sample_dict = ena_datasource.get_biosample_data_biosampleid(primary_metagenome["host_biospecimen"])

        primary_uuid = f"{uuid.uuid4()}-{project_name}-metagenome"
        host_scientific_name = primary_metagenome["host_taxname"]
        host_taxid = primary_metagenome["host_taxid"]

        # Create primary metagenome sample
        primary_dict = {
            'title': [primary_uuid, None],
            'taxon_id': [primary_metagenome["metagenome_taxid"], None],
            'scientific_name': [primary_metagenome["metagenome_taxname"], None],
            'host scientific name': [host_scientific_name, None],
            'host taxid': [host_taxid, None],
            'broad-scale environmental context': [primary_metagenome["broad-scale environmental context"], None],
            'local environmental context': [primary_metagenome["local environmental context"], None],
            'environmental medium': [primary_metagenome["environmental medium"], None],
            'ENA-CHECKLIST': ['ERC000013', None],
            'tolid': [primary_metagenome["metagenome_tolid"], None],
            'sample derived from': [primary_metagenome["host_biospecimen"], None]
        }

        log("Check primary checklist")
        # Download tol checklist
        tol_field_dict = ena_datasource.get_xml_checklist('ERC000013')

        log("Copy primary checklist items")
        # Copy extra host fields, extract data from fields required to populate tol checklist
        primary_sample_dict = copy_checklist_items(tol_field_dict, host_sample_dict, primary_dict)

        primary_samples_dict[primary_uuid] = primary_sample_dict

        # Validate
        log("Validate primary checklist items")
        tol_validation_passed = validate_samples_with_checklist(tol_field_dict, primary_samples_dict)


    # for key, primary_dict in primary_submission_dict.items():
        binned_samples_dict = {}
        mag_samples_dict = {}
        binned_mag_samples_dict = {}

        if primary_metagenome["binned_path"]:
            # binned metagenome checklist
            log("Load binned checklist")
            bm_field_dict = ena_datasource.get_xml_checklist('ERC000050')

            #   extract data from fields required to populate binned metagenome checklist
            # Import binned metagenome
            binned_mag_samples_dict = {}

            df_binned = pd.read_csv(primary_metagenome["binned_path"])

            for index, row in df_binned.iterrows():

                # Create binned sample
                binned_dict = {
                    'title': [f"{uuid.uuid4()}-{project_name}-{row['bin_name']}", None],
                    'taxon_id': [row["taxon_id"], None],
                    'scientific_name': [row["taxon"], None],
                    'host scientific name': [host_scientific_name, None],
                    'host taxid': [host_taxid, None],
                    'tolid': [row["tol_id"], None],
                    'ENA-CHECKLIST': ['ERC000050', None],
                    'number of standard tRNAs extracted': [row["number of standard tRNAs extracted"], None],
                    'assembly software': [row["assembly software"], None],
                    '16S recovered': [row["16S recovered"], None],
                    '16S recovery software': [row["16S recovery software"], None],
                    'tRNA extraction software': [row["tRNA extraction software"], None],
                    'completeness score': [row["completeness score"], "%"],
                    'completeness software': [row["completeness software"], None],
                    'contamination score': [row["contamination score"], "%"],
                    'binning software': [row["binning software"], None],
                    'MAG coverage software': [row["MAG coverage software"], None],
                    'binning parameters': [row["binning parameters"], None],
                    'taxonomic identity marker': [row["taxonomic identity marker"], None],
                    'taxonomic classification': [row["taxonomic classification"], None],
                    'assembly quality': [row["assembly quality"], None],       
                    'sequencing method': [row["sequencing method"], None],  
                    'investigation type': [row["investigation type"], None],  
                    'isolation_source': [row["isolation_source"], None], 
                    'broad-scale environmental context': [row["broad-scale environmental context"], None],  
                    'local environmental context': [row["local environmental context"], None],  
                    'environmental medium': [row["environmental medium"], None],  
                    'metagenomic source': [row["metagenomic source"], None]  
                }

                if binned_dict['assembly quality'][0] == "Many fragments with little to no review of assembly other than reporting of standard assembly statistics.":
                    binned_dict['assembly quality'][0] = "Many fragments with little to no review of assembly other than reporting of standard assembly statistics"

                if binned_dict['completeness score'][0] == 100.0:
                    binned_dict['completeness score'][0] = 100

                # Copy extra host fields, extract data from fields required to populate tol checklist
                log(f"Copy checklist items for binned {index}")
                binned_sample_dict = copy_checklist_items(bm_field_dict, primary_dict, binned_dict)

                binned_samples_dict[binned_sample_dict['title'][0]] = binned_sample_dict
                binned_mag_samples_dict[binned_sample_dict['title'][0]] = binned_sample_dict
            
            # Validate
            log(f"Validate binned checklist items")
            binned_validation_passed = validate_samples_with_checklist(bm_field_dict, binned_samples_dict)

        if primary_metagenome["mag_path"]:
            # MAGs checklist
            mag_field_dict = ena_datasource.get_xml_checklist('ERC000047')

        # extract data from fields required to populate MAG biosample checklist
            df_mag = pd.read_csv(primary_metagenome["mag_path"])

            for index, row in df_mag.iterrows():

                # Create MAG sample
                mag_dict = {
                    'title': [f"{uuid.uuid4()}-{project_name}-{row['bin_name']}", None],
                    'taxon_id': [row["taxon_id"], None],
                    'scientific_name': [row["taxon"], None],
                    'host scientific name': [host_scientific_name, None],
                    'host taxid': [host_taxid, None],
                    'tolid': [row["tol_id"], None],
                    'ENA-CHECKLIST': ['ERC000047', None],
                    'number of standard tRNAs extracted': [row["number of standard tRNAs extracted"], None],
                    'assembly software': [row["assembly software"], None],
                    '16S recovered': [row["16S recovered"], None],
                    '16S recovery software': [row["16S recovery software"], None],
                    'tRNA extraction software': [row["tRNA extraction software"], None],
                    'completeness score': [row["completeness score"], "%"],
                    'completeness software': [row["completeness software"], None],
                    'contamination score': [row["contamination score"], "%"],
                    'binning software': [row["binning software"], None],
                    'MAG coverage software': [row["MAG coverage software"], None],
                    'binning parameters': [row["binning parameters"], None],
                    'taxonomic identity marker': [row["taxonomic identity marker"], None],
                    'taxonomic classification': [row["taxonomic classification"], None],
                    'assembly quality': [row["assembly quality"], None],
                    'sequencing method': [row["sequencing method"], None],
                    'investigation type': [row["investigation type"], None],
                    'isolation_source': [row["isolation_source"], None],
                    'broad-scale environmental context': [row["broad-scale environmental context"], None],
                    'local environmental context': [row["local environmental context"], None],
                    'environmental medium': [row["environmental medium"], None],
                    'metagenomic source': [row["metagenomic source"], None]
                }

                if mag_dict['assembly quality'][0] == "Many fragments with little to no review of assembly other than reporting of standard assembly statistics.":
                    mag_dict['assembly quality'][0] = "Many fragments with little to no review of assembly other than reporting of standard assembly statistics"

                if mag_dict['completeness score'][0] == 100.0:
                    mag_dict['completeness score'][0] = 100

                # Copy extra host fields, extract data from fields required to populate tol checklist
                log(f"Copy checklist items for MAG {index}")
                mag_sample_dict = copy_checklist_items(mag_field_dict, primary_dict, mag_dict)

                mag_samples_dict[mag_sample_dict['title'][0]] = mag_sample_dict
                binned_mag_samples_dict[mag_sample_dict['title'][0]] = mag_sample_dict
            
            # Validate 
            log(f"Validate mag checklist items")
            mag_validation_passed = validate_samples_with_checklist(mag_field_dict, mag_samples_dict)

        # # Check validation - if fails do not submit:
        if tol_validation_passed and binned_validation_passed and mag_validation_passed:

            # binned_mag_samples_dict = dict(list(binned_samples_dict.items()) + list(mag_samples_dict.items()))

            # Submit manifest of all primary metagenomes.
            ## Submit to Enadatasource,
            ## 1. converts to xml, (creates sample id - UUID)
            ## 2. submits to ena
            ## 3. intepret response xml, appends biosampleid to sample dict
            log(f"Generate ENA IDs for primary samples")
            primary_submission_success, primary_submission_dict = ena_datasource.generate_ena_ids_for_samples(uuid.uuid4(), primary_samples_dict)

            # binned_mag_submission_dict - read errors from this rather than 
            if not primary_submission_success:
                log(f"ENA generation failed for primary")
                # print(primary_submission_dict)
                for val in primary_submission_dict.values():
                    log(val)
            else:
                log(f"ENA generation succeeded for primary")
                primary_metagenome_dict = primary_submission_dict[primary_uuid]

                # Amend binned and mags with returned biosample IDs.
                if primary_metagenome_dict["biosample_accession"][0]:


                    updated_binned_mag_samples_dict = {}
                    for key, val in binned_mag_samples_dict.items():
                        # print(val['taxon_id'][0])
                        # if val['taxon_id'][0] == 2066855:
                        val["sample derived from"] = [primary_metagenome_dict["biosample_accession"][0],None]
                        updated_binned_mag_samples_dict[key] = val

                    # Submit manifest of all binned and MAGs.
                    log(f"Generate ENA IDs for binned/MAG samples")
                    binned_mag_submission_success, binned_mag_submission_dict = ena_datasource.generate_ena_ids_for_samples(uuid.uuid4(), updated_binned_mag_samples_dict)

                    # binned_mag_submission_dict - read errors from this rather than 
                    if not binned_mag_submission_success:
                        log(f"ENA generation failed for binned/mag")
                        # print(binned_mag_submission_dict)
                        for val in binned_mag_submission_dict.values():
                            log(val)
                    else:
                        log(f"ENA generation succeeded for binned/mag")
                        # Build output summarising generated biosample IDs (primary, binned, MAGs).

                        cols=['Type', 'ToLID', 'Biosample Accession']
                        samples=[["primary", primary_metagenome_dict["tolid"][0], primary_metagenome_dict["biosample_accession"][0]]]

                        # output_df = pd.DataFrame(columns=['Type', 'ToLID', 'Biosample Accession'])
                        # output_row = pd.DataFrame({'Type': "primary", 'ToLID': primary_metagenome_dict["tolid"][0],'Biosample Accession': primary_metagenome_dict["biosample_accession"][0]})
                        # output_df = pd.concat([output_df, output_row], axis=0, ignore_index=True)

                        for key, val in binned_mag_submission_dict.items():
                            samples.append([val['title'][0].split("-")[6], val["tolid"][0], val["biosample_accession"][0]])
                            # output_row = pd.DataFrame({'Type': val['title'][0].split("-")[6], 'ToLID': val["tolid"][0],'Biosample Accession': val["biosample_accession"][0]})
                            # output_df = pd.concat([output_df, output_row], axis=0, ignore_index=True)

                        output_df = pd.DataFrame(samples, columns = cols)
                        log(f"Output biosamples")
                        output_df.to_csv(output_file_name,index=False)

                        # method to convert submission response xml into biosample summary list.
                        # print(primary_dict["tolid"][0])
                        # primary_biosampleid = primary_dict["biosample_accession"][0]
                        # print(primary_biosampleid)

                        # for key, dict in binned_mag_submission_dict.items():
                            # print(dict["tolid"][0])
                            # print(dict["biosample_accession"][0])
                
                else:
                    log("Biosample accession not returned for primary metagenome")

#     # tol_sdk - tests - copy and update test methods from manifest_utils, xml_utils

# Run update submission
#     set host_taxid - to pull
#         - dont pass organism name
#         -- sample symbiont of. 




if __name__ == "__main__":
    main()
