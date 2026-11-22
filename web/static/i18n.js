(() => {
  // Each pair is [English, Vietnamese]
  const PAIRS = [
    ["Dashboard", "Bảng điều khiển"],
    ["Sign in", "Đăng nhập"],
    ["Sign out", "Đăng xuất"],
    ["Teacher", "Giáo viên"],
    ["Student", "Sinh viên"],
    ["Cancel", "Hủy"],
    ["Confirm", "Xác nhận"],
    ["Back to home", "Về trang chủ"],
    ["Multi-cloud online quiz platform", "Nền tảng thi trắc nghiệm đa đám mây"],
    ["Create exams, take tests, auto-grade & issue certificates", "Tạo đề thi, làm bài trực tuyến, chấm điểm & cấp chứng chỉ tự động"],
    ["Teachers build an exam in minutes. Students take it online, get their score instantly and download a PDF certificate generated automatically on AWS Lambda.", "Giáo viên tạo đề chỉ trong vài phút. Sinh viên làm bài trực tuyến, nhận điểm ngay và tải chứng chỉ PDF được tạo tự động trên AWS Lambda."],
    ["Get started", "Bắt đầu ngay"],
    ["View architecture", "Xem kiến trúc"],
    ["PASSED", "ĐẠT"],
    ["Graded automatically in seconds", "Chấm điểm tự động trong vài giây"],
    ["PDF certificate", "Chứng chỉ PDF"],
    ["Stored on Amazon S3 · presigned link", "Lưu trên Amazon S3 · liên kết bảo mật"],
    ["Strict access control", "Kiểm soát truy cập chặt chẽ"],
    ["Sign in with Microsoft Entra ID, with separate Teacher and Student roles.", "Đăng nhập qua Microsoft Entra ID, tách biệt vai trò Giáo viên và Sinh viên."],
    ["Instant grading", "Chấm điểm tức thì"],
    ["SQS queue + AWS Lambda grade serverlessly and handle a whole class submitting at once.", "Hàng đợi SQS + AWS Lambda chấm điểm không máy chủ, chịu tải cả lớp nộp bài cùng lúc."],
    ["Dynamic files", "Tệp tin động"],
    ["PDF certificates, printable HTML reports and CSV grade exports.", "Chứng chỉ PDF, báo cáo HTML in ấn và xuất bảng điểm CSV."],
    ["Clear statistics", "Thống kê rõ ràng"],
    ["Average score, pass rate and the correct-answer rate of every question.", "Điểm trung bình, tỉ lệ đạt và tỉ lệ trả lời đúng từng câu hỏi."],
    ["Multi-cloud architecture", "Kiến trúc đa đám mây"],
    ["Azure manages users & data, AWS handles grading & files", "Azure quản lý người dùng & dữ liệu, AWS xử lý chấm bài & tệp tin"],
    ["Welcome back", "Chào mừng trở lại"],
    ["Sign in to QuizCloud", "Đăng nhập vào QuizCloud"],
    ["Sign in with Microsoft Entra ID", "Đăng nhập bằng Microsoft Entra ID"],
    ["or sign in with email", "hoặc đăng nhập bằng email"],
    ["Password", "Mật khẩu"],
    ["Create one", "Tạo tài khoản"],
    ["Create an account", "Tạo tài khoản mới"],
    ["Create account", "Tạo tài khoản"],
    ["Create student account", "Tạo tài khoản sinh viên"],
    ["Join QuizCloud to take or manage exams", "Tham gia QuizCloud để làm bài hoặc quản lý kỳ thi"],
    ["Full name", "Họ và tên"],
    ["Confirm password", "Xác nhận mật khẩu"],
    ["Already have an account?", "Đã có tài khoản?"],
    ["Don't have an account?", "Chưa có tài khoản?"],
    ["TEACHER DASHBOARD", "BẢNG ĐIỀU KHIỂN GIÁO VIÊN"],
    ["Teacher dashboard", "Bảng điều khiển giáo viên"],
    ["STUDENT DASHBOARD", "BẢNG ĐIỀU KHIỂN SINH VIÊN"],
    ["Student space", "Trang sinh viên"],
    ["Join", "Tham gia"],
    ["Private", "Riêng tư"],
    ["Public", "Công khai"],
    ["Public exam", "Đề công khai"],
    ["New exam", "Tạo đề mới"],
    ["+ New exam", "+ Tạo đề mới"],
    ["Exams", "Bài thi"],
    ["Open exams", "Đề đang mở"],
    ["Completed", "Đã hoàn thành"],
    ["Certificates earned", "Chứng chỉ đã đạt"],
    ["Exams for you", "Bài thi dành cho bạn"],
    ["Published", "Đã mở"],
    ["Draft", "Bản nháp"],
    ["Graded submissions", "Bài đã chấm"],
    ["Average score", "Điểm trung bình"],
    ["Pass rate", "Tỉ lệ đạt"],
    ["MY EXAMS", "BÀI THI CỦA TÔI"],
    ["My exams", "Bài thi của tôi"],
    ["No description", "Không có mô tả"],
    ["Managed", "Giám sát"],
    ["Under review", "Đang xem xét"],
    ["Grading", "Đang chấm"],
    ["Average", "Trung bình"],
    ["Edit", "Chỉnh sửa"],
    ["Results", "Kết quả"],
    ["Questions", "Câu hỏi"],
    ["Add a question", "Thêm câu hỏi"],
    ["Add question", "Thêm câu hỏi"],
    ["Bulk import from CSV", "Nhập hàng loạt từ CSV"],
    ["Import file", "Nhập tệp"],
    ["Generate questions with Azure AI", "Tạo câu hỏi bằng Azure AI"],
    ["Generate with AI", "Tạo bằng AI"],
    ["Settings", "Cài đặt"],
    ["Time limit (minutes)", "Thời gian làm bài (phút)"],
    ["Pass mark (%)", "Điểm đạt (%)"],
    ["Attempts per student", "Số lần làm tối đa"],
    ["Choose-by deadline (UTC)", "Hạn chốt bài (UTC)"],
    ["Save settings", "Lưu cài đặt"],
    ["Publish exam", "Mở đề thi"],
    ["Close exam", "Đóng đề thi"],
    ["Delete exam", "Xóa đề thi"],
    ["Exam results", "Kết quả bài thi"],
    ["Submissions", "Bài nộp"],
    ["Highest", "Cao nhất"],
    ["Lowest", "Thấp nhất"],
    ["Export CSV", "Xuất CSV"],
    ["HTML report", "Báo cáo HTML"],
    ["Print report", "In báo cáo"],
    ["Real-time monitoring", "Giám sát thời gian thực"],
    ["Live student progress & tab-switch alerts", "Tiến độ làm bài & cảnh báo chuyển tab trực tiếp"],
    ["Connecting...", "Đang kết nối..."],
    ["Azure Web PubSub · Connected", "Azure Web PubSub · Đã kết nối"],
    ["Active attempts", "Lượt thi đang diễn ra"],
    ["Recent activity & tab alerts", "Hoạt động & cảnh báo gần đây"],
    ["Loading...", "Đang tải..."],
    ["No activity yet.", "Chưa có hoạt động nào."],
    ["Attempt", "Lượt thi"],
    ["Score", "Điểm"],
    ["Percent", "Tỉ lệ"],
    ["Result", "Kết quả"],
    ["Integrity", "Trung thực"],
    ["Updated / Submitted (UTC)", "Cập nhật / Nộp lúc (UTC)"],
    ["Counts", "Tính điểm"],
    ["Passed", "Đạt"],
    ["Failed", "Chưa đạt"],
    ["Details", "Chi tiết"],
    ["Retake", "Thi lại"],
    ["Approve", "Phê duyệt"],
    ["Force submit", "Thu bài ngay"],
    ["No attempts in progress.", "Không có thí sinh nào đang thi."],
    ["Not started", "Chưa vào thi"],
    ["Submitted · Passed", "Đã nộp · Đạt"],
    ["Submitted · Failed", "Đã nộp · Chưa đạt"],
    ["In progress", "Đang làm"],
    ["Grading...", "Đang chấm..."],
    ["Clean", "Hợp lệ"],
    ["Assigned exams", "Bài thi được giao"],
    ["Public exams", "Bài thi công khai"],
    ["Access control & Exam assignments", "Quản lý quyền truy cập & Giao bài thi"],
    ["1. Search students by email", "1. Tìm học sinh theo email"],
    ["2. Paste multiple emails", "2. Nhập hoặc dán nhiều email cùng lúc"],
    ["Assign students to exam", "Thêm học sinh vào đề thi"],
    ["Remove", "Xóa"],
    ["Active", "Đã có tài khoản"],
    ["Pending login", "Chờ đăng nhập"],
    ["Visibility", "Chế độ hiển thị (Visibility)"],
    ["Private", "Riêng tư (Private)"],
    ["Public", "Công khai (Public)"],
    ["Save", "Lưu"],
    ["Copy", "Sao chép"],
    ["Copied", "Đã chép"],
    ["New code", "Tạo mã mới"],
    ["Take exam", "Làm bài thi"],
    ["Submit", "Nộp bài"],
    ["Exam title", "Tên bài thi"],
    ["Description", "Mô tả"],
    ["Create and add questions", "Tạo và thêm câu hỏi"],
    ["Managed exam", "Chế độ thi giám sát"],
    ["Enter fullscreen and start", "Vào toàn màn hình và bắt đầu"],
    ["Start", "Bắt đầu"],
    ["Waiting for your teacher", "Đang chờ giáo viên phê duyệt"],
    ["Return to fullscreen", "Quay lại toàn màn hình"],
    ["Continue in fullscreen", "Tiếp tục ở chế độ toàn màn hình"],
    ["Download PDF", "Tải chứng chỉ PDF"],
    ["Certificate verification", "Xác thực chứng chỉ"],
    ["Verify", "Kiểm tra"],
    ["Valid", "Hợp lệ"],
    ["Congratulations! You passed the exam 🎉", "Chúc mừng! Bạn đã vượt qua bài thi 🎉"],
    ["NOT PASSED", "CHƯA ĐẠT"],
    ["Keep going, you'll get it next time!", "Cố gắng hơn ở lần thi tiếp theo nhé!"],
    ["Certificate of completion", "Chứng chỉ hoàn thành"],
    ["Exam result slip", "Phiếu kết quả bài thi"],
    ["Download certificate (PDF)", "Tải chứng chỉ (PDF)"],
    ["Download result slip (PDF)", "Tải phiếu kết quả (PDF)"],
    ["Review your answers", "Xem lại bài làm"],
    ["Your answer", "Câu trả lời của bạn"],
    ["Correct answer", "Đáp án đúng"],
    ["Release", "Công bố kết quả"],
    ["Cancel certificate", "Hủy chứng chỉ"],
    ["No events recorded.", "Không có sự kiện nào được ghi nhận."],
    ["Your result is under review", "Kết quả của bạn đang được xem xét"],
    ["Certificate revoked", "Chứng chỉ đã bị thu hồi"],
    ["Result cancelled", "Kết quả đã bị hủy"],
    ["The score and certificate are hidden from the student until you decide.", "Điểm số và chứng chỉ đang được ẩn với sinh viên cho đến khi bạn quyết định."],
    ["Activity during this managed exam was flagged. Your teacher will review it; you will get an email when your result is available.", "Hệ thống ghi nhận dấu hiệu bất thường trong bài thi giám sát. Giáo viên sẽ xem xét và bạn sẽ nhận email khi có kết quả."],
    ["After review, your teacher cancelled the result and certificate for this exam.", "Sau khi xem xét, giáo viên đã hủy kết quả và chứng chỉ cho bài thi này."],
    ["Grading failed", "Chấm bài thất bại"],
    ["Grading your answers...", "Đang chấm bài làm của bạn..."],
    ["Your answers have been saved safely.", "Bài làm của bạn đã được lưu an toàn."],
    ["Regrade", "Chấm lại"],
    ["Revoked", "Đã thu hồi"],
    ["Invalidated", "Không còn hiệu lực"],
    ["switched tab / window", "đã chuyển tab / cửa sổ"],
    ["switched away", "đã chuyển cửa sổ"],
    ["left fullscreen", "đã thoát toàn màn hình"],
    ["reopened the exam", "đã mở lại trang thi"],
    ["went silent", "bị mất kết nối"],
    ["tried to copy", "đã thử sao chép"],
    ["tried to paste", "đã thử dán"],
    ["opened the right-click menu", "đã mở menu chuột phải"],
    ["was let back in", "đã được giáo viên duyệt cho thi tiếp"],
    ["was auto-submitted", "đã bị tự động thu bài"],
    ["was force-submitted", "đã bị giáo viên thu bài"],
    ["result released", "đã công bố kết quả"],
    ["certificate cancelled", "đã hủy chứng chỉ"],
    // Remaining pages: static strings and flash messages
    ["Create a new exam", "Tạo đề thi mới"],
    ["Publish to students", "Mở cho học sinh"],
    ["Delete this exam and all its submissions?", "Xóa đề thi này cùng toàn bộ bài nộp?"],
    ["Edits here create", "Chỉnh sửa ở đây sẽ tạo"],
    ["Code:", "Mã:"],
    ["Exam code:", "Mã bài thi:"],
    ["Access & student management", "Phân quyền & Quản lý thí sinh"],
    ["Separate with commas (", "Phân tách bằng dấu phẩy ("],
    ["), semicolons (", "), chấm phẩy ("],
    [") or new lines. Microsoft / Entra ID emails can be added before the student signs in for the first time.", ") hoặc xuống dòng. Hỗ trợ thêm trước email Microsoft / Entra ID khi học sinh chưa đăng nhập lần đầu."],
    ["Assigned students (", "Danh sách thí sinh được giao ("],
    ["Actions", "Thao tác"],
    ["Multiple answers", "Nhiều đáp án"],
    ["Delete", "Xóa bỏ"],
    ["No questions yet. Add one using the panel on the right.", "Chưa có câu hỏi nào. Thêm câu hỏi ở khung bên phải."],
    ["Illustration image (optional, max 5MB)", "Ảnh minh họa (không bắt buộc, tối đa 5MB)"],
    ["Tick the green box for the correct answer(s). Tick several boxes for a multiple-answer question.", "Đánh dấu ô xanh cho (các) đáp án đúng. Đánh dấu nhiều ô cho câu hỏi nhiều đáp án."],
    ["or", "hoặc"],
    ["Columns:", "Các cột:"],
    ["; correct is", "; cột correct là"],
    ["Versions", "Phiên bản"],
    ["Students keep the version they started with. New attempts use the current one.", "Học sinh giữ phiên bản lúc bắt đầu làm bài. Lượt làm mới dùng phiên bản hiện tại."],
    ["Current", "Hiện tại"],
    ["Restore", "Khôi phục"],
    ["Generating with AI...", "Đang tạo bằng AI..."],
    ["Please upload a document or paste lesson text first.", "Vui lòng tải lên tài liệu hoặc dán nội dung bài học trước."],
    ["No students found matching this email.", "Không tìm thấy tài khoản học sinh nào khớp email này."],
    ["Retake granted", "Đã cấp lượt thi lại"],
    ["No submissions yet.", "Chưa có bài nộp nào."],
    ["Grading error", "Lỗi chấm điểm"],
    ["Withheld", "Tạm giữ"],
    ["Released", "Đã công bố"],
    ["Cancelled", "Đã hủy"],
    ["standard", "thường"],
    ["Submit this attempt now?", "Nộp lượt làm bài này ngay?"],
    ["Local sync active", "Đang đồng bộ cục bộ"],
    ["Tab-switch warning:", "Cảnh báo chuyển tab:"],
    ["Submitted (UTC)", "Nộp lúc (UTC)"],
    ["Continue", "Tiếp tục"],
    ["Choose this one", "Chọn lượt này"],
    ["No attempts yet.", "Chưa có lượt làm bài nào."],
    ["Claim retake", "Nhận lượt thi lại"],
    ["Claim your retake? Your previous attempts are erased, your certificate for this exam is invalidated, and the exam starts immediately.", "Nhận lượt thi lại? Các lượt làm trước sẽ bị xóa, chứng chỉ của bài thi này bị vô hiệu và bài thi bắt đầu ngay."],
    ["Pick the attempt that counts. Only that attempt gets a certificate, and picking one ends the exam for you: no further attempts.", "Hãy chọn lượt được tính điểm. Chỉ lượt đó được cấp chứng chỉ, và khi đã chọn thì bài thi kết thúc: không thể làm thêm lượt nào."],
    ["Pick the attempt that counts. Only that attempt gets a certificate, and picking one ends the exam for you: no further attempts. If you have not picked by the deadline, your best attempt is picked for you.", "Hãy chọn lượt được tính điểm. Chỉ lượt đó được cấp chứng chỉ, và khi đã chọn thì bài thi kết thúc: không thể làm thêm lượt nào. Nếu đến hạn bạn chưa chọn, lượt cao điểm nhất sẽ được chọn thay bạn."],
    ["Continue exam", "Tiếp tục làm bài"],
    ["View result", "Xem kết quả"],
    ["Start exam", "Bắt đầu làm bài"],
    ["No exams are open right now. Check back later!", "Hiện chưa có bài thi nào mở. Hãy quay lại sau!"],
    ["No exams in this section.", "Không có bài thi nào trong mục này."],
    ["No exams yet. Click", "Chưa có đề thi nào. Nhấn"],
    ["to get started.", "để bắt đầu."],
    ["all attempts", "tất cả các lượt"],
    ["Reason (shown on the public verification page)", "Lý do (hiển thị trên trang xác minh công khai)"],
    ["Choose a reason...", "Chọn lý do..."],
    ["The email to the student also includes a short explanation matching the chosen reason.", "Email gửi học sinh cũng kèm lời giải thích ngắn theo lý do đã chọn."],
    ["Revoke permanently", "Thu hồi vĩnh viễn"],
    ["Release the result and issue the certificate?", "Công bố kết quả và cấp chứng chỉ?"],
    ["Cancel the certificate? The student will be emailed.", "Hủy chứng chỉ? Học sinh sẽ nhận email thông báo."],
    ["· counted", "· có tính"],
    ["tab switch", "chuyển tab"],
    ["focus lost", "mất tiêu điểm"],
    ["fullscreen exit", "thoát toàn màn hình"],
    ["reentry", "vào lại"],
    ["heartbeat gap", "khoảng mất tín hiệu"],
    ["context menu", "menu chuột phải"],
    ["approved", "đã cho phép"],
    ["auto submitted", "tự động nộp"],
    ["force submitted", "buộc nộp"],
    ["Academic misconduct", "Vi phạm quy chế thi"],
    ["Issued in error", "Cấp nhầm"],
    ["Identity could not be verified", "Không xác minh được danh tính"],
    ["Other", "Khác"],
    ["Your submission is in the", "Bài nộp của bạn đang nằm trong hàng đợi"],
    ["queue. AWS Lambda is grading it and generating your PDF certificate; this page updates automatically.", ". AWS Lambda đang chấm bài và tạo chứng chỉ PDF; trang này sẽ tự động cập nhật."],
    ["Tab switches:", "Số lần chuyển tab:"],
    ["Warning: Tab or window switch recorded", "Cảnh báo: Đã ghi nhận việc chuyển tab hoặc cửa sổ"],
    ["Tab switches in this session:", "Số lần chuyển tab trong phiên này:"],
    ["Leaving the exam tab or switching windows is logged and reported to your teacher in real time.", "Việc rời tab bài thi hoặc chuyển cửa sổ được ghi lại và báo cho giáo viên theo thời gian thực."],
    ["A violation was recorded. Your teacher must approve before you can continue. The timer keeps running.", "Đã ghi nhận một vi phạm. Giáo viên phải cho phép thì bạn mới làm tiếp được. Đồng hồ vẫn tiếp tục chạy."],
    ["This exam must be taken in fullscreen.", "Bài thi này phải làm ở chế độ toàn màn hình."],
    ["Submit your answers? You can only submit once.", "Nộp bài? Bạn chỉ được nộp một lần."],
    ["Select all correct answers", "Chọn tất cả đáp án đúng"],
    ["Your answers are submitted automatically when time runs out.", "Bài làm sẽ tự động được nộp khi hết giờ."],
    ["Grant a retake", "Cấp quyền thi lại"],
    ["Withdraw this retake?", "Thu hồi lượt thi lại này?"],
    ["Withdraw retake", "Thu hồi lượt thi lại"],
    ["When the student claims this retake:", "Khi học sinh nhận lượt thi lại này:"],
    ["permanently deleted", "xóa vĩnh viễn"],
    [": answers, scores and the managed-mode event log. They are not kept anywhere in QuizCloud.", ": gồm câu trả lời, điểm và nhật ký giám sát. Dữ liệu này không được lưu lại ở bất kỳ đâu trong QuizCloud."],
    ["Their certificate for this exam is marked", "Chứng chỉ của học sinh cho bài thi này sẽ bị đánh dấu"],
    ["on the public verification page, and they are emailed about it.", "trên trang xác minh công khai, và học sinh sẽ nhận email thông báo."],
    ["A new attempt starts immediately.", "Một lượt làm mới bắt đầu ngay."],
    ["Current attempts", "Các lượt hiện có"],
    ["Download attempts (.json)", "Tải các lượt làm bài (.json)"],
    ["Download the file now if you need these records later; it is the only copy that will remain.", "Hãy tải tệp ngay nếu sau này bạn cần các dữ liệu này; đây là bản duy nhất còn lại."],
    ["The retake gives", "Lượt thi lại cho phép"],
    ["One attempt, which counts automatically", "Một lượt, tự động được tính điểm"],
    ["Claim before (UTC, optional)", "Hạn nhận (UTC, không bắt buộc)"],
    ["Leave empty for no expiry.", "Để trống nếu không giới hạn thời gian."],
    ["I understand that claiming this retake permanently deletes these attempts and invalidates the certificate.", "Tôi hiểu rằng khi nhận lượt thi lại, các lượt này sẽ bị xóa vĩnh viễn và chứng chỉ bị vô hiệu."],
    ["Grant retake", "Cấp lượt thi lại"],
    ["Verify a certificate", "Xác minh chứng chỉ"],
    ["Check", "Tra cứu"],
    ["Not found", "Không tìm thấy"],
    ["No certificate with ID", "Không có chứng chỉ nào với mã"],
    ["was issued by QuizCloud.", "được QuizCloud cấp."],
    ["Certificate ID", "Mã chứng chỉ"],
    ["Exam", "Đề thi"],
    ["Issued", "Ngày cấp"],
    ["Status since", "Trạng thái từ"],
    ["Reason", "Lý do"],
    ["Your account has no role yet", "Tài khoản của bạn chưa có vai trò"],
    ["You signed in successfully, but you have not been assigned the", "Bạn đã đăng nhập thành công nhưng chưa được gán vai trò"],
    ["role in Microsoft Entra. Please ask an administrator to grant you access.", "trong Microsoft Entra. Vui lòng liên hệ quản trị viên để được cấp quyền."],
    ["Self-registration creates a", "Tự đăng ký sẽ tạo tài khoản"],
    ["account. Teachers sign in with Microsoft Entra ID.", ". Giáo viên đăng nhập bằng Microsoft Entra ID."],
    ["Teacher · create exams, view statistics", "Giáo viên · tạo đề thi, xem thống kê"],
    ["Student · take exams, earn certificates", "Sinh viên · làm bài thi, nhận chứng chỉ"],
    ["Demo mode: pick a sample account to continue", "Chế độ demo: chọn một tài khoản mẫu để tiếp tục"],
    ["or sign in with another account", "hoặc đăng nhập bằng tài khoản khác"],
    ["Role", "Vai trò"],
    ["In production, set", "Khi triển khai thật, đặt"],
    ["to sign in with Microsoft Entra External ID.", "để đăng nhập bằng Microsoft Entra External ID."],
    ["Invalid email or password.", "Email hoặc mật khẩu không đúng."],
    ["Please enter your name, email and role.", "Vui lòng nhập họ tên, email và vai trò."],
    ["Please enter a valid full name and email.", "Vui lòng nhập họ tên và email hợp lệ."],
    ["Password must be at least 6 characters.", "Mật khẩu phải có ít nhất 6 ký tự."],
    ["Passwords do not match.", "Mật khẩu không khớp."],
    ["An account with this email already exists. Please sign in.", "Email này đã có tài khoản. Vui lòng đăng nhập."],
    ["Student account created successfully!", "Tạo tài khoản sinh viên thành công!"],
    ["Invalid sign-in session, please try again.", "Phiên đăng nhập không hợp lệ, vui lòng thử lại."],
    ["Invalid or expired session. Please refresh and try again.", "Phiên làm việc không hợp lệ hoặc đã hết hạn. Vui lòng tải lại trang và thử lại."],
    ["Exam title is required.", "Vui lòng nhập tên đề thi."],
    ["Exam created. Now add some questions.", "Đã tạo đề thi. Giờ hãy thêm câu hỏi."],
    ["Please select students or enter at least 1 email.", "Vui lòng chọn học sinh hoặc nhập ít nhất 1 email."],
    ["Could not upload the question image. Please check storage settings.", "Không thể tải ảnh câu hỏi lên. Vui lòng kiểm tra cấu hình lưu trữ."],
    ["Question added.", "Đã thêm câu hỏi."],
    ["Please paste lesson content or upload a document (.pdf, .docx, .txt).", "Vui lòng dán nội dung bài học hoặc tải lên tài liệu (.pdf, .docx, .txt)."],
    ["Please choose a CSV file.", "Vui lòng chọn tệp CSV."],
    ["Exams with several attempts need a deadline for choosing the attempt that counts.", "Đề thi nhiều lượt cần có hạn chót để chọn lượt được tính điểm."],
    ["Settings saved.", "Đã lưu cài đặt."],
    ["Add at least 1 question before publishing the exam.", "Hãy thêm ít nhất 1 câu hỏi trước khi mở đề thi."],
    ["Exam published to students.", "Đã mở đề thi cho học sinh."],
    ["Exam closed.", "Đã đóng đề thi."],
    ["Exam deleted.", "Đã xóa đề thi."],
    ["Please enter an exam code.", "Vui lòng nhập mã bài thi."],
    ["The exam code is invalid or the exam is not open yet.", "Mã bài thi không hợp lệ hoặc bài thi chưa được mở."],
    ["Your account has no valid email to join the exam.", "Tài khoản của bạn chưa có email hợp lệ để tham gia bài thi."],
    ["Your answers were saved but grading failed. Click 'Regrade' or contact your teacher.", "Bài làm đã được lưu nhưng chấm điểm thất bại. Nhấn 'Regrade' hoặc liên hệ giáo viên."],
    ["No attempts left for this exam.", "Bạn đã hết lượt làm bài thi này."],
    ["This attempt cannot be selected.", "Không thể chọn lượt làm này."],
    ["This retake cannot be claimed right now.", "Hiện chưa thể nhận lượt thi lại này."],
    ["This retake has expired or was already used.", "Lượt thi lại đã hết hạn hoặc đã được dùng."],
    ["This student already has an open retake.", "Học sinh này đã có một lượt thi lại chưa dùng."],
    ["Confirm that you understand what claiming a retake erases.", "Hãy xác nhận bạn đã hiểu những gì sẽ bị xóa khi nhận lượt thi lại."],
    ["The student has an attempt in progress; grant the retake after it ends.", "Học sinh đang làm bài; hãy cấp lượt thi lại sau khi lượt này kết thúc."],
    ["Retake withdrawn.", "Đã thu hồi lượt thi lại."],
    ["Released, but issuing the certificate failed. Use 'Regrade' to retry.", "Đã công bố, nhưng cấp chứng chỉ thất bại. Dùng 'Regrade' để thử lại."],
    ["Result released to the student.", "Đã công bố kết quả cho học sinh."],
    ["Choose a reason (and describe it when choosing 'Other').", "Hãy chọn lý do (và mô tả khi chọn 'Khác')."],
    ["Certificate revoked; the student has been notified.", "Đã thu hồi chứng chỉ; học sinh đã được thông báo."],
    ["Certificate cancelled; the student has been notified.", "Đã hủy chứng chỉ; học sinh đã được thông báo."],
    ["Grading is still unavailable, please try again later.", "Hệ thống chấm điểm vẫn chưa sẵn sàng, vui lòng thử lại sau."],
    ["You do not have permission to access this page.", "Bạn không có quyền truy cập trang này."],
    ["Page not found.", "Không tìm thấy trang."],
    ["Uploaded document file is empty.", "Tệp tài liệu tải lên bị trống."],
    ["Document size exceeds the 10 MB limit.", "Tài liệu vượt quá giới hạn 10 MB."],
    ["Could not extract readable text from the uploaded document. If it is a scanned PDF, please paste the text manually.", "Không trích xuất được văn bản từ tài liệu. Nếu đây là PDF scan, vui lòng dán nội dung thủ công."],
    ["Lesson text cannot be empty.", "Nội dung bài học không được để trống."],
    ["No image file provided.", "Chưa chọn tệp ảnh."],
    ["Uploaded image file is empty.", "Tệp ảnh tải lên bị trống."],
    ["Image size exceeds the 5 MB limit.", "Ảnh vượt quá giới hạn 5 MB."],
    // Exam manage: AI generation, settings, visibility
    ["Upload a document (.pdf, .docx, .txt) or paste your lesson notes and let Azure OpenAI draft multiple-choice questions. You review and edit them before anything is added.", "Tải lên tài liệu (.pdf, .docx, .txt) hoặc dán nội dung bài giảng để Azure OpenAI soạn câu hỏi trắc nghiệm. Bạn sẽ duyệt và chỉnh sửa trước khi câu hỏi được thêm."],
    ["Upload document (optional, max 10MB)", "Tải lên tài liệu (không bắt buộc, tối đa 10MB)"],
    ["With more than one attempt, students pick the attempt that counts; at the deadline the best one is picked for anyone who has not. Attempt and deadline settings apply to all students immediately, not per version.", "Khi cho phép nhiều lượt, học sinh tự chọn lượt được tính điểm; đến hạn chốt, hệ thống chọn lượt cao điểm nhất cho ai chưa chọn. Cài đặt số lượt và hạn chốt áp dụng ngay cho mọi học sinh, không theo phiên bản."],
    ["Managed mode", "Chế độ giám sát"],
    ["Every violation is logged and shown on the results page. Violations: leaving fullscreen, losing focus for more than 5 seconds, reopening the exam page, and the page going silent for more than 30 seconds.", "Mọi vi phạm đều được ghi lại và hiển thị ở trang kết quả. Vi phạm gồm: thoát toàn màn hình, rời khỏi trang quá 5 giây, mở lại trang bài thi và trang mất tín hiệu quá 30 giây."],
    ["Require fullscreen", "Bắt buộc toàn màn hình"],
    ["Require my approval to continue after a violation", "Phải được tôi duyệt mới được làm tiếp sau khi vi phạm"],
    ["Without approval, a student who leaves the exam can come straight back. Violations are still logged and counted.", "Nếu không cần duyệt, học sinh rời bài thi có thể quay lại ngay. Vi phạm vẫn được ghi lại và tính."],
    ["On violation (both can be combined)", "Khi vi phạm (có thể kết hợp cả hai)"],
    ["Withhold score and certificate until I review", "Giữ lại điểm và chứng chỉ cho đến khi tôi xem xét"],
    ["Auto-submit after", "Tự động nộp bài sau"],
    ["violations", "lần vi phạm"],
    ["Allow during the exam", "Cho phép trong khi thi"],
    ["Paste", "Dán"],
    ["Right-click menu", "Menu chuột phải"],
    ["Private (assigned students only)", "Riêng tư (Chỉ học sinh được thêm)"],
    ["Public (all students)", "Công khai (Tất cả học sinh)"],
    ["Only students whose email is on the list below, or who enter the correct join code, can access and take this exam.", "Chỉ học sinh có email trong danh sách dưới đây hoặc nhập đúng mã tham gia mới được phép truy cập và làm bài."],
    ["This exam is Public. Every student account in the system can see and take it.", "Đề thi đang ở chế độ Công khai. Tất cả tài khoản học sinh trong hệ thống đều có thể nhìn thấy và làm bài."],
    ["No students are assigned to this private exam yet.", "Chưa có thí sinh nào được gán cho đề thi riêng tư này."],
    ["Private exams are only visible to assigned students and automatically get a join code (Access Code).", "Đề riêng tư chỉ hiển thị cho học sinh trong danh sách được giao và tự động sinh mã tham gia (Access Code)."],
    ["Visibility changed to Private.", "Chế độ hiển thị đã cập nhật thành Riêng tư."],
    ["Visibility changed to Public.", "Chế độ hiển thị đã cập nhật thành Công khai."],
    // AI question review
    ["Review AI questions", "Duyệt câu hỏi AI"],
    ["Nothing has been added yet. Check each answer key, edit or untick what you don't want, then add the rest.", "Chưa có câu hỏi nào được thêm. Hãy kiểm tra đáp án từng câu, sửa hoặc bỏ chọn những câu không cần, rồi thêm phần còn lại."],
    ["Azure OpenAI is not configured, so these are placeholder demo questions, not real AI output.", "Azure OpenAI chưa được cấu hình nên đây là câu hỏi mẫu minh họa, không phải kết quả AI thật."],
    ["Points", "Số điểm"],
    ["Discard all", "Hủy tất cả"],
    ["Add selected questions", "Thêm các câu đã chọn"],
    ["A question needs text, at least 2 options and at least 1 correct answer (on a filled-in option).", "Câu hỏi cần có nội dung, ít nhất 2 phương án và ít nhất 1 đáp án đúng (trên phương án đã điền)."],
    ["No questions were selected, so nothing was added.", "Chưa chọn câu hỏi nào nên không có gì được thêm."],
    ["AI did not return any valid questions. Please try again with clearer lesson text.", "AI không trả về câu hỏi hợp lệ nào. Vui lòng thử lại với nội dung bài học rõ ràng hơn."],
    ["Failed to generate questions with AI. Please try again later.", "Không thể tạo câu hỏi bằng AI. Vui lòng thử lại sau."],
    ["Could not read document. The file may be corrupted or password-protected.", "Không thể đọc tài liệu. Tệp có thể bị hỏng hoặc được bảo vệ bằng mật khẩu."],
    ["Invalid number of drafts.", "Số lượng câu hỏi nháp không hợp lệ."],
    ["The uploaded file is too large (max 10 MB).", "Tệp tải lên quá lớn (tối đa 10 MB)."],
  ];

  // Normalization aliases for mixed VI/EN source strings rendered by Jinja
  const ALIASES_TO_EN = {
    "Chưa vào thi": "Not started",
    "Đã nộp · Passed": "Submitted · Passed",
    "Đã nộp · Failed": "Submitted · Failed",
    "Đang làm (In progress)": "In progress",
    "Đã có tài khoản": "Active",
    "Chờ đăng nhập": "Pending login",
    "Bài thi được giao": "Assigned exams",
    "Bài thi công khai": "Public exams",
    "Quản lý quyền truy cập & Giao bài thi": "Access control & Exam assignments",
    "1. Tìm học sinh theo email": "1. Search students by email",
    "2. Nhập hoặc dán nhiều email cùng lúc": "2. Paste multiple emails",
    "Thêm học sinh vào đề thi": "Assign students to exam",
    "Xóa": "Remove",
    "Chế độ hiển thị (Visibility)": "Visibility",
    "Riêng tư (Private)": "Private",
    "Công khai (Public)": "Public",
    "Lưu": "Save",
    "Sao chép": "Copy",
    "Đã chép": "Copied",
    "Tạo mã mới": "New code",
    "Riêng tư": "Private",
    "Công khai": "Public",
    "Đề công khai": "Public exam",
    "Tham gia": "Join",
    "Họ tên": "Full name",
    "Trạng thái": "Status",
  };

  const TO_VI = {};
  const TO_EN = { ...ALIASES_TO_EN };
  for (const [en, vi] of PAIRS) {
    TO_VI[en] = vi;
    TO_VI[en.toLowerCase()] = vi;
    TO_EN[vi] = en;
  }
  for (const [mixed, en] of Object.entries(ALIASES_TO_EN)) {
    if (TO_VI[en]) TO_VI[mixed] = TO_VI[en];
  }

  const PH_EN_TO_VI = {
    "Hoặc dán nội dung bài giảng, tóm tắt chương học vào đây...": "Hoặc dán nội dung bài giảng, tóm tắt chương học vào đây...",
    "Nhập email học sinh để tìm (ít nhất 3 ký tự)...": "Nhập email học sinh để tìm (ít nhất 3 ký tự)...",
    "Enter exam code (e.g. QC842A)": "Nhập mã bài thi (VD: QC842A)",
    "Nhập mã bài thi (VD: QC842A)": "Nhập mã bài thi (VD: QC842A)",
    "Enter your password": "Nhập mật khẩu",
    "At least 6 characters": "Ít nhất 6 ký tự",
    "Re-enter password": "Nhập lại mật khẩu",
    "Type the question...": "Nhập nội dung câu hỏi...",
    "Option A": "Phương án A",
    "Option B": "Phương án B",
    "Option C": "Phương án C",
    "Option D": "Phương án D",
    "e.g. Cloud Computing - Midterm Quiz": "VD: Điện toán đám mây - Kiểm tra giữa kỳ",
    "Topics covered, instructions...": "Nội dung kiểm tra, hướng dẫn...",
    "Details (required for 'Other'; added after the reason)": "Chi tiết (bắt buộc khi chọn 'Khác'; thêm sau lý do)",
    "Certificate ID, e.g. 4F2A9C01BD": "Mã chứng chỉ, VD: 4F2A9C01BD",
  };
  const PH_VI_TO_EN = {
    "Hoặc dán nội dung bài giảng, tóm tắt chương học vào đây...": "Or paste lesson notes or study summary here...",
    "Nhập email học sinh để tìm (ít nhất 3 ký tự)...": "Search student by email (at least 3 characters)...",
    "Nhập mã bài thi (VD: QC842A)": "Enter exam code (e.g. QC842A)",
    "Nhập mật khẩu": "Enter your password",
    "Ít nhất 6 ký tự": "At least 6 characters",
    "Nhập lại mật khẩu": "Re-enter password",
    "Nhập nội dung câu hỏi...": "Type the question...",
    "Phương án A": "Option A",
    "Phương án B": "Option B",
    "Phương án C": "Option C",
    "Phương án D": "Option D",
    "VD: Điện toán đám mây - Kiểm tra giữa kỳ": "e.g. Cloud Computing - Midterm Quiz",
    "Nội dung kiểm tra, hướng dẫn...": "Topics covered, instructions...",
    "Chi tiết (bắt buộc khi chọn 'Khác'; thêm sau lý do)": "Details (required for 'Other'; added after the reason)",
    "Mã chứng chỉ, VD: 4F2A9C01BD": "Certificate ID, e.g. 4F2A9C01BD",
  };

  const pl = (n, w) => `${n} ${w}${n === "1" ? "" : "s"}`;
  const tv = x => TO_VI[x] || x, te = x => TO_EN[x] || x;
  const RULES_TO_VI = [
    [/^Leaving the exam tab or switching windows is logged and reported to your teacher in real time\. The exam will be submitted automatically after (\d+) violations?\.$/,
      m => `Việc rời tab bài thi hoặc chuyển cửa sổ được ghi lại và báo cho giáo viên theo thời gian thực. Bài thi sẽ tự động được nộp sau ${m[1]} lần vi phạm.`],
    [/^(graded|pending|error|in progress)((?: · [\d.]+\/[\d.]+)?)(?: · (\d+) violations?)?$/,
      m => `${{graded: "đã chấm", pending: "chờ chấm", error: "lỗi chấm", "in progress": "đang làm"}[m[1]]}${m[2]}${m[3] ? ` · ${m[3]} vi phạm` : ""}`],
    [/^· ([\d.]+%) · (Passed|Failed)$/, m => `· ${m[1]} · ${m[2] === "Passed" ? "Đạt" : "Chưa đạt"}`],
    [/^· (.+) · counted$/, m => `· ${m[1]} · có tính`],
    [/^([\d.]+) points?$/, m => `${m[1]} điểm`],
    [/^([\d.]+) pt$/, m => `${m[1]} điểm`],
    [/^([\d.]+) points?( ·)?$/, m => `${m[1]} điểm${m[2] || ""}`],
    [/^Pass at ([\d.]+%)$/, m => `Đạt từ ${m[1]}`],
    [/^(\d+) attempts · choose by (.+) UTC$/, m => `${m[1]} lượt · chọn trước ${m[2]} UTC`],
    [/^This creates version (\d+)\. (\d+) students? mid-attempt and (\d+) finished attempts? keep their current version; only new attempts get the change\. Continue\?$/,
      m => `Thao tác này tạo phiên bản ${m[1]}. ${m[2]} học sinh đang làm bài và ${m[3]} lượt đã hoàn thành vẫn giữ phiên bản hiện tại; chỉ lượt làm mới nhận thay đổi. Tiếp tục?`],
    [/^version (\d+)$/, m => `phiên bản ${m[1]}`],
    [/^\. (\d+) students? (?:is|are) mid-attempt and (\d+) attempts? (?:is|are) finished; they keep the version they started on\. Only attempts started after the edit get the change\.$/,
      m => `. ${m[1]} học sinh đang làm bài và ${m[2]} lượt đã hoàn thành; các lượt này giữ phiên bản lúc bắt đầu. Chỉ lượt bắt đầu sau khi chỉnh sửa mới nhận thay đổi.`],
    [/^Version (\d+)$/, m => `Phiên bản ${m[1]}`],
    [/^(\d+) questions? · (\d+) attempts? · (.+)$/, m => `${m[1]} câu hỏi · ${m[2]} lượt · ${m[3]}`],
    [/^Updated (.+)$/, m => `Cập nhật ${m[1]}`],
    [/^· v(\d+) · (\d+:\d+) left$/, m => `· v${m[1]} · còn ${m[2]}`],
    [/^· updated (.+)$/, m => `· cập nhật ${m[1]}`],
    [/^silent (\d+)s$/, m => `mất tín hiệu ${m[1]} giây`],
    [/^waiting: (.+)$/, m => `đang chờ: ${tv(m[1])}`],
    [/^(.+) left the exam screen at (.+) · Total violations:$/, m => `${m[1]} đã rời màn hình bài thi lúc ${m[2]} · Tổng số vi phạm:`],
    [/^(\d+)\/(\d+) attempts used$/, m => `Đã dùng ${m[1]}/${m[2]} lượt`],
    [/^Choose by (.+) UTC$/, m => `Chọn trước ${m[1]} UTC`],
    [/^Final: attempt (\d+)$/, m => `Chốt: lượt ${m[1]}`],
    [/^Start attempt (\d+) of (\d+)\? The timer starts immediately\.$/, m => `Bắt đầu lượt ${m[1]}/${m[2]}? Đồng hồ sẽ chạy ngay.`],
    [/^Start attempt (\d+)$/, m => `Bắt đầu lượt ${m[1]}`],
    [/^Claim retake \(until (.+) UTC\)$/, m => `Nhận lượt thi lại (trước ${m[1]} UTC)`],
    [/^Make attempt (\d+) the one that counts\? This is final: you cannot change it or take more attempts\.$/,
      m => `Chọn lượt ${m[1]} để tính điểm? Lựa chọn này là cuối cùng: bạn không thể đổi hay làm thêm lượt.`],
    [/^Attempt (\d+)( \(counts\))?$/, m => `Lượt ${m[1]}${m[2] ? " (được tính)" : ""}`],
    [/^Revoke certificate (\w+)$/, m => `Thu hồi chứng chỉ ${m[1]}`],
    [/^Revoke certificate (\w+)\? This is permanent: the verification page will show it as revoked with the reason, the result is hidden from the student and removed from statistics, and the student is emailed\.$/,
      m => `Thu hồi chứng chỉ ${m[1]}? Thao tác này là vĩnh viễn: trang xác minh sẽ hiện chứng chỉ bị thu hồi kèm lý do, kết quả bị ẩn với học sinh và loại khỏi thống kê, và học sinh sẽ nhận email.`],
    [/^Your teacher revoked the certificate for this exam\.(?: Reason: (.+))?$/,
      m => `Giáo viên đã thu hồi chứng chỉ của bài thi này.${m[1] ? ` Lý do: ${tv(m[1])}` : ""}`],
    [/^\/(\d+) answered$/, m => `/${m[1]} đã trả lời`],
    [/^The exam will be submitted automatically after (\d+) violations?\.$/, m => `Bài thi sẽ tự động được nộp sau ${m[1]} lần vi phạm.`],
    [/^The exam is submitted automatically after (\d+) violations?\.$/, m => `Bài thi được tự động nộp sau ${m[1]} lần vi phạm.`],
    [/^Your activity is monitored\. Leaving (fullscreen, )?switching away or reopening this page counts as a violation( and needs your teacher's approval to continue)?\.$/,
      m => `Hoạt động của bạn được giám sát. ${m[1] ? "Thoát toàn màn hình, " : ""}${m[1] ? "rời" : "Rời"} khỏi trang hoặc mở lại trang này đều tính là vi phạm${m[2] ? " và cần giáo viên cho phép mới được làm tiếp" : ""}.`],
    [/^(.+) already has an open retake(?:, valid until (.+) UTC)?\.$/, m => `${m[1]} đã có một lượt thi lại chưa dùng${m[2] ? `, hiệu lực đến ${m[2]} UTC` : ""}.`],
    [/^All (\d+) attempts? below are$/, m => `Toàn bộ ${m[1]} lượt dưới đây sẽ bị`],
    [/^Certificate (\w+) \((\w+)\)$/, m => `Chứng chỉ ${m[1]} (${tv(m[2])})`],
    [/^All (\d+) attempts again, then the student chooses$/, m => `Làm lại đủ ${m[1]} lượt, sau đó học sinh tự chọn`],
    [/^Sign-in failed: (.+)$/, m => `Đăng nhập thất bại: ${m[1]}`],
    [/^Imported (\d+) question\(s\)\.$/, m => `Đã nhập ${m[1]} câu hỏi.`],
    [/^Restored version (\d+)\.$/, m => `Đã khôi phục phiên bản ${m[1]}.`],
    [/^Attempt (\d+) selected\. This exam is now final\.$/, m => `Đã chọn lượt ${m[1]}. Bài thi đã được chốt.`],
    [/^Retake granted to (.+)\.$/, m => `Đã cấp lượt thi lại cho ${m[1]}.`],
    [/^Could not read document: (.+)$/, m => `Không thể đọc tài liệu: ${tv(m[1])}`],
    [/^Unsupported document format '(.*)'\. Allowed formats: (.+)\.$/, m => `Định dạng tài liệu '${m[1]}' không được hỗ trợ. Định dạng cho phép: ${m[2]}.`],
    [/^Invalid image format '(.*)'\. Allowed formats: (.+)\.$/, m => `Định dạng ảnh '${m[1]}' không hợp lệ. Định dạng cho phép: ${m[2]}.`],
    [/^line (\d+): (.+)$/, m => `dòng ${m[1]}: ${tv(m[2])}`],
    [/^New join code created: (.+)\.$/, m => `Đã tạo mã tham gia mới: ${m[1]}.`],
    [/^Removed (.+) from the assigned students\.$/, m => `Đã xóa ${m[1]} khỏi danh sách thí sinh.`],
    [/^You already have access to the exam '(.+)'\.$/, m => `Bạn đã có quyền truy cập bài thi '${m[1]}'.`],
    [/^Access granted to the exam: (.+)\.$/, m => `Đã mở quyền truy cập bài thi: ${m[1]}.`],
    [/^Added (\d+) students?((?:, skipped .+?)*)\.$/, m => `Đã thêm ${m[1]} học sinh${m[2].replace(/, skipped (\d+) existing emails?/, ", bỏ qua $1 email đã tồn tại").replace(/, skipped (\d+) invalid emails?/, ", bỏ qua $1 email không hợp lệ")}.`],
  ];
  const RULES_TO_EN = [
    [/^Việc rời tab bài thi hoặc chuyển cửa sổ được ghi lại và báo cho giáo viên theo thời gian thực\. Bài thi sẽ tự động được nộp sau (\d+) lần vi phạm\.$/,
      m => `Leaving the exam tab or switching windows is logged and reported to your teacher in real time. The exam will be submitted automatically after ${pl(m[1], "violation")}.`],
    [/^(đã chấm|chờ chấm|lỗi chấm|đang làm)((?: · [\d.]+\/[\d.]+)?)(?: · (\d+) vi phạm)?$/,
      m => `${{"đã chấm": "graded", "chờ chấm": "pending", "lỗi chấm": "error", "đang làm": "in progress"}[m[1]]}${m[2]}${m[3] ? ` · ${pl(m[3], "violation")}` : ""}`],
    [/^· ([\d.]+%) · (Đạt|Chưa đạt)$/, m => `· ${m[1]} · ${m[2] === "Đạt" ? "Passed" : "Failed"}`],
    [/^· (.+) · có tính$/, m => `· ${m[1]} · counted`],
    [/^([\d.]+) điểm( ·)?$/, m => `${pl(m[1], "point")}${m[2] || ""}`],
    [/^Đạt từ ([\d.]+%)$/, m => `Pass at ${m[1]}`],
    [/^(\d+) lượt · chọn trước (.+) UTC$/, m => `${m[1]} attempts · choose by ${m[2]} UTC`],
    [/^Thao tác này tạo phiên bản (\d+)\. (\d+) học sinh đang làm bài và (\d+) lượt đã hoàn thành vẫn giữ phiên bản hiện tại; chỉ lượt làm mới nhận thay đổi\. Tiếp tục\?$/,
      m => `This creates version ${m[1]}. ${pl(m[2], "student")} mid-attempt and ${pl(m[3], "finished attempt")} keep their current version; only new attempts get the change. Continue?`],
    [/^phiên bản (\d+)$/, m => `version ${m[1]}`],
    [/^\. (\d+) học sinh đang làm bài và (\d+) lượt đã hoàn thành; các lượt này giữ phiên bản lúc bắt đầu\. Chỉ lượt bắt đầu sau khi chỉnh sửa mới nhận thay đổi\.$/,
      m => `. ${pl(m[1], "student")} ${m[1] === "1" ? "is" : "are"} mid-attempt and ${pl(m[2], "attempt")} ${m[2] === "1" ? "is" : "are"} finished; they keep the version they started on. Only attempts started after the edit get the change.`],
    [/^Phiên bản (\d+)$/, m => `Version ${m[1]}`],
    [/^(\d+) câu hỏi · (\d+) lượt · (.+)$/, m => `${pl(m[1], "question")} · ${pl(m[2], "attempt")} · ${m[3]}`],
    [/^Cập nhật (.+)$/, m => `Updated ${m[1]}`],
    [/^· v(\d+) · còn (\d+:\d+)$/, m => `· v${m[1]} · ${m[2]} left`],
    [/^· cập nhật (.+)$/, m => `· updated ${m[1]}`],
    [/^mất tín hiệu (\d+) giây$/, m => `silent ${m[1]}s`],
    [/^đang chờ: (.+)$/, m => `waiting: ${te(m[1])}`],
    [/^(.+) đã rời màn hình bài thi lúc (.+) · Tổng số vi phạm:$/, m => `${m[1]} left the exam screen at ${m[2]} · Total violations:`],
    [/^Đã dùng (\d+)\/(\d+) lượt$/, m => `${m[1]}/${m[2]} attempts used`],
    [/^Chọn trước (.+) UTC$/, m => `Choose by ${m[1]} UTC`],
    [/^Chốt: lượt (\d+)$/, m => `Final: attempt ${m[1]}`],
    [/^Bắt đầu lượt (\d+)\/(\d+)\? Đồng hồ sẽ chạy ngay\.$/, m => `Start attempt ${m[1]} of ${m[2]}? The timer starts immediately.`],
    [/^Bắt đầu lượt (\d+)$/, m => `Start attempt ${m[1]}`],
    [/^Nhận lượt thi lại \(trước (.+) UTC\)$/, m => `Claim retake (until ${m[1]} UTC)`],
    [/^Chọn lượt (\d+) để tính điểm\? Lựa chọn này là cuối cùng: bạn không thể đổi hay làm thêm lượt\.$/,
      m => `Make attempt ${m[1]} the one that counts? This is final: you cannot change it or take more attempts.`],
    [/^Lượt (\d+)( \(được tính\))?$/, m => `Attempt ${m[1]}${m[2] ? " (counts)" : ""}`],
    [/^Thu hồi chứng chỉ (\w+)$/, m => `Revoke certificate ${m[1]}`],
    [/^Thu hồi chứng chỉ (\w+)\? Thao tác này là vĩnh viễn: trang xác minh sẽ hiện chứng chỉ bị thu hồi kèm lý do, kết quả bị ẩn với học sinh và loại khỏi thống kê, và học sinh sẽ nhận email\.$/,
      m => `Revoke certificate ${m[1]}? This is permanent: the verification page will show it as revoked with the reason, the result is hidden from the student and removed from statistics, and the student is emailed.`],
    [/^Giáo viên đã thu hồi chứng chỉ của bài thi này\.(?: Lý do: (.+))?$/,
      m => `Your teacher revoked the certificate for this exam.${m[1] ? ` Reason: ${te(m[1])}` : ""}`],
    [/^\/(\d+) đã trả lời$/, m => `/${m[1]} answered`],
    [/^Bài thi sẽ tự động được nộp sau (\d+) lần vi phạm\.$/, m => `The exam will be submitted automatically after ${pl(m[1], "violation")}.`],
    [/^Bài thi được tự động nộp sau (\d+) lần vi phạm\.$/, m => `The exam is submitted automatically after ${pl(m[1], "violation")}.`],
    [/^Hoạt động của bạn được giám sát\. (Thoát toàn màn hình, )?[Rr]ời khỏi trang hoặc mở lại trang này đều tính là vi phạm( và cần giáo viên cho phép mới được làm tiếp)?\.$/,
      m => `Your activity is monitored. Leaving ${m[1] ? "fullscreen, " : ""}switching away or reopening this page counts as a violation${m[2] ? " and needs your teacher's approval to continue" : ""}.`],
    [/^(.+) đã có một lượt thi lại chưa dùng(?:, hiệu lực đến (.+) UTC)?\.$/, m => `${m[1]} already has an open retake${m[2] ? `, valid until ${m[2]} UTC` : ""}.`],
    [/^Toàn bộ (\d+) lượt dưới đây sẽ bị$/, m => `All ${pl(m[1], "attempt")} below are`],
    [/^Chứng chỉ (\w+) \((.+)\)$/, m => `Certificate ${m[1]} (${te(m[2])})`],
    [/^Làm lại đủ (\d+) lượt, sau đó học sinh tự chọn$/, m => `All ${m[1]} attempts again, then the student chooses`],
    [/^Đăng nhập thất bại: (.+)$/, m => `Sign-in failed: ${m[1]}`],
    [/^Đã nhập (\d+) câu hỏi\.$/, m => `Imported ${m[1]} question(s).`],
    [/^Đã khôi phục phiên bản (\d+)\.$/, m => `Restored version ${m[1]}.`],
    [/^Đã chọn lượt (\d+)\. Bài thi đã được chốt\.$/, m => `Attempt ${m[1]} selected. This exam is now final.`],
    [/^Đã cấp lượt thi lại cho (.+)\.$/, m => `Retake granted to ${m[1]}.`],
    [/^Không thể đọc tài liệu: (.+)$/, m => `Could not read document: ${te(m[1])}`],
    [/^Định dạng tài liệu '(.*)' không được hỗ trợ\. Định dạng cho phép: (.+)\.$/, m => `Unsupported document format '${m[1]}'. Allowed formats: ${m[2]}.`],
    [/^Định dạng ảnh '(.*)' không hợp lệ\. Định dạng cho phép: (.+)\.$/, m => `Invalid image format '${m[1]}'. Allowed formats: ${m[2]}.`],
    [/^dòng (\d+): (.+)$/, m => `line ${m[1]}: ${te(m[2])}`],
    [/^Đã tạo mã tham gia mới: (.+)\.$/, m => `New join code created: ${m[1]}.`],
    [/^Đã xóa (.+) khỏi danh sách thí sinh\.$/, m => `Removed ${m[1]} from the assigned students.`],
    [/^Bạn đã có quyền truy cập bài thi '(.+)'\.$/, m => `You already have access to the exam '${m[1]}'.`],
    [/^Đã mở quyền truy cập bài thi: (.+)\.$/, m => `Access granted to the exam: ${m[1]}.`],
    [/^Đã thêm (\d+) học sinh((?:, bỏ qua .+?)*)\.$/, m => `Added ${pl(m[1], "student")}${m[2].replace(/, bỏ qua (\d+) email đã tồn tại/, (_, n) => `, skipped ${pl(n, "existing email")}`).replace(/, bỏ qua (\d+) email không hợp lệ/, (_, n) => `, skipped ${pl(n, "invalid email")}`)}.`],
  ];

  let applying = false;

  function translateText(raw, lang) {
    const norm = raw.replace(/\s+/g, " ").trim();
    if (!norm) return null;
    const map = lang === "vi" ? TO_VI : TO_EN;
    if (map[norm]) return map[norm];
    if (lang === "vi" && map[norm.toLowerCase()]) return map[norm.toLowerCase()];

    let m;
    if (lang === "vi") {
      if ((m = norm.match(/^Hello,\s*(.+?)\s*(👋)?$/))) return `Xin chào, ${m[1]}${m[2] ? " " + m[2] : ""}`;
      if ((m = norm.match(/^(\d+)\s+questions?$/i))) return `${m[1]} câu hỏi`;
      if ((m = norm.match(/^(\d+)\s+submissions?$/i))) return `${m[1]} bài nộp`;
      if ((m = norm.match(/^(\d+)\s+violations?$/i))) return `${m[1]} vi phạm`;
      if ((m = norm.match(/^(\d+)\s+min$/i))) return `${m[1]} phút`;
      if ((m = norm.match(/^(\d+\/\d+)\s+answered$/i))) return `${m[1]} đã trả lời`;
      if ((m = norm.match(/^(\d+)\s+students?$/i))) return `${m[1]} học sinh`;
      if ((m = norm.match(/^Passed\s*·\s*([\d.]+%)$/i))) return `Đạt · ${m[1]}`;
      if ((m = norm.match(/^Failed\s*·\s*([\d.]+%)$/i))) return `Chưa đạt · ${m[1]}`;
      if ((m = norm.match(/^(\d+\/\d+)\s+attempts$/i))) return `${m[1]} lượt`;
      if ((m = norm.match(/^All \((\d+)\)$/))) return `Tất cả (${m[1]})`;
      if ((m = norm.match(/^Assigned exams \((\d+)\)$/))) return `Bài thi được giao (${m[1]})`;
      if ((m = norm.match(/^Public exams \((\d+)\)$/))) return `Đề công khai (${m[1]})`;
      if ((m = norm.match(/^Assigned students \((\d+)\)$/))) return `Danh sách thí sinh được giao (${m[1]})`;
      if ((m = norm.match(/^([\d.]+\/[\d.]+)\s+points?$/i))) return `${m[1]} điểm`;
      if ((m = norm.match(/^([\d.]+\/[\d.]+)\s+pt$/i))) return `${m[1]} điểm`;
      if ((m = norm.match(/^(\d+)\s+correct$/i))) return `${m[1]} câu đúng`;
      if ((m = norm.match(/^(\d+)\s+wrong$/i))) return `${m[1]} câu sai`;
      if ((m = norm.match(/^Pass mark\s+([\d.]+%)$/i))) return `Điểm đạt ${m[1]}`;
      if ((m = norm.match(/^Private · (\d+) students?$/))) return `Riêng tư · ${m[1]} học sinh`;
      if ((m = norm.match(/^Question (\d+)$/))) return `Câu ${m[1]}`;
      if ((m = norm.match(/^Adding these creates version (\d+)\.$/))) return `Thêm các câu này sẽ tạo phiên bản ${m[1]}.`;
      if ((m = norm.match(/^(\d+) students? mid-attempt and (\d+) finished attempts? keep the version they started on\. Only attempts started afterwards get the new questions\.$/))) {
        return `${m[1]} học sinh đang làm bài và ${m[2]} lượt đã hoàn thành vẫn giữ phiên bản lúc bắt đầu. Chỉ các lượt bắt đầu sau đó mới nhận câu hỏi mới.`;
      }
      if ((m = norm.match(/^(\d+) questions? needs? fixing before anything can be added\.$/))) return `${m[1]} câu hỏi cần sửa trước khi có thể thêm.`;
      if ((m = norm.match(/^This creates version (\d+); only new attempts get the added questions\. Continue\?$/))) {
        return `Thao tác này tạo phiên bản ${m[1]}; chỉ các lượt làm bài mới nhận câu hỏi được thêm. Tiếp tục?`;
      }
      if ((m = norm.match(/^Added (\d+) AI-generated question\(s\)\.$/))) return `Đã thêm ${m[1]} câu hỏi do AI tạo.`;
      if (norm.match(/^·?\s*Generated by AWS Lambda, stored on Amazon S3, time-limited presigned link$/i)) {
        return `${norm.startsWith("·") ? "· " : ""}Tạo bởi AWS Lambda, lưu trên Amazon S3, liên kết tải có thời hạn`;
      }
    } else {
      if ((m = norm.match(/^Xin chào,\s*(.+?)\s*(👋)?$/))) return `Hello, ${m[1]}${m[2] ? " " + m[2] : ""}`;
      if ((m = norm.match(/^(\d+)\s+câu hỏi$/i))) return `${m[1]} question${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+bài nộp$/i))) return `${m[1]} submission${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+vi phạm$/i))) return `${m[1]} violation${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+phút$/i))) return `${m[1]} min`;
      if ((m = norm.match(/^(\d+\/\d+)\s+đã trả lời$/i))) return `${m[1]} answered`;
      if ((m = norm.match(/^(\d+)\s+học sinh$/i))) return `${m[1]} student${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^Đạt\s*·\s*([\d.]+%)$/i))) return `Passed · ${m[1]}`;
      if ((m = norm.match(/^Chưa đạt\s*·\s*([\d.]+%)$/i))) return `Failed · ${m[1]}`;
      if ((m = norm.match(/^(\d+\/\d+)\s+lượt$/i))) return `${m[1]} attempts`;
      if ((m = norm.match(/^Tất cả \((\d+)\)$/))) return `All (${m[1]})`;
      if ((m = norm.match(/^Bài thi được giao \((\d+)\)$/))) return `Assigned exams (${m[1]})`;
      if ((m = norm.match(/^Đề công khai \((\d+)\)$/))) return `Public exams (${m[1]})`;
      if ((m = norm.match(/^Danh sách thí sinh được giao \((\d+)\)$/))) return `Assigned students (${m[1]})`;
      if ((m = norm.match(/^([\d.]+\/[\d.]+)\s+điểm$/i))) return `${m[1]} points`;
      if ((m = norm.match(/^(\d+)\s+câu đúng$/i))) return `${m[1]} correct`;
      if ((m = norm.match(/^(\d+)\s+câu sai$/i))) return `${m[1]} wrong`;
      if ((m = norm.match(/^Điểm đạt\s+([\d.]+%)$/i))) return `Pass mark ${m[1]}`;
      if ((m = norm.match(/^Riêng tư · (\d+) học sinh$/))) return `Private · ${m[1]} student${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^Câu (\d+)$/))) return `Question ${m[1]}`;
      if ((m = norm.match(/^Thêm các câu này sẽ tạo phiên bản (\d+)\.$/))) return `Adding these creates version ${m[1]}.`;
      if ((m = norm.match(/^(\d+) học sinh đang làm bài và (\d+) lượt đã hoàn thành vẫn giữ phiên bản lúc bắt đầu\. Chỉ các lượt bắt đầu sau đó mới nhận câu hỏi mới\.$/))) {
        return `${m[1]} student${m[1] === "1" ? "" : "s"} mid-attempt and ${m[2]} finished attempt${m[2] === "1" ? "" : "s"} keep the version they started on. Only attempts started afterwards get the new questions.`;
      }
      if ((m = norm.match(/^(\d+) câu hỏi cần sửa trước khi có thể thêm\.$/))) {
        return `${m[1]} question${m[1] === "1" ? " needs" : "s need"} fixing before anything can be added.`;
      }
      if ((m = norm.match(/^Thao tác này tạo phiên bản (\d+); chỉ các lượt làm bài mới nhận câu hỏi được thêm\. Tiếp tục\?$/))) {
        return `This creates version ${m[1]}; only new attempts get the added questions. Continue?`;
      }
      if ((m = norm.match(/^Đã thêm (\d+) câu hỏi do AI tạo\.$/))) return `Added ${m[1]} AI-generated question(s).`;
      if (norm.match(/^·?\s*Tạo bởi AWS Lambda, lưu trên Amazon S3, liên kết tải có thời hạn$/i)) {
        return `${norm.startsWith("·") ? "· " : ""}Generated by AWS Lambda, stored on Amazon S3, time-limited presigned link`;
      }
    }
    for (const [re, fn] of lang === "vi" ? RULES_TO_VI : RULES_TO_EN) {
      if ((m = norm.match(re))) return fn(m);
    }
    return null;
  }

  function applyLanguage(lang) {
    if (applying) return;
    applying = true;
    try {
      document.documentElement.lang = lang;
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
      let node;
      while ((node = walker.nextNode())) {
        const parentTag = node.parentElement?.tagName;
        if (!parentTag || parentTag === "SCRIPT" || parentTag === "STYLE" || parentTag === "CODE") continue;
        const translated = translateText(node.nodeValue, lang);
        if (translated !== null) {
          const lead = node.nodeValue.match(/^\s*/)[0];
          const trail = node.nodeValue.match(/\s*$/)[0];
          const next = `${lead}${translated}${trail}`;
          if (next !== node.nodeValue) node.nodeValue = next;
        }
      }
      const phMap = lang === "vi" ? PH_EN_TO_VI : PH_VI_TO_EN;
      document.querySelectorAll("[placeholder]").forEach(el => {
        const cur = el.getAttribute("placeholder");
        if (phMap[cur]) el.setAttribute("placeholder", phMap[cur]);
      });
      document.querySelectorAll(".qc-lang-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.lang === lang);
      });
    } finally {
      applying = false;
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-bs-theme", theme);
    const icon = document.getElementById("qc-theme-icon");
    if (icon) {
      icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars";
    }
  }

  window.qcT = text => translateText(text, localStorage.getItem("qc_lang") || "en") || text;

  window.qcSetLang = lang => {
    localStorage.setItem("qc_lang", lang);
    applyLanguage(lang);
  };

  window.qcToggleTheme = () => {
    const cur = document.documentElement.getAttribute("data-bs-theme") || "light";
    const next = cur === "dark" ? "light" : "dark";
    localStorage.setItem("qc_theme", next);
    applyTheme(next);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem("qc_theme") || "light";
    const savedLang = localStorage.getItem("qc_lang") || "en";
    applyTheme(savedTheme);
    applyLanguage(savedLang);

    const observer = new MutationObserver(() => {
      if (applying) return;
      const lang = localStorage.getItem("qc_lang") || "en";
      applyLanguage(lang);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
