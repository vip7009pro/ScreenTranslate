# Screen Overlay Translator

Screen Overlay Translator là một ứng dụng desktop Windows hoạt động theo kiểu tính năng "Screen Translate" trên Android.
Ứng dụng cho phép bạn chụp một vùng màn hình, OCR nội dung trong ảnh, dịch văn bản đã nhận diện, rồi vẽ bản dịch lên một lớp overlay trong suốt đúng ngay vị trí vùng đã chụp.

## Điểm nổi bật

- Chạy ở system tray và dùng hotkey toàn cục.
- Có lớp snipping trong suốt toàn màn hình để chọn vùng cần dịch.
- Pipeline chụp màn hình có xử lý DPI để khớp chính xác với tọa độ hiển thị trên Windows.
- OCR bằng Tesseract thông qua `pytesseract`.
- Dịch bằng `deep-translator` với Google Translate.
- Overlay kết quả trong suốt, luôn nằm trên cùng.
- Copy toàn bộ bản dịch hoặc chỉ copy block văn bản đang chọn.
- Có thể đổi ngôn ngữ OCR nguồn và ngôn ngữ đích ngay trong tray menu.
- Đã tích hợp sẵn dữ liệu OCR cho English, Chinese Simplified, Japanese, Korean và Vietnamese.

## Ngôn ngữ được hỗ trợ

Trong tray menu, ứng dụng hiện hỗ trợ các lựa chọn sau:

- Auto detect
- English
- Chinese (Simplified)
- Japanese
- Korean
- Vietnamese

Ngôn ngữ đích mặc định: Vietnamese.

## Pipeline xử lý từng bước

Mỗi lần bạn dùng ứng dụng để dịch một vùng màn hình, pipeline sẽ đi theo thứ tự sau:

```text
Nhấn hotkey
  -> service hotkey ở system tray
  -> mở overlay snipping trong suốt
  -> người dùng kéo thả để chọn vùng
  -> vùng chọn được chụp với mapping DPI-aware
  -> ảnh được đưa vào Tesseract OCR
  -> các từ có confidence thấp bị loại bỏ
  -> các từ được gom thành block / dòng có ngữ cảnh
  -> mỗi block được dịch
  -> tạo overlay trong suốt đúng vị trí trên màn hình
  -> các label dịch được vẽ đè lên vùng chữ gốc
  -> người dùng có thể copy toàn bộ hoặc chỉ block đang chọn
```

### Bước 1: Hotkey và tray service

Ứng dụng chạy trong system tray và lắng nghe phím `Ctrl+Shift+E`.
Trên Windows, hotkey được đăng ký bằng `RegisterHotKey` native để ổn định hơn.
Nếu đăng ký native không hoạt động, ứng dụng sẽ fallback sang package `keyboard`.

### Bước 2: Chế độ snipping

Khi bạn nhấn hotkey, ứng dụng hiển thị một overlay bán trong suốt phủ toàn màn hình.
Bạn kéo chuột để xác định hình chữ nhật vùng cần chụp.
Overlay sẽ đóng ngay sau khi chọn xong.

### Bước 3: Chụp màn hình

Vùng đã chọn được chụp bằng `mss`.
Ứng dụng map tọa độ logical của Qt sang tọa độ physical của màn hình dựa trên DPI scale hiện tại.
Điều này giúp vùng chụp khớp với overlay ngay cả khi Windows đang scale màn hình.

### Bước 4: OCR

Ảnh đã chụp được đưa vào Tesseract bằng `pytesseract.image_to_data()`.
Ứng dụng lấy ra:

- text
- left / top / width / height
- confidence
- metadata phân nhóm theo dòng và block

Các chuỗi rỗng và các từ có confidence thấp sẽ bị loại bỏ.
Sau đó các từ được gom thành block văn bản có ngữ cảnh, thay vì dịch từng từ riêng lẻ.

### Bước 5: Dịch

Mỗi block OCR được dịch bằng `deep-translator`.
Ngôn ngữ nguồn OCR và ngôn ngữ đích được chọn từ tray menu.
Ngôn ngữ đích mặc định là tiếng Việt.

### Bước 6: Overlay kết quả

Ứng dụng tạo một cửa sổ PyQt mới, frameless, trong suốt và luôn nằm trên cùng, ngay tại vị trí tương ứng với vùng đã chụp.
Với mỗi block đã dịch, ứng dụng tạo một label và đặt nó đúng theo tọa độ OCR.
Nền của label đủ đặc để che phần chữ gốc phía dưới.

Overlay còn có:

- nút `All`: copy toàn bộ bản dịch vào clipboard
- nút `Sel`: copy block văn bản đang được chọn
- nút `X`: đóng overlay

Bạn có thể click vào một block đã dịch để chọn nó trước khi dùng `Sel`.

## Cài đặt

### 1. Cài Python dependencies

Dùng virtual environment của dự án và cài các package cần thiết:

```powershell
python -m pip install -r requirements.txt
```

Nếu bạn đang dùng thẳng workspace venv, có thể chạy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Cài Tesseract-OCR cho Windows

Cài Tesseract cho Windows, ví dụ bản UB Mannheim.

Sau khi cài xong, hãy đảm bảo `tesseract.exe` nằm trong PATH, hoặc đặt biến môi trường sau:

```powershell
$env:SCREEN_TRANSLATE_TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR'
```

Bạn có thể trỏ biến này tới thư mục cài đặt hoặc trực tiếp tới file `tesseract.exe`.
Ứng dụng sẽ tự nhận cả hai.

### 3. Kiểm tra dữ liệu OCR language

Repository này đã kèm sẵn thư mục `tessdata` với các file traineddata sau:

- `eng.traineddata`
- `chi_sim.traineddata`
- `jpn.traineddata`
- `kor.traineddata`
- `vie.traineddata`

Khi thư mục `tessdata` local có mặt, ứng dụng sẽ tự dùng nó.
Nhờ vậy bộ ngôn ngữ được hỗ trợ hoạt động mà không phụ thuộc vào cài đặt Tesseract hệ thống.

## Chạy ứng dụng

Từ thư mục gốc của dự án:

```powershell
.\.venv\Scripts\python.exe .\screen_overlay_translator.py
```

Khi icon tray xuất hiện:

1. Nhấn `Ctrl+Shift+E`.
2. Kéo chọn vùng màn hình bạn muốn dịch.
3. Chờ OCR và dịch xong.
4. Dùng các nút trên overlay để copy text hoặc đóng overlay.

## Đổi ngôn ngữ nguồn và đích

Mở menu ở tray icon và dùng:

- `Source OCR language`
- `Target translation language`

Ngôn ngữ nguồn sẽ ảnh hưởng tới OCR.
Ngôn ngữ đích sẽ ảnh hưởng tới kết quả dịch.

Các lựa chọn khả dụng giống với danh sách ngôn ngữ được hỗ trợ ở trên.
Ngôn ngữ đích mặc định là Vietnamese.

## Copy văn bản

Overlay dịch có hai thao tác copy:

- `All` copy toàn bộ các block đã dịch theo thứ tự đọc.
- `Sel` copy block mà bạn đã click chọn gần nhất.

Điều này rất hữu ích khi overlay chứa nhiều đoạn dịch và bạn chỉ cần một câu hoặc một đoạn cụ thể.

## Cấu hình

Biến môi trường chính bạn có thể cần đặt là:

- `SCREEN_TRANSLATE_TESSERACT_CMD`: đường dẫn tới `tesseract.exe` hoặc thư mục cài Tesseract

Ứng dụng cũng hỗ trợ `SCREEN_TRANSLATE_OCR_CONFIG` nếu bạn muốn thay đổi các flag của OCR engine.
Cấu hình mặc định đã được tối ưu cho text trên màn hình và thường là lựa chọn tốt nhất.

## Cấu trúc dự án

- `screen_overlay_translator.py` - file chạy chính, chứa toàn bộ logic GUI / OCR / dịch
- `requirements.txt` - danh sách Python dependencies
- `tessdata/` - dữ liệu OCR local dùng cho Tesseract
- `CONTEXT.md` - ghi chú trạng thái và context hiện tại của workspace

## Xử lý sự cố

### Không tìm thấy Tesseract

Nếu ứng dụng báo Tesseract chưa được cài hoặc không có trong PATH, hãy kiểm tra:

1. Xác nhận `tesseract.exe` tồn tại.
2. Đảm bảo `SCREEN_TRANSLATE_TESSERACT_CMD` trỏ tới thư mục cài đặt hoặc trực tiếp file executable.
3. Kiểm tra workspace venv có thể chạy `pytesseract.get_tesseract_version()`.

### Không nhận diện được tiếng Hàn, Nhật hoặc Trung

Nếu một ngôn ngữ nào đó không nhận diện đúng:

1. Kiểm tra file `.traineddata` tương ứng có tồn tại trong `tessdata/`.
2. Chuyển source OCR language trong tray menu sang ngôn ngữ phù hợp.
3. Đảm bảo thư mục `tessdata` local vẫn nằm cạnh `screen_overlay_translator.py`.

### Kết quả dịch không đúng

Bản dịch dùng Google Translate thông qua `deep-translator`.
Nếu dịch lỗi, hãy kiểm tra kết nối mạng rồi thử lại.

### Nút copy không hoạt động

Đảm bảo overlay đang được focus và có ít nhất một block đã dịch.
Hãy click vào một block trước, sau đó dùng `Sel`.

## Ghi chú

- Đây là triển khai dành riêng cho Windows.
- Ứng dụng được thiết kế để hoạt động đúng với monitor scaling và nhiều màn hình.
- Các đường xử lý cho OCR và overlay position được tách riêng để đảm bảo tọa độ chụp thật sự chính xác.
