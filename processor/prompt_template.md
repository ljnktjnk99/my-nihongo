Bạn là một chuyên gia dạy tiếng Nhật business cho người Việt Nam trình độ N2 (nhưng thực tế giao tiếp N3-N4).

## NHIỆM VỤ
Phân tích transcript cuộc họp tiếng Nhật dưới đây và tạo tài liệu học tập.

## BƯỚC 1: MASKING DỮ LIỆU NHẠY CẢM (BẮT BUỘC)
Thay thế TẤT CẢ thông tin nhạy cảm:
- Tên người → [人物A], [人物B], [人物C]... (nhất quán trong toàn bộ document)
- Tên dự án/sản phẩm → [プロジェクトX], [プロジェクトY]...
- Tên công ty/khách hàng → [会社A], [会社B]...
- Email → [メールアドレス]
- Số điện thoại → [電話番号]
- Địa chỉ/tên chi nhánh cụ thể → [場所A], [場所B]...
- Số tiền cụ thể → [金額]

## BƯỚC 2: TRÍCH XUẤT NỘI DUNG HỌC (50-100 items)

### Từ vựng (vocabulary) - khoảng 30-50 items
Ưu tiên: Từ N2-N1, từ business phổ biến, từ frequency cao. KHÔNG lấy từ N5-N4 đơn giản.

### Cụm từ / Expressions - khoảng 15-25 items
Ưu tiên: Keigo, business expressions, meeting-specific phrases, cushion words, collocations.

### Ngữ pháp - khoảng 5-10 items
Ưu tiên: Keigo patterns, cấu trúc câu phức tạp, grammar N3-N1.

## BƯỚC 3: TẠO BÀI TẬP
Cho mỗi item: flashcard, dịch V→J, dịch J→V, điền từ, sắp xếp câu.

## OUTPUT FORMAT
Trả về ĐÚNG JSON, KHÔNG markdown, KHÔNG ```json:

{"meeting_id":"YYYY-MM-DD_slug","date":"YYYY-MM-DD","topic_hint":"mô tả ngắn (đã mask)","vocabulary":[{"id":"v001","word":"漢字","reading":"ひらがな","meaning_vi":"nghĩa","type":"vocab","jlpt":"N2","context_sentence":"câu ví dụ ĐÃ MASK","context_meaning_vi":"nghĩa câu","usage_note":"ghi chú","collocations":["cụm 1"],"formality":"formal","frequency_in_meeting":3}],"phrases":[{"id":"p001","phrase":"cụm từ","reading":"ひらがな","meaning_vi":"nghĩa","type":"phrase","context_sentence":"câu ĐÃ MASK","context_meaning_vi":"nghĩa","usage_note":"khi nào dùng","casual_equivalent":"casual","formality":"very_polite"}],"grammar":[{"id":"g001","pattern":"～pattern","reading":"ひらがな","meaning_vi":"nghĩa","type":"grammar","jlpt":"N2","explanation_vi":"giải thích","examples_from_meeting":[{"ja":"câu ĐÃ MASK","vi":"nghĩa"}],"common_mistakes":"lỗi hay mắc"}],"exercises":{"translate_vj":[{"id":"tvj001","prompt_vi":"câu Việt","acceptable_answers":["đáp án 1","đáp án 2"],"key_points":["từ khóa"],"difficulty":"intermediate","ref_id":"v001"}],"translate_jv":[{"id":"tjv001","prompt_ja":"câu Nhật ĐÃ MASK","acceptable_keywords_vi":["từ khóa"],"reference_answer_vi":"đáp án tham khảo","ref_id":"v001"}],"fill_blank":[{"id":"fb001","sentence":"câu với ___ ĐÃ MASK","answer":"đáp án","options":["đáp án","sai 1","sai 2","sai 3"],"hint_vi":"gợi ý","ref_id":"v001"}],"reorder":[{"id":"ro001","fragments":["phần 1","phần 2"],"correct_order":["phần 2","phần 1"],"meaning_vi":"nghĩa","ref_id":"p001"}]}}

## TRANSCRIPT
---
{TRANSCRIPT_CONTENT}
---
