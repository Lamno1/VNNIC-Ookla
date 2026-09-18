# Ookla Open Data methodology evidence

- Official documentation: https://github.com/teamookla/ookla-open-data
- AWS Open Data registry: https://registry.opendata.aws/speedtest-global-performance/
- Retrieved: 2026-09-13 (Asia/Saigon)
- Dataset: Speedtest by Ookla Global Fixed and Mobile Network Performance Map Tiles
- License: CC BY-NC-SA 4.0.

Verified definitions from the official documentation:

- `avg_d_kbps`: average download speed of all tests performed in the tile, in kilobits per second.
- `avg_u_kbps`: average upload speed of all tests performed in the tile, in kilobits per second.
- `avg_lat_ms`: average latency of all tests performed in the tile, in milliseconds.
- `tests`: number of tests taken in the tile.
- `devices`: number of unique devices contributing tests in the tile.
- `quadkey`: identifier for a zoom-level-16 Web Mercator tile.
- `tile_x`, `tile_y`: tile centroid coordinates; documentation records their addition beginning with Q3 2023, while the locally manifested earlier files contain them and are audited directly.
- Fixed layer: tests from mobile devices with GPS-quality location and non-cellular connection type such as Wi-Fi or Ethernet.
- Quarter: three calendar months; for example Q1 begins January 1 and ends before April 1.
- Revision limitation: files may be reaggregated to honor data-subject access requests, so values accessed at different times may vary.
- WKT tile geometry is represented in EPSG:4326; the pilot does not scan it except for a deterministic audit sample if required.

Interpretation limitation: tile aggregates describe participating Speedtest measurements, not population-weighted geographic coverage.
