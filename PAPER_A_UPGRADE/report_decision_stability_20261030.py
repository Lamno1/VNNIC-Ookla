"""Build a reviewable evidence pack without changing the manuscript."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
DATA=HERE/'decision_stability_20261030'
OUT=ROOT/'reports/decision_stability_20261030'


def md(frame):
    def f(x):
        if isinstance(x,float):return f'{x:.3f}'
        return str(x)
    return '\n'.join(['| '+' | '.join(frame.columns)+' |','|'+'|'.join(['---']*len(frame.columns))+'|']+
                     ['| '+' | '.join(f(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None)])


def main():
    OUT.mkdir(exist_ok=True)
    c=pd.read_csv(DATA/'comparisons.csv');s=pd.read_csv(DATA/'selection_summary.csv')
    a=pd.read_csv(DATA/'aggregation_comparisons.csv');r=pd.read_csv(DATA/'rankings.csv')
    primary=c[(c.panel=='base')&(c.metric=='log')&(c.axis=='source')&(c.k==10)].copy()
    primary['inversions_pct']=100*primary.inversion_fraction
    tbl=primary[['period','window_a','N','spearman','common_top_mass','replacements']]
    sens=c[(c.metric=='log')&(c.axis=='source')].groupby(['period','panel','k']).agg(
        common_min=('common_top_mass','min'),common_median=('common_top_mass','median'),common_max=('common_top_mass','max')).reset_index()
    sens.to_csv(OUT/'cutoff_and_aggregation_sensitivity.csv',index=False)
    ranks=r[(r.panel=='base')&(r.metric=='log')]
    ranks[ranks.top10.gt(0)].to_csv(OUT/'selected_provinces_primary.csv',index=False)
    p=pd.read_csv(DATA/'province_scenarios.csv')
    p[(p.panel=='base')&(p.metric=='log')&(p.k==10)].to_csv(OUT/'province_summary_primary.csv',index=False)
    sets=s[(s.panel=='base')&(s.metric=='log')&(s.k==10)][['period','subset','source','scenarios','always','ever','never']]
    ag=a[(a.metric=='log')&(a.source=='VNNIC')&(a.k==10)&(a.panel_a=='base')&(a.panel_b=='monthly_mean')][['period','window','common_top_mass','replacements']]
    coverage=r.groupby(['period','panel']).N.first().reset_index()
    summary=pd.read_csv(DATA/'comparison_summary.csv')
    ws=summary[(summary.panel=='base')&(summary.metric=='log')&(summary.axis=='window')&(summary.k==10)]
    ws=ws[['period','source_a','comparisons','retention_min','retention_median','retention_max']]
    v=json.loads((DATA/'validation.json').read_text(encoding='utf-8'))
    report='''# Hồ sơ kết quả: độ bền của kết luận về tỉnh cải thiện nhanh

Ngày 30/10/2026. Phân tích thăm dò có đặc tả trước lượt tính mới, sau khi đã biết
kết quả quý, nửa năm và 2023–2024. Không phải đăng ký trước độc lập với dữ liệu.

## Kết luận có thể bảo vệ

**Đây là diễn giải hệ quả phân loại của bất đồng L4, không phải một phát hiện
độc lập thứ hai, một phương pháp mới hay bằng chứng về quyền ưu tiên.**

Hai danh sách độc lập, chọn đều 10 trong 63 tỉnh, có kỳ vọng chung 100/63 = 1,587
tỉnh và thay 8,413 vị trí. Trung bình quan sát qua bảy cửa sổ là 1,143 tỉnh chung
trong mỗi giai đoạn. Câu "thay 6–10 tỉnh" phải đọc cạnh mốc 8,413, không dùng
riêng để thổi phồng đóng góp. Đây là tham chiếu toán học, không phải mô hình
đã khớp cấu trúc không gian. Các cửa sổ chồng lấn: không dùng 14 hàng như 14
quan sát độc lập và không kết luận tương đương hay thấp hơn ngẫu nhiên có ý nghĩa.

Với các thứ hạng thay đổi không hòa ở đây, tỷ lệ đảo thứ tự bằng đúng
(1 − Kendall tau)/2 (sai khác số thực tối đa 1,11e-16). Đây là phép viết lại,
không phải bằng chứng bổ sung. Kendall này tính trên thay đổi L4; Kendall trên
mức tốc độ L3 trong bài là đại lượng khác. Cột đảo thứ tự đã bỏ khỏi bảng rút
gọn và hình chính, giữ trong dữ liệu máy để tái lập.

Trong cả hai giai đoạn, việc đổi nguồn trên cùng cửa sổ thay thế phần lớn danh sách
10 tỉnh tăng trưởng log tốc độ cao nhất. Bất đồng vẫn có ở Q1, Q3, Q4 và H2, là các
cửa sổ không chứa Q2, và vẫn có khi chỉ xét 2023–2024. Nó không chỉ xuất hiện ở
cửa sổ Q2 hay chỉ ở mức cắt 10 tỉnh.

Đây là hệ quả phân loại quan sát được, không phải bằng chứng tỉnh bị xếp sai so
với chân lý. Hai nguồn khác đơn vị tổng hợp và phạm vi đo. Đổi cửa sổ cũng đổi
đại lượng theo thời gian cần đánh giá; không được coi mọi khác biệt là sai số đo.

## EXPERIMENT_RESULT

### 1. Đổi nguồn, giữ cửa sổ: kết quả chính

Mỗi hàng dùng cùng 63 tỉnh. `common_top_mass` là số tỉnh chung trong nhóm 10,
`replacements` là số vị trí bị thay khi đổi nguồn. Không có hòa điểm ở ranh giới
nhóm được chọn trong dữ liệu thực; quy tắc chia trọng số khi hòa đã được kiểm riêng.
Thống kê đảo thứ tự chỉ được giữ trong CSV đầy đủ, không dùng làm kết quả riêng.

'''+md(tbl)+'''

Số vị trí thay thế là 6–10/10 trong 2021–2024 và 8–10/10 trong 2023–2024,
so với mốc 8,413/10 của các danh sách độc lập chọn đều. Đây là diễn giải của L4,
không phải kết quả độc lập hay p-value. Không có ngưỡng tự đặt để tuyên
bố "novelty đạt". Giá trị tăng trưởng log và tăng Mbps là hai tiêu chí riêng, không
gộp chúng để chọn kết quả thuận lợi.

Với tiêu chí phụ tăng Mbps, số tỉnh chung là 0–5/10 trong 2021–2024 và 0–1/10
trong 2023–2024. Ở H2/2021–2024, tương quan của thay đổi Mbps là 0,618 nhưng
hai nguồn chỉ chung 2/10 tỉnh trong nhóm đầu. Đây là minh họa lấy từ bảng đầy đủ,
không phải một nguyên lý toán học mới hoặc một kiểm định độc lập.

### 2. Đổi cửa sổ trong từng nguồn

Mỗi nguồn có đủ 21 cặp cửa sổ; bảng báo khoảng và trung vị tỷ lệ giữ lại nhóm 10.
Đó là phân bố hữu hạn qua những cửa sổ đã chọn, không phải khoảng tin cậy.

'''+md(ws)+'''

Ngay ở cặp Ookla Q4–H2/2021–2024, tương quan thay đổi log là 0,931 nhưng chỉ
giữ 6/10 tỉnh. Tuy nhiên Q4 và H2 đo hai giai đoạn khác nhau; ví dụ này chứng minh
rằng tương quan tổng thể không xác định danh sách được chọn, một tính chất đã
biết; không chứng minh lỗi của một cửa sổ nào hoặc một khám phá mới.

### 3. Tỉnh nào được chọn một cách ổn định?

`always` = có mặt ở mọi kịch bản trong tập; `ever` = xuất hiện ít nhất một lần;
`never` = không xuất hiện lần nào. `both` gộp hai nguồn với số cửa sổ cân bằng.
Các kịch bản chồng lấn và không độc lập. Tần suất không phải xác suất đúng.

'''+md(sets)+'''

Ở mỗi giai đoạn, 46 tỉnh xuất hiện ít nhất một lần trong 14 danh sách, không tỉnh
nào có mặt trong tất cả 14. Chỉ xét Q1/Q3/Q4/H2 và hai nguồn vẫn không tỉnh nào
có mặt ở mọi danh sách; hợp các danh sách có 34 tỉnh (2021–2024) và 39 tỉnh
(2023–2024). Thống kê này không có nghĩa không tỉnh nào cải thiện thật hoặc đáng
được đầu tư; quy tắc nhóm đầu chỉ đánh giá mức cải thiện đã quan sát.

Danh tính của tất cả tỉnh, hạng, mức tăng và lần được chọn được lưu trong
`selected_provinces_primary.csv`, `province_summary_primary.csv` và các bảng đầy
đủ ở thư mục dữ liệu. Hai heatmap hiển thị toàn bộ 63 tỉnh, không chỉ các ví dụ cực trị.

### 4. Độ nhạy: mức cắt, trung bình/trung vị và đủ tháng

'''+md(sens)+'''

Khi đổi từ trung vị sang trung bình các tháng của riêng VNNIC, giữ nguồn và cửa
sổ cố định, số tỉnh chung trong nhóm 10 như sau:

'''+md(ag)+'''

Đặc biệt ở cấp năm, đổi cách gộp tháng thay 6/10 tỉnh trong 2021–2024 và 5/10
trong 2023–2024. Điều này là độ nhạy với một lựa chọn cách gộp cụ thể; không
phải đối chiếu trung bình và trung vị của các lượt đo bên trong từng tháng.

Cỡ tập tỉnh chung được giữ cố định qua cả bảy cửa sổ trong từng panel:

'''+md(coverage)+'''

Quy tắc đủ tháng loại Hà Giang trong 2021–2024, giữ 62 tỉnh; 2023–2024 giữ 63.
Bảng độ nhạy báo kết quả riêng, không trộn mẫu 62 với 63. Không có bằng chứng
rằng bất đồng nhóm đầu chỉ do một ô thiếu tháng. Ookla ở H1/H2/năm được gộp
từ thống kê tỉnh–quý; không dựng lại trung vị các ô/lượt đo nửa năm hoặc năm.

## RESULT_AUDIT

'''+f'''- arithmetic_checks: đường tính thứ hai khớp {v['numeric_comparisons']:,} phép so sánh số,
  gồm ô dữ liệu gộp lại, hạng, nhóm chọn, các so sánh nguồn/cửa sổ/cách gộp,
  tóm tắt theo tỉnh và hướng của các cặp tỉnh. Con số này là số ô được đối chiếu,
  không phải số bằng chứng độc lập.
'''+'''- Đường đối chiếu đọc lại bảng đầu vào đã lưu, xáo trộn thứ tự dòng, không gọi
  Data hoặc hàm phân tích chính cho kiểm dữ liệu thật. Cả hai vẫn trong cùng
  workspace và dùng cùng dữ liệu nguồn; không phải nhóm xác minh độc lập.
- Bốn trường hợp tổng hợp kiểm hòa ở ranh giới, hạng giống nhau, đảo toàn bộ,
  biến đổi đơn điệu và bất biến theo thứ tự dòng.
- Cả 201 fingerprint trong manifest_rev15 giữ nguyên. Ba hình PDF đã được render
  kiểm bố cục; không có chữ ngoài khung trang. Kiểm tra này không thay thế kiểm
  thống kê hoặc chứng nhận mọi nhánh mã khóa.
- Kiểm độc lập ban đầu phát hiện khác biệt cộng số thực của hai cách tính trung
  bình có thể phá một điểm hòa trong hạng Mbps phụ. Đã dùng math.fsum để tổng
  không phụ thuộc thứ tự dòng, ghi đính chính triển khai vào đặc tả và chạy lại.
  Không sửa ngưỡng kết quả hoặc chọn một thuật toán vì có số thuận lợi hơn.
- Đối chiếu 14 hệ số L4 với bảng H1/H2 và 2023–2024 đã có: khớp tới 1e-12.
- inference_assessment: chỉ mô tả trên dữ liệu quan sát, không p-value, bootstrap
  tỉnh, khoảng tin cậy hay nhãn có ý nghĩa. Vấn đề hiệu chỉnh không gian trước đây
  không được tuyên bố đã giải quyết; độ tin cậy của phép đo và tính đại diện còn thiếu.
- effect_size_and_economic_significance: báo trực tiếp số tỉnh thay thế và cặp đảo
  thứ tự. Chưa định lượng mất mát phúc lợi hoặc tác động của quyết định chính sách thật.
- power_or_precision: không có thiết kế lấy mẫu/kiểm định để tính power; các giá trị
  là mô tả hữu hạn. Không diễn giải tần suất kịch bản như xác suất hoặc độ tin cậy.
- multiplicity: báo đủ hai giai đoạn × bốn panel × hai tiêu chí × ba mức cắt; không
  chọn trường hợp để gán ý nghĩa. Không chạy thêm baseline/cửa sổ để đạt kết quả.
- sensitivity_findings: bất đồng danh sách còn ở giai đoạn ngắn hơn, ngoài Q2,
  đủ tháng và trung bình tháng; các độ lớn riêng khác nhau và đã báo đầy đủ.
- distributional_findings: toàn bộ 63 tỉnh được hiển thị và lưu, không chỉ tương
  quan toàn quốc; cả phân bố thứ hạng và danh sách nhóm đầu được công bố.
- required_corrections: không gọi quy trình là phương pháp mới, tần suất là xác
  suất, hoặc xếp hạng cải thiện là thứ tự nhu cầu đầu tư. Phân biệt độ nhạy với
  tính chính xác, và giới hạn sự khái quát vào những nguồn/giai đoạn đang xét.
- verdict: ARITHMETICALLY_VERIFIED_DESCRIPTIVE_INTERPRETATION_OF_L4;
  not an independent second finding; accuracy and method novelty not established.

## Đặt đóng góp trong bài thế nào?

Chỉ dùng một đoạn kết quả ngắn và một hình tóm tắt trong bài, bảng độ nhạy ở phụ
lục và danh sách đầy đủ trong CSV đi kèm. Câu có thể bảo vệ: **bài lượng hóa hệ
quả phân loại tỉnh của bất đồng đã thấy ở L4 và độ nhạy với một lựa chọn gộp tháng**.

Phản biện đúng có thể nói đây là ứng dụng gia tăng của công cụ đã có. Hồ sơ
`NOVELTY_CHALLENGE.md` đối chiếu mười công trình gần, đặc biệt bài Canada 2013
đã ghi nhận xếp hạng tỉnh khác nhau giữa hai nguồn. Vì vậy không viết "đầu tiên"
hay "phương pháp mới". Những phát hiện mới trong bộ dữ liệu này cần được định
vị là đóng góp thực nghiệm cụ thể; quyền ưu tiên trên toàn bộ tài liệu còn chưa xác lập.

## Tái lập và tệp

Từ thư mục gốc dự án, dùng môi trường Python của dự án:

```powershell
python PAPER_A_UPGRADE/decision_stability_20261030.py
python PAPER_A_UPGRADE/validate_decision_stability_20261030.py
python PAPER_A_UPGRADE/decision_overlap_reference_20261030.py
python PAPER_A_UPGRADE/plot_decision_stability_20261030.py
python PAPER_A_UPGRADE/report_decision_stability_20261030.py
```

Đặc tả: `PAPER_A_UPGRADE/decision_stability_specification_20261030.md`.
Dữ liệu đầy đủ: `PAPER_A_UPGRADE/decision_stability_20261030/`.
Ba hình PDF/PNG và các bảng rút gọn nằm cùng hồ sơ này. Đoạn tiếng Anh, định
nghĩa công thức và caption: `MANUSCRIPT_ADDITION.md`. Sau phản biện, phần rút
gọn đã tích hợp vào §4.4, §5.4 và Note S4 (S26–S28) của rev16. Hình mới là 5;
hình Delta cũ đổi thành 6. Diễn giải hiện hành là hệ quả phân loại của L4, không
phải phát hiện thứ hai. Bản trước tích hợp được lưu ở `before_review_integration/`.
Bản kê SHA256 ghi đầu vào, mã và kết quả. Không thay mã khóa, không cập nhật
manifest cũ để làm mất dấu thay đổi. Xem `REVIEW_CORRECTION.md` cho bản dựng
và kiểm tra mới nhất.
'''
    (OUT/'RESULTS_VI.md').write_text(report,encoding='utf-8')
    # Artifact manifest includes the current manuscript as an explicit reference,
    # not an assertion that this addition has been integrated into it.
    files=[HERE/name for name in ['decision_stability_specification_20261030.md',
         'decision_stability_20261030.py','validate_decision_stability_20261030.py',
         'plot_decision_stability_20261030.py','report_decision_stability_20261030.py',
         'decision_overlap_reference_20261030.py','decision_stability_review_amendment_20261030.md']]
    files+=list(DATA.glob('*'))+list(OUT.glob('*.md'))+list(OUT.glob('*.csv'))+list(OUT.glob('*.pdf'))+list(OUT.glob('*.png'))
    files+=[OUT/'figure_checks.json']
    files+=[ROOT/'reports/measurement_divergence_manuscript_revision_16.md']
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    (OUT/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Results report saved; manifest contains',len(manifest),'artifacts.')


if __name__=='__main__':main()
