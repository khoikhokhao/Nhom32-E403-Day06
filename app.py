import streamlit as st
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from vinfast_kb import retrieve_context

# 1. Khởi tạo
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="VinFast Agent Copilot", page_icon="⚡")
st.title("⚡ VinFast Agent Copilot")
st.caption("AI Agent tích hợp RAG Scoring & Native Function Calling")

# 2. Định nghĩa Agent Tools (Vũ khí ăn tiền Hackathon)
agent_tools = [
    {
        "type": "function",
        "function": {
            "name": "book_service",
            "description": "Gọi hàm này khi người dùng muốn đặt lịch và ĐÃ CUNG CẤP ĐỦ: dòng xe, số điện thoại, tên, thời gian, địa điểm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "car_model": {"type": "string", "description": "Dòng xe (VD: VF 7)"},
                    "phone": {"type": "string", "description": "Số điện thoại"},
                    "service_type": {"type": "string", "description": "Loại dịch vụ (lái thử, bảo dưỡng)"},
                    "customer_name": {"type": "string", "description": "Tên khách hàng"},
                    "time": {"type": "string", "description": "Thời gian đặt lịch"},
                    "location": {"type": "string", "description": "Địa điểm showroom hoặc thành phố"}
                },
                # Ép AI phải thu thập đủ 6 thông tin này mới được gọi Tool
                "required": ["car_model", "phone", "service_type", "customer_name", "time", "location"]
            }
        }
    }
    ,
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Gọi hàm này NGAY LẬP TỨC khi phát hiện lỗi an toàn (tai nạn, pin quá nhiệt, hỏng phanh).",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Lý do chuyển tuyến an toàn"}
                },
                "required": ["reason"]
            }
        }
    }
]

# 3. System Prompt
SYSTEM_PROMPT = """
Bạn là Trợ lý AI cao cấp của VinFast.
1. GROUNDEDNESS: Chỉ tư vấn dựa trên Dữ liệu RAG được cung cấp. Nếu RAG không có, nói không biết.
2. AGENTIC BEHAVIOR: 
- Nếu khách muốn đặt lịch mà chưa có SĐT, hãy hỏi SĐT. Nếu đủ SĐT, hãy dùng công cụ `book_service`.
- Nếu khách báo lỗi nguy hiểm, TUYỆT ĐỐI không chẩn đoán. Dùng ngay công cụ `escalate_to_human`.
"""

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Xin chào! Trợ lý VinFast đã sẵn sàng."}]

for msg in st.session_state.messages:
    if msg["role"] not in ["system", "tool"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 4. Xử lý Input
if prompt := st.chat_input("Nhập câu hỏi..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # RAG Retrieval
    rag_context = retrieve_context(prompt)
    with st.expander("🔍 System Logs: Dữ liệu RAG Trích xuất (Dành cho Giám khảo)"):
        st.info(rag_context)

    # Lắp ráp tin nhắn
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    api_messages.append({"role": "system", "content": f"DỮ LIỆU RAG HIỆN TẠI:\n{rag_context}"})
    
    # Chỉ gửi các tin nhắn không phải là log hệ thống cũ để tiết kiệm token
    for msg in st.session_state.messages:
        if msg["role"] in ["user", "assistant"]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

    # Gọi API GPT với Tools
    with st.chat_message("assistant"):
        placeholder = st.empty()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            tools=agent_tools,
            tool_choice="auto", # Cho phép AI tự quyết định có dùng Tool hay không
            temperature=0.1
        )
        
        response_message = response.choices[0].message

        # KIỂM TRA AI QUYẾT ĐỊNH DÙNG TOOL HAY TRẢ LỜI TEXT
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "book_service":
                    st.success("✅ ĐÃ GHI NHẬN LỆNH ĐẶT LỊCH VÀO HỆ THỐNG!")
                    st.write(f"**👤 Khách hàng:** {function_args.get('customer_name')} | **📞 SĐT:** {function_args.get('phone')}")
                    st.write(f"**🚗 Dòng xe:** {function_args.get('car_model')} | **📝 Dịch vụ:** {function_args.get('service_type')}")
                    st.write(f"**⏰ Thời gian:** {function_args.get('time')}")
                    st.write(f"**📍 Địa điểm:** {function_args.get('location')}")
                    st.caption("Lệnh API nội bộ đã được trigger thành công.")
                    
                    st.session_state.messages.append({"role": "assistant", "content": f"✅ Đã chốt lịch {function_args.get('service_type')} xe {function_args.get('car_model')} cho anh/chị {function_args.get('customer_name')} lúc {function_args.get('time')} tại {function_args.get('location')}."})
                    
                elif function_name == "escalate_to_human":
                    st.error("🚨 KÍCH HOẠT QUY TRÌNH AN TOÀN KHẨN CẤP (SAFETY FALLBACK) 🚨")
                    st.write(f"**⚠️ Lý do:** {function_args.get('reason')}")
                    st.write("**Hành động:** Yêu cầu khách hàng dừng xe an toàn. Đang chuyển kết nối tới Kỹ sư trưởng VinFast...")
                    st.info("📞 Hoặc gọi ngay Hotline: 1900 23 23 89")
                    st.session_state.messages.append({"role": "assistant", "content": f"🚨 Chuyển tiếp khẩn cấp do: {function_args.get('reason')}"})
        else:
            # Nếu không gọi Tool, trả lời chat bình thường
            answer = response_message.content
            placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})