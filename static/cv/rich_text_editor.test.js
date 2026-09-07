// Contract-level browser checks for the resume editor behavior.
// The application test suite covers widget wiring; this file documents the
// client-side contract for manual/browser smoke testing.
(() => {
  const requiredCommands = ['bold', 'italic', 'insertUnorderedList', 'insertOrderedList', 'indent', 'outdent', 'createLink', 'removeFormat'];
  window.__nptorRichTextContract = { requiredCommands, selector: 'textarea[data-rich-text="true"]' };
})();
