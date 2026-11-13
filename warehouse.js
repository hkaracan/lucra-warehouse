const search = document.querySelector('#block-search');
const results = document.querySelector('#results');
const moreResults = document.querySelector('#more-results');
const status = document.querySelector('#status');
const empty = document.querySelector('#empty');
const plan = document.querySelector('#plan');
const cards = new Map();
const occupiedPositions = new Set(bundles.map(bundle => bundle.position));
const updated = document.querySelector('#last-updated');
const refreshedAt = new Date(bundleDataUpdatedAt);
const staleWarning = document.querySelector('#stale-warning');
const staleAfterMs = 2 * 60 * 60 * 1000;
updated.dateTime = bundleDataUpdatedAt;
updated.textContent = new Intl.DateTimeFormat('tr-TR', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Istanbul',
}).format(refreshedAt);

function updateFreshness() {
  staleWarning.hidden = Date.now() - refreshedAt.getTime() < staleAfterMs;
}

updateFreshness();
setInterval(updateFreshness, 60 * 1000);

function isInView(node) {
  const bounds = node.getBoundingClientRect();
  return bounds.top >= document.querySelector('.site-header').getBoundingClientRect().bottom
    && bounds.bottom <= window.innerHeight;
}

function element(tag, className, text = '') {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

for (let lane = 1; lane <= 4; lane++) {
  const label = element('div', 'lane');
  label.append(element('span', '', 'Koridor'), document.createTextNode(String(lane)));
  plan.append(label);
  if (lane === 4) break;

  const row = 'ABC'[lane - 1];
  const storage = element('div', 'storage');
  storage.setAttribute('aria-label', row);
  storage.append(element('div', 'storage-heading', row));
  for (let number = 1; number <= 13; number++) {
    if (row === 'A' && (number === 13 || (number === 12 && !occupiedPositions.has('A12')))) {
      storage.append(element('div', number === 13 ? 'selection' : '', number === 13 ? 'Seleksiyon Alanı' : ''));
      continue;
    }
    const position = row + number;
    const card = element('button', 'position', position);
    card.type = 'button';
    card.id = `konum-${position}`;
    card.addEventListener('click', () => {
      search.value = position;
      clearPositionLink();
      render();
    });
    storage.append(card);
    cards.set(position, card);
  }
  plan.append(storage);
}

function makeResult({ code, position, count }, label) {
  const item = element('li', 'result');
  const link = element('a', '');
  link.append(element('strong', '', label), element('span', 'result-count', ` ×${count}`));
  link.setAttribute('aria-label', `${code}, ${position}, ${count} bundle`);
  link.href = `#konum-${position}`;
  link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    if (isInView(cards.get(position))) event.preventDefault();
  });
  item.append(link);
  return item;
}

function render() {
  const query = search.value.toUpperCase().replace(/\s+/g, '');
  const position = cards.has(query) ? query : null;
  const exact = bundles.some(bundle => bundle.code === query);
  const found = query ? bundles.filter(bundle => position
    ? bundle.position === position
    : exact ? bundle.code === query : bundle.code.includes(query)) : [];
  const tooBroad = !position && !exact && found.length > 4;
  const matches = tooBroad ? [] : found;
  const positions = new Set(position ? [position] : matches.map(bundle => bundle.position));
  for (const [position, card] of cards) card.classList.toggle('is-match', positions.has(position));
  const rows = matches.map(bundle => makeResult(bundle, position
    ? bundle.code
    : exact ? bundle.position : `${bundle.code} · ${bundle.position}`));
  const extraRows = rows.length > 4 ? rows.splice(3) : [];
  if (extraRows.length) {
    const more = element('a', '', `+${extraRows.length} sonuç`);
    more.href = '#more-results';
    const item = element('li', 'result');
    item.append(more);
    rows.push(item);
  }
  results.replaceChildren(...rows);
  moreResults.replaceChildren(...extraRows);
  moreResults.hidden = extraRows.length === 0;
  empty.hidden = !query || matches.length > 0;
  empty.textContent = tooBroad
    ? `${found.length} eşleşme var. Blok kodunu biraz daha yazın.`
    : position
    ? 'Bu konumda kayıtlı bundle yok.'
    : 'Eşleşen blok veya konum bulunamadı.';
  status.textContent = !query ? '' : matches.length ? `${matches.length} sonuç bulundu.` : empty.textContent;
}

function clearPositionLink() {
  if (location.hash.startsWith('#konum-')) history.replaceState(null, '', location.href.split('#')[0]);
}

search.addEventListener('input', () => {
  clearPositionLink();
  render();
});
const linkedPosition = location.hash.replace(/^#konum-/, '');
if (cards.has(linkedPosition)) search.value = linkedPosition;
render();
