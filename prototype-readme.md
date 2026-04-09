# Prototype — VinFast Agent Copilot (Nhóm 32 - Phòng E403)

## Mô tả
Trợ lý AI Agent hỗ trợ khách hàng tra cứu thông tin xe, chính sách VinFast và tự động hóa quy trình đặt lịch dịch vụ. Khác với Chatbot thông thường, hệ thống được thiết kế theo hướng Augmentation, tích hợp cơ chế "Intent Mapping" (Dịch ý định) để tối ưu RAG và Native Function Calling để xử lý an toàn khẩn cấp (Safety Fallback) khi phát hiện sự cố xe nguy hiểm.

## Level: Working prototype
- Giao diện UI/UX được build bằng Python Streamlit.
- 100% Flow chạy thật, kết nối trực tiếp với OpenAI API.
- Tích hợp công cụ (Tools) tự động hiển thị UI Đặt lịch và UI Cảnh báo an toàn.

## Links
- **Source Code (GitHub):** [Thêm link Repo Github Nhóm của bạn vào đây]
- **Video Demo (Backup):** [Thêm link video Loom/Google Drive của bạn vào đây nếu có quay]

## Tools & API
- **Giao diện:** Streamlit (Python)
- **AI Model:** GPT-4o-mini (OpenAI API)
- **Knowledge Base (RAG):** In-memory JSON Data kết hợp thuật toán Weighted Scoring và Intent Mapping (Tự code bằng Python).
- **Core Technology:** OpenAI Native Function Calling (Tích hợp 2 tools: `book_service` và `escalate_to_human`).

## Phân công

| Thành viên | Phần đảm nhiệm | Output cụ thể |
|-----------|------|--------|
| **Ngô Quang Tăng** | Thiết kế luồng UX & AI Canvas | `spec-final.md` (Phần 1, 2), `demo-slides.pdf` |
| **Vũ Đức Minh** | Lên kịch bản Fallback & Kịch bản thuyết trình | Kịch bản Demo 5 phút (`demo-script.md`) |
| **Trần Sỹ Minh Quân** | Eval Framework, Quản trị rủi ro | `spec-final.md` (Phần 4: Failure Modes) |
| **Nguyễn Thế Anh** | Phân tích Business & Metrics | `spec-final.md` (Phần 3, 5: Eval Metrics, ROI) |
| **Phạm Minh Khôi** | Technical PM & Lập trình AI Agent MVP | Code `app.py`, `vinfast_kb.py`, `data.json`, `prototype-readme.md` |
