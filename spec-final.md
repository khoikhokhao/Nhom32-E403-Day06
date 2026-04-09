# SPEC Final — Nhóm 32 - Phòng E403

**Track Lựa Chọn:** VinFast

## 🎯 Tuyên Bố Vấn Đề (Problem Statement)
**Ai gặp vấn đề gì:** Khách hàng mua xe điện và chủ xe VinFast thường bị "ngợp" trước lượng thông tin phân tán (giá pin, sạc, bảo dưỡng), dẫn đến hành trình trải nghiệm bị đứt đoạn và tăng tải cho đội ngũ CSKH.
**AI giải quyết thế nào:** Một AI Agent tích hợp sâu vào hệ sinh thái VinFast, tự động hóa việc tra cứu chính sách bằng RAG, chủ động đặt lịch qua Function Calling, và có khả năng xử lý cảnh báo an toàn tức thì.

---

## 1. AI Product Canvas

| | Value (Giá trị) | Trust (Niềm tin) | Feasibility (Khả thi) |
|---|---|---|---|
| **Trả lời** | **User:** (1) Khách tìm hiểu xe mới; (2) Chủ xe cần hỗ trợ kỹ thuật/đặt lịch.<br><br>**Pain points:** Tra cứu chính sách phức tạp; chờ tổng đài lâu.<br><br>**AI Solutions:** AI Agent giải đáp 24/7 từ Knowledge Base chuẩn; tự động hỏi thiếu thông tin để chốt lịch lái thử/bảo dưỡng bằng Tool Call. | **Hậu quả khi sai:** Gợi ý sai giá gây phàn nàn; hướng dẫn xử lý cảnh báo lỗi xe sai gây nguy hiểm tính mạng.<br><br>**Xây dựng Trust:** Mọi câu trả lời có trích dẫn nguồn. Tích hợp UI Tool hiển thị rõ thông tin khách vừa đặt (Tên, SĐT, Giờ, Địa điểm).<br><br>**Sửa lỗi:** Tích hợp nút "Chỉnh sửa lệnh" trên UI thay vì gõ lại prompt. | **Tech Stack:** RAG Pipeline (Weighted Scoring + Intent Mapping) kết hợp OpenAI Native Function Calling để tạo Agent.<br><br>**Costs:** Chi phí token API GPT-4o-mini siêu rẻ (~$0.01/chat).<br><br>**Risks chính:** Semantic Gap (Khách hỏi tiếng Việt, RAG tag tiếng Anh) -> Đã xử lý bằng thuật toán Intent Mapping. |

**Automation hay Augmentation?** ☐ Automation · ☑ Augmentation
**Justify:** Mua xe ô tô là quyết định tài chính lớn (High-involvement), và lỗi kỹ thuật xe liên quan đến an toàn. AI chỉ đóng vai trò phân tích, trích xuất thông tin và thiết lập Form (Copilot). Người dùng hoặc Kỹ thuật viên VinFast mới là người chốt hạ cuối cùng.

**Learning Signal:**
1. **User correction đi vào đâu?** Khi người dùng bấm nút [Sửa thông tin] trên giao diện Đặt lịch -> Ghi log vào Explicit Feedback -> Dùng để fine-tune thuật toán trích xuất thực thể (NER) của Model.
2. **Product thu signal gì để biết tốt lên/tệ đi?** Tỉ lệ tự giải quyết xong (Deflection rate); Tỉ lệ chốt form đặt lịch thành công; Tỉ lệ kích hoạt tính năng "Human Handoff".
3. **Data thuộc loại nào?** User-specific (ngân sách, sđt) + Domain-specific (Cẩm nang xe VF).
   **Có marginal value không?** Có. Log sửa lỗi và các câu hỏi thực tế của khách hàng là tài sản Data Flywheel độc quyền mà VinFast dùng để tối ưu lại RAG Document, các hãng đối thủ không thể có được.

---

## 2. User Stories — 4 Paths

### Feature 1: AI Agent Tự động Đặt Lịch (Function Calling)
**Trigger:** User yêu cầu đặt lịch lái thử/bảo dưỡng -> AI kiểm tra xem đã đủ tham số chưa (Tên, SĐT, Giờ, Địa điểm, Loại xe).

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** | User thấy gì? Flow kết thúc ra sao? | User nhập thiếu thông tin -> AI tự động hỏi thêm. Khi đủ thông tin, AI kích hoạt hàm `book_service`, UI bật khung thông báo Xanh Lá Cây xác nhận chốt lịch. |
| **Low-confidence** | System báo "không chắc" bằng cách nào? | User nói "bảo dưỡng con xe của tôi". AI không biết xe gì, dừng việc gọi Tool và hỏi lại: "Bạn đang sử dụng dòng xe VinFast nào để mình đặt lịch cho chính xác?" |
| **Failure** | User biết AI sai bằng cách nào? Recover ra sao? | AI trích xuất nhầm SĐT (user gõ nhầm 1 số). Tool đã kích hoạt và hệ thống lưu sai. User phát hiện lỗi khi nhìn vào UI xác nhận. |
| **Correction** | User sửa bằng cách nào? Data đó đi vào đâu? | User bấm "Hủy/Sửa" ngay trên Khung Xanh. Data được đẩy về hệ thống để theo dõi tỉ lệ Entity Extraction Failure của GPT. |

### Feature 2: Safety Fallback (Cảnh báo an toàn khẩn cấp)
**Trigger:** User nhập triệu chứng lỗi xe -> AI phân loại mức độ rủi ro.

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| **Happy** | User thấy gì? Flow kết thúc ra sao? | User báo "lỗi hệ thống phanh màu đỏ". AI nhận diện Safety Trigger, lập tức kích hoạt Tool `escalate_to_human`, bật UI Cảnh báo ĐỎ, báo tấp lề và gọi Hotline 1900 23 23 89. |
| **Low-confidence** | System báo "không chắc" bằng cách nào? | User báo "xe thỉnh thoảng kêu rít rít". AI không đủ context chẩn đoán âm thanh -> Gợi ý chuyển máy cho Kỹ thuật viên để an tâm. |
| **Failure** | User biết AI sai bằng cách nào? Recover ra sao? | Xe bốc khói nhưng AI tưởng lỗi nhẹ và khuyên "đi tiếp bình thường". **Hậu quả thảm khốc, user không biết AI sai.** |
| **Correction** | User sửa bằng cách nào? Data đó đi vào đâu? | Data từ các ca Escalation thực tế được team QA phân tích hàng tuần để đưa thêm từ khóa nguy hiểm vào bộ Hardcode Guardrails chặn ngay vòng ngoài. |

---

## 3. Eval Metrics & Threshold

**Optimize Precision hay Recall?** ☑ Recall
**Tại sao?** Bỏ sót một cảnh báo nguy hiểm hoặc lỗi xe nghiêm trọng (False Negative) khiến khách hàng gặp tai nạn tệ hơn rất nhiều so với việc cảnh báo nhầm (False Positive) và ép họ gọi cho bộ phận Kỹ thuật.

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| **Recall (Safety Triggers)** - Bắt trúng từ khóa nguy hiểm (phanh, pin, con rùa) | ≥ 99% | < 95% trong 3 ngày liên tiếp (Nguy cơ an toàn cao). |
| **Groundedness Score** - Tỉ lệ câu trả lời bám sát 100% dữ liệu RAG | ≥ 95% | < 85% -> Model bắt đầu có dấu hiệu ảo giác (Hallucination). |
| **Deflection Rate** - Tỉ lệ tự giải quyết, không cần gặp CSKH | ≥ 40% | < 20% -> AI chưa đem lại ROI về mặt vận hành. |

---

## 4. Top 3 Failure Modes

| # | Trigger | Hậu quả | Mitigation (Giảm nhẹ) |
|---|---------|---------|------------|
| 1 | **Out-of-Domain/Jailbreak:** User hỏi giá cổ phiếu VFS hoặc yêu cầu AI làm thơ. | AI bị cuốn theo câu hỏi, trả lời lan man -> Mất hình ảnh chuyên nghiệp của thương hiệu. | **System Prompt Guardrails:** Hardcode lệnh ép AI phải từ chối lịch sự và chủ động lái câu chuyện về xe điện. |
| 2 | **Semantic Gap (Lệch ngữ nghĩa):** User hỏi "chạy bao xa", nhưng RAG database lưu tag tiếng Anh là "range". | RAG quét trượt, AI trả lời "Không biết" dù hệ thống có dữ liệu. | Tích hợp thuật toán **Intent Mapping**, tự động nhận diện ý định tiếng Việt và bơm keyword tiếng Anh vào chuỗi tìm kiếm RAG. |
| 3 | **Cập nhật chính sách trễ:** RAG truy xuất bảng giá của tháng trước. | Gợi ý sai giá xe/pin -> Khách khiếu nại. (User không biết bị sai lúc chat). | Bắt buộc in dòng Disclaimer: *"Báo giá mang tính tham khảo"* và đồng bộ Vector DB tự động lúc 2h sáng mỗi ngày. |

---

## 5. ROI 3 kịch bản

**Giả định:** Triển khai thử nghiệm với 15.000 lượt chat/tháng. Chi phí API + Server khoảng 1.000 VNĐ/lượt chat (Cố định: 15.000.000 VNĐ/tháng).

| | Conservative (Kém) | Realistic (Kỳ vọng) | Optimistic (Xuất sắc) |
|---|-------------|-----------|------------|
| **Tỉ lệ tự giải quyết** | 15% | 35% | 55% |
| **Cost** | 15.000.000 VNĐ | 15.000.000 VNĐ | 15.000.000 VNĐ |
| **Benefit (Tiết kiệm CSKH)**| 100 giờ (Trị giá 20 Triệu) | 250 giờ (Trị giá 50 Triệu) | 450 giờ (Trị giá 90 Triệu) |
| **Net ROI (Giá trị ròng)** | **+ 5.000.000 VNĐ** | **+ 35.000.000 VNĐ** | **+ 75.000.000 VNĐ** |

**Kill Criteria:** Dừng dự án nếu sau 2 tháng triển khai Net ROI âm, HOẶC điểm CSAT < 3.5/5 liên tục trong 2 tuần.

---

## 6. Mini AI Spec (Thông số kỹ thuật MVP)

### Scope & Tech Flow
- **Nền tảng:** Web App (Python Streamlit).
- **Core Engine:** GPT-4o-mini tích hợp Native Function Calling.
- **Workflow:**
  1. User nhập Prompt.
  2. Hệ thống chạy **Intent Mapping** (Dịch ý định) để tối ưu hóa từ khóa và đưa vào hệ thống **RAG (Weighted Scoring)** để trích xuất ngữ cảnh nội bộ.
  3. LLM phân tích Context và Input:
     - Nếu phát hiện lỗi an toàn -> Gọi hàm `escalate_to_human`.
     - Nếu đủ thông tin đặt lịch -> Gọi hàm `book_service`.
     - Nếu là hỏi đáp thông thường -> Render văn bản Markdown.
  4. Streamlit UI nhận tín hiệu từ Tool để render các giao diện Cảnh báo/Xác nhận tương ứng.

### Phân công thực hiện Hackathon
- **Ngô Quang Tăng:** Phụ trách AI Canvas & Thiết kế luồng UX (User Stories - 4 Paths), thiết kế Slide Pitching.
- **Vũ Đức Minh:** Xây dựng kịch bản Fallback, lên nội dung Kịch bản thuyết trình (Demo Script).
- **Trần Sỹ Minh Quân:** Xây dựng Eval Framework, rà soát Failure Modes (Thư viện rủi ro) và thiết kế phương án Mitigation.
- **Nguyễn Thế Anh:** Phân tích Business/Tài chính (Tính toán ROI 3 kịch bản), xác định các Eval Metrics.
- **Phạm Minh Khôi:** Lập trình hệ thống MVP (Xây dựng RAG Scoring, tích hợp Agent Tool Calling), tổng hợp tài liệu Mini Spec.