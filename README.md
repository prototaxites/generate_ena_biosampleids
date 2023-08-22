# Generate ENA Biosamples

## Generate cobiont biosample ids - (Uses TOL submissions API).

Credentials are required as a JSON file with the values:
```
{
    "submission_credentials": {
        "api_url": <SUBMISSIONS API URL>,
        "api_key": <SUBMISSIONS API KEY>,
    }
}
```
Requires input CSV (with columns for Cobiont Taxname, Cobiont Taxid, and Host Biospecimen)
```
host_biospecimen,cobiont_taxname,cobiont_taxid
SAMEA12097741,Gammaproteobacteria bacterium Psp_hYS2021,3040533
```
To run use command 
```
python generate_cobiont_biosampleId_using_submissions_api.py -a dev_submission_credentials.json -p asg -d input.csv -o output.csv
```

## Generate metagenome biosample ids (with linked binned and MAGs) - (Uses ENA API) .

### Credentials
Credentials are required as a .json file with the values:
```
{
    "credentials": {
        "uri": <ENA WEBSITE>,
        "user": <ENA USERNAME>,
        "password": <ENA PASSWORD>,
        "contact_name": <ENA CONTACT NAME>,
        "contact_email": <ENA CONTACT EMAIL>
    }
}
```
### To run use command 
    python generate_metagenome_biosample.py -a dev_environment.json -p asg -d test_data/input_data.csv -o test_data/output_summary.csv

### Input data CSV format

Required fields - primary metagenome:
|||
|---|---|
|host_biospecimen|Biosample id of host sample|
|host_taxname|Scientific name of host|
|host_taxid| Taxonomy ID of host|
|metagenome_taxname| Scientific name of metagenome|
|metagenome_taxid|Taxonomy ID of metagenome|
|metagenome_tolid||
|broad-scale environmental context||
|local environmental context||
|environmental medium||
|binned_path| Path to binned samples .csv|
|mag_path|Path to MAG samples .csv|

e.g.
```

```