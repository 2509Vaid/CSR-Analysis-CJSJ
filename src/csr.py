"""Shared data loading, cleaning, and measurement functions.

All paths are relative to the repository root, so run scripts from there:
    python src/analysis.py
    python src/figures.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "CSR_Report_2026-07-04.csv.gz"
POP_FILE = ROOT / "data" / "external" / "census2011_population.csv"
MPI_FILE = ROOT / "data" / "external" / "niti_mpi_2023_headcount.csv"

AMT = "Project Amount Spent (In INR Cr.)"
NONGEO = {"pan india", "pan india (other centralized funds)", "nec/not mentioned"}
TOP5 = ["maharashtra", "karnataka", "gujarat", "tamil nadu", "delhi"]
UTS = {"dnh&dd", "jammu and kashmir", "leh & ladakh", "chandigarh", "delhi",
       "andaman and nicobar", "lakshadweep", "puducherry"}
INDIA_POP_2011 = 1_210_854_977


def unit(state_key):
    """Map dataset regions to NITI Aayog MPI units (DNH and Daman & Diu merged in 2020)."""
    return "dnh&dd" if state_key in ("dadra and nagar haveli", "daman and diu") else state_key


def load_projects():
    """Load project records and normalize labels that differ only in case or spacing."""
    df = pd.read_csv(RAW)
    df["state"] = df["CSR State"].str.strip().str.lower()
    df["psu"] = df["PSU/Non-PSU"].str.strip().str.upper()          # 'NON-PSU' == 'Non-PSU'
    df["company"] = (df["Company Name"].str.upper()
                     .str.replace(r"\s+", " ", regex=True).str.strip())
    df["geo"] = ~df["state"].isin(NONGEO)
    return df


def load_population():
    pop = pd.read_csv(POP_FILE).set_index("state_key")["population_2011"]
    assert pop.sum() == INDIA_POP_2011, "State populations must sum to the 2011 national total"
    return pop


def load_mpi():
    return pd.read_csv(MPI_FILE).set_index("unit_key")["mpi_headcount_pct_2019_21"]


def gini(values, weights):
    """Population-weighted Gini: each resident receives their region's per-resident value."""
    order = np.argsort(values)
    x = np.asarray(values, float)[order]
    w = np.asarray(weights, float)[order]
    cw = np.r_[0, np.cumsum(w) / w.sum()]
    cx = np.r_[0, np.cumsum(x * w) / np.sum(x * w)]
    return 1 - np.sum((cw[1:] - cw[:-1]) * (cx[1:] + cx[:-1]))


def state_totals(df, pop):
    """State-assigned spending (INR crore) for all 37 regions, zero-filled."""
    return df[df.geo].groupby("state")[AMT].sum().reindex(pop.index, fill_value=0)


def unit_table(df, pop, mpi):
    """36 MPI units with total spending, population, per-resident spending, and MPI headcount."""
    st = state_totals(df, pop)
    u = pd.DataFrame({
        "crore": st.groupby(st.index.map(unit)).sum(),
        "pop": pop.groupby(pop.index.map(unit)).sum(),
    })
    u["per_resident_rs"] = u.crore * 1e7 / u["pop"]
    u["mpi"] = mpi
    assert len(u) == 36 and u.notna().all().all()
    return u


def spearman(u, drop=()):
    f = u.drop(index=[k for k in drop if k in u.index])
    return stats.spearmanr(f.per_resident_rs, f.mpi)


def summarize(df, pop, mpi, poor9):
    """Headline measures for any subset of project records."""
    st = state_totals(df, pop)
    assigned = st.sum()
    u = unit_table(df, pop, mpi)
    rho, p = spearman(u)
    return {
        "total_crore": df[AMT].sum(),
        "assigned_crore": assigned,
        "top5_share": st[TOP5].sum() / assigned,
        "gini": gini(st / pop, pop),
        "spearman_rho": rho,
        "spearman_p": p,
        "poor9_share": u.loc[poor9, "crore"].sum() / assigned,
        "bihar_per_resident_rs": u.loc["bihar", "per_resident_rs"],
    }
