"""Evidence report and scientific figures from validated saved outputs."""
from pathlib import Path
import json,hashlib,math
from xml.sax.saxutils import escape
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
DATA=HERE/'coverage_identification_20261030';OUT=ROOT/'reports/coverage_identification_20261030'


def mdtable(d):
    def f(x):return f'{x:.3f}' if isinstance(x,float) else str(x)
    return '\n'.join(['| '+' | '.join(d.columns)+' |','|'+'|'.join(['---']*len(d.columns))+'|']+
                      ['| '+' | '.join(f(v) for v in row)+' |' for row in d.itertuples(index=False,name=None)])


def figures(s,cert):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
    labels=[f'{r.period}, Q{r.quarter}' for r in s.itertuples()];y=np.arange(8)
    fig,axs=plt.subplots(1,2,figsize=(10.3,5),layout='constrained')
    axs[0].barh(y,s.median_province_cell_jaccard,color='#3c8296',height=.55)
    axs[0].set_yticks(y,labels);axs[0].invert_yaxis();axs[0].set_xlim(0,.6)
    axs[0].set_title('(a) Median provincial cell overlap',fontsize=11)
    axs[0].set_xlabel('Common cells / union cells')
    for i,v in enumerate(s.median_province_cell_jaccard):axs[0].text(v+.008,i,f'{v:.3f}',va='center',fontsize=8)
    for i,r in enumerate(cert.itertuples()):
        lo,hi=r.growth_lower_decimal,r.growth_upper_decimal
        axs[1].plot([lo,hi],[i,i],color='#b46b38',linewidth=4,solid_capstyle='butt')
        axs[1].plot([lo,hi],[i,i],'|',color='#6a3614',markersize=10)
        axs[1].text((lo+hi)/2,i-.15,f'{lo:.3f}–{hi:.3f}',ha='center',va='bottom',fontsize=8)
    axs[1].set_yticks(y,labels);axs[1].invert_yaxis();axs[1].set_xlim(1,3.35)
    axs[1].set_title('(b) Growth factors shared by all 63 intervals',fontsize=10)
    axs[1].set_xlabel('Admissible completed median-speed ratio')
    for ax in axs:ax.spines[['top','right']].set_visible(False)
    fig.supxlabel('Separate endpoint-union targets. Identification sets, not confidence intervals.\nEvery row admits all strict provincial orders in the continuous missing-value model.',fontsize=8)
    fig.savefig(OUT/'coverage_identification_summary.pdf',bbox_inches='tight')
    fig.savefig(OUT/'coverage_identification_summary.png',dpi=170,bbox_inches='tight');plt.close(fig)
    w=pd.read_csv(DATA/'completion_witnesses.csv');w=w[(w.period=='2023-2024')&(w.quarter==2)]
    original=w[w.orientation=='available_order'].set_index('province_id').target_rank
    fig,ax=plt.subplots(figsize=(6.6,5.0),layout='constrained')
    for orient,label,color,marker in [('available_order','Completion A: available-cell order','#286c84','o'),
                                      ('reverse_available_order','Completion B: complete reverse','#b46b38','x')]:
        g=w[w.orientation==orient].set_index('province_id').loc[original.index]
        ax.plot(original.to_numpy(),g.target_rank.to_numpy(),marker=marker,color=color,markersize=3,linewidth=1,label=label)
    ax.set_xlim(0,64);ax.set_ylim(64,0);ax.set_xticks([1,10,20,30,40,50,63]);ax.set_yticks([1,10,20,30,40,50,63])
    ax.set_xlabel('Province position in available-cell improvement order')
    ax.set_ylabel('Rank after completing only unobserved cells')
    ax.set_title('Same observed cells, opposite completed rankings\n2023–2024 Q2; illustrative of eight verified configurations',fontsize=11)
    ax.legend(loc='center right',fontsize=8,framealpha=.9)
    ax.spines[['top','right']].set_visible(False)
    fig.supxlabel('Both completions preserve every observed value. Neither is asserted true or plausible.\nThe fixed-footprint target differs from the published available-cell statistic.',fontsize=8)
    fig.savefig(OUT/'opposite_completion_rankings.pdf',bbox_inches='tight')
    fig.savefig(OUT/'opposite_completion_rankings.png',dpi=170,bbox_inches='tight');plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    s=pd.read_csv(DATA/'summary.csv');cert=pd.read_csv(DATA/'exact_shared_interval_certificate.csv')
    w=pd.read_csv(DATA/'completion_summary.csv');val=json.loads((DATA/'validation.json').read_text(encoding='utf-8'))
    assert val['passed'] and w.full_order_verified.all()
    assert s.strict_order_identified_pairs.eq(0).all() and s.full_rank_range.eq(63).all()
    figures(s,cert)
    short=s[['period','quarter','median_province_cell_jaccard','change_interval_finite','certain_increase',
             'strict_order_identified_pairs','guaranteed_top10','possible_top10']]
    short.to_csv(OUT/'headline_results.csv',index=False)
    cert.to_csv(OUT/'exact_interval_certificate.csv',index=False)
    title='Độ phủ ô và khả năng xác định thứ tự cải thiện tốc độ'
    intro='''Kết quả mới khác về bản chất với tương quan L4: xét riêng Ookla, cùng các ô đã quan sát có thể tương thích với mọi thứ tự cải thiện tỉnh trên một tập ô cố định, nếu không ràng buộc giá trị ở ô vắng mặt. Đây là kết quả nhận diện có điều kiện, không phải phát hiện một phương pháp toán học mới hay bằng chứng nguồn nào chính xác hơn.'''
    target='''Mỗi cấu hình dùng hợp các mã ô quan sát ở hai thời điểm làm tập địa lý cố định. Đại lượng đích là thay đổi trung vị của các tốc độ trung bình ô–quý trên tập đó, khi có giá trị cho mọi ô ở cả hai thời điểm. Nó khác trung vị của các ô đang có dữ liệu và không đại diện mọi hộ dân, mọi địa điểm hoặc toàn bộ lãnh thổ. Nếu ô vắng mặt không có một thống kê tốc độ tiềm năng có nghĩa, đại lượng hoàn thiện này cần được định nghĩa lại trước khi diễn giải chính sách.'''
    finding='''Cả tám cấu hình đều có 0/1.953 cặp tỉnh xác định chắc được thứ tự; khoảng hạng của mỗi tỉnh là [1,63], không tỉnh nào chắc chắn thuộc nhóm 10, và cả 63 tỉnh đều có thể thuộc nhóm đó. Một số tỉnh vẫn có mức cải thiện được xác định dương: mất nhận diện thứ tự không có nghĩa không biết tỉnh nào đã tăng.'''
    proof='''Các khoảng thay đổi của 63 tỉnh có phần giao mở trong từng cấu hình. Gán 63 giá trị khác nhau trong phần giao này theo một thứ tự tùy ý, rồi chọn giá trị thiếu để đạt các trung vị tương ứng, sẽ tạo ra thứ tự đó. So sánh phân số chính xác trên dữ liệu kbps xác nhận phần giao có độ rộng dương ở cả tám cấu hình; kết luận không dựa riêng vào làm tròn số thực hoặc việc khoảng ngoài quá lỏng.'''
    witness=f'''Đã dựng và kiểm độc lập 16 thứ hạng hoàn chỉnh: thứ tự ô đang quan sát và thứ tự đảo ngược, cho từng cấu hình riêng. Mọi giá trị quan sát giữ nguyên. Các giá trị điền hữu hạn nằm trong khoảng {w.min_fill_Mbps.min():.2f}–{w.max_fill_Mbps.max():.2f} Mbps, đồng thời nằm trong khoảng tốc độ đã quan sát của chính tỉnh–thời điểm tương ứng. Cả 16 thứ tự vẫn giữ khi làm tròn giá trị điền tới kbps nguyên, kiểm bằng tỷ số phân số chính xác. Không tuyên bố chúng là cách điền hợp lý, có xác suất cao, hay đồng thời tương thích cho mọi cấu hình trong một bảng nhiều năm duy nhất.'''
    caution='''Điểm cần giữ đúng mức: ở Q2/2023–2024, khoảng hệ số tăng chung chỉ khoảng 1,3315–1,3404. Mọi thứ tự có thể được tạo bằng những mức tăng rất gần nhau; đảo thứ hạng không tự chứng minh chênh lệch kinh tế lớn hoặc mất mát phúc lợi. Các khoảng là tập nhận diện logic, không phải khoảng tin cậy và không phân bổ xác suất cho thứ hạng.'''
    validation=f'''Tái dựng 16 quý; kiểm hình học độc lập bằng Shapely cho {val['independent_spatial_tiles']:,} dòng ô lưu (tính cả dòng chỉ được gán theo cách cũ). Cách gán cũ tái lập đúng trung vị, số ô và số lượt đo của 63 tỉnh ở từng quý. Mã đối chiếu riêng xác nhận {val['numeric_comparisons']:,} so sánh số; kiểm 203 ví dụ giới hạn, 40.733 cách hoàn thiện trên lưới hữu hạn và 16 thứ tự hoàn thiện. Hai mã dùng cùng dữ liệu/workspace, không phải một nhóm nghiên cứu độc lập.'''
    novelty='''Đóng góp có thể bảo vệ là: một chẩn đoán nhận diện theo độ phủ, có chứng chỉ và nhân chứng hoàn thiện, cho sự cải thiện trên tập ô địa lý cố định; cùng một dữ liệu quan sát có thể không chọn ra bất kỳ thứ tự tỉnh nào dưới giả định yếu đã nêu. Lý thuyết giới hạn dữ liệu thiếu và hạng khoảng đã có từ trước. Đối chiếu nguồn gần chưa đầy đủ toàn văn; chưa xác lập quyền ưu tiên hoặc mức chấp nhận của tạp chí. Không dùng kết quả này để gọi lại một phép toán đã biết là phương pháp mới.'''
    artifact='''Phần mới được đóng thành hồ sơ riêng; mã của lượt này không ghi vào bản thảo hay PDF rev16. Kiểm hash cuối thấy các tệp bài cũ trong workspace đã thay đổi so với bản kê trước; khác biệt được ghi riêng, không khôi phục hay ghi đè tệp đang được cập nhật. Mã, đặc tả, chứng minh, dữ liệu và hồ sơ tìm tài liệu đủ để đọc phản biện trước khi tích hợp. Không thêm trần tốc độ, loại quý hoặc đổi baseline để làm nhận diện tốt hơn sau khi thấy kết quả.'''
    paragraphs=[intro,target,finding,proof,witness,caution,validation,novelty,artifact]
    report='# '+title+'\n\n'+'\n\n'.join(paragraphs[:3])+'\n\n'+mdtable(short)+'\n\n'
    report+='\n\n'.join(paragraphs[3:])+'\n\n## Chứng chỉ phần giao hệ số tăng\n\n'+mdtable(cert[['period','quarter','growth_lower_decimal','growth_upper_decimal']])
    report+='''

## RESULT_AUDIT

- result_under_review: khả năng nhận diện thứ tự cải thiện trung vị trên tập ô hợp cố định, riêng từng cấu hình.
- arithmetic_checks: xem validation.json, exact_certificate_report.json và completion_report.json; các phép đối chiếu không phải bằng chứng độc lập lặp lại.
- inference_assessment: tập nhận diện xác định dưới mô hình hoàn thiện, không kiểm định thống kê, không bootstrap và không giả định độc lập ngẫu nhiên giữa tỉnh. Việc cho phép chọn giá trị thiếu theo tỉnh là ràng buộc mô hình dạng tích, không phải tuyên bố về phân bố xác suất.
- effect_size_and_economic_significance: không nhận diện được thứ tự, nhưng không tự chứng minh chênh lệch tốc độ hoặc tác động chính sách lớn; báo cả độ rộng phần giao.
- power_or_precision: không có power/CI cho bài toán logic hữu hạn này. Tính đúng của ràng buộc và ý nghĩa đại lượng đích quan trọng hơn p-value.
- multiplicity: báo đủ tám cấu hình và ba mức k đã định; không chọn cửa sổ hoặc trần tốc độ thuận lợi.
- sensitivity_findings: cùng tập ô có hệ số thay đổi tương quan với tập đang quan sát khoảng 0,807–0,955; điều đó không bảo đảm nhận diện cho tập hợp ô. Không gọi hiệu hai cách tính là tác động nhân quả của thành phần mẫu.
- distributional_findings: báo tất cả 504 tỉnh–cấu hình, 15.624 cặp tỉnh và 1.008 hoàn thiện tỉnh trong CSV.
- required_corrections: không suy kết quả sang hạng của thống kê đang quan sát, hạng dân cư, độ chính xác, mọi địa bàn hoặc giả thuyết nguyên nhân đứt gãy VNNIC.
- verdict: VERIFIED_CONDITIONAL_NONIDENTIFICATION_CERTIFICATE; METHOD_PRIORITY_UNRESOLVED.

## Tái lập

Từ thư mục gốc dự án, dùng môi trường hiện có:

```powershell
python PAPER_A_UPGRADE/build_coverage_tiles_20261030.py
python PAPER_A_UPGRADE/coverage_identification_20261030.py
python PAPER_A_UPGRADE/coverage_completion_witness_20261030.py
python PAPER_A_UPGRADE/coverage_exact_certificate_20261030.py
python PAPER_A_UPGRADE/validate_coverage_identification_20261030.py
python PAPER_A_UPGRADE/report_coverage_identification_20261030.py
```

Cache mới: PAPER_A_UPGRADE/data/coverage_tiles_canonical_20261030/.
Kết quả: PAPER_A_UPGRADE/coverage_identification_20261030/.
Mã cũ, số cũ và rev16 không thay đổi. Hai lượt cache nháp thất bại ở kiểm tọa độ được giữ, không sử dụng: raw tile_x/tile_y làm tròn bốn chữ số và tâm hình học vĩ độ khác rất nhỏ với tâm Mercator. Mã mới dùng tâm giải mã quadkey nhất quán, vẫn tái lập riêng cách gán cũ để kiểm soát. Ghi chú thay đổi nằm trong đặc tả và metadata cache.
'''
    (OUT/'RESULTS_VI.md').write_text(report,encoding='utf-8')
    # Four-page evidence brief, with full derivation left in the linked theory file.
    for name,weight in [('DV','normal'),('DVB','bold')]:
        pdfmetrics.registerFont(TTFont(name,font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight=weight))))
    body=ParagraphStyle('body',fontName='DV',fontSize=9.3,leading=13,spaceAfter=9)
    head=ParagraphStyle('head',fontName='DVB',fontSize=15,leading=20,spaceAfter=12)
    small=ParagraphStyle('small',fontName='DV',fontSize=7.4,leading=10)
    def para(text,style=body):return Paragraph(escape(text),style)
    def table(headers,values,widths):
        tab=Table([[para(h,small) for h in headers]]+[[para(str(x),small) for x in row] for row in values],colWidths=widths,repeatRows=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4edf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.5,colors.grey),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        return tab
    story=[para(title,head),para('Hồ sơ kiểm chứng — 30/10/2026',small),Spacer(1,10),para(intro),para(target),para(finding)]
    vals=[[r.period,'Q'+str(r.quarter),r.change_interval_finite,r.certain_increase,r.strict_order_identified_pairs,r.guaranteed_top10,r.possible_top10] for r in s.itertuples()]
    story+=[table(['Giai đoạn','Quý','Khoảng log hữu hạn','Chắc chắn tăng','Cặp có thứ tự chắc','Chắc top 10','Có thể top 10'],vals,[76,32,70,65,76,65,65]),Spacer(1,12),para('63 tỉnh trong mỗi cấu hình; 1.953 cặp tỉnh. Chắc chắn/có thể là mệnh đề trong mô hình hoàn thiện, không phải độ tin cậy thống kê.',small),PageBreak()]
    story+=[para('Vì sao đây là chứng chỉ, không chỉ là khoảng rộng?',head),para(proof),Image(str(OUT/'coverage_identification_summary.png'),width=505,height=245),Spacer(1,12),para(caution),para('Chứng minh và định nghĩa đầy đủ: THEORY_AND_SCOPE.md. Các phân số chính xác: exact_shared_interval_certificate.csv.',small),PageBreak()]
    story+=[para('Hai dữ liệu hoàn thiện, cùng quan sát, ngược thứ tự',head),para(witness),Image(str(OUT/'opposite_completion_rankings.png'),width=440,height=332),Spacer(1,8),para('Hình dùng Q2/2023–2024 để minh họa cấu hình có phần giao hẹp nhất. Toàn bộ tám cấu hình đã được dựng hai thứ tự và lưu, không chỉ trường hợp minh họa.',small),PageBreak()]
    story+=[para('Kiểm tra, đóng góp và giới hạn',head),para(validation),para(novelty),para(artifact),para('Nền tảng tài liệu',head),para('Manski (2005): giới hạn dữ liệu thiếu, DOI 10.1016/j.ijar.2004.10.006. Salo và Punkka: hạng khoảng và quan hệ trội, bản thảo tác giả 2010. Lee et al. (2023): sai lệch lấy mẫu và diễn biến theo thời gian, arXiv:2310.16136. Sharma et al. (2024): tổng hợp không gian, DOI 10.1145/3700416. Hồ sơ NOVELTY_CHALLENGE.md ghi rõ mức đã đọc và các nguồn chưa truy cập toàn văn.',small)]
    def footer(canvas,doc):
        canvas.setFont('DV',8);canvas.drawRightString(A4[0]-42,24,f'{doc.page}')
    SimpleDocTemplate(str(OUT/'coverage_identification_evidence.pdf'),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    print('Wrote results, two scientific figures, and evidence brief.')


if __name__=='__main__':main()
