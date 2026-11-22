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
    ["Points", "Điểm"],
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
  };

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
