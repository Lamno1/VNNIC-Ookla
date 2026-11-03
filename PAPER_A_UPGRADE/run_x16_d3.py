"""X16 D3 (post-run correction, 2026-10-10): S2 Delta recomputed on the common province set (VNNIC, Ookla and DTI all finite).
Reuses run_x16.py gates and helpers unchanged (text before the S1 section), same seeds; writes results_x16/s2_delta_d3.csv only."""
import re as _re
_src = open(HERE_PATH if False else __file__.replace("run_x16_d3.py", "run_x16.py"), encoding="utf-8").read()
_head = _src.split("# ------------------------------------------------ S1")[0]
_part = _src.split("# ------------------------------------------------ S2 (D1.3 pairs)")[0].split("# ------------------------------------------------ S1")[1]
exec(compile(_head.replace('GATES_ONLY = len(sys.argv) > 1 and sys.argv[1] == "gates"', "GATES_ONLY = False"), "run_x16.py", "exec"))
exec(compile("# S1\n" + _part, "run_x16_S1", "exec"))   # S1 and BOOT exactly as in the original run (needed for Holm/labels untouched)
rows = []
old = pd.read_csv(R / "s2_delta.csv")
for fid in FAM:
    for per, yr in PERS:
        for nk, y in IND[yr].items():
            if (fid, per, "VNNIC", nk) not in BOOT: continue
            xv, xo = vec(fid, "VNNIC", per), vec(fid, "Ookla", per)
            m = np.isfinite(xv) & np.isfinite(xo) & np.isfinite(y); n = int(m.sum())
            a, b = np.where(m, xv, np.nan), np.where(m, xo, np.nan); yy = np.where(m, y, np.nan)
            rv, ro = sp(xv[m], y[m]), sp(xo[m], y[m]); db = fast_rho(a, yy) - fast_rho(b, yy); lo, hi = ci(db)
            o = old[(old.family == fid) & (old.period == per) & (old.indicator == nk)].iloc[0]
            rows.append(dict(family=fid, period=per, indicator=nk, N_common=n, rho_V=rv, rho_O=ro, delta=rv - ro, lo=lo, hi=hi, p_boot=twosided(db),
                             R16_2_d3=lab_delta(lo, hi, n), delta_orig=o.delta, lo_orig=o.lo, hi_orig=o.hi, R16_2_orig=o.R16_2_unadjusted,
                             differs=bool(n < D.n or abs(rv - ro - o.delta) > 1e-9)))
d3 = pd.DataFrame(rows); d3.to_csv(R / "s2_delta_d3.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("rows", len(d3), "with N_common<63:", int((d3.N_common < 63).sum()), "rows whose delta differs from original:", int(d3.differs.sum()))
print(d3[d3.differs].round(4).to_string())
print("headline rows unchanged:", bool((d3[(d3.family == "F1") & (d3.indicator == "D_inf") & d3.period.isin(["2021", "2023"])].differs == False).all()))
print("label changes:", int((d3.R16_2_d3 != d3.R16_2_orig).sum()))
