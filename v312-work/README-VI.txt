LÝ LÂM LAM — BẢN HIỆN TẠI V312
V312 sửa phân loại lỗi: nếu WebGL/GPU không khởi tạo được, báo cáo sẽ ưu tiên hướng dẫn đồ họa cụ thể thay vì nhầm thành lỗi mã ứng dụng.
Đã thêm kiểm thử hồi quy cho cả sự kiện error và unhandledrejection; kiểm thử tự động không thay thế việc xác nhận avatar render trên Chrome/Safari thật.
Đã có kiểm thử tự động cho cổng khởi chạy, cấu trúc GLB, thư viện và máy chủ xem trước. Những kiểm thử này không thay thế việc xác nhận avatar render trên Chrome/Safari thật.

LÝ LÂM LAM V310 — AUDIT CẤU TRÚC GLB TRƯỚC KHI KHỞI CHẠY
========================================================
- Trước khi mở ứng dụng, cổng khởi chạy kiểm tra sâu GLB: thứ tự/độ dài chunk, JSON glTF 2.0, buffer nhúng, giới hạn bufferView/accessor và tham chiếu mesh/node/skin/scene. Tệp sai cấu trúc sẽ bị chặn sớm với lỗi cụ thể.
- Đã kiểm tra mô hình hiện tại: 390.580 byte, 103 nodes, 85 meshes, 425 accessors, 425 bufferViews; cấu trúc đạt.
- Các bước kiểm tra HTTP, module Three.js và kiểm thử hồi quy vẫn được giữ nguyên.
- Giới hạn: audit cấu trúc không thay thế việc render WebGL trên Chrome Windows hoặc Safari/iPhone thật.

LÝ LÂM LAM V309 — THREE.JS NỘI BỘ LÀ CHẾ ĐỘ MẶC ĐỊNH
================================================
Cách dễ nhất trên Windows: mở thư mục `lylamlam_work`, nhấp đúp `START-LAM-LAM-WINDOWS.bat`. Tệp sẽ chạy kiểm tra tự động; nếu PASS, máy chủ khởi động và tự yêu cầu trình duyệt mặc định mở URL xem thử. Giữ cửa sổ máy chủ mở. Nếu trình duyệt không tự bật, mở URL được in trong cửa sổ đó bằng Chrome. Nhấn Ctrl+C trong cửa sổ đó để dừng máy chủ.
Nếu Windows báo không có lệnh `node`, hãy cài Node.js LTS từ trang chính thức rồi mở lại. Không cần Git/GitHub.

LÝ LÂM LAM V300 — PHÂN LOẠI LỖI TẢI GLB THEO PHẢN HỒI HTTP
=====================================================================
- Khi GLTFLoader báo lỗi, ứng dụng đọc mã HTTP từ sự kiện XHR nếu có. HTTP 4xx/5xx được báo riêng; lỗi mạng/CORS (không có mã HTTP) và lỗi đọc/phân tích GLB được phân biệt rõ hơn.
- Thông báo giữ đường dẫn mô hình, gợi ý kiểm tra HTTPS/quyền truy cập và chẩn đoán khởi động hiện có.
- Thêm kiểm thử hồi quy tĩnh cho các nhánh phân loại lỗi.
- Giới hạn: không xác minh phản hồi HTTP trực tiếp của host hoặc render GLB trên trình duyệt. Three.js chính thức vẫn chưa có trong vendor/three vì môi trường không truy cập được npm/mirror (EAI_AGAIN).

LÝ LÂM LAM V299 — PHÂN LOẠI LỖI KHỞI ĐỘNG CỤC BỘ
=====================================================================
- Khi lỗi khởi động xuất phát từ một tệp JavaScript/HTML cùng origin, ứng dụng nay giữ nguyên chế độ hiện tại, báo lỗi mã ứng dụng và không tự chuyển CDN Three.js không liên quan.
- Bổ sung nhận diện URL tệp cục bộ cho cả sự kiện `error` và `unhandledrejection`, kèm kiểm thử hồi quy.
- Điều này giúp phân biệt lỗi mã ứng dụng với lỗi tải Three.js; không khắc phục sự cố mạng hoặc thay thế việc kiểm tra trình duyệt thực.
- Giới hạn vẫn còn: Three.js chính thức chưa có trong `vendor/three`; registry npm không phân giải DNS trong môi trường hiện tại. Chưa xác minh avatar render thật hoặc Safari/iPhone.

LÝ LÂM LAM V298 — DỌN ĐIỀU KHIỂN PHỤC HỒI SAU KHI WEBGL HOẠT ĐỘNG LẠI
=====================================================================
- Khi WebGL khôi phục context sau sự cố và avatar đã tải xong, nay ẩn cả nút thử tải lại lẫn nút đổi chế độ Three.js. Trước đây chỉ nút tải lại được ẩn, có thể để lại nút đổi chế độ gây hiểu nhầm rằng ứng dụng vẫn lỗi.
- Thêm kiểm thử hồi quy cho nhánh `webglcontextrestored`.
- Kiểm thử mã không mô phỏng được mất/khôi phục GPU thực tế.
- Giới hạn vẫn còn: Three.js chính thức chưa có trong `vendor/three`; tải từ npm và mirror đều lỗi DNS `EAI_AGAIN`. Chưa xác minh avatar render hoặc Safari/iPhone thật.

LÝ LÂM LAM V297 — SỬA LỖI CẤU TRÚC HTML CHẶN KHỞI ĐỘNG
====================================================================
- Đóng thẻ `</style>` trước script tạo import map. Trước sửa, trình phân tích HTML có thể coi phần còn lại của tài liệu là nội dung CSS, làm hỏng cấu trúc trang và ngăn ứng dụng khởi chạy bình thường.
- Thêm kiểm thử hồi quy xác nhận thẻ style đóng trước import-map script, `</head>` và `<body>` có thứ tự hợp lệ.
- Đây là sửa lỗi cấu trúc HTML thực tế; kiểm thử tự động không thay thế xác minh render trên trình duyệt thật.
- Giới hạn còn lại: Three.js chính thức chưa được đóng gói trong `vendor/three`; chưa xác nhận avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V296 — PHÂN BIỆT TREO TẢI GLB VỚI TREO TẢI MODULE
====================================================================
- Watchdog khởi chạy nay phân biệt hai tình huống: Three.js chưa tải/khởi tạo (còn cơ hội thử CDN thay thế) và renderer đã sẵn sàng nhưng yêu cầu mô hình GLB bị treo.
- Nếu renderer đã sẵn sàng mà 15 giây vẫn chưa tải xong GLB, ứng dụng hiển thị lỗi nhắm đúng `lam-default.glb` và giữ nút phục hồi thay vì tải lại toàn trang qua CDN khác một cách không cần thiết.
- Nếu GLB tải thành công muộn, ứng dụng xóa cờ thất bại và ẩn nút phục hồi cũ.
- Kiểm thử hồi quy phân biệt timeout module và timeout GLB. Đây là kiểm thử mã và luồng điều khiển, không giả nhận là đã thử mạng thực.
- Giới hạn: Three.js chính thức vẫn chưa có trong `vendor/three`; chưa xác nhận avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V295 — KHÔI PHỤC ĐIỀU KHIỂN KHI GLB KHÔNG TẢI ĐƯỢC
================================================================
- Sửa lỗi giao diện khi tải `lam-default.glb` thất bại: trước đây callback ghi đè toàn bộ `#status`, làm mất nút “Thử tải lại” và nút đổi chế độ Three.js.
- V295 chỉ cập nhật `#status-message`, đánh dấu khởi chạy thất bại, hủy bộ đếm thời gian khởi chạy và hiển thị các điều khiển phục hồi nếu có.
- Bổ sung kiểm thử hồi quy xác nhận callback lỗi không xóa các nút phục hồi.
- Giới hạn: đây là sửa lỗi phục hồi khi GLB lỗi, không chứng minh mô hình đã tải thành công. Three.js chính thức vẫn chưa có trong `vendor/three`; chưa xác nhận avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V294 — XUẤT LẠI GÓI THREE.JS NGOẠI TUYẾN AN TOÀN
=============================================================
- Công cụ xuất gói V294 có thể chạy lặp vào cùng thư mục đích, hữu ích khi người dùng cần tải/xuất lại gói sau một lần chạy thành công hoặc gián đoạn ở bước chuyển file.
- Mỗi tarball vẫn phải khớp `dist.integrity` SHA-512 từ registry trước khi được chép vào thư mục đầu ra; manifest được làm mới theo gói vừa xác minh.
- Kiểm thử hồi quy chạy exporter hai lần liên tiếp trong cùng thư mục.
- Giới hạn không đổi: môi trường hiện tại chưa tải được tarball Three.js chính thức; chưa xác nhận avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V293 — KIỂM TRA ĐỒ THỊ MODULE TRƯỚC KHI CHẠY LOCAL
=================================================================
- Launcher nay kiểm tra đồ thị import của toàn bộ Three.js nội bộ trước khi mở máy chủ xem trước; chỉ kiểm tra đủ tên tệp là chưa đủ.
- Nếu thiếu module tương đối, có import thoát khỏi `vendor/three` hoặc package import không được import map ánh xạ, launcher dừng và in lỗi cụ thể thay vì mở trang có nguy cơ trắng avatar.
- Kiểm thử tích hợp bao gồm bundle fixture hợp lệ được khởi chạy với `?three=local` và bundle hỏng bị chặn trước khi phục vụ; launcher cũng chuyển SIGINT/SIGTERM cho máy chủ con để tránh tiến trình mồ côi.
- Bộ kiểm thử hồi quy: 114/114 đạt trên bản phát hành đã giải nén sạch.
- Giới hạn: kiểm tra đồ thị module không thay thế việc tải thư viện chính thức hay render WebGL. Môi trường hiện tại vẫn chưa lấy được tarball `three@0.160.0`; avatar thật, GitHub Pages và Safari/iPhone chưa được xác minh.

LÝ LÂM LAM V292 — DỰ PHÒNG CDN KHÔNG PHỤ THUỘC SESSIONSTORAGE
=================================================================
- Sửa một trường hợp khởi chạy thực tế: nếu Safari/chế độ riêng tư hoặc chính sách trình duyệt chặn `sessionStorage`, cơ chế thử CDN unpkg trước đây có thể bị vô hiệu hóa.
- V292 dùng thêm tham số URL `threeFallbackAttempted=1` làm dấu chống lặp; vẫn giữ các tham số khác và phần hash. Khi ứng dụng khởi chạy thành công, dấu tạm được xóa khỏi URL.
- Kiểm thử thực thi mô phỏng `sessionStorage` ném lỗi, xác nhận lần chuyển sang unpkg vẫn diễn ra và không tạo vòng lặp.
- Bộ kiểm thử: 113/113 đạt. Thay đổi này cải thiện khả năng phục hồi khi lưu trữ bị chặn, nhưng không làm CDN hoạt động khi thiết bị không có mạng.
- Three.js chính thức vẫn chưa có trong `vendor/three` ở môi trường đóng gói; chưa xác nhận avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V291 — DỰ PHÒNG REGISTRY KHI XUẤT GÓI NGOẠI TUYẾN
===============================================================
- Trên máy có Internet, công cụ xuất gói V289 nay thử registry npm chính thức trước, rồi chỉ chuyển sang `https://registry.npmmirror.com/` nếu lỗi thuộc nhóm DNS/mạng/timeout.
- Metadata `dist.integrity` và tarball luôn được lấy từ cùng registry đã chọn; SHA-512 của bytes vẫn phải khớp trước khi xuất.
- Manifest ghi rõ registry được dùng. Lỗi metadata, phiên bản hoặc integrity không bị che bằng cách chuyển nguồn.
- Chạy `node tools/export-three-offline-bundle.cjs --out three-offline-bundle`, sau đó chuyển tarball và manifest sang máy cần tích hợp, rồi chạy công cụ nhập V290.
- Kiểm thử mô phỏng DNS lỗi ở registry chính thức và xác nhận mirror được dùng cho cả metadata lẫn tarball. Môi trường tạo bản hiện tại vẫn không phân giải được hai registry, nên chưa lấy được tarball thật; chưa xác nhận avatar render, Pages hay Safari/iPhone.

LÝ LÂM LAM V290 — NHẬP GÓI THREE.JS NGOẠI TUYẾN
=================================================
- Thêm `tools/import-three-offline-bundle.cjs` để nhập gói tarball + manifest được tạo bởi V289 mà không cần cú pháp biến môi trường riêng của Bash/PowerShell.
- Công cụ kiểm tra đúng `three@0.160.0`, tên tarball, SHA-512 SRI và SHA-512 hex đối chiếu trực tiếp với bytes của tarball trước khi gọi bước staging.
- Dùng: `node tools/import-three-offline-bundle.cjs --bundle-dir ./three-offline-bundle` (hoặc chỉ định thư mục chứa cả `three-0.160.0.tgz` và `THREE-OFFLINE-MANIFEST.txt`).
- Nếu tarball bị đổi, sai manifest hoặc sai phiên bản, quá trình dừng trước khi giải nén. Đây là quy trình nhập; nó không có nghĩa thư viện đã được lấy hoặc avatar đã render trong môi trường hiện tại.

LÝ LÂM LAM V288 — DỰ PHÒNG REGISTRY KHI LẤY THREE.JS
====================================================
- Giữ nguyên ưu tiên cache npm ngoại tuyến và ghim chính xác `three@0.160.0`.
- Nếu registry npm chính thức lỗi mạng/DNS/timeout, công cụ thử lại cùng phiên bản qua `https://registry.npmmirror.com/`.
- Chỉ đổi registry khi lỗi được phân loại là lỗi kết nối; lỗi phiên bản, gói hoặc xác minh khác vẫn dừng an toàn.
- Tarball cục bộ vẫn phải vượt qua SHA-512 pin nếu workflow yêu cầu, sau đó qua công cụ staging và kiểm tra đồ thị import.
- Đã thử thực tế cả hai registry trong môi trường đóng gói; cả hai đều lỗi DNS `EAI_AGAIN`. Đây là phương án dự phòng tải gói, chưa lấy được Three.js. Chưa xác nhận avatar render, GitHub Pages hay Safari/iPhone thật.

LÝ LÂM LAM V287 — DỰ PHÒNG CDN KHI KHỞI ĐỘNG BỊ TREO
=====================================================
- Sửa một trường hợp lỗi thực tế: khi tải module bị treo nhưng không phát ra sự kiện lỗi hữu ích, watchdog 15 giây trước đây chỉ hiện thông báo và chờ người dùng thao tác. Nay nó gọi cùng cơ chế chuyển sang unpkg đúng một lần.
- Giữ giới hạn một lần bằng sessionStorage; không đổi chế độ local/unpkg và không lặp tải vô hạn.
- Chẩn đoán khởi động nay hiển thị đúng `three=unpkg` thay vì ghi nhầm jsDelivr.
- Kiểm thử hồi quy xác minh nhánh timeout và nhãn chế độ. Đây là kiểm tra logic, không chứng minh CDN tải được; môi trường hiện tại vẫn lỗi DNS EAI_AGAIN và chưa có vendor/three chính thức.
- Chưa xác minh avatar render, GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V285 — CDN THAY THẾ ĐƯỢC GHIM PHIÊN BẢN
=====================================================
- Thêm chế độ `?three=unpkg`, dùng `https://unpkg.com/three@0.160.0/` làm CDN thay thế, vẫn ghim chính xác Three.js 0.160.0.
- Khi CDN jsDelivr bị chặn hoặc không truy cập được, có thể thử `node tools/start-preview.cjs --three unpkg` hoặc mở URL có `?three=unpkg`. Chế độ này vẫn cần Internet; chưa xác nhận unpkg truy cập được trong môi trường hiện tại.
- Nút thử lại luân phiên giữa jsDelivr, unpkg và thư viện nội bộ; trước khi chuyển sang nội bộ, ứng dụng kiểm tra các tài nguyên cần thiết.
- Launcher và máy chủ xem trước đều hỗ trợ `--three cdn|unpkg|local`; chế độ nội bộ vẫn dừng an toàn nếu thiếu `vendor/three`.
- Môi trường build hiện tại không phân giải được jsDelivr/unpkg và chưa có gói Three.js trong npm cache. Chưa xác nhận render avatar, triển khai GitHub Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V284 — SỬA URL CHẾ ĐỘ THREE.JS NỘI BỘ
====================================================
- Thêm `node tools/start-preview.cjs` để mở máy chủ xem thử nhanh mà không phải tự gõ lệnh máy chủ riêng.
- Nếu đủ các tệp Three.js nội bộ và mô hình GLB, launcher chọn chế độ nội bộ; nếu chưa có thì nói rõ đang dùng CDN và cần Internet.
- Dùng `node tools/start-preview.cjs --local-three` để yêu cầu chế độ nội bộ và dừng an toàn nếu thiếu tệp; dùng `--lan` để thử từ iPhone cùng Wi-Fi trên mạng đáng tin cậy.
- Tùy chọn: `--port 8080` và `--root <thư-mục>`.
- V284 sửa để URL tự thêm `?three=local` khi phát hiện thư viện nội bộ; nếu thiếu thư viện, URL giữ chế độ CDN.
- Chưa thể lấy gói Three.js chính thức trong môi trường tạo bản này do DNS npm lỗi EAI_AGAIN; chưa xác nhận avatar render hoặc Safari/iPhone thật.

CHẠY NHANH TRÊN MÁY CÓ NODE.JS
1. Giải nén ZIP và mở Terminal/CMD tại thư mục vừa giải nén.
2. Chạy `node tools/start-preview.cjs` rồi mở URL được in ra.
3. Mặc định chỉ máy tính đó truy cập được. Muốn thử iPhone cùng Wi-Fi, chạy `node tools/start-preview.cjs --lan` và mở URL LAN được in ra; chỉ dùng mạng tin cậy, sau đó nhấn Ctrl+C để dừng.
4. Nếu CDN không tải được, cần lấy/stage Three.js chính thức bằng `node tools/fetch-vendor-three.cjs` trên máy có Internet, rồi chạy `node tools/start-preview.cjs --local-three`.

LÝ LÂM LAM V280 — LƯU CACHE NPM CHỈ SAU KHI LẤY THƯ VIỆN THÀNH CÔNG
====================================================================
- Sửa workflow GitHub Actions: chỉ lưu cache npm khi bước lấy và staging Three.js thành công, đồng thời cache chính xác chưa được khôi phục từ khóa chính.
- Tránh đóng băng cache npm chưa đầy đủ vào khóa bất biến khi lần tải gói thất bại.
- Vẫn dừng triển khai nếu không lấy được Three.js; không chuyển sang CDN dự phòng.
- Chưa xác nhận cache/Pages trên GitHub-hosted runner hoặc render thực tế; vendor/three vẫn cần được lấy từ npm hoặc tarball chính thức đã xác minh.

LÝ LÂM LAM V245 — KIỂM TRA LIÊN KẾT MODULE THREE.JS
===================================================
- Trước khi triển khai, chạy `node tools/vendor-module-integrity.cjs` để quét import tương đối trong build và examples/jsm của vendor/three.
- Công cụ phát hiện module addon bị thiếu hoặc đường dẫn tương đối thoát khỏi thư mục vendor; GitHub Actions dừng nếu kiểm tra thất bại.
- Đây là kiểm tra cấu trúc module, không xác nhận CDN, WebGL, render hoặc Safari/iPhone.

- V239 phân biệt lỗi khởi tạo WebGL/render context với lỗi CDN chung và hiển thị hướng dẫn xử lý phù hợp trên màn hình. Đây là cải thiện thông báo lỗi, không thay thế kiểm thử render trực tiếp.
- V238 thêm kiểm thử HTTP cục bộ cho trang, mô hình GLB, các module cốt lõi, MIME type và phản hồi 404; đây không phải kiểm thử render trình duyệt.
LÝ LÂM LAM — V237 Startup Resource Preflight
====================================

MỤC TIÊU
- Bản xem thử avatar 3D trên trình duyệt; chưa phải ứng dụng iOS cài đặt.
- Ưu tiên khởi chạy phần cốt lõi: tải Three.js, dựng renderer, tải lam-default.glb và cung cấp điều khiển camera.
- Các mô-đun chẩn đoán nâng cao chỉ được nạp khi URL có ?diagnostics=1 để giảm công việc lúc mở ứng dụng bình thường.
- V236 hiển thị lỗi JavaScript/tải mô-đun chưa xử lý ngay trên màn hình trong giai đoạn khởi chạy.
- V237 thêm công cụ preflight kiểm tra đường dẫn module cục bộ, tệp GLB/JSON lõi và cấu trúc import map trước khi triển khai.
- Chưa kết nối AI/backend cảm xúc, hội thoại hoặc giọng nói.

CHẠY NHANH
1. Giải nén toàn bộ ZIP, giữ nguyên cấu trúc tệp.
2. Đưa nội dung thư mục lên host web tĩnh có HTTPS (GitHub Pages là một lựa chọn).
3. Mở URL gốc bằng Safari; chờ trạng thái “Mô hình đã tải”.
4. Thử Khuôn mặt, Toàn thân, +/− và kéo avatar để xoay.
5. Chỉ thêm ?diagnostics=1 khi cần dùng bảng kiểm thử biểu cảm.
6. Trước khi triển khai, chạy `node tools/startup-preflight.cjs` để kiểm tra các tệp và đường dẫn cục bộ.
7. Nếu khởi chạy không hoàn tất sau 15 giây, thông báo trên màn hình sẽ nhắc kiểm tra Internet/CDN Three.js và WebGL. Nếu lỗi JavaScript hoặc tải mô-đun xảy ra trước khi khởi tạo 3D, thông báo sẽ kèm chi tiết lỗi khi trình duyệt cung cấp.



THƯ VIỆN THREE.JS TỰ LƯU TRỮ (V241 — TÙY CHỌN)
- Mặc định ứng dụng vẫn dùng CDN jsDelivr như trước.
- Nếu đã có gói npm chính thức `three@0.160.0`, chạy: `node tools/vendor-three.cjs /đường/dẫn/tới/node_modules/three`.
- Công cụ từ chối tên gói/phiên bản sai và kiểm tra các tệp core, GLTFLoader, OrbitControls cùng LICENSE trước khi sao chép.
- Triển khai cả thư mục `vendor/three` cùng toàn bộ dự án, sau đó mở URL với `?three=local` (ví dụ `https://ten-trang-web.example/?three=local`).
- Có thể kiểm tra tệp trước khi triển khai bằng `node tools/startup-preflight.cjs` và `node tools/static-http-smoke.cjs`.
- Các bản V241–V242 chưa chứa thư viện Three.js nội bộ vì môi trường tạo gói không truy cập được CDN/npm. V243 thêm cách tự tải và staging tự động trên máy có mạng: chạy `node tools/fetch-vendor-three.cjs`. Công cụ cố định đúng `three@0.160.0`, bỏ qua lifecycle scripts, tải vào thư mục tạm và dùng lại trình kiểm tra trước khi thay `vendor/three`. Nếu không có mạng, lệnh sẽ báo lỗi; ứng dụng và chế độ CDN mặc định không bị đổi. Sau khi thành công, chạy `node tools/startup-preflight.cjs` và `node tools/static-http-smoke.cjs`, triển khai cả `vendor/three`, rồi mở `?three=local`. Chưa xác minh render trực quan hoặc iPhone Safari.

TẢI VÀ ĐÓNG GÓI THREE.JS CHÍNH THỨC (V243)
- Trên máy có Node.js/npm và Internet, từ thư mục gốc dự án chạy `node tools/fetch-vendor-three.cjs`.
- Công cụ chỉ yêu cầu `three@0.160.0`, tắt lifecycle scripts và đưa gói vào thư mục tạm; sau đó gọi `tools/vendor-three.cjs` để kiểm tra tên, phiên bản, addon và LICENSE trước khi staging.
- Nếu npm registry không truy cập được, lệnh báo lỗi và dọn thư mục tạm. Không coi việc công cụ tồn tại là bằng chứng thư viện đã tải hoặc avatar đã chạy.
- Sau khi staging thành công, chạy `node tools/startup-preflight.cjs` và `node tools/static-http-smoke.cjs`, triển khai thư mục `vendor/three`, rồi kiểm tra bằng trình duyệt thật.


CÁCH MỞ TRÊN IPHONE
1. Giải nén gói ZIP trên máy tính hoặc trong ứng dụng Tệp.
2. Đưa TOÀN BỘ nội dung bên trong thư mục này lên dịch vụ lưu trữ web tĩnh có HTTPS.
3. Mở URL HTTPS mà dịch vụ cấp bằng Safari.
4. Chờ dòng trạng thái báo mô hình đã tải. Nếu lỗi, kiểm tra tệp lam-default.glb và kết nối Internet.

LƯU Ý QUAN TRỌNG
- Không mở index.html trực tiếp từ ứng dụng Tệp; mô-đun 3D thường cần máy chủ web.
- Three.js đang được tải từ jsDelivr, do đó cần Internet và CDN phải truy cập được.
- Chưa xác nhận hiển thị trên iPhone vật lý. Kiểm thử cú pháp/tệp không thay thế kiểm thử trên thiết bị thật.
- Không nhập dữ liệu riêng tư vào bản thử nghiệm.

SO SÁNH BẢN GHI BIỂU CẢM (V226)
Trong ?diagnostics=1, dán hai JSON snapshot để so sánh trọng số morph trước/sau. Xem EXPRESSION-COMPARISON-VI.txt. Chênh lệch số học không phải điểm chất lượng hình ảnh.

CHẾ ĐỘ CHẨN ĐOÁN
Thêm ?diagnostics=1 vào cuối URL, ví dụ https://ten-trang-web.example/?diagnostics=1
để bật bảng thử morph, camera, mesh và animation. Các nút chỉ điều khiển cục bộ.

KIỂM TRA BẢN GÓI
V217 có bộ kiểm thử hồi quy tự động và kiểm tra cấu trúc GLB. Các kiểm thử cục bộ đã chạy thành công.
Chưa xác nhận render 3D trực quan trên trình duyệt từ xa, deploy công khai hoặc chạy trên iPhone thật.


KIỂM THỬ HỒI QUY V217
- Yêu cầu Node.js 20 trở lên.
- Chạy: node --test tests/*.test.cjs
- Bộ kiểm thử xác minh các helper biểu cảm/chuyển động, công cụ kiểm tra mesh và cấu trúc GLB.
- GitHub Actions sẽ chạy bộ kiểm thử trước khi triển khai; nếu kiểm thử thất bại, quy trình xuất bản dừng lại.
- Kiểm thử tự động không thay thế việc mở trên Safari/iPhone vật lý.


ĐIỀU KHIỂN DI ĐỘNG — V218
- Khuôn mặt: chuyển nhanh sang góc nhìn gần mặt.
- Toàn thân: lùi camera để quan sát mô hình.
- + / −: phóng to hoặc thu nhỏ; Đặt lại khôi phục góc nhìn mặc định.
- Hướng dẫn: mở/đóng hướng dẫn thao tác.
- Có thể vuốt để xoay avatar và dùng hai ngón tay để zoom.
- Các nút chỉ điều khiển góc nhìn cục bộ; không gửi hình ảnh hoặc dữ liệu lên API.


BỐ CỤC DI ĐỘNG — V219
- Dùng dynamic viewport height (100dvh) để giảm lỗi chiều cao khi thanh công cụ Safari thay đổi.
- Bật viewport-fit=cover và chừa vùng an toàn theo safe-area của iPhone.
- Sáu nút thao tác được xếp thành lưới ba cột; bảng hướng dẫn/chẩn đoán đặt dưới thanh nút.
- Đây là cải tiến CSS và kiểm thử tĩnh; chưa xác minh trực quan trên iPhone/Safari thật.


ĐỘ ỔN ĐỊNH HIỂN THỊ — V220
- Tự cập nhật kích thước renderer và tỷ lệ camera khi viewport thay đổi, bao gồm visual viewport trên trình duyệt di động.
- Giới hạn pixel ratio tối đa 2 để tránh tăng tải GPU không cần thiết trên màn hình mật độ điểm ảnh cao.
- Giới hạn bước thời gian mỗi khung hình ở 50 ms để chuyển tab quay lại không gây bước nhảy biểu cảm quá lớn.
- Hiển thị thông báo khi WebGL mất hoặc khôi phục context. Đây là xử lý dự phòng; hành vi thực tế còn phụ thuộc trình duyệt và thiết bị.


KIỂM TRA MÔ HÌNH GLB — V221
- MODEL-AUDIT-VI.txt ghi lại số liệu cấu trúc của lam-default.glb và các giới hạn chưa thể kết luận bằng metadata.
- Mô hình có 85 mesh, 8.036 đỉnh POSITION, 11.268 tam giác, 17 khớp, 4 material, 12 tên morph trên 6 mesh và 6 animation thử biến dạng.
- GLB không nhúng texture ảnh; animation hiện tại mang tên Deform_Test. Đây là quan sát từ metadata, không phải kết luận mô hình hiển thị xấu.
- Chất lượng khuôn mặt, biểu cảm và biến dạng khớp vẫn cần kiểm tra trực quan từng trường hợp trên trình duyệt.


ĐIỀU CHỈNH MORPH — V222
- Trong chế độ ?diagnostics=1, mỗi morph chuẩn có thanh trượt từ 0 đến 1 với bước 0,05 và giá trị số hiển thị trực tiếp.
- Các preset Nụ cười, Chớp mắt, Mở miệng nói, F/V và Môi tròn đồng bộ lại vị trí thanh trượt.
- “Đưa về trung tính” đặt các giá trị thử về 0; “Trở lại điều khiển API” rời chế độ thử morph cục bộ.
- V222 cũng sửa thứ tự khởi tạo thanh công cụ để chế độ chẩn đoán không tham chiếu biến trước khi khởi tạo.


KIỂM TRA DELTA BIỂU CẢM — V223
- MORPH-DELTA-AUDIT-VI.txt ghi lại những morph thực sự làm thay đổi POSITION và các mesh nhận biến dạng.
- Cả 12 morph chuẩn đều có ít nhất một delta POSITION khác 0; blink_left/right tác động lên từng mắt tương ứng, brow_raise tác động lên hai lông mày, còn nhóm hàm/miệng tác động lên mouth và/hoặc chin.
- Đây là kết quả đọc dữ liệu số trong GLB, chưa khẳng định hình ảnh biến dạng tự nhiên hoặc đúng giải phẫu.


TỔ HỢP BIỂU CẢM — V224
- Bổ sung ba preset để kiểm tra biểu cảm kết hợp: Cười + chớp mắt, Cười khi nói, Môi tròn khi nói.
- Nút preset có trạng thái aria-pressed để hỗ trợ nhận biết bằng công nghệ trợ năng; trạng thái được xóa khi kéo thanh morph, đặt trung tính hoặc trở lại chế độ API.
- Các preset chỉ là điểm khởi đầu cho kiểm tra; chưa chứng minh biểu cảm tự nhiên.


V225 — BẢN GHI TỔ HỢP BIỂU CẢM
- Tạo JSON để lưu trọng số morph hiện tại và áp dụng lại sau này.
- Bản ghi có schema/version và tên asset; từ chối schema sai, asset khác, morph lạ hoặc trọng số không hợp lệ.
- Xem EXPRESSION-SNAPSHOT-VI.txt để biết cách dùng và giới hạn.


BỘ CA CHUẨN HÓA VÀ ĐÁNH GIÁ (V227)
- expression-baseline-cases-v1.json cung cấp 12 ca thử có trọng số lặp lại được; đây là preset tạm thời, chưa phải chuẩn hình ảnh đã xác minh.
- EXPRESSION-EVALUATION-VI.txt hướng dẫn giữ điều kiện chụp, lưu bằng chứng và chấm điểm trực quan 0–4.
- Chỉ số delta morph không tự cho biết biểu cảm đẹp hơn. Chưa xác minh trực quan trên trình duyệt hoặc iPhone thật.


CHẠY CA THỬ TƯƠNG TÁC — V228
- Mở ?diagnostics=1 để bật bảng chẩn đoán.
- Trong mục “Bộ ca thử chuẩn hóa”, chọn một trong 12 ca rồi bấm “Áp dụng ca thử”.
- Giao diện tải expression-baseline-cases-v1.json cùng thư mục, kiểm tra schema, asset và các trọng số trước khi áp dụng.
- Ghi chú kiểm tra trực quan của ca được hiển thị sau khi áp dụng. Lưu snapshot và ảnh chụp theo EXPRESSION-EVALUATION-VI.txt.
- Các ca còn là preset tạm thời; cần xác minh trực quan, chưa được coi là chuẩn vàng.


PHIẾU ĐÁNH GIÁ BIỂU CẢM — V229
- Chọn và áp dụng một ca thử trước; thay đổi morph bằng tay sẽ hủy liên kết với ca đã áp dụng để tránh gắn nhầm ID.
- Nhập phiên bản và thiết bị/trình duyệt, chấm 5 tiêu chí từ 0–4 hoặc N/A, ghi quan sát và tên ảnh bằng chứng nếu có.
- Bấm “Tạo phiếu JSON” để tạo bản ghi có kèm snapshot trọng số hiện tại; sao chép JSON và lưu cùng ảnh bằng chứng ở bên ngoài.
- Có thể dùng “Kiểm tra phiếu JSON” để xác minh dữ liệu trước khi lưu. Không có lưu trữ đám mây hay gửi dữ liệu lên máy chủ.
- Điểm do con người nhập; công cụ không tự đánh giá chất lượng ảnh, không lưu file ảnh và không tự động ghi vào ổ đĩa.


SO SÁNH PHIẾU ĐÁNH GIÁ — V230
- Dán hai phiếu JSON của cùng một ca thử vào mục “So sánh phiếu đánh giá giữa phiên bản”.
- Báo cáo so sánh điểm từng tiêu chí, trung bình các điểm số hợp lệ (bỏ qua N/A), ghi chú và tên tệp bằng chứng.
- Nếu cả hai phiếu có snapshot tương thích, báo cáo thêm delta trọng số morph; đây là số học, không phải kết luận chất lượng hình ảnh.
- Chỉ so sánh các phiếu cùng case ID. Khác asset hoặc tập morph sẽ bị từ chối; dữ liệu vẫn chỉ xử lý cục bộ.


V231 — XUẤT BÁO CÁO SO SÁNH JSON
Trong ?diagnostics=1, sau khi so sánh thành công hai phiếu đánh giá cùng ca, bấm “Tạo báo cáo JSON”. Báo cáo chứa phiên bản, thiết bị/trình duyệt, người đánh giá, điểm từng tiêu chí, ghi chú, tên tệp bằng chứng và so sánh snapshot nếu có. Dùng nút kiểm tra để xác minh schema trước khi sao chép/lưu JSON. Báo cáo được tạo cục bộ, không tự lưu tệp và không gửi lên máy chủ.
Báo cáo nêu rõ giới hạn khi thiết bị khác nhau hoặc thiếu tên tệp bằng chứng; dữ liệu morph chỉ là số học và không chứng minh chất lượng hình ảnh.


V232 — TỔNG HỢP NHIỀU BÁO CÁO ĐÁNH GIÁ
- Trong ?diagnostics=1, dán một mảng JSON gồm các báo cáo so sánh V231 hợp lệ rồi bấm “Tổng hợp báo cáo”.
- Kết quả nhóm theo case ID, hiển thị số báo cáo, delta trung bình và số lần từng tiêu chí tăng/giữ nguyên/giảm.
- Có thể sao chép JSON đầu ra để lưu riêng. Tính toán cục bộ, không gửi dữ liệu lên máy chủ và không tự lưu tệp.
- Tổng hợp chỉ phản ánh điểm do người đánh giá nhập; khác biệt thiết bị, ánh sáng, người chấm và bằng chứng vẫn có thể làm sai lệch kết luận.

V233 — KIỂM TRA TÊN TỆP BẰNG CHỨNG
- Trong ?diagnostics=1, dán mảng báo cáo JSON và chọn các ảnh liên quan bằng bộ chọn tệp cục bộ.
- Công cụ đối chiếu tên tệp A/B với basename của các tệp được chọn, phân loại khớp duy nhất, thiếu, chưa ghi và trùng tên.
- Có thể sao chép JSON kiểm tra để lưu riêng. Không tải ảnh lên máy chủ và không tự lưu tệp.
- Đây chỉ là kiểm tra tham chiếu tên tệp; không đọc nội dung ảnh, không xác nhận ảnh đúng ca thử/phiên bản và không tự đánh giá chất lượng biểu cảm.

V234 — DẤU VÂN TAY SHA-256 CHO BẰNG CHỨNG
- Trong ?diagnostics=1, nhập mảng báo cáo và chọn các ảnh; công cụ đối chiếu tên tệp rồi tính SHA-256 cho byte của từng tệp đã chọn ngay trong trình duyệt.
- Báo cáo lưu manifest gồm tên tệp, kích thước, MIME type do trình duyệt cung cấp, SHA-256 và chỉ số tệp; tham chiếu khớp duy nhất nhận kèm hash tương ứng.
- Hash giống nhau cho biết các byte đã chọn giống nhau theo SHA-256; hash không chứng minh nguồn gốc, điều kiện chụp, ca thử hay chất lượng biểu cảm.
- Không tải tệp lên máy chủ và không tự lưu. Nếu Web Crypto không khả dụng, công cụ báo lỗi thay vì giả vờ tạo hash.


V235 — ƯU TIÊN KHỞI CHẠY ỨNG DỤNG
- Tách các mô-đun chẩn đoán/đánh giá khỏi đường khởi chạy mặc định; chỉ nạp chúng khi ?diagnostics=1.
- Thêm thông báo dự phòng sau 15 giây nếu mã ứng dụng chưa khởi chạy được, hữu ích khi CDN hoặc WebGL gặp sự cố.
- Gắn trạng thái tải bằng role=status và aria-live để thông báo dễ được công nghệ trợ năng đọc.
- Vẫn cần Internet để tải Three.js từ jsDelivr; chưa đóng gói thư viện Three.js cục bộ và chưa xác minh trực quan trên iPhone/Safari thật.


V242 — KIỂM TRA SẴN SÀNG THƯ VIỆN TỰ LƯU TRỮ
- Startup preflight phân biệt rõ trường hợp chưa có vendor/three với thư mục vendor đã tồn tại nhưng thiếu tệp bắt buộc.
- Nếu đủ tệp, preflight kiểm tra package.json có đúng three@0.160.0; thư mục thiếu tệp hoặc sai phiên bản được báo lỗi.
- Công cụ staging giữ lại thư viện hiện tại trong lúc thay thế và phục hồi nếu bước chuyển thư mục mới thất bại.
- Đây là bảo vệ quy trình đóng gói; không có nghĩa thư viện Three.js đã được tải vào gói hoặc avatar đã được render xác minh.

V240 — KIỂM TRA KHẢ NĂNG TRUY CẬP CDN
- Chạy tùy chọn `node tools/cdn-connectivity-check.cjs` để kiểm tra ba URL đã cấu hình: Three.js core, GLTFLoader và OrbitControls.
- Mỗi yêu cầu có timeout hữu hạn; lỗi DNS, TLS, kết nối hoặc HTTP không thành công được báo riêng theo URL.
- Công cụ không tải/lưu thư viện và không làm kiểm thử gói phụ thuộc vào Internet. Kết quả chỉ phản ánh môi trường đang chạy lệnh, không chứng minh iPhone/Safari hoặc host triển khai có cùng kết quả.

GITHUB PAGES TỰ LƯU TRỮ THREE.JS (V244)
- Quy trình GitHub Actions hiện tự tải chính thức three@0.160.0, staging vào vendor/three, chuyển bản triển khai để mặc định dùng thư viện nội bộ, rồi chạy startup preflight và HTTP smoke test trước khi publish.
- Bản ZIP nguồn vẫn giữ CDN làm mặc định; chỉ bản triển khai qua workflow được đổi sang dùng local vendor theo mặc định.
- Trên trang Pages đã triển khai, thêm `?three=cdn` vào URL để chọn lại CDN nếu cần chẩn đoán. Không thêm tham số thì dùng `vendor/three`.
- Nếu npm registry không truy cập được hoặc staging/preflight thất bại, workflow dừng và không publish bản mới.
- Công cụ `tools/prepare-pages-deploy.cjs` kiểm tra đủ tệp và đúng `three@0.160.0` trước khi sửa bộ chọn import map; chạy độc lập trên gói nguồn chưa có `vendor/three` sẽ bị từ chối.
- Kiểm thử cục bộ dùng gói fixture để xác nhận logic build; môi trường hiện tại không phân giải được registry.npmjs.org nên chưa xác nhận tải thật qua GitHub Actions. Render trực quan trên trình duyệt và iPhone vẫn chưa được xác minh.


V246 — KIỂM THỬ AN TOÀN CHUẨN BỊ GITHUB PAGES
- Bổ sung kiểm thử hồi quy theo luồng đầy đủ với thư mục vendor giả lập: thiếu thư viện thì quy trình phải dừng và không được sửa index.html.
- Khi đủ gói đúng phiên bản, kiểm thử xác nhận bản triển khai mặc định dùng vendor/three và vẫn giữ lựa chọn `?three=cdn`.
- Chạy chuẩn bị nhiều lần phải cho kết quả giống nhau, không sửa đổi HTML thêm ở lần tiếp theo.
- Chỉ kiểm chứng logic build bằng fixture; không thay thế việc tải Three.js thật, triển khai Pages hoặc xác nhận render avatar trên trình duyệt/iPhone.


V247 — DỰ PHÒNG TRIỂN KHAI KHI NPM KHÔNG KHẢ DỤNG
- GitHub Actions vẫn ưu tiên tải Three.js 0.160.0 và chuẩn bị bản tự lưu trữ. Nếu tải npm thất bại, workflow phát cảnh báo và tiếp tục triển khai ở chế độ CDN mặc định thay vì chặn toàn bộ bản xem thử. Trong trường hợp dự phòng, trình duyệt người xem vẫn cần truy cập được jsDelivr.
- Khi tải thư viện thành công, bước chuẩn bị Pages và kiểm tra liên kết module vẫn bắt buộc. Kiểm tra preflight và HTTP chạy trong cả hai nhánh. Đây là cơ chế phục hồi triển khai, không phải bằng chứng avatar đã render trên trình duyệt thật.


V248 — CHỈ DỰ PHÒNG CDN KHI LỖI MẠNG
- Thu hẹp nhánh dự phòng V247: chỉ cho phép tiếp tục ở chế độ CDN nếu bước tải npm gặp lỗi mạng/DNS/timeout được nhận diện rõ.
- Nếu lỗi do sai phiên bản, gói thiếu tệp, lỗi staging hoặc lỗi chương trình, GitHub Actions dừng triển khai thay vì âm thầm chuyển sang CDN.
- Bổ sung regression assertion cho marker đầu ra của GitHub Actions và điều kiện dừng an toàn.
- Chưa xác minh tải npm thật hoặc render avatar trong trình duyệt/iPhone.


PHÂN LOẠI LỖI DỰ PHÒNG CDN (V249)
- Quy trình GitHub Pages chỉ được phép chuyển sang CDN khi công cụ tải Three.js gặp chữ ký lỗi mạng/DNS/socket cụ thể như EAI_AGAIN, ENOTFOUND, ETIMEDOUT, ECONNRESET, ECONNREFUSED hoặc ERR_SOCKET_TIMEOUT.
- Các từ chung như “network” hoặc “fetch” không đủ để kết luận là lỗi mạng, tránh cho lỗi cấu hình/gói npm bị che giấu bởi phương án dự phòng.
- Kiểm thử mô phỏng nhiều mã lỗi mạng và các thông báo dễ gây nhầm lẫn. Vẫn cần chạy GitHub Actions trên môi trường có mạng và kiểm tra render trình duyệt thật.

V250 — THEO DÕI ĐẾN KHI MÔ HÌNH THỰC SỰ TẢI XONG
- Bộ đếm 15 giây không còn dừng ngay sau khi renderer khởi tạo; nó tiếp tục theo dõi cho đến khi GLB tải thành công hoặc có lỗi khởi chạy rõ ràng.
- Trạng thái tách riêng renderer sẵn sàng (`window.__lyLamRendererReady`) và avatar đã tải xong (`window.__lyLamAppBooted`).
- Khi trình duyệt cung cấp tổng số byte, dòng trạng thái hiển thị tiến độ tải mô hình.
- Nếu tải GLB thất bại, trang giữ thông báo cụ thể thay vì để watchdog ghi đè sau đó.
- Đây là cải thiện quan sát và phản hồi lúc khởi chạy; chưa thay thế kiểm thử render thực tế trên Safari/iPhone.


V251 — KHÔI PHỤC KHỞI CHẠY BẰNG NÚT THỬ LẠI
- Thêm nút “Thử tải lại” vào bảng trạng thái khi lỗi khởi chạy, lỗi mô-đun, lỗi tải GLB hoặc hết thời gian chờ. Nút tải lại toàn bộ trang để thử lại sau khi khắc phục mạng/tài nguyên.
- Tách nội dung trạng thái vào `#status-message`; cập nhật tiến độ tải GLB không còn thay toàn bộ phần tử trạng thái và vô tình xóa nút thử lại.
- Đây là đường phục hồi UX cho lỗi tạm thời, không tự sửa lỗi CDN hay thay thế xác minh render.


CHẨN ĐOÁN KHỞI CHẠY V252
- Nếu ứng dụng chưa tải xong sau 15 giây, thông báo hiển thị trạng thái online/offline do trình duyệt báo, chế độ Three.js (CDN hoặc nội bộ), khả năng tạo WebGL context và URL đang mở.
- Trạng thái online của trình duyệt không đảm bảo CDN truy cập được; đây chỉ là thông tin giúp khoanh vùng. Nếu đã khắc phục kết nối/tài nguyên, bấm “Thử tải lại”.
- Thông tin chẩn đoán được tạo ngay trong trình duyệt; không tự gửi lên máy chủ.

V253 — LÀM RÕ LỖI TẢI MÔ HÌNH GLB
- Khi GLTFLoader báo lỗi, trạng thái nêu đường dẫn tài sản, phân loại thận trọng lỗi mạng/quyền truy cập hoặc lỗi đọc/phân tích GLB, thông điệp lỗi nếu có và thông tin chẩn đoán khởi chạy V252.
- Không tự suy đoán mã HTTP vì GLTFLoader không phải lúc nào cũng cung cấp mã đó. Nút “Thử tải lại” vẫn được giữ.
- Chưa xác minh truy cập CDN thực tế, render trình duyệt hoặc Safari trên iPhone trong môi trường hiện tại.


LÝ LÂM LAM V254 — KHÔI PHỤC WEBGL
- Khi WebGL mất context, giao diện hiện nút thử tải lại thay vì chỉ đưa ra lời nhắc.
- Khi context được khôi phục, trạng thái được cập nhật; nút thử tải lại chỉ ẩn nếu mô hình đã tải xong.
- Đã thêm kiểm thử hồi quy cho luồng giao diện này. Kiểm thử mã không thay thế thử nghiệm GPU/Safari thực tế.


## V255 — Chuyển chế độ Three.js khi khởi chạy lỗi
Khi ứng dụng hiện nút thử lại sau lỗi khởi chạy, có thêm nút chuyển giữa CDN jsDelivr và thư viện nội bộ. Nút giữ nguyên các tham số URL khác (ví dụ diagnostics=1). Chế độ nội bộ chỉ hoạt động nếu gói triển khai đã có `vendor/three`; nút này không tự tải hay tạo thư viện bị thiếu.


## V256 — Kiểm tra trước khi chuyển sang Three.js nội bộ

Khi chuyển từ CDN sang chế độ nội bộ, ứng dụng kiểm tra URL `vendor/three/build/three.module.js` trước. Nếu tệp chưa được triển khai hoặc máy chủ không truy cập được, trang giữ nguyên URL/chế độ hiện tại và báo lý do thay vì chuyển sang chế độ chắc chắn không khởi chạy. Kiểm tra HEAD chỉ xác nhận phản hồi của tệp lõi; không thay thế kiểm thử addon hay render thực tế.


## V257 — Kiểm tra các tài nguyên đầu vào của chế độ Three.js nội bộ

Trước khi chuyển sang chế độ nội bộ, ứng dụng kiểm tra song song bốn URL đầu vào: Three.js core, GLTFLoader, OrbitControls và lam-default.glb. Nếu một hoặc nhiều URL không truy cập được, giao diện liệt kê từng URL cùng mã HTTP và giữ nguyên chế độ hiện tại. Đây là kiểm tra đầu vào, không chứng minh mọi module phụ thuộc đều tồn tại hoặc avatar render thành công.


## V259 — Chặn triển khai khi đồ thị import Three.js bị lỗi

Trước khi đổi cấu hình GitHub Pages sang mặc định dùng `vendor/three`, công cụ chuẩn bị triển khai chạy bộ kiểm tra toàn bộ import tương đối trong các mô-đun Three.js. Nếu thiếu module phụ thuộc, quy trình dừng trước khi sửa `index.html`; cấu hình CDN/local ban đầu được giữ nguyên. Điều này bổ sung lớp bảo vệ trước triển khai, bên cạnh kiểm tra staging V258. Chưa có gói Three.js chính thức trong working tree; chưa xác minh render trình duyệt/Safari iPhone.


V262 — CHUẨN BỊ GITHUB PAGES THEO CƠ CHẾ NGUYÊN TỬ
- Công cụ chuẩn bị Pages xác thực cả cấu hình import map dự kiến trước khi ghi bất kỳ thay đổi nào vào index.html.
- Khi cần đổi bộ chọn CDN/local, nội dung mới được ghi vào tệp tạm cạnh index.html rồi thay thế bằng rename; nếu xác thực ứng viên thất bại, HTML gốc được giữ nguyên.
- Kiểm thử hồi quy bao gồm trường hợp vendor hợp lệ nhưng import map bị thiếu đường dẫn bắt buộc, xác nhận không sửa HTML và không để lại tệp tạm.
- 87/87 kiểm thử tự động đạt. Chưa có gói Three.js chính thức trong môi trường hiện tại; chưa xác minh deploy GitHub Pages hoặc render trên trình duyệt/iPhone.


## V264 — Kiểm chứng thực thi chốt SHA-512

Bản V264 bổ sung kiểm thử chạy thật công cụ lấy thư viện với tarball giả và npm giả. Khi mã SHA-512 được cấu hình sai, công cụ phải từ chối trước khi gọi npm và không được tạo `vendor/three`. Kiểm thử này chứng minh nhánh từ chối hoạt động; nó không chứng minh đã có gói Three.js chính thức hay avatar đã render.

## V265 — Kiểm chứng cả nhánh chấp nhận tarball

V265 bổ sung kiểm thử chạy thật cho trường hợp mã SHA-512 khớp, với cả dạng hex và SRI theo chuẩn npm. Kiểm thử xác nhận bước kiểm tra integrity được thông qua trước khi gọi npm; npm giả dừng có chủ đích trước staging. Kết hợp V264, cả nhánh từ chối pin sai và nhánh chấp nhận pin đúng đều có kiểm thử thực thi. Tệp tarball dùng trong kiểm thử là fixture, không phải gói Three.js chính thức.

GHI CHÚ V266 — GHIM SHA-512 CHO TARBALL NGOẠI TUYẾN
Khi cung cấp gói Three.js qua biến THREE_TARBALL, có thể đặt THREE_TARBALL_SHA512 bằng SHA-512 dạng hex 128 ký tự hoặc SRI dạng sha512-BASE64. Để bắt buộc phải có mã đối chiếu, đặt THREE_TARBALL_REQUIRE_SHA512=1. Khi bật chế độ này mà thiếu mã đối chiếu, quy trình từ chối trước khi gọi npm. Chỉ dùng mã SHA-512 lấy từ nguồn đáng tin cậy; mã tự tính từ cùng một tệp không chứng minh nguồn gốc chính thức.


V270 — ĐÓNG GÓI TỐI THIỂU CHO GITHUB PAGES
--------------------------------------------------
Workflow triển khai hiện tạo artifact riêng bằng:
  node tools/prepare-pages-artifact.cjs dist
và chỉ tải thư mục dist/ lên GitHub Pages. Artifact giữ index.html, module ứng dụng,
GLB, JSON ca thử, các mô-đun JS ở thư mục gốc, .nojekyll và vendor/three nếu đã có.
Không công khai thư mục tests/, tools/ hoặc các tài liệu nội bộ trong artifact.
Công cụ xác minh các import tương đối tĩnh trước khi hoàn tất artifact.
Lưu ý: nếu vendor/three chưa được cung cấp, bản CDN vẫn cần trình duyệt truy cập CDN.
Đóng gói tối thiểu không thay thế cho kiểm thử render trên trình duyệt thật.

V272 — AN TOÀN ĐẦU VÀO ARTIFACT GITHUB PAGES
- Bộ dựng artifact dùng `lstat` để từ chối symbolic link ở các tài nguyên bắt buộc và mô-đun JavaScript cấp gốc, tránh vô tình theo liên kết ra ngoài khi sao chép.
- Nếu kiểm tra đầu vào thất bại, artifact hợp lệ trước đó được giữ nguyên.
- Kiểm thử V272 mô phỏng symbolic link tới tệp ngoài và xác nhận quá trình đóng gói bị từ chối.
- Đây là bảo vệ cấu trúc gói công khai, không chứng minh Three.js đã được tải hoặc avatar render trên trình duyệt.


### V273 — tăng độ bền khi lấy Three.js
- Bước tải npm thử lại tối đa hai lần với khoảng chờ có giới hạn; mỗi yêu cầu có timeout 15 giây và tiến trình tải bị giới hạn 60 giây. GitHub Actions giới hạn riêng bước này ở 3 phút.
- Mục tiêu là tránh chuyển sang CDN chỉ vì một lỗi mạng thoáng qua, đồng thời vẫn tránh chờ vô hạn. Không có nghĩa Three.js đã được tải thành công trong môi trường hiện tại; cần xem kết quả workflow thực tế.


### V274 — kiểm tra HTTP trên đúng artifact sẽ triển khai
- `node tools/static-http-smoke.cjs` tiếp tục kiểm tra thư mục nguồn như trước; có thể truyền đường dẫn thư mục làm đối số, ví dụ `node tools/static-http-smoke.cjs dist`.
- GitHub Actions chạy smoke test lần nữa sau khi tạo `dist/`, trước khi tải artifact lên GitHub Pages. Vì vậy các kiểm tra GET/HEAD, MIME, GLB, 404 và chống path traversal áp dụng cho đúng bộ tệp công khai đã đóng gói.
- Đây vẫn là máy chủ HTTP cục bộ mô phỏng, không phải xác nhận trang Pages đã lên mạng hoặc avatar đã render trên Safari/iPhone thật.


### V275 — triển khai đóng khi thiếu Three.js tự lưu trữ
- Workflow GitHub Pages không còn tiếp tục xuất bản ở chế độ CDN nếu tải/đóng gói `three@0.160.0` thất bại. Đây là lựa chọn fail-closed: thà dừng deployment có lỗi còn hơn báo triển khai thành công nhưng ứng dụng lại phụ thuộc CDN ngoài dự kiến.
- Bước chuyển import map sang local và kiểm tra toàn vẹn đồ thị module vendor đều bắt buộc trước khi tạo artifact.
- Nếu runner không truy cập được npm và không có tarball đã xác minh, deployment sẽ thất bại rõ ràng; điều này không có nghĩa bản local đã có Three.js. Cần kiểm tra kết quả workflow trên GitHub để xác nhận acquisition thực tế.


### V276 — loại bỏ tín hiệu CDN dự phòng cũ
- Script tải Three.js không còn ghi `fallback=true` vào `GITHUB_OUTPUT` khi gặp lỗi DNS/socket. Tín hiệu này không còn được workflow dùng từ V275 nhưng vẫn có thể gây hiểu nhầm cho workflow tùy biến hoặc người vận hành.
- Khi lỗi mạng xảy ra, script chỉ in hướng dẫn bằng văn bản và kết thúc với mã lỗi; không có cờ máy đọc được nào cho phép chuyển sang CDN.
- Kiểm thử hồi quy mô phỏng lỗi `EAI_AGAIN`, xác nhận tiến trình thất bại, không tạo tệp output dự phòng và hiển thị hướng dẫn rõ ràng.

## V277 — Cache gói Three.js trên GitHub Actions

- Workflow khôi phục cache npm (`~/.npm`) trước bước lấy `three@0.160.0`, dùng khóa theo hệ điều hành, phiên bản thư viện và nội dung công cụ lấy gói.
- Cache giúp những lần triển khai sau ít phụ thuộc vào việc tải lại từ registry; cache không bảo đảm có sẵn trong lần chạy đầu hoặc sau khi bị xóa.
- Quy trình vẫn fail-closed: nếu không lấy được thư viện từ cache hoặc registry, deployment phải dừng, không chuyển sang CDN.
- Chưa xác minh được workflow trên GitHub-hosted runner hoặc render avatar thật trong môi trường này.


## V278 — lưu cache npm kể cả khi tải Three.js thất bại

- Thêm bước `actions/cache/save@v4` sau bước lấy Three.js, với `if: always()`, để giữ metadata/tarball npm đã tải được trước khi gặp lỗi mạng tạm thời.
- Cache được lưu dưới cùng khóa phiên bản/hệ điều hành với bước khôi phục. Nếu khóa đã tồn tại, cache bất biến có thể không được ghi đè; khi đó workflow vẫn giữ hành vi an toàn.
- Đây không phải phương án CDN dự phòng và không cho phép triển khai tiếp khi bước lấy Three.js thất bại.
- Kiểm thử tĩnh xác nhận bước lưu cache chạy sau bước lấy gói và trước bước chuẩn bị deployment.
- Chưa thể xác nhận cache thực sự được lưu trên GitHub Actions hoặc avatar render; cần xem workflow run thực tế.


## V279 — Không ghi đè cache npm đã khớp chính xác
- Bước khôi phục cache có ID `npm-cache`.
- Bước lưu cache vẫn chạy sau lỗi lấy Three.js để giữ dữ liệu tải dở, nhưng bỏ qua khi đã khôi phục đúng khóa cache chính; tránh thử ghi đè một cache bất biến đã tồn tại.
- Điều này cải thiện độ tin cậy của workflow; chưa chứng minh cache GitHub hoặc triển khai Pages thực tế nếu chưa chạy trên runner.


## V281 — Có đường nhập tarball Three.js đã ghim SHA-512 qua GitHub Actions

- Khi chạy thủ công workflow Deploy, có thể cung cấp `three_tarball_path` là đường dẫn tương đối tới gói `three-0.160.0.tgz` đã được đưa vào repository, cùng `three_tarball_sha512` lấy từ nguồn đáng tin cậy.
- Workflow truyền giá trị qua biến môi trường, không chèn đường dẫn/mã băm vào lệnh shell; công cụ tải bắt buộc có mã SHA-512 và từ chối nếu thiếu hoặc không khớp trước khi giải nén.
- Để trống hai đầu vào thì quy trình vẫn dùng cache npm rồi thử registry như trước. Lỗi lấy thư viện vẫn chặn triển khai, không chuyển sang CDN.
- Đây là đường thay thế cho trường hợp runner không truy cập registry npm được, nhưng chỉ hữu ích khi tarball đã được đưa vào repository và mã SHA-512 được xác nhận từ nguồn đáng tin cậy. Chưa có tarball chính thức trong môi trường hiện tại; chưa xác nhận triển khai GitHub Pages hoặc render avatar thật.


## V284 — Sửa URL chế độ Three.js nội bộ khi khởi chạy xem trước

- Khắc phục lỗi điều phối giữa launcher và trang: trước đây launcher có thể phát hiện đủ thư viện nội bộ nhưng URL in ra vẫn không có `?three=local`, khiến trang tiếp tục chọn CDN.
- Máy chủ xem trước nhận `--three cdn|local` và in URL đúng chế độ; các địa chỉ LAN cho iPhone cũng mang đúng tham số.
- Nếu thiếu thư viện nội bộ, launcher tiếp tục dùng CDN và thông báo cần Internet; tùy chọn `--local-three` vẫn dừng an toàn khi thiếu tài nguyên.
- Chưa có thư viện Three.js chính thức trong môi trường này nên chưa xác minh render avatar thật.


## V286 — Tự thử CDN thay thế một lần khi khởi chạy sớm thất bại

- Nếu trang gặp lỗi trước khi renderer Three.js sẵn sàng khi dùng đường mặc định jsDelivr, ứng dụng tự tải lại một lần với CDN unpkg, vẫn ghim `three@0.160.0`.
- Dùng `sessionStorage` để chặn vòng lặp tải lại; giữ các tham số URL khác và phần hash. Khi ứng dụng khởi chạy thành công, dấu đánh dấu thử lại được xóa.
- Không tự đổi CDN khi đã chọn `three=local`, `three=unpkg`, hoặc khi lỗi được nhận diện là lỗi WebGL/renderer. Nút chuyển chế độ thủ công và kiểm tra fail-closed của thư viện nội bộ vẫn được giữ.
- Kiểm thử hồi quy xác minh nhánh thử lại một lần và giới hạn tránh vòng lặp. Môi trường phát triển hiện không phân giải được jsDelivr/unpkg (`EAI_AGAIN`), nên chưa xác nhận tải CDN thật, render avatar, GitHub Pages hoặc Safari/iPhone.

## V287 — Dự phòng khi tải module bị treo

- Watchdog 15 giây giờ thử CDN unpkg một lần nếu ứng dụng chưa khởi chạy và chưa ghi nhận lỗi; trước đây tình huống tải treo có thể chỉ hiện nút thử lại mà không tự chuyển nguồn.
- Sửa thông tin chẩn đoán để nhận diện chính xác chế độ unpkg.
- Kiểm thử tự động bao gồm nhánh timeout; cần thử trình duyệt thật để xác nhận tải CDN và render 3D.


## V289 — Tạo gói Three.js ngoại tuyến có xác minh SHA-512

Mục tiêu là vượt nút thắt khi môi trường dự án không truy cập được npm registry:

1. Trên một máy có Internet, giải nén bản V289 và chạy `node tools/export-three-offline-bundle.cjs --out three-offline-bundle`.
2. Công cụ truy vấn `npm view three@0.160.0 dist.integrity --json`, tải đúng bản bằng `npm pack`, rồi tự tính SHA-512 và so khớp với metadata npm. Nếu không khớp, công cụ từ chối xuất gói.
3. Chuyển cả `three-0.160.0.tgz` và `THREE-OFFLINE-MANIFEST.txt` sang máy/môi trường ngoại tuyến. Giữ nguyên tarball, không giải nén rồi nén lại.
4. Từ thư mục dự án trên máy ngoại tuyến, chạy lệnh dùng đúng SHA-512 SRI ghi trong manifest:

   `THREE_TARBALL="/đường/dẫn/three-0.160.0.tgz" THREE_TARBALL_SHA512="sha512-..." THREE_TARBALL_REQUIRE_SHA512=1 node tools/fetch-vendor-three.cjs`

   Trên PowerShell, đặt ba biến môi trường tương ứng trước khi chạy lệnh Node.
5. Khi staging hoàn tất, chạy `node tools/startup-preflight.cjs`, `node tools/vendor-module-integrity.cjs` và `node tools/start-preview.cjs --local-three`.

`export-three-offline-bundle.cjs` chỉ tạo gói từ npm khi chạy trên máy có mạng; môi trường phát hành hiện tại vẫn không truy cập được registry, vì vậy chưa có tarball chính thức được đưa vào ZIP này. Chưa xác minh render avatar, triển khai Pages hoặc Safari/iPhone thật.

LÝ LÂM LAM V289 — XUẤT GÓI THREE.JS NGOẠI TUYẾN
=================================================
- Trên máy có Node.js/npm và Internet, chạy `node tools/export-three-offline-bundle.cjs --out three-offline-bundle`.
- Công cụ truy vấn `dist.integrity` của đúng `three@0.160.0`, tải tarball và tự tính SHA-512; nếu không khớp, không xuất gói.
- Chuyển cả `three-0.160.0.tgz` và `THREE-OFFLINE-MANIFEST.txt` sang máy/môi trường ngoại tuyến, sau đó dùng lệnh nhập V290 ở trên.
- Môi trường đóng gói hiện tại không truy cập được registry; chưa có tarball chính thức và chưa xác nhận render avatar.

---
CẬP NHẬT V302 (2026-10-11)
- Đã bổ sung thư viện Three.js 0.160.0 vào vendor/three từ gói V300 đã nhận, không tải từ mạng.
- Kiểm thử tự động: avatar-core 40/40; package-integrity 80/80; startup preflight PASS; vendor module integrity PASS.
- Chưa xác nhận avatar render trực tiếp trong trình duyệt; cần thử URL ?three=local qua HTTP/HTTPS.

V304 — KIỂM TRA KHỞI CHẠY BẰNG MỘT LỆNH
Từ thư mục lylamlam_work, chạy:
  node tools/verify-startup.cjs
Lệnh này chạy preflight, kiểm tra module Three.js, bài test hồi quy và HTTP smoke; lệnh dừng ngay ở bước lỗi đầu tiên. PASS không thay thế việc mở ứng dụng trong trình duyệt để xác minh WebGL và avatar thực tế.


V306 — KIỂM TRA MÁY CHỦ XEM THỬ THẬT
--------------------------------------
Chạy `node tools/verify-startup.cjs` để chạy toàn bộ kiểm tra. Bản V306 bổ sung kiểm tra tích hợp bằng cách khởi chạy máy chủ xem thử thật trên cổng ngẫu nhiên và kiểm tra trang, GLB, các mô-đun Three.js, phản hồi HEAD, lỗi 404 và bảo vệ đường dẫn. Kết quả tự động vẫn không chứng minh avatar đã render bằng WebGL; cần mở trang trong Chrome để xác nhận phần hình ảnh.


V308 — CHẨN ĐOÁN TRÌNH DUYỆT
Nếu trang bị treo hoặc không hiện avatar, bấm “Tạo báo cáo lỗi” ở thanh thông báo, rồi “Sao chép báo cáo” và gửi nội dung văn bản cho người hỗ trợ. Báo cáo kiểm tra WebGL và mã HTTP của các tệp chính; dữ liệu không tự gửi đi.
