# 🚀 Hướng dẫn chạy Local — Prep-Hire

> **Nhánh làm việc:** `An`  
> Tất cả thay đổi đều nằm trên nhánh `An` ở mỗi repo. Clone/checkout đúng nhánh trước khi chạy.

---

## 📁 Cấu trúc dự án

```
PBL6/
├── prep-hire-be/   ← STT Backend (FastAPI, port 8000)
├── prep-hire-ai/   ← AI Backend  (FastAPI, port 9001)
└── prep-hire-fe/   ← Frontend    (Vite/React, port 5173)
```

---

## ⚡ Yêu cầu hệ thống

| Công cụ | Phiên bản khuyến nghị |
|---------|----------------------|
| Python  | 3.10+                |
| Node.js | 18+                  |
| npm     | 9+                   |
| Git     | bất kỳ               |

---

## 1️⃣ Clone và checkout nhánh `An`

```powershell
# Clone 3 repo (nếu chưa có)
git clone https://github.com/thinhgangg/prep-hire-be.git
git clone https://github.com/thinhgangg/prep-hire-ai.git
git clone https://github.com/thinhgangg/prep-hire-fe.git

# Checkout nhánh An ở từng repo
cd prep-hire-be  && git checkout An && cd ..
cd prep-hire-ai  && git checkout An && cd ..
cd prep-hire-fe  && git checkout An && cd ..
```

---

## 2️⃣ STT Backend (`prep-hire-be`, port 8000)

### Cài đặt

```powershell
cd prep-hire-be

# Tạo virtualenv và cài thư viện
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Cấu hình `.env`

Sao chép file mẫu rồi điền giá trị:

```powershell
copy .env.example .env
```

Các biến quan trọng trong `.env`:

```env
# URL của AI backend (prep-hire-ai)
STT_REMOTE_BASE_URL=http://127.0.0.1:9001

# Thời gian timeout khi gọi remote STT (giây)
STT_REMOTE_TIMEOUT_SECONDS=120

# Supabase (để lấy terminology datastore — có thể để trống nếu dùng file jsonl)
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_ANON_KEY=
```

> ℹ️ Nếu **không có Supabase**, STT service sẽ tự dùng file `data/verified_aliases.jsonl` làm datastore thuật ngữ.

### Chạy server

```powershell
# Phải cd vào đúng thư mục prep-hire-be
cd D:\...\prep-hire-be
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8000
```

✅ Server chạy tại: `http://127.0.0.1:8000`

---

## 3️⃣ AI Backend (`prep-hire-ai`, port 9001)

### Cài đặt

```powershell
cd prep-hire-ai

# Tạo virtualenv và cài thư viện
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Cấu hình `.env`

```powershell
copy .env.example .env
```

Điền các biến cần thiết (LLM API keys, database, v.v.)

### Chạy server

```powershell
# ⚠️ QUAN TRỌNG: phải cd vào đúng thư mục prep-hire-ai
cd D:\...\prep-hire-ai
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 9001
```

✅ Server chạy tại: `http://127.0.0.1:9001`

> ⚠️ **Lỗi phổ biến:** Nếu thấy `ModuleNotFoundError: No module named 'app'`, nghĩa là bạn đang chạy uvicorn từ thư mục sai (thư mục cha). Phải `cd` vào đúng `prep-hire-ai` rồi mới chạy.

---

## 4️⃣ Frontend (`prep-hire-fe`, port 5173)

### Cài đặt

```powershell
cd prep-hire-fe
npm install
```

### Cấu hình `.env`

```powershell
copy .env.example .env
```

Nội dung `.env`:

```env
VITE_BE_URL=http://localhost:8000
VITE_AI_URL=http://localhost:9001
```

### Chạy dev server

```powershell
cd D:\...\prep-hire-fe
npm run dev
```

✅ Frontend chạy tại: `http://localhost:5173`

---

## 🔄 Thứ tự khởi động

Mở **3 terminal riêng biệt**, chạy theo thứ tự:

```
Terminal 1: AI Backend  (port 9001) ← khởi động trước
Terminal 2: STT Backend (port 8000) ← phụ thuộc AI backend
Terminal 3: Frontend    (port 5173) ← sau cùng
```

---

## 🐛 Các lỗi đã fix trong nhánh `An`

### `prep-hire-be` — `stt_service.py`

**Lỗi:** `NameError: name 'datastore_source' is not defined`

**Nguyên nhân:** Biến `datastore_source` chỉ được định nghĩa trong method `transcribe()` (dùng Whisper local), nhưng lại được tham chiếu trong method `_transcribe_remote()` (dùng khi có `STT_REMOTE_BASE_URL`).

**Fix:** Thêm định nghĩa `datastore_source` vào `_transcribe_remote()`:

```python
# app/services/stt_service.py — trong _transcribe_remote()
datastore_source = (
    "supabase"
    if settings.SUPABASE_URL
    and (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY)
    else "jsonl"
)
```

**File thay đổi:**
- `app/services/stt_service.py` — thêm `datastore_source` vào `_transcribe_remote`
- `app/api/stt.py` — cập nhật API STT jobs
- `app/core/config.py` — thêm config mới
- `app/main.py` — cập nhật startup
- `docs/` — thêm tài liệu Colab GPU và SQL datastore

### `prep-hire-ai` — `interview.py`

**Thay đổi:** Cập nhật interview endpoint, thêm dependency.

**File thay đổi:**
- `app/api/v1/endpoints/interview.py`
- `app/main.py`
- `requirements.txt`

### `prep-hire-fe`

**Thay đổi:** Tích hợp luồng phỏng vấn hoàn chỉnh — STT polling, submit câu trả lời, chuyển sang câu hỏi tiếp theo.

**File thay đổi:**
- `src/Pages.tsx` — trang processing với polling STT job
- `src/App.tsx` — routing cập nhật
- `src/candidate/CandidatePages.tsx` — giao diện phòng phỏng vấn
- `src/services/sttApi.ts` — API calls đến STT backend
- `src/services/interviewApi.ts` (**file mới**) — API calls đến AI backend
- `src/styles.css` — style cập nhật

---

## 📌 Ghi chú

- Mỗi lần pull code mới: `git pull origin An`
- Không commit thẳng lên `main`, luôn dùng nhánh `An` rồi tạo PR
- File `.env` **không được commit** (đã có trong `.gitignore`)
