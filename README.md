# Generate ENA Biosamples

## Using submissions API to generate cobiont biosamples.

Credentials are required as a JSON file with the values:
{
    "submission_credentials": {
        "api_url": <SUBMISSIONS API URL>,
        "api_key": <SUBMISSIONS API KEY>,
    }
}

Requires input CSV (with columns for Cobiont Taxname, Cobiont Taxid, and Host Biospecimen)

e.g.
host_biospecimen,cobiont_taxname,cobiont_taxid
SAMEA12097741,Gammaproteobacteria bacterium Psp_hYS2021,3040533

To run use command 
    python generate_cobiont_biosampleId_using_submissions_api.py -a dev_submission_credentials.json -p asg -d input.csv -o output.csv


## Using ENA API to generate metagenome biosamples (with linked binned and MAGs).

Under construction

Credentials are required as a .json file with the values:
{
    "credentials": {
        "uri": <ENA WEBSITE>,
        "user": <ENA USERNAME>,
        "password": <ENA PASSWORD>,
        "contact_name": <ENA CONTACT NAME>,
        "contact_email": <ENA CONTACT EMAIL>
    }
}

To run use command 
    python generate_cobiont_biosampleId_using_submissions_api.py -a dev_environment.json -p asg -d test_data/input_data.csv -o test_data/output_summary.csv

e.g.
        python generate_cobiont_biosampleId_using_submissions_api.py -a dev_environment.json -p asg -d test_data/glLicPygm2_primary_biosample.csv -o test_data/glLicPygm2_output_biosamples.csv


SAMEA12097741,Gammaproteobacteria bacterium Psp_hYS2021,3040533
SAMEA13602795,Alphaproteobacteria bacterium CMAR1,3040918



cobiont_taxname,cobiont_taxid,host_biospecimen,biosample_accession
Pleurocapsa sp. FMAR1,3040204,SAMEA13854150,SAMEA114098567