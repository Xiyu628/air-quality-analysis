# Air Quality Analysis in Greater Melbourne

## Overview

This project analyses air quality across Greater Melbourne using publicly available datasets from **EPA Victoria** and the **Australian Bureau of Statistics (ABS)**.

The project performs data cleaning, statistical analysis, spatial analysis, visualisation, and automated report generation to investigate the relationship between air pollution exposure and socio-economic indicators.

---

## Features

* Data validation and quality checking
* Air quality data preprocessing
* Pollutant trend analysis
* Spatial exposure estimation
* Socio-economic correlation analysis (SEIFA)
* Automated figure generation
* Automated PDF report generation

---

## Data Sources

The project uses three publicly available datasets:

* EPA Victoria AirWatch Hourly Air Quality Data
* ABS SEIFA 2021
* ABS ASGS Edition 3 SA2 Boundary Data

Large raw datasets are **not included** in this repository and can be downloaded from the official providers.

---

## Technologies

* Python
* Pandas
* NumPy
* GeoPandas
* SciPy
* Matplotlib
* Seaborn
* ReportLab

---

## Project Structure

```text
.
├── code/
│   ├── 01_check_data.py
│   ├── 02_build_processed_data.py
│   ├── 03_make_figures.py
│   ├── 04_generate_pdfs.py
│   └── config.py
│
├── data/
│   ├── processed/
│   └── raw/           (ignored in Git)
│
├── figures/
│
├── outputs/
│
├── report/
│   ├── report.tex
│   └── air_quality_report.pdf
│
├── requirements.txt
└── README.md
```

---

## Workflow

### 1. Check datasets

```bash
python code/01_check_data.py
```

### 2. Build processed datasets

```bash
python code/02_build_processed_data.py
```

### 3. Generate visualisations

```bash
python code/03_make_figures.py
```

### 4. Generate PDF report

```bash
python code/04_generate_pdfs.py
```

---

## Generated Outputs

### Processed datasets

* Monthly pollutant summary
* Daily PM2.5 statistics
* Weekday-hour pollution patterns
* Station summaries
* SA2 exposure estimates
* Correlation tables

### Figures

* Monthly PM2.5 Heatmap
* Daily PM2.5 Time Series
* Weekday-Hour PM2.5 Pattern
* Pollution Exceedance Heatmap
* SEIFA Correlation Heatmap
* PM2.5 vs IRSD Scatter Plot

### Report

The project automatically generates an analytical PDF report summarising:

* Data preprocessing
* Temporal pollution trends
* Pollutant comparisons
* Spatial exposure analysis
* Socio-economic relationships
* Key findings

---

## Installation

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Notes

The repository includes:

* Source code
* Processed datasets
* Figures
* Generated report

Raw datasets are excluded from version control because they are publicly available and significantly increase repository size.

---

## Author

**Xiyu Hao**

UNSW Sydney

GitHub: https://github.com/Xiyu628
