"""Reproduce every number in the analysis and write result tables to results/.

Usage (from the repository root):
    python src/analysis.py
"""
import numpy as np
import pandas as pd
from scipy import stats

from csr import (AMT, NONGEO, ROOT, TOP5, UTS, gini, load_mpi, load_population,
                 load_projects, spearman, state_totals, summarize, unit_table)

OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
lines = []


def log(text=""):
    print(text)
    lines.append(text)


df = load_projects()
pop = load_population()
mpi = load_mpi()

# ---------------------------------------------------------------- data overview
log("== Data and cleaning")
log(f"Records: {len(df):,}")
log(f"Company-name strings: {df['Company Name'].nunique():,} -> {df.company.nunique():,} after normalizing case/spacing")
log(f"State labels: {df['CSR State'].nunique()} -> {df.state.nunique()} after lower-casing "
    f"({df.state.nunique() - len(NONGEO)} geographic regions + {len(NONGEO)} non-geographic)")
log(f"Zero-amount records: {(df[AMT] == 0).sum():,} ({(df[AMT] == 0).mean():.1%}); "
    f"negative records: {(df[AMT] < 0).sum()} totaling {df.loc[df[AMT] < 0, AMT].sum():.2f} crore")

T = df[AMT].sum()
st = state_totals(df, pop)
A = st.sum()
log(f"Total spending: {T:,.2f} crore; state-assigned: {A:,.2f}; not assigned: {T - A:,.2f} ({(T - A) / T:.1%})")
for k in sorted(NONGEO):
    s = df.loc[df.state == k, AMT].sum()
    log(f"   {k}: {s:,.2f} crore ({s / T:.1%})")

# ---------------------------------------------------------------- regional table
reg = pd.DataFrame({"crore": st, "population_2011": pop})
reg["share_of_assigned_pct"] = reg.crore / A * 100
reg["per_resident_rs"] = reg.crore * 1e7 / reg.population_2011
reg = reg.sort_values("crore", ascending=False)
reg.round(3).to_csv(OUT / "regional_summary.csv", index_label="state_key")

log("\n== Concentration")
log(f"Top five ({', '.join(TOP5)}): {reg.loc[TOP5, 'crore'].sum():,.0f} crore = "
    f"{reg.loc[TOP5, 'crore'].sum() / A:.1%} of assigned spending, "
    f"{reg.loc[TOP5, 'population_2011'].sum() / pop.sum():.1%} of population")
nat = A * 1e7 / pop.sum()
below = reg[reg.per_resident_rs < nat]
log(f"National average: Rs {nat:,.0f} per resident; {len(below)} regions below it hold "
    f"{below.population_2011.sum() / pop.sum():.1%} of population and received {below.crore.sum() / A:.1%}")
log(f"Gini (ten-year, 37 regions): {gini(st / pop, pop):.3f}")

# ---------------------------------------------------------------- over time
fy = df.groupby("Financial Year")[AMT].sum()
g = df[df.geo]
annual = pd.DataFrame({"total_crore": fy})
annual["assigned_crore"] = g.groupby("Financial Year")[AMT].sum()
annual["unassigned_pct"] = (1 - annual.assigned_crore / annual.total_crore) * 100
annual["top5_share_pct"] = (g[g.state.isin(TOP5)].groupby("Financial Year")[AMT].sum()
                            / annual.assigned_crore * 100)
annual["gini"] = [gini(state_totals(d, pop) / pop, pop) for _, d in df.groupby("Financial Year")]
annual["yoy_growth_pct"] = fy.pct_change() * 100
annual.round(3).to_csv(OUT / "annual_summary.csv")
log("\n== Change over time")
log(annual.round(2).to_string())
log(f"Growth FY 2014-15 to FY 2023-24: {fy.iloc[-1] / fy.iloc[0] - 1:.1%}; "
    f"CAGR {(fy.iloc[-1] / fy.iloc[0]) ** (1 / 9) - 1:.1%}")

# ---------------------------------------------------------------- poverty test
u = unit_table(df, pop, mpi)
u.round(3).to_csv(OUT / "poverty_units.csv", index_label="unit_key")
rho, p = spearman(u)
rng = np.random.default_rng(0)
boot = []
for _ in range(5000):
    i = rng.integers(0, len(u), len(u))
    boot.append(stats.spearmanr(u.per_resident_rs.values[i], u.mpi.values[i])[0])
lo, hi = np.percentile(boot, [2.5, 97.5])
log("\n== Spending and multidimensional poverty (36 units)")
log(f"Spearman rho = {rho:.3f}, p = {p:.4f}, 95% bootstrap CI [{lo:.2f}, {hi:.2f}]")

recent = df[df["Financial Year"].isin(["FY 2019-20", "FY 2020-21", "FY 2021-22", "FY 2022-23", "FY 2023-24"])]
small = set(u.index[u["pop"] < 1_000_000])
checks = {
    "States only (n=28)": spearman(u, UTS),
    "Excluding Delhi": spearman(u, {"delhi"}),
    "Excluding units < 1M residents": spearman(u, small),
    "FY 2019-20 to 2023-24 spending": spearman(unit_table(recent, pop, mpi)),
}
for label, (r_, p_) in checks.items():
    log(f"   {label}: rho = {r_:.3f}, p = {p_:.4f}")
t = stats.kendalltau(u.per_resident_rs, u.mpi)
log(f"   Kendall tau = {t[0]:.3f}, p = {t[1]:.4f}")
loo = [spearman(u, {k}) for k in u.index]
log(f"   Leave-one-out: rho {min(x[0] for x in loo):.3f} to {max(x[0] for x in loo):.3f}; "
    f"p > 0.05 in {sum(x[1] > 0.05 for x in loo)} of {len(loo)} (max p {max(x[1] for x in loo):.3f})")

q = u.sort_values("mpi", ascending=False)
poor9 = list(q.index[:9])
for label, part in [("Nine highest-poverty units", q.head(9)), ("Nine lowest-poverty units", q.tail(9))]:
    log(f"{label}: {part['pop'].sum() / u['pop'].sum():.1%} of population, "
        f"{part.crore.sum() / u.crore.sum():.1%} of assigned spending")

# ---------------------------------------------------------------- subgroups
log("\n== PSU vs non-PSU, and excluding the ten largest spenders")
top10 = df.groupby("company")[AMT].sum().sort_values(ascending=False).head(10)
log(f"Ten largest spenders ({top10.sum() / T:.1%} of all spending): {', '.join(top10.index.str.title())}")
subsets = {
    "All": df,
    "PSU": df[df.psu == "PSU"],
    "Non-PSU": df[df.psu == "NON-PSU"],
    "Excluding ten largest": df[~df.company.isin(top10.index)],
}
sub = pd.DataFrame({k: summarize(d, pop, mpi, poor9) for k, d in subsets.items()}).T
sub.round(4).to_csv(OUT / "subgroup_summary.csv", index_label="subset")
log(sub.round(3).to_string())
for grp in ["PSU", "NON-PSU"]:
    s = state_totals(df[df.psu == grp], pop)
    log(f"{grp} top destinations: " + ", ".join(f"{k.title()} {v:.1%}" for k, v in (s / s.sum()).nlargest(5).items()))


# ---------------------------------------------------------------- Finance Commission benchmark
fc = pd.read_csv(ROOT / "data" / "external" / "fc15_devolution_shares_2021_26.csv").set_index("state_key")["fc15_share_pct_2021_26"]
assert abs(fc.sum() - 100) < 1e-6 and len(fc) == 28


def dissim(a, b):
    """Dissimilarity index: % of the total that must move for distribution a to match b."""
    return 0.5 * np.abs(a - b).sum()


s28 = state_totals(df, pop)[fc.index]
csr_sh = s28 / s28.sum() * 100
pop_sh = pop[fc.index] / pop[fc.index].sum() * 100
log("\n== Benchmark: Fifteenth Finance Commission devolution shares (28 states)")
log(f"28 states' share of assigned spending: {s28.sum() / A:.1%}")
log(f"Spearman, CSR share vs FC share: rho = {stats.spearmanr(csr_sh, fc)[0]:.2f}")
log(f"Dissimilarity: CSR vs FC {dissim(csr_sh, fc):.1f}%; CSR vs population {dissim(csr_sh, pop_sh):.1f}%; "
    f"FC vs population {dissim(fc, pop_sh):.1f}%")
log(f"States receiving less than their FC share: {(csr_sh < fc).sum()} of 28")
for k in ["bihar", "uttar pradesh", "maharashtra"]:
    log(f"   {k.title()}: actual {s28[k]:,.0f} crore; if divided by FC shares {fc[k] / 100 * s28.sum():,.0f} crore")
for grp in ["PSU", "NON-PSU"]:
    sg = state_totals(df[df.psu == grp], pop)[fc.index]
    log(f"   {grp}: dissimilarity vs FC {dissim(sg / sg.sum() * 100, fc):.1f}%")
bench = pd.DataFrame({"csr_share_pct": csr_sh, "fc15_share_pct": fc, "population_share_pct": pop_sh,
                      "csr_crore": s28, "csr_crore_if_fc_shares": fc / 100 * s28.sum()})
bench.round(3).to_csv(OUT / "finance_commission_benchmark.csv", index_label="state_key")

(OUT / "results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nWrote results to {OUT}")
