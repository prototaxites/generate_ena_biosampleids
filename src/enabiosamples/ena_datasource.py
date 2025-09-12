#!/usr/bin/env python

import uuid
import datetime
import tempfile
import xml.etree.ElementTree as ElementTree
from typing import Dict, List, Tuple
import requests
from requests.auth import HTTPBasicAuth


class EnaDataSource:
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

    update_xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<SUBMISSION xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation=\
"ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.submission.xsd">
<CONTACTS></CONTACTS>
<ACTIONS>
<ACTION>
<MODIFY/>
</ACTION>
</ACTIONS>
</SUBMISSION>"""

    def __init__(self, config: Dict, debug: True):
        self.get_uri = config["uri"]

        if config["set_uri"]:
            self.set_uri = config["set_uri"]
        else:
            self.set_uri = config["uri"]

        self.user = config["user"]
        self.password = config["password"]
        self.contact_name = config["contact_name"]
        self.contact_email = config["contact_email"]
        self.log_file = (
            f"ena_datasource_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        self.debug = debug

    def log(self, message):
        file_obj = open(self.log_file, "a")
        file_obj.write(f"{message}\n")
        file_obj.close()

    def post_request(self, command: str, files) -> requests.Response:
        response = requests.post(
            self.set_uri + command,
            files=files,
            auth=HTTPBasicAuth(self.user, self.password),
        )
        if response.status_code != 200:
            raise Exception(f"""Cannot connect to ENA (status code '{str(response.status_code)}').
                            Details: {response.text}""")

        return response

    def get_request(self, command: str) -> requests.Response:
        response = requests.get(
            self.get_uri + command, auth=HTTPBasicAuth(self.user, self.password)
        )

        if response.status_code != 200:
            raise Exception(
                f"Cannot connect to ENA (status code '{str(response.status_code)}')'"
            )

        return response

    def get_xml_checklist(
        self, checklist_id: str
    ) -> Dict[str, Tuple[str, str, object]]:
        output = self.get_request(f"/ena/browser/api/xml/{checklist_id}")
        return self._convert_checklist_xml_to_dict(output.text)

    def get_biosample_data_biosampleid(self, biosample_id: str):
        output = self.get_request(f"/ena/browser/api/xml/{biosample_id}")
        samples = self._convert_xml_to_list_of_sample_dict(output.text)

        # Only returning one sample for biosample
        return samples[0]

    def generate_ena_ids_for_samples(
        self, manifest_id: str, samples: Dict[str, Dict]
    ) -> Tuple[str, Dict[str, Dict]]:
        bundle_xml_file, sample_count = self._build_bundle_sample_xml(samples)

        with open(bundle_xml_file, "r") as bxf:
            bundle_xml_file_contents = bxf.read()

            element = ElementTree.XML(bundle_xml_file_contents)
            ElementTree.indent(element)
            bundle_xml_file_contents = ElementTree.tostring(element, encoding="unicode")

        if sample_count == 0:
            raise Exception("All samples have unknown taxonomy ID")

        submission_xml_file = self._build_submission_xml(
            manifest_id, self.contact_name, self.contact_email
        )

        xml_files = [
            ("SAMPLE", open(bundle_xml_file, "rb")),
            ("SUBMISSION", open(submission_xml_file, "rb")),
        ]

        response = self.post_request("/ena/submit/drop-box/submit/", xml_files)

        try:
            assigned_samples = self._assign_ena_ids(samples, response.text)

        except Exception as ex:
            raise self.log(f"Error returned from ENA service: {ex}")

        if not assigned_samples:
            errors = {}
            error_count = 0
            for error_node in ElementTree.fromstring(response.text).findall(
                "./MESSAGES/ERROR"
            ):
                if error_node is not None:
                    error_count += 1
                    errors[str(error_count)] = error_node.text

            return False, errors
        else:
            return True, assigned_samples

    def _convert_checklist_xml_to_dict(
        self, checklist_xml: str
    ) -> Dict[str, Tuple[str, str, object]]:
        fields = {}

        root = ElementTree.fromstring(checklist_xml)
        for field_group_node in root.findall("./CHECKLIST/DESCRIPTOR/FIELD_GROUP"):
            for field_node in field_group_node.findall("./FIELD"):
                label, mandatory_status = None, None

                label_node = field_node.find("./LABEL")

                if label_node is not None:
                    label = label_node.text

                mandatory_node = field_node.find("./MANDATORY")

                if mandatory_node is not None:
                    mandatory_status = mandatory_node.text

                regex_node = field_node.find("./FIELD_TYPE/TEXT_FIELD/REGEX_VALUE")
                if regex_node is not None:
                    regex_str = regex_node.text
                    fields[label] = [mandatory_status, "restricted text", regex_str]
                    continue

                text_choice_node = field_node.find("./FIELD_TYPE/TEXT_CHOICE_FIELD")

                if text_choice_node is not None:
                    text_options = []
                    for text_option_node in text_choice_node.findall(
                        "./TEXT_VALUE/VALUE"
                    ):
                        text_options.append(text_option_node.text)

                    fields[label] = [mandatory_status, "text choice", text_options]
                    continue

                taxon_node = field_node.find("./FIELD_TYPE/TEXT_FIELD/TAXON_FIELD")

                if taxon_node is not None:
                    regex_str = regex_node.text
                    fields[label] = [mandatory_status, "valid taxonomy", ""]
                    continue

                fields[label] = [mandatory_status, "free text", ""]

        return fields

    def _convert_xml_to_list_of_sample_dict(
        self, response_xml: str
    ) -> List[Dict[str, List[str]]]:
        samples = []
        # Convert sample xml to dictionary
        # SAMPLE_ATTRIBUTE use TAG as key, tuple (VALUE, UNITS)
        # Additional entries TITLE, SAMPLE_NAME, TAXONID

        root = ElementTree.fromstring(response_xml)
        for xml_sample_node in root.findall("./SAMPLE"):
            sample = {}

            title, taxon_id, scientific_name = None, None, None

            title_node = xml_sample_node.find("./TITLE")
            taxon_id_node = xml_sample_node.find("./SAMPLE_NAME/TAXON_ID")
            scientific_name_node = xml_sample_node.find("./SAMPLE_NAME/SCIENTIFIC_NAME")

            if title_node is not None:
                title = title_node.text

            if taxon_id_node is not None:
                taxon_id = taxon_id_node.text

            if scientific_name_node is not None:
                scientific_name = scientific_name_node.text

            sample["title"] = [title, None]
            sample["taxon_id"] = [taxon_id, None]
            sample["scientific_name"] = [scientific_name, None]

            for xml_sample_attr_node in xml_sample_node.findall(
                "./SAMPLE_ATTRIBUTES/SAMPLE_ATTRIBUTE"
            ):
                tag, val, units = None, None, None

                tag_node = xml_sample_attr_node.find("./TAG")
                val_node = xml_sample_attr_node.find("./VALUE")
                units_node = xml_sample_attr_node.find("./UNITS")

                if tag_node is not None:
                    tag = tag_node.text

                if val_node is not None:
                    val = val_node.text

                if units_node is not None:
                    units = units_node.text

                sample[tag] = [val, units]

            samples.append(sample)

        return samples

    def _build_bundle_sample_xml(
        self, samples: Dict[str, Dict[str, List[str]]]
    ) -> Tuple[str, int]:
        """build structure and save to file bundle_file_subfix.xml"""

        manifest_id = uuid.uuid4()

        dir_ = tempfile.TemporaryDirectory()

        filename = f"{dir_.name}bundle_{str(manifest_id)}.xml"

        with open(filename, "w") as sample_xml_file:
            sample_xml_file.write(self.sample_xml_template)

        sample_count = self._update_bundle_sample_xml(samples, filename)

        return filename, sample_count

    def _update_bundle_sample_xml(
        self, samples: Dict[str, Dict[str, List[str]]], bundlefile: str
    ) -> int:
        """update the sample with submission alias adding a new sample"""

        tree = ElementTree.parse(bundlefile)
        root = tree.getroot()
        sample_count = 0
        for title, sample in samples.items():
            sample_count += 1
            sample_alias = ElementTree.SubElement(root, "SAMPLE")

            # Title is format <unique id>-<project name>-<specimen_type>
            t_arr = title.split("-")

            sample_alias.set(
                "alias", f"{t_arr[0]}-{t_arr[1]}-{t_arr[2]}-{t_arr[3]}-{t_arr[4]}"
            )
            sample_alias.set("center_name", "SangerInstitute")

            title_block = ElementTree.SubElement(sample_alias, "TITLE")
            title_block.text = title
            sample_name = ElementTree.SubElement(sample_alias, "SAMPLE_NAME")
            taxon_id = ElementTree.SubElement(sample_name, "TAXON_ID")
            taxon_id.text = str(sample["taxon_id"][0])
            scientific_name = ElementTree.SubElement(sample_name, "SCIENTIFIC_NAME")
            scientific_name.text = str(sample["scientific_name"][0])
            sample_attributes = ElementTree.SubElement(
                sample_alias, "SAMPLE_ATTRIBUTES"
            )

            for key, val in sample.items():
                if key in ["title", "taxon_id", "scientific_name"]:
                    continue

                sample_attribute = ElementTree.SubElement(
                    sample_attributes, "SAMPLE_ATTRIBUTE"
                )
                tag = ElementTree.SubElement(sample_attribute, "TAG")
                tag.text = key
                value = ElementTree.SubElement(sample_attribute, "VALUE")
                value.text = str(val[0])
                # add ena units where necessary
                if val[1]:
                    unit = ElementTree.SubElement(sample_attribute, "UNITS")
                    unit.text = val[1]

        if self.debug:
            ElementTree.dump(tree)
        tree.write(open(bundlefile, "w"), encoding="unicode")
        return sample_count

    def _build_submission_xml(
        self, manifest_id: str, contact_name: str, contact_email: str
    ) -> str:
        dir_ = tempfile.TemporaryDirectory()

        submissionfile = f"{dir_.name}submission_{str(manifest_id)}.xml"

        with open(submissionfile, "w") as submission_xml_file:
            submission_xml_file.write(self.submission_xml_template)

        # build submission XML
        tree = ElementTree.parse(submissionfile)
        root = tree.getroot()

        # set SRA contacts
        contacts = root.find("CONTACTS")

        # set copo sra contacts
        copo_contact = ElementTree.SubElement(contacts, "CONTACT")
        copo_contact.set("name", contact_name)
        copo_contact.set("inform_on_error", contact_email)
        copo_contact.set("inform_on_status", contact_email)
        if self.debug:
            ElementTree.dump(tree)

        tree.write(open(submissionfile, "w"), encoding="unicode")

        return submissionfile

    def _assign_ena_ids(
        self, samples: str, xml: str
    ) -> Dict[str, Dict[str, List[str]]]:
        try:
            tree = ElementTree.fromstring(xml)
        except ElementTree.ParseError:
            return False

        success_status = tree.get("success")
        if success_status == "false":
            return False
        else:
            return self._assign_biosample_accessions(samples, xml)

    def _assign_biosample_accessions(
        self, samples: Dict[str, Dict[str, List[str]]], xml: str
    ) -> Dict[str, Dict[str, List[str]]]:
        # Parse response to return generated biosample ids

        assigned_samples = {}

        tree = ElementTree.fromstring(xml)
        submission_accession = tree.find("SUBMISSION").get("accession")
        for child in tree.iter():
            if child.tag == "SAMPLE":
                sample_id = child.get("alias")
                sra_accession = child.get("accession")
                biosample_accession = child.find("EXT_ID").get("accession")

                for key, sample_dict in samples.items():
                    if sample_id in key:
                        sample_dict["sra_accession"] = [sra_accession, None]
                        sample_dict["biosample_accession"] = [biosample_accession, None]
                        sample_dict["submission_accession"] = [
                            submission_accession,
                            None,
                        ]

                        assigned_samples[key] = sample_dict

        return assigned_samples

    def get_existing_sample_data(self, accession: str):
        output = self.get_request(f"/ena/submit/drop-box/samples/{accession}")

        return output.text

    def get_accession_from_biosampleid(self, biosampleid: str):
        output = self.get_request(f"/biosamples/samples/{biosampleid}")

        return output.text

    def update_existing_xml(self, manifest_id: str, updated_xml):
        dir_ = tempfile.TemporaryDirectory()

        updatedxmlfile = f"{dir_.name}submission_{str(manifest_id)}.xml"

        with open(updatedxmlfile, "w") as updated_xml_file:
            updated_xml_file.write(updated_xml)

        updated_submission_xml_file = self._build_update_xml(
            manifest_id, self.contact_name, self.contact_email
        )

        xml_files = [
            ("SAMPLE", open(updatedxmlfile, "rb")),
            ("SUBMISSION", open(updated_submission_xml_file, "rb")),
        ]

        response = self.post_request("/ena/submit/drop-box/submit/", xml_files)

        return updatedxmlfile, updated_submission_xml_file, response.text

    def _build_update_xml(
        self, manifest_id: str, contact_name: str, contact_email: str
    ) -> str:
        dir_ = tempfile.TemporaryDirectory()

        submissionfile = f"{dir_.name}submission_{str(manifest_id)}.xml"

        with open(submissionfile, "w") as submission_xml_file:
            submission_xml_file.write(self.update_xml_template)

        # build submission XML
        tree = ElementTree.parse(submissionfile)
        root = tree.getroot()

        # set SRA contacts
        contacts = root.find("CONTACTS")

        # set copo sra contacts
        copo_contact = ElementTree.SubElement(contacts, "CONTACT")
        copo_contact.set("name", contact_name)
        copo_contact.set("inform_on_error", contact_email)
        copo_contact.set("inform_on_status", contact_email)
        if self.debug:
            ElementTree.dump(tree)

        tree.write(open(submissionfile, "w"), encoding="unicode")

        return submissionfile
