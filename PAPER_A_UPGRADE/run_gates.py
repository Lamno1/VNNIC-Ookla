from upg_common import *
D = Data()
res = []
# G1
tgt = {2021: 0.5423517271081965, 2022: 0.48787278731386163, 2023: 0.29627496159754224, 2024: 0.24810983373683076}
for y in range(2021, 2025):
    r = sp(D.vq2[y], D.fq2["ookla_tile_median_download_mbps"][y]); res.append(("G1", y, r, tgt[y], abs(r - tgt[y]) < 5e-4))
# G2
t2 = {"ookla_tile_median_download_mbps": -0.24707181259600616, "ookla_tile_mean_download_mbps": -0.19254032258064516,
      "ookla_tests_weighted_mean_download_mbps": -0.17842741935483872, "ookla_devices_weighted_mean_download_mbps": -0.168683}
dv = D.vq2[2024] - D.vq2[2021]
for k, t in t2.items():
    do = D.fq2[k][2024] - D.fq2[k][2021]; r = sp(dv, do); res.append(("G2_raw", k, r, t, abs(r - t) < 5e-4))
    dl = np.log(D.vq2[2024]) - np.log(D.vq2[2021]); dlo = np.log(D.fq2[k][2024]) - np.log(D.fq2[k][2021]); res.append(("G2_log(info)", k, sp(dl, dlo), np.nan, True))
# G3
for y in range(2021, 2025):
    a = D.O[(y, 2)]; b = D.fq2["ookla_tile_median_download_mbps"][y]; ok = int((np.abs(a - b) <= 0.01).sum()); res.append(("G3", y, ok, 60, ok >= 60))
df = pd.DataFrame(res, columns=["gate", "item", "value", "target", "pass"])
print(df.to_string()); print("ALL PASS:", bool(df[~df.gate.str.contains("info")]["pass"].all()))
df.to_csv(HERE / "results" / "gates.csv", index=False)
