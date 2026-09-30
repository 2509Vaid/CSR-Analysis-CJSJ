# Data sources

## raw/CSR_Report_2026-07-04.csv.gz

Project-level CSR spending reported by companies under Section 135 of the Companies Act 2013, FY 2014–15 to FY 2023–24.

- **Source:** Ministry of Corporate Affairs, Government of India, National CSR Portal, https://www.csr.gov.in/
- **Downloaded:** July 4, 2026 (date in the original file name)
- **Records:** 628,701
- **Compression:** gzip; pandas reads it directly. To decompress: `gunzip -k CSR_Report_2026-07-04.csv.gz`

| Column | Description |
|---|---|
| Company Name | Reporting company |
| Financial Year | e.g. `FY 2014-15` |
| PSU/Non-PSU | Public sector undertaking status |
| CSR State | State or union territory of the project, or a non-geographic category |
| CSR Development Sector | Sector (e.g. education, health) |
| CSR Sub Development Sector | Sub-sector |
| Project Amount Spent (In INR Cr.) | Amount spent, crore rupees (1 crore = 10 million) |

The file is included unchanged (apart from compression) for reproducibility. Known quirks: labels that differ only in capitalization (handled in `src/csr.py`), 127,799 zero-value records, and 18 negative records totaling −₹3.88 crore (kept as reported).

## external/census2011_population.csv

Population of each region in the dataset, from the Office of the Registrar General and Census Commissioner, India, *Census of India 2011: Primary Census Abstract* (2013). Andhra Pradesh and Telangana, and Jammu and Kashmir and Ladakh, are split to match the dataset's post-2011 labels. The 37 values sum to India's official 2011 total of 1,210,854,977; `src/csr.py` checks this on load.

## external/niti_mpi_2023_headcount.csv

Share of each state or union territory's population that is multidimensionally poor in 2019–21 (NFHS-5), from NITI Aayog, *National Multidimensional Poverty Index: A Progress Review 2023*. Values were transcribed from the report's state-wise headcount chart and cross-checked against its chart of percentage-point changes since 2015–16. The report treats Dadra and Nagar Haveli and Daman and Diu as one union territory (`dnh&dd`).

## external/fc15_devolution_shares_2021_26.csv

Each state's share (%) of the divisible pool of central taxes for 2021–26, as recommended by the Fifteenth Finance Commission (28 states; union territories are not included). Values from the Commission's report as tabulated by PRS Legislative Research, "Report of the 15th Finance Commission for 2021-26" (https://prsindia.org/policy/report-summaries/report-15th-finance-commission-2021-26). The shares sum to 100. The formula gives 45% weight to income distance, 15% to 2011 population, 15% to area, 10% to forest and ecology, 12.5% to demographic performance, and 2.5% to tax and fiscal effort.
