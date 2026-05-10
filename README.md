# 🎬 CineView — Nền Tảng Xem Phim với AI

CineView là nền tảng xem phim thông minh kết hợp AI để phân tích đánh giá và gợi ý phim cá nhân hóa.

## ✨ Tính Năng Mới: AI Recommendation Cá Nhân Hóa

### Hệ Thống Gợi Ý
- **Mục "Các phim bạn có thể thích"** trên trang chủ — gợi ý được cá nhân hóa theo lịch sử xem
- **Vector Embeddings** lưu trữ trong **ChromaDB** (persistent local storage)
- **TF-IDF Similarity** để so sánh phim dựa trên thể loại, nội dung, và đánh giá
- **Cold Start**: Khi chưa có lịch sử, hiển thị phim nổi bật nhất
- **Tự động ghi nhận** mỗi lần người dùng xem phim
- **Like/Dislike** trên trang chi tiết phim để tinh chỉnh gợi ý

### Kiến Trúc
```
User xem phim → recordInteraction() → ChromaDB vector store
                                    ↓
Trang chủ → /recommendations/for-you → vector similarity → gợi ý cá nhân
```

### ChromaDB Schema
- **Collection `movies`**: Vector embedding của mỗi phim (title, genres, overview, rating)
- **Collection `user_preferences`**: Lịch sử tương tác của từng user

## 🚀 Cài Đặt

### Backend
```bash
cd backend
pip install -r requirements.txt
# Tạo file .env với TMDB_API_KEY và GEMINI_API_KEY
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🔧 API Endpoints Mới

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/recommendations/for-you` | Lấy gợi ý cá nhân hóa |
| POST | `/recommendations/interact` | Ghi nhận tương tác (view/like/dislike) |
| GET | `/recommendations/similar/{id}` | Phim tương tự |
| GET | `/recommendations/history` | Lịch sử tương tác |
| GET | `/recommendations/stats` | Thống kê vector store |

## 🌐 Ngôn Ngữ
Toàn bộ giao diện người dùng đã được dịch sang **Tiếng Việt**.
