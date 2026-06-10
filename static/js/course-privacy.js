document.addEventListener('DOMContentLoaded', () => {
  const privateCheckbox = document.getElementById('id_is_private');
  const privatePanel = document.querySelector('[data-private-course-panel]');
  const accessCodeInput = document.querySelector('[data-access-code-input]');
  const generateButton = document.querySelector('[data-generate-access-code]');

  const syncPrivatePanel = () => {
    if (!privatePanel || !privateCheckbox) return;
    privatePanel.hidden = !privateCheckbox.checked;
    privatePanel.classList.toggle('privacy-card--hidden', !privateCheckbox.checked);
  };

  const generateCode = () => {
    if (!accessCodeInput) return;
    const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let result = '';
    for (let i = 0; i < 8; i += 1) {
      result += alphabet[Math.floor(Math.random() * alphabet.length)];
    }
    accessCodeInput.value = result;
    accessCodeInput.dispatchEvent(new Event('input', { bubbles: true }));
  };

  if (privateCheckbox) {
    privateCheckbox.addEventListener('change', syncPrivatePanel);
    syncPrivatePanel();
  }

  if (generateButton) {
    generateButton.addEventListener('click', generateCode);
  }
});
