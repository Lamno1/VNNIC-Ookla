# VNNIC-Ookla Repository

Dự án này chứa mã nguồn để thu thập, xử lý và tích hợp dữ liệu từ hai nguồn chính: **VNNIC** (Trung tâm Internet Việt Nam) và **Ookla** (Dữ liệu toàn cầu về tốc độ mạng và hiệu suất Internet).

## Cấu trúc Thư mục

Repository được chia thành 2 thư mục chính đại diện cho 2 nguồn dữ liệu: `OOKLA` và `VNNIC`. Mỗi thư mục bao gồm các phần như sau:

```
VNNIC-Ookla/
├── OOKLA/
│   ├── CODE/       # Chứa mã nguồn xử lý dữ liệu Ookla
│   ├── LOGS/       # Thư mục chứa log đầu ra (đã được cấu hình ignore)
│   └── RAW/        # Thư mục chứa dữ liệu thô tải về (đã được cấu hình ignore)
└── VNNIC/
    ├── CODE/       # Chứa mã nguồn xử lý và thu thập dữ liệu VNNIC
    ├── DERIVED/    # Dữ liệu đã qua xử lý hoặc trích xuất (đã được cấu hình ignore)
    ├── LOGS/       # Thư mục chứa log đầu ra (đã được cấu hình ignore)
    └── RAW/        # Thư mục chứa dữ liệu thô tải về (đã được cấu hình ignore)
```

## Thông tin về Mã nguồn (Code)

Mã nguồn được viết chủ yếu bằng Python với chức năng cụ thể như sau:

### 1. Mã nguồn Ookla (`OOKLA/CODE`)
- `build_ookla_schema_registry.py`: Script dùng để xây dựng lược đồ (schema) và cấu trúc dữ liệu cho Ookla, giúp chuẩn hóa và định dạng dữ liệu đầu vào.

### 2. Mã nguồn VNNIC (`VNNIC/CODE`)
- `download_vnnic.py`: Chịu trách nhiệm kết nối và tự động tải về các tệp dữ liệu thô từ hệ thống VNNIC.
- `attach_crosswalk_audit_panel.py`: Script dùng để gắn bảng đối chiếu (crosswalk) và thực hiện các bước kiểm tra/kiểm toán (audit) trên dữ liệu VNNIC để đảm bảo tính nhất quán và chất lượng dữ liệu.

## Thông tin về Dữ liệu (Data)

**Lưu ý quan trọng**: Do giới hạn dung lượng lưu trữ trên GitHub và tính chất bảo mật của dữ liệu, toàn bộ các tệp tin dữ liệu thực tế không được đẩy (push) lên kho lưu trữ này. Thay vào đó, chúng tôi quản lý dữ liệu thô bằng **Mã nguồn tự động tải (Automated Download Scripts)**.

- **Dữ liệu thô (RAW)**: Không upload lên Git. Để lấy dữ liệu thô, bạn chỉ cần chạy các file mã nguồn (ví dụ: `VNNIC/CODE/download_vnnic.py`). Mã nguồn sẽ tự động kết nối đến các API công khai (như hệ thống Internet Atlas của VNNIC) để tải toàn bộ dữ liệu thô và lưu vào thư mục `RAW` trên máy tính của bạn.
- **Dữ liệu phái sinh (DERIVED)**: Không upload lên Git. Sau khi có dữ liệu thô, bạn chạy tiếp các script xử lý (ví dụ: `attach_crosswalk_audit_panel.py`) để làm sạch và lưu dữ liệu đầu ra vào thư mục `DERIVED`.
- **Log (LOGS)**: Các tệp ghi lại quá trình chạy mã nguồn. Không upload lên Git.

Tất cả các thư mục này đã được định nghĩa trong file `.gitignore` để đảm bảo chúng luôn nằm trên máy cục bộ của bạn và không đẩy lên server GitHub. Cách tiếp cận này giúp repository luôn nhẹ, sạch sẽ và bất kỳ ai cũng có thể **tái tạo lại bộ dữ liệu (reproduce data)** bằng cách chạy code.
