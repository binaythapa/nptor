(function () {
  const root = document.querySelector('[data-builder-workspace="true"]');
  if (!root) return;

  const form = document.getElementById('cv-builder-form');
  const state = document.getElementById('builder-save-state');
  const preview = document.getElementById('cv-preview-frame');
  const csrf = form.querySelector('[name="csrfmiddlewaretoken"]').value;
  const cvId = root.dataset.cvId;
  const fields = form.elements;
  let saveTimer = null;
  let activeBulletTarget = null;

  function setState(label, tone) {
    state.textContent = label;
    state.className = 'tag ' + (tone || 'is-light');
  }

  function selectedSections() {
    const result = {};
    document.querySelectorAll('[data-section-input]').forEach(function (input) {
      if (!result[input.dataset.sectionInput]) result[input.dataset.sectionInput] = [];
      if (input.checked) result[input.dataset.sectionInput].push(Number(input.value));
    });
    Object.keys(result).forEach(function (section) {
      const list = document.querySelector('[data-record-list="' + section + '"]');
      if (!list) return;
      const ordered = [];
      list.querySelectorAll('[data-record-id]').forEach(function (record) {
        const checkbox = record.querySelector('[data-section-input="' + section + '"]');
        if (checkbox && checkbox.checked) ordered.push(Number(record.dataset.recordId));
      });
      if (ordered.length) result[section] = ordered;
    });
    return result;
  }

  function cvSkills() {
    return (document.getElementById('cv-skills-input').value || '')
      .split(',')
      .map(function (item) { return item.trim(); })
      .filter(Boolean);
  }

  function builderState() {
    const targetJob = {
      title: document.getElementById('target-job-title').value.trim(),
      company: document.getElementById('target-job-company').value.trim(),
      description: document.getElementById('target-job-description').value.trim()
    };
    const experienceBullets = {};
    document.querySelectorAll('[data-experience-bullet]').forEach(function (textarea) {
      experienceBullets[textarea.dataset.experienceBullet] = textarea.value;
    });
    return {
      title: fields.title.value.trim(),
      status: fields.status.value,
      template_id: fields.template.value,
      professional_title: fields.professional_title.value,
      summary: fields.summary.value,
      linkedin_url: fields.linkedin_url.value,
      portfolio_url: fields.portfolio_url.value,
      target_job: targetJob,
      experience_bullets: experienceBullets,
      cv_skills: cvSkills(),
      selected_sections: selectedSections()
    };
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    });
    let data = {};
    try { data = await response.json(); } catch (error) {}
    if (!response.ok || data.ok === false) throw new Error(data.error || 'Request failed.');
    return data;
  }

  async function saveNow(showPreview) {
    setState('Saving…', 'is-warning');
    try {
      await postJson('/cv/' + cvId + '/builder/autosave/', builderState());
      setState('Saved', 'is-success is-light');
      if (showPreview && preview) preview.contentWindow.location.reload();
      return true;
    } catch (error) {
      setState('Save error', 'is-danger is-light');
      window.console.error(error);
      return false;
    }
  }

  function scheduleSave() {
    setState('Unsaved', 'is-warning is-light');
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(function () { saveNow(true); }, 700);
  }

  function renderSuggestion(container, value, apply) {
    container.classList.remove('is-hidden');
    container.innerHTML = '';
    const label = document.createElement('p');
    label.className = 'has-text-weight-semibold mb-2';
    label.textContent = 'AI suggestion';
    const content = document.createElement('div');
    content.className = 'suggestion-value';
    content.textContent = value;
    const actions = document.createElement('div');
    actions.className = 'ai-suggestion-actions';
    const use = document.createElement('button');
    use.type = 'button'; use.className = 'button is-small is-primary'; use.textContent = 'Apply';
    use.addEventListener('click', function () { apply(); container.classList.add('is-hidden'); scheduleSave(); });
    const dismiss = document.createElement('button');
    dismiss.type = 'button'; dismiss.className = 'button is-small'; dismiss.textContent = 'Dismiss';
    dismiss.addEventListener('click', function () { container.classList.add('is-hidden'); });
    actions.appendChild(use); actions.appendChild(dismiss);
    container.appendChild(label); container.appendChild(content); container.appendChild(actions);
  }

  async function runAI(button) {
    const action = button.dataset.aiAction;
    const ok = await saveNow(false);
    if (!ok) return;
    button.classList.add('is-loading');
    try {
      const payload = { action: action };
      if (action === 'bullet') {
        activeBulletTarget = button.dataset.bulletTarget;
        const textarea = document.querySelector('[data-experience-bullet="' + activeBulletTarget + '"]');
        payload.text = textarea ? textarea.value : '';
        payload.section = 'experience';
      }
      const data = await postJson('/cv/' + cvId + '/builder/ai/', payload);
      const suggestion = data.suggestion || {};
      if (action === 'summary') {
        renderSuggestion(document.getElementById('summary-suggestion'), suggestion.summary || '', function () {
          fields.summary.value = suggestion.summary || '';
        });
      } else if (action === 'bullet') {
        renderSuggestion(document.getElementById('bullet-suggestion'), suggestion.bullet || '', function () {
          const textarea = document.querySelector('[data-experience-bullet="' + activeBulletTarget + '"]');
          if (textarea) textarea.value = suggestion.bullet || '';
        });
      } else if (action === 'skills') {
        const container = document.getElementById('skills-suggestion');
        container.classList.remove('is-hidden');
        container.innerHTML = '<p class="has-text-weight-semibold mb-2">AI skill suggestions</p>';
        const list = document.createElement('div');
        (suggestion.skills || []).forEach(function (skill, index) {
          const label = document.createElement('label');
          label.className = 'checkbox mr-4 mb-2 is-inline-block';
          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox'; checkbox.dataset.aiSkill = String(index); checkbox.checked = true;
          label.appendChild(checkbox); label.appendChild(document.createTextNode(' ' + skill));
          label.dataset.skill = skill;
          list.appendChild(label);
        });
        const actions = document.createElement('div'); actions.className = 'ai-suggestion-actions';
        const use = document.createElement('button'); use.type = 'button'; use.className = 'button is-small is-primary'; use.textContent = 'Add selected skills';
        use.addEventListener('click', function () {
          const selected = Array.from(list.querySelectorAll('input:checked')).map(function (input) { return input.closest('label').dataset.skill; });
          const current = cvSkills();
          const currentKeys = current.map(function (x) { return x.toLowerCase(); });
          const merged = current.concat(selected.filter(function (skill) { return currentKeys.indexOf(skill.toLowerCase()) === -1; }));
          document.getElementById('cv-skills-input').value = merged.join(', ');
          container.classList.add('is-hidden');
          scheduleSave();
        });
        const dismiss = document.createElement('button'); dismiss.type = 'button'; dismiss.className = 'button is-small'; dismiss.textContent = 'Dismiss';
        dismiss.addEventListener('click', function () { container.classList.add('is-hidden'); });
        actions.appendChild(use); actions.appendChild(dismiss);
        container.appendChild(list); container.appendChild(actions);
      }
    } catch (error) {
      window.alert(error.message);
    } finally {
      button.classList.remove('is-loading');
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>\'"]/g, function (char) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]);
    });
  }

  document.querySelectorAll('input, textarea, select').forEach(function (input) {
    if (input.closest('.cv-builder-page')) {
      input.addEventListener('input', scheduleSave);
      input.addEventListener('change', scheduleSave);
    }
  });

  document.querySelectorAll('.section-toggle').forEach(function (button) {
    button.addEventListener('click', function () {
      const section = button.dataset.section;
      const inputs = document.querySelectorAll('[data-section-input="' + section + '"]');
      const shouldCheck = Array.from(inputs).some(function (input) { return !input.checked; });
      inputs.forEach(function (input) { input.checked = shouldCheck; });
      scheduleSave();
    });
  });

  document.querySelectorAll('.builder-record-list').forEach(function (list) {
    let dragged = null;
    list.querySelectorAll('[draggable="true"]').forEach(function (record) {
      record.addEventListener('dragstart', function () { dragged = record; record.style.opacity = '0.5'; });
      record.addEventListener('dragend', function () { record.style.opacity = ''; dragged = null; scheduleSave(); });
      record.addEventListener('dragover', function (event) {
        event.preventDefault();
        if (!dragged || dragged === record) return;
        const rect = record.getBoundingClientRect();
        list.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? record : record.nextSibling);
      });
    });
  });

  document.querySelectorAll('.cv-nav-item').forEach(function (button) {
    button.addEventListener('click', function () {
      const target = document.getElementById(button.dataset.scrollTarget);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.querySelectorAll('.cv-nav-item').forEach(function (item) { item.classList.remove('is-active'); });
      button.classList.add('is-active');
    });
  });

  document.querySelectorAll('.ai-action').forEach(function (button) {
    button.addEventListener('click', function () { runAI(button); });
  });

  document.getElementById('check-ats').addEventListener('click', async function () {
    const button = this;
    const result = document.getElementById('ats-result');
    const ok = await saveNow(false);
    if (!ok) return;
    button.classList.add('is-loading');
    try {
      const data = await postJson('/cv/' + cvId + '/builder/ats/', { job_description: document.getElementById('target-job-description').value });
      const analysis = data.analysis || {};
      const resultData = analysis.result || {};
      result.classList.remove('is-hidden');
      result.innerHTML = '<div class="ats-score">' + Number(analysis.score || 0) + '<span class="is-size-7 has-text-grey"> / 100</span></div>' +
        '<p class="mt-2">' + escapeHtml(resultData.summary || 'ATS analysis complete.') + '</p>' +
        '<p class="has-text-weight-semibold mt-3">Missing keywords</p>' +
        '<div class="ats-keywords">' + (resultData.missing_keywords || []).map(function (item) { return '<span class="tag is-warning is-light">' + escapeHtml(item) + '</span>'; }).join('') + '</div>' +
        '<p class="has-text-weight-semibold mt-3">Recommendations</p><ul>' + (resultData.recommendations || []).map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>';
      if (preview) preview.contentWindow.location.reload();
    } catch (error) {
      result.classList.remove('is-hidden');
      result.innerHTML = '<p class="has-text-danger">' + escapeHtml(error.message) + '</p>';
    } finally {
      button.classList.remove('is-loading');
    }
  });

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    window.clearTimeout(saveTimer);
    saveNow(true);
  });

  const overridesNode = document.getElementById('cv-builder-overrides');
  if (overridesNode) {
    try {
      const overrides = JSON.parse(overridesNode.textContent || '{}');
      const bullets = overrides.experience_bullets || {};
      Object.keys(bullets).forEach(function (id) {
        const textarea = document.querySelector('[data-experience-bullet="' + id + '"]');
        if (textarea) textarea.value = bullets[id];
      });
      if (Array.isArray(overrides.cv_skills)) document.getElementById('cv-skills-input').value = overrides.cv_skills.join(', ');
    } catch (error) { window.console.error(error); }
  }
})();
