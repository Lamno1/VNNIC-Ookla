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

## Hướng dẫn tái tạo Dữ liệu (How to reproduce Data)

**Lưu ý quan trọng**: Do giới hạn dung lượng lưu trữ trên GitHub và tính chất bảo mật của dữ liệu, toàn bộ các tệp tin dữ liệu thực tế (thô và phái sinh) không được đẩy (push) lên kho lưu trữ này. Thay vào đó, chúng tôi quản lý dữ liệu bằng **Mã nguồn tự động (Automated Scripts)**. Bất kỳ ai cũng có thể tái tạo lại bộ dữ liệu bằng cách làm theo các bước sau:

### Bước 1: Tải dữ liệu thô (RAW)
Các file dữ liệu thô không có sẵn trên Git. Để tải dữ liệu thô mới nhất từ VNNIC (từ năm 2019 đến 2026), bạn cần mở terminal/command prompt tại thư mục gốc của dự án và chạy lệnh sau:

```bash
# Chạy script tải dữ liệu từ VNNIC Internet Atlas
python VNNIC/CODE/download_vnnic.py
```

*Kết quả*: Mã nguồn sẽ tự động kết nối đến API công khai, tải toàn bộ dữ liệu thô và tự động tạo thư mục `VNNIC/RAW/` trên máy tính của bạn để lưu trữ chúng. Quá trình tải cũng sẽ tự sinh ra file log tại `VNNIC/LOGS/`.

### Bước 2: Xử lý dữ liệu phái sinh (DERIVED)
Sau khi đã có dữ liệu thô ở Bước 1, bạn tiếp tục chạy các script xử lý để làm sạch và hợp nhất dữ liệu:

```bash
# Chạy script xử lý và kiểm toán dữ liệu
python VNNIC/CODE/attach_crosswalk_audit_panel.py
```

*Kết quả*: Dữ liệu sau xử lý sẽ được tự động lưu vào thư mục `VNNIC/DERIVED/` để bạn có thể sử dụng cho việc phân tích.

### Bước 3: Xử lý dữ liệu Ookla (Nếu cần)
Tương tự, đối với dữ liệu Ookla, bạn có thể chạy:

```bash
# Chạy script xây dựng schema cho dữ liệu Ookla
python OOKLA/CODE/build_ookla_schema_registry.py
```

*Kết quả*: Dữ liệu hoặc schema của Ookla sẽ được xử lý tại thư mục `OOKLA/`.

---
**Ghi chú**: Tất cả các thư mục `RAW`, `DERIVED` và `LOGS` đã được cấu hình ẩn khỏi Git thông qua file `.gitignore`. Cách tiếp cận này giúp repository luôn nhẹ, sạch sẽ và đảm bảo tính nhất quán (reproducibility) khi chia sẻ mã nguồn.
