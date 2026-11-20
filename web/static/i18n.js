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
    ["STUDENT DASHBOARD", "BẢNG ĐIỀU KHIỂN SINH VIÊN"],
    ["New exam", "Tạo đề mới"],
    ["+ New exam", "+ Tạo đề mới"],
    ["Exams", "Bài thi"],
    ["Published", "Đã mở"],
    ["Draft", "Bản nháp"],
    ["Graded submissions", "Bài đã chấm"],
    ["Average score", "Điểm trung bình"],
    ["Pass rate", "Tỉ lệ đạt"],
    ["MY EXAMS", "BÀI THI CỦA TÔI"],
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
    "Enter your password": "Nhập mật khẩu",
    "At least 6 characters": "Ít nhất 6 ký tự",
    "Re-enter password": "Nhập lại mật khẩu",
    "Type the question...": "Nhập nội dung câu hỏi...",
  };
  const PH_VI_TO_EN = {
    "Hoặc dán nội dung bài giảng, tóm tắt chương học vào đây...": "Or paste lesson notes or study summary here...",
    "Nhập email học sinh để tìm (ít nhất 3 ký tự)...": "Search student by email (at least 3 characters)...",
    "Nhập mật khẩu": "Enter your password",
    "Ít nhất 6 ký tự": "At least 6 characters",
    "Nhập lại mật khẩu": "Re-enter password",
    "Nhập nội dung câu hỏi...": "Type the question...",
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
      if ((m = norm.match(/^Assigned students \((\d+)\)$/))) return `Danh sách thí sinh được giao (${m[1]})`;
    } else {
      if ((m = norm.match(/^Xin chào,\s*(.+?)\s*(👋)?$/))) return `Hello, ${m[1]}${m[2] ? " " + m[2] : ""}`;
      if ((m = norm.match(/^(\d+)\s+câu hỏi$/i))) return `${m[1]} question${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+bài nộp$/i))) return `${m[1]} submission${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+vi phạm$/i))) return `${m[1]} violation${m[1] === "1" ? "" : "s"}`;
      if ((m = norm.match(/^(\d+)\s+phút$/i))) return `${m[1]} min`;
      if ((m = norm.match(/^(\d+\/\d+)\s+đã trả lời$/i))) return `${m[1]} answered`;
      if ((m = norm.match(/^Danh sách thí sinh được giao \((\d+)\)$/))) return `Assigned students (${m[1]})`;
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
