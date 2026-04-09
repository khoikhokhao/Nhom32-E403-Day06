# SPEC Final — Nhóm 32 - Phòng E403

**Track Lựa Chọn:** VinFast

## 🎯 Tuyên Bố Vấn Đề (Problem Statement)
**Ai gặp vấn đề gì:** Khách hàng mua xe điện và chủ xe VinFast thường bị "ngợp" trước lượng thông tin phân tán (giá pin, sạc, bảo dưỡng), dẫn đến hành trình trải nghiệm bị đứt đoạn và tăng tải cho đội ngũ CSKH.
**AI giải quyết thế nào:** Một AI Agent hoạt động như "Copilot", tự động hóa việc tra cứu chính sách bằng hệ thống RAG nội bộ, chủ động xử lý đặt lịch qua Function Calling, và có cơ chế chuyển tuyến khẩn cấp khi gặp sự cố an toàn.

---

## 1. AI Product Canvas

| | Value (Giá trị) | Trust (Niềm tin) | Feasibility (Khả thi) |
|---|---|---|---|
| **Trả lời** | **User:** (1) Khách tìm hiểu xe mới; (2) Chủ xe cần hỗ trợ kỹ thuật/đặt lịch.<br><br>**Pain points:** Tra cứu chính sách phức tạp; chờ tổng đài lâu.<br><br>**AI Solutions:** AI Agent giải đáp 24/7 từ kho dữ liệu JSON nội bộ; tự động hỏi thiếu thông tin để chốt lịch bằng Agent Tool. | **Hậu quả khi sai:** Gợi ý sai giá gây phàn nàn; hướng dẫn xử lý cảnh báo lỗi xe sai gây nguy hiểm tính mạng.<br><br>**Xây dựng Trust:** In rõ cấu trúc lệnh Đặt lịch (Tên, SĐT, Giờ, Địa điểm) ra màn hình để khách xác nhận.<br><br>**Sửa lỗi:** Xử lý qua hội thoại. Khách chat đính chính (VD: "Tôi gõ nhầm giờ"), AI tự hiểu context và ghi đè thông tin mới. | **Tech Stack:** RAG Pipeline (Weighted Scoring + Intent Mapping) kết hợp OpenAI Native Function Calling.<br><br>**Costs:** API GPT-4o-mini rất rẻ (~$0.01/chat), độ trễ thấp.<br><br>**Risks chính:** Semantic Gap (Khách hỏi tiếng Việt, Data tag tiếng Anh) -> Đã xử lý bằng code Intent Mapping. |

**Automation hay Augmentation?** ☐ Automation · ☑ Augmentation
**Justify:** Mua xe ô tô là quyết định lớn, lỗi kỹ thuật liên quan đến tính mạng. AI đóng vai trò tư vấn và trích xuất tham số (Augmentation). Quyết định cuối cùng luôn thuộc về người dùng (chốt thông tin) và Kỹ thuật viên (xử lý lỗi).

**Learning Signal:**
1. **User correction đi vào đâu?** Trong phiên bản MVP, các đính chính của user được lưu trực tiếp vào Session State (lịch sử chat) để LLM tự sửa lỗi context. 
2. **Product thu signal gì để biết tốt lên/tệ đi?** Dựa vào File Log hội thoại. Đánh giá Tỉ lệ chốt form đặt lịch thành công (gọi hàm `book_service`) và Tỉ lệ kích hoạt tính năng chuyển người thật (gọi hàm `escalate_to_human`).
3. **Data thuộc loại nào?** User-specific (nhu cầu, sđt) + Domain-specific (Cẩm nang xe VF).

---

## 2. User Stories — 4 Paths

### Feature 1: AI Agent Tự động Đặt Lịch (Function Calling)
**Trigger:** User yêu cầu đặt lịch lái thử/bảo dưỡng.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** | User thấy gì? Flow kết thúc ra sao? | User nhập đủ thông tin. AI kích hoạt hàm `book_service`, UI bật khung thông báo xác nhận chốt lịch. |
| **Low-confidence** | System báo "không chắc" bằng cách nào? | User nói "đặt lịch bảo dưỡng". AI thiếu tham số (Tên, xe, sđt, giờ, địa điểm), nó dừng việc gọi Tool và chủ động chat hỏi lại người dùng để thu thập đủ. |
| **Failure** | User biết AI sai bằng cách nào? Recover ra sao? | AI trích xuất sai tên dòng xe (do khách gõ sai chính tả). Khách phát hiện lỗi khi nhìn vào Khung xác nhận trên UI. |
| **Correction** | User sửa bằng cách nào? | Khách hàng chat lại: *"Tôi đặt xe VF7 chứ không phải VF6"*. AI lập tức cập nhật Session History và phản hồi xác nhận lại thông tin đúng. |

### Feature 2: Safety Fallback (Cảnh báo an toàn khẩn cấp)
**Trigger:** User nhập triệu chứng lỗi xe.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** | User thấy gì? Flow kết thúc ra sao? | User báo "lỗi hệ thống phanh". AI nhận diện từ khóa nguy hiểm, kích hoạt Tool `escalate_to_human`, bật UI Cảnh báo ĐỎ, báo tấp lề và yêu cầu gọi Hotline. |
| **Low-confidence** | System báo "không chắc" bằng cách nào? | User báo "xe thỉnh thoảng kêu rít rít". Context mập mờ, AI từ chối chẩn đoán bệnh và khuyên mang xe qua xưởng kiểm tra. |
| **Failure** | User biết AI sai bằng cách nào? Recover ra sao? | Xe bốc khói nhưng AI tưởng lỗi nhẹ và khuyên "đi tiếp bình thường". **Hậu quả thảm khốc, user không biết AI sai.** |
| **Correction** | User sửa bằng cách nào? Data đi đâu? | (Quy trình vận hành): Team Product review file Log hàng tuần. Nếu phát hiện câu hỏi nguy hiểm bị miss, sẽ Hardcode cụm từ đó vào System Prompt hoặc bổ sung Data RAG để chặn đứng ở các lần sau. |

---

## 3. Eval Metrics & Threshold

**Optimize Precision hay Recall?** ☑ Recall (Đặc biệt cho Safety Triggers)
**Tại sao?** Bỏ sót một cảnh báo lỗi phanh (False Negative) khiến khách hàng gặp tai nạn tệ hơn rất nhiều so với việc cảnh báo nhầm (False Positive) và ép họ gọi Hotline.

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| **Recall (Safety Triggers)** - Khả năng nhận diện chính xác các từ khóa nguy hiểm. | ≥ 99% | < 95% trong 3 ngày liên tiếp (Nguy cơ an toàn). |
| **Groundedness Score** - Tỉ lệ câu trả lời dựa trên file `data.json` của hệ thống. | ≥ 95% | < 85% -> LLM bắt đầu có dấu hiệu ảo giác bịa thông tin. |
| **Task Completion Rate** - Tỉ lệ thu thập đủ 6 tham số để gọi hàm đặt lịch. | ≥ 40% | < 20% -> Agent hỏi vòng vo, khách bỏ ngang (Drop-off). |

---

## 4. Top 3 Failure Modes

| # | Trigger | Hậu quả | Mitigation (Giảm nhẹ) |
|---|---------|---------|------------|
| 1 | **Out-of-Domain/Jailbreak:** User hỏi giá cổ phiếu VFS hoặc cố tình thử thách AI. | AI trả lời lan man -> Mất hình ảnh chuyên nghiệp. | **System Prompt Guardrails:** Thiết lập lệnh ép AI phải từ chối lịch sự và chủ động lái câu chuyện về xe điện. |
| 2 | **Semantic Gap (Lệch ngữ nghĩa):** User hỏi "chạy bao xa", nhưng File Data lưu tag "range". | Hàm Search RAG quét trượt, AI không có context để trả lời. | Thiết kế thuật toán **Intent Mapping**, tự nhận diện từ khóa tiếng Việt và bơm keyword tiếng Anh vào hàm RAG trước khi quét. |
| 3 | **Cập nhật chính sách trễ:** File Data nội bộ chưa cập nhật giá mới. | AI gợi ý sai giá -> Khách khiếu nại. (Khách không biết bị sai lúc chat). | Bắt buộc AI sử dụng Disclaimer trong giao tiếp và cập nhật bản ghi `data.json` theo thời gian thực từ cơ sở dữ liệu hệ thống. |

---

## 5. Phân tích ROI - 3 Kịch bản Pilot

**Giả định:** Pilot với 15.000 lượt chat/tháng. Chi phí cố định (API + Server) ~15.000.000 VNĐ/tháng.

| | Conservative (Kém) | Realistic (Kỳ vọng) | Optimistic (Xuất sắc) |
|---|-------------|-----------|------------|
| **Tỉ lệ tự xử lý xong (Deflection)** | 15% | 35% | 55% |
| **Cost** | 15.000.000 VNĐ | 15.000.000 VNĐ | 15.000.000 VNĐ |
| **Benefit (Giờ CSKH tiết kiệm)**| 100 giờ (~20 Triệu) | 250 giờ (~50 Triệu) | 450 giờ (~90 Triệu) |
| **Net ROI (Giá trị ròng)** | **+ 5.000.000 VNĐ** | **+ 35.000.000 VNĐ** | **+ 75.000.000 VNĐ** |

**Kill Criteria:** Tạm dừng hệ thống nếu sau 2 tháng triển khai Net ROI âm, HOẶC điểm CSAT < 3.5/5 liên tục trong 2 tuần.

---

## 6. Mini AI Spec (Thông số kỹ thuật MVP)

### Scope & Tech Flow
- **Nền tảng MVP:** Web App (Streamlit Python).
- **Core Engine:** LLM GPT-4o-mini kết hợp Native Function Calling.
- **Workflow:**
  1. User nhập câu hỏi.
  2. Hệ thống chạy logic **Intent Mapping** (Dịch ý định) để tối ưu từ khóa, sau đó đưa vào hàm **RAG (Weighted Scoring)** để trích xuất ngữ cảnh từ file `data.json`.
  3. LLM phân tích Context và Input:
     - Phát hiện từ khóa an toàn -> Gọi hàm `escalate_to_human`.
     - Đủ điều kiện đặt lịch -> Gọi hàm `book_service`.
     - Hỏi đáp bình thường -> Trả lời theo văn bản.
  4. Giao diện Streamlit xử lý tín hiệu Tool Calling để hiển thị khung thông báo tương ứng.

### Phân công thực hiện Hackathon
- **Ngô Quang Tăng:** AI Canvas, User Stories (4 Paths), thiết kế Slide Pitching.
- **Vũ Đức Minh:** Kịch bản Fallback, nội dung Kịch bản thuyết trình (Demo Script).
- **Trần Sỹ Minh Quân:** Eval Framework, rà soát Failure Modes & Mitigation.
- **Nguyễn Thế Anh:** Tính toán ROI 3 kịch bản, xác định Eval Metrics.
- **Phạm Minh Khôi:** Lập trình hệ thống MVP (Xây dựng KB RAG, tích hợp Agent Tool Calling), tổng hợp Mini Spec.
