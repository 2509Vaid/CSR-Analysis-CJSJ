"""Draw the three figures and save them to figures/.

Usage (from the repository root):
    python src/figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy import stats

from csr import AMT, ROOT, TOP5, load_mpi, load_population, load_projects, state_totals, unit_table

OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
# Times New Roman to match the manuscript; Liberation Serif is its metric-compatible substitute.
plt.rcParams.update({"font.family": ["Times New Roman", "Liberation Serif", "DejaVu Serif"], "font.size": 7})
BLUE, ORANGE, GREY, LIGHT = "#1f4e79", "#c55a11", "#a6a6a6", "#bdd7ee"
comma = FuncFormatter(lambda v, _: f"{v:,.0f}")

df = load_projects()
pop = load_population()
mpi = load_mpi()
st = state_totals(df, pop)
nat = st.sum() * 1e7 / pop.sum()

# ---------------------------------------------------------------- Figure 1
pc = (st * 1e7 / pop).sort_values()
names = {"andaman and nicobar": "Andaman & Nicobar", "dadra and nagar haveli": "Dadra & Nagar Haveli",
         "daman and diu": "Daman & Diu", "jammu and kashmir": "Jammu & Kashmir", "leh & ladakh": "Ladakh"}
highlight = {"bihar", "jharkhand", "uttar pradesh"}
fig, ax = plt.subplots(figsize=(3.4, 4.6), dpi=300)
colors = [BLUE if k in TOP5 else ORANGE if k in highlight else GREY for k in pc.index]
ax.barh(range(len(pc)), pc.values, color=colors, height=0.72)
ax.set_yticks(range(len(pc)))
ax.set_yticklabels([names.get(k, k.title()) for k in pc.index], fontsize=5.6)
for i, v in enumerate(pc.values):
    ax.text(v + 50, i, f"{v:,.0f}", va="center", fontsize=5.3,
            bbox=dict(fc="white", ec="none", pad=0.3), zorder=3)
ax.axvline(nat, ls="--", lw=0.8, color="k", zorder=0)
ax.text(nat + 80, 0.6, f"National average ₹{nat:,.0f}", fontsize=5.5)
ax.set_xlabel("CSR spending per resident, FY 2014–15 to 2023–24\n(₹, nominal; Census 2011 population)")
ax.set_xlim(0, 6100)
ax.xaxis.set_major_formatter(comma)
ax.spines[["top", "right"]].set_visible(False)
ax.margins(y=0.01)
ax.legend(handles=[Patch(color=BLUE, label="Five largest recipients by total"),
                   Patch(color=ORANGE, label="Bihar, Jharkhand, Uttar Pradesh"),
                   Patch(color=GREY, label="Other regions")],
          loc="lower right", bbox_to_anchor=(1.0, 0.10), fontsize=5.5, frameon=False)
fig.tight_layout()
fig.savefig(OUT / "figure1_per_resident.png")
plt.close(fig)

# ---------------------------------------------------------------- Figure 2
fy = df.groupby("Financial Year")[AMT].sum()
ga = df[df.geo].groupby("Financial Year")[AMT].sum()
t5 = df[df.geo & df.state.isin(TOP5)].groupby("Financial Year")[AMT].sum() / ga * 100
x = [s.replace("FY ", "").replace("20", "", 1) for s in fy.index]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(3.4, 3.6), dpi=300,
                             gridspec_kw={"height_ratios": [1.5, 1]}, sharex=True)
a1.bar(x, ga / 1000, color=BLUE, label="Assigned to a state/UT")
a1.bar(x, (fy - ga) / 1000, bottom=ga / 1000, color=LIGHT, label="PAN India, centralized funds, not mentioned")
for i, v in enumerate(fy):
    a1.text(i, v / 1000 + 0.4, f"{v / 1000:.1f}", ha="center", fontsize=5.3)
a1.set_ylabel("₹ thousand crore (nominal)")
a1.legend(fontsize=5.3, frameon=False, loc="upper left")
a1.set_ylim(0, 39)
a1.text(-0.2, 1.0, "(a)", transform=a1.transAxes, fontsize=7, fontweight="bold")
a2.plot(x, t5, marker="o", ms=2.5, color=BLUE, lw=1)
for i, v in enumerate(t5):
    a2.text(i, v + 1.4, f"{v:.0f}", ha="center", fontsize=5.3)
a2.set_ylim(40, 65)
a2.set_ylabel("Top-five share (%)")
a2.set_xlabel("Financial year")
a2.text(-0.2, 1.0, "(b)", transform=a2.transAxes, fontsize=7, fontweight="bold")
for a in (a1, a2):
    a.spines[["top", "right"]].set_visible(False)
plt.setp(a2.get_xticklabels(), rotation=45, ha="right")
fig.tight_layout()
fig.savefig(OUT / "figure2_annual.png")
plt.close(fig)

# ---------------------------------------------------------------- Figure 3
u = unit_table(df, pop, mpi)
rho, p = stats.spearmanr(u.per_resident_rs, u.mpi)
fig, ax = plt.subplots(figsize=(3.4, 2.8), dpi=300)
ax.scatter(u.mpi, u.per_resident_rs, s=12, color=BLUE, zorder=3)
ax.set_yscale("log")
ax.set_ylim(80, 8000)
ax.yaxis.set_major_formatter(comma)
labels = {"bihar": ("Bihar", -4, 6, "right"), "jharkhand": ("Jharkhand", 4, 3, "left"),
          "meghalaya": ("Meghalaya", 0, -10, "center"), "uttar pradesh": ("Uttar Pradesh", 4, -7, "left"),
          "madhya pradesh": ("Madhya Pradesh", 0, 5, "center"), "delhi": ("Delhi", 4, 0, "left"),
          "maharashtra": ("Maharashtra", 4, 0, "left"), "kerala": ("Kerala", 4, -7, "left"),
          "goa": ("Goa", 4, 0, "left"), "tripura": ("Tripura", 4, -3, "left"),
          "dnh&dd": ("DNH & DD", 4, 0, "left"), "odisha": ("Odisha", 4, 2, "left")}
for k, (t, dx, dy, ha) in labels.items():
    ax.annotate(t, (u.loc[k, "mpi"], u.loc[k, "per_resident_rs"]), xytext=(dx, dy),
                textcoords="offset points", fontsize=5.5, ha=ha)
ax.axhline(nat, ls="--", lw=0.7, color="k", zorder=0)
ax.text(35, nat * 1.08, f"National average ₹{nat:,.0f}", fontsize=5.5, ha="right")
ax.text(35, 6000, f"Spearman ρ = {rho:.2f}, p = {p:.3f}, n = {len(u)}".replace("-", "−"), fontsize=6, ha="right")
ax.set_xlabel("Population multidimensionally poor, 2019–21 (%)")
ax.set_ylabel("CSR spending per resident, 10 years (₹, log)")
ax.set_xlim(-1, 36)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(OUT / "figure3_poverty.png")
plt.close(fig)

print(f"Wrote figures to {OUT}")
