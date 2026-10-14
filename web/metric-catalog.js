(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.MetricCatalog = api;
})(globalThis, function () {
  function fromData(data) {
    return (data?.metric_order || [])
      .filter(id => data?.metric_sections?.[id] && data?.metric_quotes?.[id])
      .map(id => ({
        id,
        title: data.note_titles?.[id] || data.metric_labels?.[id] || id,
        note: data.metric_quotes[id],
        definition: data.notes?.[id] || "",
        section: data.metric_sections[id],
      }));
  }

  return { fromData };
});
