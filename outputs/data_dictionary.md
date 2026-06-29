# Data Dictionary

## Processed files

- `stations.csv`: monitoring station metadata and SA2 membership.
- `station_pollutant_summary.csv`: station-by-pollutant annual and seasonal concentration summaries.
- `monthly_summary.csv`: station-by-pollutant monthly mean concentrations.
- `weekday_hour_patterns.csv`: average concentration by station, pollutant, weekday and hour.
- `daily_pm25.csv`: daily mean PM2.5 by station.
- `exceedance_counts.csv`: station-by-pollutant exceedance-day counts.
- `correlations.csv`: Spearman correlations between SA2-level interpolated exposure and SEIFA indexes.
- `sa2_exposure_seifa.geojson`: Greater Melbourne SA2 polygons with SEIFA attributes and IDW exposure estimates.

## Important fields

- `pollutant`: harmonised pollutant label.
- `annual_mean`, `monthly_mean`, `daily_mean`: average concentration over the named time window.
- `exceed_days`: number of days exceeding the threshold used in this project.
- `irsd_score`, `irsad_score`, `ier_score`, `ieo_score`: ABS SEIFA scores.
- `*_idw`: inverse-distance-weighted exposure estimate at SA2 level.
