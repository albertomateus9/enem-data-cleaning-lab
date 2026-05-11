from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_SAMPLE = ROOT / "data" / "sample" / "sample.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
CHARTS = ROOT / "charts"
REPORTS = ROOT / "reports"

PROJECT = {
  "code": "P01",
  "slug": "enem-data-cleaning-lab",
  "title": "Laboratorio De Limpeza De Dados Do ENEM",
  "discipline": "Armazenamento, Manipulacao E Transformacao De Dados I",
  "disciplinePt": "Armazenamento, Manipulacao E Transformacao De Dados I",
  "kind": "cleaning",
  "dataset": "Amostra segura local",
  "source": "Amostra sintetica local",
  "description": "Limpeza de dados estilo ENEM com pandas, tratamento de nulos, padronizacao e exportacao segura.",
  "topics": [
    "data-science",
    "python",
    "jupyter-notebook",
    "education-technology",
    "eetepa",
    "enem",
    "data-cleaning",
    "pandas",
    "portugues-brasil",
    "educacao-tecnologica",
    "ciencia-de-dados"
  ]
}

def ensure_dirs() -> None:
    for directory in (DATA_PROCESSED, CHARTS, REPORTS):
        directory.mkdir(parents=True, exist_ok=True)


def read_sample() -> pd.DataFrame:
    if DATA_SAMPLE.suffix == ".json":
        with DATA_SAMPLE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if PROJECT["kind"] == "json_normalize":
            return pd.json_normalize(payload, sep="_")
        return pd.DataFrame(payload)
    return pd.read_csv(DATA_SAMPLE)


def save_dataframe(df: pd.DataFrame, filename: str) -> str:
    ensure_dirs()
    path = DATA_PROCESSED / filename
    df.to_csv(path, index=False)
    return str(path.relative_to(ROOT))


def save_chart(filename: str) -> str:
    ensure_dirs()
    path = CHARTS / filename
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()
    return str(path.relative_to(ROOT))


def run_cleaning() -> dict:
    df = read_sample()
    cleaned = df.drop(columns=["COLUMN_UNUSED"], errors="ignore").rename(columns=str.lower)
    for column in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[column]):
            cleaned[column] = cleaned[column].fillna(cleaned[column].median())
        else:
            cleaned[column] = cleaned[column].fillna("nao_informado")
    return {"rows": len(cleaned), "outputs": [save_dataframe(cleaned, "enem_clean_sample.csv")]}


def run_sqlite() -> dict:
    df = read_sample()
    ensure_dirs()
    db_path = DATA_PROCESSED / "movies_sample.db"
    with sqlite3.connect(db_path) as connection:
        df.to_sql("movies", connection, if_exists="replace", index=False)
        query = pd.read_sql_query(
            "SELECT genre, COUNT(*) AS total_movies, ROUND(AVG(vote_average), 2) AS avg_vote FROM movies GROUP BY genre",
            connection,
        )
    return {"rows": len(df), "outputs": [str(db_path.relative_to(ROOT)), save_dataframe(query, "genre_summary.csv")]}


def run_json_normalize() -> dict:
    df = read_sample()
    return {"rows": len(df), "outputs": [save_dataframe(df, "ibge_municipalities_normalized.csv")]}


def run_tidy_prices() -> dict:
    df = read_sample()
    tidy = df.melt(id_vars=["product", "market"], var_name="month", value_name="price")
    tidy["pct_variation"] = tidy.groupby(["product", "market"])["price"].pct_change().fillna(0).round(4)
    return {"rows": len(tidy), "outputs": [save_dataframe(tidy, "prices_tidy.csv")]}


def run_quality_audit() -> dict:
    df = read_sample()
    report = pd.DataFrame({
        "column": df.columns,
        "missing": [int(df[column].isna().sum()) for column in df.columns],
        "dtype": [str(df[column].dtype) for column in df.columns],
    })
    duplicate_rows = int(df.duplicated().sum())
    html = "<h1>Relatório De Qualidade De Dados</h1>" + report.to_html(index=False) + f"<p>Linhas duplicadas: {duplicate_rows}</p>"
    ensure_dirs()
    html_path = REPORTS / "quality_report.html"
    html_path.write_text(html, encoding="utf-8")
    return {"rows": len(df), "duplicates": duplicate_rows, "outputs": [save_dataframe(report, "quality_summary.csv"), str(html_path.relative_to(ROOT))]}


def classify_imc(value: float) -> str:
    if value < 18.5:
        return "abaixo_da_referencia"
    if value < 25:
        return "referencia"
    if value < 30:
        return "atencao"
    return "high_atencao"


def run_imc() -> dict:
    df = read_sample()
    df["imc"] = (df["weight_kg"] / (df["height_m"] ** 2)).round(2)
    df["classification"] = df["imc"].apply(classify_imc)
    return {"rows": len(df), "outputs": [save_dataframe(df, "imc_classification.csv")]}


def sieve(limit: int) -> list[int]:
    flags = [True] * (limit + 1)
    flags[0:2] = [False, False]
    for number in range(2, int(math.sqrt(limit)) + 1):
        if flags[number]:
            for multiple in range(number * number, limit + 1, number):
                flags[multiple] = False
    return [number for number, prime in enumerate(flags) if prime]


def run_primes() -> dict:
    base = 7
    table = pd.DataFrame({"multiplier": list(range(1, 11)), "result": [base * n for n in range(1, 11)]})
    primes = pd.DataFrame({"prime": sieve(80)})
    return {"rows": len(table) + len(primes), "outputs": [save_dataframe(table, "times_table.csv"), save_dataframe(primes, "primes_until_80.csv")]}


def run_registry() -> dict:
    df = read_sample()
    new_record = pd.DataFrame([{"registry_id": "S004", "name": "Student Delta", "course": "Data Science", "status": "active"}])
    updated = pd.concat([df, new_record], ignore_index=True).drop_duplicates("registry_id")
    active = updated[updated["status"] == "active"]
    return {"rows": len(updated), "active": len(active), "outputs": [save_dataframe(updated, "registry_updated.csv")]}


def run_quiz() -> dict:
    questions = json.loads(DATA_SAMPLE.read_text(encoding="utf-8"))
    random.seed(42)
    rows = []
    for item in questions:
        options = item["options"][:]
        random.shuffle(options)
        rows.append({"question": item["question"], "answer": item["answer"], "options": " | ".join(options), "points": 1})
    result = pd.DataFrame(rows)
    return {"rows": len(result), "score_referencia": int(result["points"].sum()), "outputs": [save_dataframe(result, "quiz_referencia.csv")]}


def run_dice() -> dict:
    random.seed(42)
    rolls = [random.randint(1, 6) for _ in range(600)]
    df = pd.DataFrame({"roll": rolls})
    freq = df["roll"].value_counts(normalize=True).sort_index().reset_index()
    freq.columns = ["face", "relative_frequency"]
    plt.figure(figsize=(7, 4))
    plt.bar(freq["face"], freq["relative_frequency"])
    plt.axhline(1 / 6, color="black", linestyle="--", label="esperado 1/6")
    plt.legend()
    return {"rows": len(df), "outputs": [save_dataframe(freq, "dice_frequency.csv"), save_chart("dice_frequency.png")]}


def run_deforestation() -> dict:
    df = read_sample()
    pivot = df.pivot(index="year", columns="state", values="area_km2")
    pivot.plot(marker="o", figsize=(7, 4), title="Amostra sintética de desmatamento")
    return {"rows": len(df), "outputs": [save_dataframe(pivot.reset_index(), "deforestation_pivot.csv"), save_chart("deforestation_series.png")]}


def run_idh() -> dict:
    df = read_sample()
    plt.figure(figsize=(7, 4))
    plt.scatter(df["income"], df["idh"])
    for _, row in df.iterrows():
        plt.annotate(row["municipality"], (row["income"], row["idh"]), fontsize=8)
    plt.xlabel("Income sample")
    plt.ylabel("IDH sample")
    return {"rows": len(df), "outputs": [save_dataframe(df, "idh_sample_processed.csv"), save_chart("idh_income_scatter.png")]}


def run_temperature() -> dict:
    df = read_sample()
    df["rolling_mean"] = df["anomaly_c"].rolling(3, min_periods=1).mean().round(3)
    df.plot(x="year", y=["anomaly_c", "rolling_mean"], marker="o", figsize=(7, 4), title="NASA GISS-style anomaly sample")
    plt.axhline(0, color="black", linewidth=0.8)
    return {"rows": len(df), "outputs": [save_dataframe(df, "temperature_anomaly_processed.csv"), save_chart("temperature_dashboard.png")]}


def run_energy() -> dict:
    df = read_sample()
    pivot = df.pivot(index="year", columns="source", values="share")
    pivot.plot(kind="bar", stacked=True, figsize=(7, 4), title="Brazil energy matrix sample")
    return {"rows": len(df), "outputs": [save_dataframe(pivot.reset_index(), "energy_matrix_pivot.csv"), save_chart("energy_matrix.png")]}


def run_air_quality() -> dict:
    df = read_sample()
    pivot = df.pivot_table(index="weekday", columns="hour", values="pm25", aggfunc="mean")
    plt.figure(figsize=(6, 4))
    plt.imshow(pivot, aspect="auto")
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.colorbar(label="PM2.5 sample")
    return {"rows": len(df), "outputs": [save_dataframe(pivot.reset_index(), "air_quality_heatmap_table.csv"), save_chart("air_quality_heatmap.png")]}


def run_carbon() -> dict:
    df = read_sample()
    df["estimated_kg_co2"] = (df["cell_hours"] * 0.03 + df["computer_hours"] * 0.06 + df["streaming_hours"] * 0.08).round(3)
    df = df.sort_values("estimated_kg_co2")
    df.plot(kind="barh", x="group", y="estimated_kg_co2", figsize=(7, 4), legend=False, title="Digital carbon footprint sample")
    return {"rows": len(df), "outputs": [save_dataframe(df, "carbon_footprint_sample.csv"), save_chart("carbon_footprint.png")]}


def run_sdg() -> dict:
    df = read_sample()
    angles = [n / float(len(df)) * 2 * math.pi for n in range(len(df))]
    angles += angles[:1]
    plt.figure(figsize=(6, 6))
    axis = plt.subplot(111, polar=True)
    for column in ("north", "south"):
        values = df[column].tolist() + df[column].tolist()[:1]
        axis.plot(angles, values, label=column)
        axis.fill(angles, values, alpha=0.1)
    axis.set_xticks(angles[:-1])
    axis.set_xticklabels(df["goal"].tolist())
    axis.legend(loc="upper right")
    return {"rows": len(df), "outputs": [save_dataframe(df, "sdg_radar_sample.csv"), save_chart("sdg_radar.png")]}


def run_fires() -> dict:
    df = read_sample()
    df["fire_rain_corr_ready"] = df["fire_spots"].corr(df["rainfall_mm"]).round(4)
    df.plot(x="month", y=["fire_spots", "rainfall_mm"], marker="o", figsize=(8, 4), title="Fire spots and rainfall sample")
    plt.xticks(rotation=45)
    return {"rows": len(df), "correlation": float(df["fire_spots"].corr(df["rainfall_mm"])), "outputs": [save_dataframe(df, "fire_seasonality.csv"), save_chart("fire_seasonality.png")]}


def run_timeline() -> dict:
    df = read_sample()
    plt.figure(figsize=(8, 4))
    plt.scatter(df["year"], [1] * len(df))
    for _, row in df.iterrows():
        plt.annotate(row["label"], (row["year"], 1), rotation=35, fontsize=8)
    plt.yticks([])
    plt.title("Digital transformation timeline sample")
    return {"rows": len(df), "outputs": [save_dataframe(df, "timeline_processed.csv"), save_chart("digital_timeline.png")]}


def run_observatory() -> dict:
    df = read_sample()
    ensure_dirs()
    db_path = DATA_PROCESSED / "observatory_sample.db"
    with sqlite3.connect(db_path) as connection:
        df.to_sql("indicators", connection, if_exists="replace", index=False)
        summary = pd.read_sql_query("SELECT source, COUNT(*) AS indicators FROM indicators GROUP BY source", connection)
    df.plot(kind="bar", x="indicator", y="value", figsize=(8, 4), legend=False, title="COP30 Para observatory sample")
    plt.xticks(rotation=35, ha="right")
    return {"rows": len(df), "outputs": [str(db_path.relative_to(ROOT)), save_dataframe(summary, "observatory_source_summary.csv"), save_chart("observatory_indicators.png")]}


RUNNERS = {
    "cleaning": run_cleaning,
    "sqlite": run_sqlite,
    "json_normalize": run_json_normalize,
    "tidy_prices": run_tidy_prices,
    "quality_audit": run_quality_audit,
    "imc": run_imc,
    "primes": run_primes,
    "registry": run_registry,
    "quiz": run_quiz,
    "dice": run_dice,
    "deforestation": run_deforestation,
    "idh": run_idh,
    "temperature": run_temperature,
    "energy": run_energy,
    "air_quality": run_air_quality,
    "carbon": run_carbon,
    "sdg": run_sdg,
    "fires": run_fires,
    "timeline": run_timeline,
    "observatory": run_observatory,
}


def run_sample() -> dict:
    result = RUNNERS[PROJECT["kind"]]()
    result["project"] = PROJECT["slug"]
    result["code"] = PROJECT["code"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=PROJECT["description"])
    parser.add_argument("--sample", action="store_true", help="Run the safe sample workflow.")
    args = parser.parse_args()
    if not args.sample:
        print("No external data workflow is enabled by default. Re-run with --sample.")
        return
    print(json.dumps(run_sample(), indent=2))


if __name__ == "__main__":
    main()
