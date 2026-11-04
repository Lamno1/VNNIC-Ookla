# Source of the 63-province to 6-region mapping

Built on 3 November 2026 from the region/province hierarchy in the saved NSO (General Statistics Office) table V05.02, "Số doanh nghiệp đăng ký thành lập mới phân theo địa phương", file data/reference/nso_official_snapshot_20260913/V05.02_response.json (snapshot dated 13 September 2026). In that table each region row is followed by its provinces. Provinces were joined to the 63-province crosswalk (GIS_DERIVED/vnnic_adm1_crosswalk_63.csv) by normalised name.

Result: all 63 crosswalk provinces matched; no NSO province left unused. Regions: Trung du và miền núi phía Bắc 14, Đồng bằng sông Hồng 11, Bắc Trung Bộ và duyên hải miền Trung 14, Tây Nguyên 5, Đông Nam Bộ 6, Đồng bằng sông Cửu Long 13 (total 63).

Limits: the hierarchy comes from an NSO data table, not from a legal document defining the regions; the web search did not return a general statistics office region definition. The mapping is the six-region scheme (not the older eight). Output: region_mapping_6.csv.
