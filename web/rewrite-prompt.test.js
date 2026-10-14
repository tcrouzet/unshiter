const assert = require("node:assert/strict");
const RewritePrompt = require("./rewrite-prompt.js");

const data = {
  site: { prompt: "Réécris le texte en respectant ces mesures." },
  metric_order: ["avg_sentence_length", "comma_ratio", "colon_ratio", "raw_count"],
  note_titles: { avg_sentence_length: "Longueur moyenne des phrases (mots)", comma_ratio: "Virgules par phrase", colon_ratio: "Deux-points par phrase", raw_count: "Mots" },
  notes: { avg_sentence_length: "Nombre moyen de mots par phrase.", comma_ratio: "[Nombre de virgules](#comma_count) divisé par le [nombre de phrases](#sentence_count).", colon_ratio: "[Nombre de deux-points](#colon_count) divisé par le [nombre de phrases](#sentence_count).", raw_count: "Nombre de mots." },
  metric_sections: { avg_sentence_length: "Rythme", comma_ratio: "Ponctuation", colon_ratio: "Ponctuation" },
  metric_tags: { comma_ratio: ["no"] },
  metric_quotes: { comma_ratio: "Nombre de virgules par phrase", colon_ratio: "Nombre de deux-points par phrase" },
};
const book = (length, commas, colons, colonCount, sentenceCount) => ({ stats: { avg_sentence_length: length, comma_ratio: commas, colon_ratio: colons, colon_count: colonCount, sentence_count: sentenceCount } });
const selectedBooks = [book(10, 1, 0.2, 1, 10), book(30, 3, 0.4, 9, 90)];
const readValue = (entry, id) => entry.stats[id];
const exported = RewritePrompt.buildExport({
  data,
  books: selectedBooks,
  readValue,
  template: data.site.prompt,
});

assert.deepEqual(exported.metrics.map(metric => metric.id), ["comma_ratio", "colon_ratio"]);
assert.equal(
  RewritePrompt.generate(exported),
  "Réécris le texte en respectant ces mesures.\n\n## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\n## 2. Ponctuation\n\nNombre de virgules par phrase : 2.\nNombre de deux-points par phrase : 0.",
);
assert.equal(
  RewritePrompt.generate({ header: "Avant\n\n[PLACEHOLDER]\n\nAprès", metrics: [] }),
  "Avant\n\n## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\nAprès",
);
assert.equal(
  RewritePrompt.generate({ metrics: [{ title: "Points d’exclamation", note: "Nombre de points d’exclamation par phrase", value: 0.003 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\n## 2. Mesures\n\nNombre de points d’exclamation par phrase : 0.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [{ id: "exclamation_ratio", title: "Points d’exclamation", note: "Pourcentage de points d’exclamation par phrase", value: 0.003 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nPas de points d’exclamation par phrase.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [{ title: "Négations", note: "Porcentage de phrases négatives", value: 0.24 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\n## 2. Mesures\n\nPorcentage de phrases négatives : 24 %.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [{ title: "Première personne", note: "Pourcentage de phrases à la première personne", value: 0.998 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\n## 2. Mesures\n\nPourcentage de phrases à la première personne : 100 %.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [{ title: "P10", note: "Longueur moyenne des 10% des phrases les plus courtes", value: 4 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nAucun.\n\n## 2. Mesures\n\nLongueur moyenne des 10% des phrases les plus courtes : 4.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [
    { id: "semicolons_ratio", title: "Points-virgules par phrase", note: "Nombre de points-virgules par phrase", section: "Ponctuation", value: 0 },
    { id: "simple_past_ratio", title: "Passé simple", note: "Pourcentage de passés simples", section: "Narration", value: 0 },
    { id: "comma_ratio", title: "Virgules par phrase", note: "Nombre de virgules par phrase", section: "Ponctuation", value: 1.5 },
  ] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nPas de points-virgules par phrase.\nPas de passés simples.\n\n## 2. Ponctuation\n\nNombre de virgules par phrase : 2.",
);
assert.equal(
  RewritePrompt.generate({ metrics: [
    { id: "present_participle_ratio", title: "Participes présents", note: "y participe(s) présent(s) toute(s) les x phrase(s). | Pas de participe présent.", section: "Narration", value: 0.04 },
    { id: "simple_past_ratio", title: "Passé simple", note: "y passé(s) simples toutes les x phrase(s). | Pas de passé simple.", section: "Narration", value: 0 },
  ] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nPas de passé simple.\n\n## 2. Narration\n\n1 participe présent toutes les 25 phrases.",
);
assert.match(
  RewritePrompt.generate({ metrics: [{ id: "past_participle_ratio", title: "Participes passés", note: "y participe(s) passé(s) toute(s) les x phrase(s). | Pas de participe passé.", section: "Narration", value: 2.1 }] }),
  /2 participes passés à chaque phrase\./,
);
assert.match(
  RewritePrompt.generate({ metrics: [{ id: "comma_ratio", title: "Virgules", note: "y virgule(s) pour x phrases. | Pas de virgule.", section: "Ponctuation", value: 1.4 }] }),
  /1 virgule par phrase\./,
);
assert.equal(
  RewritePrompt.generate({ minimum_ratio: 0.01, metrics: [{ id: "semicolons_ratio", title: "Points-virgules", note: "y point(s)-virgule(s) pour x phrase(s). | Pas de point-virgule.", section: "Ponctuation", value: 1 / 334 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nPas de point-virgule.",
);
assert.match(
  RewritePrompt.generate({ minimum_ratio: 0.01, metrics: [{ id: "semicolons_ratio", title: "Points-virgules", note: "y point(s)-virgule(s) pour x phrase(s). | Pas de point-virgule.", section: "Ponctuation", value: 0.01 }] }),
  /1 point-virgule pour 100 phrases\./,
);
assert.match(
  RewritePrompt.generate({ metrics: [{ id: "avg_sentence_length", title: "Longueur moyenne", note: "Longueur moyenne des phrases: x mots.", section: "Rythme", value: 14.26 }] }),
  /Longueur moyenne des phrases: 14 mots\./,
);
const tenseData = {
  site: {},
  metric_order: ["verb_present_ratio"],
  note_titles: { verb_present_ratio: "Verbes au présent" },
  notes: { verb_present_ratio: "[Nombre de verbes au présent](#verb_present_count) divisé par le [nombre de verbes](#verb_count)." },
  metric_sections: { verb_present_ratio: "Narration" },
  metric_quotes: { verb_present_ratio: "Verbes au présent: x sur y verbe(s)." },
};
const tenseBooks = [{ stats: { verb_present_ratio: 0.75, verb_present_count: 3, verb_count: 4 } }, { stats: { verb_present_ratio: 0.75, verb_present_count: 3, verb_count: 4 } }];
const tenseExport = RewritePrompt.buildExport({ data: tenseData, books: tenseBooks, readValue });
assert.match(RewritePrompt.generate(tenseExport), /Verbes au présent: 75 sur 100 verbes\./);

const frequencyData = {
  site: {},
  prompt_min_ratio: 0.01,
  metric_order: ["oral_familiarity_ratio", "simple_past_ratio"],
  note_titles: { oral_familiarity_ratio: "Familiarité orale", simple_past_ratio: "Passé simple" },
  notes: {
    oral_familiarity_ratio: "[Nombre de marqueurs](#familiarity_marker_count) divisé par le [nombre de mots](#word_count).",
    simple_past_ratio: "[Nombre de passés simples](#simple_past_count) divisé par le [nombre de verbes](#verb_count).",
  },
  metric_sections: { oral_familiarity_ratio: "Registre", simple_past_ratio: "Registre" },
  metric_quotes: {
    oral_familiarity_ratio: "Familiarité orale: y pour x mot(s).",
    simple_past_ratio: "Passé simple: x sur y verbe(s). | Pas de passé simple.",
  },
};
const frequencyBooks = [
  { stats: { oral_familiarity_ratio: 10, familiarity_marker_count: 1, word_count: 10, simple_past_ratio: 0, simple_past_count: 0, verb_count: 4 } },
  { stats: { oral_familiarity_ratio: 5, familiarity_marker_count: 1, word_count: 30, simple_past_ratio: 0, simple_past_count: 0, verb_count: 6 } },
];
const frequencyExport = RewritePrompt.buildExport({ data: frequencyData, books: frequencyBooks, readValue });
assert.match(RewritePrompt.generate(frequencyExport), /Familiarité orale: 1 pour 20 mots\./);
assert.match(RewritePrompt.generate(frequencyExport), /Pas de passé simple\./);

const rareFamiliarityBooks = [{ stats: { oral_familiarity_ratio: 0.07, familiarity_marker_count: 1, word_count: 1420, simple_past_ratio: 0, simple_past_count: 0, verb_count: 100 } }];
frequencyData.metric_quotes.oral_familiarity_ratio = "Familiarité orale: y pour x mot(s). | Quasiment pas de familiarité orale.";
const rareFamiliarityExport = RewritePrompt.buildExport({ data: frequencyData, books: rareFamiliarityBooks, readValue });
assert.match(RewritePrompt.generate(rareFamiliarityExport), /Quasiment pas de familiarité orale\./);

const nounData = {
  site: {},
  prompt_min_ratio: 0.01,
  metric_order: ["noun_ratio"],
  note_titles: { noun_ratio: "Densité des noms" },
  notes: { noun_ratio: "Somme des [noms communs](#common_noun_count) et [noms propres](#proper_noun_count), divisée par le [nombre de mots](#word_count)." },
  metric_sections: { noun_ratio: "Syntaxe" },
  metric_quotes: { noun_ratio: "Noms: y pour x mots." },
};
const nounBooks = [{ stats: { noun_ratio: 0.2, common_noun_count: 15, proper_noun_count: 5, word_count: 100 } }];
const nounExport = RewritePrompt.buildExport({ data: nounData, books: nounBooks, readValue });
assert.match(RewritePrompt.generate(nounExport), /Noms: 1 pour 5 mots\./);

const personData = {
  site: {},
  prompt_min_ratio: 0.01,
  metric_order: ["personal_subject_ratio"],
  note_titles: { personal_subject_ratio: "Sujets personnels" },
  notes: { personal_subject_ratio: "[Nombre de sujets personnels](#personal_subject_count) divisé par le [nombre de sujets classables](#classifiable_subject_count)." },
  metric_sections: { personal_subject_ratio: "Narration" },
  metric_quotes: { personal_subject_ratio: "Sujets personnels: y sur x sujets identifiables." },
};
const personBooks = [{ stats: { personal_subject_ratio: 0.2, personal_subject_count: 2, classifiable_subject_count: 10 } }];
const personExport = RewritePrompt.buildExport({ data: personData, books: personBooks, readValue });
assert.match(RewritePrompt.generate(personExport), /Sujets personnels: 20 sur 100 sujets identifiables\./);

assert.match(
  RewritePrompt.generate({ minimum_ratio: 0.01, rare_ratio: 0.02, metrics: [{ id: "rare_ratio", title: "Rare", note: "Occurrence: y pour x mots. | Aucune occurrence.", section: "Mesures", value: 0.015 }] }),
  /Occurrence: Très rare\./,
);
assert.match(
  RewritePrompt.generate({ metrics: [{ id: "burstiness_word", title: "Burstiness en mots", note: "Différence moyenne: x mot(s).", section: "Rythme", value: 1 }] }),
  /Différence moyenne: 1 mot\./,
);

assert.equal(
  RewritePrompt.generate({ minimum_ratio: 0.01, metrics: [{ id: "dialogue_ratio", title: "Dialogue", note: "Dialogues: x % du texte. | Pas de dialogue.", section: "Narration", value: 0 }] }),
  "## 1. Interdits stricts (jamais d'exception)\n\nPas de dialogue.",
);
assert.match(
  RewritePrompt.generate({ minimum_ratio: 0.01, metrics: [{ id: "dialogue_ratio", title: "Dialogue", note: "Dialogues: x % du texte. | Pas de dialogue.", section: "Narration", value: 0.163 }] }),
  /Dialogues: 16 % du texte\./,
);
