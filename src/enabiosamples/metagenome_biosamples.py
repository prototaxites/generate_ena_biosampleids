#!/usr/bin/env python
"""
Command-line interface for the modular MetagenomeBiosampleGenerator

This script provides a command-line interface that reads CSV files and uses the
modular MetagenomeBiosampleGenerator to generate ENA biosample IDs.
It maintains compatibility with the original script's interface while using
the new modular backend.
"""

import json
import sys

import click
import polars as pl
from ena_datasource import EnaDataSource
from enabiosamples.HostAssocMetagenomeBiosampleGenerator import (
    HostAssocMetagenomeBiosampleGenerator,
)


def read_bin_csv(path: str) -> pl.DataFrame:
    """Validate that binned/MAG CSV has required columns."""

    return pl.read_csv(
        path,
        schema={
            "bin_name": pl.String,
            "tol_id": pl.String,
            "taxon": pl.String,
            "taxon_id": pl.Int64,
            "number of standard tRNAs extracted": pl.Int16,
            "assembly software": pl.String,
            "16S recovered": pl.String,
            "16S recovery software": pl.String,
            "tRNA extraction software": pl.String,
            "completeness score": pl.Float64,
            "completeness software": pl.String,
            "contamination score": pl.Float64,
            "binning software": pl.String,
            "MAG coverage software": pl.String,
            "binning parameters": pl.String,
            "taxonomic identity marker": pl.String,
            "taxonomic classification": pl.String,
            "assembly quality": pl.String,
            "sequencing method": pl.String,
            "investigation type": pl.String,
            "isolation_source": pl.String,
            "broad-scale environmental context": pl.String,
            "local environmental context": pl.String,
            "environmental medium": pl.String,
            "metagenomic source": pl.String,
        },
    )


def process_metagenomes(
    primary_df: pl.DataFrame, generator: HostAssocMetagenomeBiosampleGenerator
) -> bool:
    for row in primary_df.iter_rows(named=True):
        binned_data_list = None
        mag_data_list = None

        if row["binned_path"]:
            try:
                binned_df = read_bin_csv(row["binned_path"])
                binned_data_list = binned_df.to_dicts()
            except Exception as e:
                print(f"Error loading binned data: {e}")

        if row["mag_path"]:
            try:
                mag_df = read_bin_csv(row["mag_path"])
                mag_data_list = mag_df.to_dicts()
            except Exception as e:
                print(f"Error loading MAG data: {e}")

        success, results = generator.generate_biosample_ids(
            primary_data=row,
            binned_data_list=binned_data_list,
            mag_data_list=mag_data_list,
        )

    return success, results


@click.command()
@click.option(
    "-a",
    "--api_credentials",
    type=click.File("r"),
    required=True,
    help="JSON file containing ENA API credentials.",
)
@click.option(
    "-p", "--project", type=str, required=True, help="Project name for sample naming"
)
@click.option("-d", "--debug", is_flag=True, default=False, help="Enable debugging")
@click.option(
    "-o",
    "--output_file",
    type=str,
    required=True,
    help="Path to output TSV file",
    default="biosamples.tsv",
)
@click.option(
    "-l",
    "--log_file",
    type=click.Path(),
    required=True,
    help="Path to log file",
    default="biosamples.log",
)
@click.argument("primary_csv", type=click.File("r"), required=True)
def cli(api_credentials, project, primary_csv, output_file, log_file, debug):
    """Main function for command-line interface."""

    try:
        credentials = json.load(api_credentials)["credentials"]
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in credentials file: {e}")
        sys.exit(1)

    primary_df = pl.read_csv(
        primary_csv,
        schema={
            "host_biospecimen": pl.String,
            "host_taxname": pl.String,
            "host_taxid": pl.Int64,
            "metagenome_taxname": pl.String,
            "metagenome_taxid": pl.Int64,
            "metagenome_tolid": pl.String,
            "broad-scale environmental context": pl.String,
            "local environmental context": pl.String,
            "environmental medium": pl.String,
            "binned_path": pl.String,
            "mag_path": pl.String,
        },
    )

    ena_datasource = EnaDataSource(config=credentials, debug=debug)

    generator = HostAssocMetagenomeBiosampleGenerator(
        ena_datasource=ena_datasource, project_name=project, log_file=log_file
    )

    success, results = process_metagenomes(primary_df=primary_df, generator=generator)

    ## Write biosamples to a TSV file
    (
        pl.DataFrame([results["primary"]] + results["magsbins"]).write_csv(
            output_file, separator="\t"
        )
    )


if __name__ == "__main__":
    cli()
