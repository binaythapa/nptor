(() => {
  const escapeHtml = (value) => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const sanitize = (html) => {
    const template = document.createElement('template');
    template.innerHTML = html;
    const allowed = new Set(['P', 'BR', 'STRONG', 'B', 'EM', 'I', 'UL', 'OL', 'LI', 'A']);
    template.content.querySelectorAll('*').forEach((node) => {
      if (!allowed.has(node.tagName)) {
        node.replaceWith(...node.childNodes);
        return;
      }
      [...node.attributes].forEach((attr) => {
        if (node.tagName === 'A' && attr.name === 'href') {
          if (!/^https?:\/\//i.test(attr.value)) node.removeAttribute(attr.name);
        } else {
          node.removeAttribute(attr.name);
        }
      });
      if (node.tagName === 'A') {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
    });
    return template.innerHTML;
  };

  const textToHtml = (value) => {
    if (!value.trim()) return '<p><br></p>';
    return value.split(/\r?\n/).map((line) => `<p>${escapeHtml(line) || '<br>'}</p>`).join('');
  };

  const sync = (editor, input) => { input.value = sanitize(editor.innerHTML); };

  const exec = (editor, input, command, value = null) => {
    editor.focus();
    document.execCommand(command, false, value);
    sync(editor, input);
    editor.dispatchEvent(new Event('input', { bubbles: true }));
  };

  const refreshState = (editor, toolbar) => {
    toolbar.querySelectorAll('[data-command]').forEach((button) => {
      const command = button.dataset.command;
      if (['bold', 'italic', 'insertUnorderedList', 'insertOrderedList'].includes(command)) {
        button.classList.toggle('is-active', document.queryCommandState(command));
      }
    });
  };

  const init = (input) => {
    if (input.dataset.richTextReady === 'true') return;
    input.dataset.richTextReady = 'true';
    const wrapper = document.createElement('div');
    wrapper.className = 'cv-rich-text';
    wrapper.innerHTML = `
      <div class="cv-rich-text__toolbar" role="toolbar" aria-label="Resume formatting">
        <button type="button" class="cv-rich-text__button" data-command="bold" aria-label="Bold"><strong>B</strong></button>
        <button type="button" class="cv-rich-text__button" data-command="italic" aria-label="Italic"><em>I</em></button>
        <span class="cv-rich-text__divider" aria-hidden="true"></span>
        <button type="button" class="cv-rich-text__button" data-command="insertUnorderedList" aria-label="Bulleted list">• List</button>
        <button type="button" class="cv-rich-text__button" data-command="insertOrderedList" aria-label="Numbered list">1. List</button>
        <button type="button" class="cv-rich-text__button" data-command="outdent" aria-label="Decrease indent">←</button>
        <button type="button" class="cv-rich-text__button" data-command="indent" aria-label="Increase indent">→</button>
        <span class="cv-rich-text__divider" aria-hidden="true"></span>
        <button type="button" class="cv-rich-text__button" data-command="createLink" aria-label="Insert link">Link</button>
        <button type="button" class="cv-rich-text__button" data-command="removeFormat" aria-label="Clear formatting">Tx</button>
      </div>
      <div class="cv-rich-text__editor" contenteditable="true" role="textbox" aria-multiline="true"></div>
      <div class="cv-rich-text__hint">Use bullets for achievements and responsibilities. Enter creates a new paragraph.</div>`;
    input.parentNode.insertBefore(wrapper, input);
    const editor = wrapper.querySelector('.cv-rich-text__editor');
    const toolbar = wrapper.querySelector('.cv-rich-text__toolbar');
    editor.innerHTML = input.value.trim() ? sanitize(input.value) : '<p><br></p>';

    toolbar.addEventListener('mousedown', (event) => event.preventDefault());
    toolbar.addEventListener('click', (event) => {
      const button = event.target.closest('[data-command]');
      if (!button) return;
      const command = button.dataset.command;
      if (command === 'createLink') {
        const url = window.prompt('Enter a URL (https://...)');
        if (url && /^https?:\/\//i.test(url)) exec(editor, input, command, url);
        return;
      }
      exec(editor, input, command);
      refreshState(editor, toolbar);
    });
    editor.addEventListener('input', () => sync(editor, input));
    editor.addEventListener('keyup', () => refreshState(editor, toolbar));
    editor.addEventListener('mouseup', () => refreshState(editor, toolbar));
    editor.addEventListener('paste', (event) => {
      event.preventDefault();
      const text = event.clipboardData.getData('text/plain');
      document.execCommand('insertHTML', false, textToHtml(text));
      sync(editor, input);
    });
    input.form?.addEventListener('submit', () => sync(editor, input));
  };

  const boot = () => document.querySelectorAll('textarea[data-rich-text="true"]').forEach(init);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
