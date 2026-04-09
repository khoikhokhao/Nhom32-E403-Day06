import json
import re

def load_data():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f).get("documents", [])
    except Exception as e:
        print(f"Lỗi đọc file data.json: {e}")
        return []

def retrieve_context(user_query, top_k=5): # Tăng top_k lên 5 để không bị lọt thông tin
    docs = load_data()
    query = user_query.lower()
    
    # 1. CHUẨN HÓA DỮ LIỆU (Normalize)
    # Chỉ nối "vf <số>" thành "vf<số>" để không phá các tag có khoảng trắng như "vf mpv 7"
    query = re.sub(r"\bvf\s+(\d+)\b", r"vf\1", query)
    # Chuẩn hóa thêm vài cách viết thường gặp của model
    query = re.sub(r"\bec\s*van\b", "ec van", query)
    query = re.sub(r"\bmpv\s*7\b", "vf mpv 7", query)
    
        # 2. BỘ DỊCH Ý ĐỊNH (Intent Mapping)
        # Giữ expanded tags ngắn gọn: ưu tiên tag lõi có độ phủ cao để tránh làm loãng điểm
    intent_mappings = [
        (["giá", "tiền", "bao nhiêu", "rẻ", "đắt", "chi phí", "niêm yết", "trả góp", "đặt cọc"],
            "price budget"),
        (["bao xa", "km", "quãng đường", "phạm vi", "tầm hoạt động", "lần sạc", "wltp", "nedc"],
         "range specs"),
        (["thông số", "công suất", "mô men", "torque", "hp", "kw", "tăng tốc", "0-100", "hiệu năng", "kích thước"],
            "specs power torque"),
        (["sạc", "trạm sạc", "kwh", "sạc nhanh", "sạc tại nhà", "sạc công cộng", "hóa đơn", "thanh toán", "đèn led", "nhiệt độ pin"],
            "charging charging rate"),
        (["thuê pin", "gói pin", "subscription pin", "mua pin", "dừng thuê pin"],
            "battery rental"),
        (["bảo hành", "sửa", "hỏng", "lỗi", "bảo dưỡng", "xưởng", "tai nạn", "an toàn", "pin cao áp", "dịch vụ thương mại", "taxi", "grab"],
            "warranty maintenance safety"),
        (["đặt lịch", "booking", "showroom", "đại lý", "dịch vụ", "hỗ trợ", "hotline", "liên hệ", "email", "tư vấn"],
            "booking showroom support contact"),
        (["chính sách", "pháp lý", "điều khoản", "cookie", "bảo mật", "dữ liệu cá nhân", "quyền dữ liệu", "xóa dữ liệu", "đồng ý", "privacy"],
            "policy privacy legal"),
        (["xe máy điện", "viper", "amio", "học sinh", "lfp"],
            "e-scooter lfp"),
    ]

    for keywords, expanded_tags in intent_mappings:
        if any(keyword in query for keyword in keywords):
            query += f" {expanded_tags}"

    query_words = re.findall(r'\w+', query)
    scored_docs = []
    
    for doc in docs:
        score = 0
        snippet_lower = doc['snippet'].lower()
        tags_lower = [t.lower() for t in doc['tags']]
        
        # 3. Chấm điểm Trọng số cao (+5 điểm): Match chính xác Tag
        for tag in tags_lower:
            if tag in query:
                score += 5
                
        # 4. Chấm điểm Trọng số thấp (+1 điểm): Match từng từ vựng
        for word in query_words:
            if word in snippet_lower:
                score += 1
                
        if score > 0:
            scored_docs.append((score, doc))
            
    # Sắp xếp từ cao xuống thấp và lấy top_k
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for score, doc in scored_docs[:top_k]:
        results.append(f"- [{doc['sourceTitle']}] (Score {score}): {doc['snippet']}")
        
    if results:
        return "DỮ LIỆU NỘI BỘ TÌM THẤY:\n" + "\n".join(results)
    return "Không tìm thấy dữ liệu nội bộ."