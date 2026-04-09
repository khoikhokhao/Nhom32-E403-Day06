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
    # Xóa khoảng trắng giữa VF và số (VD: "vf 6" thành "vf6") để match chuẩn tag
    query = query.replace("vf ", "vf")
    
    # 2. BỘ DỊCH Ý ĐỊNH (Intent Mapping) - Vũ khí bí mật!
    # Nếu câu hỏi có từ khóa tiếng Việt, tự động bơm thêm Tag tiếng Anh vào để quét RAG
    if any(w in query for w in ["giá", "tiền", "bao nhiêu", "rẻ"]):
        query += " price budget"
    if any(w in query for w in ["bao xa", "km", "quãng đường", "chạy", "sạc"]):
        query += " range charging specs"
    if any(w in query for w in ["bảo hành", "sửa", "hỏng", "lỗi", "con rùa"]):
        query += " warranty safety maintenance"

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