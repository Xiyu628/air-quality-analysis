# Data README

This folder stores the raw and processed data used by the project.

## Raw Data

Expected files:

- `raw/2024_All_sites_air_quality_hourly_avg_AIR-I-F-V-VH-O-S1-DB-M2-4-0.xlsx`
- `raw/seifa_2021_sa2.xlsx`
- `raw/SA2_2021/SA2_2021_AUST_GDA2020.shp`
- matching shapefile sidecar files: `.dbf`, `.shx`, `.prj`, `.xml`

Official source pages:

- EPA Victoria / DataVic AirWatch yearly hourly averages: https://discover.data.vic.gov.au/dataset/epa-air-watch-all-sites-air-quality-hourly-averages-yearly
- ABS SEIFA 2021: https://www.abs.gov.au/statistics/people/people-and-communities/socio-economic-indexes-areas-seifa-australia/2021
- ABS ASGS Edition 3 digital boundary files: https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files

## Processed Data

Generated or reused files:

- `processed/stations.csv`: station metadata and SA2 membership.
- `processed/station_pollutant_summary.csv`: annual and seasonal pollutant summaries by station.
- `processed/monthly_summary.csv`: monthly mean concentration by station and pollutant.
- `processed/weekday_hour_patterns.csv`: weekday-hour concentration fingerprints.
- `processed/daily_pm25.csv`: daily mean PM2.5 by station.
- `processed/exceedance_counts.csv`: exceedance-day counts by station and pollutant.
- `processed/correlations.csv`: Spearman correlations between SA2 exposure estimates and SEIFA indexes.
- `processed/sa2_exposure_seifa.geojson`: Greater Melbourne SA2 polygons with SEIFA fields and IDW exposure estimates.

The processed data are designed to be small enough for reporting and reproducible analysis. The raw data are kept only for provenance and rebuilding.
