# V331 — Tiêu chí avatar chân thực theo ảnh tham chiếu của Lam

**Trạng thái:** YÊU CẦU CHẤT LƯỢNG CHÍNH — CHƯA ĐẠT  
**Bản hiện tại:** V330 chỉ là bản thử nghiệm kỹ thuật để kiểm tra tải GLB, Three.js và chuyển động chờ. Không được gọi V330 là avatar chân thực hoặc avatar hoàn chỉnh.

## Mục tiêu hình ảnh

Tạo một nhân vật nữ trưởng thành 3D có độ chân thực gần ảnh tham chiếu do Phi cung cấp. Giữ nhận diện thiết kế của Lam:

- Mặt trái xoan mềm, đường hàm tự nhiên và chuyển tiếp cằm-cổ liền mạch; tránh bề mặt phẳng, khối cầu hoặc các mảng gắn trên mặt.
- Mắt nâu ấm có hình cầu mắt, giác mạc/độ bóng, mống mắt, đồng tử, mí trên-dưới và góc mắt đúng cấu trúc; không dùng mắt dạng nút nổi.
- Mũi nhỏ tự nhiên, sống và cánh mũi hòa vào mặt; môi có thể tích và viền môi mềm, không dùng các khối cầu/viên nổi.
- Tóc đen dài, có ngôi và mái mảnh tự nhiên; nhiều lớp có hướng sợi và độ cong hợp lý, không phải mũ tóc kín hay vài thanh hình trụ.
- Da tông ấm với biến thiên màu sắc rất nhẹ, roughness/specular có kiểm soát và subsurface scattering phù hợp; không bề mặt nhựa hoặc da phẳng một màu.
- Cổ, vai, cánh tay, bàn tay, thân, hông, đùi, cẳng chân và bàn chân phải có giải phẫu, tỷ lệ và chuyển tiếp mô mềm tự nhiên; không dùng chuỗi ellipsoid/capsule nhìn rõ như đồ chơi.
- Trang phục hiện đại, chất liệu vải có nếp và độ dày; giữ điểm nhấn dây chuyền nhỏ như ảnh tham chiếu. Dáng người mục tiêu khoảng 1,60 m, khỏe khoắn và cân đối.

## Quyết định kỹ thuật

Không tiếp tục cố biến blockout V330 thành avatar chân thực chỉ bằng chỉnh kích thước các khối. Cần chuyển sang quy trình nhân vật có chất lượng giải phẫu và bề mặt:

1. Dùng ảnh tham chiếu làm chuẩn hình dáng/nhận diện; dựng các góc tham chiếu bổ sung trong quá trình modeling nếu cần. Không giả định một ảnh đơn lẻ cung cấp thông tin chính xác cho toàn bộ mặt bên và sau đầu.
2. Tạo hoặc sculpt mesh đầu và cơ thể có mật độ hình học phù hợp, rồi retopology để mesh chạy ổn định. Những chi tiết quan trọng như mí mắt, cánh mũi, vành môi, tai, cổ và bàn tay phải là hình học có cấu trúc.
3. Xây dựng UV và texture PBR: base color, roughness, normal/bump và các bản đồ cần thiết; dùng shader da với scattering có tiết chế. Dựng tóc theo từng lọn/lớp cong bám da đầu, tránh tóc dạng mũ.
4. Dựng rig có skin weights được xác minh ở vai, khuỷu, cổ tay, hông, gối và cổ; thêm facial blendshapes/rig cho ít nhất 12 biểu cảm mục tiêu.
5. Xuất GLB tối ưu nhưng không hạ chất lượng khuôn mặt để đạt dung lượng. Đặt mục tiêu tải tốt trên Safari/iPhone; đo kích thước, thời gian tải và bộ nhớ trên thiết bị thật khi có thể.
6. Kiểm tra ảnh render góc chính diện, 3/4, nghiêng, cận mặt và toàn thân; sau đó chạy thử GLB trong viewer Three.js ở desktop và viewport di động.

## Cổng chấp nhận — tất cả đều bắt buộc

- [ ] Ảnh render cận mặt được Phi đối chiếu và chấp thuận; không chỉ qua kiểm tra mã.
- [ ] Khuôn mặt không có các điểm nổi/đường nối bất thường quanh mắt, mũi, má, môi, cằm hoặc chân tóc.
- [ ] Tóc, mắt, da và vải đều thể hiện vật liệu và chi tiết phù hợp với ánh sáng, không trông như đồ chơi nhựa.
- [ ] Ảnh toàn thân có khớp nối và tỷ lệ liền mạch, bàn tay/bàn chân có hình dạng tự nhiên.
- [ ] GLB có rig thực sự; các chuyển động chớp mắt, cười và miệng nói có biến dạng quan sát được, không chỉ khai báo tên morph.
- [ ] Browser test xác nhận renderer/WebGL, GLB, animation và morph; không có lỗi console hoặc request hỏng.
- [ ] Kiểm tra lại source SHA-256 để xác nhận asset đang chạy không bị thay thế ngoài ý muốn trước khi bản mới được duyệt.

## Bản hiện có

V330 có 74 mesh và chuyển động chờ toàn-root; bản browser candidate không chứa skeletal skin. Dù GLB tải được và kiểm thử Three.js thành công, hình hiện tại vẫn là blockout cách điệu, chưa đạt mục tiêu chân thực. Giữ bản gốc đang chạy và không quảng bá V330 là bản cuối. Chỉ đổi asset production sau khi các cổng trên được kiểm tra thực tế và Phi chấp thuận ảnh render.
