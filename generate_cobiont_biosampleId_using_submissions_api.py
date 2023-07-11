#!/usr/bin/env python

import requests
import optparse
import pandas as pd
import datetime
import json

# headers = {
#        'accept': 'application/json',
#        #'api-key' : 'kdyne83bcpaxec7b39dxmew86napj3e4'
#        'api-key' : 'kro93bxm49f7qa651nvytlj3sxbgmr8r'
# }
headers = {}
project_name = ""
log_file = ""
replace_policy = ""
api_url = ""
#api_url = "https://submissions-staging.tol.sanger.ac.uk/api/v1/"
# api_url = "https://submissions.tol.sanger.ac.uk/api/v1/"

def log(message):
    curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_obj = open(log_file, 'a')
    file_obj.write(f"({curr_time}) {message}\n")
    file_obj.close()

def api_request(method, request_url, json_data = ""):

    url = api_url + request_url

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers)
        else:
            raise Exception("No method specified")
    except requests.exceptions as err:
        print(err)
        success = False

    if response.status_code == 200:
        success = True
    else:
        success = False
        log(response)
    
    if success:
        return success, response.json()
    else:

        return success, None

def api_request_get(request_url):
    return api_request("GET", request_url)

def api_request_post(request_url, json_data):
    return api_request("POST", request_url, json_data)

def api_request_patch(request_url):
    return api_request("PATCH", request_url)

def get_sample_details_from_biospecimenID(host_biospecimen_id):
    success, response = api_request_get(f'specimens/biospecimenId/{host_biospecimen_id}/samples')

    # Check
    log(response)

    return response.get('specimenId')

def build_cobiont_samples(samples_json):
    success, response = api_request_post("manifests",samples_json)

    log(response)

    # check manifestid exists
    if success:
        return success, response.get('manifestId')
    else:
        return success, None

def fill_details_from_manifest_id(manifest_id):
    success, response = api_request_patch(f'manifests/{manifest_id}/fill')

    log(response)

    if success:
        return success, response
    else:
        return success, None

def validate_sample_from_manifest_id(manifest_id):
    success, response = api_request_get(f'manifests/{manifest_id}/validate')

    #Check if error
    log(response)

    for response_validation in response.get("validations")[0].get("results"):
        if response_validation.get("severity") == "ERROR":
            success = False

    if success:
        return success, response
    else:
        return success, None

def generate_biosamples_from_manifest_id(manifest_id):
    success, response = api_request_patch(f'manifests/{manifest_id}/generate')

    #Generate BioSampleID summary

    return success, response

def build_samples_as_JSON(project_name, cobionts_data, specimen_dict):
    samples = []

    for index, row in cobionts_data.iterrows():
        specimen_dict[row["host_biospecimen"]]
        samples.append(build_sample_as_JSON(row["cobiont_taxid"], row["cobiont_taxname"], specimen_dict[row["host_biospecimen"]], index+1))

    samples_json = {
                "projectName": project_name,
                "samples": samples
            }

    return samples_json

def build_sample_as_JSON(cobiont_taxon_id, cobiont_species_name, specimen_id, row):
    sex = "NOT_COLLECTED"
    lifestage = "NOT_COLLECTED"
    symbiont = "SYMBIONT"

    if replace_policy == "TRFM_PTB":
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "TISSUE_REMOVED_FOR_BARCODING": "N",
                        "PLATE_ID_FOR_BARCODING": "NOT_APPLICABLE",
                        "TUBE_OR_WELL_ID_FOR_BARCODING": "NOT_APPLICABLE",
                        "BARCODE_PLATE_PRESERVATIVE": "NOT_APPLICABLE",
                        "row": row}
    elif replace_policy == "TRFM_PT":
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "TISSUE_REMOVED_FOR_BARCODING": "N",
                        "PLATE_ID_FOR_BARCODING": "NOT_APPLICABLE",
                        "TUBE_OR_WELL_ID_FOR_BARCODING": "NOT_APPLICABLE",
                        "row": row}
    elif replace_policy == "LIN_O":
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "ORDER_OR_GROUP": "NOT_SPECIFIED",
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "row": row}
    elif replace_policy == "LIN_FO":
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "FAMILY": "NOT_SPECIFIED",
                        "ORDER_OR_GROUP": "NOT_SPECIFIED",
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "row": row}
    elif replace_policy == "LIN_FOG":
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "FAMILY": "NOT_SPECIFIED",
                        "GENUS": "NOT_SPECIFIED",
                        "ORDER_OR_GROUP": "NOT_SPECIFIED",
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "row": row}
    else:
        sample_json = { "ORGANISM_PART": "**OTHER_SOMATIC_ANIMAL_TISSUE**",               
                        "SCIENTIFIC_NAME": cobiont_species_name,
                        "SEX": sex,
                        "SPECIMEN_ID": specimen_id,
                        "TAXON_ID": cobiont_taxon_id,
                        "LIFESTAGE": lifestage,
                        "SYMBIONT": symbiont,
                        "row": row}

    return sample_json


# def not_main():

#     global project_name
#     project_name = "test"

#     global log_file 
#     log_file = f'cobiont_{project_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

#     validation_success, validation_response = validate_sample_from_manifest_id("1395")
#     for response_validation in validation_response.get("validations")[0].get("results"):
#         print(response_validation.get("message"))

#    # print(validation_response.get("validations")[0].get("results")[0].get("message"))

def main():

    parser = optparse.OptionParser()
    parser.add_option('-a', '--apikey', 
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
    parser.add_option('-r', '--replace', 
            dest="replace", 
            default="",
            ) 
    parser.add_option('-o', '--output_file', 
            dest="output", 
            default="",
            )           

    (options, args) = parser.parse_args()

    global project_name
    project_name = options.proj

    output_file_name = options.output
    global replace_policy
    replace_policy = options.replace

    global log_file 
    log_file = f'cobiont_{project_name}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    with open(options.api) as json_file:
        enviromment_params = json.load(json_file)

    global api_url
    api_url = enviromment_params["submission_credentials"]["api_url"]

    api_key = enviromment_params["submission_credentials"]["api_key"]

    global headers
    headers = {
       'accept': 'application/json',
       'api-key': api_key
    }

    df = pd.read_csv(options.data)

    biospecimenids = df["host_biospecimen"].unique()

    start_build = True
    # Build dictionary of species ids
    specimen_dict = {}
    for bsid in biospecimenids:
        specimen_id = get_sample_details_from_biospecimenID(bsid)
        specimen_dict[bsid] = specimen_id

        if specimen_id:
            log(f'{bsid} - {specimen_id}')
        else:
            log(f'{bsid} - no valid found' )
            start_build = False
            break

    if start_build:
        # Use details from host to build cobionts
        samples_json = build_samples_as_JSON(project_name, df, specimen_dict)
        log(samples_json)

        # Build cobionts
        build_success, manifest_id = build_cobiont_samples(samples_json)

        if build_success:

            #Use manifest id to fill to get JSON with extra fields.
            fill_success, fill_response = fill_details_from_manifest_id(manifest_id)

            log(fill_response)

            if fill_success:

                # Optionally validate the samples. Ignore warnings about TaxonID not being in TOLID database, TOLIDs will not be created for cobiont samples.
                validation_success, validation_response = validate_sample_from_manifest_id(manifest_id)

                if validation_success:
                    # Generate the biosamples.
                    generation_success, generation_response = generate_biosamples_from_manifest_id(manifest_id)
                    log(generation_response)

                    df_output = pd.DataFrame(columns=['cobiont_taxname','cobiont_taxid','host_biospecimen','biosample_accession'])

                    for i in generation_response.get("samples"):
                        row = {'cobiont_taxname':i.get('SCIENTIFIC_NAME'), 'cobiont_taxid': i.get('TAXON_ID'), 'host_biospecimen': i.get('sampleSymbiontOf'), 'biosample_accession': i.get('biosampleAccession')}
                        df_row = pd.DataFrame([row])
                        df_output = pd.concat([df_output, df_row], axis=0, ignore_index=True)

                    df_output.to_csv(output_file_name, index=False)
                else:
                    log("Validation unsuccessful")
            else:
                log("Fill unsuccessful")         
        else:
            log("Build unsuccessful")
    else:
        log("Required host unavailable")

if __name__ == '__main__':
    main()

# For eahc need to establish success state, otherwise do not progress to next step

