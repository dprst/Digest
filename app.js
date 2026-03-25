const state = { lang: 'uk', issues: [], activeIssue: null, deferredInstallPrompt: null };

const dom = {
  dateLine: document.getElementById('dateLine'),
  langSelect: document.getElementById('langSelect'),
  installBtn: document.getElementById('installBtn'),
  globalFilter: document.getElementById('globalFilter'),
  ukraineFilter: document.getElementById('ukraineFilter'),
  globalList: document.getElementById('globalList'),
  ukraineList: document.getElementById('ukraineList'),
  archiveList: document.getElementById('archiveList'),
  archiveSearch: document.getElementById('archiveSearch'),
  tabToday: document.getElementById('tabToday'),
  tabArchive: document.getElementById('tabArchive'),
  tabMethod: document.getElementById('tabMethod'),
  executiveTitle: document.getElementById('executiveTitle'),
  signalsTitle: document.getElementById('signalsTitle'),
  globalTitle: document.getElementById('globalTitle'),
  globalTitleInner: document.getElementById('globalTitleInner'),
  ukraineTitle: document.getElementById('ukraineTitle'),
  ukraineTitleInner: document.getElementById('ukraineTitleInner'),
  proTitle: document.getElementById('proTitle'),
  metricsTitle: document.getElementById('metricsTitle'),
  researchTitle: document.getElementById('researchTitle'),
  sourceTitle: document.getElementById('sourceTitle'),
  archiveTitle: document.getElementById('archiveTitle'),
  methodTitle: document.getElementById('methodTitle'),
  tocTitle: document.getElementById('tocTitle'),
  tocNav: document.getElementById('tocNav'),
  hero: document.getElementById('hero'),
  executiveList: document.getElementById('executiveList'),
  signals: document.getElementById('signals'),
  proLead: document.getElementById('proLead'),
  proList: document.getElementById('proList'),
  metricsList: document.getElementById('metricsList'),
  researchList: document.getElementById('researchList'),
  sourceCloud: document.getElementById('sourceCloud'),
  methodList: document.getElementById('methodList')
};

const t = {
  uk: {
    today: 'Сьогодні',
    archive: 'Архів',
    method: 'Методологія',
    topSignals: '3 ключові сигнали',
    executive: 'Executive summary (1 хв)',
    global: '🌍 World Digest',
    ukraine: '🇺🇦 Україна',
    pro: '📣 Communications Strategy',
    research: '📚 Рекомендовано',
    metrics: '📊 Метрики',
    sourceTitle: 'Джерела',
    methodTitle: 'Методологія',
    toc: 'Навігація',
    all: 'Усі теми',
    why: 'Чому важливо',
    implication: 'Імплікації',
    sources: 'Першоджерела',
    open: 'Відкрити',
    updated: 'Оновлено',
    datePrefix: 'Випуск',
    details: 'Детальніше',
    loadError: 'Не вдалося завантажити випуск.',
    methodBullets: [
      'Кожна новина має гіперпосилання на першоджерело.',
      'Випуск ділиться на: World, Ukraine, Communications Strategy, Metrics, Research.',
      'Контент подається як short summary + deeper context у розгортанні.',
      'Список джерел дублюється окремим блоком внизу випуску.'
    ]
  },
  en: {
    today: 'Today',
    archive: 'Archive',
    method: 'Method',
    topSignals: 'Top 3 signals',
    executive: 'Executive summary (1 min)',
    global: '🌍 World Digest',
    ukraine: '🇺🇦 Ukraine',
    pro: '📣 Communications Strategy',
    research: '📚 Recommended',
    metrics: '📊 Metrics',
    sourceTitle: 'Sources',
    methodTitle: 'Methodology',
    toc: 'Jump to',
    all: 'All categories',
    why: 'Why it matters',
    implication: 'Comms implication',
    sources: 'Primary sources',
    open: 'Open',
    updated: 'Updated',
    datePrefix: 'Issue',
    details: 'Read more',
    loadError: 'Failed to load issue.',
    methodBullets: [
      'Every story includes direct hyperlinks to primary sources.',
      'Each issue is split into: World, Ukraine, Communications Strategy, Metrics, Research.',
      'Content uses short summaries with expandable deeper context.',
      'All sources are also listed in a dedicated source section.'
    ]
  }
};

const text = (k) => t[state.lang][k];
const safe = (v, fallback = '') => (v ?? fallback);

function setActiveView(view) {
  document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.view === view));
  document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === `view${view[0].toUpperCase()}${view.slice(1)}`));
}

function renderLabels() {
  dom.tabToday.textContent = text('today');
  dom.tabArchive.textContent = text('archive');
  dom.tabMethod.textContent = text('method');
  dom.executiveTitle.textContent = text('executive');
  dom.signalsTitle.textContent = text('topSignals');
  dom.globalTitle.textContent = text('global');
  dom.globalTitleInner.textContent = text('global');
  dom.ukraineTitle.textContent = text('ukraine');
  dom.ukraineTitleInner.textContent = text('ukraine');
  dom.proTitle.textContent = text('pro');
  dom.metricsTitle.textContent = text('metrics');
  dom.researchTitle.textContent = text('research');
  dom.sourceTitle.textContent = text('sourceTitle');
  dom.archiveTitle.textContent = text('archive');
  dom.methodTitle.textContent = text('methodTitle');
  dom.tocTitle.textContent = text('toc');
  dom.archiveSearch.placeholder = state.lang === 'uk' ? 'Пошук в архіві' : 'Search archive';
}

function fillFilter(select, items) {
  const prev = select.value || 'all';
  const categories = [...new Set(items.map((s) => s.category))];
  select.innerHTML = `<option value="all">${text('all')}</option>${categories.map((c) => `<option value="${c}">${c}</option>`).join('')}`;
  if ([...select.options].some((o) => o.value === prev)) select.value = prev;
}

const links = (sources = []) => sources.map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>`).join('');

function storyCard(story) {
  return `<article class="story">
    <h3>${safe(story.headline?.[state.lang], safe(story.headline?.uk, ''))} <span class="tag ${story.importance || 'watch'}">${story.importance || 'watch'}</span></h3>
    <div class="meta">${story.category || ''} • ${story.score || '-'} /100 • ${story.published_at || ''}</div>
    <p>${safe(story.summary?.[state.lang], '')}</p>
    <details>
      <summary>${text('details')}</summary>
      <p><span class="label">${text('why')}:</span> ${safe(story.why_it_matters?.[state.lang], '')}</p>
      <p><span class="label">${text('implication')}:</span> ${safe(story.comms_implication?.[state.lang], '')}</p>
    </details>
    <div class="sources"><span class="label">${text('sources')}:</span> ${links(story.sources)}</div>
  </article>`;
}

function renderStories(bucket, filterEl, listEl) {
  const items = safe(state.activeIssue?.briefs?.[bucket], []);
  fillFilter(filterEl, items);
  const filtered = filterEl.value === 'all' ? items : items.filter((i) => i.category === filterEl.value);
  listEl.innerHTML = filtered.map(storyCard).join('');
}

function renderIssue() {
  const issue = state.activeIssue;
  if (!issue) return;

  renderLabels();

  dom.dateLine.textContent = `${text('datePrefix')}: ${issue.meta.date} • ${text('updated')}: ${issue.meta.updated_at} (${issue.meta.timezone})`;
  dom.hero.innerHTML = `<h2>${safe(issue.header?.[state.lang], issue.meta.date)}</h2><p>${safe(issue.editorial_intro?.[state.lang], '')}</p>`;

  const execItems = safe(issue.executive_summary?.[state.lang], safe(issue.top_signals, []).map((s) => s[state.lang]));
  dom.executiveList.innerHTML = execItems.map((i) => `<li>${i}</li>`).join('');

  dom.signals.innerHTML = safe(issue.top_signals, []).map((s) => `<article class="signal ${s.importance || 'watch'}"><strong>${safe(s[state.lang], '')}</strong><div>${s.score || '-'} /100</div></article>`).join('');

  renderStories('global', dom.globalFilter, dom.globalList);
  renderStories('ukraine', dom.ukraineFilter, dom.ukraineList);

  dom.proLead.textContent = safe(issue.pro_block?.lead?.[state.lang], '');
  dom.proList.innerHTML = safe(issue.pro_block?.items, []).map((p) => `<article class="pro-item">
    <h3>${safe(p.title?.[state.lang], '')}</h3>
    <p>${safe(p.insight?.[state.lang], '')}</p>
    <p><span class="label">${text('implication')}:</span> ${safe(p.application?.[state.lang], '')}</p>
    <div class="sources"><span class="label">${text('sources')}:</span> ${links(p.sources)}</div>
  </article>`).join('');

  dom.metricsList.innerHTML = safe(issue.comms_metrics, []).map((m) => `<article class="metric-item">
    <h3>${safe(m.title?.[state.lang], '')}</h3>
    <p>${safe(m.description?.[state.lang], '')}</p>
    <p><span class="label">Formula:</span> <code>${safe(m.formula, '')}</code></p>
    <ul>${safe(m.tools, []).map((tool) => `<li><a href="${tool.url}" target="_blank" rel="noopener">${tool.name}</a></li>`).join('')}</ul>
  </article>`).join('');

  dom.researchList.innerHTML = safe(issue.research_radar, []).map((r) => `<article class="research-item">
    <h3>${r.title}</h3>
    <p>${safe(r.why_read?.[state.lang], '')}</p>
    <div class="sources"><a href="${r.url}" target="_blank" rel="noopener">${text('open')}</a></div>
  </article>`).join('');

  const allSources = [];
  const add = (arr) => safe(arr, []).forEach((item) => safe(item.sources, []).forEach((s) => allSources.push(s)));
  add(issue.briefs?.global);
  add(issue.briefs?.ukraine);
  add(issue.pro_block?.items);
  safe(issue.research_radar, []).forEach((r) => allSources.push({ name: r.title, url: r.url }));
  const uniq = [...new Map(allSources.map((s) => [s.url, s])).values()];
  dom.sourceCloud.innerHTML = uniq.map((s) => `<a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>`).join('');

  const toc = [
    ['#executive', text('executive')],
    ['#signalsSection', text('topSignals')],
    ['#globalSection', text('global')],
    ['#ukraineSection', text('ukraine')],
    ['#proSection', text('pro')],
    ['#metricsSection', text('metrics')],
    ['#researchSection', text('research')],
    ['#sourceSection', text('sourceTitle')]
  ];
  dom.tocNav.innerHTML = toc.map(([href, label]) => `<a href="${href}">${label}</a>`).join('');

  dom.methodList.innerHTML = text('methodBullets').map((b) => `<li>${b}</li>`).join('');

  renderArchive();
}

function renderArchive() {
  const q = dom.archiveSearch.value.trim().toLowerCase();
  const filtered = state.issues.filter((i) => `${i.meta.date} ${safe(i.editorial_intro?.uk, '')} ${safe(i.editorial_intro?.en, '')}`.toLowerCase().includes(q));
  dom.archiveList.innerHTML = filtered.map((i) => `<li>
    <div><strong>${i.meta.date}</strong><br><small>${safe(i.editorial_intro?.[state.lang], '').slice(0, 110)}…</small></div>
    <button class="open-issue" data-date="${i.meta.date}">${text('open')}</button>
  </li>`).join('');
}

async function loadIssues() {
  try {
    const idx = await fetch('data/issues/index.json').then((r) => r.json());
    const issues = await Promise.all(idx.issues.map((p) => fetch(p).then((r) => r.json())));
    issues.sort((a, b) => b.meta.date.localeCompare(a.meta.date));
    state.issues = issues;
    state.activeIssue = issues[0];
    renderIssue();
  } catch (e) {
    dom.hero.innerHTML = `<h2>${text('loadError')}</h2><p>${String(e.message || e)}</p>`;
  }
}

function setupEvents() {
  document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => setActiveView(tab.dataset.view)));

  dom.langSelect.addEventListener('change', (e) => {
    state.lang = e.target.value;
    localStorage.setItem('dn-lang', state.lang);
    renderIssue();
  });

  dom.globalFilter.addEventListener('change', () => renderStories('global', dom.globalFilter, dom.globalList));
  dom.ukraineFilter.addEventListener('change', () => renderStories('ukraine', dom.ukraineFilter, dom.ukraineList));
  dom.archiveSearch.addEventListener('input', renderArchive);

  dom.archiveList.addEventListener('click', (e) => {
    const b = e.target.closest('.open-issue');
    if (!b) return;
    state.activeIssue = state.issues.find((i) => i.meta.date === b.dataset.date);
    renderIssue();
    setActiveView('today');
  });

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.deferredInstallPrompt = e;
    dom.installBtn.hidden = false;
  });

  dom.installBtn.addEventListener('click', async () => {
    if (!state.deferredInstallPrompt) return;
    state.deferredInstallPrompt.prompt();
    await state.deferredInstallPrompt.userChoice;
    state.deferredInstallPrompt = null;
    dom.installBtn.hidden = true;
  });
}

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');

state.lang = localStorage.getItem('dn-lang') || 'uk';
dom.langSelect.value = state.lang;
setupEvents();
loadIssues();
