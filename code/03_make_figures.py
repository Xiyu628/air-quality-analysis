"""Generate report figures from the local processed data files."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "tmp" / "matplotlib"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import AIR_XLSX, FIGURES_DIR, PROCESSED_DIR, ensure_output_dirs
from config import TARGET_POLLUTANTS
from config import require_raw_inputs


POLLUTANT_COLORS = {
    "PM2.5": "#D7263D",
    "PM10": "#F46036",
    "NO2": "#2E86AB",
    "O3": "#6A8E3F",
    "SO2": "#8E44AD",
    "CO": "#555555",
}


def clean_pollutant(value: object) -> str:
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


def savefig(name: str) -> Path:
    path = FIGURES_DIR / f"{name}.png"
    plt.tight_layout()
    plt.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close()
    return path


def ensure_air_derived_tables() -> None:
    monthly_path = PROCESSED_DIR / "monthly_summary.csv"
    daily_path = PROCESSED_DIR / "daily_pm25.csv"
    if monthly_path.exists() and daily_path.exists():
        return

    require_raw_inputs()
    print("Creating monthly_summary.csv and daily_pm25.csv from local AirWatch raw file...")
    columns = [
        "datetime_local",
        "location_name",
        "value",
        "validation_flag",
        "parameter_name",
    ]
    air = pd.read_excel(AIR_XLSX, sheet_name="AllData", usecols=columns)
    air["dt_local"] = pd.to_datetime(air["datetime_local"], errors="coerce")
    air["year"] = air["dt_local"].dt.year
    air["month"] = air["dt_local"].dt.month
    air["date"] = air["dt_local"].dt.date
    air["parameter"] = air["parameter_name"].map(clean_pollutant)
    air = air[
        (air["year"] == 2024)
        & (air["validation_flag"] == "Y")
        & (air["parameter"].isin(TARGET_POLLUTANTS))
    ].copy()

    monthly = (
        air.groupby(["location_name", "parameter", "month"])["value"]
        .mean()
        .reset_index()
        .rename(columns={"location_name": "station", "parameter": "pollutant", "value": "monthly_mean"})
    )
    monthly["monthly_mean"] = monthly["monthly_mean"].round(2)
    monthly.to_csv(monthly_path, index=False)

    daily_pm25 = (
        air[air["parameter"] == "PM2.5"]
        .groupby(["location_name", "date"])["value"]
        .mean()
        .reset_index()
        .rename(columns={"location_name": "station", "value": "daily_mean"})
    )
    daily_pm25["date"] = daily_pm25["date"].astype(str)
    daily_pm25["daily_mean"] = daily_pm25["daily_mean"].round(2)
    daily_pm25.to_csv(daily_path, index=False)


def figure_monthly_pm25_heatmap() -> Path:
    monthly = pd.read_csv(PROCESSED_DIR / "monthly_summary.csv")
    pm25 = monthly[monthly["pollutant"] == "PM2.5"].copy()
    pivot = pm25.pivot_table(index="station", columns="month", values="monthly_mean")
    order = pivot.mean(axis=1).sort_values(ascending=False).index
    pivot = pivot.loc[order, list(range(1, 13))]

    plt.figure(figsize=(10, 5.8))
    im = plt.imshow(pivot.values, aspect="auto", cmap="magma")
    plt.colorbar(im, label="Monthly mean PM2.5")
    plt.xticks(np.arange(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    plt.title("Monthly PM2.5 Patterns by Monitoring Station")
    plt.xlabel("Month in 2024")
    plt.ylabel("Station")
    return savefig("fig01_monthly_pm25_heatmap")


def figure_daily_pm25_timeseries() -> Path:
    daily = pd.read_csv(PROCESSED_DIR / "daily_pm25.csv", parse_dates=["date"])
    candidate_stations = ["Melbourne CBD", "Alphington", "Traralgon"]
    stations = [s for s in candidate_stations if s in set(daily["station"])]
    if not stations:
        stations = sorted(daily["station"].unique())[:3]

    plt.figure(figsize=(10.5, 4.8))
    for station in stations:
        sub = daily[daily["station"] == station].sort_values("date")
        rolling = sub["daily_mean"].rolling(30, min_periods=10, center=True).mean()
        plt.plot(sub["date"], rolling, label=station, linewidth=2)
    plt.axhline(25, color="#b2182b", linestyle="--", linewidth=1.2, label="PM2.5 daily threshold")
    plt.title("Daily PM2.5 Trend at Representative Stations")
    plt.xlabel("Date")
    plt.ylabel("30-day rolling mean PM2.5")
    plt.legend(frameon=False, ncol=2)
    return savefig("fig02_daily_pm25_timeseries")


def figure_weekday_hour_heatmap() -> Path:
    wh = pd.read_csv(PROCESSED_DIR / "weekday_hour_patterns.csv")
    station = "Melbourne CBD" if "Melbourne CBD" in set(wh["station"]) else wh["station"].iloc[0]
    sub = wh[(wh["station"] == station) & (wh["pollutant"] == "PM2.5")].copy()
    pivot = sub.pivot_table(index="weekday", columns="hour", values="mean_value")
    pivot = pivot.loc[[0, 1, 2, 3, 4, 5, 6]]

    plt.figure(figsize=(10, 3.8))
    im = plt.imshow(pivot.values, aspect="auto", cmap="inferno")
    plt.colorbar(im, label="Mean PM2.5")
    plt.xticks(np.arange(0, 24, 2), [str(x) for x in range(0, 24, 2)])
    plt.yticks(np.arange(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    plt.title(f"Weekday x Hour PM2.5 Fingerprint: {station}")
    plt.xlabel("Hour of day")
    plt.ylabel("Weekday")
    return savefig("fig03_weekday_hour_pm25")


def figure_exceedance_heatmap() -> Path:
    exc = pd.read_csv(PROCESSED_DIR / "exceedance_counts.csv")
    pivot = exc.pivot_table(index="station", columns="pollutant", values="exceed_days", fill_value=0)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    pollutants = [p for p in ["PM2.5", "PM10", "NO2", "O3", "SO2", "CO"] if p in pivot.columns]
    pivot = pivot[pollutants]

    plt.figure(figsize=(8.5, 5.5))
    im = plt.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    plt.colorbar(im, label="Exceedance days")
    plt.xticks(np.arange(len(pollutants)), pollutants)
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    plt.title("Exceedance Days by Station and Pollutant")
    plt.xlabel("Pollutant")
    plt.ylabel("Station")
    return savefig("fig04_exceedance_heatmap")


def figure_correlation_heatmap() -> Path:
    corr = pd.read_csv(PROCESSED_DIR / "correlations.csv")
    pivot = corr.pivot_table(index="pollutant", columns="seifa_index", values="spearman_rho")
    pivot = pivot.loc[[p for p in ["PM2.5", "PM10", "NO2", "O3"] if p in pivot.index]]
    pivot = pivot[[c for c in ["IRSD", "IRSAD", "IER", "IEO"] if c in pivot.columns]]

    plt.figure(figsize=(6.8, 4.4))
    im = plt.imshow(pivot.values, aspect="auto", cmap="RdBu_r", vmin=-0.7, vmax=0.7)
    plt.colorbar(im, label="Spearman rho")
    plt.xticks(np.arange(len(pivot.columns)), pivot.columns)
    plt.yticks(np.arange(len(pivot.index)), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.values[i, j]
            color = "white" if abs(value) > 0.35 else "black"
            plt.text(j, i, f"{value:.2f}", ha="center", va="center", color=color, fontweight="bold")
    plt.title("SA2 Exposure Estimates vs SEIFA Scores")
    return savefig("fig05_seifa_correlation_heatmap")


def figure_seifa_pm25_scatter() -> Path:
    with (PROCESSED_DIR / "sa2_exposure_seifa.geojson").open(encoding="utf-8") as f:
        geo = json.load(f)
    rows = [feature["properties"] for feature in geo["features"]]
    df = pd.DataFrame(rows)
    df = df[["irsd_score", "pm25_idw", "population"]].dropna()
    sizes = 12 + 80 * (df["population"] / df["population"].max()).clip(0, 1)

    plt.figure(figsize=(7.4, 5.2))
    plt.scatter(df["irsd_score"], df["pm25_idw"], s=sizes, alpha=0.45, color="#2E86AB", edgecolor="white", linewidth=0.4)
    z = np.polyfit(df["irsd_score"], df["pm25_idw"], 1)
    xs = np.linspace(df["irsd_score"].min(), df["irsd_score"].max(), 100)
    plt.plot(xs, z[0] * xs + z[1], color="#b2182b", linewidth=2, label="Linear trend")
    plt.title("Greater Melbourne SA2 PM2.5 Estimate vs IRSD Score")
    plt.xlabel("IRSD score (higher = less disadvantaged)")
    plt.ylabel("IDW-estimated annual mean PM2.5")
    plt.legend(frameon=False)
    return savefig("fig06_pm25_irsd_scatter")


def write_key_findings() -> None:
    corr = pd.read_csv(PROCESSED_DIR / "correlations.csv")
    exc = pd.read_csv(PROCESSED_DIR / "exceedance_counts.csv")
    top_exc = exc.sort_values("exceed_days", ascending=False).head(8)
    lines = [
        "# Key Findings",
        "",
        "## Highest exceedance counts",
        "",
    ]
    for _, row in top_exc.iterrows():
        lines.append(f"- {row['station']} / {row['pollutant']}: {int(row['exceed_days'])} exceedance days out of {int(row['total_days'])}.")
    lines += ["", "## Exposure-SEIFA correlations", ""]
    for _, row in corr.iterrows():
        lines.append(f"- {row['pollutant']} vs {row['seifa_index']}: rho = {row['spearman_rho']:.2f}, p = {row['p_value']}.")
    (FIGURES_DIR.parent / "outputs" / "key_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ensure_output_dirs()
    ensure_air_derived_tables()
    paths = [
        figure_monthly_pm25_heatmap(),
        figure_daily_pm25_timeseries(),
        figure_weekday_hour_heatmap(),
        figure_exceedance_heatmap(),
        figure_correlation_heatmap(),
        figure_seifa_pm25_scatter(),
    ]
    write_key_findings()
    print("Generated figures:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
