#!/usr/bin/env python

import uuid
import datetime
import re
from typing import Dict, List, Tuple, Optional, Any
from ena_datasource import EnaDataSource


class HostAssocMetagenomeBiosampleGenerator:
    def __init__(
        self,
        ena_datasource: EnaDataSource,
        project_name: str,
        log_file: Optional[str] = None,
    ):
        self.ena_datasource = ena_datasource
        self.project_name = project_name
        self.log_file = (
            log_file
            or f"cobiont_{project_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

    def log(self, message: str) -> None:
        curr_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as file_obj:
            file_obj.write(f"({curr_time}) {message}\n")

    def copy_checklist_items(
        self,
        field_dict: Dict[str, Any],
        parent_dict: Dict[str, Any],
        child_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Copy checklist items from parent to child dictionary and validate mandatory fields.

        Args:
            field_dict: Dictionary containing field definitions from checklist
            parent_dict: Parent dictionary to copy from
            child_dict: Child dictionary to copy to

        Returns:
            Updated child dictionary with copied fields
        """
        for parent_key, parent_val in parent_dict.items():
            if parent_key not in child_dict:
                if parent_key == "sex":
                    child_val = parent_val.copy()
                    child_val[0] = child_val[0].lower()

                    if "hermaphrodite" in child_val[0]:
                        child_val[0] = "hermaphrodite"
                    elif "sexual morph" in child_val[0]:
                        child_val[0] = "other"

                    child_dict["host sex"] = child_val

                elif parent_key == "lifestage":
                    child_dict["host life stage"] = parent_val

                elif parent_key in [
                    "geographic location (latitude)",
                    "geographic location (longitude)",
                ]:
                    child_val = parent_val.copy()

                    try:
                        coordinate = float(child_val[0])
                        child_val[0] = f"{coordinate:.2f}"
                    except ValueError:
                        self.log(
                            f"Warning: Could not parse {parent_key} value '{child_val[0]}' as a number"
                        )

                    child_dict[parent_key] = child_val

                elif parent_key == "organism":
                    continue

                else:
                    child_dict[parent_key] = parent_val

        # Check for missing fields
        mandatory_missing = []
        recommended_missing = []
        optional_missing = []

        for field_key, field_val in field_dict.items():
            if field_key not in child_dict:
                requirement_level = field_val[0]

                if requirement_level == "mandatory":
                    if field_key in ["collected_by", "sample derived from"]:
                        continue
                    mandatory_missing.append(field_key)

                elif requirement_level == "recommended":
                    recommended_missing.append(field_key)
                elif requirement_level == "optional":
                    optional_missing.append(field_key)

        if mandatory_missing:
            self.log("Missing mandatory fields:")
            for field in mandatory_missing:
                self.log(f"  {field}")

        return child_dict

    def validate_samples_with_checklist(
        self, field_dict: Dict[str, Any], samples_dict: Dict[str, Any]
    ) -> bool:
        validation_status = True

        for sample_key, sample_val in samples_dict.items():
            value_dict = sample_val
            invalid_text = []
            invalid_option = []

            for value_key, value_val in value_dict.items():
                if value_key in field_dict.keys():
                    if field_dict[value_key][1] == "restricted text":
                        pattern = re.compile(field_dict[value_key][2])
                        if not pattern.match(str(value_val[0])):
                            invalid_text.append(
                                f"   {value_key} is set to invalid '{value_val[0]}'. "
                                f"Required regex is: {field_dict[value_key][2]}"
                            )

                    elif field_dict[value_key][1] == "text choice":
                        if value_val[0] not in field_dict[value_key][2]:
                            invalid_option.append(
                                f"   {value_key} is set to invalid option "
                                f"'{value_val[0]}'. Valid options are: {field_dict[value_key][2]}"
                            )

            # Log validation errors
            if invalid_text or invalid_option:
                self.log("================")
                self.log(
                    f"{sample_key} - {sample_val.get('taxon_id', ['N/A'])[0]} - {sample_val.get('tolid', ['N/A'])[0]}"
                )
                for field in invalid_text:
                    self.log(field)
                for field in invalid_option:
                    self.log(field)
                self.log("================")

            if invalid_text or invalid_option:
                validation_status = False

        return validation_status

    def create_primary_metagenome_sample(
        self, primary_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a primary metagenome sample dictionary.

        Args:
            primary_data: Dictionary containing primary metagenome data with keys:
                - host_biospecimen: Host biospecimen ID
                - host_taxname: Host taxonomic name
                - host_taxid: Host taxonomic ID
                - metagenome_taxid: Metagenome taxonomic ID
                - metagenome_taxname: Metagenome taxonomic name
                - metagenome_tolid: Metagenome ToL ID
                - broad-scale environmental context: Environmental context
                - local environmental context: Local context
                - environmental medium: Environmental medium

        Returns:
            Dictionary representing the primary metagenome sample
        """
        primary_uuid = f"{uuid.uuid4()}-{self.project_name}-metagenome"

        primary_dict = {
            "title": [primary_uuid, None],
            "taxon_id": [primary_data["metagenome_taxid"], None],
            "scientific_name": [primary_data["metagenome_taxname"], None],
            "host scientific name": [primary_data["host_taxname"], None],
            "host taxid": [primary_data["host_taxid"], None],
            "broad-scale environmental context": [
                primary_data["broad-scale environmental context"],
                None,
            ],
            "local environmental context": [
                primary_data["local environmental context"],
                None,
            ],
            "environmental medium": [primary_data["environmental medium"], None],
            "ENA-CHECKLIST": ["ERC000013", None],
            "tolid": [primary_data["metagenome_tolid"], None],
            "sample symbiont of": [primary_data["host_biospecimen"], None],
        }

        return primary_dict

    def create_bin_sample(
        self,
        binned_data: Dict[str, Any],
        host_scientific_name: str,
        host_taxid: str,
        checklist: str,
    ) -> Dict[str, Any]:
        """
        Create a binned metagenome sample dictionary.

        Args:
            binned_data: Dictionary containing binned sample data with keys:
            Dictionary containing bin/mag data with keys:
                - tol_id: ToLID of bin
                - taxon: taxonomic name of bin
                - taxon_id: TaxID of bin
                - number of standard tRNAs extracted
                - assembly software
                - 16S recovered
                - 16S recovery software
                - tRNA extraction software
                - completeness score
                - completeness software
                - contamination score
                - binning software
                - MAG coverage software
                - binning parameters
                - taxonomic identity marker
                - taxonomic classification
                - assembly quality
                - sequencing method
                - investigation type
                - isolation_source
                - broad-scale environmental context
                - local environmental context
                - environmental medium
                - metagenomic source
        Returns:
            Dictionary representing the binned sample
        """
        binned_dict = {
            "title": [
                f"{uuid.uuid4()}-{self.project_name}-{binned_data['bin_name']}",
                None,
            ],
            "taxon_id": [binned_data["taxon_id"], None],
            "scientific_name": [binned_data["taxon"], None],
            "host scientific name": [host_scientific_name, None],
            "host taxid": [host_taxid, None],
            "tolid": [binned_data["tol_id"], None],
            "ENA-CHECKLIST": [checklist, None],
            "number of standard tRNAs extracted": [
                binned_data["number of standard tRNAs extracted"],
                None,
            ],
            "assembly software": [binned_data["assembly software"], None],
            "16S recovered": [binned_data["16S recovered"], None],
            "16S recovery software": [binned_data["16S recovery software"], None],
            "tRNA extraction software": [binned_data["tRNA extraction software"], None],
            "completeness score": [binned_data["completeness score"], "%"],
            "completeness software": [binned_data["completeness software"], None],
            "contamination score": [binned_data["contamination score"], "%"],
            "binning software": [binned_data["binning software"], None],
            "MAG coverage software": [binned_data["MAG coverage software"], None],
            "binning parameters": [binned_data["binning parameters"], None],
            "taxonomic identity marker": [
                binned_data["taxonomic identity marker"],
                None,
            ],
            "taxonomic classification": [binned_data["taxonomic classification"], None],
            "assembly quality": [binned_data["assembly quality"], None],
            "sequencing method": [binned_data["sequencing method"], None],
            "investigation type": [binned_data["investigation type"], None],
            "isolation_source": [binned_data["isolation_source"], None],
            "broad-scale environmental context": [
                binned_data["broad-scale environmental context"],
                None,
            ],
            "local environmental context": [
                binned_data["local environmental context"],
                None,
            ],
            "environmental medium": [binned_data["environmental medium"], None],
            "metagenomic source": [binned_data["metagenomic source"], None],
        }

        if (
            binned_dict["assembly quality"][0]
            == "Many fragments with little to no review of assembly other than reporting of standard assembly statistics."
        ):
            binned_dict["assembly quality"][0] = (
                "Many fragments with little to no review of assembly other than reporting of standard assembly statistics"
            )

        if binned_dict["completeness score"][0] == 100.0:
            binned_dict["completeness score"][0] = 100

        return binned_dict

    def process_primary_metagenome(
        self, primary_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
        """
        Process a primary metagenome sample.

        Args:
            primary_data: Dictionary containing primary metagenome data

        Returns:
            Tuple of (validation_success, primary_sample_dict, host_sample_dict)
        """
        self.log("Processing primary metagenome")

        # Get host data from ENA
        host_sample_dict = self.ena_datasource.get_biosample_data_biosampleid(
            primary_data["host_biospecimen"]
        )

        # Create primary metagenome sample
        primary_dict = self.create_primary_metagenome_sample(primary_data)

        # Get and validate checklist
        self.log("Check primary checklist")
        tol_field_dict = self.ena_datasource.get_xml_checklist("ERC000013")

        self.log("Copy primary checklist items")
        primary_sample_dict = self.copy_checklist_items(
            tol_field_dict, host_sample_dict, primary_dict
        )

        # Validate
        self.log("Validate primary checklist items")
        primary_samples_dict = {primary_sample_dict["title"][0]: primary_sample_dict}
        validation_passed = self.validate_samples_with_checklist(
            tol_field_dict, primary_samples_dict
        )

        return validation_passed, primary_sample_dict, host_sample_dict

    def process_bin_samples(
        self,
        binned_data_list: List[Dict[str, Any]],
        primary_dict: Dict[str, Any],
        host_scientific_name: str,
        host_taxid: str,
        checklist: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Process binned metagenome samples.

        Args:
            binned_data_list: List of dictionaries containing binned sample data
            primary_dict: Primary sample dictionary
            host_scientific_name: Host scientific name
            host_taxid: Host taxonomic ID

        Returns:
            Tuple of (validation_success, binned_samples_dict)
        """
        self.log("Processing binned samples")

        # Get binned metagenome checklist
        bm_field_dict = self.ena_datasource.get_xml_checklist(checklist)

        binned_samples_dict = {}

        for i, binned_data in enumerate(binned_data_list):
            binned_dict = self.create_bin_sample(
                binned_data, host_scientific_name, host_taxid, checklist
            )

            self.log(f"Copy checklist items for binned {i}")
            binned_sample_dict = self.copy_checklist_items(
                bm_field_dict, primary_dict, binned_dict
            )
            binned_samples_dict[binned_sample_dict["title"][0]] = binned_sample_dict

        # Validate
        self.log("Validate binned checklist items")
        validation_passed = self.validate_samples_with_checklist(
            bm_field_dict, binned_samples_dict
        )

        return validation_passed, binned_samples_dict

    def generate_biosample_ids(
        self,
        primary_data: Dict[str, Any],
        binned_data_list: Optional[List[Dict[str, Any]]] = None,
        mag_data_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate ENA biosample IDs for metagenome samples.

        Args:
            primary_data: Dictionary containing primary metagenome data
            binned_data_list: Optional list of binned sample data
            mag_data_list: Optional list of MAG sample data

        Returns:
            Tuple of (success, results_dict) where results_dict contains:
                - 'primary': primary sample with biosample ID
                - 'binned': dict of binned samples with biosample IDs
                - 'mags': dict of MAG samples with biosample IDs
                - 'summary': list of [type, tolid, biosample_accession] for output
        """
        # Process primary metagenome
        primary_validation_passed, primary_sample_dict, host_sample_dict = (
            self.process_primary_metagenome(primary_data)
        )

        if not primary_validation_passed:
            self.log("Primary validation failed")
            return False, {"error": "Primary validation failed"}

        # Process binned and MAG samples
        binned_samples_dict = {}
        mag_samples_dict = {}
        binned_validation_passed = True
        mag_validation_passed = True

        if binned_data_list:
            binned_validation_passed, binned_samples_dict = self.process_bin_samples(
                binned_data_list,
                primary_sample_dict,
                primary_data["host_taxname"],
                primary_data["host_taxid"],
                "ERC000050",
            )

        if mag_data_list:
            mag_validation_passed, mag_samples_dict = self.process_bin_samples(
                mag_data_list,
                primary_sample_dict,
                primary_data["host_taxname"],
                primary_data["host_taxid"],
                "ERC000047",
            )

        if not (
            primary_validation_passed
            and binned_validation_passed
            and mag_validation_passed
        ):
            self.log("Validation failed")
            return False, {"error": "Validation failed"}

        # Submit to ENA
        self.log("Generate ENA IDs for primary samples")
        primary_samples_dict = {primary_sample_dict["title"][0]: primary_sample_dict}
        primary_success, primary_submission_dict = (
            self.ena_datasource.generate_ena_ids_for_samples(
                uuid.uuid4(), primary_samples_dict
            )
        )

        if not primary_success:
            self.log("ENA generation failed for primary")
            for val in primary_submission_dict.values():
                self.log(str(val))
            return False, {
                "error": "Primary ENA submission failed",
                "details": primary_submission_dict,
            }

        self.log("ENA generation succeeded for primary")
        primary_uuid = primary_sample_dict["title"][0]
        primary_metagenome_dict = primary_submission_dict[primary_uuid]

        # Submit binned and MAG samples if they exist
        binned_mag_submission_dict = {}
        if binned_samples_dict or mag_samples_dict:
            # Combine binned and MAG samples
            combined_samples_dict = {**binned_samples_dict, **mag_samples_dict}

            # Add primary biosample ID to derived samples
            if primary_metagenome_dict.get("biosample_accession", [None])[0]:
                updated_combined_samples_dict = {}
                for key, val in combined_samples_dict.items():
                    val["sample derived from"] = [
                        primary_metagenome_dict["biosample_accession"][0],
                        None,
                    ]
                    updated_combined_samples_dict[key] = val

                self.log("Generate ENA IDs for binned/MAG samples")
                combined_success, binned_mag_submission_dict = (
                    self.ena_datasource.generate_ena_ids_for_samples(
                        uuid.uuid4(), updated_combined_samples_dict
                    )
                )

                if not combined_success:
                    self.log("ENA generation failed for binned/mag")
                    for val in binned_mag_submission_dict.values():
                        self.log(str(val))
                    return False, {
                        "error": "Binned/MAG ENA submission failed",
                        "details": binned_mag_submission_dict,
                    }

                self.log("ENA generation succeeded for binned/mag")
            else:
                self.log("Biosample accession not returned for primary metagenome")
                return False, {"error": "Primary biosample accession not available"}

        summary = {
            "primary": {
                "tolid": primary_metagenome_dict["tolid"][0],
                "biosample": primary_metagenome_dict["biosample_accession"][0],
            },
            "magsbins": [
                {"tolid": val["tolid"][0], "biosample": val["biosample_accession"][0]}
                for key, val in binned_mag_submission_dict.items()
            ],
        }

        return True, summary
