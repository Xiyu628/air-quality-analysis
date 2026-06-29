"""Build cleaned and analysis-ready data files from local raw inputs."""

from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr

from config import (
    AIR_XLSX,
    DATA_SOURCES,
    NEPM_THRESHOLDS,
    OUTPUTS_DIR,
    PROCESSED_DIR,
    PROJECT_ROOT,
    SA2_SHP,
    SEIFA_XLSX,
    SPATIAL_POLLUTANTS,
    TARGET_POLLUTANTS,
    ensure_output_dirs,
    require_raw_inputs,
)


def harmonise_pollutant_name(value: object) -> str:
    text = str(value).strip()
    upper = text.upper()
    if "PM2.5" in upper:
        return "PM2.5"
    if "PM10" in upper:
        return "PM10"
    if upper.startswith("NO2"):
        return "NO2"
    if upper.startswith("O3"):
        return "O3"
    if upper.startswith("SO2"):
        return "SO2"
    if upper.startswith("CO"):
        return "CO"
    return text


def idw(values: np.ndarray, source_xy: np.ndarray, target_xy: np.ndarray, power: float = 2.0) -> np.ndarray:
    distances = cdist(target_xy, source_xy)
    distances = np.maximum(distances, 1e-9)
    weights = 1.0 / distances**power
    return (weights @ values) / weights.sum(axis=1)


def read_and_clean_air_quality() -> tuple[pd.DataFrame, dict[str, object]]:
    raw = pd.read_excel(AIR_XLSX, sheet_name="AllData")
    stats: dict[str, object] = {
        "raw_rows": int(len(raw)),
        "raw_columns": int(raw.shape[1]),
    }

    air = raw.copy()
    air["dt_local"] = pd.to_datetime(air["datetime_local"], errors="coerce")
    air["dt_aest"] = pd.to_datetime(air["datetime_AEST"], errors="coerce")
    air["year"] = air["dt_local"].dt.year
    air["month"] = air["dt_local"].dt.month
    air["date"] = air["dt_local"].dt.date
    air["hour"] = air["dt_local"].dt.hour
    air["weekday"] = air["dt_local"].dt.dayofweek
    air["parameter"] = air["parameter_name"].map(harmonise_pollutant_name)

    air = air[(air["year"] == 2024) & air["parameter"].isin(TARGET_POLLUTANTS)].copy()
    stats["rows_2024_target_pollutants"] = int(len(air))
    stats["validation_flag_counts"] = air["validation_flag"].value_counts(dropna=False).to_dict()

    air = air[air["validation_flag"] == "Y"].copy()
    before_dedup = len(air)
    air = air.drop_duplicates(
        subset=["location_id", "datetime_local", "datetime_AEST", "parameter"]
    )
    stats["validated_rows_before_dedup"] = int(before_dedup)
    stats["validated_rows_after_dedup"] = int(len(air))
    stats["duplicate_rows_removed"] = int(before_dedup - len(air))

    season_map = {
        12: "summer",
        1: "summer",
        2: "summer",
        3: "autumn",
        4: "autumn",
        5: "autumn",
        6: "winter",
        7: "winter",
        8: "winter",
        9: "spring",
        10: "spring",
        11: "spring",
    }
    air["season"] = air["month"].map(season_map)
    return air, stats


def read_seifa() -> pd.DataFrame:
    seifa = pd.read_excel(SEIFA_XLSX, sheet_name="Table 1", skiprows=5)
    seifa = seifa.iloc[:, :11].copy()
    seifa.columns = [
        "sa2_code",
        "sa2_name",
        "irsd_score",
        "irsd_decile",
        "irsad_score",
        "irsad_decile",
        "ier_score",
        "ier_decile",
        "ieo_score",
        "ieo_decile",
        "population",
    ]
    seifa["sa2_code"] = seifa["sa2_code"].astype(str)
    seifa = seifa[seifa["sa2_code"].str.startswith("2")].copy()
    for col in seifa.columns[2:]:
        seifa[col] = pd.to_numeric(seifa[col], errors="coerce")
    return seifa


def build_spatial_tables(air: pd.DataFrame, seifa: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    sa2_all = gpd.read_file(SA2_SHP)
    sa2_vic = sa2_all[sa2_all["STE_NAME21"] == "Victoria"].copy()
    sa2_vic = sa2_vic.rename(
        columns={
            "SA2_CODE21": "sa2_code",
            "SA2_NAME21": "sa2_name",
            "SA3_NAME21": "sa3_name",
            "GCC_NAME21": "gcc_name",
            "AREASQKM21": "area_km2",
        }
    )[["sa2_code", "sa2_name", "sa3_name", "gcc_name", "area_km2", "geometry"]]
    sa2_vic["sa2_code"] = sa2_vic["sa2_code"].astype(str)
    sa2_vic = sa2_vic.merge(
        seifa[
            [
                "sa2_code",
                "irsd_score",
                "irsd_decile",
                "irsad_score",
                "irsad_decile",
                "ier_score",
                "ier_decile",
                "ieo_score",
                "ieo_decile",
                "population",
            ]
        ],
        on="sa2_code",
        how="left",
    )

    stations = (
        air.groupby("location_name")
        .agg(id=("location_id", "first"), lat=("latitude", "first"), lon=("longitude", "first"))
        .reset_index()
        .rename(columns={"location_name": "name"})
    )
    station_points = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations["lon"], stations["lat"]),
        crs=4326,
    )
    joined = gpd.sjoin(
        station_points,
        sa2_vic.to_crs(4326)[["sa2_code", "sa2_name", "gcc_name", "geometry"]],
        how="left",
        predicate="within",
    ).drop(columns="index_right")
    joined["gcc"] = joined["gcc_name"].fillna("Rest of Vic.")
    stations_out = joined[["id", "name", "lat", "lon", "sa2_code", "sa2_name", "gcc"]].copy()
    stations_out["type"] = np.where(stations_out["gcc"] == "Greater Melbourne", "metropolitan", "regional")
    return sa2_vic, stations_out


def build_aggregates(air: pd.DataFrame, stations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stations.to_csv(PROCESSED_DIR / "stations.csv", index=False)

    annual = (
        air.groupby(["location_name", "parameter"])
        .agg(
            annual_mean=("value", "mean"),
            annual_median=("value", "median"),
            annual_p95=("value", lambda x: x.quantile(0.95)),
            annual_max=("value", "max"),
            n_hours=("value", "count"),
        )
        .reset_index()
    )
    seasonal = (
        air.groupby(["location_name", "parameter", "season"])["value"]
        .mean()
        .reset_index()
        .pivot_table(index=["location_name", "parameter"], columns="season", values="value")
        .reset_index()
    )
    seasonal.columns.name = None
    seasonal = seasonal.rename(columns={s: f"{s}_mean" for s in ["autumn", "spring", "summer", "winter"]})
    summary = annual.merge(seasonal, on=["location_name", "parameter"], how="left")
    summary = summary.rename(columns={"location_name": "station", "parameter": "pollutant"}).round(2)
    summary.to_csv(PROCESSED_DIR / "station_pollutant_summary.csv", index=False)

    monthly = (
        air.groupby(["location_name", "parameter", "month"])["value"]
        .mean()
        .reset_index()
        .rename(columns={"location_name": "station", "parameter": "pollutant", "value": "monthly_mean"})
    )
    monthly["monthly_mean"] = monthly["monthly_mean"].round(2)
    monthly.to_csv(PROCESSED_DIR / "monthly_summary.csv", index=False)

    weekday_labels = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    wh = (
        air.groupby(["location_name", "parameter", "weekday", "hour"])["value"]
        .mean()
        .reset_index()
        .rename(columns={"location_name": "station", "parameter": "pollutant", "value": "mean_value"})
    )
    wh["mean_value"] = wh["mean_value"].round(2)
    wh["weekday_label"] = wh["weekday"].map(weekday_labels)
    wh.to_csv(PROCESSED_DIR / "weekday_hour_patterns.csv", index=False)

    daily_pm25 = (
        air[air["parameter"] == "PM2.5"]
        .groupby(["location_name", "date"])["value"]
        .mean()
        .reset_index()
        .rename(columns={"location_name": "station", "value": "daily_mean"})
    )
    daily_pm25["date"] = daily_pm25["date"].astype(str)
    daily_pm25["daily_mean"] = daily_pm25["daily_mean"].round(2)
    daily_pm25.to_csv(PROCESSED_DIR / "daily_pm25.csv", index=False)

    daily_pm = (
        air[air["parameter"].isin(["PM2.5", "PM10"])]
        .groupby(["location_name", "parameter", "date"])
        .agg(daily_mean=("value", "mean"), n_hours=("value", "count"))
        .reset_index()
    )
    daily_pm = daily_pm[daily_pm["n_hours"] >= 18].copy()
    daily_pm["threshold"] = daily_pm["parameter"].map(NEPM_THRESHOLDS)
    daily_pm["exceed"] = daily_pm["daily_mean"] > daily_pm["threshold"]
    exceed_pm = (
        daily_pm.groupby(["location_name", "parameter"])
        .agg(exceed_days=("exceed", "sum"), total_days=("date", "count"))
        .reset_index()
    )

    gas = air[air["parameter"].isin(["NO2", "O3", "SO2"])].copy()
    gas["threshold"] = gas["parameter"].map(NEPM_THRESHOLDS)
    gas["exceed"] = gas["value"] > gas["threshold"]
    gas_daily = gas.groupby(["location_name", "parameter", "date"])["exceed"].any().reset_index()
    exceed_gas = (
        gas_daily.groupby(["location_name", "parameter"])
        .agg(exceed_days=("exceed", "sum"), total_days=("date", "count"))
        .reset_index()
    )

    co = air[air["parameter"] == "CO"].copy()
    if not co.empty:
        co = co.sort_values(["location_name", "dt_local"])
        co["co_8h_mean"] = (
            co.groupby("location_name")["value"]
            .rolling(window=8, min_periods=6)
            .mean()
            .reset_index(level=0, drop=True)
        )
        co["exceed"] = co["co_8h_mean"] > NEPM_THRESHOLDS["CO"]
        co_daily = co.groupby(["location_name", "parameter", "date"])["exceed"].any().reset_index()
        exceed_co = (
            co_daily.groupby(["location_name", "parameter"])
            .agg(exceed_days=("exceed", "sum"), total_days=("date", "count"))
            .reset_index()
        )
    else:
        exceed_co = pd.DataFrame(columns=["location_name", "parameter", "exceed_days", "total_days"])

    exceed = pd.concat([exceed_pm, exceed_gas, exceed_co], ignore_index=True)
    exceed = exceed.rename(columns={"location_name": "station", "parameter": "pollutant"})
    exceed.to_csv(PROCESSED_DIR / "exceedance_counts.csv", index=False)
    return annual, summary


def build_sa2_exposure(
    sa2_vic: gpd.GeoDataFrame,
    stations: pd.DataFrame,
    annual: pd.DataFrame,
) -> gpd.GeoDataFrame:
    gm_sa2 = sa2_vic[sa2_vic["gcc_name"] == "Greater Melbourne"].copy()
    gm_stations = stations[stations["gcc"] == "Greater Melbourne"].copy()

    gm_sa2_proj = gm_sa2.to_crs(7855)
    centroids = gm_sa2_proj.geometry.centroid
    target_xy = np.c_[centroids.x.values, centroids.y.values]

    station_points = gpd.GeoDataFrame(
        gm_stations,
        geometry=gpd.points_from_xy(gm_stations["lon"], gm_stations["lat"]),
        crs=4326,
    ).to_crs(7855)
    source_xy = np.c_[station_points.geometry.x.values, station_points.geometry.y.values]

    for pollutant in SPATIAL_POLLUTANTS:
        station_values = annual[
            (annual["location_name"].isin(gm_stations["name"])) & (annual["parameter"] == pollutant)
        ].set_index("location_name")["annual_mean"]
        values = np.array([station_values.get(name, np.nan) for name in gm_stations["name"]])
        mask = ~np.isnan(values)
        if mask.sum() >= 3:
            column = pollutant.lower().replace(".", "") + "_idw"
            gm_sa2[column] = idw(values[mask], source_xy[mask], target_xy, power=2).round(2)

    idw_cols = [c for c in gm_sa2.columns if c.endswith("_idw")]
    export = gm_sa2.to_crs(4326).copy()
    export["geometry"] = export["geometry"].simplify(0.001, preserve_topology=True)
    keep_cols = [
        "sa2_code",
        "sa2_name",
        "sa3_name",
        "area_km2",
        "irsd_score",
        "irsd_decile",
        "irsad_score",
        "irsad_decile",
        "ier_score",
        "ier_decile",
        "ieo_score",
        "ieo_decile",
        "population",
    ] + idw_cols + ["geometry"]
    export = export[keep_cols]
    for column in export.select_dtypes(include=[np.number]).columns:
        export[column] = export[column].round(2)
    out_file = PROCESSED_DIR / "sa2_exposure_seifa.geojson"
    if out_file.exists():
        out_file.unlink()
    export.to_file(out_file, driver="GeoJSON")
    return export


def build_correlations(sa2_exposure: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    pollutant_cols = [
        ("pm25_idw", "PM2.5"),
        ("pm10_idw", "PM10"),
        ("no2_idw", "NO2"),
        ("o3_idw", "O3"),
    ]
    seifa_cols = [
        ("irsd_score", "IRSD"),
        ("irsad_score", "IRSAD"),
        ("ier_score", "IER"),
        ("ieo_score", "IEO"),
    ]
    for pcol, pollutant in pollutant_cols:
        if pcol not in sa2_exposure.columns:
            continue
        for scol, seifa_name in seifa_cols:
            valid = sa2_exposure[[pcol, scol]].dropna()
            if len(valid) > 10:
                rho, p_value = spearmanr(valid[pcol], valid[scol])
                rows.append(
                    {
                        "pollutant": pollutant,
                        "seifa_index": seifa_name,
                        "spearman_rho": round(float(rho), 4),
                        "p_value": round(float(p_value), 6),
                        "n_sa2": int(len(valid)),
                    }
                )
    corr = pd.DataFrame(rows)
    corr.to_csv(PROCESSED_DIR / "correlations.csv", index=False)
    return corr


def write_documentation(stats: dict[str, object]) -> None:
    data_dictionary = """# Data Dictionary

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
"""
    (OUTPUTS_DIR / "data_dictionary.md").write_text(data_dictionary, encoding="utf-8")

    quality = [
        "# Quality Checks",
        "",
        f"- Raw AirWatch rows: {stats['raw_rows']:,}",
        f"- Raw AirWatch columns: {stats['raw_columns']:,}",
        f"- Rows in 2024 target pollutants: {stats['rows_2024_target_pollutants']:,}",
        f"- Validated rows before deduplication: {stats['validated_rows_before_dedup']:,}",
        f"- Validated rows after deduplication: {stats['validated_rows_after_dedup']:,}",
        f"- Duplicate rows removed: {stats['duplicate_rows_removed']:,}",
        "",
        "Validation-flag counts before filtering:",
    ]
    for key, value in stats["validation_flag_counts"].items():
        quality.append(f"- `{key}`: {value:,}")
    (OUTPUTS_DIR / "quality_checks.md").write_text("\n".join(quality) + "\n", encoding="utf-8")

    sources = ["# Data Sources", ""]
    for name, info in DATA_SOURCES.items():
        local = info["local_file"].relative_to(PROJECT_ROOT)
        sources.append(f"- {name}: {info['url']}")
        sources.append(f"  - Local file expected at: `{local}`")
    (OUTPUTS_DIR / "data_sources.md").write_text("\n".join(sources) + "\n", encoding="utf-8")

    summary = {
        "processed_files": sorted(p.name for p in PROCESSED_DIR.glob("*") if p.is_file()),
        "quality_stats": stats,
    }
    (OUTPUTS_DIR / "processing_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    ensure_output_dirs()
    require_raw_inputs()
    print("Building processed data from local raw files...")
    air, stats = read_and_clean_air_quality()
    seifa = read_seifa()
    sa2_vic, stations = build_spatial_tables(air, seifa)
    annual, _summary = build_aggregates(air, stations)
    sa2_exposure = build_sa2_exposure(sa2_vic, stations, annual)
    build_correlations(sa2_exposure)
    write_documentation(stats)
    print("Processed data written to:", PROCESSED_DIR)
    print("Documentation written to:", OUTPUTS_DIR)


if __name__ == "__main__":
    main()
