(function () {
  function getCsrfToken(form) {
    return form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";
  }

  function updateButton(form, shortlisted) {
    const button = form.querySelector("button");
    if (!button) return;
    button.classList.toggle("is-shortlisted", shortlisted);
    button.setAttribute("aria-pressed", shortlisted ? "true" : "false");
    button.setAttribute("title", shortlisted ? "Remove from shortlist" : "Add to shortlist");
    const icon = button.querySelector("span[aria-hidden='true']");
    const sr = button.querySelector(".sr-only");
    if (icon) icon.textContent = shortlisted ? "★" : "☆";
    if (sr) sr.textContent = shortlisted ? "Remove from shortlist" : "Add to shortlist";
  }

  function removeDashboardCard(form) {
    const card = form.closest("[data-shortlist-card]");
    if (!card) return;
    card.remove();
    const section = document.querySelector(".dashboard-shortlist-section");
    if (section && !section.querySelector("[data-shortlist-card]")) section.remove();
  }

  document.addEventListener("submit", function (event) {
    const form = event.target.closest("[data-shortlist-form]");
    if (!form) return;

    event.preventDefault();
    const button = form.querySelector("button");
    if (button) button.disabled = true;

    fetch(form.action, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(form),
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
      },
      credentials: "same-origin"
    })
      .then(function (response) {
        if (!response.ok) throw new Error("Shortlist update failed");
        return response.json();
      })
      .then(function (data) {
        const isDashboard = form.closest(".dashboard-shortlist-section");
        if (isDashboard && !data.shortlisted) {
          removeDashboardCard(form);
          return;
        }
        updateButton(form, Boolean(data.shortlisted));
      })
      .catch(function () {
        form.submit();
      })
      .finally(function () {
        if (button) button.disabled = false;
      });
  });
})();
