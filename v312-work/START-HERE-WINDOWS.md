# Mở LÝ LÂM LAM trên Windows

## Cách mở

1. Giải nén đầy đủ thư mục ứng dụng `v312-work`; không di chuyển riêng file HTML hoặc file GLB ra khỏi thư mục.
2. Nhấp đúp `START-LAM-WINDOWS.bat`.
3. Cửa sổ máy chủ sẽ chọn một cổng trống trên máy và mở trình duyệt. Giữ cửa sổ máy chủ mở trong khi sử dụng.
4. Để dừng, quay lại cửa sổ máy chủ và nhấn `Ctrl+C`.

## Nếu không mở được

- Nếu báo không tìm thấy Node.js, cài Node.js LTS rồi mở lại cửa sổ Command Prompt.
- Đừng đóng gói hoặc xóa thư mục `vendor/three` hay `lam-default.glb`; chúng là tài nguyên chạy cục bộ.
- Máy chủ chỉ nghe trên `127.0.0.1`, nên bản xem thử này chỉ dành cho máy tính đang chạy nó; chưa phải địa chỉ HTTPS và chưa mở cho iPhone.
- Phần avatar có thể tải được, nhưng dòng trạng thái hiện tại vẫn báo API hội thoại chưa tích hợp. Không xem đây là bản trợ lý trò chuyện hoàn chỉnh.

## Kiểm tra trước khi mở

Trong PowerShell, tại thư mục `v312-work`, có thể chạy:

```powershell
node tools\start-windows-preview.cjs --check
```

Kết quả mong đợi: `PASS: Windows launcher prerequisites found (6 files).`
