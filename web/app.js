const RADAR = [
  ["classicism_score", null],
  ["baroque_score", null],
  ["narrativity_score", null],
  ["emotionality_score", null],
  ["discursivite_score", null],
];
const RADAR_PCA = [];
const SUMMARY = [
  ["punctuation_ratio", null], ["punctuation_diversity", null],
  ["structural_diversity", null], ["structural_rhythm", null],
  ["average_syntactic_depth", null], ["sentence_start_diversity", null],
  ["sentence_start_recurrence_distance", null],
  ["burstiness", null], ["burstiness_ratio", null, true], ["noun_verb_ratio", null], ["local_repetition_ratio", null],
];
const DETAILS = [
  ["action_verb_ratio", null, true], ["temporal_connector_ratio", null, true], ["personal_subject_ratio", null, true], ["narrative_past_ratio", null, true],
  ["emotion_word_ratio", null, true], ["emotion_sentence_ratio", null, true],
  ["intensifier_adjective_ratio", null, true],
  ["emotion_intensification_ratio", null, true],
  ["joy_emotion_ratio", null, true], ["sadness_emotion_ratio", null, true],
  ["fear_emotion_ratio", null, true], ["anger_emotion_ratio", null, true],
  ["surprise_emotion_ratio", null, true], ["disgust_emotion_ratio", null, true],
  ["contempt_emotion_ratio", null, true], ["somatic_emotion_ratio", null, true],
  ["emotional_category_entropy", null, true],
  ["ellipsis_ratio", null, true],
  ["question_mark_ratio", null, true],
  ["exclamation_ratio", null, true], ["exclamative_construction_ratio", null, true],
  ["logical_connector_ratio", null, true], ["abstract_noun_ratio", null, true], ["gnomic_present_ratio", null, true],
  ["proper_noun_density", null, true],
  ["concrete_noun_ratio", null, true],
  ["tense_shift_rate", null, true],
  ["scene_summary_ratio", null, true], ["incise_density", null, true], ["coordination_accumulation_ratio", null, true], ["right_branching_depth", null, true], ["punctuation_variety_score", null, true], ["modal_generalization_ratio", null, true],
  ["global_repetition_ratio", null, true], ["local_phonetic_repetition_ratio", null, true], ["global_phonetic_repetition_ratio", null, true], ["absolute_repetition_rate", null, true],
  ["present_participle_ratio", null, true], ["past_participle_ratio", null, true],
  ["simple_past_ratio", null, true], ["literary_subjunctive_ratio", null, true], ["negation_completeness_ratio", null, true], ["negation_ratio", null, true], ["periphrastic_future_ratio", null, true], ["oral_familiarity_ratio", null, true], ["dialogue_ratio", null, true], ["avg_modifiers_per_noun", null, true], ["heavily_modified_noun_ratio", null, true], ["lexical_rarity_score", null, true], ["adjective_chain_ratio", null, true], ["avg_adjective_chain_length", null, true],
  ["trigram_repetition", null, true], ["function_word_ratio", null, true], ["noun_ratio", null, true], ["verb_ratio", null, true], ["adjective_ratio", null, true], ["adverb_ratio", null, true], ["common_noun_ratio", null, true], ["proper_noun_ratio", null, true], ["sentence_length_std_dev", null, false], ["gzip_compression_ratio", null, true], ["relative_clause_ratio", null, true], ["nominal_sentence_ratio", null, true], ["active_voice_ratio", null, true], ["metaphorical_comme_ratio", null, true], ["hapax_ratio", null, true],
  ["word_count", null, false], ["sentence_count", null, false], ["paragraph_count", null, false], ["avg_word_length", null, false], ["avg_sentence_length", null, false], ["median_sentence_length", null, false], ["sentence_length_p10", null, false], ["sentence_length_p90", null, false], ["paragraph_length_std_dev", null, false], ["document_char_count", null, false], ["relative_clause_count", null, false], ["subordinate_clause_count", null, false], ["nominal_sentence_count", null, false], ["common_noun_count", null, false], ["proper_noun_count", null, false], ["repetition_word_count", null, false], ["local_repetition_count", null, false], ["global_repetition_count", null, false],
];
// Ensemble unique des champs pouvant être agrégés pour un profil d’auteur.
// SUMMARY était auparavant absent : le tableau 2 devenait donc vide en mode
// auteurs, alors que les tableaux utilisant DETAILS restaient alimentés.
const ALL_METRICS = [...RADAR, ...SUMMARY, ...DETAILS.map(([key, label]) => [key, label])]
  .filter((item, index, all) => all.findIndex(other => other[0] === item[0]) === index);
// Les comptes bruts restent dans le tableau 3 et ne participent pas à la
// dispersion ni aux distances stylistiques. Leurs ratios dérivés restent des mesures.
const TECHNICAL_KEYS = new Set(["document_char_count", "word_count", "sentence_count", "paragraph_count", "relative_clause_count", "subordinate_clause_count", "nominal_sentence_count", "common_noun_count", "proper_noun_count", "repetition_word_count", "local_repetition_count", "global_repetition_count"]);
// La distance stylistique utilise toutes les mesures individuelles, mais
// exclut les cinq scores BigFive (composites) et les données objectives.
const COMPOSITE_FIELDS = new Set(["classicism_score", "baroque_score", "narrativity_score", "emotionality_score", "discursivite_score"]);
// Mesures dont la valeur dérive de la longueur du texte et non du style.
// Loi de Heaps : le vocabulaire croît en N^0,6, donc tout rapport au nombre
// de mots décroît en N^-0,4. Le taux de trigrammes répétés croît
// symétriquement. Ces champs restent affichés dans les tableaux, ils sortent
// seulement du Δ de Burrows, de la carte MDS et de l'ACP.
// Leurs équivalents calculés par blocs de 1 000 mots sont conservés.
const LENGTH_SENSITIVE_FIELDS = new Set([
  "hapax_ratio",
  "trigram_repetition",
  "global_repetition_ratio",
  "global_phonetic_repetition_ratio",
  "absolute_repetition_rate",
]);
const BURROWS_FIELDS = [];
// L’écart-type brut reste disponible dans les données, mais l’axe affiché
// est bien la diversité locale (burstiness).
const REMOVED_KEYS = new Set();
const MENU_METRICS = ALL_METRICS.filter(([key], index, all) => !TECHNICAL_KEYS.has(key) && !REMOVED_KEYS.has(key) && all.findIndex(item => item[0] === key) === index);
let COLORS = ["#4a2c20", "#d13c36", "#3478b8", "#57a052", "#8b55a2", "#e19a2d", "#2b9b9b"];
let IA_COLOR = "#777777";
let data, chart, surfaceChart, mdsChart, typicityChart, pcaCharts = [], evolutionCharts = [], corpusProfile = false, authorProfile = false, authorLimits = false, currentRadarTitle = "Radar", radarMode = "bigfive";
const CONFIG_STORAGE_KEYS = [
  "unshiter-evolution-highlight", "unshiter-secondary-table-order",
  "unshiter-neighborhood", "unshiter-books", "unshiter-metrics",
  "unshiter-authors-open", "unshiter-metrics-open", "unshiter-presets",
  "unshiter-flipped", "unshiter-view-mode", "unshiter-radar-mode",
  "unshiter-extreme-selection",
];
let storageCorpus = "";
function storageKey(key) { return storageCorpus ? `${key}:${storageCorpus}` : key; }
function storageGet(key) { return localStorage.getItem(storageKey(key)); }
function storageSet(key, value) { localStorage.setItem(storageKey(key), value); }
function storageRemove(key) { localStorage.removeItem(storageKey(key)); }
function activateCorpusStorage(corpusId) {
  storageCorpus = corpusId;
  // Les anciennes configurations globales sont incompatibles avec plusieurs
  // corpus et ne doivent être attribuées arbitrairement à aucun d'eux.
  CONFIG_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
}
function clearCorpusStorage({ keepPresets = true } = {}) {
  CONFIG_STORAGE_KEYS.filter(key => !keepPresets || key !== "unshiter-presets").forEach(storageRemove);
}
let evolutionOrder = "values", evolutionHighlight = "";
let secondaryTableOrder = "delta";
let renderedTableData = [];
const flippedAxes = new Set();
function publicMetricId(key) { return key; }
function metricKey(ref) { return ref; }
function isEvolutionHighlighted(entity) {
  if (!entity || !evolutionHighlight) return false;
  return evolutionHighlight.startsWith("author:")
    ? entity.author === evolutionHighlight.slice(7)
    : evolutionHighlight === `work:${entity.id}`;
}
function noteEntry(key) {
  const id = key;
  const title = data?.note_titles?.[key] || key;
  const aliases = title.replace(/\*\*/g, "").split("/").map(alias => alias.trim());
  const boldDefault = title.match(/\*\*([^*]+)\*\*/)?.[1]?.trim() || aliases[0];
  return { id, title, aliases, preferred: aliases[0], boldDefault };
}
function metricLabel(key) { const entry = noteEntry(key); if (!flippedAxes.has(key)) return entry.preferred; const alternate = entry.aliases.find(alias => alias !== entry.preferred); return alternate || entry.preferred; }
function metricNote(key) {
  const entry = noteEntry(key);
  return data?.notes?.[entry.id] || "Note non référencée.";
}
function renderNote(id) {
  const title = data.note_titles?.[String(id)] || "Note";
  const raw = data.notes?.[String(id)] || "";
  const escape = text => text.replace(/[&<>"']/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[char]));
  let body = escape(raw).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/\[([^\]]+)\]\(#([a-z][a-z0-9_]*)\)/g, '<button type="button" class="note-link" data-note-id="$2">$1</button>').replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
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
  return output.join("").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, "<em>$1</em>").replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
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
  return read(key) == null ? null : Number(read(key));
};
// Le Δ de Burrows moyenne des écarts de z-scores : chaque champ vaut une voix.
// Or plusieurs familles mesurent la même chose sous plusieurs angles, dont
// certaines avec une dépendance linéaire exacte : common + proper ≈ noun,
// et la somme des huit catégories ≈ emotion_word_ratio.
// Une famille de k champs pèse donc k voix au lieu d'une. On la ramène à une.
const FIELD_FAMILIES = [
  ["avg_sentence_length", "median_sentence_length", "sentence_length_p10", "sentence_length_p90"],
  ["sentence_length_std_dev", "burstiness", "burstiness_ratio"],
  ["noun_ratio", "common_noun_ratio", "proper_noun_ratio"],
  ["joy_emotion_ratio", "sadness_emotion_ratio", "fear_emotion_ratio", "anger_emotion_ratio",
   "surprise_emotion_ratio", "disgust_emotion_ratio", "contempt_emotion_ratio", "somatic_emotion_ratio"],
  ["emotion_word_ratio", "emotion_sentence_ratio", "emotion_intensification_ratio"],
  ["local_repetition_ratio", "local_phonetic_repetition_ratio"],
];
const FIELD_WEIGHT = new Map();
FIELD_FAMILIES.forEach(family => family.forEach(field => FIELD_WEIGHT.set(field, 1 / family.length)));
function burrowsContext(entities, referenceEntities = data.books) {
  const corpusVectors = referenceEntities.map(entity => BURROWS_FIELDS.map(key => value(entity, key)));
  const means = BURROWS_FIELDS.map((_, i) => { const values = corpusVectors.map(row => row[i]).filter(Number.isFinite); return values.reduce((sum, n) => sum + n, 0) / (values.length || 1); });
  const deviations = BURROWS_FIELDS.map((_, i) => { const values = corpusVectors.map(row => row[i]).filter(Number.isFinite), mean = means[i]; return Math.sqrt(values.reduce((sum, n) => sum + (n - mean) ** 2, 0) / (values.length || 1)); });
  const vectors = entities.map(entity => BURROWS_FIELDS.map((key, i) => { const n = value(entity, key); return Number.isFinite(n) && deviations[i] > 0 ? (n - means[i]) / deviations[i] : null; }));
  const weights = BURROWS_FIELDS.map(key => FIELD_WEIGHT.get(key) ?? 1);
  const distance = (left, right) => {
    let sum = 0, total = 0;
    for (let index = 0; index < left.length; index++) {
      if (!Number.isFinite(left[index]) || !Number.isFinite(right[index])) continue;
      sum += weights[index] * Math.abs(left[index] - right[index]);
      total += weights[index];
    }
    return total ? sum / total : 0;
  };
  return { vectors, distance };
}
function burrowsDistancesToCenter(context, centerContext = context) {
  const centroid = BURROWS_FIELDS.map((_, index) => {
    const column = centerContext.vectors.map(vector => vector[index]).filter(Number.isFinite);
    return column.length ? column.reduce((sum, number) => sum + number, 0) / column.length : null;
  });
  return context.vectors.map(vector => context.distance(vector, centroid));
}
function significantAtomicFields(books) {
  const candidates = [...new Set([...SUMMARY, ...DETAILS].map(([key]) => key))]
    .filter(key => !COMPOSITE_FIELDS.has(key)
      && !TECHNICAL_KEYS.has(key)
      && !LENGTH_SENSITIVE_FIELDS.has(key));
  return candidates.filter(key => {
    const values = books.map(book => value(book, key));
    if (!values.every(Number.isFinite)) throw new Error(`Mesure atomique incomplète : ${key}`);
    return (dispersion(values, key) ?? 0) >= DISPERSION_SIGNIFICANCE_POINTS;
  });
}
function selected() { return [...document.querySelectorAll("#authors input[type=checkbox]:not(.author-toggle):checked")].map(x => data.books.find(b => b.id === Number(x.value))).filter(Boolean); }
function checkedMetrics() { return [...new Set([...document.querySelectorAll("#metrics input:checked")].map(x => metricKey(x.value)))]; }
function neighborhoodState() {
  const books = selected(), entities = authorProfile || authorLimits ? authorAverages(books) : books;
  const reference = document.getElementById("neighborhood-reference"), pinned = document.getElementById("neighborhood-pinned"), count = document.getElementById("neighborhood-count");
  const key = entity => entity ? `${entity.author || ""}\u0000${entity.title || ""}` : "";
  const pinnedValue = pinned?.value ?? "";
  const mode = authorProfile ? "authors" : authorLimits ? "author-limits" : corpusProfile ? "limits" : "works";
  return {
    mode,
    book_ids: books.map(book => book.id),
    reference: key(entities[Number(reference?.value || 0)]),
    pinned: pinnedValue === "" ? "" : key(entities[Number(pinnedValue)]),
    count: count?.value || "5",
  };
}
function saveNeighborhoodState() { storageSet("unshiter-neighborhood", JSON.stringify(neighborhoodState())); }
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
function authorSortKey(value) {
  const text = String(value?.author || value || "").trim();
  const parts = text.split(/\s+/).filter(Boolean);
  return parts.length > 1 ? `${parts.at(-1)}\u0000${parts.slice(0, -1).join(" ")}` : text;
}
function authorCompare(left, right) {
  const a = String(left?.author || left || "").trim();
  const b = String(right?.author || right || "").trim();
  if (a.toLocaleLowerCase() === "ia") return b.toLocaleLowerCase() === "ia" ? 0 : -1;
  if (b.toLocaleLowerCase() === "ia") return 1;
  return authorSortKey(a).localeCompare(authorSortKey(b), "fr", { sensitivity: "base" });
}
const INVERSE = new Set(["noun_verb_ratio", "local_repetition_ratio", "global_repetition_ratio", "local_phonetic_repetition_ratio", "global_phonetic_repetition_ratio", "absolute_repetition_rate", "trigram_repetition", "adjective_ratio", "adverb_ratio", "relative_clause_ratio", "nominal_sentence_ratio", "metaphorical_comme_ratio", "sentence_start_diversity", "burstiness"]);
const DISPLAY_INVERTED = new Set(["burstiness"]);
function scale(key, n) {
  if (n == null) return null;
  // Important : la référence est l'ensemble des livres exportés, pas la
  // sélection affichée. Ainsi retirer un auteur ne change pas les limites.
  const values = corpusValues.get(key) || [];
  if (!values.length) return null;
  if (RADAR_PCA.some(([field]) => field === key)) {
    const sorted = [...values].sort((a, b) => a - b);
    if (sorted.length === 1) return 50;
    const lower = sorted.findIndex(value => value >= n);
    const upper = sorted.findLastIndex(value => value <= n);
    return Math.max(0, Math.min(100, ((Math.max(lower, 0) + Math.max(upper, 0)) / 2) / (sorted.length - 1) * 100));
  }
  const maximum = Math.max(...values);
  if (!Number.isFinite(maximum)) return null;
  // L'origine reste le zéro réel : la plus petite valeur du corpus n'est
  // jamais artificiellement ramenée à 0 %.
  let relative = Math.max(0, Math.min(1, maximum ? n / maximum : 0));
  const entry = noteEntry(key);
  const preferredIsSecond = entry.aliases.indexOf(entry.boldDefault) === 1;
  if (preferredIsSecond !== flippedAxes.has(key)) relative = 1 - relative;
  // Courbe logarithmique continue : elle étale les valeurs basses puis ralentit
  // progressivement vers le bord, sans seuil ni saturation artificielle.
  return Math.max(0, Math.min(100, Math.log1p(4 * relative) / Math.log1p(4) * 100));
}
function activeRadarKeys() {
  return radarMode === "pca" ? RADAR_PCA.map(([key]) => key) : checkedMetrics();
}
function draw() {
  const books = selected(), keys = activeRadarKeys(), labels = keys.map(metricLabel);
  // Les tableaux sont indépendants des graphiques : ils doivent rester
  // visibles même si Chart.js ou un graphique facultatif échoue à se charger.
  renderTables(books);
  const title = `${radarTitle(books)}${radarMode === "pca" ? " · PCA" : ""}`;
  currentRadarTitle = title;
  const radarHeading = document.querySelector(".chart-box")?.closest(".chart-frame")?.querySelector("h2");
  if (radarHeading) radarHeading.textContent = radarMode === "pca" ? "Radar PCA" : "Radar";
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
  drawMDS(books);
  drawNeighborhood(books);
  drawTypicity(books);
  drawExtremeValues();
  drawEvolution(books);
  drawPcaCharts();
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
  return authorAverages(books).sort((a, b) => authorCompare(a.author, b.author)).map((book, i) => { const color = isAI(book) ? IA_COLOR : COLORS[i % COLORS.length]; return ({ label: book.author.trim().split(/\s+/).at(-1), isAI: isAI(book), data: keys.map(key => { const n = scale(key, value(book, key)); return n == null ? null : Math.max(10, n); }), borderColor: color, backgroundColor: pastel(color), fill: true, pointRadius: 0 }); });
}
function authorAverages(books) {
  const groups = books.reduce((result, book) => { (result[book.author || "Auteur inconnu"] ||= []).push(book); return result; }, {});
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b)).map(([author, authorBooks]) => { const stats = {}; for (const [key] of ALL_METRICS) { const values = authorBooks.map(book => value(book, key)).filter(Number.isFinite); if (values.length) stats[publicMetricId(key)] = values.reduce((sum, n) => sum + n, 0) / values.length; } return { author, analyses: [{ stats }] }; });
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
  const keys = activeRadarKeys();
  const profiles = (authorProfile || authorLimits) ? authorSurfaceProfiles(books, keys) : books.map(book => ({ label: book.title, author: book.author || "Auteur inconnu", values: keys.map(key => scale(key, value(book, key))) }));
  const labels = profiles.map(profile => profile.label);
  const surfaceBox = document.querySelector(".surface-box");
  if (surfaceBox) surfaceBox.style.height = `${Math.max(300, profiles.length * 30 + 90)}px`;
  const areas = profiles.map(profile => { const values = profile.values, n = values.length; return n < 3 ? 0 : Math.abs(values.reduce((sum, v, i) => sum + v * values[(i + 1) % n] * Math.sin(2 * Math.PI / n), 0) / 2); });
  const maximumArea = Math.max(...areas, 0);
  const sorted = labels.map((label, i) => ({ label, author: profiles[i].author || profiles[i].hover || "Auteur inconnu", hover: profiles[i].hover || profiles[i].author || "Auteur inconnu", area: maximumArea ? areas[i] / maximumArea * 100 : 0, color: isAI(profiles[i]) ? IA_COLOR : COLORS[i % COLORS.length] })).sort((a, b) => a.area - b.area);
  const surfaceTitle = document.querySelector(".surface-box h2");
  if (surfaceTitle) {
    const title = `Couverture stylistique${radarMode === "pca" ? " PCA" : ""}${singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""}`;
    surfaceTitle.childNodes[0].textContent = `${title} `;
    surfaceTitle.dataset.exportTitle = title;
    surfaceBox.dataset.exportTitle = title;
  }
  surfaceChart = new Chart(document.getElementById("surfaces"), { type: "bar", data: { labels: sorted.map(x => x.label), datasets: [{ label: "Couverture stylistique", data: sorted.map(x => x.area), backgroundColor: sorted.map(x => `${x.color}b8`), borderColor: sorted.map(x => x.color), borderWidth: 1 }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => sorted[items[0]?.dataIndex]?.hover || "", label: () => "" } } }, scales: { x: { display: false, beginAtZero: true }, y: { grid: { display: false }, ticks: { font: context => ({ weight: isAI(sorted[context.index]?.author) ? "700" : "400" }) } } } } });
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
if (typeof Chart !== "undefined") Chart.register({ id: "mdsLabelsAndLinks", afterDatasetsDraw(instance) {
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
if (typeof Chart !== "undefined") Chart.register({ id: "distanceReference", afterDraw(instance) {
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
    const saved = JSON.parse(storageGet("unshiter-neighborhood") || "null");
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
    const oldPinnedValue = pinnedSelect.value;
    const oldPinnedKey = oldPinnedValue === "" ? "" : (entities[Number(oldPinnedValue)] ? entityKey(entities[Number(oldPinnedValue)]) : "");
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
    const saved = JSON.parse(storageGet("unshiter-neighborhood") || "null");
    const pinnedKey = saved && Object.hasOwn(saved, "pinned") ? saved.pinned : oldPinnedKey;
    const restoredPinned = pinnedKey ? entities.findIndex(entity => entityKey(entity) === pinnedKey) : -1;
    pinnedSelect.value = restoredPinned >= 0 ? String(restoredPinned) : "";
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
function drawTypicity(selectedBooks) {
  const canvas = document.getElementById("typicity-chart");
  if (!canvas) return;
  typicityChart?.destroy();
  let chartArea = canvas.parentElement;
  if (!chartArea?.classList.contains("typicity-chart-area")) {
    chartArea = document.createElement("div");
    chartArea.className = "typicity-chart-area";
    canvas.before(chartArea);
    chartArea.appendChild(canvas);
  }
  const authorMode = authorProfile || authorLimits;
  const entities = authorMode ? authorAverages(selectedBooks) : selectedBooks;
  const context = burrowsContext(entities, entities);
  const centerDistances = burrowsDistancesToCenter(context);
  const scored = entities.map((entity, index) => ({ entity, score: centerDistances[index] }));
  const pairDistances = [];
  for (let left = 0; left < context.vectors.length; left++) for (let right = left + 1; right < context.vectors.length; right++) pairDistances.push(context.distance(context.vectors[left], context.vectors[right]));
  const meanTypicity = scored.reduce((sum, item) => sum + item.score, 0) / Math.max(scored.length, 1);
  const meanPairDistance = pairDistances.reduce((sum, distance) => sum + distance, 0) / Math.max(pairDistances.length, 1);
  const scaleRatio = meanPairDistance ? meanTypicity / meanPairDistance : 1;
  console.assert(scaleRatio >= .4 && scaleRatio <= 1.2, `Échelle de typicité incohérente : moyenne=${meanTypicity}, distance moyenne=${meanPairDistance}, ratio=${scaleRatio}`);
  const referenceIndex = Number(document.getElementById("neighborhood-reference")?.value || 0);
  const reference = entities[referenceIndex];
  const authorNames = [...new Set(entities.map(entity => entity.author || "Auteur inconnu"))].sort(authorCompare);
  const authorColors = Object.fromEntries(authorNames.map((author, index) => [author, isAI(author) ? IA_COLOR : COLORS[index % COLORS.length]]));
  const rows = scored.map(({ entity, score }) => ({
    entity,
    author: entity.author || "Auteur inconnu",
    label: authorMode ? (entity.author || "Auteur inconnu") : (entity.title || "Œuvre"),
    exportLabel: authorMode ? (entity.author || "Auteur inconnu") : (entity.title || "Œuvre"),
    score,
    highlighted: authorMode ? entity.author === reference?.author : entity.id === reference?.id,
  })).sort((left, right) => left.score - right.score || left.label.localeCompare(right.label, "fr"));
  const corpusLabel = data.corpora?.find(corpus => corpus.id === storageCorpus)?.label || storageCorpus;
  document.getElementById("typicity-title").textContent = `Typicité stylistique — ${corpusLabel}`;
  const box = canvas.closest(".typicity-box");
  if (box) box.style.height = "auto";
  chartArea.style.height = `${Math.max(260, rows.length * 30 + 50)}px`;
  const valueLabels = { id: "typicityValueLabels", afterDatasetsDraw(instance) { const meta = instance.getDatasetMeta(0), context2d = instance.ctx; context2d.save(); context2d.fillStyle = "#514a44"; context2d.font = "12px system-ui"; context2d.textBaseline = "middle"; meta.data.forEach((bar, index) => context2d.fillText(rows[index].score.toFixed(2), bar.x + 7, bar.y)); context2d.restore(); } };
  typicityChart = new Chart(canvas, { type: "bar", plugins: [valueLabels], data: { labels: rows.map(row => row.label), datasets: [{ data: rows.map(row => row.score), backgroundColor: rows.map(row => row.highlighted ? "#1565c0" : `${authorColors[row.author]}b8`), borderColor: rows.map(row => row.highlighted ? "#1565c0" : authorColors[row.author]), borderWidth: rows.map(row => row.highlighted ? 2 : 1) }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, interaction: { mode: "index", axis: "y", intersect: true }, layout: { padding: { right: 55 } }, plugins: { legend: { display: false }, tooltip: { mode: "index", axis: "y", intersect: true, position: "nearest", callbacks: { title: items => rows[items[0]?.dataIndex]?.label || "", label: item => rows[item.dataIndex]?.author || "Auteur inconnu", afterLabel: item => `Δ ${Number(item.raw).toFixed(2)}` } } }, scales: { x: { beginAtZero: true, title: { display: true, text: "Distance Δ de Burrows au centre" } }, y: { grid: { display: false }, ticks: { font: context => ({ weight: rows[context.index]?.highlighted ? "700" : "400" }), color: context => rows[context.index]?.highlighted ? "#1565c0" : "#514a44" } } } } });
  typicityChart.$csvRows = [[authorMode ? "Auteur" : "Œuvre", "Auteur", "Typicité"], ...rows.map(row => [row.exportLabel, row.author, row.score.toFixed(2)])];
}
function extremeMetricKeys() {
  // Même univers que les analyses stylistiques : mesures atomiques dont la
  // dispersion normalisée atteint le seuil de significativité du corpus.
  return significantAtomicFields(data.books).filter(key => !REMOVED_KEYS.has(key));
}
function drawExtremeValues() {
  const select = document.getElementById("extreme-entity");
  const compareSelect = document.getElementById("extreme-compare");
  const orderSelect = document.getElementById("extreme-order");
  const output = document.getElementById("extreme-values");
  if (!select || !output) return;
  const escapeHtml = text => String(text ?? "").replace(/[&<>\"]/g, character => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[character]));
  const saved = JSON.parse(storageGet("unshiter-extreme-selection") || "null");
  const previous = select.value || saved?.entity || "";
  const previousComparison = compareSelect?.value || saved?.comparison || "";
  if (orderSelect && !orderSelect.dataset.restored) {
    if (["1", "2", "3", "4", "5"].includes(String(saved?.order))) orderSelect.value = String(saved.order);
    orderSelect.dataset.restored = "true";
  }
  const authors = authorAverages(data.books).sort((left, right) => authorCompare(left.author, right.author));
  const works = [...data.books].sort((left, right) => authorCompare(left, right) || String(left.title).localeCompare(String(right.title), "fr"));
  const entityOptions = `<optgroup label="Auteurs">${authors.map(author => `<option value="author:${escapeHtml(author.author)}">${escapeHtml(author.author)}</option>`).join("")}</optgroup><optgroup label="Œuvres">${works.map(book => `<option value="work:${book.id}">${escapeHtml(book.title)} — ${escapeHtml(book.author || "Auteur inconnu")}</option>`).join("")}</optgroup>`;
  select.innerHTML = entityOptions;
  if (compareSelect) compareSelect.innerHTML = `<option value="">Aucune comparaison</option>${entityOptions}`;
  if ([...select.options].some(option => option.value === previous)) select.value = previous;
  if (compareSelect && [...compareSelect.options].some(option => option.value === previousComparison)) compareSelect.value = previousComparison;
  const resolve = reference => {
    if (!reference) return null;
    const [kind, identifier] = reference.split(/:(.*)/s);
    return {
      population: kind === "author" ? authors : data.books,
      target: kind === "author" ? authors.find(author => author.author === identifier) : data.books.find(book => String(book.id) === identifier),
    };
  };
  const primary = resolve(select.value), comparison = resolve(compareSelect?.value || "");
  const extremeOrder = Math.max(1, Number(orderSelect?.value) || 2);
  if (!primary?.target || primary.population.length < 2) { output.innerHTML = "<p>Pas assez d’entités pour calculer des rangs.</p>"; return; }
  const positionFor = (resolved, key) => {
    if (!resolved?.target || resolved.population.length < 2) return null;
    const targetValue = value(resolved.target, key);
    const values = resolved.population.map(entity => value(entity, key)).filter(Number.isFinite);
    if (!Number.isFinite(targetValue) || values.length < 2) return null;
    const lower = values.filter(number => number < targetValue).length;
    const higher = values.filter(number => number > targetValue).length;
    const lowRank = lower + 1, highRank = higher + 1;
    const ordinal = rank => `${rank}e`;
    const useLower = lowRank <= highRank;
    const position = useLower
      ? (lowRank === 1 ? "Plus bas" : `${ordinal(lowRank)} plus bas`)
      : (highRank === 1 ? "Plus haut" : `${ordinal(highRank)} plus haut`);
    return { position, side: useLower ? "low" : "high", rank: useLower ? lowRank : highRank, percentile: lower / (values.length - 1) * 100, extreme: lowRank <= extremeOrder || highRank <= extremeOrder };
  };
  const rows = [];
  for (const key of extremeMetricKeys()) {
    const first = positionFor(primary, key), second = positionFor(comparison, key);
    if (!first || (!first.extreme && !second?.extreme)) continue;
    rows.push({ key, first, second, closePosition: Boolean(second && first.side === second.side && Math.abs(first.rank - second.rank) <= 1) });
  }
  rows.sort((left, right) => left.first.percentile - right.first.percentile || metricLabel(left.key).localeCompare(metricLabel(right.key), "fr"));
  if (!rows.length) { output.innerHTML = "<p>Aucune valeur ne figure aux deux extrémités du classement.</p>"; return; }
  const firstLabel = select.selectedOptions[0]?.textContent || "Classement";
  const secondLabel = compareSelect?.selectedOptions[0]?.textContent || "";
  output.innerHTML = `<table><thead><tr><th>Mesure</th><th>${escapeHtml(firstLabel)}</th>${comparison ? `<th>${escapeHtml(secondLabel)}</th>` : ""}</tr></thead><tbody>${rows.map(row => `<tr${row.closePosition ? ' class="close-position"' : ""}><td>${escapeHtml(metricLabel(row.key))} <button class="table-note-help metric-help" type="button" data-note-id="${row.key}" data-key="${row.key}" aria-label="Afficher la définition">?</button></td><td>${row.first.position}</td>${comparison ? `<td>${row.second?.position || "—"}</td>` : ""}</tr>`).join("")}</tbody></table>`;
}
function saveExtremeSelection() {
  const entity = document.getElementById("extreme-entity")?.value || "";
  const comparison = document.getElementById("extreme-compare")?.value || "";
  const order = document.getElementById("extreme-order")?.value || "2";
  storageSet("unshiter-extreme-selection", JSON.stringify({ entity, comparison, order }));
}
function drawEvolution(selectedBooks) {
  evolutionCharts.forEach(item => item.destroy());
  evolutionCharts = [];
  const authorMode = Boolean(authorProfile);
  const books = [...(authorMode ? authorEvolutionEntities(selectedBooks) : selectedBooks)].filter(book => authorMode || (book.publication_date && !Number.isNaN(Date.parse(book.publication_date)))).sort((a, b) => authorMode ? String(a.author).localeCompare(String(b.author), "fr") : Date.parse(a.publication_date) - Date.parse(b.publication_date));
  const definitions = [
    ...checkedMetrics().map(key => [key, metricLabel(key)]),
    ...RADAR_PCA.map(([key, label]) => [key, label]),
  ].filter((definition, index, all) => all.findIndex(([key]) => key === definition[0]) === index);
  const container = document.getElementById("evolution-charts");
  const entityKey = entity => entity ? (authorMode ? `author:${entity.author}` : `work:${entity.id}`) : "";
  const entityLabel = entity => authorMode ? entity.author : `${entity.title} — ${entity.author}`;
  const escapeOption = text => String(text ?? "").replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[char]));
  const authors = [...new Set(books.map(entity => entity.author).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fr"));
  const authorOptions = authors.map(author => `<option value="${escapeOption(`author:${author}`)}"${evolutionHighlight === `author:${author}` ? " selected" : ""}>${escapeOption(author)}</option>`).join("");
  const workOptions = authorMode ? "" : [...books]
    .sort((a, b) => entityLabel(a).localeCompare(entityLabel(b), "fr"))
    .map(entity => `<option value="${escapeOption(entityKey(entity))}"${entityKey(entity) === evolutionHighlight ? " selected" : ""}>${escapeOption(entityLabel(entity))}</option>`)
    .join("");
  const highlightOptions = `<optgroup label="Auteurs">${authorOptions}</optgroup>${workOptions ? `<optgroup label="Œuvres">${workOptions}</optgroup>` : ""}`;
  container.innerHTML = `<div class="evolution-controls"><span class="evolution-order" role="group" aria-label="Ordre des graphiques"><button type="button" data-order="dates" class="${evolutionOrder === "dates" ? "active" : ""}" aria-pressed="${evolutionOrder === "dates"}">Dates</button><span aria-hidden="true">|</span><button type="button" data-order="values" class="${evolutionOrder === "values" ? "active" : ""}" aria-pressed="${evolutionOrder === "values"}">Valeurs</button></span><label>Étiquette bleue <select class="evolution-highlight"><option value="">Aucune</option>${highlightOptions}</select></label></div>`;
  container.querySelectorAll(".evolution-order button").forEach(button => button.addEventListener("click", () => {
    evolutionOrder = button.dataset.order;
    drawEvolution(selectedBooks);
  }));
  container.querySelector(".evolution-highlight").addEventListener("change", event => {
    evolutionHighlight = event.target.value;
    if (evolutionHighlight) storageSet("unshiter-evolution-highlight", evolutionHighlight);
    else storageRemove("unshiter-evolution-highlight");
    drawEvolution(selectedBooks);
    renderTables(selectedBooks);
  });
  definitions.forEach(([key, label], i) => {
    // Le tri par valeur suit le score effectivement affiché : les axes
    // inversés sont donc ordonnés dans le sens visible, pas par valeur brute.
    const plotBooks = evolutionOrder === "dates"
      ? [...books].sort((a, b) => Date.parse(a.publication_date) - Date.parse(b.publication_date))
      : [...books].sort((a, b) => (scale(key, value(a, key)) ?? Infinity) - (scale(key, value(b, key)) ?? Infinity));
    const id = `evolution-${i}`;
    const evolutionTitle = `${label}${!authorMode && singleAuthor(books) ? ` · ${singleAuthor(books)}` : ""}`;
    const noteId = noteEntry(key).id;
    const help = noteId == null ? "" : ` <button class="metric-help help" data-key="${publicMetricId(key)}" type="button" aria-label="Afficher l’explication">?</button>`;
    const pcaHeading = key === RADAR_PCA[0]?.[0] ? '<h2 class="evolution-section-title">Composantes PCA</h2>' : "";
    container.insertAdjacentHTML("beforeend", `${pcaHeading}<div class="evolution-chart chart-frame"><div class="chart-heading"><h3>${evolutionTitle}${help}</h3><select class="chart-download" data-canvas="${id}" aria-label="Télécharger ${evolutionTitle}"><option value="png">PNG</option><option value="svg">SVG</option><option value="csv">CSV</option></select></div><canvas id="${id}"></canvas></div>`);
    const lineColor = books.every(isAI) ? IA_COLOR : COLORS[i % COLORS.length];
    const isHighlighted = index => {
      const entity = plotBooks[index];
      if (!entity) return false;
      return isEvolutionHighlighted(entity);
    };
    const isPcaComponent = RADAR_PCA.some(([field]) => field === key);
    const lineChart = new Chart(document.getElementById(id), { type: "line", data: { labels: plotBooks.map(book => authorMode ? book.author : book.title), datasets: [{ label, data: plotBooks.map(book => { const n = value(book, key); return n == null ? null : scale(key, n); }), borderColor: lineColor, backgroundColor: lineColor, pointBackgroundColor: context => isHighlighted(context.dataIndex) ? "#1565c0" : lineColor, pointBorderColor: context => isHighlighted(context.dataIndex) ? "#1565c0" : lineColor, pointRadius: context => isHighlighted(context.dataIndex) ? 5 : 3, tension: .25, spanGaps: true }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100, ticks: { display: true, stepSize: 20 }, grid: { color: "#ccd1d5" } }, x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45, color: context => isHighlighted(context.index) ? "#1565c0" : "#666", font: context => ({ weight: isHighlighted(context.index) || isAI(plotBooks[context.index]) ? "700" : "400" }) } } }, plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => { const book = plotBooks[items[0]?.dataIndex]; return authorMode ? book?.author || "" : `${String(book?.publication_date || "").slice(0, 4)} · ${book?.title || ""}${book?.author ? ` — ${book.author}` : ""}`; }, label: item => isPcaComponent ? `${Number(item.raw).toFixed(1)} %` : format(value(plotBooks[item.dataIndex], key), key) } } } } });
    lineChart.$years = [];
    lineChart.$pointLabels = [];
    lineChart.$pointEntities = plotBooks;
    lineChart.$csvRows = [
      [authorMode ? "Auteur" : "Œuvre", "Auteur", "Date", "Valeur brute", "Valeur graphique (0–100)"],
      ...plotBooks.map(book => [authorMode ? book.author : book.title, book.author || "", book.publication_date || "", value(book, key), scale(key, value(book, key))]),
    ];
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
      if (values.length) stats[publicMetricId(key)] = values.reduce((sum, n) => sum + n, 0) / values.length;
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
      if (values.length) {
        const median = values[Math.floor((values.length - 1) / 2)];
        // Les profils d’auteur sont des entités synthétiques : sérialiser
        // directement avec l’identifiant public évite toute ambiguïté entre
        // le nom Python du champ et la clé stockée dans les analyses.
        stats[publicMetricId(key)] = median;
      }
    }
    return { author, title: author, analyses: [{ stats }] };
  });
}
if (typeof Chart !== "undefined") Chart.register({ id: "publicationYears", afterDatasetsDraw(instance) { const meta = instance.getDatasetMeta(0); const labels = instance.$pointLabels?.length ? instance.$pointLabels : (instance.$years || []); const ctx = instance.ctx; const limit = instance.chartArea.top + instance.chartArea.height * .75; ctx.save(); ctx.fillStyle = "#6f6962"; ctx.textAlign = "center"; meta.data.forEach((point, i) => { if (labels[i]) { ctx.font = `${isAI(instance.$pointEntities?.[i]) ? "700" : "400"} 11px system-ui`; ctx.fillText(labels[i], point.x, point.y < limit ? point.y + 15 : point.y - 9); } }); ctx.restore(); } });
function chartExportTitle(canvas, name) {
  const frame = canvas?.closest(".chart-frame");
  if (frame?.dataset.exportTitle) return frame.dataset.exportTitle;
  const titleElement = frame?.querySelector("h3, h2");
  if (!titleElement) return name;
  const titleClone = titleElement.cloneNode(true);
  titleClone.querySelectorAll("button, select").forEach(control => control.remove());
  return titleClone.textContent.replace(/\s+/g, " ").trim() || name;
}
function chartExportSubtitle(canvas) {
  return canvas?.closest(".chart-frame")?.querySelector(":scope > p")?.textContent?.replace(/\s+/g, " ").trim() || "";
}
function radarLegendEntries() {
  if (chart?.data?.datasets?.length) return chart.data.datasets.map(dataset => ({
    label: String(dataset.label || "").trim(),
    color: dataset.borderColor || "#777777",
  })).filter(item => item.label);
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
  if (format === "csv") {
    const instance = typeof Chart !== "undefined" ? Chart.getChart(canvas) : null;
    if (!instance) return;
    let rows = instance.$csvRows;
    if (!rows) {
      const labels = instance.data.labels || [];
      const datasets = instance.data.datasets || [];
      const scatter = datasets.some(dataset => (dataset.data || []).some(point => point && typeof point === "object"));
      rows = scatter
        ? [["Série", "Étiquette", "X", "Y"], ...datasets.flatMap(dataset => (dataset.data || []).map(point => [dataset.label || "", point.label || "", point.x, point.y]))]
        : [[name === "radar" ? "Axe" : "Étiquette", ...datasets.map(dataset => dataset.label || "Valeur")], ...labels.map((label, index) => [label, ...datasets.map(dataset => dataset.data?.[index] ?? "")])];
    }
    const csv = rows.map(row => row.map(cell => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
    const href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = href; link.download = `${name}.csv`; document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
  }
  const png = canvas.toDataURL("image/png");
  if (format === "svg") {
    if (name === "radar") {
      const legend = radarLegendSvg(canvas.width, canvas.height + 22);
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height + legend.height}" viewBox="0 0 ${canvas.width} ${canvas.height + legend.height}"><rect width="100%" height="100%" fill="white"/><image href="${png}" x="0" y="0" width="${canvas.width}" height="${canvas.height}"/><g>${legend.markup}</g></svg>`;
      const href = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      const a = document.createElement("a"); a.download = `${name}.svg`; a.href = href; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 1000); return;
    }
    const title = chartExportTitle(canvas, name);
    const subtitle = chartExportSubtitle(canvas);
    const safeTitle = title.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
    const safeSubtitle = subtitle.replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;"}[char] || char));
    const top = subtitle ? 92 : 64;
    const exportHeight = canvas.height + top;
    const subtitleMarkup = subtitle ? `<text x="${canvas.width / 2}" y="62" text-anchor="middle" font-family="system-ui" font-size="16" fill="#6f6962">${safeSubtitle}</text>` : "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${exportHeight}" viewBox="0 0 ${canvas.width} ${exportHeight}"><rect width="100%" height="100%" fill="white"/><text x="${canvas.width / 2}" y="34" text-anchor="middle" font-family="system-ui" font-size="28" font-weight="600">${safeTitle}</text>${subtitleMarkup}<image href="${png}" x="0" y="${top}" width="${canvas.width}" height="${canvas.height}"/></svg>`;
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
  const subtitle = chartExportSubtitle(canvas);
  if (subtitle) {
    const title = chartExportTitle(canvas, name), composed = document.createElement("canvas");
    const top = 92;
    composed.width = canvas.width; composed.height = canvas.height + top;
    const context = composed.getContext("2d"); context.fillStyle = "#fff"; context.fillRect(0, 0, composed.width, composed.height);
    context.fillStyle = "#282522"; context.font = "600 28px system-ui"; context.textAlign = "center"; context.fillText(title, composed.width / 2, 34);
    context.fillStyle = "#6f6962"; context.font = "16px system-ui"; context.fillText(subtitle, composed.width / 2, 62);
    context.drawImage(canvas, 0, top);
    const link = document.createElement("a"); link.download = `${name}.png`; link.href = composed.toDataURL("image/png"); document.body.appendChild(link); link.click(); link.remove(); return;
  }
  const a = document.createElement("a"); a.download = `${name}.png`; a.href = png; document.body.appendChild(a); a.click(); a.remove();
}
function jacobiEigenDecomposition(source) {
  const size = source.length;
  const matrix = source.map(row => [...row]);
  const vectors = Array.from({ length: size }, (_, row) => Array.from({ length: size }, (_, column) => row === column ? 1 : 0));
  const tolerance = 1e-10;
  for (let iteration = 0; iteration < Math.max(1, size * size * 50); iteration++) {
    let p = 0, q = 1, maximum = 0;
    for (let row = 0; row < size; row++) for (let column = row + 1; column < size; column++) {
      const candidate = Math.abs(matrix[row][column]);
      if (candidate > maximum) { maximum = candidate; p = row; q = column; }
    }
    if (maximum < tolerance || size < 2) break;
    const angle = .5 * Math.atan2(2 * matrix[p][q], matrix[q][q] - matrix[p][p]);
    const cosine = Math.cos(angle), sine = Math.sin(angle);
    const pp = matrix[p][p], qq = matrix[q][q], pq = matrix[p][q];
    matrix[p][p] = cosine * cosine * pp - 2 * sine * cosine * pq + sine * sine * qq;
    matrix[q][q] = sine * sine * pp + 2 * sine * cosine * pq + cosine * cosine * qq;
    matrix[p][q] = matrix[q][p] = 0;
    for (let index = 0; index < size; index++) if (index !== p && index !== q) {
      const ip = matrix[index][p], iq = matrix[index][q];
      matrix[index][p] = matrix[p][index] = cosine * ip - sine * iq;
      matrix[index][q] = matrix[q][index] = sine * ip + cosine * iq;
    }
    for (let row = 0; row < size; row++) {
      const vp = vectors[row][p], vq = vectors[row][q];
      vectors[row][p] = cosine * vp - sine * vq;
      vectors[row][q] = sine * vp + cosine * vq;
    }
  }
  return Array.from({ length: size }, (_, index) => ({
    value: Math.max(0, matrix[index][index]),
    vector: vectors.map(row => row[index]),
  })).sort((left, right) => right.value - left.value);
}
function computePca(books) {
  const fields = significantAtomicFields(books);
  const columns = fields.map(key => books.map(book => value(book, key)));
  const standardizedColumns = [], retainedFields = [];
  columns.forEach((column, index) => {
    const mean = column.reduce((sum, number) => sum + number, 0) / column.length;
    const deviation = Math.sqrt(column.reduce((sum, number) => sum + (number - mean) ** 2, 0) / column.length);
    if (deviation > 1e-12) {
      retainedFields.push(fields[index]);
      standardizedColumns.push(column.map(number => (number - mean) / deviation));
    }
  });
  const matrix = books.map((_, row) => standardizedColumns.map(column => column[row]));
  const dimension = retainedFields.length;
  const covariance = Array.from({ length: dimension }, (_, row) => Array.from({ length: dimension }, (_, column) => matrix.reduce((sum, values) => sum + values[row] * values[column], 0) / Math.max(books.length, 1)));
  const eigenpairs = dimension ? jacobiEigenDecomposition(covariance) : [];
  const components = eigenpairs.map(pair => {
    const largestIndex = pair.vector.reduce((best, loading, index) => Math.abs(loading) > Math.abs(pair.vector[best] || 0) ? index : best, 0);
    const direction = pair.vector[largestIndex] < 0 ? -1 : 1;
    const vector = pair.vector.map(loading => loading * direction);
    const scores = matrix.map(values => values.reduce((sum, number, index) => sum + number * vector[index], 0));
    const scoreMean = scores.reduce((sum, score) => sum + score, 0) / Math.max(scores.length, 1);
    const scoreVariance = scores.reduce((sum, score) => sum + (score - scoreMean) ** 2, 0) / Math.max(scores.length, 1);
    const tolerance = Math.max(1e-8, Math.abs(pair.value) * 1e-7);
    if (Math.abs(scoreVariance - pair.value) > tolerance) throw new Error(`PCA incohérente : variance(scores)=${scoreVariance}, valeur propre=${pair.value}`);
    return { vector, scores, scoreVariance };
  });
  const measuredTotalVariance = components.reduce((sum, component) => sum + component.scoreVariance, 0);
  const totalVariance = dimension || 1;
  if (Math.abs(measuredTotalVariance - dimension) > Math.max(1e-8, dimension * 1e-7)) throw new Error(`PCA incohérente : variance totale=${measuredTotalVariance}, mesures=${dimension}`);
  components.forEach(component => { component.variance = component.scoreVariance / totalVariance; });
  let cumulative = 0, retainedCount = 0;
  while (retainedCount < Math.min(5, components.length) && (retainedCount === 0 || cumulative < .8)) {
    cumulative += components[retainedCount].variance;
    retainedCount++;
  }
  let explainedCumulative = 0;
  const allComponents = components.map((component, index) => {
    explainedCumulative += component.variance;
    return { id: `pc${index + 1}`, variance: component.variance, cumulative: explainedCumulative };
  });
  const rows = components.slice(0, retainedCount).map((component, componentIndex) => {
    const loadings = retainedFields.map((id, index) => ({ id, title: metricLabel(id), loading: component.vector[index] })).sort((left, right) => Math.abs(right.loading) - Math.abs(left.loading));
    const id = `pc${componentIndex + 1}`;
    const dominantTitles = loadings.slice(0, 3).map(item => item.title);
    const title = `PC${componentIndex + 1} · ${dominantTitles.join(" / ")}`;
    const definition = `Dominé par : ${dominantTitles.join(", ")}.`;
    const values = books.map((book, rowIndex) => ({ entity_id: book.id, title: book.title, author: book.author || "", value: component.scores[rowIndex] }));
    return { id, title, definition, dispersion: component.variance * 100, score_variance: component.scoreVariance, dispersion_significant: true, loadings, values };
  });
  data.tables ||= {};
  data.tables.pca = { id: "pca", title: "PCA", input_fields: retainedFields, components: allComponents, rows };
  RADAR_PCA.splice(0, RADAR_PCA.length, ...rows.map(row => [row.id, row.title]));
  rows.forEach(row => {
    data.metric_labels[row.id] = row.title;
    data.note_titles[row.id] = row.title;
    data.notes[row.id] = row.definition;
    if (!ALL_METRICS.some(([key]) => key === row.id)) ALL_METRICS.push([row.id, row.title]);
    row.values.forEach(entry => {
      const book = books.find(candidate => candidate.id === entry.entity_id);
      if (book?.analyses?.[0]?.stats) book.analyses[0].stats[row.id] = entry.value;
    });
  });
}
function pcaTable(books) {
  const rows = data?.tables?.pca?.rows || [];
  const header = `<th>Mesure</th>${dispersionTableHeader()}${books.map(book => `<th>${book.title || book.author || ""}</th>`).join("")}`;
  const body = rows.map(row => `<tr><td>${row.title} <button class="table-note-help metric-help" type="button" data-note-id="${row.id}" data-key="${row.id}" aria-label="Afficher la définition">?</button></td><td class="dispersion-usable">${row.dispersion.toFixed(1)} %</td>${books.map(book => `<td>${Number(value(book, row.id)).toFixed(1)}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}
function drawPcaCharts() {
  pcaCharts.forEach(chart => chart.destroy());
  pcaCharts = [];
  const box = document.getElementById("pca-analysis");
  if (!box) return;
  box.hidden = radarMode !== "pca";
  if (box.hidden) return;
  const pca = data?.tables?.pca;
  const charts = document.getElementById("pca-charts");
  charts.innerHTML = '<div class="pca-chart"><h3>Variance expliquée cumulée</h3><canvas id="pca-scree"></canvas></div>';
  const scree = new Chart(document.getElementById("pca-scree"), { type: "line", data: { labels: pca.components.map(component => component.id.toUpperCase()), datasets: [{ data: pca.components.map(component => component.cumulative * 100), borderColor: COLORS[0], backgroundColor: COLORS[0], pointRadius: 3 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 100, title: { display: true, text: "% cumulé" } } } } });
  pcaCharts.push(scree);
  pca.rows.forEach((row, index) => {
    const id = `pca-loadings-${index}`;
    charts.insertAdjacentHTML("beforeend", `<div class="pca-loading-chart"><h3>${row.title} · ${row.dispersion.toFixed(1)} % de variance</h3><canvas id="${id}"></canvas></div>`);
    const canvas = document.getElementById(id), ordered = [...row.loadings].sort((left, right) => left.loading - right.loading);
    canvas.parentElement.style.height = `${Math.max(300, ordered.length * 24 + 70)}px`;
    const chart = new Chart(canvas, { type: "bar", data: { labels: ordered.map(item => item.title), datasets: [{ data: ordered.map(item => item.loading), backgroundColor: ordered.map(item => item.loading < 0 ? "#d13c36b8" : "#3478b8b8") }] }, options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "Loading" } }, y: { ticks: { autoSkip: false } } } } });
    pcaCharts.push(chart);
  });
}
function renderTables(books) {
  // Les tableaux restent consultables pendant une transition de sélection
  // (les cases peuvent déclencher un dessin intermédiaire avec une liste
  // vide). La sélection finale est utilisée dès qu'elle est disponible.
  const tableSource = books.length ? books : (data?.books || []);
  const tableBooks = authorProfile || authorLimits ? authorMedians(tableSource) : tableSource;
  const canonicalLabel = ([key, fallback, ...rest]) => [key, data?.metric_labels?.[key] || fallback, ...rest];
  const summaryDefinitions = SUMMARY.map(canonicalLabel);
  const details = DETAILS.filter(([key]) => !REMOVED_KEYS.has(key) && !TECHNICAL_KEYS.has(key) && !SUMMARY.some(([field]) => field === key)).map(canonicalLabel);
  // Les mesures secondaires sont réunies dans un seul tableau et classées
  // par dispersion décroissante sur la sélection affichée.
  const secondaryDefinitions = [...summaryDefinitions, ...details].sort((a, b) => {
    if (secondaryTableOrder === "notes") {
      const order = new Map((data?.metric_order || []).map((key, index) => [key, index]));
      return (order.get(a[0]) ?? Number.MAX_SAFE_INTEGER) - (order.get(b[0]) ?? Number.MAX_SAFE_INTEGER);
    }
    const values = definition => tableBooks.map(book => value(book, definition[0])).filter(Number.isFinite);
    return (dispersion(values(b), b[0]) ?? -1) - (dispersion(values(a), a[0]) ?? -1);
  });
  // Le tableau de détails doit toujours exister, même si une configuration
  // de mesures est incomplète : les mesures non techniques restent affichées.
  const technical = DETAILS.filter(([key]) => TECHNICAL_KEYS.has(key)).map(canonicalLabel);
  const technicalCharacterIndex = technical.findIndex(([key]) => key === "document_char_count");
  const technicalWordsIndex = technical.findIndex(([key]) => key === "word_count");
  if (technicalCharacterIndex >= 0 && technicalWordsIndex >= 0) technical.splice(technicalWordsIndex, 0, technical.splice(technicalCharacterIndex, 1)[0]);
  const characterIndex = details.findIndex(([key]) => key === "document_char_count");
  const wordsIndex = details.findIndex(([key]) => key === "word_count");
  if (characterIndex >= 0 && wordsIndex >= 0 && characterIndex > wordsIndex) details.splice(wordsIndex, 0, details.splice(characterIndex, 1)[0]);
  const orderLabel = secondaryTableOrder === "delta" ? "Ordre des notes" : "Ordre par delta";
  const orderButton = `<button id="secondary-table-order" class="table-order" type="button">${orderLabel}</button>`;
  document.getElementById("tables").innerHTML = `<div class="table-wrap"><h2>Tableau PCA ${tableExportMenu("table-pca")}</h2><div id="table-pca">${pcaTable(tableBooks)}</div></div><div class="table-wrap"><h2>Tableau 1 · BigFive ${tableExportMenu("table-bigfive")}</h2><div id="table-bigfive">${table(tableBooks, RADAR.map(canonicalLabel))}</div></div><div class="table-wrap" id="secondary-table-wrap"><h2>Tableau 2 · Mesures ${tableExportMenu("table-secondary")}${orderButton}</h2><div id="table-secondary">${table(tableBooks, secondaryDefinitions, secondaryTableOrder === "notes")}</div></div><div class="table-wrap"><h2>Tableau 3 · Données ${tableExportMenu("table-technical")}</h2><div id="table-technical">${table(tableBooks, technical)}</div></div>`;
  renderedTableData = [
    { id: "pca", title: "Tableau PCA", definitions: RADAR_PCA, books: tableBooks },
    { id: "bigfive", title: "Tableau 1 · BigFive", definitions: RADAR.map(canonicalLabel), books: tableBooks },
    { id: "measures", title: "Tableau 2 · Mesures", definitions: secondaryDefinitions, books: tableBooks },
    { id: "raw_data", title: "Tableau 3 · Données", definitions: technical, books: tableBooks },
  ];
}
function tableExportMenu(id) {
  return `<select class="chart-download table-download" data-table-id="${id}" aria-label="Télécharger le tableau" title="Télécharger le tableau"><option value="">Télécharger</option><option value="png">PNG</option><option value="svg">SVG</option><option value="csv">CSV</option></select>`;
}
function downloadRenderedTable(container, name, format) {
  const table = container?.querySelector("table"); if (!table) return;
  const escapeXml = text => String(text ?? "").replace(/[&<>\"]/g, character => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[character]));
  const sourceRows = format === "csv" ? [...table.rows].filter(row => !row.classList.contains("metric-section")) : [...table.rows];
  const rows = sourceRows.map(row => [...row.cells].map(cell => cell.textContent.trim()));
  const rowColors = sourceRows.map(row => row.classList.contains("close-position") ? "#c62828" : "#222222");
  const link = document.createElement("a");
  if (format === "csv") {
    const csv = rows.map(row => row.map(cell => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
    link.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" })); link.download = `${name}.csv`;
  } else {
    const widths = rows[0].map((_, i) => Math.max(80, ...rows.map(row => (row[i] || "").length * 7 + 20)));
    const selectedLabel = name === "extreme-values" ? document.getElementById("extreme-entity")?.selectedOptions?.[0]?.textContent?.trim() : "";
    const comparedLabel = name === "extreme-values" ? document.getElementById("extreme-compare")?.selectedOptions?.[0]?.textContent?.trim() : "";
    const exportTitle = selectedLabel ? `Valeurs extrêmes — ${selectedLabel}${document.getElementById("extreme-compare")?.value ? ` / ${comparedLabel}` : ""}` : "";
    const titleHeight = exportTitle ? 46 : 0;
    const tableWidth = widths.reduce((left, right) => left + right, 0) + 10;
    const exportWidth = Math.max(tableWidth, exportTitle.length * 9 + 30);
    const height = rows.length * 28 + 20 + titleHeight; let y = 22 + titleHeight;
    const body = rows.map((row, ri) => { let x = 5; const cells = row.map((cell, i) => { const out = `<rect x="${x}" y="${y - 18}" width="${widths[i]}" height="28" fill="${ri === 0 ? "#eee" : "white"}" stroke="#ddd"/><text x="${x + 5}" y="${y}" font-family="system-ui" font-size="12" fill="${rowColors[ri]}"${rowColors[ri] === "#c62828" ? ' font-weight="600"' : ""}>${escapeXml(cell)}</text>`; x += widths[i]; return out; }).join(""); y += 28; return cells; }).join("");
    const titleMarkup = exportTitle ? `<text x="${exportWidth / 2}" y="30" text-anchor="middle" font-family="system-ui" font-size="18" font-weight="600">${escapeXml(exportTitle)}</text>` : "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${exportWidth}" height="${height}"><rect width="100%" height="100%" fill="white"/>${titleMarkup}${body}</svg>`;
    const svgUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    if (format === "png") {
      const image = new Image();
      image.onload = () => {
        const canvas = document.createElement("canvas"); canvas.width = exportWidth; canvas.height = height;
        canvas.getContext("2d").drawImage(image, 0, 0);
        URL.revokeObjectURL(svgUrl);
        const pngLink = document.createElement("a"); pngLink.download = `${name}.png`; pngLink.href = canvas.toDataURL("image/png"); document.body.appendChild(pngLink); pngLink.click(); pngLink.remove();
      };
      image.src = svgUrl;
      return;
    }
    link.href = svgUrl; link.download = `${name}.svg`;
  }
  document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
const INTEGER_DISPLAY_METRICS = new Set(["word_count", "sentence_count", "paragraph_count", "document_char_count", "relative_clause_count", "subordinate_clause_count", "nominal_sentence_count", "common_noun_count", "proper_noun_count", "repetition_word_count", "local_repetition_count", "global_repetition_count"]);
const RAW_DISPLAY_METRICS = new Set([
  "logical_connector_ratio", "temporal_connector_ratio", "punctuation_ratio",
  "noun_verb_ratio", "avg_word_length", "avg_sentence_length",
  "median_sentence_length", "sentence_length_p10",
  "sentence_length_p90", "paragraph_length_std_dev", "sentence_length_std_dev",
  "average_syntactic_depth", "burstiness", "avg_modifiers_per_noun",
  "avg_adjective_chain_length", "right_branching_depth", "emotional_category_entropy",
  "sentence_start_recurrence_distance",
]);
const NATIVE_PERCENT_METRICS = new Set([
  "logical_connector_ratio", "temporal_connector_ratio", "punctuation_ratio",
]);
const PERCENT_DECIMALS = new Map([
  ["intensifier_adjective_ratio", 1],
  ["emotion_intensification_ratio", 1],
  ["joy_emotion_ratio", 1], ["sadness_emotion_ratio", 1], ["fear_emotion_ratio", 1], ["anger_emotion_ratio", 1],
  ["surprise_emotion_ratio", 1], ["disgust_emotion_ratio", 1], ["contempt_emotion_ratio", 1], ["somatic_emotion_ratio", 1],
  ["ellipsis_ratio", 1],
  ["question_mark_ratio", 1],
]);
function dispersion(values, key) {
  const numbers = values.filter(Number.isFinite);
  if (numbers.length < 2) return null;
  let percentages;
  if (!RAW_DISPLAY_METRICS.has(key) || NATIVE_PERCENT_METRICS.has(key)) {
    const factor = NATIVE_PERCENT_METRICS.has(key) ? 1 : 100;
    percentages = numbers.map(value => value * factor);
  } else {
    const corpusNumbers = (corpusValues.get(key) || []).filter(Number.isFinite);
    if (!corpusNumbers.length) return null;
    const corpusMean = corpusNumbers.reduce((sum, value) => sum + value, 0) / corpusNumbers.length;
    if (corpusMean === 0) return numbers.every(value => value === 0) ? 0 : null;
    percentages = numbers.map(value => (value - corpusMean) / Math.abs(corpusMean) * 100);
  }
  if (Math.max(...percentages) - Math.min(...percentages) < 5) return 0;
  const mean = percentages.reduce((sum, value) => sum + value, 0) / percentages.length;
  return Math.sqrt(percentages.reduce((sum, value) => sum + (value - mean) ** 2, 0) / percentages.length);
}
const DISPERSION_SIGNIFICANCE_POINTS = 5;
function dispersionTableHeader() {
  return '<th>σ <button class="table-note-help" type="button" data-note-id="note_dispersion" title="Afficher la note Dispersion">?</button></th>';
}
function table(books, definitions, withSections = false) {
  const escapeHtml = text => String(text).replace(/[&<>\"]/g, char => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"}[char]));
  const header = `<th>Mesure</th>${dispersionTableHeader()}${books.map(b => `<th class="${isEvolutionHighlighted(b) ? "highlighted-entity" : ""}">${b.title}</th>`).join("")}`;
  let previousSection = null;
  const rows = definitions.map(([key, label]) => {
    const section = withSections ? data?.metric_sections?.[key] : null;
    const intertitle = section && section !== previousSection
      ? `<tr class="metric-section"><th colspan="${books.length + 2}">${escapeHtml(section)}</th></tr>` : "";
    if (section) previousSection = section;
    const rawValues = books.map(book => value(book, key));
    const displayed = rawValues.map(n => DISPLAY_INVERTED.has(key) && n != null ? 1 - n : n);
    const sigma = TECHNICAL_KEYS.has(key) ? null : dispersion(rawValues, key);
    const noteId = noteEntry(key).id;
    const note = noteId == null ? "" : ` <button class="table-note-help metric-help" type="button" data-note-id="${noteId}" data-key="${publicMetricId(key)}" aria-label="Afficher la note">?</button>`;
    const significant = sigma != null && sigma >= DISPERSION_SIGNIFICANCE_POINTS;
    const dispersionClass = sigma == null ? "" : significant ? "dispersion-usable" : "dispersion-low";
    const dispersionCell = sigma == null ? "—" : `${sigma.toLocaleString("fr-FR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
    return `${intertitle}<tr data-dispersion-significant="${significant}"><td>${metricLabel(key)}${note}</td><td class="${dispersionClass}">${dispersionCell}</td>${displayed.map((n, i) => `<td class="${[isAI(books[i]) ? "ai-value" : "", isEvolutionHighlighted(books[i]) ? "highlighted-entity" : ""].filter(Boolean).join(" ")}">${format(n, key)}</td>`).join("")}</tr>`;
  }).join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${rows}</tbody></table>`;
}
function format(n, key) { if (n == null) return "—"; if (INTEGER_DISPLAY_METRICS.has(key)) return Number(n).toLocaleString("fr-FR"); if (["logical_connector_ratio", "temporal_connector_ratio"].includes(key)) return `${Number(n).toFixed(0)} %`; if (RAW_DISPLAY_METRICS.has(key)) return Number(n).toFixed(key === "burstiness" || key === "noun_verb_ratio" ? 2 : 1); return `${(Number(n) * 100).toFixed(PERCENT_DECIMALS.get(key) ?? 0)} %`; }
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
function buildStyleExport() {
  const round2 = value => Number.isFinite(value) ? Math.round(value * 100) / 100 : value;
  const books = selected();
  const metrics = {};
  for (const [field, label] of Object.entries(data.metric_labels || {})) {
    const entry = noteEntry(field);
    metrics[field] = { id: entry.id, label, title: entry.title || label, definition: data.notes?.[entry.id] || "" };
  }
  const tableOrder = [
    ["classicism_score", "baroque_score", "narrativity_score", "emotionality_score", "discursivite_score"],
    ["punctuation_ratio", "punctuation_diversity", "structural_diversity", "structural_rhythm", "average_syntactic_depth", "sentence_start_diversity", "sentence_start_recurrence_distance", "burstiness", "noun_verb_ratio", "local_repetition_ratio"],
    ["local_phonetic_repetition_ratio", "global_phonetic_repetition_ratio", "absolute_repetition_rate", "trigram_repetition", "function_word_ratio", "noun_ratio", "verb_ratio", "adjective_ratio", "adverb_ratio", "present_participle_ratio", "past_participle_ratio", "simple_past_ratio", "literary_subjunctive_ratio", "negation_completeness_ratio", "negation_ratio", "periphrastic_future_ratio", "oral_familiarity_ratio", "dialogue_ratio", "avg_modifiers_per_noun", "heavily_modified_noun_ratio", "lexical_rarity_score", "adjective_chain_ratio", "avg_adjective_chain_length", "action_verb_ratio", "temporal_connector_ratio", "personal_subject_ratio", "narrative_past_ratio", "emotion_word_ratio", "emotion_sentence_ratio", "joy_emotion_ratio", "sadness_emotion_ratio", "fear_emotion_ratio", "anger_emotion_ratio", "surprise_emotion_ratio", "disgust_emotion_ratio", "contempt_emotion_ratio", "somatic_emotion_ratio", "emotional_category_entropy", "intensifier_adjective_ratio", "emotion_intensification_ratio", "ellipsis_ratio", "question_mark_ratio", "exclamation_ratio", "exclamative_construction_ratio", "logical_connector_ratio", "abstract_noun_ratio", "gnomic_present_ratio", "relative_clause_ratio", "nominal_sentence_ratio", "active_voice_ratio", "metaphorical_comme_ratio", "hapax_ratio"],
    ["document_char_count", "word_count", "sentence_count", "paragraph_count", "avg_word_length", "avg_sentence_length", "median_sentence_length", "sentence_length_p10", "sentence_length_p90", "paragraph_length_std_dev", "sentence_length_std_dev", "avg_paragraph_length"],
  ];
  // L’export reprend toutes les mesures affichées dans les tableaux, quelle
  // que soit la sélection courante à gauche.
  const orderedFields = [...new Set(tableOrder.flat().concat(Object.keys(metrics)))].filter(field => metrics[field]);
  const nonNormalizable = TECHNICAL_KEYS;
  // Export brut du corpus sélectionné : une seule valeur moyenne par mesure.
  // Les noms d’œuvres et d’auteurs restent dans l’interface, pas dans ce fichier.
  for (const field of orderedFields) {
    const info = metrics[field];
    const values = books.map(book => Number(book.analyses?.[0]?.stats?.[info.id])).filter(Number.isFinite);
    const corpusValues = data.books.flatMap(book => (book.analyses || []).map(analysis => Number(analysis.stats?.[info.id]))).filter(Number.isFinite);
    const rawValue = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    info.value = round2(rawValue);
    if (rawValue != null && corpusValues.length) {
      const rank = 1 + corpusValues.filter(value => value < rawValue).length;
      info["rank-in-corpus"] = `${rank}/${corpusValues.length}`;
    }
    const sigmaPoints = dispersion(corpusValues, field) ?? 0;
    info.dispersion = round2(sigmaPoints);
    info.dispersion_significant = sigmaPoints >= DISPERSION_SIGNIFICANCE_POINTS;
    if (!nonNormalizable.has(field)) {
      info.corpus_min = corpusValues.length ? Math.min(...corpusValues) : null;
      info.corpus_max = corpusValues.length ? Math.max(...corpusValues) : null;
      // Cet export encode la position entre les deux bornes afin que la valeur
      // réelle puisse être reconstruite exactement par le générateur.
      if (rawValue != null && corpusValues.length) {
        const minimum = Math.min(...corpusValues), maximum = Math.max(...corpusValues);
        info.value = maximum === minimum ? 0 : (rawValue - minimum) / (maximum - minimum);
      }
    }
  }
  return { metrics: orderedFields.map(field => { const { label, ...entry } = metrics[field]; return entry; }) };
}
function saveGeneratedFile(name, content, type) {
  const href = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a"); link.href = href; link.download = name;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}
function exportAllTableData() {
  const round1 = number => Number.isFinite(number) ? Math.round(number * 10) / 10 : null;
  const displayedNumber = (number, key) => {
    if (!Number.isFinite(number)) return null;
    const directed = DISPLAY_INVERTED.has(key) ? 1 - number : number;
    if (RADAR_PCA.some(([field]) => field === key)) return round1(directed);
    if (!RAW_DISPLAY_METRICS.has(key)) return round1(directed * 100);
    return round1(directed);
  };
  const tables = renderedTableData.map(source => ({
    id: source.id,
    title: source.title,
    ...(source.id === "pca" ? {
      input_measure_count: data?.tables?.pca?.input_fields?.length || 0,
      input_measure_ids: data?.tables?.pca?.input_fields || [],
    } : {}),
    rows: source.definitions.map(([key]) => {
      const pcaRow = source.id === "pca" ? data?.tables?.pca?.rows?.find(row => row.id === key) : null;
      const values = source.books.map((book, index) => {
        const rawValue = value(book, key);
        return {
          entity_id: book.id ?? (book.author ? `author:${book.author}` : `entity:${index}`),
          title: book.title || book.author || "",
          author: book.author || "",
          value: displayedNumber(rawValue, key),
        };
      });
      const rawValues = source.books.map(book => value(book, key)).filter(Number.isFinite);
      const sigma = TECHNICAL_KEYS.has(key) ? null : dispersion(rawValues, key);
      return {
        id: publicMetricId(key),
        title: pcaRow?.title || metricLabel(key),
        definition: pcaRow?.definition || metricNote(key),
        dispersion: round1(pcaRow?.dispersion ?? sigma),
        ...(pcaRow ? { score_variance: round1(pcaRow.score_variance) } : {}),
        dispersion_significant: pcaRow ? true : sigma != null && sigma >= DISPERSION_SIGNIFICANCE_POINTS,
        values,
      };
    }),
  }));
  const payload = {
    generated_at: new Date().toISOString(),
    corpus: storageCorpus,
    mode: authorProfile || authorLimits ? "authors" : "works",
    tables,
  };
  saveGeneratedFile(`unshiter-${storageCorpus || "corpus"}-all-data.json`, JSON.stringify(payload, null, 2), "application/json");
}
function exportPromptAndData() {
  saveGeneratedFile("style-interpretation-data.json", JSON.stringify(buildStyleExport(), null, 2), "application/json");
}
function generateRewritePrompt(exported, rules, metricOrder, metricSections, header = "", debug = false) {
  const excluded = new Set(["classicism_score", "baroque_score", "narrativity_score", "emotionality_score", "discursivite_score"]);
  const byId = new Map((exported?.metrics || []).map(metric => [metric.id, metric]));
  const linesBySection = new Map();
  const round2 = value => Math.round(value * 100) / 100;
  const hasBounds = metric => Number.isFinite(metric?.corpus_min) && Number.isFinite(metric?.corpus_max);
  const realValue = metric => metric.corpus_min + Number(metric.value) * (metric.corpus_max - metric.corpus_min);
  const linkedChildren = metric => {
    const links = [...String(metric.definition || "").matchAll(/\[([^\]]+)\]\(#([a-z][a-z0-9_]*)\)/g)]
      .map(match => ({ label: match[1], id: match[2], metric: byId.get(match[2]) }))
      .filter(child => child.metric && !hasBounds(child.metric));
    return links.length >= 3 ? links : [];
  };
  for (const id of metricOrder || []) {
    const metric = byId.get(id), section = metricSections?.[id];
    if (!metric || !section || excluded.has(id) || metric.dispersion_significant !== true) continue;
    const children = linkedChildren(metric);
    const family = children.length >= 3;
    if (!family && !hasBounds(metric)) continue;
    let action = "";
    if (hasBounds(metric) && Number.isFinite(Number(metric.value))) {
      const value = realValue(metric);
      const bracket = (rules?.[id]?.brackets || []).find(item => Array.isArray(item.range) && value >= item.range[0] && value <= item.range[1]);
      if (bracket?.action) action = bracket.action.replaceAll("{value}", String(round2(value)));
    }
    let familyDetail = "";
    if (family) {
      const total = children.reduce((sum, child) => sum + Math.max(0, Number(child.metric.value) || 0), 0);
      const shares = children
        .map(child => ({ ...child, share: total ? Math.max(0, Number(child.metric.value) || 0) / total * 100 : 0 }))
        .sort((left, right) => right.share - left.share || left.id.localeCompare(right.id));
      const present = shares
        .filter(child => child.share >= 3)
      const absent = shares.filter(child => Number(child.metric.value) === 0);
      const ruleCommon = rules?.[id]?.common;
      if (typeof ruleCommon === "string") {
        const commonUnit = rules?.[id]?.common_unit;
        familyDetail = ruleCommon.replace(/\{([a-z][a-z0-9_]*)\}/g, (placeholder, ratioId) =>
          hasBounds(byId.get(ratioId)) && Number.isFinite(Number(byId.get(ratioId).value))
            ? String(commonUnit === "absolute"
              ? round2(realValue(byId.get(ratioId)))
              : Math.floor(realValue(byId.get(ratioId)) * 100))
            : placeholder
        );
      } else {
        const details = [];
        if (present.length) details.push(`Répartition : ${present.map(child => `${child.label} ${round2(child.share)} %`).join(", ")}.`);
        if (absent.length) details.push(`Absents : ${absent.map(child => child.label).join(", ")}.`);
        familyDetail = details.join(" ");
      }
      if (!action && familyDetail) familyDetail = `${String(metric.title || id).replace(/\*\*/g, "")} : ${familyDetail}`;
    }
    const guidance = [action, familyDetail].filter(Boolean).join(" ") || "";
    const definition = String(metric.definition || "")
      .replace(/\[([^\]]+)\]\(#[a-z][a-z0-9_]*\)/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .trim();
    const title = String(metric.title || id).replace(/\*\*/g, "");
    const content = guidance ? `${title} — ${definition}\n${guidance}` : "";
    const line = content ? `${debug ? `[${id}] ` : ""}${content}` : "";
    if (!line) continue;
    if (!linesBySection.has(section)) linesBySection.set(section, []);
    linesBySection.get(section).push(line);
  }
  const sectionOrder = [...new Set((metricOrder || []).map(id => metricSections?.[id]).filter(Boolean))];
  const body = sectionOrder
    .filter(section => linesBySection.has(section))
    .map(section => `## ${section}\n${linesBySection.get(section).join("\n")}`)
    .join("\n\n");
  return [String(header || "").trim(), body].filter(Boolean).join("\n\n");
}
function exportRewritePrompt() {
  const exported = buildStyleExport();
  const args = [exported, data.rewrite_rules || {}, data.metric_order || [], data.metric_sections || {}, data.site?.prompt || ""];
  const prompt = generateRewritePrompt(...args);
  const showIds = ["true", "1", "yes", "oui"].includes(String(data.site?.prompt_ids || "").toLowerCase());
  const debugPrompt = generateRewritePrompt(...args, showIds);
  const dialog = document.getElementById("rewrite-prompt-dialog");
  const output = document.getElementById("rewrite-prompt-output");
  if (!dialog || !output) return;
  output.value = debugPrompt;
  output.dataset.copyValue = prompt;
  dialog.showModal();
}
function controls() {
  const setRadarMode = mode => {
    radarMode = mode;
    storageSet("unshiter-radar-mode", mode);
    document.getElementById("radar-bigfive")?.classList.toggle("active", mode === "bigfive");
    document.getElementById("radar-pca")?.classList.toggle("active", mode === "pca");
    draw();
  };
  document.getElementById("radar-bigfive")?.addEventListener("click", () => setRadarMode("bigfive"));
  document.getElementById("radar-pca")?.addEventListener("click", () => setRadarMode("pca"));
  document.getElementById("radar-bigfive")?.classList.toggle("active", radarMode === "bigfive");
  document.getElementById("radar-pca")?.classList.toggle("active", radarMode === "pca");
  const distanceBox = document.querySelector(".distance-box");
  if (distanceBox && !document.querySelector(".mds-box")) distanceBox.insertAdjacentHTML("afterend", '<section class="mds-box chart-frame" hidden><div class="chart-heading"><h2>Carte stylistique MDS <button class="metric-help help" data-note-id="note_mds" type="button" aria-label="Afficher l’explication">?</button></h2><div class="mds-controls" aria-label="Navigation de la carte"><button type="button" id="mds-zoom-out" aria-label="Dézoomer">−</button><button type="button" id="mds-zoom-in" aria-label="Zoomer">+</button><button type="button" id="mds-reset" aria-label="Réinitialiser la vue">Réinitialiser</button></div><select class="chart-download" data-canvas="mds" aria-label="Télécharger la carte stylistique MDS"><option value="png">PNG</option><option value="svg">SVG</option><option value="csv">CSV</option></select></div><canvas id="mds"></canvas></section><section class="neighborhood-box chart-frame"><h2>Voisinage stylistique <button class="metric-help help" data-note-id="note_neighborhood" type="button" aria-label="Afficher l’explication">?</button></h2><label class="reference-select">Œuvre de référence <select id="neighborhood-reference"></select></label><label class="reference-select">Œuvre épinglée <select id="neighborhood-pinned"><option value="">Aucune œuvre épinglée</option></select></label><label class="reference-select">Nombre de voisins <select id="neighborhood-count"><option value="5" selected>5</option><option value="10">10</option><option value="15">15</option><option value="20">20</option><option value="25">25</option><option value="30">30</option><option value="35">35</option><option value="40">40</option><option value="45">45</option><option value="all">Tous</option></select></label><h3 id="neighborhood-verdict" class="neighborhood-verdict"></h3><div id="neighborhood-table" class="neighborhood-table"></div><button type="button" id="neighborhood-download" class="table-download">Télécharger le tableau</button></section><section class="typicity-box chart-frame"><div class="chart-heading"><h2 id="typicity-title">Typicité stylistique</h2><select class="chart-download" data-canvas="typicity-chart" aria-label="Télécharger la typicité stylistique"><option value="png">PNG</option><option value="svg">SVG</option><option value="csv">CSV</option></select></div><p>Plus la barre est courte, plus le texte est proche du profil moyen du corpus.</p><canvas id="typicity-chart"></canvas></section><section class="extreme-box chart-frame"><div class="chart-heading"><h2>Valeurs extrêmes</h2><select class="chart-download table-download" data-table-id="extreme-values" aria-label="Télécharger le tableau" title="Télécharger le tableau"><option value="">Télécharger</option><option value="svg">SVG</option><option value="csv">CSV</option></select></div><label class="reference-select">Auteur ou œuvre <select id="extreme-entity"></select></label><label class="reference-select">Ordre <select id="extreme-order"><option value="1">1</option><option value="2" selected>2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select></label><p>Mesures classées parmi les valeurs les plus basses ou les plus hautes du corpus, selon l’ordre choisi.</p><div id="extreme-values" class="extreme-values"></div></section><div class="bonus-links"><button type="button" id="show-distance" class="bonus-link">Afficher Singularité (bonus)</button><button type="button" id="show-mds" class="bonus-link">Afficher la carte MDS (bonus)</button></div>');
  const extremeHeading = document.querySelector(".extreme-box .chart-heading");
  if (extremeHeading) {
    extremeHeading.querySelector(".table-download")?.remove();
    extremeHeading.insertAdjacentHTML("beforeend", tableExportMenu("extreme-values"));
  }
  const extremeEntityLabel = document.getElementById("extreme-entity")?.closest("label");
  if (extremeEntityLabel && !document.getElementById("extreme-compare")) extremeEntityLabel.insertAdjacentHTML("afterend", '<label class="reference-select">Comparer avec <select id="extreme-compare"><option value="">Aucune comparaison</option></select></label>');
  const mdsBox = document.querySelector(".mds-box");
  if (mdsBox) mdsBox.hidden = false;
  distanceBox?.remove();
  document.querySelector(".bonus-links")?.remove();
  const typicityBox = document.querySelector(".typicity-box");
  const neighborhoodBox = document.querySelector(".neighborhood-box");
  if (neighborhoodBox && typicityBox) neighborhoodBox.after(typicityBox);
  document.getElementById("extreme-entity")?.addEventListener("change", () => { saveExtremeSelection(); drawExtremeValues(); });
  document.getElementById("extreme-compare")?.addEventListener("change", () => { saveExtremeSelection(); drawExtremeValues(); });
  document.getElementById("extreme-order")?.addEventListener("change", () => { saveExtremeSelection(); drawExtremeValues(); });
  const oldTableDownload = document.getElementById("neighborhood-download");
  if (oldTableDownload?.tagName === "BUTTON") {
    const tableDownload = document.createElement("select"); tableDownload.id = "neighborhood-download"; tableDownload.className = "chart-download table-download"; tableDownload.dataset.table = "neighborhood-table"; tableDownload.setAttribute("aria-label", "Télécharger le tableau"); tableDownload.innerHTML = '<option value="" selected>Télécharger le tableau</option><option value="png">PNG</option><option value="svg">SVG</option>'; oldTableDownload.replaceWith(tableDownload); document.getElementById("neighborhood-table")?.before(tableDownload);
  }
  document.getElementById("mds-zoom-out")?.addEventListener("click", () => mdsZoom(1.25));
  document.getElementById("mds-zoom-in")?.addEventListener("click", () => mdsZoom(.8));
  document.getElementById("mds-reset")?.addEventListener("click", mdsReset);
  const neighborhoodCount = document.getElementById("neighborhood-count");
  if (neighborhoodCount) neighborhoodCount.innerHTML = [5, 10, 15, 20, 25, 30, 35, 40, 45].map(value => `<option value="${value}"${value === 5 ? " selected" : ""}>${value}</option>`).join("") + '<option value="all">Tous</option>';
  const savedNeighborhood = JSON.parse(storageGet("unshiter-neighborhood") || "null");
  if (savedNeighborhood?.count && neighborhoodCount.querySelector(`option[value="${savedNeighborhood.count}"]`)) neighborhoodCount.value = savedNeighborhood.count;
  document.getElementById("neighborhood-reference")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); drawTypicity(selected()); });
  document.getElementById("neighborhood-pinned")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); });
  document.getElementById("neighborhood-count")?.addEventListener("change", () => { saveNeighborhoodState(); drawNeighborhood(selected()); });
  const savedBookIds = JSON.parse(storageGet("unshiter-books") || JSON.stringify(savedNeighborhood?.book_ids || [])).map(Number);
  // Après une resynchronisation SQLite, les identifiants peuvent changer.
  // Une ancienne sélection qui ne contient plus aucun livre ne doit pas
  // laisser l'interface et les tableaux avec zéro colonne d'œuvre.
  const currentBookIds = new Set(data.books.map(book => book.id));
  const validSavedBookIds = savedBookIds.filter(id => currentBookIds.has(id));
  const savedBooks = new Set(validSavedBookIds.length ? validSavedBookIds : []);
  if (savedBookIds.length && !validSavedBookIds.length) storageRemove("unshiter-books");
  const rawSavedMetrics = JSON.parse(storageGet("unshiter-metrics") || "[]").map(metricKey);
  const availableMetricKeys = new Set(MENU_METRICS.map(([key]) => key));
  const validSavedMetrics = rawSavedMetrics.filter(key => availableMetricKeys.has(key));
  const savedMetrics = new Set(validSavedMetrics);
  if (rawSavedMetrics.length && !validSavedMetrics.length) storageRemove("unshiter-metrics");
  const groups = Object.groupBy ? Object.groupBy(data.books, b => b.author || "Auteur inconnu") : data.books.reduce((a, b) => ((a[b.author || "Auteur inconnu"] ||= []).push(b), a), {});
  const authorsPanel = document.getElementById("authors-panel");
  if (authorsPanel) {
    authorsPanel.open = storageGet("unshiter-authors-open") !== "0";
    authorsPanel.addEventListener("toggle", () => storageSet("unshiter-authors-open", authorsPanel.open ? "1" : "0"));
  }
  const metrics = document.getElementById("metrics");
  const metricsTitle = metrics?.previousElementSibling;
  if (metrics && metricsTitle?.tagName === "H2") {
    const panel = document.createElement("details");
    panel.id = "metrics-panel";
    panel.open = storageGet("unshiter-metrics-open") !== "0";
    const summary = document.createElement("summary");
    summary.textContent = "Mesures du radar";
    panel.appendChild(summary);
    metricsTitle.replaceWith(panel);
    panel.appendChild(metrics);
    panel.addEventListener("toggle", () => storageSet("unshiter-metrics-open", panel.open ? "1" : "0"));
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
    storageSet("unshiter-books", JSON.stringify(check ? data.books.map(book => book.id) : []));
    updateClearBooksLabel();
    draw();
    saveNeighborhoodState();
  });
  MENU_METRICS.forEach(([key]) => { const id = publicMetricId(key); const defaultChecked = RADAR.some(([radarKey]) => radarKey === key); document.getElementById("metrics").insertAdjacentHTML("beforeend", `<label class="metric-row"><input type="checkbox" value="${id}" ${savedMetrics.size ? (savedMetrics.has(key) ? "checked" : "") : (defaultChecked ? "checked" : "")}> <span>${metricLabel(key)}</span><button class="metric-flip" data-key="${id}" type="button" title="Inverser le sens">↔</button><button class="metric-help" data-key="${id}" type="button">?</button></label>`); });
  const reset = document.createElement("button"); reset.id = "metrics-reset"; reset.type = "button"; reset.textContent = "Réinitialiser"; (document.getElementById("metrics-panel") || document.getElementById("metrics")).after(reset);
  reset.addEventListener("click", () => { clearCorpusStorage(); flippedAxes.clear(); location.reload(); });
  const presetBox = document.createElement("div");
  presetBox.className = "config-actions";
  presetBox.innerHTML = '<button type="button" id="config-save">Sauvegarder la configuration</button><div id="config-presets"></div>';
  reset.after(presetBox);
  const storedPresets = JSON.parse(storageGet("unshiter-presets") || "{}");
  const presets = Array.isArray(storedPresets)
    ? Object.fromEntries(storedPresets.filter(item => item && item.name).map(item => [String(item.name).trim(), item]))
    : (storedPresets && typeof storedPresets === "object" ? storedPresets : {});
  const presetList = presetBox.querySelector("#config-presets");
  presetList.replaceChildren();
  Object.keys(presets).sort((a, b) => a.localeCompare(b)).forEach(name => {
    const button = document.createElement("button"); button.type = "button"; button.dataset.name = name;
    const label = document.createElement("span"); label.textContent = name; button.appendChild(label);
    const remove = document.createElement("span"); remove.className = "preset-remove"; remove.textContent = "×"; remove.title = "Supprimer cette configuration"; remove.setAttribute("role", "button");
    remove.addEventListener("click", event => { event.preventDefault(); event.stopPropagation(); delete presets[name]; storageSet("unshiter-presets", JSON.stringify(presets)); button.remove(); });
    button.appendChild(remove);
    button.addEventListener("click", () => { const preset = presets[name]; storageSet("unshiter-books", JSON.stringify(preset.books)); storageSet("unshiter-metrics", JSON.stringify(preset.metrics)); storageSet("unshiter-flipped", JSON.stringify(preset.flipped || [])); storageSet("unshiter-neighborhood", JSON.stringify(preset.neighborhood || {})); storageSet("unshiter-view-mode", preset.view_mode || "works"); location.reload(); }); presetList.appendChild(button);
  });
  presetBox.querySelector("#config-save").addEventListener("click", () => {
    const name = window.prompt("Nom de la configuration :")?.trim();
    if (!name) return;
    Object.keys(presets).filter(existing => existing.toLocaleLowerCase() === name.toLocaleLowerCase()).forEach(existing => delete presets[existing]);
    saveNeighborhoodState();
    presets[name] = { books: selected().map(book => book.id), metrics: checkedMetrics().map(publicMetricId), flipped: [...flippedAxes].map(publicMetricId), neighborhood: JSON.parse(storageGet("unshiter-neighborhood") || "null"), view_mode: authorProfile ? "authors" : authorLimits ? "author-limits" : corpusProfile ? "limits" : "works" };
    storageSet("unshiter-presets", JSON.stringify(presets));
    location.reload();
  });
  document.querySelectorAll("#authors input, #metrics input").forEach(x => x.addEventListener("change", () => { storageSet("unshiter-books", JSON.stringify(selected().map(b => b.id))); storageSet("unshiter-metrics", JSON.stringify(checkedMetrics().map(publicMetricId))); updateClearBooksLabel(); draw(); saveNeighborhoodState(); }));
  document.querySelectorAll(".author-toggle").forEach(x => x.addEventListener("change", () => { document.querySelectorAll(`#${x.dataset.target} input`).forEach(b => b.checked = x.checked); storageSet("unshiter-books", JSON.stringify(selected().map(b => b.id))); updateClearBooksLabel(); draw(); saveNeighborhoodState(); }));
  updateClearBooksLabel();
  document.addEventListener("change", event => { const select = event.target.closest(".chart-download, .table-download"); if (select) { if (select.dataset.table) downloadNeighborhoodTable(select.value); else if (select.dataset.tableId) downloadRenderedTable(document.getElementById(select.dataset.tableId), select.dataset.tableId, select.value); else downloadCanvas(document.getElementById(select.dataset.canvas), select.dataset.canvas, select.value); select.selectedIndex = -1; } });
  document.addEventListener("click", event => { if (!event.target.closest("#secondary-table-order")) return; secondaryTableOrder = secondaryTableOrder === "delta" ? "notes" : "delta"; storageSet("unshiter-secondary-table-order", secondaryTableOrder); renderTables(selected()); });
  const noteClose = document.getElementById("metric-note-close");
  if (noteClose) noteClose.addEventListener("click", () => { document.getElementById("metric-note").hidden = true; });
  document.addEventListener("click", event => { if (event.target.closest(".open-app-help")) { event.preventDefault(); showApplicationHelp(); } });
  document.addEventListener("click", event => { const button = event.target.closest(".metric-help, .metric-flip, .table-note-help, .note-link"); if (!button) return; event.preventDefault(); event.stopPropagation(); const note = document.getElementById("metric-note"); if (button.classList.contains("note-link")) { document.getElementById("metric-note-text").innerHTML = renderNote(button.dataset.noteId); note.hidden = false; return; } if (button.classList.contains("table-note-help")) { document.getElementById("metric-note-text").innerHTML = renderNote(button.dataset.noteId); note.hidden = false; return; } const key = metricKey(button.dataset.key); if (button.classList.contains("metric-help")) { const id = button.dataset.noteId || noteEntry(key).id; document.getElementById("metric-note-text").innerHTML = id == null ? "<p>Note non référencée.</p>" : renderNote(id); note.hidden = false; } else { flippedAxes.has(key) ? flippedAxes.delete(key) : flippedAxes.add(key); storageSet("unshiter-flipped", JSON.stringify([...flippedAxes].map(publicMetricId))); const row = button.closest(".metric-row"); row.querySelector("span").textContent = metricLabel(key); draw(); } });
  const limitsButton = document.getElementById("corpus-profile"), authorsButton = document.getElementById("author-profile"), authorLimitsButton = document.getElementById("author-limits"), worksButton = document.getElementById("works-profile");
  const exportBox = document.createElement("div"); exportBox.className = "prompt-exports";
  const promptButton = document.createElement("button"); promptButton.type = "button"; promptButton.id = "export-style-prompt"; promptButton.textContent = "Prompt d’analyse"; exportBox.appendChild(promptButton); promptButton.addEventListener("click", exportStylePrompt);
  const promptFilesButton = document.createElement("button"); promptFilesButton.type = "button"; promptFilesButton.id = "export-style-files"; promptFilesButton.textContent = "Données pour analyse"; exportBox.appendChild(promptFilesButton); promptFilesButton.addEventListener("click", exportPromptAndData);
  const rewriteButton = document.createElement("button"); rewriteButton.type = "button"; rewriteButton.id = "export-rewrite-prompt"; rewriteButton.textContent = "Prompt de réécriture"; exportBox.appendChild(rewriteButton); rewriteButton.addEventListener("click", exportRewritePrompt);
  const allDataButton = document.createElement("button"); allDataButton.type = "button"; allDataButton.id = "all-data-download"; allDataButton.textContent = "All data"; exportBox.appendChild(allDataButton); allDataButton.addEventListener("click", exportAllTableData);
  document.querySelector("aside")?.appendChild(exportBox);
  document.body.insertAdjacentHTML("beforeend", '<dialog id="rewrite-prompt-dialog" class="rewrite-prompt-dialog"><div class="rewrite-prompt-heading"><h2>Prompt de réécriture</h2><button type="button" id="rewrite-prompt-close" aria-label="Fermer">×</button></div><textarea id="rewrite-prompt-output" readonly></textarea><div class="rewrite-prompt-actions"><button type="button" id="rewrite-prompt-copy">Copier</button></div></dialog>');
  const rewriteDialog = document.getElementById("rewrite-prompt-dialog");
  document.getElementById("rewrite-prompt-close")?.addEventListener("click", () => rewriteDialog.close());
  document.getElementById("rewrite-prompt-copy")?.addEventListener("click", async event => {
    const output = document.getElementById("rewrite-prompt-output");
    try {
      await navigator.clipboard.writeText(output.dataset.copyValue || output.value);
    } catch (_) {
      const displayed = output.value;
      output.value = output.dataset.copyValue || displayed;
      output.select();
      document.execCommand("copy");
      output.value = displayed;
      output.setSelectionRange(0, 0);
    }
    event.currentTarget.textContent = "Copié";
    setTimeout(() => { event.currentTarget.textContent = "Copier"; }, 1200);
  });
  const savedViewMode = storageGet("unshiter-view-mode") || savedNeighborhood?.mode || "works";
  if (savedViewMode === "authors") { authorProfile = true; corpusProfile = false; authorLimits = false; }
  else if (savedViewMode === "author-limits") { authorProfile = false; corpusProfile = true; authorLimits = true; }
  else if (savedViewMode === "limits") { authorProfile = false; corpusProfile = true; authorLimits = false; }
  worksButton.hidden = true; authorsButton.hidden = false;
  const showWorksMode = () => { limitsButton.hidden = false; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = true; };
  const showLimitsMode = () => { limitsButton.hidden = true; authorsButton.hidden = false; authorLimitsButton.hidden = true; worksButton.hidden = false; };
  if (authorProfile) { limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; }
  else if (authorLimits) { limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = true; worksButton.hidden = false; }
  else if (corpusProfile) showLimitsMode();
  limitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = false; storageSet("unshiter-view-mode", "limits"); showLimitsMode(); draw(); saveNeighborhoodState(); });
  authorsButton.addEventListener("click", () => { authorProfile = true; corpusProfile = false; authorLimits = false; storageSet("unshiter-view-mode", "authors"); limitsButton.hidden = true; authorsButton.hidden = true; authorLimitsButton.hidden = false; worksButton.hidden = false; draw(); saveNeighborhoodState(); });
  authorLimitsButton.addEventListener("click", () => { corpusProfile = true; authorProfile = false; authorLimits = true; storageSet("unshiter-view-mode", "author-limits"); draw(); saveNeighborhoodState(); });
  worksButton.addEventListener("click", () => { authorProfile = false; corpusProfile = false; authorLimits = false; storageSet("unshiter-view-mode", "works"); showWorksMode(); draw(); saveNeighborhoodState(); });
}
fetch("data.json?v=20260923203536630768000").then(r => r.json()).then(json => {
  data = json;
  const corpusSelect = document.getElementById("corpus-select");
  const availableCorpora = (data.corpora || []).filter(corpus => data.books.some(book => (book.corpora || []).includes(corpus.id)));
  const requestedCorpus = new URLSearchParams(location.search).get("corpus");
  const defaultCorpus = availableCorpora.some(corpus => corpus.id === "bigcorpus") ? "bigcorpus" : availableCorpora[0]?.id;
  const activeCorpus = availableCorpora.some(corpus => corpus.id === requestedCorpus) ? requestedCorpus : defaultCorpus;
  activateCorpusStorage(activeCorpus);
  radarMode = storageGet("unshiter-radar-mode") === "pca" ? "pca" : "bigfive";
  evolutionHighlight = storageGet("unshiter-evolution-highlight") || "";
  const savedSecondaryTableOrder = storageGet("unshiter-secondary-table-order");
  secondaryTableOrder = ["delta", "notes"].includes(savedSecondaryTableOrder) ? savedSecondaryTableOrder : "delta";
  if (corpusSelect) {
    corpusSelect.replaceChildren(...availableCorpora.map(corpus => {
      const option = document.createElement("option");
      option.value = corpus.id;
      option.textContent = corpus.label || corpus.id;
      option.selected = corpus.id === activeCorpus;
      return option;
    }));
    corpusSelect.addEventListener("change", () => {
      const url = new URL(location.href);
      if (corpusSelect.value === "bigcorpus") url.searchParams.delete("corpus");
      else url.searchParams.set("corpus", corpusSelect.value);
      location.assign(url);
    });
  }
  data.books = data.books.filter(book => (book.corpora || ["bigcorpus"]).includes(activeCorpus));
  // Les composites dépendent des maxima du corpus choisi. Les analyses
  // élémentaires restent partagées ; seuls ces cinq scores sont recomposés.
  for (const [score, weights] of Object.entries(data.composite_weights || {})) {
    const maxima = Object.fromEntries(Object.keys(weights).map(field => [field, Math.max(0, ...data.books.map(book => Number(book.analyses?.[0]?.stats?.[field])).filter(Number.isFinite))]));
    for (const book of data.books) for (const analysis of book.analyses || []) {
      analysis.stats[score] = Object.entries(weights).reduce((sum, [field, weight]) => {
        const raw = Number(analysis.stats?.[field]);
        return sum + (Number.isFinite(raw) && maxima[field] ? weight * raw / maxima[field] : 0);
      }, 0);
    }
  }
  // Les tests de dispersion des mesures en unité native dépendent des
  // références du corpus. Elles doivent être disponibles avant le filtrage
  // partagé par Burrows, la singularité, la MDS et le voisinage.
  for (const [key] of ALL_METRICS) {
    corpusValues.set(key, data.books.map(book => value(book, key)).filter(Number.isFinite));
  }
  for (const key of data.raw_metrics || []) {
    if (!DETAILS.some(([field]) => field === key)) DETAILS.push([key, data.metric_labels?.[key] || key, false]);
    TECHNICAL_KEYS.add(key);
    INTEGER_DISPLAY_METRICS.add(key);
    if (!ALL_METRICS.some(([field]) => field === key)) ALL_METRICS.push([key, data.metric_labels?.[key] || key]);
  }
  // La dispersion des mesures exprimées dans leur unité native utilise la
  // moyenne du corpus. Ces références doivent exister avant la sélection
  // des colonnes PCA, sinon toutes les RAW_DISPLAY_METRICS sont écartées.
  for (const [key] of ALL_METRICS) {
    corpusValues.set(key, data.books.map(book => value(book, key)).filter(Number.isFinite));
  }
  BURROWS_FIELDS.splice(0, BURROWS_FIELDS.length, ...significantAtomicFields(data.books));
  console.info(`[voisinage] ${BURROWS_FIELDS.length} mesures atomiques conservées avec une dispersion ≥ ${DISPERSION_SIGNIFICANCE_POINTS} %`);
  computePca(data.books);
  const logicalConnectorValues = data.books.flatMap(book => (book.analyses || []).map(analysis => ({
    value: analysis.stats?.logical_connector_ratio,
    book: book.title,
  }))).filter(item => Number.isFinite(item.value));
  const logicalConnectorMaximum = logicalConnectorValues.reduce(
    (maximum, item) => !maximum || item.value > maximum.value ? item : maximum,
    null,
  );
  if (logicalConnectorMaximum) console.info(
    `[dispersion] logical_connector_ratio max brut avant affichage : ${logicalConnectorMaximum.value} % — ${logicalConnectorMaximum.book}`,
  );
  COLORS = Object.entries(data.palette || {}).filter(([key, color]) => key.startsWith("color") && color).map(([, color]) => color);
  IA_COLOR = data.palette?.ia || IA_COLOR;
  // Les inversions d'axes font partie de la configuration persistante, au
  // même titre que les œuvres et les mesures cochées.
  const savedFlips = JSON.parse(storageGet("unshiter-flipped") || "[]").map(metricKey);
  const availableMetricKeys = new Set(MENU_METRICS.map(([key]) => key));
  const validSavedFlips = savedFlips.filter(key => availableMetricKeys.has(key));
  validSavedFlips.forEach(key => flippedAxes.add(key));
  if (savedFlips.length !== validSavedFlips.length) storageSet("unshiter-flipped", JSON.stringify(validSavedFlips));
  // L’ordre et la sélection par défaut viennent exclusivement des marqueurs
  // #tab1_N des notes, jamais d’une liste parallèle dans le JavaScript.
  if (Array.isArray(data.default_radar) && data.default_radar.length) {
    const ordered = data.default_radar.map(metricKey).map(key => RADAR.find(item => item[0] === key)).filter(Boolean);
    RADAR.splice(0, RADAR.length, ...ordered);
  }
  document.getElementById("site-name").textContent = data.site?.name || "Unshiter";
  const footerAuthor = document.getElementById("footer-author");
  footerAuthor.textContent = data.site?.author || "Thierry Crouzet";
  footerAuthor.href = data.site?.author_url || "https://tcrouzet.com";
  // La présentation du site peut contenir du Markdown (liens, emphase,
  // listes et paragraphes), comme les notes affichées dans l'application.
  document.getElementById("site-description").innerHTML = markdownToHtml(data.site?.description || "");
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
