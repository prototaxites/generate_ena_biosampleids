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

class EnaDataSource():

    def __init__(self, config: Dict):

        super().__init__(config,
                         expected=['uri', 'user', 'password', 'contact_name', 'contact_email'])

    def post_request(self, command: str, files) -> requests.Response:
        response = requests.post(self.uri + command,
                                 files=files,
                                 auth=HTTPBasicAuth(self.user, self.password))
        if (response.status_code != 200):
            raise Exception(f"Cannot connect to ENA (status code '{str(response.status_code)}')'")

        return response

    def get_request(self, command: str) -> requests.Response:
        response = requests.get(self.uri + command,
                                auth=HTTPBasicAuth(self.user, self.password))

        if (response.status_code != 200):
            raise Exception(f"Cannot connect to ENA (status code '{str(response.status_code)}')'")

        return response

    def get_xml_checklist(self, checklist_id: str) -> Dict[str, Tuple[str, str, object]]:
        output = self.get_request(f'/ena/browser/api/xml/{checklist_id}')

        checklist_dict = convert_checklist_xml_to_dict(output.text)

        return checklist_dict

    def get_biosample_data_biosampleid(self, biosample_id: str):
        output = self.get_request(f'/ena/browser/api/xml/{biosample_id}')

        samples = convert_xml_to_list_of_sample_dict(output.text)

        # Only returning one sample for biosample
        return samples[0]

    def generate_ena_ids_for_samples(self, manifest_id: str,
                                     samples: Dict[str, Dict]) -> Tuple[str, Dict[str, Dict]]:

        bundle_xml_file, sample_count = build_bundle_sample_xml(samples)

        with open(bundle_xml_file, 'r') as bxf:
            bundle_xml_file_contents = bxf.read()

            element = ElementTree.XML(bundle_xml_file_contents)
            ElementTree.indent(element)
            bundle_xml_file_contents = ElementTree.tostring(element, encoding='unicode')

        if sample_count == 0:
            raise Exception('All samples have unknown taxonomy ID')

        submission_xml_file = build_submission_xml(manifest_id, self.contact_name,
                                                      self.contact_email)

        xml_files = [('SAMPLE', open(bundle_xml_file, 'rb')),
                     ('SUBMISSION', open(submission_xml_file, 'rb'))]

        response = self.post_request('/ena/submit/drop-box/submit/', xml_files)

        try:
            assigned_samples = assign_ena_ids(samples, response.text)

        except Exception as ex:
            raise log(f"Error returned from ENA service: {ex}")

        if not assigned_samples:
            errors = {}
            error_count = 0
            for error_node in ElementTree.fromstring(response.text).findall('./MESSAGES/ERROR'):
                if error_node is not None:
                    error_count += 1
                    errors[str(error_count)] = error_node.text

            return False, errors
        else:
            return True, assigned_samples


sample_xml_template = """<?xml version="1.0" ?>
<SAMPLE_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation=\
"ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.sample.xsd">
</SAMPLE_SET>"""


submission_xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<SUBMISSION xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation=\
"ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.submission.xsd">
<CONTACTS></CONTACTS>
<ACTIONS>
<ACTION>
<ADD/>
</ACTION>
<ACTION>
<RELEASE/>
</ACTION>
</ACTIONS>
</SUBMISSION>"""


def convert_checklist_xml_to_dict(checklist_xml: str) -> Dict[str, Tuple[str, str, object]]:
    # key label, val [mandatory_status, ]

    fields = {}

    root = ElementTree.fromstring(checklist_xml)
    for field_group_node in root.findall('./CHECKLIST/DESCRIPTOR/FIELD_GROUP'):
        for field_node in field_group_node.findall('./FIELD'):

            label, mandatory_status = None, None

            label_node = field_node.find('./LABEL')

            if label_node is not None:
                label = label_node.text

            mandatory_node = field_node.find('./MANDATORY')

            if mandatory_node is not None:
                mandatory_status = mandatory_node.text

            regex_node = field_node.find('./FIELD_TYPE/TEXT_FIELD/REGEX_VALUE')
            if regex_node is not None:
                regex_str = regex_node.text
                fields[label] = [mandatory_status, 'restricted text', regex_str]
                continue

            text_choice_node = field_node.find('./FIELD_TYPE/TEXT_CHOICE_FIELD')

            if text_choice_node is not None:
                text_options = []
                for text_option_node in text_choice_node.findall('./TEXT_VALUE/VALUE'):
                    text_options.append(text_option_node.text)

                fields[label] = [mandatory_status, 'text choice', text_options]
                continue

            taxon_node = field_node.find('./FIELD_TYPE/TEXT_FIELD/TAXON_FIELD')

            if taxon_node is not None:
                regex_str = regex_node.text
                fields[label] = [mandatory_status, 'valid taxonomy', '']
                continue

            fields[label] = [mandatory_status, 'free text', '']

    return fields


def convert_xml_to_list_of_sample_dict(response_xml: str) -> List[Dict[str, List[str]]]:
    samples = []
    # Convert sample xml to dictionary
    # SAMPLE_ATTRIBUTE use TAG as key, tuple (VALUE, UNITS)
    # Additional entries TITLE, SAMPLE_NAME, TAXONID

    root = ElementTree.fromstring(response_xml)
    for xml_sample_node in root.findall('./SAMPLE'):
        sample = {}

        title, taxon_id, scientific_name = None, None, None

        title_node = xml_sample_node.find('./TITLE')
        taxon_id_node = xml_sample_node.find('./SAMPLE_NAME/TAXON_ID')
        scientific_name_node = xml_sample_node.find('./SAMPLE_NAME/SCIENTIFIC_NAME')

        if title_node is not None:
            title = title_node.text

        if taxon_id_node is not None:
            taxon_id = taxon_id_node.text

        if scientific_name_node is not None:
            scientific_name = scientific_name_node.text

        sample['title'] = [title, None]
        sample['taxon_id'] = [taxon_id, None]
        sample['scientific_name'] = [scientific_name, None]

        for xml_sample_attr_node in \
                xml_sample_node.findall('./SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE'):
            tag, val, units = None, None, None

            tag_node = xml_sample_attr_node.find('./TAG')
            val_node = xml_sample_attr_node.find('./VALUE')
            units_node = xml_sample_attr_node.find('./UNITS')

            if tag_node is not None:
                tag = tag_node.text

            if val_node is not None:
                val = val_node.text

            if units_node is not None:
                units = units_node.text

            sample[tag] = [val, units]

        samples.append(sample)

    return samples


def build_bundle_sample_xml(samples: Dict[str, Dict[str, List[str]]]) -> Tuple[str, int]:
    """build structure and save to file bundle_file_subfix.xml"""

    manifest_id = uuid.uuid4()

    dir_ = tempfile.TemporaryDirectory()

    filename = f'{dir_.name}bundle_{str(manifest_id)}.xml'

    with open(filename, 'w') as sample_xml_file:
        sample_xml_file.write(sample_xml_template)

    sample_count = update_bundle_sample_xml(samples, filename)

    return filename, sample_count


def update_bundle_sample_xml(samples: Dict[str, Dict[str, List[str]]], bundlefile: str) -> int:
    """update the sample with submission alias adding a new sample"""

    # print('adding sample to bundle sample xml')
    tree = ElementTree.parse(bundlefile)
    root = tree.getroot()
    sample_count = 0
    for title, sample in samples.items():
        sample_count += 1
        sample_alias = ElementTree.SubElement(root, 'SAMPLE')

        # Title is format <unique id>-<project name>-<specimen_type>
        t_arr = title.split('-')

        sample_alias.set('alias',
                        f'{t_arr[0]}-{t_arr[1]}-{t_arr[2]}-{t_arr[3]}-{t_arr[4]}')
        sample_alias.set('center_name', 'SangerInstitute')

        title_block = ElementTree.SubElement(sample_alias, 'TITLE')
        title_block.text = title
        sample_name = ElementTree.SubElement(sample_alias, 'SAMPLE_NAME')
        taxon_id = ElementTree.SubElement(sample_name, 'TAXON_ID')
        taxon_id.text = str(sample['taxon_id'][0])
        scientific_name = ElementTree.SubElement(sample_name, 'SCIENTIFIC_NAME')
        scientific_name.text = str(sample['scientific_name'][0])
        sample_attributes = ElementTree.SubElement(sample_alias, 'SAMPLE_ATTRIBUTES')

        for key, val in sample.items():

            if key in ['title', 'taxon_id', 'scientific_name']:
                continue

            sample_attribute = ElementTree.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
            tag = ElementTree.SubElement(sample_attribute, 'TAG')
            tag.text = key
            value = ElementTree.SubElement(sample_attribute, 'VALUE')
            value.text = str(val[0])
            # add ena units where necessary
            if val[1]:
                unit = ElementTree.SubElement(sample_attribute, 'UNITS')
                unit.text = val[1]

    ElementTree.dump(tree)
    tree.write(open(bundlefile, 'w'),
            encoding='unicode')
    return sample_count


def build_submission_xml(manifest_id: str, contact_name: str, contact_email: str) -> str:

    dir_ = tempfile.TemporaryDirectory()

    submissionfile = f'{dir_.name}submission_{str(manifest_id)}.xml'

    with open(submissionfile, 'w') as submission_xml_file:
        submission_xml_file.write(submission_xml_template)

    # build submission XML
    tree = ElementTree.parse(submissionfile)
    root = tree.getroot()

    # set SRA contacts
    contacts = root.find('CONTACTS')

    # set copo sra contacts
    copo_contact = ElementTree.SubElement(contacts, 'CONTACT')
    copo_contact.set('name', contact_name)
    copo_contact.set('inform_on_error', contact_email)
    copo_contact.set('inform_on_status', contact_email)
    ElementTree.dump(tree)

    tree.write(open(submissionfile, 'w'),
            encoding='unicode')

    return submissionfile


def assign_ena_ids(samples: str, xml: str) -> Dict[str, Dict[str, List[str]]]:

    try:
        tree = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return False

    success_status = tree.get('success')
    if success_status == 'false':
        return False
    else:
        return assign_biosample_accessions(samples, xml)


def assign_biosample_accessions(samples: Dict[str, Dict[str, List[str]]],
                                xml: str) -> Dict[str, Dict[str, List[str]]]:
    # Parse response to return generated biosample ids

    assigned_samples = {}

    tree = ElementTree.fromstring(xml)
    submission_accession = tree.find('SUBMISSION').get('accession')
    for child in tree.iter():
        if child.tag == 'SAMPLE':
            sample_id = child.get('alias')
            sra_accession = child.get('accession')
            biosample_accession = child.find('EXT_ID').get('accession')

            for key, sample_dict in samples.items():

                if sample_id in key:
                    sample_dict['sra_accession'] = [sra_accession, None]
                    sample_dict['biosample_accession'] = [biosample_accession, None]
                    sample_dict['submission_accession'] = [submission_accession, None]

                    assigned_samples[key] = sample_dict

    return assigned_samples

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

        # Create primary metagenome sample
        primary_dict = {
            'title': [primary_uuid, None],
            'taxon_id': [primary_metagenome["metagenome_taxid"], None],
            'host scientific name': [primary_metagenome["metagenome_taxname"], None],
            'broad-scale environmental context': [primary_metagenome["broad-scale environmental context"], None],
            'local environmental context': [primary_metagenome["local environmental context"], None],
            'environmental medium': [primary_metagenome["environmental medium"], None],
            'ENA-CHECKLIST': ['ERC000013', None],
            'tolid': [primary_metagenome["metagenome_tolid"], None]
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
