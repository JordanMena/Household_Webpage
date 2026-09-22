document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('recipe-form');
  const available = document.getElementById('available-tags');
  const associated = document.getElementById('associated-tags');
  const hiddenTags = document.getElementById('tags');
  const status = document.getElementById('import-status');
  const panel = document.getElementById('import-panel');
  const manualButton = document.getElementById('manual-mode');
  const importButton = document.getElementById('import-mode');
  const sort = container => Array.from(container.children)
    .sort((a, b) => a.dataset.tagName.localeCompare(b.dataset.tagName))
    .forEach(tag => container.appendChild(tag));
  const sync = () => {
    hiddenTags.value = Array.from(associated.children).map(tag => tag.dataset.tagName).join('|');
    sort(available); sort(associated);
    document.querySelectorAll('.tag-item').forEach(tag => {
      tag.setAttribute('role', 'button');
      tag.tabIndex = 0;
      tag.setAttribute('aria-pressed', String(tag.parentElement === associated));
    });
  };
  function selectTag(name) {
    name = name.trim().toLowerCase();
    let tag = Array.from(document.querySelectorAll('.tag-item')).find(el => el.dataset.tagName.toLowerCase() === name);
    if (!tag) {
      tag = document.createElement('span');
      tag.className = 'badge badge-primary m-1 tag-item';
      tag.style.cursor = 'pointer';
      tag.dataset.tagName = name;
      tag.textContent = name;
    }
    associated.appendChild(tag);
  }
  hiddenTags.value.split('|').filter(Boolean).forEach(selectTag);
  sync();
  function toggleTag(event) {
    if (!event.target.classList.contains('tag-item')) return;
    if (event.type === 'keydown' && !['Enter', ' '].includes(event.key)) return;
    event.preventDefault();
    const tag = event.target;
    (tag.parentElement === available ? associated : available).appendChild(tag);
    sync();
  }
  [available, associated].forEach(container => {
    container.addEventListener('click', toggleTag);
    container.addEventListener('keydown', toggleTag);
  });
  function addTag() {
    const input = document.getElementById('new-tag');
    const name = input.value.trim();
    const error = document.getElementById('tag-status');
    if (!name || name.length > 20 || name.includes('|')) {
      error.textContent = 'Enter a tag name of 1–20 characters, without |.';
      return;
    }
    selectTag(name); sync(); input.value = ''; error.textContent = '';
  }
  document.getElementById('add-tag').addEventListener('click', addTag);
  document.getElementById('new-tag').addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); addTag(); }
  });
  function showImport(show) {
    panel.hidden = !show;
    importButton.setAttribute('aria-expanded', String(show));
    manualButton.setAttribute('aria-pressed', String(!show));
    document.getElementById(show ? 'recipe-json' : 'name').focus();
  }
  manualButton.addEventListener('click', () => showImport(false));
  importButton.addEventListener('click', () => showImport(true));
  document.getElementById('copy-prompt').addEventListener('click', async () => {
    const prompt = document.getElementById('llm-prompt');
    try {
      await navigator.clipboard.writeText(prompt.value);
      status.textContent = 'Instructions copied. Add your recipe URL or text at the end.';
    } catch (_) {
      prompt.closest('details').open = true;
      prompt.focus(); prompt.select();
      status.textContent = 'Instructions selected. Press Ctrl+C (or Command+C) to copy.';
    }
  });
  function previewSteps() {
    const list = document.getElementById('steps-list');
    list.replaceChildren();
    document.getElementById('directions').value.split(/\n\s*\n/).filter(step => step.trim()).forEach(step => {
      const li = document.createElement('li');
      li.textContent = step.trim(); li.className = 'mb-2'; li.style.whiteSpace = 'pre-wrap';
      list.appendChild(li);
    });
  }
  document.getElementById('directions').addEventListener('input', previewSteps);
  previewSteps();
  document.getElementById('load-import').addEventListener('click', async event => {
    const button = event.currentTarget;
    button.disabled = true;
    status.textContent = 'Checking recipe…';
    const body = new FormData();
    body.set('recipe_json', document.getElementById('recipe-json').value);
    body.set('csrf_token', form.querySelector('[name=csrf_token]')?.value || '');
    body.set('recipe_id', form.dataset.recipeId);
    try {
      const response = await fetch(form.dataset.importUrl, { method: 'POST', body });
      const result = await response.json();
      if (!response.ok) {
        status.textContent = Object.entries(result.errors || {}).map(([key, errors]) => `${key}: ${errors.join(' ')}`).join('\n') || 'Could not load this recipe.';
        status.style.whiteSpace = 'pre-line';
        return;
      }
      Object.entries(result.values).forEach(([key, value]) => {
        if (key !== 'tags') document.getElementById(key).value = value;
      });
      Array.from(associated.children).forEach(tag => available.appendChild(tag));
      result.values.tags.forEach(selectTag); sync(); previewSteps();
      const duplicates = document.getElementById('import-duplicates');
      duplicates.replaceChildren();
      duplicates.hidden = !result.duplicates.length;
      if (result.duplicates.length) {
        duplicates.appendChild(document.createTextNode('This source URL is already saved: '));
        result.duplicates.forEach(item => {
          const link = document.createElement('a');
          link.href = item.url; link.textContent = item.name; link.target = '_blank'; link.rel = 'noopener';
          duplicates.appendChild(link); duplicates.appendChild(document.createTextNode(' '));
        });
      }
      status.textContent = 'Recipe loaded. Review the fields below, then choose Save recipe. Nothing has been saved yet.';
      document.getElementById('name').focus();
    } catch (_) {
      status.textContent = 'Could not load the recipe. Your pasted JSON is still here; please try again.';
    } finally { button.disabled = false; }
  });
});
