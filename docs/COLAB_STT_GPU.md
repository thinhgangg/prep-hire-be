# Chạy Whisper bằng GPU Google Colab

1. Mở `COLAB_STT_GPU.ipynb` bằng Google Colab.
2. Chọn **Runtime > Change runtime type > T4 GPU**.
3. Chạy lần lượt toàn bộ cell và giữ tab Colab mở.
   Cell cuối phải tiếp tục ở trạng thái đang chạy; không bấm nút Stop.
   Notebook ghim `av<19` vì PyAV 19 không còn hỗ trợ tham số
   `metadata_errors` mà bản faster-whisper hiện tại sử dụng.
4. Tạo tài khoản miễn phí tại ngrok, sao chép **authtoken**, rồi dán token vào
   ô nhập ẩn ở cell cuối.
5. Cell cuối in ra một dòng dạng:

   ```text
   VITE_API_BASE_URL=https://xxxx.ngrok-free.app
   ```

6. Trong `prep-hire-fe/.env`, đặt URL vừa nhận được:

   ```env
   VITE_API_BASE_URL=https://xxxx.ngrok-free.app
   ```

7. Khởi động lại frontend bằng `npm run dev`.
8. Mở URL `/health` được notebook in ra. Chỉ bắt đầu thử khi thấy `device: cuda`.

URL tunnel có thể thay đổi mỗi lần Colab khởi động lại. Muốn quay lại backend local, đổi
`VITE_API_BASE_URL` về `http://localhost:8000` rồi khởi động lại frontend.

Notebook chỉ thay backend STT. AI backend và quy trình tạo/xếp hạng bốn câu hỏi
ứng viên vẫn chạy như cũ.
