const RADAR = [
  ["punctuation_per_300_words", "Ponctuation (signes/300 mots)"], ["punctuation_diversity", "Diversité de ponctuation"],
  ["structural_diversity", "Diversité des structures"], ["structural_rhythm", "Rythme des structures"],
  ["average_syntactic_depth", "Profondeur syntaxique"], ["sentence_start_diversity", "Diversité des débuts de phrase"],
  ["burstiness", "Burstiness"], ["noun_verb_ratio", "Ratio noms/verbes"], ["filtered_repetition_rate", "Répétitions lexicales"],
];
const DETAILS = [
  ["stylistic_repetition_rate", "Diversité stylistique", true], ["family_repetition_rate", "Répétitions familiales", true], ["phonetic_repetition_rate", "Répétitions sonores", true], ["absolute_repetition_rate", "Répétitions non filtrées", true],
  ["trigram_repetition", "Répétition globale des trigrammes", true], ["moving_trigram_repetition", "Répétition locale des trigrammes", true], ["function_word_ratio", "Mots-outils", true], ["noun_ratio", "Noms", true], ["verb_ratio", "Verbes", true], ["adjective_ratio", "Adjectifs", true], ["adverb_ratio", "Adverbes", true], ["sentence_word_std_dev", "Diversité de longueurs de phrase (mots)", false], ["gzip_compression_ratio", "Compression gzip", true], ["relative_clause_ratio", "Relatives et subordonnées", true], ["nominal_sentence_ratio", "Phrases nominales", true], ["active_voice_ratio", "Voix active", true], ["metaphorical_comme_ratio", "Comparaisons métaphoriques", true], ["form_lemma_ratio", "Formes par lemme", false], ["hapax_ratio", "Mots employés une seule fois", true],
  ["word_count", "Mots", false], ["sentence_count", "Phrases", false], ["paragraph_count", "Paragraphes", false], ["avg_word_length", "Longueur moyenne des mots (caractères)", false], ["avg_sentence_length", "Longueur moyenne des phrases (caractères)", false], ["avg_sentence_word_count", "Longueur moyenne des phrases (mots)", false], ["median_sentence_length", "Longueur médiane des phrases (caractères)", false], ["sentence_length_p10", "Longueur P10 des phrases (caractères)", false], ["sentence_length_p90", "Longueur P90 des phrases (caractères)", false], ["paragraph_length_std_dev", "Écart-type des paragraphes (mots)", false],
];
const ALL_METRICS = [...RADAR, ...DETAILS.map(([key, label]) => [key, label])];
const COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"];
let data, chart, surfaceChart, evolutionCharts = [], corpusProfile = false, authorProfile = false, authorLimits = false;
const flippedAxes = new Set();
Chart.register({ id: "axisQuestions", afterDraw(instance) { const scale = instance.scales.r; if (!scale) return; const ctx = instance.ctx; ctx.save(); ctx.font = "bold 12px system-ui"; ctx.fillStyle = "#6f6962"; ctx.textAlign = "center"; instance.data.labels.forEach((_label, i) => { const point = scale.getPointPositionForValue(i, 108); ctx.fillText("?", point.x, point.y); }); ctx.restore(); } });
// Valeurs de référence du corpus complet. Elles sont construites une seule fois
// au chargement et ne dépendent jamais des cases actuellement cochées.
let corpusValues = new Map();
const value = (book, key) => {
  const stats = book.analyses[0]?.stats || {};
  if (key === "stylistic_repetition_rate") return 1 - Number(stats.stylistic_repetition_rate || 0);
  if (key === "relative_clause_ratio") return Number(stats.relative_clause_ratio || 0) + Number(stats.subordinate_clause_ratio || 0);
  return stats[key] == null ? null : Number(stats[key]);
};
function selected() { return [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle):checked")].map(x => data.books.find(b => b.id === Number(x.value))).filter(Boolean); }
function checkedMetrics() { return [...document.querySelectorAll("#metrics input:checked")].map(x => x.value); }
const INVERSE = new Set(["filtered_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate", "trigram_repetition", "moving_trigram_repetition", "adjective_ratio", "adverb_ratio", "relative_clause_ratio", "metaphorical_comme_ratio"]);
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
  const books = selected(), keys = checkedMetrics(), labels = keys.map(k => ALL_METRICS.find(x => x[0] === k)?.[1] || k);
  chart?.destroy();
  const multipleAuthors = new Set(books.map(book => book.author).filter(Boolean)).size > 1;
  const authorName = author => (author || "Auteur inconnu").trim().split(/\s+/).at(-1);
  const datasets = corpusProfile ? profileDatasets(keys, authorLimits ? authorAverages(books) : books) : authorProfile ? authorDatasets(keys, books) : books.map((b, i) => ({ label: multipleAuthors ? `${b.title} · ${authorName(b.author)}` : b.title, data: keys.map(k => scale(k, value(b, k))), borderColor: COLORS[i % COLORS.length], backgroundColor: `${COLORS[i % COLORS.length]}22`, pointRadius: 0 }));
  chart = new Chart(document.getElementById("radar"), { type: "radar", data: { labels, datasets }, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "nearest", intersect: false }, onClick: (event, elements) => { if (elements.length) return; const scale = chart.scales.r, dx = event.x - scale.xCenter, dy = event.y - scale.yCenter, radius = Math.hypot(dx, dy); if (radius < scale.drawingArea * .78) return; let angle = Math.atan2(dy, dx) + Math.PI / 2; if (angle < 0) angle += Math.PI * 2; const index = Math.round(angle / (Math.PI * 2 / keys.length)) % keys.length, key = keys[index]; flippedAxes.has(key) ? flippedAxes.delete(key) : flippedAxes.add(key); const help = document.getElementById("axis-help"); help.textContent = data.notes?.[ALL_METRICS.find(item => item[0] === key)?.[1]] || "Aucune note disponible pour cette mesure."; help.hidden = false; draw(); }, scales: { r: { min: 0, max: 100, ticks: { display: false, stepSize: 25 }, grid: { display: true, color: "#ccd1d5" }, angleLines: { display: true, color: "#d9dddf" } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { label: () => "", title: items => items[0]?.dataset?.label || "" } } } } });
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
    return index === 0 ? values[0] : index === 2 ? values.at(-1) : values[Math.floor((values.length - 1) / 2)];
  }), borderColor: colors[index], backgroundColor: `${colors[index]}22`, pointRadius: 0 }));
}
function authorDatasets(keys, books) {
  return authorAverages(books).map((book, i) => ({ label: book.author.trim().split(/\s+/).at(-1), data: keys.map(key => scale(key, value(book, key))), borderColor: COLORS[i % COLORS.length], backgroundColor: `${COLORS[i % COLORS.length]}22`, pointRadius: 0 }));
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
  const areas = profiles.map(profile => { const values = profile.values, n = values.length; return n < 3 ? 0 : Math.abs(values.reduce((sum, v, i) => sum + v * values[(i + 1) % n] * Math.sin(2 * Math.PI / n), 0) / 2); });
  const sorted = labels.map((label, i) => ({ label, area: areas[i], color: COLORS[i % COLORS.length] })).sort((a, b) => a.area - b.area);
  surfaceChart = new Chart(document.getElementById("surfaces"), { type: "bar", data: { labels: sorted.map(x => x.label), datasets: [{ label: "Couverture stylistique", data: sorted.map(x => x.area), backgroundColor: sorted.map(x => `${x.color}b8`), borderColor: sorted.map(x => x.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: () => "" } } }, scales: { x: { display: false, beginAtZero: true }, y: { grid: { display: false } } } } });
}
function drawEvolution(selectedBooks) {
  evolutionCharts.forEach(item => item.destroy());
  evolutionCharts = [];
  const books = [...selectedBooks].filter(book => book.publication_date && !Number.isNaN(Date.parse(book.publication_date))).sort((a, b) => Date.parse(a.publication_date) - Date.parse(b.publication_date));
  const definitions = checkedMetrics().map(key => ALL_METRICS.find(item => item[0] === key)).filter(Boolean);
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
  document.getElementById("tables").innerHTML = `<div class="table-wrap"><h2>Tableau 1 · synthèse</h2>${table(books, RADAR)}</div><div class="table-wrap"><h2>Tableau 2 · détails</h2>${table(books, DETAILS)}</div>`;
}
function table(books, definitions) { return `<table><thead><tr><th>Mesure</th>${books.map(b => `<th>${b.title}</th>`).join("")}</tr></thead><tbody>${definitions.map(([key, label]) => `<tr><td>${label}</td>${books.map(b => `<td>${format(value(b, key), key)}</td>`).join("")}</tr>`).join("")}</tbody></table>`; }
function format(n, key) { if (n == null) return "—"; if (["word_count", "sentence_count", "paragraph_count"].includes(key)) return Number(n).toLocaleString("fr-FR"); if (["punctuation_per_300_words", "noun_verb_ratio", "form_lemma_ratio", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "sentence_word_std_dev", "average_syntactic_depth", "burstiness"].includes(key)) return Number(n).toFixed(key === "burstiness" || key === "noun_verb_ratio" || key === "form_lemma_ratio" ? 2 : 1); return `${(Number(n) * 100).toFixed(0)} %`; }
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
  for (const [author, books] of Object.entries(groups).sort()) { const id = `a${Math.random().toString(36).slice(2)}`; const all = books.every(b => savedBooks.size ? savedBooks.has(b.id) : true); document.getElementById("authors").insertAdjacentHTML("beforeend", `<details open><summary><input class="author-toggle" data-target="${id}" type="checkbox" ${all ? "checked" : ""}> ${author} (${books.length})</summary><div id="${id}">${books.map(b => `<label class="book"><input type="checkbox" value="${b.id}" ${savedBooks.size ? (savedBooks.has(b.id) ? "checked" : "") : "checked"}> ${b.title}</label>`).join("")}</div></details>`); }
  ALL_METRICS.forEach(([key, label], index) => document.getElementById("metrics").insertAdjacentHTML("beforeend", `<label><input type="checkbox" value="${key}" ${savedMetrics.size ? (savedMetrics.has(key) ? "checked" : "") : (index < RADAR.length ? "checked" : "")}> ${label}</label>`));
  document.querySelectorAll("#authors input, #metrics input").forEach(x => x.addEventListener("change", () => { localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); localStorage.setItem("unshiter-metrics", JSON.stringify(checkedMetrics())); draw(); }));
  document.querySelectorAll(".author-toggle").forEach(x => x.addEventListener("change", () => { document.querySelectorAll(`#${x.dataset.target} input`).forEach(b => b.checked = x.checked); localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); draw(); }));
  document.addEventListener("change", event => { const select = event.target.closest(".chart-download"); if (select) downloadCanvas(document.getElementById(select.dataset.canvas), select.dataset.canvas, select.value); });
  const limitsButton = document.getElementById("corpus-profile"), authorsButton = document.getElementById("author-profile"), authorLimitsButton = document.getElementById("author-limits"), worksButton = document.getElementById("works-profile");
  const showWorksButton = () => { limitsButton.hidden = true; authorsButton.hidden = true; worksButton.hidden = false; };
  const showModeButtons = () => { limitsButton.hidden = false; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = true; };
  limitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = false; showWorksButton(); draw(); });
  authorsButton.addEventListener("click", () => { authorProfile = true; corpusProfile = false; authorLimits = false; limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; draw(); });
  authorLimitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = true; draw(); });
  worksButton.addEventListener("click", () => { authorProfile = false; corpusProfile = false; authorLimits = false; showModeButtons(); draw(); });
}
fetch("data.json").then(r => r.json()).then(json => {
  data = json;
  document.getElementById("site-name").textContent = data.site?.name || "Site Unshiter";
  document.getElementById("site-author").textContent = data.site?.author || "Thierry Crouzet";
  document.getElementById("site-author").href = data.site?.author_url || "https://tcrouzet.com";
  document.getElementById("site-description").textContent = data.site?.description || "";
  const help = document.getElementById("coverage-help"); help.textContent = data.site?.coverage_help || "Surface sur le graphique radar.";
  document.getElementById("coverage-help-button").addEventListener("click", () => { help.hidden = !help.hidden; });
  // Toutes les valeurs disponibles servent à établir chaque axe du radar.
  for (const [key] of ALL_METRICS) {
    corpusValues.set(key, data.books.map(b => value(b, key)).filter(Number.isFinite));
  }
  document.getElementById("status").textContent = `${data.books.length} livre${data.books.length > 1 ? "s" : ""} · export du ${new Date(data.generated_at).toLocaleString("fr-FR")}`;
  controls();
  draw();
}).catch(() => { document.getElementById("status").textContent = "Impossible de charger data.json."; });
