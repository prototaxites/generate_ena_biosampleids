#!/usr/bin/env python

import optparse
import datetime
import json
import uuid
import tempfile
import pandas as pd
import xml.etree.ElementTree as ElementTree
from ena_datasource import EnaDataSource
# Update

# Load from sample accession.


def log(message):
    # curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_obj = open(log_file, 'a')
    # file_obj.write(f"({curr_time}) {message}\n")
    file_obj.write(f"{message}\n")
    file_obj.close()

def add_element(parent_element, tag_text, value_text):
        sample_attribute = ElementTree.SubElement(parent_element, 'SAMPLE_ATTRIBUTE')
        tag = ElementTree.SubElement(sample_attribute, 'TAG')
        tag.text = tag_text
        value = ElementTree.SubElement(sample_attribute, 'VALUE')
        value.text = value_text

def main():

    parser = optparse.OptionParser()
    parser.add_option('-a', '--api_credentials', 
                  dest="api", 
                  default="",
                  )
    parser.add_option('-d', '--data_csv', 
                dest="data", 
                default="default.csv",
                )          

    (options, args) = parser.parse_args()

    # global project_name
    # project_name = options.proj

    # # output_file_name = options.output
    # global replace_policy
    # replace_policy = options.replace

    global log_file 
    log_file = f'cobiont_update_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    with open(options.api) as json_file:
        enviromment_params = json.load(json_file)

    # TODO: Check credentials in valid format.

    # Check connection to local tol-sdk
    ena_datasource = EnaDataSource(enviromment_params['credentials'])
 
    df_samples = pd.read_csv(options.data)

    results_data = {}

    for index, sample in df_samples.iterrows():

        biosampleid = sample['biosampleid']
        host_species_name = sample['host scientific name']
        host_taxid = sample['host taxid']
        host_biosampleid = sample['host biosampleid']
        broadscale_environmental_context = sample['broadscale_environmental_context']
        local_environmental_context = sample['local_environmental_context']
        environmental_medium = sample['environmental_medium']
  

        # Get accession from biosample id.
        # intial_sample_data = ena_datasource.get_accession_from_biosampleid(biosampleid)
        # print(biosample_id_data)


        intial_sample_data = ena_datasource.get_existing_sample_data(biosampleid)
        # biosample_data = ena_datasource.get_existing_sample_data(biosampleid)

        # dir_ = tempfile.TemporaryDirectory()

        # initdataxml = f'{dir_.name}init_data.xml'

        # with open(initdataxml, 'w') as init_data_xml:
        #     init_data_xml.write(biosample_data)

        # bio_tree = ElementTree.parse(initdataxml)
        # bio_root = bio_tree.getroot()
        # secondary_id_element = bio_root.find('./SAMPLE/IDENTIFIERS/SECONDARY_ID')
        # print(f"{biosampleid} - {secondary_id_element.text}")

        # # # # Get sample data from accession
        # # ers_sample_data = ena_datasource.get_existing_sample_data('ERS15992257')

        # # print(intial_sample_data)
        # # print(ers_sample_data)

        dir_ = tempfile.TemporaryDirectory()

        initdataxml = f'{dir_.name}init_data.xml'

        with open(initdataxml, 'w') as init_data_xml:
            init_data_xml.write(intial_sample_data)

        # print("XML INITIAL FILE")
        # print(intial_sample_data)

        tree = ElementTree.parse(initdataxml)
        root = tree.getroot()
        # ElementTree.SubElement(root, 'SAMPLE')


        sample_attributes = root.find('./SAMPLE/SAMPLE_ATTRIBUTES')

        host_scientific_name_included = False
        host_taxid_included = False
        sample_derived_from_included = False
        is_primary = False
        broadscale_included = False
        local_env_included = False
        env_med_included = False

        for attribute in sample_attributes:
            tag_node = attribute.find('./TAG')
            val_node = attribute.find('./VALUE')

            # Remove organism tag that has host species name set.
            if tag_node.text == "organism" and val_node.text == host_species_name:
                sample_attributes.remove(attribute)

            # If host scientific name tag exists, set it to new scientific name and mark it as included.
            if tag_node.text == "host scientific name": 
                # Set host scientific name
                # attribute.set("host scientific name",host_species_name)
                val_node.text = host_species_name
                host_scientific_name_included = True

            # If host taxid tag exists, set it to new taxid and mark it as included.
            if tag_node.text == "host taxid":
                # Set host taxid
                # attribute.set("host taxid",host_taxid)
                val_node.text = str(host_taxid)
                host_taxid_included = True

            if tag_node.text == "sample derived from":
                sample_derived_from_included = True

            if tag_node.text == "broad-scale environmental context":
                broadscale_included = True

            if tag_node.text == "local environmental context":
                local_env_included = True

            if tag_node.text == "environmental medium":
                env_med_included = True

            if tag_node.text == "ENA-CHECKLIST":

                if val_node.text == "ERC000053":
                    # Update checklist
                    val_node.text = "ERC000013"
                
                # Add sample derived from
                if val_node.text == "ERC000013":
                    is_primary = True

        # If not host_scientific_name not already a attribute, add it.
        if not host_scientific_name_included:
            add_element(sample_attributes,"host scientific name",host_species_name)

        # If not host_taxid not already a attribute, add it.
        if not host_taxid_included:
            add_element(sample_attributes,"host taxid",str(host_taxid))

        if is_primary: 
            if not sample_derived_from_included:
                add_element(sample_attributes,"sample derived from",host_biosampleid)
            if not broadscale_included:
                add_element(sample_attributes,"broad-scale environmental context",broadscale_environmental_context)
            if not local_env_included:
                add_element(sample_attributes,"local environmental context",local_environmental_context)
            if not env_med_included:
                add_element(sample_attributes,"environmental medium",environmental_medium)

        ElementTree.indent(tree)
        ElementTree.dump(tree)
        tree.write(open(initdataxml, 'w'),
                encoding='unicode')

        with open(initdataxml) as modifiedxml:
            modified_xml = modifiedxml.read()
            
        # print("XML MODIFIED FILE")
        # print(modified_xml)
        # print(biosampleid)
        try:
            updatedxmlfile_path, updated_submission_xml_file_path, update_response = ena_datasource.update_existing_xml(uuid.uuid4(),modified_xml)
            results_data[biosampleid] = "success"
        except Exception as ex:
            results_data[biosampleid] = f"failed: {ex}"
    

        # print("XML SAMPLE FILE")
        # with open(updatedxmlfile_path) as updatedxmlfile:
        #     print(updatedxmlfile.read())
        # print("XML SUBMISSION FILE")
        # with open(updated_submission_xml_file_path) as updated_submission_xml_file:
        #     print(updated_submission_xml_file.read())

        print("UPDATE_RESPONSE")
        print(update_response)
        # results_data[biosampleid] = update_response
        # print(biosampleid)
        updated_sample_data = ena_datasource.get_existing_sample_data(biosampleid)
        # print(updated_sample_data)

        # Output before and after for comparison
        with open('intial_sample_data.xml', 'w') as init_file:
            init_file.write(intial_sample_data)

        with open('updated_sample_data.xml', 'w') as updat_file:
            updat_file.write(updated_sample_data)
    
    
    for key, value in results_data.items():
        print(key)
        print(value)


if __name__ == "__main__":
    main()
