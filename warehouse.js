const search = document.querySelector('#block-search');
const results = document.querySelector('#results');
const lookup = document.querySelector('.lookup');
const status = document.querySelector('#status');
const empty = document.querySelector('#empty');
const plan = document.querySelector('#plan');
const cards = new Map();
const occupancy = new Map();
for (const { position, count } of bundles) {
  occupancy.set(position, (occupancy.get(position) ?? 0) + count);
}
const updated = document.querySelector('#last-updated');
updated.dateTime = bundleDataUpdatedAt;
updated.textContent = new Intl.DateTimeFormat('tr-TR', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Istanbul',
}).format(new Date(bundleDataUpdatedAt));

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
    if (row === 'A' && (number === 13 || (number === 12 && !occupancy.has('A12')))) {
      storage.append(element('div', number === 13 ? 'selection' : '', number === 13 ? 'Seleksiyon Alanı' : ''));
      continue;
    }
    const position = row + number;
    const card = element('button', 'position', position);
    card.type = 'button';
    card.id = `konum-${position}`;
    const count = occupancy.get(position) ?? 0;
    card.setAttribute('aria-label', `${position}, ${count} bundle`);
    card.addEventListener('click', () => {
      search.value = position;
      clearPositionLink();
      render();
      lookup.scrollIntoView({ block: 'start' });
    });
    const slots = element('div', 'slots');
    slots.setAttribute('aria-hidden', 'true');
    for (let slot = 0; slot < count; slot++) slots.append(element('span', 'bundle-slot'));
    card.append(slots);
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
  results.replaceChildren(...matches.map(bundle => makeResult(bundle, position
    ? bundle.code
    : exact ? bundle.position : `${bundle.code} · ${bundle.position}`)));
  lookup.hidden = !query;
  empty.hidden = matches.length > 0;
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
