#!/usr/bin/env python
"""
Command-line interface for the modular MetagenomeBiosampleGenerator

This script provides a command-line interface that reads CSV files and uses the
modular MetagenomeBiosampleGenerator to generate ENA biosample IDs.
It maintains compatibility with the original script's interface while using
the new modular backend.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

import pandas as pd
from MetagenomeGenerator import HostAssocMetagenomeBiosampleGenerator

def validate_primary_csv_columns(df: pd.DataFrame) -> None:
    """Validate that the primary CSV has required columns."""
    required_columns = [
        "host_biospecimen",
        "host_taxname",
        "host_taxid",
        "metagenome_taxid",
        "metagenome_taxname",
        "metagenome_tolid",
        "broad-scale environmental context",
        "local environmental context",
        "environmental medium",
        "binned_path",
        "mag_path",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Primary CSV missing required columns: {missing_columns}")
        print(f"Required columns: {required_columns}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)


def validate_bin_columns(df: pd.DataFrame) -> None:
    """Validate that binned/MAG CSV has required columns."""
    required_columns = [
        "bin_name",
        "taxon_id",
        "taxon",
        "tol_id",
        "number of standard tRNAs extracted",
        "assembly software",
        "16S recovered",
        "16S recovery software",
        "tRNA extraction software",
        "completeness score",
        "completeness software",
        "contamination score",
        "binning software",
        "MAG coverage software",
        "binning parameters",
        "taxonomic identity marker",
        "taxonomic classification",
        "assembly quality",
        "sequencing method",
        "investigation type",
        "isolation_source",
        "broad-scale environmental context",
        "local environmental context",
        "environmental medium",
        "metagenomic source",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: CSV missing required columns: {missing_columns}")
        print(f"Required columns: {required_columns}")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)


def convert_primary_row_to_dict(row: pd.Series) -> Dict[str, Any]:
    """Convert a pandas Series (CSV row) to the primary data format."""
    return {
        "host_biospecimen": str(row["host_biospecimen"]),
        "host_taxname": str(row["host_taxname"]),
        "host_taxid": str(row["host_taxid"]),
        "metagenome_taxid": str(row["metagenome_taxid"]),
        "metagenome_taxname": str(row["metagenome_taxname"]),
        "metagenome_tolid": str(row["metagenome_tolid"]),
        "broad-scale environmental context": str(
            row["broad-scale environmental context"]
        ),
        "local environmental context": str(row["local environmental context"]),
        "environmental medium": str(row["environmental medium"]),
        "binned_path": None
        if pd.isna(row["binned_path"]) or row["binned_path"] == ""
        else str(row["binned_path"]),
        "mag_path": None
        if pd.isna(row["mag_path"]) or row["mag_path"] == ""
        else str(row["mag_path"]),
    }


def save_results_to_csv(results: Dict[str, Any], output_file: str) -> None:
    """Save results summary to CSV file."""
    try:
        summary_data = results.get("summary", [])
        if summary_data:
            df = pd.DataFrame(
                summary_data, columns=["Type", "ToLID", "Biosample Accession"]
            )
            df.to_csv(output_file, index=False)
    except Exception as e:
        print(f"Error saving results to '{output_file}': {e}")


def process_metagenomes(
    primary_df: pd.DataFrame,
    generator: MetagenomeBiosampleGenerator,
    output_file: Optional[str] = None,
) -> bool:
    """
    Process all metagenomes in the primary CSV.

    Args:
        primary_df: DataFrame with primary metagenome data
        generator: MetagenomeBiosampleGenerator instance
        binned_paths: List of paths to binned sample CSVs (one per primary sample)
        mag_paths: List of paths to MAG sample CSVs (one per primary sample)
        output_file: Output CSV file path

    Returns:
        True if all processing succeeded, False otherwise
    """
    all_results = []
    overall_success = True

    for index, primary_row in primary_df.iterrows():
        primary_data = convert_primary_row_to_dict(primary_row)

        binned_data_list = None
        mag_data_list = None

        if primary_data["binned_path"]:
            binned_path = primary_data["binned_path"].strip()
            if binned_path:
                print(f"Loading binned data from: {binned_path}")
                try:
                    binned_df = pd.read_csv(binned_path)
                    validate_bin_columns(binned_df)
                    binned_data_list = binned_df.to_dict()
                except Exception as e:
                    print(f"Error loading binned data: {e}")
                    overall_success = False

        if primary_data["mag_path"]:
            mag_path = primary_data["mag_path"].strip()
            if mag_path:
                try:
                    mag_df = pd.read_csv(mag_path)
                    validate_bin_columns(mag_df)
                    mag_data_list = mag_df.to_dict()
                except Exception as e:
                    print(f"Error loading MAG data: {e}")
                    overall_success = False

        # Generate biosample IDs
        success, results = generator.generate_biosample_ids(
            primary_data=primary_data,
            binned_data_list=binned_data_list,
            mag_data_list=mag_data_list,
        )

        if success:
            if "summary" in results:
                all_results.extend(results["summary"])

            primary = results.get("primary", {})
            if "biosample_accession" in primary:
                print(f"  Primary ID: {primary['biosample_accession'][0]}")

            binned_count = len(results.get("binned", {}))
            mag_count = len(results.get("mags", {}))
            if binned_count > 0:
                print(f"  Binned samples: {binned_count}")
            if mag_count > 0:
                print(f"  MAG samples: {mag_count}")

        else:
            print(
                f"❌ Failed to generate biosample IDs for {primary_data['metagenome_tolid']}"
            )
            print(f"  Error: {results.get('error', 'Unknown error')}")
            overall_success = False


    if all_results:
        try:
            combined_results = {"summary": all_results}
            save_results_to_csv(combined_results, output_file)
        except Exception as e:
            print(f"Error saving combined results: {e}")
            overall_success = False

    return overall_success


def main():
    """Main function for command-line interface."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-a",
        "--api_credentials",
        dest="credentials",
        required=True,
        help="Path to JSON file containing ENA API credentials",
    )

    parser.add_argument(
        "-p",
        "--project_name",
        dest="project",
        required=True,
        help="Project name for sample naming",
    )

    parser.add_argument(
        "-d",
        "--data_csv",
        dest="primary_csv",
        required=True,
        help="Path to CSV file containing primary metagenome data",
    )

    parser.add_argument(
        "-o",
        "--output_file",
        dest="output",
        help="Path to output CSV file for results summary",
    )

    args = parser.parse_args()

    try:
        with open(args.credentials, "r") as f:
            credentials = json.load(f)["credentials"]
    except FileNotFoundError:
        print(f"Error: Credentials file '{args.credentials}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in credentials file: {e}")
        sys.exit(1)

    primary_df = pd.read_csv(args.primary_csv)
    validate_primary_csv_columns(primary_df)

    generator = HostAssocMetagenomeBiosampleGenerator(
        ena_credentials=credentials,
        project_name=args.project,
    )

    success = process_metagenomes(
        primary_df=primary_df,
        generator=generator,
        output_file=args.output,
    )

if __name__ == "__main__":
    main()
