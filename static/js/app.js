document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-auto-dismiss]').forEach((el) => {
    const delay = Number(el.dataset.autoDismiss || 0);
    if (!delay) return;
    setTimeout(() => {
      el.style.transition = 'opacity .3s ease, transform .3s ease';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      setTimeout(() => el.remove(), 320);
    }, delay);
  });

  document.querySelectorAll('[data-category-select]').forEach((categorySelect) => {
    const form = categorySelect.closest('form');
    if (!form) return;

    const subcategorySelect = form.querySelector('[data-subcategory-select]');
    if (!subcategorySelect) return;

    const selectedSubcategory = subcategorySelect.dataset.selected || subcategorySelect.value || '';
    const subcategoryMap = {
      programming: [
        { value: 'python', label: 'Python' },
        { value: 'java', label: 'Java' },
        { value: 'cpp', label: 'C++' },
        { value: 'go', label: 'Go' },
        { value: 'c', label: 'C' },
        { value: 'c_sharp', label: 'C#' },
        { value: 'java_script', label: 'JavaScript' },
        { value: 'web', label: 'Web-разработка' },
        { value: 'html', label: 'HTML' },
        { value: 'css', label: 'CSS' },
        { value: 'front', label: 'Frontend-разработка' },
      ],
      math: [
        { value: 'lin_algebra', label: 'Линейная алгебра' },
        { value: 'discr_math', label: 'Дискретная математика' },
        { value: 'math_analys', label: 'Математический анализ' },
        { value: 'diff_uravn', label: 'Дифференциальные уравнения' },
        { value: 'chisl_methods', label: 'Численные методы' },
        { value: 'uravn_math_physics', label: 'Уравнения математической физики' },
      ],
      design: [
        { value: 'uiux', label: 'UI/UX' },
        { value: 'graphic', label: 'Графический дизайн' },
      ],
      school_program: [
        { value: 's_math', label: 'Математика' },
        { value: 's_foreign_lang', label: 'Иностранный язык' },
        { value: 's_programming', label: 'Информатика' },
        { value: 's_biology', label: 'Биология' },
        { value: 's_russian', label: 'Русский язык' },
        { value: 's_geography', label: 'География' },
        { value: 's_economy', label: 'Экономика' },
        { value: 's_history', label: 'История' },
        { value: 's_social_science', label: 'Обществознание' },
        { value: 's_physics', label: 'Физика' },
      ],
      foreign_lang: [
        { value: 'english', label: 'Английский язык' },
        { value: 'german', label: 'Немецкий язык' },
        { value: 'french', label: 'Французский язык' },
        { value: 'spanish', label: 'Испанский язык' },
      ],
    };

    const updateSubcategories = () => {
      const selectedCategory = categorySelect.value;
      const options = subcategoryMap[selectedCategory] || [];
      const currentValue = subcategorySelect.value || selectedSubcategory;

      subcategorySelect.innerHTML = '';

      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = selectedCategory ? 'Выберите подкатегорию' : 'Выберите категорию сначала';
      subcategorySelect.appendChild(defaultOption);

      options.forEach((item) => {
        const option = document.createElement('option');
        option.value = item.value;
        option.textContent = item.label;
        if (item.value === currentValue) option.selected = true;
        subcategorySelect.appendChild(option);
      });
    };

    categorySelect.addEventListener('change', updateSubcategories);
    updateSubcategories();
  });

  document.addEventListener('click', (e) => {
    const lessonLink = e.target.closest('.lesson-details-link');
    if (lessonLink) e.stopPropagation();
  });

  document.querySelectorAll('[data-progress-value]').forEach((el) => {
    const value = Number(el.dataset.progressValue || 0);
    el.style.setProperty('--progress-value', `${value}`);
    el.style.width = `${value}%`;
  });

  document.querySelectorAll('[data-avatar-color]').forEach((el) => {
    const color = el.dataset.avatarColor;
    if (!color) return;
    el.style.setProperty('--avatar-color', color);
    el.style.background = color;
  });

  document.querySelectorAll('[data-swatch-color]').forEach((el) => {
    const color = el.dataset.swatchColor;
    if (!color) return;
    el.style.setProperty('--swatch-color', color);
    el.style.background = color;
  });
});

function initRichTextToolbars() {
  document.querySelectorAll('.rt-toolbar').forEach((tb) => {
    if (tb.dataset.initialized) return;
    tb.dataset.initialized = 'true';

    const targetId = tb.getAttribute('data-target');
    const ta = document.getElementById(targetId);
    if (!ta) return;

    function wrapSelection(before, after) {
      ta.focus();
      const start = ta.selectionStart || 0;
      const end = ta.selectionEnd || 0;
      const value = ta.value || '';
      const selected = value.slice(start, end);
      ta.value = value.slice(0, start) + before + selected + after + value.slice(end);
      const cursor = start + before.length + selected.length + after.length;
      ta.setSelectionRange(cursor, cursor);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }

    tb.addEventListener('click', (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;

      e.preventDefault();
      const cmd = btn.dataset.cmd;
      const size = btn.dataset.size;
      const color = btn.dataset.color;

      if (cmd === 'b') wrapSelection('<b>', '</b>');
      if (cmd === 'i') wrapSelection('<i>', '</i>');
      if (cmd === 'u') wrapSelection('<u>', '</u>');
      if (size) wrapSelection(`<span style="font-size:${size}px;">`, '</span>');
      if (color) wrapSelection(`<span style="color:${color};">`, '</span>');
    });
  });
}

document.addEventListener('DOMContentLoaded', initRichTextToolbars);
