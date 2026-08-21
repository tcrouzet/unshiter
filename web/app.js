const RADAR = [
  ["punctuation_per_300_words", "Densité de ponctuations"], ["punctuation_diversity", "Diversité de ponctuation"],
  ["structural_diversity", "Diversité des structures"], ["structural_rhythm", "Rythme des structures"],
  ["average_syntactic_depth", "Profondeur syntaxique"], ["sentence_start_diversity", "Diversité des débuts de phrase"], ["sentence_word_std_dev", "Diversité des longueurs de phrase"],
  ["noun_verb_ratio", "Ratio noms/verbes"], ["filtered_repetition_rate", "Répétitions lexicales"],
];
const DETAILS = [
  ["stylistic_repetition_rate", "Diversité stylistique", true], ["family_repetition_rate", "Répétitions familiales", true], ["phonetic_repetition_rate", "Répétitions sonores", true], ["absolute_repetition_rate", "Répétitions non filtrées", true],
  ["trigram_repetition", "Répétition globale des trigrammes", true], ["moving_trigram_repetition", "Répétition locale des trigrammes", true], ["function_word_ratio", "Mots-outils", true], ["noun_ratio", "Noms", true], ["verb_ratio", "Verbes", true], ["adjective_ratio", "Adjectifs", true], ["adverb_ratio", "Adverbes", true], ["sentence_word_std_dev", "Diversité de longueurs de phrase (mots)", false], ["gzip_compression_ratio", "Compression gzip", true], ["relative_clause_ratio", "Relatives et subordonnées", true], ["nominal_sentence_ratio", "Phrases nominales", true], ["active_voice_ratio", "Voix active", true], ["metaphorical_comme_ratio", "Comparaisons métaphoriques", true], ["form_lemma_ratio", "Formes par lemme", false], ["hapax_ratio", "Mots employés une seule fois", true],
  ["word_count", "Mots", false], ["sentence_count", "Phrases", false], ["paragraph_count", "Paragraphes", false], ["avg_word_length", "Longueur moyenne des mots (caractères)", false], ["avg_sentence_length", "Longueur moyenne des phrases (caractères)", false], ["avg_sentence_word_count", "Longueur moyenne des phrases (mots)", false], ["median_sentence_length", "Longueur médiane des phrases (caractères)", false], ["sentence_length_p10", "Longueur P10 des phrases (caractères)", false], ["sentence_length_p90", "Longueur P90 des phrases (caractères)", false], ["paragraph_length_std_dev", "Écart-type des paragraphes (mots)", false], ["document_char_count", "Signes (caractères)", false],
];
const ALL_METRICS = [...RADAR, ...DETAILS.map(([key, label]) => [key, label])];
const TECHNICAL_KEYS = new Set(["word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "document_char_count"]);
const REMOVED_KEYS = new Set(["avg_sentence_word_count", "sentence_word_std_dev"]);
const MENU_METRICS = ALL_METRICS.filter(([key], index, all) => !TECHNICAL_KEYS.has(key) && (!REMOVED_KEYS.has(key) || key === "sentence_word_std_dev") && all.findIndex(item => item[0] === key) === index);
let COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"];
let data, chart, surfaceChart, evolutionCharts = [], corpusProfile = false, authorProfile = false, authorLimits = false;
const flippedAxes = new Set();
function noteEntry(key) {
  const publicId = data?.metric_note_ids?.[key];
  const id = publicId == null ? null : data?.note_ids?.[publicId];
  const title = data?.metric_labels?.[key] || (id == null ? `Mesure ${publicId || "non référencée"}` : (data?.note_titles?.[String(id)] || `Mesure ${id}`));
  return { id, title, aliases: title.split("/").map(alias => alias.trim()) };
}
function metricLabel(key) { const entry = noteEntry(key); const inverse = INVERSE.has(key) !== flippedAxes.has(key); return entry.aliases[inverse ? 1 : 0] || entry.aliases[0]; }
function metricNote(key) {
  const entry = noteEntry(key);
  return entry.id == null ? "Note non référencée." : (data?.notes?.[String(entry.id)] || "Note non référencée.");
}
function pastel(hex, alpha = "35") { return /^#[0-9a-f]{6}$/i.test(hex) ? `${hex}${alpha}` : hex; }
// Valeurs de référence du corpus complet. Elles sont construites une seule fois
// au chargement et ne dépendent jamais des cases actuellement cochées.
let corpusValues = new Map();
const value = (book, key) => {
  const stats = book.analyses[0]?.stats || {};
  if (key === "stylistic_repetition_rate") return 1 - Number(stats.stylistic_repetition_rate || 0);
  if (key === "relative_clause_ratio") return Number(stats.relative_clause_ratio || 0) + Number(stats.subordinate_clause_ratio || 0);
  if (key === "noun_verb_ratio" && stats[key] == null) return Number(stats.verb_ratio) ? Number(stats.noun_ratio || 0) / Number(stats.verb_ratio) : 0;
  return stats[key] == null ? null : Number(stats[key]);
};
function selected() { return [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle):checked")].map(x => data.books.find(b => b.id === Number(x.value))).filter(Boolean); }
function checkedMetrics() { return [...new Set([...document.querySelectorAll("#metrics input:checked")].map(x => x.value))]; }
const INVERSE = new Set(["noun_verb_ratio", "filtered_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate", "trigram_repetition", "moving_trigram_repetition", "adjective_ratio", "adverb_ratio", "relative_clause_ratio", "nominal_sentence_ratio", "metaphorical_comme_ratio"]);
function scale(key, n) {
  if (n == null) return null;
  // Important : la référence est l'ensemble des livres exportés, pas la
  // sélection affichée. Ainsi retirer un auteur ne change pas les limites.
  const values = corpusValues.get(key) || [];
  const minimum = Math.min(...values), maximum = Math.max(...values);
  if (!Number.isFinite(minimum) || maximum === minimum) return 50;
  let relative = (n - minimum) / (maximum - minimum);
  if (INVERSE.has(key) !== flippedAxes.has(key)) relative = 1 - relative;
  return Math.max(0, Math.min(100, relative * 100));
}
function draw() {
  const books = selected(), keys = checkedMetrics(), labels = keys.map(metricLabel);
  chart?.destroy();
  const multipleAuthors = new Set(books.map(book => book.author).filter(Boolean)).size > 1;
  const authorName = author => (author || "Auteur inconnu").trim().split(/\s+/).at(-1);
  const datasets = corpusProfile ? profileDatasets(keys, authorLimits ? authorAverages(books) : books) : authorProfile ? authorDatasets(keys, books) : books.map((b, i) => ({ label: multipleAuthors ? `${b.title} · ${authorName(b.author)}` : b.title, data: keys.map(k => { const n = scale(k, value(b, k)); return n == null ? null : Math.max(10, n); }), borderColor: COLORS[i % COLORS.length], backgroundColor: pastel(COLORS[i % COLORS.length]), fill: true, pointRadius: 0 }));
  chart = new Chart(document.getElementById("radar"), { type: "radar", data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "nearest", intersect: false }, scales: { r: { min: 0, max: 100, ticks: { display: false, stepSize: 25 }, pointLabels: { font: context => ({ size: Math.max(11, Math.min(15, context.chart.width / 65)), weight: "600" }) }, grid: { display: true, color: "#ccd1d5" }, angleLines: { display: true, color: "#d9dddf" } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: () => "", title: items => items[0]?.dataset?.label || "" } } } } });
  document.getElementById("radar-legend").innerHTML = datasets.map(dataset => `<span><i style="background:${dataset.borderColor}"></i>${dataset.label}</span>`).join("");
  drawSurfaces(books);
  drawEvolution(books);
  renderTables(books);
}
function profileDatasets(keys, books) {
  const rows = ["Minimum", "Médiane", "Maximum"];
  const colors = ["#3478b8", "#d13c36", "#e19a2d"];
  return rows.map((label, index) => ({ label, data: keys.map(key => {
    const values = books.map(book => scale(key, value(book, key))).filter(Number.isFinite).sort((a, b) => a - b);
    if (!values.length) return 50;
    return Math.max(10, index === 0 ? values[0] : index === 2 ? values.at(-1) : values[Math.floor((values.length - 1) / 2)]);
  }), borderColor: colors[index], backgroundColor: pastel(colors[index]), fill: true, pointRadius: 0 }));
}
function authorDatasets(keys, books) {
  return authorAverages(books).map((book, i) => ({ label: book.author.trim().split(/\s+/).at(-1), data: keys.map(key => { const n = scale(key, value(book, key)); return n == null ? null : Math.max(10, n); }), borderColor: COLORS[i % COLORS.length], backgroundColor: pastel(COLORS[i % COLORS.length]), fill: true, pointRadius: 0 }));
}
function authorAverages(books) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([author, authorBooks]) => { const stats = {}; for (const [key] of ALL_METRICS) { const values = authorBooks.map(book => value(book, key)).filter(Number.isFinite); if (values.length) stats[key] = values.reduce((sum, n) => sum + n, 0) / values.length; } return { author, analyses: [{ stats }] }; });
}
function drawSurfaces(books) {
  surfaceChart?.destroy();
  const keys = checkedMetrics();
  const profiles = (authorProfile || authorLimits) ? authorAverages(books).map(book => ({ label: book.author, values: keys.map(key => scale(key, value(book, key)) ?? 0) })) : books.map(book => ({ label: book.title, values: keys.map(key => scale(key, value(book, key)) ?? 0) }));
  const labels = profiles.map(profile => profile.label);
  const surfaceBox = document.querySelector(".surface-box");
  if (surfaceBox) surfaceBox.style.height = `${Math.max(300, profiles.length * 30 + 90)}px`;
  const areas = profiles.map(profile => { const values = profile.values, n = values.length; return n < 3 ? 0 : Math.abs(values.reduce((sum, v, i) => sum + v * values[(i + 1) % n] * Math.sin(2 * Math.PI / n), 0) / 2); });
  const sorted = labels.map((label, i) => ({ label, area: areas[i], color: COLORS[i % COLORS.length] })).sort((a, b) => a.area - b.area);
  surfaceChart = new Chart(document.getElementById("surfaces"), { type: "bar", data: { labels: sorted.map(x => x.label), datasets: [{ label: "Couverture stylistique", data: sorted.map(x => x.area), backgroundColor: sorted.map(x => `${x.color}b8`), borderColor: sorted.map(x => x.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: () => "" } } }, scales: { x: { display: false, beginAtZero: true }, y: { grid: { display: false } } } } });
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
    container.insertAdjacentHTML("beforeend", `<div class="evolution-chart chart-frame"><h3>${label}</h3><canvas id="${id}"></canvas><select class="chart-download" data-canvas="${id}" aria-label="Télécharger ${label}"><option value="png">PNG</option><option value="svg">SVG</option></select></div>`);
    const lineChart = new Chart(document.getElementById(id), { type: "line", data: { labels: books.map(book => book.title), datasets: [{ label, data: books.map(book => { const n = value(book, key); return n == null ? null : scale(key, n); }), borderColor: COLORS[i % COLORS.length], backgroundColor: COLORS[i % COLORS.length], tension: .25, pointRadius: 3, spanGaps: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { display: false }, grid: { color: "#ccd1d5" } }, x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => `${books[items[0].dataIndex].publication_date.slice(0, 4)} · ${books[items[0].dataIndex].title}` } } } } });
    lineChart.$years = books.map(book => book.publication_date.slice(0, 4));
    evolutionCharts.push(lineChart);
  });
}
Chart.register({ id: "publicationYears", afterDatasetsDraw(instance) { const meta = instance.getDatasetMeta(0); const years = instance.$years || []; const ctx = instance.ctx; const limit = instance.chartArea.top + instance.chartArea.height * .75; ctx.save(); ctx.font = "11px system-ui"; ctx.fillStyle = "#6f6962"; ctx.textAlign = "center"; meta.data.forEach((point, i) => { if (years[i]) ctx.fillText(years[i], point.x, point.y < limit ? point.y + 15 : point.y - 9); }); ctx.restore(); } });
function downloadCanvas(canvas, name, format = "png") {
  const png = canvas.toDataURL("image/png");
  if (format === "svg") {
    const title = canvas.closest(".chart-frame")?.querySelector("h3, h2")?.textContent || name;
    const safeTitle = title.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height + 42}" viewBox="0 0 ${canvas.width} ${canvas.height + 42}"><rect width="100%" height="100%" fill="white"/><text x="20" y="28" font-family="system-ui" font-size="20" font-weight="600">${safeTitle}</text><image href="${png}" x="0" y="42" width="${canvas.width}" height="${canvas.height}"/></svg>`;
    const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; a.click(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
  }
  const a = document.createElement("a"); a.download = `${name}.png`; a.href = png; a.click();
}
function renderTables(books) {
  document.getElementById("tables").innerHTML = `<div class="table-wrap"><h2>Tableau 1 · synthèse</h2>${table(books, RADAR)}</div><div class="table-wrap"><h2>Tableau 2 · détails</h2>${table(books, DETAILS.filter(([key]) => !REMOVED_KEYS.has(key)))}</div>`;
}
function table(books, definitions) { return `<table><thead><tr><th>Mesure</th>${books.map(b => `<th>${b.title}</th>`).join("")}</tr></thead><tbody>${definitions.map(([key, label]) => `<tr><td>${metricLabel(key)}</td>${books.map(b => `<td>${format(value(b, key), key)}</td>`).join("")}</tr>`).join("")}</tbody></table>`; }
function format(n, key) { if (n == null) return "—"; if (["word_count", "sentence_count", "paragraph_count", "document_char_count"].includes(key)) return Number(n).toLocaleString("fr-FR"); if (["punctuation_per_300_words", "noun_verb_ratio", "form_lemma_ratio", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "sentence_word_std_dev", "average_syntactic_depth", "burstiness"].includes(key)) return Number(n).toFixed(key === "burstiness" || key === "noun_verb_ratio" || key === "form_lemma_ratio" ? 2 : 1); return `${(Number(n) * 100).toFixed(0)} %`; }
function downloadSvg() {
  if (!chart) return;
  const w = 1000, h = 760, cx = 500, cy = 350, radius = 260, count = chart.data.labels.length;
  const point = (value, i) => { const angle = -Math.PI / 2 + i * Math.PI * 2 / count; return [cx + Math.cos(angle) * radius * value / 100, cy + Math.sin(angle) * radius * value / 100]; };
  const labels = chart.data.labels.map((label, i) => { const [x, y] = point(108, i); return `<text x="${x}" y="${y}" text-anchor="middle" font-family="system-ui" font-size="14">${label}</text>`; }).join("");
  const polygons = chart.data.datasets.map((set, i) => `<polygon points="${set.data.map((v, j) => point(v, j).join(",")).join(" ")}" fill="${COLORS[i % COLORS.length]}22" stroke="${COLORS[i % COLORS.length]}" stroke-width="3"/>`).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="100%" height="100%" fill="white"/><g stroke="#ddd8d2" fill="none">${[25,50,75,100].map(v => `<circle cx="${cx}" cy="${cy}" r="${radius*v/100}"/>`).join("")}</g>${polygons}${labels}<text x="20" y="30" font-family="system-ui" font-size="18">Unshiter · radar</text></svg>`;
  const a = document.createElement("a"); a.download = "unshiter-radar.svg"; a.href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })); a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function controls() {
  const savedBooks = new Set(JSON.parse(localStorage.getItem("unshiter-books") || "[]").map(Number));
  const savedMetrics = new Set(JSON.parse(localStorage.getItem("unshiter-metrics") || "[]"));
  const groups = Object.groupBy ? Object.groupBy(data.books, b => b.author || "Auteur inconnu") : data.books.reduce((a, b) => ((a[b.author || "Auteur inconnu"] ||= []).push(b), a), {});
  const authorsPanel = document.getElementById("authors-panel");
  if (authorsPanel) {
    authorsPanel.open = localStorage.getItem("unshiter-authors-open") !== "0";
    authorsPanel.addEventListener("toggle", () => localStorage.setItem("unshiter-authors-open", authorsPanel.open ? "1" : "0"));
  }
  for (const [author, books] of Object.entries(groups).sort()) { const id = `a${Math.random().toString(36).slice(2)}`; const all = books.every(b => savedBooks.size ? savedBooks.has(b.id) : true); document.getElementById("authors").insertAdjacentHTML("beforeend", `<details open><summary><input class="author-toggle" data-target="${id}" type="checkbox" ${all ? "checked" : ""}> ${author} (${books.length})</summary><div id="${id}">${books.map(b => `<label class="book"><input type="checkbox" value="${b.id}" ${savedBooks.size ? (savedBooks.has(b.id) ? "checked" : "") : "checked"}> ${b.title}</label>`).join("")}</div></details>`); }
  MENU_METRICS.forEach(([key], index) => document.getElementById("metrics").insertAdjacentHTML("beforeend", `<label class="metric-row"><input type="checkbox" value="${key}" ${savedMetrics.size ? (savedMetrics.has(key) ? "checked" : "") : (index < RADAR.length ? "checked" : "")}> <span>${metricLabel(key)}</span><button class="metric-flip" data-key="${key}" type="button" title="Inverser le sens">↔</button><button class="metric-help" data-key="${key}" type="button">?</button></label>`));
  const reset = document.createElement("button"); reset.id = "metrics-reset"; reset.type = "button"; reset.textContent = "Réinitialiser"; document.getElementById("metrics").after(reset);
  reset.addEventListener("click", () => { Object.keys(localStorage).filter(key => key.startsWith("unshiter-")).forEach(key => localStorage.removeItem(key)); flippedAxes.clear(); location.reload(); });
  document.querySelectorAll("#authors input, #metrics input").forEach(x => x.addEventListener("change", () => { localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); localStorage.setItem("unshiter-metrics", JSON.stringify(checkedMetrics())); draw(); }));
  document.querySelectorAll(".author-toggle").forEach(x => x.addEventListener("change", () => { document.querySelectorAll(`#${x.dataset.target} input`).forEach(b => b.checked = x.checked); localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); draw(); }));
  document.addEventListener("change", event => { const select = event.target.closest(".chart-download"); if (select) downloadCanvas(document.getElementById(select.dataset.canvas), select.dataset.canvas, select.value); });
  const noteClose = document.getElementById("metric-note-close");
  if (noteClose) noteClose.addEventListener("click", () => { document.getElementById("metric-note").hidden = true; });
  document.addEventListener("click", event => { const button = event.target.closest(".metric-help, .metric-flip"); if (!button) return; event.preventDefault(); event.stopPropagation(); const note = document.getElementById("metric-note"); if (button.classList.contains("metric-help")) { const id = button.dataset.noteId || noteEntry(button.dataset.key).id; document.getElementById("metric-note-text").textContent = id == null ? "Note non référencée." : (data.notes?.[String(id)] || "Note non référencée."); note.hidden = false; } else { flippedAxes.has(button.dataset.key) ? flippedAxes.delete(button.dataset.key) : flippedAxes.add(button.dataset.key); const row = button.closest(".metric-row"); row.querySelector("span").textContent = metricLabel(button.dataset.key); draw(); } });
  const limitsButton = document.getElementById("corpus-profile"), authorsButton = document.getElementById("author-profile"), authorLimitsButton = document.getElementById("author-limits"), worksButton = document.getElementById("works-profile");
  worksButton.hidden = false; authorsButton.hidden = true;
  const showWorksButton = () => { limitsButton.hidden = true; authorsButton.hidden = true; worksButton.hidden = false; };
  const showModeButtons = () => { limitsButton.hidden = false; authorsButton.hidden = true; authorLimitsButton.hidden = true; worksButton.hidden = false; };
  limitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = false; showWorksButton(); draw(); });
  authorsButton.addEventListener("click", () => { authorProfile = true; corpusProfile = false; authorLimits = false; limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; draw(); });
  authorLimitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = true; draw(); });
  worksButton.addEventListener("click", () => { authorProfile = false; corpusProfile = false; authorLimits = false; showModeButtons(); draw(); });
}
fetch("data.json?v=20260821084151192439000").then(r => r.json()).then(json => {
  data = json;
  COLORS = Object.values(data.palette || {}).filter(Boolean);
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
