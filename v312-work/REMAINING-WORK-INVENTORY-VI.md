# LÝ LÂM LAM — Kiểm kê phần còn thiếu và kế hoạch hoàn thành

Ngày kiểm kê: 2026-10-13  
Nhánh kiểm tra: `step1-body-rebuild`  
Commit nền: `4aeb9276c96237e9c31c3ba5ba0a99e0aecc254c`  
Chromium CI: [Run #10 — PASS](https://github.com/PhiLam-ai/Ly-lam-lam/actions/runs/38355563264)

## Trạng thái đã xác minh

- [x] Chromium headless khởi chạy trang xem avatar.
- [x] Tải được `lam-default.glb`; không có page error, console error, request lỗi hoặc HTTP response lỗi trong lần kiểm thử.
- [x] Canvas WebGL được tạo (1280 × 800 trong môi trường CI).
- [x] GLB có 85 mesh, 12 morph và 6 animation theo debug state của viewer.
- [x] Viewer chuẩn hóa chiều cao mô hình về 1,60 m và có assertion tự động (sai số cho phép ±0,02 m).
- [x] Kiểm tra tĩnh đường dẫn viewer, cấu trúc GLB và cú pháp JavaScript đạt trong Run #10.

## Phần còn thiếu — ưu tiên theo thứ tự

### P0 — Làm cho bản chạy thử đáng tin cậy
- [ ] Xác nhận trực quan mô hình thực sự nhìn thấy, đúng chiều, không xuyên/lỗi vật liệu; kiểm thử Chromium hiện mới xác nhận canvas, tải GLB và trạng thái viewer.
- [ ] Chạy trên Chrome Windows của Anh với đúng thư mục phát hành và kiểm tra thao tác xoay, zoom, nút biểu cảm.
- [ ] Đóng gói và kiểm tra tài nguyên Three.js ngoại tuyến. Bản viewer trên nhánh này đang tham chiếu Three.js qua CDN jsDelivr; CI thành công không chứng minh CDN luôn truy cập được hoặc đã có bundle nội bộ.
- [ ] Triển khai HTTPS thật, xác minh đường dẫn gốc và GLB tải thành công sau khi phát hành.
- [ ] Kiểm thử Safari trên iPhone thật (màn hình dọc/ngang, chạm, safe area, quay lại tab, mạng yếu). Chưa có bằng chứng đã hoàn thành.
- [ ] Tạo gói phát hành có hướng dẫn chạy, manifest SHA-256 được tính từ đúng gói cuối, và giữ bản ổn định trước đó để rollback.

### P1 — Hoàn thiện avatar 3D
- [ ] Đánh giá chất lượng hình thể/chi tiết khuôn mặt bằng ảnh render thật; số mesh/morph/animation không tự chứng minh mô hình giống thiết kế đã thống nhất.
- [ ] Xác nhận 12 morph tương ứng đúng biểu cảm cần dùng, có biên độ hữu ích và phối hợp không gây méo.
- [ ] Kiểm tra 6 animation: tên, thời lượng, chuyển động, khả năng phát/dừng và chuyển trạng thái.
- [ ] Hoàn thiện tóc, mắt, da, quần áo, phụ kiện và tỷ lệ cơ thể theo thiết kế Lam; không đánh dấu hoàn tất chỉ từ mô hình blockout.
- [ ] Kiểm tra rig/skin, bàn tay, khớp vai/gối, bàn chân và chuyển động toàn thân bằng render trực quan.

### P2 — Tích hợp trợ lý Lam
- [ ] Kết nối API/backend hội thoại thật. Hiện giao diện báo “API chưa kết nối (xem thử cục bộ)”; `avatar_api_recovery.js` hiện chỉ chứa chính sách retry, không phải backend hội thoại.
- [ ] Thiết kế lưu nhớ có kiểm soát: dữ liệu nào lưu, nơi lưu, sửa/xóa/xuất dữ liệu, xử lý lỗi và phục hồi.
- [ ] Tích hợp giọng nói: nhận giọng nói, chuyển văn bản thành giọng nói, trạng thái nghe/nói, quyền micro, dừng nghe và xử lý khi iOS khóa màn hình.
- [ ] Nối điều khiển giọng nói với avatar: biểu cảm/lip-sync phù hợp, tránh để morph xung đột với animation.
- [ ] Thêm kiểm thử lỗi mạng, hết hạn phiên, API không khả dụng, phản hồi chậm và giới hạn chi phí.
- [ ] Không ghi khóa API bí mật vào mã frontend hoặc kho Git; dùng backend/proxy an toàn khi tích hợp dịch vụ trả phí.

### P3 — Bảo mật và sản phẩm
- [ ] Thiết kế đăng nhập/mật khẩu và quản lý phiên; không coi màn hình khóa cục bộ là bảo vệ dữ liệu phía máy chủ.
- [ ] Chọn kiến trúc lưu trữ, quyền riêng tư và sao lưu; xác định dữ liệu nào đồng bộ giữa thiết bị.
- [ ] Kiểm tra khả năng cài như ứng dụng web (PWA) trên iPhone; chưa phải ứng dụng iOS native.
- [ ] Kiểm thử hiệu năng, mức dùng bộ nhớ/nhiệt/pin, mạng yếu và khả năng truy cập.
- [ ] Lập quy trình phát hành có phiên bản, CI, kiểm tra SHA-256 và rollback.

## Ranh giới xác minh

Run #10 chỉ xác nhận kiểm thử tự động trên Chromium headless và kiểm tra tĩnh của repository tại commit nêu trên. Nó không xác nhận Safari/iPhone, triển khai HTTPS công khai, API hội thoại, giọng nói, lưu nhớ, đăng nhập hay chất lượng nghệ thuật của avatar.

## Cổng hoàn thành

Không tuyên bố “ứng dụng hoàn chỉnh” cho tới khi P0 được xác minh thực tế. Không tuyên bố “Lam có thể trò chuyện/nhớ/nói” cho tới khi các P2 tương ứng đã tích hợp và có kiểm thử. Cập nhật từng mục chỉ khi có bằng chứng kiểm thử hoặc bản triển khai tương ứng.
