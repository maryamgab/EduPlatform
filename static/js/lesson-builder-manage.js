(function () {
  function initEditors() {
    try { document.execCommand("styleWithCSS", false, true); } catch (e) {}

    function sync(editor, hidden) {
      hidden.value = editor.innerHTML;
      hidden.dispatchEvent(new Event("input", { bubbles: true }));
      hidden.dispatchEvent(new Event("change", { bubbles: true }));
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

    function setActive(toolbar, attr, value) {
      toolbar.querySelectorAll("button[" + attr + "]").forEach(btn => {
        btn.classList.toggle("rt-active", btn.getAttribute(attr) === value);
      });
    }

    function updateCmdButtons(toolbar) {
      toolbar.querySelectorAll("button[data-cmd]").forEach(btn => {
        const cmd = btn.getAttribute("data-cmd");
        let active = false;
        try { active = document.queryCommandState(cmd); } catch (e) {}
        btn.classList.toggle("rt-active", active);
      });
    }

    function getCaretStyle(editor) {
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

    function updateToolbarFromCaret(toolbar, editor) {
      updateCmdButtons(toolbar);
      const st = getCaretStyle(editor);
      setActive(toolbar, "data-color", st.color);
      setActive(toolbar, "data-size", st.size);
    }

    function bind(toolbar, editor, hidden) {
      if (!toolbar || !editor || !hidden) return;

      if ((!editor.innerHTML || !editor.innerHTML.trim()) && hidden.value) {
        editor.innerHTML = hidden.value;
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
        sync(editor, hidden);
        saveSelection();
        updateToolbarFromCaret(toolbar, editor);
      });

      ["keyup", "mouseup", "focus", "click"].forEach(evt => {
        editor.addEventListener(evt, () => {
          saveSelection();
          updateToolbarFromCaret(toolbar, editor);
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
          sync(editor, hidden);
          saveSelection();
          updateToolbarFromCaret(toolbar, editor);
          return;
        }

        if (color) {
          restoreSelection();
          document.execCommand("foreColor", false, color);
          sync(editor, hidden);
          saveSelection();
          updateToolbarFromCaret(toolbar, editor);
          return;
        }

        if (size) {
          applyFontPx(size);
          sync(editor, hidden);
          updateToolbarFromCaret(toolbar, editor);
          return;
        }
      });

      const form = toolbar.closest("form");
      if (form) form.addEventListener("submit", () => sync(editor, hidden));

      saveSelection();
      updateToolbarFromCaret(toolbar, editor);
    }

    document.querySelectorAll(".rt-toolbar-add").forEach(tb => {
      const id = tb.getAttribute("data-hidden-id");
      const hidden = id ? document.getElementById(id) : null;
      const editor = document.querySelector('.rt-editor-add[data-hidden-id="' + id + '"]');
      bind(tb, editor, hidden);
    });

    document.querySelectorAll(".inline-rt-form").forEach(form => {
      bind(
        form.querySelector(".rt-toolbar"),
        form.querySelector(".rt-editor"),
        form.querySelector(".rt-hidden")
      );
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEditors);
  } else {
    initEditors();
  }

function toggleBlockSections(root) {
  const form = root || document;
  const typeSelect = form.querySelector('select[name="type"], select[id$="-type"]');
  const textSection = form.querySelector('.js-text-section');
  const mediaSections = form.querySelectorAll('.js-media-section');

  if (!typeSelect) return;

  function apply() {
    const isText = typeSelect.value === 'text';

    if (textSection) {
      textSection.classList.toggle('is-hidden', !isText);
    }

    mediaSections.forEach((section) => {
      section.classList.toggle('is-hidden', isText);
    });
  }

    typeSelect.addEventListener('change', apply);
    apply();
  }

  document.addEventListener('DOMContentLoaded', function () {
    const addForm = document.getElementById('addBlockForm');
    if (addForm) toggleBlockSections(addForm);
  });


})();