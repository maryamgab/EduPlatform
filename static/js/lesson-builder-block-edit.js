(function () {
  function init() {
    const editor = document.getElementById("rtEditor");
    const toolbar = document.getElementById("rtToolbar");
    const hidden = document.querySelector("textarea");
    const typeSelect = document.querySelector('select[name="type"]');
    const textSection = document.querySelector('.js-text-section');
    const mediaSections = document.querySelectorAll('.js-media-section');

    function toggleSections() {
      if (!typeSelect) return;
      const isText = typeSelect.value === 'text';

      if (textSection) {
        textSection.classList.toggle('is-hidden', !isText);
      }

      mediaSections.forEach((section) => {
        section.classList.toggle('is-hidden', isText);
      });
    }

    if (typeSelect) {
      typeSelect.addEventListener('change', toggleSections);
      toggleSections();
    }

    if (!editor || !toolbar || !hidden) return;

    try { document.execCommand("styleWithCSS", false, true); } catch (e) {}

    editor.innerHTML = hidden.value || "";

    function syncToHidden() {
      hidden.value = editor.innerHTML;
      hidden.dispatchEvent(new Event("input", { bubbles: true }));
      hidden.dispatchEvent(new Event("change", { bubbles: true }));
    }

    let savedRange = null;

    function saveSelection() {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const r = sel.getRangeAt(0);
      if (!editor.contains(r.startContainer)) return;
      savedRange = r.cloneRange();
    }

    function restoreSelection() {
      editor.focus();
      const sel = window.getSelection();
      if (!sel) return;
      sel.removeAllRanges();
      if (savedRange) sel.addRange(savedRange);
    }

    function setActive(attr, value) {
      toolbar.querySelectorAll("button[" + attr + "]").forEach(btn => {
        btn.classList.toggle("rt-active", btn.getAttribute(attr) === value);
      });
    }

    function updateCmdButtons() {
      toolbar.querySelectorAll("button[data-cmd]").forEach(btn => {
        const cmd = btn.getAttribute("data-cmd");
        let active = false;
        try { active = document.queryCommandState(cmd); } catch (e) {}
        btn.classList.toggle("rt-active", active);
      });
    }

    function rgbToHex(rgb) {
      const m = (rgb || "").match(/\d+/g);
      if (!m || m.length < 3) return null;
      const r = parseInt(m[0], 10), g = parseInt(m[1], 10), b = parseInt(m[2], 10);
      const toHex = (n) => n.toString(16).padStart(2, "0");
      return ("#" + toHex(r) + toHex(g) + toHex(b)).toUpperCase();
    }

    function closestPaletteColor(hex) {
      const palette = ["#000000", "#1D4ED8", "#15803D", "#B91C1C"];
      const up = (hex || "").toUpperCase();
      if (palette.includes(up)) return up;

      function hexToRgb(h) {
        const x = (h || "").replace("#", "");
        if (x.length !== 6) return null;
        return { r: parseInt(x.slice(0,2),16), g: parseInt(x.slice(2,4),16), b: parseInt(x.slice(4,6),16) };
      }

      const c = hexToRgb(up);
      if (!c) return "#000000";

      let best = palette[0], bestD = Infinity;
      for (const p of palette) {
        const pr = hexToRgb(p);
        const d = (c.r - pr.r) ** 2 + (c.g - pr.g) ** 2 + (c.b - pr.b) ** 2;
        if (d < bestD) { bestD = d; best = p; }
      }
      return best;
    }

    function closestFontSize(px) {
      const sizes = [14, 16, 20];
      const n = parseFloat(px || "16");
      let best = sizes[0], bestD = Infinity;
      for (const s of sizes) {
        const d = Math.abs(n - s);
        if (d < bestD) { bestD = d; best = s; }
      }
      return String(best);
    }

    function getCaretStyle() {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return { color: "#000000", size: "14" };
      const r = sel.getRangeAt(0);
      if (!editor.contains(r.startContainer)) return { color: "#000000", size: "14" };

      let el = r.startContainer;
      if (el.nodeType === Node.TEXT_NODE) el = el.parentElement;
      if (!el || el.nodeType !== Node.ELEMENT_NODE) el = editor;

      const cs = window.getComputedStyle(el);
      return {
        color: closestPaletteColor(rgbToHex(cs.color)),
        size: closestFontSize(cs.fontSize),
      };
    }

    function updateToolbarFromCaret() {
      updateCmdButtons();
      const st = getCaretStyle();
      setActive("data-color", st.color);
      setActive("data-size", st.size);
    }

    function applyFontPx(px) {
      restoreSelection();

      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;

      const range = sel.getRangeAt(0);
      if (!editor.contains(range.startContainer)) return;

      if (!range.collapsed) {
        const span = document.createElement("span");
        span.style.fontSize = px + "px";
        try {
          range.surroundContents(span);
        } catch (e) {
          const frag = range.extractContents();
          span.appendChild(frag);
          range.insertNode(span);
        }

        sel.removeAllRanges();
        const after = document.createRange();
        after.setStartAfter(span);
        after.collapse(true);
        sel.addRange(after);

        saveSelection();
        return;
      }

      const span = document.createElement("span");
      span.style.fontSize = px + "px";
      span.appendChild(document.createTextNode("\u200B"));

      range.insertNode(span);

      const inside = document.createRange();
      inside.setStart(span.firstChild, 1);
      inside.collapse(true);

      sel.removeAllRanges();
      sel.addRange(inside);

      saveSelection();
    }

    editor.addEventListener("input", () => {
      syncToHidden();
      saveSelection();
      updateToolbarFromCaret();
    });

    ["keyup", "mouseup", "focus", "click"].forEach(evt => {
      editor.addEventListener(evt, () => {
        saveSelection();
        updateToolbarFromCaret();
      });
    });

    toolbar.addEventListener("mousedown", (e) => e.preventDefault());

    toolbar.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      e.preventDefault();

      const cmd = btn.getAttribute("data-cmd");
      const color = btn.getAttribute("data-color");
      const size = btn.getAttribute("data-size");

      if (cmd) {
        restoreSelection();
        document.execCommand(cmd, false, null);
        syncToHidden();
        saveSelection();
        updateToolbarFromCaret();
        return;
      }

      if (color) {
        restoreSelection();
        document.execCommand("foreColor", false, color);
        syncToHidden();
        saveSelection();
        updateToolbarFromCaret();
        return;
      }

      if (size) {
        applyFontPx(size);
        syncToHidden();
        updateToolbarFromCaret();
        return;
      }
    });

    document.getElementById("blockForm").addEventListener("submit", () => {
      syncToHidden();
    });

    saveSelection();
    updateToolbarFromCaret();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();


(function () {
  function init() {
    const hidden = document.querySelector("textarea");
    const editor = document.getElementById("rtEditor");
    const toolbar = document.getElementById("rtToolbar");

    if (hidden && editor) {
      editor.innerHTML = hidden.value || "";
    }

    const typeSelect = document.querySelector('select[name="type"]');
    const textSection = document.querySelector('.js-text-section');
    const mediaSections = document.querySelectorAll('.js-media-section');

    function toggleSections() {
      if (!typeSelect) return;
      const isText = typeSelect.value === "text";

      if (textSection) {
        textSection.classList.toggle("is-hidden", !isText);
      }

      mediaSections.forEach((section) => {
        section.classList.toggle("is-hidden", isText);
      });
    }

    if (typeSelect) {
      typeSelect.addEventListener("change", toggleSections);
      toggleSections();
    }

    if (!hidden || !editor || !toolbar) return;

    function sync() {
      hidden.value = editor.innerHTML;
    }

    toolbar.addEventListener("click", function (e) {
      const btn = e.target.closest("button");
      if (!btn) return;

      e.preventDefault();
      editor.focus();

      const cmd = btn.dataset.cmd;
      const size = btn.dataset.size;
      const color = btn.dataset.color;

      if (cmd) {
        document.execCommand(cmd, false, null);
      } else if (color) {
        document.execCommand("foreColor", false, color);
      } else if (size) {
        document.execCommand("fontSize", false, "7");
        const fonts = editor.querySelectorAll('font[size="7"]');
        fonts.forEach((font) => {
          font.removeAttribute("size");
          font.style.fontSize = size + "px";
        });
      }

      sync();
    });

    editor.addEventListener("input", sync);

    const form = document.getElementById("blockForm");
    if (form) {
      form.addEventListener("submit", sync);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();