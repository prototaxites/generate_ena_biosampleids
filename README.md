# Scripts for generating ENA Biosample IDs

These scripts are methods to generate Biosample IDs for cobionts and metagenomes.

These scripts use the [ENA API](https://ena-docs.readthedocs.io/en/latest/retrieval/programmatic-access.html), so credentials for accessing the ENA API must be provided in the form of a .json file in the following format.

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

### Software requirements

- pandas >= 2.1.4
- requests >= 2.28.1

## Generate cobiont biosample ids

This is to be used when a biospecimen exists and you wish to create cobionts linked to this biospecimen.

### **1. Create input CSV with the following columns:**

| Column Name      | Required Data                                                                |
| ---------------- | ---------------------------------------------------------------------------- |
| host_biospecimen | Biospecimen ID of host (e.g. SAMEA12097741)                                  |
| cobiont_taxname  | Scientific name of cobiont (e.g. Gammaproteobacteria bacterium Psp_hYS2021)  |
| cobiont_taxid    | Taxon ID of cobiont (e.g. 3040533)                                           |
| cobiont_tolid    | [Tree of Life ID](https://id.tol.sanger.ac.uk/) of cobiont (e.g. ucAstSpea1) |

Example input CSV

```
host_biospecimen,cobiont_taxname,cobiont_taxid,cobiont_tolid
SAMEA111491374,Asterochloris sp. CNOR1,3094912,ucAstSpea1
```

Multiple cobionts can be added as additional rows in the CSV. They do not have to be associated with the same host biospecimen.

### **2. Run using the following command**

```
python generate_cobiont_biosampleId.py
-a <credentials_file_name>[.json]
-p <project_name>
-d <input_file_name>[.csv]
-o <output_file_name>[.csv]
```

This method adds a new entry to the ENA website using the provided project name. It is marked as being a symbiont with the 'sample derived from' set to the host biospecimen. It is validated using the checklist [Tree of Life Checklist](https://www.ebi.ac.uk/ena/browser/view/ERC000053), with all fields being populated from the existing host biospecimen. The only fields that are not populated in this way are those included in the CSV (scientific name, Taxon ID and ToLID).

### **3. Using the output file**

The method returns a CSV in the below format to the file path set in the -o argument.

```
Type,ToLID,Biosample Accession
cobiont,ucAstSpea1,SAMEA114709654
cobiont,ucAstSpeb1,SAMEA114709655
```

Biosample Accession is the Biosample IDs for the added cobionts.

N.B. The biosample IDs will be returned on running this script, but there is sometimes a short delay on these entries being visible on the website.

## Generate metagenome biosample ids (with linked binned and MAGs)

This is to be used when you have a biospecimen and you wish to create an associated metagenome with linked binned and MAGs. This requires three CSV files as input: the primary containing the metagenome details, the binned containing the binned metagenome samples, and the MAG containing the MAG samples.

### **1. Create primary CSV with the following columns:**

| Column Name                       | Required Data                                                     |
| --------------------------------- | ----------------------------------------------------------------- |
| host_biospecimen                  | Biosample id of host specimen (e.g. SAMEA111454470)               |
| host_taxname                      | Scientific name of host specimen (e.g. Heterometopus palaeformis) |
| host_taxid                        | Taxonomy ID of host specimen (e.g. 5965)                          |
| metagenome_taxname                | Scientific name of metagenome (e.g. ciliate metagenome)           |
| metagenome_taxid                  | Taxonomy ID of metagenome (e.g. 1969832)                          |
| metagenome_tolid                  | (e.g. piHetPala1.metagenome)                                      |
| broad-scale environmental context | (e.g. aquatic biome)                                              |
| local environmental context       | (e.g. small freshwater lake biome)                                |
| environmental medium              | (e.g. ciliate culture)                                            |
| binned_path                       | Path to binned samples CSV (e.g. ./binned_biosample_metadata.csv) |
| mag_path                          | Path to MAG samples CSV (e.g. ./mag_biosample_metadata.csv)       |

Example CSV

```
host_biospecimen,host_taxname,host_taxid,metagenome_taxname,metagenome_taxid,metagenome_tolid,broad-scale environmental context,local environmental context,environmental medium,binned_path,mag_path
SAMEA111454470,Heterometopus palaeformis,5965,ciliate metagenome,1969832,piHetPala1.metagenome,aquatic biome,small freshwater lake biome,ciliate culture,./binned_biosample_metadata.csv,./mag_biosample_metadata.csv
```

Primary metagenome samples being submitted to ENA are validated using the [GSC MIxS host associated](https://www.ebi.ac.uk/ena/browser/view/ERC000013) checklist.

### **2. Create binned samples CSV**

| Column Name                        | Required Data                                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| bin_name                           | (e.g. MAGScoT_cleanbin_000125)                                                                                           |
| tol_id                             | (e.g. piHetPala1.Methanobacteriaceae_archaeon_1)                                                                         |
| taxon                              | (e.g. Methanobacteriaceae archaeon)                                                                                      |
| taxon_id                           | (e.g. 2099680)                                                                                                           |
| number of standard tRNAs extracted | (e.g. 28)                                                                                                                |
| assembly software                  | (e.g. metaMDBG)                                                                                                          |
| 16S recovered                      | (e.g. No)                                                                                                                |
| 16S recovery software              | (e.g. PROKKA (version 1.14.5))                                                                                           |
| tRNA extraction software           | (e.g. PROKKA (version 1.14.5))                                                                                           |
| completeness score                 | (e.g. 73.94)                                                                                                             |
| completeness software              | (e.g. checkM (version 1.2.1); checkM_DB (release 2015-01-16))                                                            |
| contamination score                | (e.g. 2.4)                                                                                                               |
| binning software                   | (e.g. MAGScoT (version 1.0.0); MetaBat (version 2.15-15-gd6ea400); bin3C (version 0.3.3); MaxBin (version 2.7); MetaTOR) |
| MAG coverage software              | (e.g. Minimap2 (version 2.24-r1122))                                                                                     |
| binning parameters                 | (e.g. coverage; graph; hic-mapping)                                                                                      |
| taxonomic identity marker          | (e.g. taxonomic classification defined by topology and ANI)                                                              |
| taxonomic classification           | (e.g. GTDB-TK (version 2.1.1); GTDB (release 207_v2))                                                                    |
| assembly quality                   | (e.g. Many fragments with little to no review of assembly other than reporting of standard assembly statistics.)         |
| sequencing method                  | (e.g. Pacbio Sequel II)                                                                                                  |
| investigation type                 | (e.g. metagenome-assembled genome)                                                                                       |
| isolation_source                   | (e.g. Ciliate: Heterometopus palaeformis)                                                                                |
| broad-scale environmental context  | (e.g. aquatic biome)                                                                                                     |
| local environmental context        | (e.g. small freshwater lake biome)                                                                                       |
| environmental medium               | (e.g. ciliate culture)                                                                                                   |
| metagenomic source                 | (e.g. ciliate metagenome)                                                                                                |

Example CSV

```
bin_name,tol_id,taxon,taxon_id,number of standard tRNAs extracted,assembly software,16S recovered,16S recovery software,tRNA extraction software,completeness score,completeness software,contamination score,binning software,MAG coverage software,binning parameters,taxonomic identity marker,taxonomic classification,assembly quality,sequencing method,investigation type,isolation_source,broad-scale environmental context,local environmental context,environmental medium,metagenomic source
MAGScoT_cleanbin_000125,piHetPala1.Methanobacteriaceae_archaeon_1,Methanobacteriaceae archaeon,2099680,28,metaMDBG,No,PROKKA (version 1.14.5),PROKKA (version 1.14.5),73.94,checkM (version 1.2.1); checkM_DB (release 2015-01-16),2.4,MAGScoT (version 1.0.0); MetaBat (version 2.15-15-gd6ea400); bin3C (version 0.3.3); MaxBin (version 2.7); MetaTOR,Minimap2 (version 2.24-r1122),coverage; graph; hic-mapping,taxonomic classification defined by topology and ANI,GTDB-TK (version 2.1.1); GTDB (release 207_v2),Many fragments with little to no review of assembly other than reporting of standard assembly statistics.,Pacbio Sequel II,metagenome-assembled genome,Ciliate: Heterometopus palaeformis,aquatic biome,small freshwater lake biome,ciliate culture,ciliate metagenome
```

Binned metagenome samples being submitted to ENA are validated using the [ENA binned metagenome](https://www.ebi.ac.uk/ena/browser/view/ERC000050) checklist.

### **3. Create MAG samples CSV**

| Column Name                        | Required Data                                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| bin_name                           | (e.g. MAGScoT_cleanbin_000084)                                                                                           |
| tol_id                             | (e.g. piHetPala1.Methanomassiliicoccaceae_archaeon_1)                                                                    |
| taxon                              | (e.g. Methanomassiliicoccaceae archaeon)                                                                                 |
| taxon_id                           | (e.g. 2052168)                                                                                                           |
| number of standard tRNAs extracted | (e.g. 39)                                                                                                                |
| assembly software                  | (e.g. metaMDBG)                                                                                                          |
| 16S recovered                      | (e.g. Yes)                                                                                                               |
| 16S recovery software              | (e.g. PROKKA (version 1.14.5))                                                                                           |
| tRNA extraction software           | (e.g. PROKKA (version 1.14.5))                                                                                           |
| completeness score                 | (e.g. 99.19                                                                                                              |
| completeness software              | (e.g. checkM (version 1.2.1); checkM_DB (release 2015-01-16))                                                            |
| contamination score                | (e.g. 0.81)                                                                                                              |
| binning software                   | (e.g. MAGScoT (version 1.0.0); MetaBat (version 2.15-15-gd6ea400); bin3C (version 0.3.3); MaxBin (version 2.7); MetaTOR) |
| MAG coverage software              | (e.g. Minimap2 (version 2.24-r1122))                                                                                     |
| binning parameters                 | (e.g. coverage; graph; hic-mapping)                                                                                      |
| taxonomic identity marker          | (e.g. taxonomic classification defined by topology and ANI)                                                              |
| taxonomic classification           | (e.g. GTDB-TK (version 2.1.1); GTDB (release 207_v2)                                                                     |
| assembly quality                   | (e.g. Single contiguous sequence without gaps or ambiguities with a consensus error rate equivalent to Q50 or better)    |
| sequencing method                  | (e.g. Pacbio Sequel II)                                                                                                  |
| investigation type                 | (e.g. metagenome-assembled genome)                                                                                       |
| isolation_source                   | (e.g. Ciliate: Heterometopus palaeformis)                                                                                |
| broad-scale environmental context  | (e.g. aquatic biome)                                                                                                     |
| local environmental context        | (e.g. small freshwater lake biome)                                                                                       |
| environmental medium               | (e.g. ciliate culture)                                                                                                   |
| metagenomic source                 | (e.g. ciliate metagenome)                                                                                                |

Example CSV

```
bin_name,tol_id,taxon,taxon_id,number of standard tRNAs extracted,assembly software,16S recovered,16S recovery software,tRNA extraction software,completeness score,completeness software,contamination score,binning software,MAG coverage software,binning parameters,taxonomic identity marker,taxonomic classification,assembly quality,sequencing method,investigation type,isolation_source,broad-scale environmental context,local environmental context,environmental medium,metagenomic source
MAGScoT_cleanbin_000084,piHetPala1.Methanomassiliicoccaceae_archaeon_1,Methanomassiliicoccaceae archaeon,2052168,39,metaMDBG,Yes,PROKKA (version 1.14.5),PROKKA (version 1.14.5),99.19,checkM (version 1.2.1); checkM_DB (release 2015-01-16),0.81,MAGScoT (version 1.0.0); MetaBat (version 2.15-15-gd6ea400); bin3C (version 0.3.3); MaxBin (version 2.7); MetaTOR,Minimap2 (version 2.24-r1122),coverage; graph; hic-mapping,taxonomic classification defined by topology and ANI,GTDB-TK (version 2.1.1); GTDB (release 207_v2),Single contiguous sequence without gaps or ambiguities with a consensus error rate equivalent to Q50 or better,Pacbio Sequel II,metagenome-assembled genome,Ciliate: Heterometopus palaeformis,aquatic biome,small freshwater lake biome,ciliate culture,ciliate metagenome
```

MAGs being submitted to ENA are validated using the [GSC MIMAGS](https://www.ebi.ac.uk/ena/browser/view/ERC000047) checklist.

### **4. Run using the following command:**

```
python generate_metagenome_biosample.py
-a <credentials_file_name>[.json]
-p <project_name>
-d <input_file_name>[.csv]
-o <output_file_name>[.csv]
```

### **5. Using the output file**

The method returns a CSV in the below format to the file path set in the -o argument.

```
Type,ToLID,Biosample Accession
cobiont,ucAstSpea1,SAMEA114709654
cobiont,ucAstSpeb1,SAMEA114709655
```

Type shows whether the added entry is
ToLID has the ToLID for the added entry.
Biosample Accession is the Biosample IDs for the added entry.

N.B. The biosample IDs will be returned on running this script, but there is sometimes a short delay on these entries being visible on the website.
