(function () {
  function initEditors(scope = document) {
    try {
      document.execCommand("styleWithCSS", false, true);
    } catch (e) {}

    const COLOR_MAP = {
      "#000000": ["#000000", "rgb(0,0,0)", "rgb(0, 0, 0)", "black"],
      "#1d4ed8": ["#1d4ed8", "rgb(29,78,216)", "rgb(29, 78, 216)"],
      "#15803d": ["#15803d", "rgb(21,128,61)", "rgb(21, 128, 61)"],
      "#b91c1c": ["#b91c1c", "rgb(185,28,28)", "rgb(185, 28, 28)"]
    };

    function normalizeColor(color) {
      if (!color) return "";
      const c = color.toLowerCase().replace(/\s+/g, "");
      for (const [hex, variants] of Object.entries(COLOR_MAP)) {
        if (variants.map(v => v.toLowerCase().replace(/\s+/g, "")).includes(c)) {
          return hex;
        }
      }
      return c;
    }

    function setActive(btn, active) {
      btn.classList.toggle("rt-active", !!active);
    }

    function findStyleState(node, editor) {
      let el = node && node.nodeType === 3 ? node.parentElement : node;
      let foundColor = "";
      let foundSize = "";

      while (el && el !== editor) {
        if (el.nodeType === 1) {
          if (!foundColor && el.getAttribute && el.getAttribute("color")) {
            foundColor = normalizeColor(el.getAttribute("color"));
          }

          if (!foundColor && el.style && el.style.color) {
            foundColor = normalizeColor(el.style.color);
          }

          if (!foundSize && el.style && el.style.fontSize) {
            foundSize = el.style.fontSize;
          }

          const tag = el.tagName ? el.tagName.toLowerCase() : "";
          if (tag === "font" && !foundColor) {
            const fontColor = el.getAttribute("color");
            if (fontColor) foundColor = normalizeColor(fontColor);
          }
        }
        el = el.parentElement;
      }

      if ((!foundColor || !foundSize) && node) {
        const baseEl = node.nodeType === 3 ? node.parentElement : node;
        if (baseEl && baseEl.nodeType === 1) {
          const computed = window.getComputedStyle(baseEl);
          if (!foundColor) foundColor = normalizeColor(computed.color || "");
          if (!foundSize) foundSize = computed.fontSize || "";
        }
      }

      return {
        color: foundColor,
        fontSize: foundSize
      };
    }

    function bind(toolbar, editor, hidden) {
      if (!toolbar || !editor || !hidden) return;
      if (toolbar.dataset.bound === "1") return;
      toolbar.dataset.bound = "1";

      let savedRange = null;

      function sync() {
        hidden.value = editor.innerHTML;
        hidden.dispatchEvent(new Event("input", { bubbles: true }));
        hidden.dispatchEvent(new Event("change", { bubbles: true }));
      }

      function saveSelection() {
        const sel = window.getSelection();
        if (!sel || sel.rangeCount === 0) return;

        const range = sel.getRangeAt(0);
        if (!editor.contains(range.startContainer) || !editor.contains(range.endContainer)) return;

        savedRange = range.cloneRange();
      }

      function restoreSelection() {
        const sel = window.getSelection();
        if (!sel) return false;

        editor.focus();

        if (savedRange) {
          sel.removeAllRanges();
          sel.addRange(savedRange);
          return true;
        }
        return false;
      }

      function updateToolbar() {
        const sel = window.getSelection();

        if (!sel || sel.rangeCount === 0 || !editor.contains(sel.anchorNode)) {
          toolbar.querySelectorAll("[data-cmd],[data-size],[data-color]").forEach((btn) => {
            btn.classList.remove("rt-active");
          });
          return;
        }

        const styleState = findStyleState(sel.anchorNode, editor);

        toolbar.querySelectorAll("[data-cmd]").forEach((btn) => {
          const cmd = btn.getAttribute("data-cmd");
          let active = false;

          try {
            active = document.queryCommandState(cmd);
          } catch (e) {
            active = false;
          }

          setActive(btn, active);
        });

        toolbar.querySelectorAll("[data-size]").forEach((btn) => {
          const size = btn.getAttribute("data-size");
          setActive(btn, styleState.fontSize === size + "px");
        });

        toolbar.querySelectorAll("[data-color]").forEach((btn) => {
          const btnColor = normalizeColor(btn.getAttribute("data-color"));
          setActive(btn, styleState.color === btnColor);
        });
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

          const after = document.createRange();
          after.setStartAfter(span);
          after.collapse(true);

          sel.removeAllRanges();
          sel.addRange(after);
          savedRange = after.cloneRange();
        } else {
          const span = document.createElement("span");
          span.style.fontSize = px + "px";
          span.appendChild(document.createTextNode("\u200B"));
          range.insertNode(span);

          const inside = document.createRange();
          inside.setStart(span.firstChild, 1);
          inside.collapse(true);

          sel.removeAllRanges();
          sel.addRange(inside);
          savedRange = inside.cloneRange();
        }

        sync();
        updateToolbar();
      }

      function applyColor(color) {
        restoreSelection();
        document.execCommand("foreColor", false, color);
        saveSelection();
        sync();
        updateToolbar();
      }

      function applyCommand(cmd) {
        restoreSelection();
        document.execCommand(cmd, false, null);
        saveSelection();
        sync();
        updateToolbar();
      }

      editor.addEventListener("input", function () {
        sync();
        saveSelection();
        updateToolbar();
      });

      ["keyup", "mouseup", "focus", "click", "blur"].forEach((evt) => {
        editor.addEventListener(evt, function () {
          saveSelection();
          updateToolbar();
        });
      });

      toolbar.addEventListener("mousedown", function (e) {
        e.preventDefault();
      });

      toolbar.addEventListener("click", function (e) {
        const btn = e.target.closest("button");
        if (!btn) return;

        e.preventDefault();

        const cmd = btn.getAttribute("data-cmd");
        const size = btn.getAttribute("data-size");
        const color = btn.getAttribute("data-color");

        if (cmd) {
          applyCommand(cmd);
          return;
        }

        if (color) {
          applyColor(color);
          return;
        }

        if (size) {
          applyFontPx(size);
          return;
        }
      });

      const form = hidden.closest("form");
      if (form) {
        form.addEventListener("submit", function () {
          sync();
        });
      }

      sync();
      updateToolbar();
    }

    scope.querySelectorAll(".rt-toolbar-add[data-hidden-id]").forEach((tb) => {
      const id = tb.getAttribute("data-hidden-id");
      const hidden = document.getElementById(id);
      const editor =
        scope.querySelector('.rt-editor-add[data-hidden-id="' + id + '"]') ||
        document.querySelector('.rt-editor-add[data-hidden-id="' + id + '"]');

      bind(tb, editor, hidden);
    });
  }

  function initDeleteButtons(scope = document) {
    scope.querySelectorAll(".btn-delete-block").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";

      btn.addEventListener("click", function () {
        const block = btn.closest(".lesson-block-item");
        if (!block) return;

        const deleteInput = block.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (deleteInput) {
          deleteInput.checked = true;
        }

        block.classList.add("is-deleted");
        updateOrders();
      });
    });
  }

  function updateOrders() {
    let visibleIndex = 1;
    document.querySelectorAll("#lesson-blocks .lesson-block-item").forEach((block) => {
      if (block.classList.contains("is-deleted")) return;
      const orderInput = block.querySelector('input[name$="-order"]');
      if (orderInput) {
        orderInput.value = visibleIndex++;
      }
    });
  }

  function toggleBlockSections(container) {
    const typeSelect = container.querySelector('select[name$="-type"]');
    const textSection = container.querySelector(".js-text-section");
    const mediaSections = container.querySelectorAll(".js-media-section");

    if (!typeSelect) return;

    function apply() {
      const isText = typeSelect.value === "text";

      if (textSection) {
        textSection.classList.toggle("is-hidden", !isText);
      }

      mediaSections.forEach((section) => {
        section.classList.toggle("is-hidden", isText);
      });
    }

    typeSelect.addEventListener("change", apply);
    apply();
  }

  function getTotalFormsInput() {
    return document.querySelector('input[name$="-TOTAL_FORMS"]');
  }

  function addBlock() {
    const container = document.getElementById("lesson-blocks");
    const template = document.getElementById("empty-block-template");
    const totalForms = getTotalFormsInput();

    if (!container || !template || !totalForms) return;

    const index = Number(totalForms.value);
    const html = template.innerHTML.replace(/__prefix__/g, index);

    const wrap = document.createElement("div");
    wrap.innerHTML = html.trim();

    const block = wrap.firstElementChild;
    if (!block) return;

    container.appendChild(block);
    totalForms.value = String(index + 1);

    const orderInput = block.querySelector('input[name$="-order"]');
    if (orderInput) {
      orderInput.value = index + 1;
    }

    initEditors(block);
    initDeleteButtons(block);
    toggleBlockSections(block);
    updateOrders();
  }

  function initAddButton() {
    const btn = document.getElementById("add-block-btn");
    if (!btn || btn.dataset.bound === "1") return;

    btn.dataset.bound = "1";
    btn.addEventListener("click", addBlock);
  }

  function boot() {
    initEditors(document);
    initDeleteButtons(document);
    initAddButton();
    document.querySelectorAll(".lesson-block-item").forEach(toggleBlockSections);
    updateOrders();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();