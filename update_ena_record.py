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

        biosampleid = sample['biosample_accession']
        cobiont_tolid = sample['cobiont_tolid']
            #         'common name': ["", None],
            # 'sex': ["NOT_COLLECTED", None],
            # 'lifestage': ["NOT_COLLECTED", None],

        # Get existing sample data
        intial_sample_data = ena_datasource.get_existing_sample_data(biosampleid)

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

        for attribute in sample_attributes:
            tag_node = attribute.find('./TAG')
            val_node = attribute.find('./VALUE')

            if tag_node.text == "tolid":
                val_node.text = cobiont_tolid

            if tag_node.text == "common name":
                val_node.text = ""

            if tag_node.text == "sex":
                val_node.text = "NOT_COLLECTED"

            if tag_node.text == "lifestage":
                val_node.text = "NOT_COLLECTED"


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

        # print("UPDATE_RESPONSE")
        # print(update_response)
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
