(function () {
  "use strict";

  // ================================================================
  // 色碼複製功能 — 點擊色碼文字時複製 HEX 值至剪貼簿
  // ================================================================
  document.addEventListener("click", function (e) {
    var target = e.target;
    if (target.classList.contains("color-hex")) {
      var hex = target.getAttribute("data-hex") || target.textContent.trim();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(hex).then(function () {
          showToast("已複製色碼：" + hex);
        })["catch"](function () {
          fallbackCopy(hex);
        });
      } else {
        fallbackCopy(hex);
      }
    }
  });

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      showToast("已複製色碼：" + text);
    } catch (e) {
      showToast("複製失敗，請手動選取");
    }
    document.body.removeChild(ta);
  }

  // ================================================================
  // Toast 訊息
  // ================================================================
  var toastEl = null;

  function showToast(msg) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "toast";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(function () {
      toastEl.classList.remove("show");
    }, 2000);
  }

  // ================================================================
  // 目錄摺疊（classic wiki TOC toggle）
  // ================================================================
  var tocTitle = document.querySelector(".toc-title");
  if (tocTitle) {
    tocTitle.style.cursor = "pointer";
    tocTitle.addEventListener("click", function () {
      var list = this.nextElementSibling;
      if (list) {
        list.style.display = list.style.display === "none" ? "" : "none";
      }
    });
  }

  // ================================================================
  // 回滾按鈕確認
  // ================================================================
  document.addEventListener("click", function (e) {
    if (e.target.classList.contains("rollback-btn")) {
      if (!confirm("確定要回滾至此版本？")) {
        e.preventDefault();
      }
    }
  });

  // ================================================================
  // 第六章：Spoiler 折疊切換
  // ================================================================
  document.addEventListener("click", function (e) {
    var toggle = e.target.closest(".spoiler-toggle");
    if (toggle) {
      var content = toggle.parentNode.querySelector(".spoiler-content");
      if (content) {
        var isHidden = content.classList.toggle("hidden");
        toggle.textContent = isHidden ? "[顯示]" : "[隱藏]";
      }
    }
  });

  // ================================================================
  // 第六章：腳註浮動顯示（hover 顯示內容）
  // ================================================================
  var footnoteTooltip = null;
  document.addEventListener("mouseover", function (e) {
    var ref = e.target.closest(".footnote-ref");
    if (!ref) {
      if (footnoteTooltip) {
        footnoteTooltip.style.display = "none";
      }
      return;
    }
    var content = ref.getAttribute("data-content");
    if (!content) return;
    if (!footnoteTooltip) {
      footnoteTooltip = document.createElement("div");
      footnoteTooltip.style.cssText =
        "position:fixed;background:#fff;border:1px solid #a2a9b1;" +
        "padding:0.4rem 0.6rem;font-size:0.85em;max-width:320px;" +
        "z-index:1000;box-shadow:1px 1px 4px rgba(0,0,0,0.15);";
      document.body.appendChild(footnoteTooltip);
    }
    footnoteTooltip.textContent = content;
    footnoteTooltip.style.display = "block";
    var rect = ref.getBoundingClientRect();
    var top = rect.bottom + 4;
    var left = rect.left;
    if (left + 320 > window.innerWidth) {
      left = window.innerWidth - 330;
    }
    footnoteTooltip.style.top = top + "px";
    footnoteTooltip.style.left = left + "px";
  });

  // ================================================================
  // 第七章：討論串折疊
  // ================================================================
  document.addEventListener("click", function (e) {
    var header = e.target.closest(".thread-header");
    if (header) {
      var body = header.parentNode.querySelector(".thread-body");
      var replies = header.parentNode.querySelectorAll(".thread-reply");
      if (body) {
        body.style.display = body.style.display === "none" ? "" : "none";
      }
      replies.forEach(function (r) {
        r.style.display = r.style.display === "none" ? "" : "none";
      });
    }
  });

})();
