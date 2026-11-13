const search = document.querySelector('#block-search');
const results = document.querySelector('#results');
const lookup = document.querySelector('.lookup');
const resultTitle = document.querySelector('#result-title');
const status = document.querySelector('#status');
const empty = document.querySelector('#empty');
const plan = document.querySelector('#plan');
const cards = new Map();
const occupiedPositions = new Set(bundles.map(bundle => bundle.position));
const updated = document.querySelector('#last-updated');
const refreshedAt = new Date(bundleDataUpdatedAt);
const staleWarning = document.querySelector('#stale-warning');
const freshLabel = document.querySelector('#fresh-label');
const staleAfterMs = 2 * 60 * 60 * 1000;
updated.dateTime = bundleDataUpdatedAt;
updated.textContent = new Intl.DateTimeFormat('tr-TR', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Istanbul',
}).format(refreshedAt);

function updateFreshness() {
  const stale = Date.now() - refreshedAt.getTime() >= staleAfterMs;
  staleWarning.hidden = !stale;
  freshLabel.hidden = stale;
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
    const card = element('button', 'position');
    card.type = 'button';
    card.id = `konum-${position}`;
    const count = element('span', 'position-count');
    count.setAttribute('aria-hidden', 'true');
    count.hidden = true;
    card.append(element('span', '', position), count);
    card.addEventListener('click', () => {
      search.value = position;
      clearPositionLink();
      search.blur();
      render();
    });
    storage.append(card);
    cards.set(position, { card, count });
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
    if (isInView(cards.get(position).card)) event.preventDefault();
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
  const counts = new Map();
  for (const bundle of matches) {
    counts.set(bundle.position, (counts.get(bundle.position) ?? 0) + bundle.count);
  }
  for (const [tile, { card, count }] of cards) {
    const quantity = counts.get(tile);
    const highlighted = tile === position || quantity !== undefined;
    card.classList.toggle('is-match', highlighted);
    card.setAttribute('aria-label', quantity === undefined ? tile : `${tile}, ${quantity} bundle`);
    count.hidden = quantity === undefined;
    count.textContent = quantity === undefined ? '' : `×${quantity}`;
  }
  // Exact block searches read directly from the tiles. Keep details for a position
  // lookup and partial searches where different block codes can share a tile.
  lookup.hidden = !query || (!position && exact);
  resultTitle.textContent = position ?? '';
  resultTitle.hidden = !position;
  results.replaceChildren(...(lookup.hidden ? [] : matches.map(bundle => makeResult(bundle, position
    ? bundle.code
    : `${bundle.code} · ${bundle.position}`))));
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
search.form.addEventListener('submit', event => {
  event.preventDefault();
  search.blur();
});
const linkedPosition = location.hash.replace(/^#konum-/, '');
if (cards.has(linkedPosition)) search.value = linkedPosition;
render();
