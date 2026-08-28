const RADAR = [
  ["classicism_score", "Classique ↔ Contemporain"],
  ["baroque_score", "Maximaliste ↔ Minimaliste"],
  ["narrativity_score", "Narratif ↔ Descriptif"],
  ["emotionality_score", "Émotionnel ↔ Neutre"],
  ["discursivite_score", "Discursif ↔ Immersif"],
];
const DETAILS = [
  ["action_verb_ratio", "Verbes d’action", true], ["temporal_connector_ratio", "Connecteurs temporels", true], ["personal_subject_ratio", "Sujets personnels", true], ["narrative_past_ratio", "Passé narratif", true],
  ["emotion_word_ratio", "Mots émotionnels", true], ["affect_verb_ratio", "Verbes de réaction affective", true], ["exclamation_ratio", "Exclamations", true], ["exclamative_construction_ratio", "Constructions exclamatives", true],
  ["logical_connector_ratio", "Connecteurs logiques", true], ["abstract_noun_ratio", "Noms abstraits", true], ["gnomic_present_ratio", "Présent gnomique", true],
  ["stylistic_repetition_rate", "Diversité stylistique", true], ["family_repetition_rate", "Répétitions familiales", true], ["phonetic_repetition_rate", "Répétitions sonores", true], ["absolute_repetition_rate", "Répétitions non filtrées", true],
  ["present_participle_ratio", "Participes présents", true], ["past_participle_ratio", "Participes passés", true],
  ["simple_past_ratio", "Passé simple", true], ["literary_subjunctive_ratio", "Subjonctif littéraire", true], ["negation_completeness_ratio", "Négations complètes", true], ["negation_ratio", "Négativité / Positivité", true], ["periphrastic_future_ratio", "Futur périphrastique", true], ["oral_familiarity_ratio", "Familiarité orale", true], ["dialogue_ratio", "Dialogue", true], ["avg_modifiers_per_noun", "Modificateurs par nom", true], ["heavily_modified_noun_ratio", "Noms fortement modifiés", true], ["lexical_rarity_score", "Rareté lexicale", true], ["adjective_chain_ratio", "Chaînes adjectivales", true], ["avg_adjective_chain_length", "Longueur des chaînes adjectivales", true],
  ["trigram_repetition", "Répétition globale des trigrammes", true], ["moving_trigram_repetition", "Répétition locale des trigrammes", true], ["function_word_ratio", "Mots-outils", true], ["noun_ratio", "Noms", true], ["verb_ratio", "Verbes", true], ["adjective_ratio", "Adjectifs", true], ["adverb_ratio", "Adverbes", true], ["sentence_word_std_dev", "Diversité de longueurs de phrase (mots)", false], ["gzip_compression_ratio", "Compression gzip", true], ["relative_clause_ratio", "Relatives et subordonnées", true], ["nominal_sentence_ratio", "Phrases nominales", true], ["active_voice_ratio", "Voix active", true], ["metaphorical_comme_ratio", "Comparaisons métaphoriques", true], ["form_lemma_ratio", "Formes par lemme", false], ["hapax_ratio", "Mots employés une seule fois", true],
  ["word_count", "Mots", false], ["sentence_count", "Phrases", false], ["paragraph_count", "Paragraphes", false], ["avg_word_length", "Longueur moyenne des mots (caractères)", false], ["avg_sentence_length", "Longueur moyenne des phrases (caractères)", false], ["avg_sentence_word_count", "Longueur moyenne des phrases (mots)", false], ["median_sentence_length", "Longueur médiane des phrases (caractères)", false], ["sentence_length_p10", "Longueur P10 des phrases (caractères)", false], ["sentence_length_p90", "Longueur P90 des phrases (caractères)", false], ["paragraph_length_std_dev", "Écart-type des paragraphes (mots)", false], ["document_char_count", "Signes (caractères)", false],
];
const BURROWS_FIELDS = ["punctuation_per_300_words", "punctuation_diversity", "structural_diversity", "structural_rhythm", "sentence_start_diversity", "burstiness", "noun_verb_ratio", "filtered_repetition_rate", "stylistic_repetition_rate", "family_repetition_rate", "phonetic_repetition_rate", "absolute_repetition_rate", "function_word_ratio", "trigram_repetition", "moving_trigram_repetition", "noun_ratio", "verb_ratio", "adjective_ratio", "adverb_ratio", "present_participle_ratio", "past_participle_ratio", "simple_past_ratio", "literary_subjunctive_ratio", "negation_completeness_ratio", "negation_ratio", "periphrastic_future_ratio", "oral_familiarity_ratio", "classicism_score", "dialogue_ratio", "gzip_compression_ratio", "relative_clause_ratio", "nominal_sentence_ratio", "active_voice_ratio", "metaphorical_comme_ratio", "average_syntactic_depth", "form_lemma_ratio", "hapax_ratio", "sentence_word_std_dev", "sentence_length_amplitude", "sentence_length_std_dev", "emotion_word_ratio", "affect_verb_ratio", "exclamation_ratio", "exclamative_construction_ratio", "emotionality_score", "logical_connector_ratio", "abstract_noun_ratio", "gnomic_present_ratio", "narrative_past_ratio", "narrativity_score", "discursivite_score"];
const ALL_METRICS = [...RADAR, ...DETAILS.map(([key, label]) => [key, label])];
const TECHNICAL_KEYS = new Set(["word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length", "avg_sentence_word_count", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "document_char_count"]);
// L’écart-type brut reste disponible dans les données, mais la mesure #6
// affichée et indexée est bien la diversité locale (burstiness).
const REMOVED_KEYS = new Set(["avg_sentence_word_count"]);
const MENU_METRICS = ALL_METRICS.filter(([key], index, all) => !TECHNICAL_KEYS.has(key) && !REMOVED_KEYS.has(key) && all.findIndex(item => item[0] === key) === index);
let COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"];
let IA_COLOR = "#777777";
let data, chart, surfaceChart, distanceChart, mdsChart, evolutionCharts = [], corpusProfile = false, authorProfile = false, authorLimits = false, currentRadarTitle = "Radar";
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
  return `<h2>${escape(title.replace(/\*\*/g, ""))}</h2><p>${body}</p><p class="app-help-link"><button type="button" class="open-app-help">Aide de l’application</button></p>`;
}
function markdownToHtml(raw) {
  const escape = text => String(text).replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
  const lines = String(raw || "").split(/\r?\n/), output = [];
  let paragraph = [], list = false;
  const flush = () => { if (paragraph.length) { output.push(`<p>${paragraph.join(" ")}</p>`); paragraph = []; } };
  const closeList = () => { if (list) { output.push("</ul>"); list = false; } };
  for (const line of lines) {
    const heading = /^(#{1,3})\s+(.+)$/.exec(line.trim());
    const bullet = /^[-*]\s+(.+)$/.exec(line.trim());
    if (heading) { flush(); closeList(); output.push(`<h${heading[1].length}>${escape(heading[2])}</h${heading[1].length}>`); continue; }
    if (bullet) { flush(); if (!list) { output.push("<ul>"); list = true; } output.push(`<li>${escape(bullet[1])}</li>`); continue; }
    if (!line.trim()) { flush(); closeList(); continue; }
    closeList(); paragraph.push(escape(line.trim()));
  }
  flush(); closeList();
  return output.join("").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
let applicationHelpCache = null;
function showApplicationHelp() {
  const note = document.getElementById("metric-note"), target = document.getElementById("metric-note-text");
  if (!note || !target) return;
  const display = content => { target.innerHTML = markdownToHtml(content); note.hidden = false; target.scrollTop = 0; };
  if (applicationHelpCache) { display(applicationHelpCache); return; }
  fetch("app-help.md").then(response => response.text()).then(content => { applicationHelpCache = content; display(content); });
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
function burrowsContext(entities) {
  const corpusVectors = data.books.map(book => BURROWS_FIELDS.map(key => value(book, key)));
  const means = BURROWS_FIELDS.map((_, i) => { const values = corpusVectors.map(row => row[i]).filter(Number.isFinite); return values.reduce((sum, n) => sum + n, 0) / (values.length || 1); });
  const deviations = BURROWS_FIELDS.map((_, i) => { const values = corpusVectors.map(row => row[i]).filter(Number.isFinite), mean = means[i]; return Math.sqrt(values.reduce((sum, n) => sum + (n - mean) ** 2, 0) / (values.length || 1)); });
  const vectors = entities.map(entity => BURROWS_FIELDS.map((key, i) => { const n = value(entity, key); return Number.isFinite(n) && deviations[i] > 0 ? (n - means[i]) / deviations[i] : null; }));
  const distance = (left, right) => { const parts = left.map((n, i) => Number.isFinite(n) && Number.isFinite(right[i]) ? Math.abs(n - right[i]) : null).filter(Number.isFinite); return parts.length ? parts.reduce((sum, n) => sum + n, 0) / parts.length : 0; };
  return { vectors, distance };
}
function selected() { return [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle):checked")].map(x => data.books.find(b => b.id === Number(x.value))).filter(Boolean); }
function checkedMetrics() { return [...new Set([...document.querySelectorAll("#metrics input:checked")].map(x => metricKey(x.value)))]; }
function neighborhoodState() {
  const books = selected(), entities = authorProfile || authorLimits ? authorAverages(books) : books;
  const reference = document.getElementById("neighborhood-reference"), pinned = document.getElementById("neighborhood-pinned"), count = document.getElementById("neighborhood-count");
  const key = entity => entity ? `${entity.author || ""}\u0000${entity.title || ""}` : "";
  return { reference: key(entities[Number(reference?.value)]), pinned: key(entities[Number(pinned?.value)]), count: count?.value || "5" };
}
function saveNeighborhoodState() { localStorage.setItem("unshiter-neighborhood", JSON.stringify(neighborhoodState())); }
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
  drawDistances(books);
  drawMDS(books);
  drawNeighborhood(books);
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
  if (surfaceTitle) {
    const title = `Couverture stylistique${singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""}`;
    surfaceTitle.childNodes[0].textContent = `${title} `;
    surfaceTitle.dataset.exportTitle = title;
    surfaceBox.dataset.exportTitle = title;
  }
  surfaceChart = new Chart(document.getElementById("surfaces"), { type: "bar", data: { labels: sorted.map(x => x.label), datasets: [{ label: "Couverture stylistique", data: sorted.map(x => x.area), backgroundColor: sorted.map(x => `${x.color}b8`), borderColor: sorted.map(x => x.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => sorted[items[0]?.dataIndex]?.hover || "", label: () => "" } } }, scales: { x: { display: false, beginAtZero: true }, y: { grid: { display: false }, ticks: { font: context => ({ weight: isAI(sorted[context.index]?.author) ? "700" : "400" }) } } } } });
}
function drawDistances(books) {
  distanceChart?.destroy();
  const canvas = document.getElementById("distances");
  if (!canvas || books.length < 2) return;
  const entities = (authorProfile || authorLimits ? authorAverages(books) : books).map((entity, index) => ({ ...entity, __color: isAI(entity) ? IA_COLOR : COLORS[index % COLORS.length] }));
  const { vectors, distance } = burrowsContext(entities);
  const nearest = vectors.map((vector, index) => {
    const distances = vectors.map((other, otherIndex) => {
      if (index === otherIndex) return null;
      return distance(vector, other);
    }).filter(Number.isFinite);
    return distances.length ? Math.min(...distances) : 0;
  });
  const ordered = entities.map((entity, index) => ({ label: entity.title || entity.author || "Œuvre", distance: nearest[index], color: entity.__color, isAI: isAI(entity) })).sort((a, b) => a.distance - b.distance);
  const box = canvas.closest(".distance-box");
  if (box) box.style.height = `${Math.max(300, ordered.length * 30 + 90)}px`;
  distanceChart = new Chart(canvas, { type: "bar", data: { labels: ordered.map(item => item.label), datasets: [{ label: "Δ Burrows", data: ordered.map(item => item.distance), backgroundColor: ordered.map(item => `${item.color}b8`), borderColor: ordered.map(item => item.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: item => `Δ ${Number(item.raw).toFixed(2)}` } } }, scales: { x: { beginAtZero: true, title: { display: true, text: "Distance moyenne entre z-scores" } }, y: { grid: { display: false }, ticks: { font: context => ({ weight: ordered[context.index]?.isAI ? "700" : "400" }) } } } } });
}
function classicalMDS(entities) {
  const context = burrowsContext(entities), n = entities.length;
  if (n < 2) return { points: [], context };
  const d = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) d[i][j] = d[j][i] = context.distance(context.vectors[i], context.vectors[j]);
  const squared = d.map(row => row.map(value => value * value));
  const rowMeans = squared.map(row => row.reduce((sum, value) => sum + value, 0) / n);
  const colMeans = Array.from({ length: n }, (_, j) => squared.reduce((sum, row) => sum + row[j], 0) / n);
  const grandMean = rowMeans.reduce((sum, value) => sum + value, 0) / n;
  const matrix = squared.map((row, i) => row.map((value, j) => -0.5 * (value - rowMeans[i] - colMeans[j] + grandMean)));
  const eigen = source => { let vector = Array(n).fill(1 / Math.sqrt(n)); for (let step = 0; step < 80; step++) { const next = source.map(row => row.reduce((sum, value, i) => sum + value * vector[i], 0)); const norm = Math.sqrt(next.reduce((sum, value) => sum + value * value, 0)) || 1; vector = next.map(value => value / norm); } const transformed = source.map(row => row.reduce((sum, value, i) => sum + value * vector[i], 0)); const lambda = vector.reduce((sum, value, i) => sum + value * transformed[i], 0); return { lambda, vector }; };
  const first = eigen(matrix), deflated = matrix.map((row, i) => row.map((value, j) => value - first.lambda * first.vector[i] * first.vector[j])), second = eigen(deflated);
  const points = entities.map((entity, i) => ({ x: first.vector[i] * Math.sqrt(Math.max(first.lambda, 0)), y: second.vector[i] * Math.sqrt(Math.max(second.lambda, 0)), entity }));
  let error = 0, total = 0;
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) { const projected = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y); error += (d[i][j] - projected) ** 2; total += d[i][j] ** 2; }
  return { points, stress: total ? Math.sqrt(error / total) : 0, context };
}
function drawMDS(books) {
  const canvas = document.getElementById("mds"); if (!canvas) return;
  mdsChart?.destroy();
  const entities = authorProfile || authorLimits ? authorAverages(books) : books;
  const result = classicalMDS(entities), groups = {};
  const title = document.querySelector(".mds-box h2");
  if (title) {
    const text = `Carte stylistique MDS — ${BURROWS_FIELDS.length} mesures, ${entities.length} œuvres · stress ${result.stress.toFixed(2)}`;
    // Preserve the shared help button while updating only the visible title.
    if (title.firstChild?.nodeType === Node.TEXT_NODE) title.firstChild.textContent = `${text} `;
    else title.insertBefore(document.createTextNode(`${text} `), title.firstChild);
  }
  result.points.forEach((point, index) => { const author = point.entity.author || "Auteur inconnu"; (groups[author] ||= []).push({ x: point.x, y: point.y, label: point.entity.title || author, isAI: isAI(point.entity) }); });
  const datasets = Object.entries(groups).sort(([a], [b]) => authorCompare(a, b)).map(([author, points], index) => ({ label: author, data: points, backgroundColor: isAI(author) ? IA_COLOR : COLORS[index % COLORS.length], borderColor: isAI(author) ? IA_COLOR : COLORS[index % COLORS.length], pointRadius: 6 }));
  const xs = result.points.map(point => point.x), ys = result.points.map(point => point.y);
  const range = values => { const min = Math.min(...values, 0), max = Math.max(...values, 0), span = Math.max(max - min, 1); return { min: min - span * .30, max: max + span * .30 }; };
  const medoid = result.points.reduce((best, point, index, points) => {
    const score = points.reduce((sum, other) => sum + Math.hypot(point.x - other.x, point.y - other.y), 0);
    return !best || score < best.score ? { point, score } : best;
  }, null)?.point || { x: 0, y: 0 };
  const spread = values => Math.max(Math.max(...values) - Math.min(...values), 1);
  const xHalf = spread(xs) * .38, yHalf = spread(ys) * .38;
  const xRange = { min: medoid.x - xHalf, max: medoid.x + xHalf };
  const yRange = { min: medoid.y - yHalf, max: medoid.y + yHalf };
  mdsInitialRange = { x: { ...xRange }, y: { ...yRange } };
  mdsFocusDataset = null;
  mdsChart = new Chart(canvas, { type: "scatter", data: { datasets }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => items[0]?.raw?.label || "" } } }, scales: { x: { min: xRange.min, max: xRange.max, grid: { color: "#e4e1de" }, title: { display: true, text: "Dimension MDS 1" } }, y: { min: yRange.min, max: yRange.max, grid: { color: "#e4e1de" }, title: { display: true, text: "Dimension MDS 2" } } } } });
  let drag = null, mdsDragged = false;
  canvas.style.cursor = "grab";
  canvas.onpointerdown = event => { mdsDragged = false; drag = { x: event.clientX, y: event.clientY, xMin: mdsChart.options.scales.x.min, xMax: mdsChart.options.scales.x.max, yMin: mdsChart.options.scales.y.min, yMax: mdsChart.options.scales.y.max }; canvas.setPointerCapture(event.pointerId); canvas.style.cursor = "grabbing"; };
  canvas.onpointermove = event => {
    if (!drag) return;
    const xScale = mdsChart.scales.x, yScale = mdsChart.scales.y;
    const deltaX = event.clientX - drag.x, deltaY = event.clientY - drag.y;
    if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) mdsDragged = true;
    const dx = -deltaX * (drag.xMax - drag.xMin) / mdsChart.chartArea.width;
    const dy = deltaY * (drag.yMax - drag.yMin) / mdsChart.chartArea.height;
    mdsChart.options.scales.x.min = drag.xMin + dx; mdsChart.options.scales.x.max = drag.xMax + dx;
    mdsChart.options.scales.y.min = drag.yMin + dy; mdsChart.options.scales.y.max = drag.yMax + dy;
    mdsChart.update("none");
  };
  canvas.onpointerup = event => { drag = null; canvas.releasePointerCapture?.(event.pointerId); canvas.style.cursor = "grab"; };
  canvas.onclick = event => { if (mdsDragged) { mdsDragged = false; return; } const elements = mdsChart.getElementsAtEventForMode(event, "nearest", { intersect: false }, true); mdsFocusDataset = elements.length ? elements[0].datasetIndex : null; mdsChart.update(); };
}
function mdsZoom(factor) {
  if (!mdsChart) return;
  ["x", "y"].forEach(axis => {
    const scale = mdsChart.options.scales[axis];
    const center = (scale.min + scale.max) / 2;
    const half = (scale.max - scale.min) * factor / 2;
    scale.min = center - half;
    scale.max = center + half;
  });
  mdsChart.update();
}
function mdsReset() {
  if (!mdsChart || !mdsInitialRange) return;
  ["x", "y"].forEach(axis => {
    mdsChart.options.scales[axis].min = mdsInitialRange[axis].min;
    mdsChart.options.scales[axis].max = mdsInitialRange[axis].max;
  });
  mdsChart.update();
}
function downloadNeighborhoodTable(format = "png") {
  const table = document.querySelector("#neighborhood-table table");
  if (!table) return;
  const rows = [...table.rows].map(row => [...row.cells].map(cell => cell.textContent.trim()));
  const widths = rows[0]?.length === 3 ? [70, 520, 130] : [70, 420, 250, 130];
  const width = widths.reduce((sum, value) => sum + value, 0), rowHeight = 34, height = 75 + rows.length * rowHeight;
  const esc = text => String(text).replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[char]));
  const title = document.getElementById("neighborhood-verdict")?.textContent || "Voisinage stylistique";
  const cells = rows.map((row, rowIndex) => row.map((cell, columnIndex) => {
    const x = widths.slice(0, columnIndex).reduce((sum, value) => sum + value, 0);
    const y = 75 + rowIndex * rowHeight;
    return `<rect x="${x}" y="${y}" width="${widths[columnIndex]}" height="${rowHeight}" fill="${rowIndex % 2 ? "#faf8f6" : "white"}" stroke="#d8d1ca"/><text x="${x + 8}" y="${y + 22}" font-family="system-ui" font-size="14">${esc(cell)}</text>`;
  }).join("")).join("");
  const header = rows.length ? rows[0].map((cell, columnIndex) => { const x = widths.slice(0, columnIndex).reduce((sum, value) => sum + value, 0); return `<rect x="${x}" y="40" width="${widths[columnIndex]}" height="${rowHeight}" fill="#eee9e4" stroke="#cfc7c0"/><text x="${x + 8}" y="62" font-family="system-ui" font-size="14" font-weight="600">${esc(cell)}</text>`; }).join("") : "";
  const bodyRows = rows.slice(1).map((row, rowIndex) => row.map((cell, columnIndex) => { const x = widths.slice(0, columnIndex).reduce((sum, value) => sum + value, 0); const y = 75 + rowIndex * rowHeight; return `<rect x="${x}" y="${y}" width="${widths[columnIndex]}" height="${rowHeight}" fill="${rowIndex % 2 ? "#faf8f6" : "white"}" stroke="#d8d1ca"/><text x="${x + 8}" y="${y + 22}" font-family="system-ui" font-size="14">${esc(cell)}</text>`; }).join("")).join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="white"/><text x="12" y="25" font-family="system-ui" font-size="18" font-weight="600">${esc(title)}</text>${header}${bodyRows}</svg>`;
  const link = document.createElement("a");
  if (format === "svg") { link.href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })); link.download = "voisinage-stylistique.svg"; }
  else { const image = new Image(); image.onload = () => { const canvas = document.createElement("canvas"); canvas.width = width * 2; canvas.height = height * 2; const ctx = canvas.getContext("2d"); ctx.scale(2, 2); ctx.drawImage(image, 0, 0); link.href = canvas.toDataURL("image/png"); link.download = "voisinage-stylistique.png"; link.click(); URL.revokeObjectURL(image.src); }; image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`; return; }
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
Chart.register({ id: "mdsLabelsAndLinks", afterDatasetsDraw(instance) {
  if (instance.canvas?.id !== "mds") return;
  const ctx = instance.ctx;
  ctx.save();
  instance.data.datasets.forEach((dataset, datasetIndex) => {
    const meta = instance.getDatasetMeta(datasetIndex);
    const points = meta.data || [];
    if (points.length) {
      const center = {
        x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
        y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
      };
      const focused = mdsFocusDataset === datasetIndex;
      ctx.strokeStyle = dataset.borderColor || "#999";
      ctx.globalAlpha = focused ? .9 : .28;
      ctx.lineWidth = focused ? 4 : 1;
      ctx.beginPath();
      points.forEach(point => { ctx.moveTo(center.x, center.y); ctx.lineTo(point.x, point.y); });
      ctx.stroke();
      // Centroïde du réseau : la moyenne des coordonnées des œuvres de l’auteur.
      ctx.globalAlpha = 1;
      ctx.fillStyle = dataset.borderColor || "#777";
      ctx.beginPath(); ctx.arc(center.x, center.y, focused ? 6 : 4, 0, Math.PI * 2); ctx.fill();
      // Le nom du réseau n'est utile que lorsqu'il regroupe plusieurs
      // œuvres. Pour une œuvre isolée, le titre du point suffit et évite le
      // chevauchement auteur/titre.
      if (points.length > 1) {
        ctx.font = focused ? "600 14px system-ui" : "12px system-ui";
        ctx.fillStyle = dataset.borderColor || "#3f3a36";
        ctx.fillText(dataset.label, center.x + 9, center.y - 9);
      }
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#3f3a36";
    ctx.font = "12px system-ui";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    points.forEach((point, index) => {
      const label = dataset.data[index]?.label;
      if (label) ctx.fillText(label, point.x + 8, point.y - 8);
    });
  });
  ctx.restore();
} });
Chart.register({ id: "distanceReference", afterDraw(instance) {
  const references = instance.options.plugins?.distanceReference?.values || [];
  if (!references.length) return;
  const scale = instance.scales.x, ctx = instance.ctx;
  ctx.save(); ctx.setLineDash([6, 4]); ctx.font = "12px system-ui";
  references.forEach((reference, index) => {
    if (!Number.isFinite(reference.value)) return;
    const x = scale.getPixelForValue(reference.value);
    ctx.strokeStyle = index ? "#3478b8" : "#d13c36";
    ctx.beginPath(); ctx.moveTo(x, instance.chartArea.top); ctx.lineTo(x, instance.chartArea.bottom); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = ctx.strokeStyle; ctx.fillText(`${reference.label} : ${reference.value.toFixed(2)}`, x + 5, instance.chartArea.top + 16 + index * 17); ctx.setLineDash([6, 4]);
  });
  ctx.restore();
} });
let neighborhoodChart, mdsInitialRange, mdsFocusDataset = null;
function drawNeighborhood(books) {
  neighborhoodChart?.destroy();
  const authorEntities = authorProfile || authorLimits;
  const entities = authorEntities ? authorAverages(books) : books, select = document.getElementById("neighborhood-reference");
  if (!entities.length) return;
  // Le mode (œuvres ou auteurs) fait partie de la signature : deux sélections
  // peuvent contenir les mêmes textes mais produire des références différentes.
  const referenceSignature = `${authorEntities ? "authors" : "works"}\u0002${entities.map(entity => `${entity.author || ""}\u0000${entity.title || ""}`).join("\u0001")}`;
  const entityKey = entity => `${entity.author || ""}\u0000${entity.title || ""}`;
  if (select && select.dataset.signature !== referenceSignature) {
    const oldKey = entities[Number(select.value)] ? entityKey(entities[Number(select.value)]) : "";
    const escape = text => String(text ?? "").replace(/[&<>\"]/g, "");
    if (authorEntities) {
      // En mode Auteurs, ne pas afficher des œuvres fictives ("Œuvre 1").
      select.innerHTML = entities.map((entity, index) => `<option value="${index}">${escape(entity.author || "Auteur inconnu")}</option>`).join("");
    } else {
      const grouped = entities.reduce((groups, entity, index) => {
        const author = entity.author || "Auteur inconnu";
        (groups[author] ||= []).push({ entity, index });
        return groups;
      }, {});
      select.innerHTML = Object.entries(grouped).sort(([a], [b]) => authorCompare(a, b)).map(([author, rows]) => {
        rows.sort((a, b) => {
          const dateA = Date.parse(a.entity.publication_date || "") || Infinity;
          const dateB = Date.parse(b.entity.publication_date || "") || Infinity;
          return dateA - dateB || (a.entity.title || "").localeCompare(b.entity.title || "", "fr", { sensitivity: "base" });
        });
        return `<optgroup label="${escape(author)}">${rows.map(({ entity, index }) => `<option value="${index}">${escape(entity.title || `Œuvre ${index + 1}`)}${entity.publication_date ? ` (${String(entity.publication_date).slice(0, 4)})` : ""}</option>`).join("")}</optgroup>`;
      }).join("");
    }
    const saved = JSON.parse(localStorage.getItem("unshiter-neighborhood") || "null");
    const restored = entities.findIndex(entity => entityKey(entity) === (saved?.reference || oldKey));
    select.value = String(restored >= 0 ? restored : 0);
    select.dataset.signature = referenceSignature;
  }
  const referenceIndex = Number(select?.value || 0), context = burrowsContext(entities), reference = context.vectors[referenceIndex];
  const corpusContext = burrowsContext(data.books);
  const corpusDistances = [];
  for (let i = 0; i < corpusContext.vectors.length; i++) for (let j = i + 1; j < corpusContext.vectors.length; j++) corpusDistances.push(corpusContext.distance(corpusContext.vectors[i], corpusContext.vectors[j]));
  const percentile = distance => corpusDistances.length ? 100 * corpusDistances.filter(value => value >= distance).length / corpusDistances.length : 50;
  const allRows = entities.map((entity, index) => ({ entity, index, rank: null, distance: index === referenceIndex ? null : context.distance(reference, context.vectors[index]) })).filter(row => row.distance != null);
  allRows.forEach(row => { row.percentile = percentile(row.distance); });
  // Le voisinage est défini par les cinq percentiles les plus élevés, pas par
  // les cinq premières lignes d'une liste dans un ordre implicite.
  allRows.sort((a, b) => b.percentile - a.percentile || a.distance - b.distance);
  allRows.forEach((row, index) => { row.rank = index + 1; });
  const pinnedSelect = document.getElementById("neighborhood-pinned");
  if (pinnedSelect && pinnedSelect.dataset.signature !== referenceSignature) {
    const oldPinnedKey = entities[Number(pinnedSelect.value)] ? entityKey(entities[Number(pinnedSelect.value)]) : "";
    const escape = text => String(text ?? "").replace(/[&<>\"]/g, "");
    let pinnedOptions;
    if (authorEntities) {
      pinnedOptions = entities.map((entity, index) => `<option value="${index}">${escape(entity.author || "Auteur inconnu")}</option>`).join("");
    } else {
      const pinnedGroups = entities.reduce((groups, entity, index) => { const author = entity.author || "Auteur inconnu"; (groups[author] ||= []).push({ entity, index }); return groups; }, {});
      pinnedOptions = Object.entries(pinnedGroups).sort(([a], [b]) => authorCompare(a, b)).map(([author, rows]) => {
        rows.sort((a, b) => (Date.parse(a.entity.publication_date || "") || Infinity) - (Date.parse(b.entity.publication_date || "") || Infinity));
        return `<optgroup label="${escape(author)}">${rows.map(({ entity, index }) => `<option value="${index}">${escape(entity.title || `Œuvre ${index + 1}`)}</option>`).join("")}</optgroup>`;
      }).join("");
    }
    pinnedSelect.innerHTML = `<option value="">Aucune œuvre épinglée</option>${pinnedOptions}`;
    const saved = JSON.parse(localStorage.getItem("unshiter-neighborhood") || "null");
    const restoredPinned = entities.findIndex(entity => entityKey(entity) === (saved?.pinned || oldPinnedKey));
    if (restoredPinned >= 0) pinnedSelect.value = String(restoredPinned);
    pinnedSelect.dataset.signature = referenceSignature;
  }
  const countSelect = document.getElementById("neighborhood-count");
  const selectedCount = countSelect?.value || "5";
  const neighborCount = selectedCount === "all" ? allRows.length : Math.max(5, Number(selectedCount) || 5);
  const topRows = allRows.slice(0, neighborCount);
  const pinnedRaw = pinnedSelect?.value || "";
  const pinnedIndex = pinnedRaw === "" ? -1 : Number(pinnedRaw);
  const pinned = Number.isInteger(pinnedIndex) && pinnedIndex >= 0 && pinnedIndex !== referenceIndex ? allRows.find(row => row.index === pinnedIndex) : null;
  const rows = [...topRows];
  // L'épinglée garde son rang naturel. Elle est ajoutée seulement si elle ne
  // figure pas déjà dans les voisins affichés, puis la liste reste triée.
  if (pinned && !rows.some(row => row.index === pinned.index)) rows.push(pinned);
  rows.sort((left, right) => left.rank - right.rank);
  const sameAuthor = entities.map((entity, index) => entity.author === entities[referenceIndex].author && index !== referenceIndex ? context.distance(reference, context.vectors[index]) : null).filter(Number.isFinite);
  const internalDistance = sameAuthor.length ? sameAuthor.reduce((sum, n) => sum + n, 0) / sameAuthor.length : null;
  const internal = Number.isFinite(internalDistance) ? percentile(internalDistance) : null;
  const median = 50;
  const authorNames = [...new Set(entities.map(entity => entity.author || "Auteur inconnu"))].sort(authorCompare);
  const authorColors = Object.fromEntries(authorNames.map((author, index) => [author, isAI(author) ? IA_COLOR : COLORS[index % COLORS.length]]));
  const referenceAuthor = entities[referenceIndex].author || "Auteur inconnu";
  const surname = author => (author || "Auteur inconnu").trim().split(/\s+/).at(-1);
  const counts = {};
  const percentileSums = {};
  topRows.forEach(row => { const author = surname(row.entity.author); counts[author] = (counts[author] || 0) + 1; percentileSums[author] = (percentileSums[author] || 0) + row.percentile; });
  // Le classement se fait sur la moyenne des percentiles de chaque auteur.
  const podium = Object.entries(counts).sort((a, b) => percentileSums[b[0]] / b[1] - percentileSums[a[0]] / a[1] || a[0].localeCompare(b[0], "fr"));
  // En mode auteurs, chaque ligne est déjà une moyenne d'auteur : il ne faut
  // surtout pas recompter des œuvres pour fabriquer l'attribution. Le rang
  // est donc directement celui des auteurs voisins.
  const attribution = authorEntities
    ? topRows.map((row, index) => `${index + 1} ${surname(row.entity.author)}`).join(", ")
    : podium.map(([author], index) => `${index + 1} ${author}`).join(", ");
  const referenceWorkTitle = authorEntities ? referenceAuthor : (entities[referenceIndex].title || referenceAuthor);
  const verdictText = authorEntities
    ? `Voisinage stylistique de ${referenceWorkTitle}`
    : `Voisinage stylistique de ${referenceWorkTitle} : ${attribution || "aucun voisin"}`;
  const verdict = document.getElementById("neighborhood-verdict");
  if (verdict) { verdict.textContent = verdictText; verdict.dataset.exportTitle = verdictText; }
  const table = document.getElementById("neighborhood-table");
  const escapeHtml = text => String(text ?? "").replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[char]));
  if (table) {
    const columns = authorEntities ? "<th>Rang</th><th>Auteur</th><th>Percentile</th>" : "<th>Rang</th><th>Œuvre</th><th>Auteur</th><th>Percentile</th>";
    const body = rows.map(row => {
      const pinnedClass = pinned?.index === row.index ? " class=\"pinned-row\"" : "";
      return authorEntities
        ? `<tr${pinnedClass}><td>${row.rank}</td><td>${escapeHtml(row.entity.author || "Auteur inconnu")}</td><td>${row.percentile.toFixed(0)} %</td></tr>`
        : `<tr${pinnedClass}><td>${row.rank}</td><td>${escapeHtml(row.entity.title || "Œuvre")}</td><td>${escapeHtml(row.entity.author || "Auteur inconnu")}</td><td>${row.percentile.toFixed(0)} %</td></tr>`;
    }).join("");
    table.innerHTML = `<table><thead><tr>${columns}</tr></thead><tbody>${body}</tbody></table>`;
  }
  const box = document.querySelector(".neighborhood-box"); if (box) box.style.height = "auto";
}
function drawEvolution(selectedBooks) {
  evolutionCharts.forEach(item => item.destroy());
  evolutionCharts = [];
  const authorMode = Boolean(authorProfile);
  const books = [...(authorMode ? authorEvolutionEntities(selectedBooks) : selectedBooks)].filter(book => authorMode || (book.publication_date && !Number.isNaN(Date.parse(book.publication_date)))).sort((a, b) => authorMode ? String(a.author).localeCompare(String(b.author), "fr") : Date.parse(a.publication_date) - Date.parse(b.publication_date));
  const definitions = checkedMetrics().map(key => [key, metricLabel(key)]).filter(Boolean);
  const container = document.getElementById("evolution-charts");
  container.innerHTML = "";
  definitions.forEach(([key, label], i) => {
    const plotBooks = authorMode
      // L'ordre suit le score effectivement affiché sur l'axe. Ainsi une
      // mesure inversée (par ex. la sparsité des adverbes) est naturellement
      // présentée dans le sens de son affichage, et non dans celui de sa
      // valeur brute.
      ? [...books].sort((a, b) => (scale(key, value(a, key)) ?? Infinity) - (scale(key, value(b, key)) ?? Infinity))
      : books;
    const id = `evolution-${i}`;
    const evolutionTitle = `${label}${!authorMode && singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""}`;
    const noteId = data.metric_note_ids?.[key] ? data.note_ids?.[data.metric_note_ids[key]] : null;
    const help = noteId == null ? "" : ` <button class="metric-help help" data-key="${publicMetricId(key)}" type="button" aria-label="Afficher l’explication">?</button>`;
    container.insertAdjacentHTML("beforeend", `<div class="evolution-chart chart-frame"><h3>${evolutionTitle}${help}</h3><canvas id="${id}"></canvas><select class="chart-download" data-canvas="${id}" aria-label="Télécharger ${evolutionTitle}"><option value="png">PNG</option><option value="svg">SVG</option></select></div>`);
    const lineColor = books.every(isAI) ? IA_COLOR : COLORS[i % COLORS.length];
    const lineChart = new Chart(document.getElementById(id), { type: "line", data: { labels: plotBooks.map(book => authorMode ? book.author : book.title), datasets: [{ label, data: plotBooks.map(book => { const n = value(book, key); return n == null ? null : scale(key, n); }), borderColor: lineColor, backgroundColor: lineColor, tension: .25, pointRadius: 3, spanGaps: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { display: false }, grid: { color: "#ccd1d5" } }, x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45, font: context => ({ weight: isAI(plotBooks[context.index]) ? "700" : "400" }) } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => authorMode ? `${plotBooks[items[0].dataIndex].author} · ${format(value(plotBooks[items[0].dataIndex], key), key)}` : `${plotBooks[items[0].dataIndex].publication_date.slice(0, 4)} · ${plotBooks[items[0].dataIndex].title}` } } } } });
    lineChart.$years = authorMode ? [] : plotBooks.map(book => book.publication_date.slice(0, 4));
    lineChart.$pointLabels = authorMode ? plotBooks.map(book => format(value(book, key), key)) : [];
    lineChart.$pointEntities = plotBooks;
    evolutionCharts.push(lineChart);
  });
}
function authorEvolutionEntities(books) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).map(([author, authorBooks]) => {
    const dated = authorBooks.filter(book => book.publication_date && !Number.isNaN(Date.parse(book.publication_date))).sort((a, b) => Date.parse(a.publication_date) - Date.parse(b.publication_date));
    const stats = {};
    for (const [key] of ALL_METRICS) {
      const values = authorBooks.map(book => value(book, key)).filter(Number.isFinite);
      if (values.length) stats[key] = values.reduce((sum, n) => sum + n, 0) / values.length;
    }
    return { author, title: author, publication_date: dated[0]?.publication_date || "", analyses: [{ stats }] };
  });
}
function authorMedians(books) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).map(([author, authorBooks]) => {
    const stats = {};
    for (const [key] of ALL_METRICS) {
      const values = authorBooks.map(book => value(book, key)).filter(Number.isFinite).sort((a, b) => a - b);
      if (values.length) stats[key] = values[Math.floor((values.length - 1) / 2)];
    }
    return { author, title: author, analyses: [{ stats }] };
  });
}
Chart.register({ id: "publicationYears", afterDatasetsDraw(instance) { const meta = instance.getDatasetMeta(0); const labels = instance.$pointLabels?.length ? instance.$pointLabels : (instance.$years || []); const ctx = instance.ctx; const limit = instance.chartArea.top + instance.chartArea.height * .75; ctx.save(); ctx.fillStyle = "#6f6962"; ctx.textAlign = "center"; meta.data.forEach((point, i) => { if (labels[i]) { ctx.font = `${isAI(instance.$pointEntities?.[i]) ? "700" : "400"} 11px system-ui`; ctx.fillText(labels[i], point.x, point.y < limit ? point.y + 15 : point.y - 9); } }); ctx.restore(); } });
function chartExportTitle(canvas, name) {
  const frame = canvas?.closest(".chart-frame");
  if (frame?.dataset.exportTitle) return frame.dataset.exportTitle;
  const titleElement = frame?.querySelector("h3, h2");
  if (!titleElement) return name;
  const titleClone = titleElement.cloneNode(true);
  titleClone.querySelectorAll("button, select").forEach(control => control.remove());
  return titleClone.textContent.replace(/\s+/g, " ").trim() || name;
}
function radarLegendEntries() {
  const domEntries = [...document.querySelectorAll("#radar-legend span")].map(item => ({
    label: item.textContent.trim(),
    color: item.querySelector("i")?.style.backgroundColor || "#777777",
  })).filter(item => item.label);
  if (domEntries.length) return domEntries;
  return (chart?.data?.datasets || []).map(dataset => ({
    label: String(dataset.label || "").trim(),
    color: dataset.borderColor || "#777777",
  })).filter(item => item.label);
}
function radarLegendRows(width, measure) {
  const entries = radarLegendEntries();
  const gap = 24, maxWidth = Math.max(180, width - 24), rows = [];
  let row = [], rowWidth = 0;
  entries.forEach(item => {
    const itemWidth = 29 + 9 + measure(item.label);
    if (row.length && rowWidth + gap + itemWidth > maxWidth) {
      rows.push({ items: row, width: rowWidth }); row = []; rowWidth = 0;
    }
    row.push({ ...item, width: itemWidth });
    rowWidth += (row.length > 1 ? gap : 0) + itemWidth;
  });
  if (row.length) rows.push({ items: row, width: rowWidth });
  return { rows, gap };
}
function radarLegendSvg(width, y) {
  const layout = radarLegendRows(width, label => 7 * label.length);
  if (!layout.rows.length) return { markup: "", height: 0 };
  const markup = layout.rows.map((line, rowIndex) => {
    let x = (width - line.width) / 2;
    const lineY = y + rowIndex * 25;
    return line.items.map(item => {
      const current = `<line x1="${x.toFixed(1)}" y1="${lineY}" x2="${(x + 22).toFixed(1)}" y2="${lineY}" stroke="${item.color}" stroke-width="4"/><text x="${(x + 29).toFixed(1)}" y="${lineY + 5}" font-family="system-ui" font-size="13">${item.label.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char]))}</text>`;
      x += item.width + layout.gap;
      return current;
    }).join("");
  }).join("");
  return { markup, height: layout.rows.length * 25 + 9 };
}
function downloadCanvas(canvas, name, format = "png") {
  if (!canvas) return;
  const png = canvas.toDataURL("image/png");
  if (format === "svg") {
    if (name === "radar") {
      const legend = radarLegendSvg(canvas.width, canvas.height + 22);
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height + legend.height}" viewBox="0 0 ${canvas.width} ${canvas.height + legend.height}"><rect width="100%" height="100%" fill="white"/><image href="${png}" x="0" y="0" width="${canvas.width}" height="${canvas.height}"/><g>${legend.markup}</g></svg>`;
      const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
    }
    const title = chartExportTitle(canvas, name);
    const safeTitle = title.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
    const exportHeight = canvas.height + 64;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${exportHeight}" viewBox="0 0 ${canvas.width} ${exportHeight}"><rect width="100%" height="100%" fill="white"/><text x="${canvas.width / 2}" y="38" text-anchor="middle" font-family="system-ui" font-size="28" font-weight="600">${safeTitle}</text><image href="${png}" x="0" y="64" width="${canvas.width}" height="${canvas.height}"/></svg>`;
    const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
  }
  if (name === "radar" && radarLegendEntries().length) {
    const legend = radarLegendEntries(), composed = document.createElement("canvas");
    const measureContext = document.createElement("canvas").getContext("2d"); measureContext.font = "13px system-ui";
    const layout = radarLegendRows(canvas.width, label => measureContext.measureText(label).width);
    const extraHeight = layout.rows.length * 25 + 9;
    composed.width = canvas.width; composed.height = canvas.height + extraHeight;
    const context = composed.getContext("2d"); context.fillStyle = "#fff"; context.fillRect(0, 0, composed.width, composed.height);
    context.drawImage(canvas, 0, 0);
    context.font = "13px system-ui"; context.textBaseline = "middle";
    layout.rows.forEach((line, rowIndex) => { let x = (canvas.width - line.width) / 2; const y = canvas.height + 18 + rowIndex * 25; line.items.forEach(item => { context.fillStyle = item.color; context.fillRect(x, y, 22, 4); context.fillStyle = "#222"; context.fillText(item.label, x + 29, y + 2); x += item.width + layout.gap; }); });
    const link = document.createElement("a"); link.download = `${name}.png`; link.href = composed.toDataURL("image/png"); document.body.appendChild(link); link.click(); link.remove(); return;
  }
  const a = document.createElement("a"); a.download = `${name}.png`; a.href = png; document.body.appendChild(a); a.click(); a.remove();
}
function renderTables(books) {
  const tableBooks = authorProfile || authorLimits ? authorMedians(books) : books;
  const details = DETAILS.filter(([key]) => !REMOVED_KEYS.has(key) && !TECHNICAL_KEYS.has(key));
  const technical = DETAILS.filter(([key]) => TECHNICAL_KEYS.has(key));
  const technicalCharacterIndex = technical.findIndex(([key]) => key === "document_char_count");
  const technicalWordsIndex = technical.findIndex(([key]) => key === "word_count");
  if (technicalCharacterIndex >= 0 && technicalWordsIndex >= 0) technical.splice(technicalWordsIndex, 0, technical.splice(technicalCharacterIndex, 1)[0]);
  const characterIndex = details.findIndex(([key]) => key === "document_char_count");
  const wordsIndex = details.findIndex(([key]) => key === "word_count");
  if (characterIndex >= 0 && wordsIndex >= 0 && characterIndex > wordsIndex) details.splice(wordsIndex, 0, details.splice(characterIndex, 1)[0]);
  document.getElementById("tables").innerHTML = `<div class="table-wrap"><h2>Tableau 1 · synthèse</h2>${table(tableBooks, RADAR)}</div><div class="table-wrap"><h2>Tableau 2 · détails</h2>${table(tableBooks, details)}</div><div class="table-wrap"><h2>Tableau 3 · données objectives</h2>${table(tableBooks, technical)}</div>`;
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
    const noteId = noteEntry(key).id;
    const note = noteId == null ? "" : ` <button class="table-note-help metric-help" type="button" data-note-id="${noteId}" data-key="${publicMetricId(key)}" aria-label="Afficher la note">?</button>`;
    return `<tr><td>${metricLabel(key)}${note}</td>${displayed.map(n => `<td>${format(n, key)}</td>`).join("")}<td>${sigma == null ? "—" : `${sigma.toFixed(1)} %`}</td></tr>`;
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
  const distanceTitle = document.querySelector(".distance-box h2");
  if (distanceTitle) {
    distanceTitle.childNodes[0].textContent = "Singularité ";
    if (!distanceTitle.querySelector(".metric-help")) distanceTitle.insertAdjacentHTML("beforeend", ' <button class="metric-help help" data-note-id="43" type="button" aria-label="Afficher l’explication">?</button>');
  }
  const distanceBox = document.querySelector(".distance-box");
  if (distanceBox && !document.querySelector(".mds-box")) distanceBox.insertAdjacentHTML("afterend", '<section class="mds-box chart-frame" hidden><h2>Carte stylistique MDS <button class="metric-help help" data-note-id="44" type="button" aria-label="Afficher l’explication">?</button></h2><div class="mds-controls" aria-label="Navigation de la carte"><button type="button" id="mds-zoom-out" aria-label="Dézoomer">−</button><button type="button" id="mds-zoom-in" aria-label="Zoomer">+</button><button type="button" id="mds-reset" aria-label="Réinitialiser la vue">Réinitialiser</button></div><canvas id="mds"></canvas><select class="chart-download" data-canvas="mds" aria-label="Télécharger la carte stylistique MDS"><option value="png">PNG</option><option value="svg">SVG</option></select></section><section class="neighborhood-box chart-frame"><h2>Voisinage stylistique <button class="metric-help help" data-note-id="45" type="button" aria-label="Afficher l’explication">?</button></h2><label class="reference-select">Œuvre de référence <select id="neighborhood-reference"></select></label><label class="reference-select">Œuvre épinglée <select id="neighborhood-pinned"><option value="">Aucune œuvre épinglée</option></select></label><label class="reference-select">Nombre de voisins <select id="neighborhood-count"><option value="5" selected>5</option><option value="10">10</option><option value="15">15</option><option value="20">20</option><option value="25">25</option><option value="30">30</option><option value="35">35</option><option value="40">40</option><option value="45">45</option><option value="all">Tous</option></select></label><h3 id="neighborhood-verdict" class="neighborhood-verdict"></h3><div id="neighborhood-table" class="neighborhood-table"></div><button type="button" id="neighborhood-download" class="table-download">Télécharger le tableau</button></section><div class="bonus-links"><button type="button" id="show-distance" class="bonus-link">Afficher Singularité (bonus)</button><button type="button" id="show-mds" class="bonus-link">Afficher la carte MDS (bonus)</button></div>');
  if (distanceBox) distanceBox.hidden = true;
  const bonusLinks = document.querySelector(".bonus-links");
  const tablesBlock = document.getElementById("tables");
  if (bonusLinks && tablesBlock) tablesBlock.parentNode.appendChild(bonusLinks);
  const mdsBox = document.querySelector(".mds-box");
  if (bonusLinks && distanceBox) bonusLinks.before(distanceBox);
  if (bonusLinks && mdsBox) bonusLinks.before(mdsBox);
  document.getElementById("show-distance")?.replaceChildren(document.createTextNode("Singularité"));
  document.getElementById("show-mds")?.replaceChildren(document.createTextNode("Carte MDS"));
  const oldTableDownload = document.getElementById("neighborhood-download");
  if (oldTableDownload?.tagName === "BUTTON") {
    const tableDownload = document.createElement("select"); tableDownload.id = "neighborhood-download"; tableDownload.className = "chart-download table-download"; tableDownload.dataset.table = "neighborhood-table"; tableDownload.setAttribute("aria-label", "Télécharger le tableau"); tableDownload.innerHTML = '<option value="" selected>Télécharger le tableau</option><option value="png">PNG</option><option value="svg">SVG</option>'; oldTableDownload.replaceWith(tableDownload); document.getElementById("neighborhood-table")?.before(tableDownload);
  }
  document.getElementById("show-distance")?.addEventListener("click", event => { if (distanceBox) { const show = distanceBox.hidden; distanceBox.hidden = !show; if (show && mdsBox) { mdsBox.hidden = true; document.getElementById("show-mds").textContent = "Carte MDS"; } event.currentTarget.textContent = distanceBox.hidden ? "Singularité" : "Masquer Singularité"; } });
  document.getElementById("show-mds")?.addEventListener("click", event => { const box = document.querySelector(".mds-box"); if (box) { const show = box.hidden; box.hidden = !show; if (show && distanceBox) { distanceBox.hidden = true; document.getElementById("show-distance").textContent = "Singularité"; } event.currentTarget.textContent = box.hidden ? "Carte MDS" : "Masquer Carte MDS"; if (!box.hidden) { mdsChart?.resize(); mdsChart?.update(); } } });
  document.getElementById("mds-zoom-out")?.addEventListener("click", () => mdsZoom(1.25));
  document.getElementById("mds-zoom-in")?.addEventListener("click", () => mdsZoom(.8));
  document.getElementById("mds-reset")?.addEventListener("click", mdsReset);
  const neighborhoodCount = document.getElementById("neighborhood-count");
  if (neighborhoodCount) neighborhoodCount.innerHTML = [5, 10, 15, 20, 25, 30, 35, 40, 45].map(value => `<option value="${value}"${value === 5 ? " selected" : ""}>${value}</option>`).join("") + '<option value="all">Tous</option>';
  const savedNeighborhood = JSON.parse(localStorage.getItem("unshiter-neighborhood") || "null");
  if (savedNeighborhood?.count && neighborhoodCount.querySelector(`option[value="${savedNeighborhood.count}"]`)) neighborhoodCount.value = savedNeighborhood.count;
  document.getElementById("neighborhood-reference")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); });
  document.getElementById("neighborhood-pinned")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); });
  document.getElementById("neighborhood-count")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); });
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
  const updateClearBooksLabel = () => {
    const booksInputs = [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle)")];
    clearBooks.textContent = booksInputs.length && booksInputs.every(input => !input.checked) ? "Tout cocher" : "Tout décocher";
  };
  clearBooks.addEventListener("click", () => {
    const booksInputs = [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle)")];
    const check = booksInputs.every(input => !input.checked);
    booksInputs.forEach(input => { input.checked = check; });
    document.querySelectorAll(".author-toggle").forEach(toggle => { toggle.checked = check; });
    localStorage.setItem("unshiter-books", JSON.stringify(check ? data.books.map(book => book.id) : []));
    updateClearBooksLabel();
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
    button.addEventListener("click", () => { const preset = presets[name]; localStorage.setItem("unshiter-books", JSON.stringify(preset.books)); localStorage.setItem("unshiter-metrics", JSON.stringify(preset.metrics)); localStorage.setItem("unshiter-flipped", JSON.stringify(preset.flipped || [])); localStorage.setItem("unshiter-neighborhood", JSON.stringify(preset.neighborhood || {})); localStorage.setItem("unshiter-view-mode", preset.view_mode || "works"); location.reload(); }); presetList.appendChild(button);
  });
  presetBox.querySelector("#config-save").addEventListener("click", () => {
    const name = window.prompt("Nom de la configuration :")?.trim();
    if (!name) return;
    Object.keys(presets).filter(existing => existing.toLocaleLowerCase() === name.toLocaleLowerCase()).forEach(existing => delete presets[existing]);
    saveNeighborhoodState();
    presets[name] = { books: selected().map(book => book.id), metrics: checkedMetrics().map(publicMetricId), flipped: [...flippedAxes].map(publicMetricId), neighborhood: JSON.parse(localStorage.getItem("unshiter-neighborhood") || "null"), view_mode: authorProfile ? "authors" : authorLimits ? "author-limits" : corpusProfile ? "limits" : "works" };
    localStorage.setItem("unshiter-presets", JSON.stringify(presets));
    location.reload();
  });
  document.querySelectorAll("#authors input, #metrics input").forEach(x => x.addEventListener("change", () => { localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); localStorage.setItem("unshiter-metrics", JSON.stringify(checkedMetrics().map(publicMetricId))); updateClearBooksLabel(); draw(); }));
  document.querySelectorAll(".author-toggle").forEach(x => x.addEventListener("change", () => { document.querySelectorAll(`#${x.dataset.target} input`).forEach(b => b.checked = x.checked); localStorage.setItem("unshiter-books", JSON.stringify(selected().map(b => b.id))); updateClearBooksLabel(); draw(); }));
  updateClearBooksLabel();
  document.addEventListener("change", event => { const select = event.target.closest(".chart-download"); if (select) { if (select.dataset.table) downloadNeighborhoodTable(select.value); else downloadCanvas(document.getElementById(select.dataset.canvas), select.dataset.canvas, select.value); select.selectedIndex = -1; } });
  const noteClose = document.getElementById("metric-note-close");
  if (noteClose) noteClose.addEventListener("click", () => { document.getElementById("metric-note").hidden = true; });
  document.addEventListener("click", event => { if (event.target.closest(".open-app-help")) { event.preventDefault(); showApplicationHelp(); } });
  document.addEventListener("click", event => { const button = event.target.closest(".metric-help, .metric-flip, .table-note-help"); if (!button) return; event.preventDefault(); event.stopPropagation(); const note = document.getElementById("metric-note"); if (button.classList.contains("table-note-help")) { document.getElementById("metric-note-text").innerHTML = renderNote(Number(button.dataset.noteId)); note.hidden = false; return; } const key = metricKey(button.dataset.key); if (button.classList.contains("metric-help")) { const id = button.dataset.noteId || noteEntry(key).id; document.getElementById("metric-note-text").innerHTML = id == null ? "<p>Note non référencée.</p>" : renderNote(id); note.hidden = false; } else { flippedAxes.has(key) ? flippedAxes.delete(key) : flippedAxes.add(key); localStorage.setItem("unshiter-flipped", JSON.stringify([...flippedAxes].map(publicMetricId))); const row = button.closest(".metric-row"); row.querySelector("span").textContent = metricLabel(key); draw(); } });
  const limitsButton = document.getElementById("corpus-profile"), authorsButton = document.getElementById("author-profile"), authorLimitsButton = document.getElementById("author-limits"), worksButton = document.getElementById("works-profile");
  const exportBox = document.createElement("div"); exportBox.className = "prompt-exports";
  const promptButton = document.createElement("button"); promptButton.type = "button"; promptButton.id = "export-style-prompt"; promptButton.textContent = "Prompt d’analyse"; exportBox.appendChild(promptButton); promptButton.addEventListener("click", exportStylePrompt);
  const promptFilesButton = document.createElement("button"); promptFilesButton.type = "button"; promptFilesButton.id = "export-style-files"; promptFilesButton.textContent = "Données pour analyse"; exportBox.appendChild(promptFilesButton); promptFilesButton.addEventListener("click", exportPromptAndData);
  document.querySelector("aside")?.appendChild(exportBox);
  const savedViewMode = localStorage.getItem("unshiter-view-mode") || "works";
  if (savedViewMode === "authors") { authorProfile = true; corpusProfile = false; authorLimits = false; }
  else if (savedViewMode === "author-limits") { authorProfile = false; corpusProfile = true; authorLimits = true; }
  else if (savedViewMode === "limits") { authorProfile = false; corpusProfile = true; authorLimits = false; }
  worksButton.hidden = true; authorsButton.hidden = false;
  const showWorksMode = () => { limitsButton.hidden = false; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = true; };
  const showLimitsMode = () => { limitsButton.hidden = true; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = false; };
  if (authorProfile) { limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; }
  else if (authorLimits) { limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = true; worksButton.hidden = false; }
  else if (corpusProfile) showLimitsMode();
  limitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = false; localStorage.setItem("unshiter-view-mode", "limits"); showLimitsMode(); draw(); });
  authorsButton.addEventListener("click", () => { authorProfile = true; corpusProfile = false; authorLimits = false; localStorage.setItem("unshiter-view-mode", "authors"); limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; draw(); });
  authorLimitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = true; localStorage.setItem("unshiter-view-mode", "author-limits"); draw(); });
  worksButton.addEventListener("click", () => { authorProfile = false; corpusProfile = false; authorLimits = false; localStorage.setItem("unshiter-view-mode", "works"); showWorksMode(); draw(); });
}
fetch("data.json?v=20260828144405168262000").then(r => r.json()).then(json => {
  data = json;
  COLORS = Object.entries(data.palette || {}).filter(([key, color]) => key.startsWith("color") && color).map(([, color]) => color);
  IA_COLOR = data.palette?.ia || IA_COLOR;
  // Les inversions d'axes font partie de la configuration persistante, au
  // même titre que les œuvres et les mesures cochées.
  const savedFlips = JSON.parse(localStorage.getItem("unshiter-flipped") || "[]");
  savedFlips.map(metricKey).forEach(key => flippedAxes.add(key));
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
  const footerHelp = document.createElement("a");
  footerHelp.href = "#";
  footerHelp.textContent = "Aide";
  footerHelp.className = "footer-help";
  footerHelp.addEventListener("click", event => { event.preventDefault(); showApplicationHelp(); });
  document.querySelector("footer").append(" — ", footerHelp);
  controls();
  draw();
}).catch(() => { document.getElementById("footer-version").textContent = "erreur de chargement"; });
