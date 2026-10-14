(function (root, factory) {
  const catalog = root.MetricCatalog || (typeof require === "function" ? require("./metric-catalog.js") : null);
  const api = factory(catalog);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RewritePrompt = api;
})(globalThis, function (catalog) {
  const cleanTitle = title => String(title || "")
    .replace(/\*\*/g, "")
    .split("/")[0]
    .replace(/\s*\([^)]*\)/g, "")
    .trim();
  const cleanDefinition = note => String(note || "")
    .replace(/\[([^\]]+)\]\(#[^)]+\)/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*/g, "")
    .replace(/\s+/g, " ")
    .replace(/[.!?]+$/, "")
    .trim();
  function selectedValue(metric, books, readValue) {
    const values = books.map(book => readValue(book, metric.id)).filter(Number.isFinite);
    return values.length === books.length && books.length
      ? values.reduce((sum, value) => sum + value, 0) / books.length
      : null;
  }

  function selectedSum(id, books, readValue) {
    const values = books.map(book => readValue(book, id)).filter(Number.isFinite);
    return values.length === books.length && books.length
      ? values.reduce((sum, value) => sum + value, 0)
      : null;
  }

  function buildExport({ data, books, readValue, template }) {
    return {
      header: String(template ?? data?.site?.prompt_rewriting ?? "").trim(),
      minimum_ratio: Number(data?.prompt_min_ratio) || 0,
      rare_ratio: Number(data?.prompt_rare_ratio) || 0,
      metrics: catalog.fromData(data).flatMap(metric => {
        const value = selectedValue(metric, books, readValue);
        if (!Number.isFinite(value)) return [];
        const linkedIds = [...String(metric.definition || "").matchAll(/\]\(#([a-z][a-z0-9_]*)\)/g)].map(match => match[1]);
        const share = /\bx\b/i.test(metric.note) && /\by\b/i.test(metric.note) && linkedIds.length >= 2
          ? [
              linkedIds.slice(0, -1).map(id => selectedSum(id, books, readValue)).reduce(
                (sum, value) => Number.isFinite(sum) && Number.isFinite(value) ? sum + value : null,
                0,
              ),
              selectedSum(linkedIds.at(-1), books, readValue),
            ]
          : [];
        return [{
          ...metric,
          title: cleanTitle(metric.title),
          value,
          numerator: share[0],
          denominator: share[1],
        }];
      }),
    };
  }

  function percentageValue(metric) {
    const note = String(metric.note || "").toLocaleLowerCase("fr");
    const context = `${metric.title} ${note}`.toLocaleLowerCase("fr");
    const percentage = /\b[xy]\b\s*%/.test(note) || /po(?:u)?rcentage|pour 100|\bpart\b|\btaux\b|densit|ratio|entropie|divis|rapport/.test(context);
    const value = percentage && Math.abs(metric.value) <= 1 ? metric.value * 100 : metric.value;
    return { percentage, value };
  }

  function formattedValue(metric) {
    const { percentage, value } = percentageValue(metric);
    return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })}${percentage ? " %" : ""}`;
  }

  function formattedNumber(metric) {
    return percentageValue(metric).value.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
  }

  function displayedAsZero(metric, minimumRatio) {
    if (String(metric.note || "").includes("|")) {
      const ratio = metricRatio(metric);
      return ratio === 0 || ratio < minimumRatio;
    }
    const { percentage, value } = percentageValue(metric);
    return percentage ? Math.round(value) === 0 : metric.value === 0;
  }

  function metricRatio(metric) {
    if (Number.isFinite(metric.numerator) && Number.isFinite(metric.denominator) && metric.denominator) {
      return Math.abs(metric.numerator / metric.denominator);
    }
    const displayed = percentageValue(metric);
    return Math.abs(displayed.percentage ? displayed.value / 100 : metric.value);
  }

  function zeroRule(metric) {
    const alternatives = String(metric.note || "").split("|");
    if (alternatives.length > 1) return cleanDefinition(alternatives.slice(1).join("|"));
    const label = cleanDefinition(metric.note)
      .replace(/^(?:nombre|po(?:u)?rcentage|part|taux|densité)\s+(?:de|des|du|d['’])\s*/i, "")
      .trim();
    return `Pas de ${label || metric.title.toLocaleLowerCase("fr")}`;
  }

  function rareRule(metric) {
    const label = String(metric.note || "").split("|")[0].split(/\b[xy]\b/)[0]
      .replace(/\(s\)/g, "")
      .trim();
    return `${label}${label.endsWith(":") ? "" : ":"} Très rare.`;
  }

  function frequencyRule(metric) {
    const template = String(metric.note || "").split("|")[0].trim();
    if (/\bx\s+sur\s+y\b/i.test(template)) return null;
    const order = template.match(/\b([xy])\b[\s\S]*?\bpour\b[\s\S]*?\b([xy])\b/i)
      || template.match(/\b([xy])\b[\s\S]*?\btoute(?:\(s\)|s)?\s+les\s+([xy])\b/i);
    if (!order || order[1] === order[2]) return null;
    const ratio = Number.isFinite(metric.numerator) && Number.isFinite(metric.denominator) && metric.denominator
      ? metric.numerator / metric.denominator
      : metric.value;
    const eventCount = ratio < 1 ? 1 : Math.max(1, Math.round(ratio));
    const interval = ratio < 1 ? Math.max(1, Math.round(1 / ratio)) : 1;
    const values = { [order[1].toLowerCase()]: eventCount, [order[2].toLowerCase()]: interval };
    return template
      .replace(/toute(?:\(s\)|s)? les ([xy]) phrase\(s\)/gi, (_match, key) => values[key.toLowerCase()] === 1 ? "à chaque phrase" : `toutes les ${values[key.toLowerCase()].toLocaleString("fr-FR")} phrases`)
      .replace(/pour ([xy]) phrase(?:\(s\)|s)?/gi, (_match, key) => values[key.toLowerCase()] === 1 ? "par phrase" : `pour ${values[key.toLowerCase()].toLocaleString("fr-FR")} phrases`)
      .replace(/\b([xy]) ([\p{L}'’-]+)\(s\)/giu, (_match, key, noun) => `${key} ${noun}${values[key.toLowerCase()] === 1 ? "" : "s"}`)
      .replace(/\(s\)/g, eventCount === 1 ? "" : "s")
      .replace(/\b([xy])\b/g, (_match, key) => values[key.toLowerCase()].toLocaleString("fr-FR"));
  }

  function metricRule(metric) {
    const template = String(metric.note || "").split("|")[0].trim();
    const shareOrder = template.match(/\b([xy])\b\s+sur\s+\b([xy])\b/i);
    if (shareOrder && shareOrder[1] !== shareOrder[2] && Number.isFinite(metric.numerator) && Number.isFinite(metric.denominator)) {
      const percentage = metric.denominator ? Math.round(metric.numerator / metric.denominator * 100) : 0;
      const values = { [shareOrder[1].toLowerCase()]: percentage, [shareOrder[2].toLowerCase()]: 100 };
      return template
        .replace(/verbe\(s\)/gi, "verbes")
        .replace(/\b([xy])\b/g, (_match, key) => values[key.toLowerCase()].toLocaleString("fr-FR"));
    }
    const frequency = frequencyRule(metric);
    if (frequency) return frequency;
    if (/\b[xy]\b/.test(template)) {
      const number = Math.round(percentageValue(metric).value);
      return template
        .replace(/\b([xy]) ([\p{L}'’-]+)\(s\)/giu, (_match, key, noun) => `${key} ${noun}${number === 1 ? "" : "s"}`)
        .replace(/\b[xy]\b/g, formattedNumber(metric));
    }
    return `${cleanDefinition(metric.note)} : ${formattedValue(metric)}.`;
  }

  function generate(exported) {
    const metrics = exported?.metrics || [];
    const minimumRatio = Number(exported?.minimum_ratio) || 0;
    const rareRatio = Number(exported?.rare_ratio) || 0;
    const zeroIds = new Set(metrics.filter(metric => displayedAsZero(metric, minimumRatio)).map(metric => metric.id));
    const prohibitions = metrics.filter(metric => zeroIds.has(metric.id)).map(zeroRule);
    const blocks = [
      [
        "## 1. Interdits stricts (jamais d'exception)",
        prohibitions.length
          ? `${prohibitions.join(".\n")}.`
          : "Aucun.",
      ].join("\n\n"),
    ];
    const sections = new Map();
    metrics.filter(metric => !zeroIds.has(metric.id)).forEach(metric => {
      const section = metric.section || "Mesures";
      if (!sections.has(section)) sections.set(section, []);
      const rare = rareRatio > minimumRatio && metricRatio(metric) >= minimumRatio && metricRatio(metric) < rareRatio;
      sections.get(section).push(rare ? rareRule(metric) : metricRule(metric));
    });
    let number = 2;
    sections.forEach((values, section) => {
      blocks.push(`## ${number++}. ${section}\n\n${values.join("\n")}`);
    });
    const generated = blocks.filter(Boolean).join("\n\n");
    const template = String(exported?.header || "").trim();
    return template.includes("[PLACEHOLDER]")
      ? template.replace("[PLACEHOLDER]", generated)
      : [template, generated].filter(Boolean).join("\n\n");
  }

  return { buildExport, generate };
});
