const RADAR = [
  ["punctuation_per_300_words", "Densité de ponctuations"], ["punctuation_diversity", "Diversité de ponctuation"],
  ["structural_diversity", "Diversité des structures"], ["structural_rhythm", "Rythme des structures"],
  ["average_syntactic_depth", "Complexité syntaxique"], ["sentence_start_diversity", "Régularité des débuts de phrase"], ["burstiness", "Uniformité locale de longueur de phrase"],
  ["noun_verb_ratio", "Ratio noms/verbes"], ["filtered_repetition_rate", "Répétitions lexicales"],
];
const DETAILS = [
  ["stylistic_repetition_rate", "Diversité stylistique", true], ["family_repetition_rate", "Répétitions familiales", true], ["phonetic_repetition_rate", "Répétitions sonores", true], ["absolute_repetition_rate", "Répétitions non filtrées", true],
  ["trigram_repetition", "Répétition globale des trigrammes", true], ["moving_trigram_repetition", "Répétition locale des trigrammes", true], ["function_word_ratio", "Mots-outils", true], ["noun_ratio", "Noms", true], ["verb_ratio", "Verbes", true], ["adjective_ratio", "Adjectifs", true], ["adverb_ratio", "Adverbes", true], ["sentence_word_std_dev", "Diversité de longueurs de phrase (mots)", false], ["gzip_compression_ratio", "Compression gzip", true], ["relative_clause_ratio", "Relatives et subordonnées", true], ["nominal_sentence_ratio", "Phrases nominales", true], ["active_voice_ratio", "Voix active", true], ["metaphorical_comme_ratio", "Comparaisons métaphoriques", true], ["form_lemma_ratio", "Formes par lemme", false], ["hapax_ratio", "Mots employés une seule fois", true],
  ["word_count", "Mots", false], ["sentence_count", "Phrases", false], ["paragraph_count", "Paragraphes", false], ["avg_word_length", "Longueur moyenne des mots (caractères)", false], ["avg_sentence_length", "Longueur moyenne des phrases (caractères)", false], ["avg_sentence_word_count", "Longueur moyenne des phrases (mots)", false], ["median_sentence_length", "Longueur médiane des phrases (caractères)", false], ["sentence_length_p10", "Longueur P10 des phrases (caractères)", false], ["sentence_length_p90", "Longueur P90 des phrases (caractères)", false], ["paragraph_length_std_dev", "Écart-type des paragraphes (mots)", false], ["document_char_count", "Signes (caractères)", false],
];
const ALL_METRICS = [...RADAR, ...DETAILS.map(([key, label]) => [key, label])];
const TECHNICAL_KEYS = new Set(["word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "document_char_count"]);
// L’écart-type brut reste disponible dans les données, mais la mesure #6
// affichée et indexée est bien la diversité locale (burstiness).
const REMOVED_KEYS = new Set(["avg_sentence_word_count"]);
const MENU_METRICS = ALL_METRICS.filter(([key], index, all) => !TECHNICAL_KEYS.has(key) && !REMOVED_KEYS.has(key) && all.findIndex(item => item[0] === key) === index);
let COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"];
let IA_COLOR = "#777777";
let data, chart, surfaceChart, evolutionCharts = [], corpusProfile = false, authorProfile = false, authorLimits = false, currentRadarTitle = "Radar";
const flippedAxes = new Set();
// L'interface ne stocke jamais de noms de champs statistiques : elle utilise
// uniquement les identifiants publics des notes (mesure_1, mesure_2, ...).
function publicMetricId(key) { return data?.metric_note_ids?.[key] || key; }
function metricKey(ref) {
  if (!data?.metric_note_ids || !String(ref).startsWith("mesure_")) return ref;
  return Object.entries(data.metric_note_ids).find(([, id]) => id === ref)?.[0] || ref;
}
function noteEntry(key) {
  const publicId = data?.metric_note_ids?.[key];
  const id = publicId == null ? null : data?.note_ids?.[publicId];
  const title = id == null ? `Mesure ${publicId || "non référencée"}` : (data?.note_titles?.[String(id)] || `Mesure ${id}`);
  const aliases = title.replace(/\*\*/g, "").split("/").map(alias => alias.trim());
  const bold = title.match(/\*\*([^*]+)\*\*/)?.[1]?.trim();
  return { id, title, aliases, preferred: bold || aliases[0] };
}
function metricLabel(key) { const entry = noteEntry(key); if (!flippedAxes.has(key)) return entry.preferred; const alternate = entry.aliases.find(alias => alias !== entry.preferred); return alternate || entry.preferred; }
function metricNote(key) {
  const entry = noteEntry(key);
  return entry.id == null ? "Note non référencée." : (data?.notes?.[String(entry.id)] || "Note non référencée.");
}
function renderNote(id) {
  const title = data.note_titles?.[String(id)] || "Note";
  const raw = data.notes?.[String(id)] || "";
  const escape = text => text.replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
  let body = escape(raw).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  body = body.replace(/\n\n/g, "</p><p>").replace(/\n/g, "<br>");
  return `<h2>${escape(title.replace(/\*\*/g, ""))}</h2><p>${body}</p>`;
}
function pastel(hex, alpha = "35") { return /^#[0-9a-f]{6}$/i.test(hex) ? `${hex}${alpha}` : hex; }
// Valeurs de référence du corpus complet. Elles sont construites une seule fois
// au chargement et ne dépendent jamais des cases actuellement cochées.
let corpusValues = new Map();
const value = (book, key) => {
  const stats = book.analyses[0]?.stats || {};
  const read = field => stats[publicMetricId(field)] ?? stats[field];
  if (key === "stylistic_repetition_rate") return 1 - Number(read(key) || 0);
  if (key === "relative_clause_ratio") return Number(read("relative_clause_ratio") || 0) + Number(read("subordinate_clause_ratio") || 0);
  if (key === "noun_verb_ratio" && read(key) == null) return Number(read("verb_ratio")) ? Number(read("noun_ratio") || 0) / Number(read("verb_ratio")) : 0;
  return read(key) == null ? null : Number(read(key));
};
function selected() { return [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle):checked")].map(x => data.books.find(b => b.id === Number(x.value))).filter(Boolean); }
function checkedMetrics() { return [...new Set([...document.querySelectorAll("#metrics input:checked")].map(x => metricKey(x.value)))]; }
function radarTitle(books) {
  const authors = [...new Set(books.map(book => (book.author || "Auteur inconnu").trim()).filter(Boolean))];
  if (authors.length === 1) return authors[0];
  return `Comparatif de ${books.length} œuvres de ${authors.length} auteurs`;
}
function singleAuthor(books) {
  const authors = [...new Set(books.map(book => (book.author || "").trim()).filter(Boolean))];
  return authors.length === 1 ? authors[0] : "";
}
function isAI(entry) { return String(entry?.author || entry || "").trim().toLocaleLowerCase() === "ia"; }
function authorCompare(left, right) {
  const a = String(left?.author || left || "").trim();
  const b = String(right?.author || right || "").trim();
  if (a.toLocaleLowerCase() === "ia") return b.toLocaleLowerCase() === "ia" ? 0 : -1;
  if (b.toLocaleLowerCase() === "ia") return 1;
  return a.localeCompare(b, "fr", { sensitivity: "base" });
}
const INVERSE = new Set(["noun_verb_ratio", "filtered_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate", "trigram_repetition", "moving_trigram_repetition", "adjective_ratio", "adverb_ratio", "relative_clause_ratio", "nominal_sentence_ratio", "metaphorical_comme_ratio", "sentence_start_diversity", "burstiness"]);
const DISPLAY_INVERTED = new Set(["sentence_start_diversity", "burstiness"]);
function scale(key, n) {
  if (n == null) return null;
  // Important : la référence est l'ensemble des livres exportés, pas la
  // sélection affichée. Ainsi retirer un auteur ne change pas les limites.
  const values = corpusValues.get(key) || [];
  if (values.length < 2) return 50;
  const minimum = Math.min(...values), maximum = Math.max(...values);
  if (!Number.isFinite(minimum) || maximum === minimum) return 50;
  let relative = Math.max(0, Math.min(1, (n - minimum) / (maximum - minimum)));
  const entry = noteEntry(key);
  const preferredIsSecond = ["mesure_1", "mesure_41"].includes(publicMetricId(key))
    ? false
    : entry.aliases.indexOf(entry.preferred) === 1;
  if (preferredIsSecond !== flippedAxes.has(key)) relative = 1 - relative;
  // Courbe logarithmique continue : elle étale les valeurs basses puis ralentit
  // progressivement vers le bord, sans seuil ni saturation artificielle.
  return Math.max(0, Math.min(100, Math.log1p(4 * relative) / Math.log1p(4) * 100));
}
function draw() {
  const books = selected(), keys = checkedMetrics(), labels = keys.map(metricLabel);
  const title = radarTitle(books);
  currentRadarTitle = title;
  chart?.destroy();
  const multipleAuthors = new Set(books.map(book => book.author).filter(Boolean)).size > 1;
  const authorName = author => (author || "Auteur inconnu").trim().split(/\s+/).at(-1);
  const radarBooks = [...books].sort((a, b) => authorCompare(a, b) || a.title.localeCompare(b.title, "fr", { sensitivity: "base" }));
  const datasets = corpusProfile ? profileDatasets(keys, authorLimits && !allAuthorWorksSelected(books) ? authorAverages(books) : books) : authorProfile ? authorDatasets(keys, books) : radarBooks.map((b, i) => { const color = isAI(b) ? IA_COLOR : COLORS[i % COLORS.length]; return ({ label: multipleAuthors ? `${b.title} · ${authorName(b.author)}` : b.title, isAI: isAI(b), data: keys.map(k => { const n = scale(k, value(b, k)); return n == null ? null : Math.max(10, n); }), borderColor: color, backgroundColor: pastel(color), fill: true, pointRadius: 0 }); });
  chart = new Chart(document.getElementById("radar"), { type: "radar", data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "nearest", intersect: false }, scales: { r: { min: 0, max: 100, ticks: { display: false, stepSize: 25 }, pointLabels: { font: context => ({ size: Math.max(11, Math.min(15, context.chart.width / 65)), weight: "600" }) }, grid: { display: true, color: "#ccd1d5" }, angleLines: { display: true, color: "#d9dddf" } } }, plugins: { title: { display: true, text: title, font: { size: 18, weight: "600" }, padding: { bottom: 8 } }, legend: { display: false }, tooltip: { callbacks: { label: () => "", title: items => items[0]?.dataset?.label || "" } } } } });
  document.getElementById("radar-legend").innerHTML = datasets.map(dataset => `<span><i style="background:${dataset.borderColor}"></i>${dataset.isAI ? `<strong>${dataset.label}</strong>` : dataset.label}</span>`).join("");
  document.querySelectorAll("#radar-legend span").forEach((item, index) => item.addEventListener("click", () => {
    const selectedDataset = datasets[index];
    chart.data.datasets.forEach(dataset => { dataset.borderWidth = 1.5; dataset.order = 0; dataset.backgroundColor = pastel(dataset.borderColor); });
    selectedDataset.borderWidth = 4;
    selectedDataset.order = -100;
    selectedDataset.backgroundColor = selectedDataset.borderColor;
    chart.data.datasets = [...chart.data.datasets.filter(dataset => dataset !== selectedDataset), selectedDataset];
    chart.update();
  }));
  drawSurfaces(books);
  drawEvolution(books);
  renderTables(books);
  // Le menu reste visuellement une icône ; aucune option n'est présélectionnée,
  // ce qui permet de télécharger deux fois de suite le même format.
  document.querySelectorAll(".chart-download").forEach(select => { select.selectedIndex = -1; });
}
function profileDatasets(keys, books) {
  const rows = ["Minimum", "Médiane", "Maximum"];
  const colors = ["#3478b8", "#d13c36", "#e19a2d"];
  return rows.map((label, index) => ({ label, data: keys.map(key => {
    const values = books.map(book => scale(key, value(book, key))).filter(Number.isFinite).sort((a, b) => a - b);
    if (!values.length) return 50;
    const result = index === 0 ? values[0] : index === 2 ? values.at(-1) : values[Math.floor((values.length - 1) / 2)];
    return Number.isFinite(result) ? Math.max(10, result) : 50;
  }), borderColor: colors[index], backgroundColor: pastel(colors[index]), fill: true, pointRadius: 0 }));
}
function allAuthorWorksSelected(books) {
  const selectedCounts = books.reduce((counts, book) => { const author = book.author || "Auteur inconnu"; counts[author] = (counts[author] || 0) + 1; return counts; }, {});
  const corpusCounts = data.books.reduce((counts, book) => { const author = book.author || "Auteur inconnu"; counts[author] = (counts[author] || 0) + 1; return counts; }, {});
  return Object.entries(selectedCounts).every(([author, count]) => count === corpusCounts[author]);
}
function authorDatasets(keys, books) {
  return authorAverages(books).map((book, i) => { const color = isAI(book) ? IA_COLOR : COLORS[i % COLORS.length]; return ({ label: book.author.trim().split(/\s+/).at(-1), isAI: isAI(book), data: keys.map(key => { const n = scale(key, value(book, key)); return n == null ? null : Math.max(10, n); }), borderColor: color, backgroundColor: pastel(color), fill: true, pointRadius: 0 }); });
}
function authorAverages(books) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([author, authorBooks]) => { const stats = {}; for (const [key] of ALL_METRICS) { const values = authorBooks.map(book => value(book, key)).filter(Number.isFinite); if (values.length) stats[key] = values.reduce((sum, n) => sum + n, 0) / values.length; } return { author, analyses: [{ stats }] }; });
}
function authorSurfaceProfiles(books, keys) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([author, authorBooks]) => ({
    label: author,
    author,
    hover: authorBooks.length === 1 ? authorBooks[0].title : author,
    values: keys.map(key => {
      const values = authorBooks.map(book => value(book, key));
      if (!values.every(Number.isFinite)) throw new Error(`Base statistique incohérente pour ${author}`);
      return scale(key, values.reduce((sum, current) => sum + current, 0) / values.length);
    }),
  }));
}
function drawSurfaces(books) {
  surfaceChart?.destroy();
  const keys = checkedMetrics();
  const profiles = (authorProfile || authorLimits) ? authorSurfaceProfiles(books, keys) : books.map(book => ({ label: book.title, author: book.author || "Auteur inconnu", values: keys.map(key => scale(key, value(book, key))) }));
  const labels = profiles.map(profile => profile.label);
  const surfaceBox = document.querySelector(".surface-box");
  if (surfaceBox) surfaceBox.style.height = `${Math.max(300, profiles.length * 30 + 90)}px`;
  const areas = profiles.map(profile => { const values = profile.values, n = values.length; return n < 3 ? 0 : Math.abs(values.reduce((sum, v, i) => sum + v * values[(i + 1) % n] * Math.sin(2 * Math.PI / n), 0) / 2); });
  const maximumArea = Math.max(...areas, 0);
  const sorted = labels.map((label, i) => ({ label, author: profiles[i].author || profiles[i].hover || "Auteur inconnu", hover: profiles[i].hover || profiles[i].author || "Auteur inconnu", area: maximumArea ? areas[i] / maximumArea * 100 : 0, color: isAI(profiles[i]) ? IA_COLOR : COLORS[i % COLORS.length] })).sort((a, b) => a.area - b.area);
  const surfaceTitle = document.querySelector(".surface-box h2");
  if (surfaceTitle) surfaceTitle.childNodes[0].textContent = `Couverture stylistique${singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""} `;
  surfaceChart = new Chart(document.getElementById("surfaces"), { type: "bar", data: { labels: sorted.map(x => x.label), datasets: [{ label: "Couverture stylistique", data: sorted.map(x => x.area), backgroundColor: sorted.map(x => `${x.color}b8`), borderColor: sorted.map(x => x.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => sorted[items[0]?.dataIndex]?.hover || "", label: () => "" } } }, scales: { x: { display: false, beginAtZero: true }, y: { grid: { display: false }, ticks: { font: context => ({ weight: isAI(sorted[context.index]?.author) ? "700" : "400" }) } } } } });
}
function drawEvolution(selectedBooks) {
  evolutionCharts.forEach(item => item.destroy());
  evolutionCharts = [];
  const books = [...selectedBooks].filter(book => book.publication_date && !Number.isNaN(Date.parse(book.publication_date))).sort((a, b) => Date.parse(a.publication_date) - Date.parse(b.publication_date));
  const definitions = checkedMetrics().map(key => [key, metricLabel(key)]).filter(Boolean);
  const container = document.getElementById("evolution-charts");
  container.innerHTML = "";
  definitions.forEach(([key, label], i) => {
    const id = `evolution-${i}`;
    const evolutionTitle = `${label}${singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""}`;
    container.insertAdjacentHTML("beforeend", `<div class="evolution-chart chart-frame"><h3>${evolutionTitle}</h3><canvas id="${id}"></canvas><select class="chart-download" data-canvas="${id}" aria-label="Télécharger ${evolutionTitle}"><option value="png">PNG</option><option value="svg">SVG</option></select></div>`);
    const lineColor = books.every(isAI) ? IA_COLOR : COLORS[i % COLORS.length];
    const lineChart = new Chart(document.getElementById(id), { type: "line", data: { labels: books.map(book => book.title), datasets: [{ label, data: books.map(book => { const n = value(book, key); return n == null ? null : scale(key, n); }), borderColor: lineColor, backgroundColor: lineColor, tension: .25, pointRadius: 3, spanGaps: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { display: false }, grid: { color: "#ccd1d5" } }, x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => `${books[items[0].dataIndex].publication_date.slice(0, 4)} · ${books[items[0].dataIndex].title}` } } } } });
    lineChart.$years = books.map(book => book.publication_date.slice(0, 4));
    evolutionCharts.push(lineChart);
  });
}
Chart.register({ id: "publicationYears", afterDatasetsDraw(instance) { const meta = instance.getDatasetMeta(0); const years = instance.$years || []; const ctx = instance.ctx; const limit = instance.chartArea.top + instance.chartArea.height * .75; ctx.save(); ctx.font = "11px system-ui"; ctx.fillStyle = "#6f6962"; ctx.textAlign = "center"; meta.data.forEach((point, i) => { if (years[i]) ctx.fillText(years[i], point.x, point.y < limit ? point.y + 15 : point.y - 9); }); ctx.restore(); } });
function downloadCanvas(canvas, name, format = "png") {
  if (!canvas) return;
  const png = canvas.toDataURL("image/png");
  if (format === "svg") {
    if (name === "radar") {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}" viewBox="0 0 ${canvas.width} ${canvas.height}"><image href="${png}" x="0" y="0" width="${canvas.width}" height="${canvas.height}"/></svg>`;
      const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
    }
    const titleElement = canvas.closest(".chart-frame")?.querySelector("h3, h2");
    const titleClone = titleElement?.cloneNode(true);
    titleClone?.querySelectorAll("button").forEach(button => button.remove());
    const title = titleClone?.textContent?.trim() || name;
    const safeTitle = title.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
    const exportHeight = canvas.height + 64;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${exportHeight}" viewBox="0 0 ${canvas.width} ${exportHeight}"><rect width="100%" height="100%" fill="white"/><text x="${canvas.width / 2}" y="38" text-anchor="middle" font-family="system-ui" font-size="28" font-weight="600">${safeTitle}</text><image href="${png}" x="0" y="64" width="${canvas.width}" height="${canvas.height}"/></svg>`;
    const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
  }
  const a = document.createElement("a"); a.download = `${name}.png`; a.href = png; document.body.appendChild(a); a.click(); a.remove();
}
function renderTables(books) {
  const details = DETAILS.filter(([key]) => !REMOVED_KEYS.has(key) && !TECHNICAL_KEYS.has(key));
  const technical = DETAILS.filter(([key]) => TECHNICAL_KEYS.has(key));
  const technicalCharacterIndex = technical.findIndex(([key]) => key === "document_char_count");
  const technicalWordsIndex = technical.findIndex(([key]) => key === "word_count");
  if (technicalCharacterIndex >= 0 && technicalWordsIndex >= 0) technical.splice(technicalWordsIndex, 0, technical.splice(technicalCharacterIndex, 1)[0]);
  const characterIndex = details.findIndex(([key]) => key === "document_char_count");
  const wordsIndex = details.findIndex(([key]) => key === "word_count");
  if (characterIndex >= 0 && wordsIndex >= 0 && characterIndex > wordsIndex) details.splice(wordsIndex, 0, details.splice(characterIndex, 1)[0]);
  document.getElementById("tables").innerHTML = `<div class="table-wrap"><h2>Tableau 1 · synthèse</h2>${table(books, RADAR)}</div><div class="table-wrap"><h2>Tableau 2 · détails</h2>${table(books, details)}</div><div class="table-wrap"><h2>Tableau 3 · données objectives</h2>${table(books, technical)}</div>`;
}
function dispersion(values) {
  const numbers = values.filter(Number.isFinite);
  if (numbers.length < 2) return null;
  let kept = numbers;
  if (numbers.length >= 4) {
    const ordered = [...numbers].sort((a, b) => a - b);
    const quantile = fraction => {
      const position = (ordered.length - 1) * fraction;
      const lower = Math.floor(position), upper = Math.ceil(position);
      return lower === upper ? ordered[lower] : ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower);
    };
    const q1 = quantile(.25), q3 = quantile(.75), iqr = q3 - q1;
    const filtered = numbers.filter(n => n >= q1 - 1.5 * iqr && n <= q3 + 1.5 * iqr);
    if (filtered.length >= 3) kept = filtered;
  }
  const mean = kept.reduce((sum, n) => sum + n, 0) / kept.length;
  if (!mean) return null;
  const standardDeviation = Math.sqrt(kept.reduce((sum, n) => sum + (n - mean) ** 2, 0) / kept.length);
  return standardDeviation / Math.abs(mean) * 100;
}
function table(books, definitions) {
  const header = `<th>Mesure</th>${books.map(b => `<th>${b.title}</th>`).join("")}<th>σ <button class="table-note-help" type="button" data-note-id="42" title="Afficher la note Dispersion">?</button></th>`;
  const rows = definitions.map(([key, label]) => {
    const displayed = books.map(b => { const n = value(b, key); return DISPLAY_INVERTED.has(key) && n != null ? 1 - n : n; });
    const sigma = TECHNICAL_KEYS.has(key) ? null : dispersion(displayed);
    return `<tr><td>${metricLabel(key)}</td>${displayed.map(n => `<td>${format(n, key)}</td>`).join("")}<td>${sigma == null ? "—" : `${sigma.toFixed(1)} %`}</td></tr>`;
  }).join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`;
}
function format(n, key) { if (n == null) return "—"; if (["word_count", "sentence_count", "paragraph_count", "document_char_count"].includes(key)) return Number(n).toLocaleString("fr-FR"); if (["punctuation_per_300_words", "noun_verb_ratio", "form_lemma_ratio", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "sentence_word_std_dev", "average_syntactic_depth", "burstiness"].includes(key)) return Number(n).toFixed(key === "burstiness" || key === "noun_verb_ratio" || key === "form_lemma_ratio" ? 2 : 1); return `${(Number(n) * 100).toFixed(0)} %`; }
function downloadSvg() {
  if (!chart) return;
  const w = 1000, h = 760, cx = 500, cy = 350, radius = 260, count = chart.data.labels.length;
  const point = (value, i) => { const angle = -Math.PI / 2 + i * Math.PI * 2 / count; return [cx + Math.cos(angle) * radius * value / 100, cy + Math.sin(angle) * radius * value / 100]; };
  const labels = chart.data.labels.map((label, i) => { const [x, y] = point(108, i); return `<text x="${x}" y="${y}" text-anchor="middle" font-family="system-ui" font-size="14">${label}</text>`; }).join("");
  const polygons = chart.data.datasets.map((set, i) => `<polygon points="${set.data.map((v, j) => point(v, j).join(",")).join(" ")}" fill="${COLORS[i % COLORS.length]}22" stroke="${COLORS[i % COLORS.length]}" stroke-width="3"/>`).join("");
  const title = currentRadarTitle || "Radar";
  const safeTitle = title.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="100%" height="100%" fill="white"/><text x="${cx}" y="30" text-anchor="middle" font-family="system-ui" font-size="22" font-weight="600">${safeTitle}</text><g stroke="#ddd8d2" fill="none">${[25,50,75,100].map(v => `<circle cx="${cx}" cy="${cy}" r="${radius*v/100}"/>`).join("")}</g>${polygons}${labels}</svg>`;
  const a = document.createElement("a"); a.download = "unshiter-radar.svg"; a.href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function exportStylePrompt() {
  fetch("style-interpretation-prompt.md").then(response => response.text()).then(content => {
    const href = URL.createObjectURL(new Blob([content], { type: "text/markdown" }));
    const link = document.createElement("a"); link.href = href; link.download = "style-interpretation-prompt.md"; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000);
  });
}
function exportPromptAndData() {
  const books = selected();
  const surfaceKeys = checkedMetrics();
  const surfaceAxes = surfaceKeys.map(field => {
    const id = data.metric_note_ids?.[field] || field;
    const noteId = data.note_ids?.[id];
    return { field, id, label: metricLabel(field), definition: noteId == null ? "" : (data.notes?.[String(noteId)] || "") };
  });
  const surfaceFor = book => {
    const values = surfaceKeys.map(key => scale(key, value(book, key))).filter(Number.isFinite);
    if (values.length < 3) return 0;
    return Math.abs(values.reduce((sum, current, index) => sum + current * values[(index + 1) % values.length] * Math.sin(2 * Math.PI / values.length), 0) / 2);
  };
  const metrics = {};
  for (const [field, label] of Object.entries(data.metric_labels || {})) {
    const id = data.metric_note_ids?.[field] || field;
    const noteId = data.note_ids?.[id];
    metrics[field] = { id, label, definition: noteId == null ? "" : (data.notes?.[String(noteId)] || "") };
  }
  const authors = {};
  for (const book of books) {
    const author = book.author || "Auteur inconnu", stats = book.analyses?.[0]?.stats || {};
    (authors[author] ||= { work_count: 0, works: [] }).work_count += 1;
    authors[author].works.push({ title: book.title, publication_date: book.publication_date, stylistic_coverage: surfaceFor(book), metrics: Object.fromEntries(Object.entries(metrics).map(([field, info]) => [field, stats[info.id]]).filter(([, value]) => value != null)) });
  }
  const save = (name, content, type) => { const href = URL.createObjectURL(new Blob([content], { type })); const link = document.createElement("a"); link.href = href; link.download = name; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); };
  save("style-interpretation-data.json", JSON.stringify({ metrics, surface: { label: "Couverture stylistique", definition: data.notes?.["29"] || "", axes: surfaceAxes }, authors }, null, 2), "application/json");
}
function controls() {
  const savedBooks = new Set(JSON.parse(localStorage.getItem("unshiter-books") || "[]").map(Number));
  const savedMetrics = new Set(JSON.parse(localStorage.getItem("unshiter-metrics") || "[]").map(metricKey));
  const groups = Object.groupBy ? Object.groupBy(data.books, b => b.author || "Auteur inconnu") : data.books.reduce((a, b) => ((a[b.author || "Auteur inconnu"] ||= []).push(b), a), {});
  const authorsPanel = document.getElementById("authors-panel");
  if (authorsPanel) {
    authorsPanel.open = localStorage.getItem("unshiter-authors-open") !== "0";
    authorsPanel.addEventListener("toggle", () => localStorage.setItem("unshiter-authors-open", authorsPanel.open ? "1" : "0"));
  }
  const metrics = document.getElementById("metrics");
  const metricsTitle = metrics?.previousElementSibling;
  if (metrics && metricsTitle?.tagName === "H2") {
    const panel = document.createElement("details");
    panel.id = "metrics-panel";
    panel.open = localStorage.getItem("unshiter-metrics-open") !== "0";
    const summary = document.createElement("summary");
    summary.textContent = "Mesures du radar";
    panel.appendChild(summary);
    metricsTitle.replaceWith(panel);
    panel.appendChild(metrics);
    panel.addEventListener("toggle", () => localStorage.setItem("unshiter-metrics-open", panel.open ? "1" : "0"));
  }
  for (const [author, books] of Object.entries(groups).sort(([a], [b]) => (a === "IA" ? -1 : b === "IA" ? 1 : a.localeCompare(b)))) { const id = `a${Math.random().toString(36).slice(2)}`; const all = books.every(b => savedBooks.size ? savedBooks.has(b.id) : true); document.getElementById("authors").insertAdjacentHTML("beforeend", `<details open><summary><input class="author-toggle" data-target="${id}" type="checkbox" ${all ? "checked" : ""}> ${author} (${books.length})</summary><div id="${id}">${books.map(b => `<label class="book"><input type="checkbox" value="${b.id}" ${savedBooks.size ? (savedBooks.has(b.id) ? "checked" : "") : "checked"}> ${b.title}</label>`).join("")}</div></details>`); }
  const clearBooks = document.createElement("button");
  clearBooks.type = "button";
  clearBooks.className = "authors-clear";
  clearBooks.textContent = "Tout décocher";
  document.getElementById("authors").appendChild(clearBooks);
  clearBooks.addEventListener("click", () => {
    document.querySelectorAll("#authors input").forEach(input => { input.checked = false; });
    localStorage.setItem("unshiter-books", JSON.stringify([]));
    draw();
  });
  MENU_METRICS.forEach(([key]) => { const id = publicMetricId(key); const defaultChecked = RADAR.some(([radarKey]) => radarKey === key); document.getElementById("metrics").insertAdjacentHTML("beforeend", `<label class="metric-row"><input type="checkbox" value="${id}" ${savedMetrics.size ? (savedMetrics.has(key) ? "checked" : "") : (defaultChecked ? "checked" : "")}> <span>${metricLabel(key)}</span><button class="metric-flip" data-key="${id}" type="button" title="Inverser le sens">↔</button><button class="metric-help" data-key="${id}" type="button">?</button></label>`); });
  const reset = document.createElement("button"); reset.id = "metrics-reset"; reset.type = "button"; reset.textContent = "Réinitialiser"; (document.getElementById("metrics-panel") || document.getElementById("metrics")).after(reset);
  reset.addEventListener("click", () => { Object.keys(localStorage).filter(key => key.startsWith("unshiter-") && key !== "unshiter-presets").forEach(key => localStorage.removeItem(key)); flippedAxes.clear(); location.reload(); });
  const presetBox = document.createElement("div");
  presetBox.className = "config-actions";
  presetBox.innerHTML = '<button type="button" id="config-save">Sauvegarder la configuration</button><div id="config-presets"></div>';
  reset.after(presetBox);
  const storedPresets = JSON.parse(localStorage.getItem("unshiter-presets") || "{}");
  const presets = Array.isArray(storedPresets)
    ? Object.fromEntries(storedPresets.filter(item => item && item.name).map(item => [String(item.name).trim(), item]))
    : (storedPresets && typeof storedPresets === "object" ? storedPresets : {});
  const presetList = presetBox.querySelector("#config-presets");
  presetList.replaceChildren();
  Object.keys(presets).sort((a, b) => a.localeCompare(b)).forEach(name => {
    const button = document.createElement("button"); button.type = "button"; button.dataset.name = name;
    const label = document.createElement("span"); label.textContent = name; button.appendChild(label);
    const remove = document.createElement("span"); remove.className = "preset-remove"; remove.textContent = "×"; remove.title = "Supprimer cette configuration"; remove.setAttribute("role", "button");
    remove.addEventListener("click", event => { event.preventDefault(); event.stopPropagation(); delete presets[name]; localStorage.setItem("unshiter-presets", JSON.stringify(presets)); button.remove(); });
    button.appendChild(remove);
    button.addEventListener("click", () => { const preset = presets[name]; localStorage.setItem("unshiter-books", JSON.stringify(preset.books)); localStorage.setItem("unshiter-metrics", JSON.stringify(preset.metrics)); location.reload(); }); presetList.appendChild(button);
  });
  presetBox.querySelector("#config-save").addEventListener("click", () => {
    const name = window.prompt("Nom de la configuration :")?.trim();
    if (!name) return;
    Object.keys(presets).filter(existing => existing.toLocaleLowerCase() === name.toLocaleLowerCase()).forEach(existing => delete presets[existing]);
    presets[name] = { books: selected().map(book => book.id), metrics: checkedMetrics().map(publicMetricId) };
    localStorage.setItem("unshiter-presets", JSON.stringify(presets));
    location.reload();
  });
  document.querySelectorAll("#authors input, #metrics input").forEach(x => x.addEventListener("change", () => { localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); localStorage.setItem("unshiter-metrics", JSON.stringify(checkedMetrics().map(publicMetricId))); draw(); }));
  document.querySelectorAll(".author-toggle").forEach(x => x.addEventListener("change", () => { document.querySelectorAll(`#${x.dataset.target} input`).forEach(b => b.checked = x.checked); localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); draw(); }));
  document.addEventListener("change", event => { const select = event.target.closest(".chart-download"); if (select) { downloadCanvas(document.getElementById(select.dataset.canvas), select.dataset.canvas, select.value); select.selectedIndex = -1; } });
  const noteClose = document.getElementById("metric-note-close");
  if (noteClose) noteClose.addEventListener("click", () => { document.getElementById("metric-note").hidden = true; });
  document.addEventListener("click", event => { const button = event.target.closest(".metric-help, .metric-flip, .table-note-help"); if (!button) return; event.preventDefault(); event.stopPropagation(); const note = document.getElementById("metric-note"); if (button.classList.contains("table-note-help")) { document.getElementById("metric-note-text").innerHTML = renderNote(Number(button.dataset.noteId)); note.hidden = false; return; } const key = metricKey(button.dataset.key); if (button.classList.contains("metric-help")) { const id = button.dataset.noteId || noteEntry(key).id; document.getElementById("metric-note-text").innerHTML = id == null ? "<p>Note non référencée.</p>" : renderNote(id); note.hidden = false; } else { flippedAxes.has(key) ? flippedAxes.delete(key) : flippedAxes.add(key); const row = button.closest(".metric-row"); row.querySelector("span").textContent = metricLabel(key); draw(); } });
  const limitsButton = document.getElementById("corpus-profile"), authorsButton = document.getElementById("author-profile"), authorLimitsButton = document.getElementById("author-limits"), worksButton = document.getElementById("works-profile");
  const exportBox = document.createElement("div"); exportBox.className = "prompt-exports";
  const promptButton = document.createElement("button"); promptButton.type = "button"; promptButton.id = "export-style-prompt"; promptButton.textContent = "Prompt d’analyse"; exportBox.appendChild(promptButton); promptButton.addEventListener("click", exportStylePrompt);
  const promptFilesButton = document.createElement("button"); promptFilesButton.type = "button"; promptFilesButton.id = "export-style-files"; promptFilesButton.textContent = "Données pour analyse"; exportBox.appendChild(promptFilesButton); promptFilesButton.addEventListener("click", exportPromptAndData);
  document.querySelector("aside")?.appendChild(exportBox);
  worksButton.hidden = true; authorsButton.hidden = false;
  const showWorksMode = () => { limitsButton.hidden = false; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = true; };
  const showLimitsMode = () => { limitsButton.hidden = true; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = false; };
  limitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = false; showLimitsMode(); draw(); });
  authorsButton.addEventListener("click", () => { authorProfile = true; corpusProfile = false; authorLimits = false; limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; draw(); });
  authorLimitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = true; draw(); });
  worksButton.addEventListener("click", () => { authorProfile = false; corpusProfile = false; authorLimits = false; showWorksMode(); draw(); });
}
fetch("data.json?v=20260822140717703062000").then(r => r.json()).then(json => {
  data = json;
  COLORS = Object.entries(data.palette || {}).filter(([key, color]) => key.startsWith("color") && color).map(([, color]) => color);
  IA_COLOR = data.palette?.ia || IA_COLOR;
  // L’ordre et la sélection par défaut viennent exclusivement des marqueurs
  // #tab1_N des notes, jamais d’une liste parallèle dans le JavaScript.
  if (Array.isArray(data.default_radar) && data.default_radar.length) {
    const ordered = data.default_radar.map(metricKey).map(key => RADAR.find(item => item[0] === key)).filter(Boolean);
    RADAR.splice(0, RADAR.length, ...ordered);
  }
  document.getElementById("site-name").textContent = data.site?.name || "Site Unshiter";
  const footerAuthor = document.getElementById("footer-author");
  footerAuthor.textContent = data.site?.author || "Thierry Crouzet";
  footerAuthor.href = data.site?.author_url || "https://tcrouzet.com";
  document.getElementById("site-description").textContent = data.site?.description || "";
  // Toutes les valeurs disponibles servent à établir chaque axe du radar.
  for (const [key] of ALL_METRICS) {
    corpusValues.set(key, data.books.map(b => value(b, key)).filter(Number.isFinite));
  }
  const versionDate = new Date(data.generated_at);
  const dateLabel = versionDate.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const copyright = data.site?.copyright || "© {author} — (date) — {livres} livres";
  const renderedCopyright = copyright.replaceAll("(date)", dateLabel).replaceAll("{date}", dateLabel).replaceAll("{livres}", String(data.books.length)).replaceAll("{author}", data.site?.author || "").replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  document.querySelector("footer").innerHTML = renderedCopyright;
  controls();
  draw();
}).catch(() => { document.getElementById("footer-version").textContent = "erreur de chargement"; });
