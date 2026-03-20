const suggestedQueries = [
  "\u004b\u0042\uC190\uD574\uBCF4\uD5D8 \uC790\uB140\uBCF4\uD5D8",
  "\u0044\u0042\uC190\uD574\uBCF4\uD5D8 \uC2E4\uC190\uBCF4\uD5D8",
  "\uD604\uB300\uD574\uC0C1 \uC5B4\uB9B0\uC774\uBCF4\uD5D8",
  "\uC0BC\uC131\uD654\uC7AC \uAC74\uAC15\uBCF4\uD5D8",
  "\uB86F\uB370\uC190\uD574\uBCF4\uD5D8 \uB3C4\uB2F4\uB3C4\uB2F4\uC790\uB140\uBCF4\uD5D8",
];

const insurers = [
  { key: "kb", name: "KB\uC190\uD574\uBCF4\uD5D8", aliases: ["kb", "kb\uC190\uD574\uBCF4\uD5D8", "kb\uC190\uBCF4", "\uCF00\uC774\uBE44"], officialUrl: "https://www.kbinsure.co.kr/CG802030001.ecs", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0" },
  { key: "db", name: "DB\uC190\uD574\uBCF4\uD5D8", aliases: ["db", "db\uC190\uD574\uBCF4\uD5D8", "db\uC190\uBCF4", "\uB3D9\uBD80\uD654\uC7AC"], officialUrl: "https://www.idbins.com/FWMAIV1535.do", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0" },
  { key: "hyundai", name: "\uD604\uB300\uD574\uC0C1", aliases: ["\uD604\uB300\uD574\uC0C1", "\uD604\uB300", "\uD558\uC774\uCE74"], officialUrl: "https://children.hi.co.kr/bin/CI/ON/CION3200G.jsp", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0" },
  { key: "samsung", name: "\uC0BC\uC131\uD654\uC7AC", aliases: ["\uC0BC\uC131\uD654\uC7AC", "\uC0BC\uC131"], officialUrl: "https://www.samsungfire.com", coverage: "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0" },
  { key: "lotte", name: "\uB86F\uB370\uC190\uD574\uBCF4\uD5D8", aliases: ["\uB86F\uB370\uC190\uD574\uBCF4\uD5D8", "\uB86F\uB370", "\uB86F\uB370\uC190\uBCF4"], officialUrl: "https://www.lotteins.co.kr", coverage: "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0" },
  { key: "meritz", name: "\uBA54\uB9AC\uCE20\uD654\uC7AC", aliases: ["\uBA54\uB9AC\uCE20\uD654\uC7AC", "\uBA54\uB9AC\uCE20"], officialUrl: "https://www.meritzfire.com", coverage: "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0" },
  { key: "hanwha", name: "\uD55C\uD654\uC0DD\uBA85", aliases: ["\uD55C\uD654\uC0DD\uBA85", "\uD55C\uD654"], officialUrl: "https://www.hanwhalife.com", coverage: "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0" },
  { key: "kyobo", name: "\uAD50\uBCF4\uC0DD\uBA85", aliases: ["\uAD50\uBCF4\uC0DD\uBA85", "\uAD50\uBCF4"], officialUrl: "https://www.kyobo.com", coverage: "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0" },
];

const genericTerms = ["\uBCF4\uD5D8", "\uC57D\uAD00", "\uC0C1\uD488", "\uC694\uC57D\uC11C", "\uC0AC\uC5C5\uBC29\uBC95\uC11C", "\uB2E4\uC6B4\uB85C\uB4DC", "\uAC80\uC0C9", "\uCC3E\uAE30", "\uACF5\uC2DC\uC2E4"];

const adminCards = [
  {
    title: "\uBCF4\uD5D8\uC0AC\uBCC4 \uBB38\uC11C \uC218\uC9D1 \uD604\uD669",
    body: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0\uC740 KB\uC190\uD574\uBCF4\uD5D8, DB\uC190\uD574\uBCF4\uD5D8, \uD604\uB300\uD574\uC0C1 \uC5B4\uB311\uD130\uB97C \uC6B0\uC120 \uAD6C\uC131\uD588\uC2B5\uB2C8\uB2E4.",
    items: ["KB \uC0C1\uC138 \uC57D\uAD00 \uD06C\uB864\uB9C1", "DB \uAC80\uC0C9 API \uC5F0\uACB0", "\uD604\uB300\uD574\uC0C1 \uC804\uCCB4 \uC0C1\uD488\uBAA9\uB85D + PDF \uC5F0\uACB0"],
  },
  {
    title: "\uB9C1\uD06C \uC804\uB7B5",
    body: "\uCD08\uAE30 MVP\uB294 \uACF5\uC2DD \uBB38\uC11C URL \uC5F0\uACB0\uC744 \uC6B0\uC120\uD558\uACE0 \uACF5\uC2DD \uCD9C\uCC98 \uD45C\uC2DC\uB97C \uC720\uC9C0\uD569\uB2C8\uB2E4.",
    items: ["KB: CG802030003.ec", "DB: cYakgwanDown.do", "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uBC14\uB85C\uAC00\uAE30"],
  },
  {
    title: "\uAC80\uC0C9 \uD750\uB984",
    body: "\uC790\uC5F0\uC5B4 \uC785\uB825\uC5D0\uC11C \uBCF4\uD5D8\uC0AC \uBCC4\uCE6D\uC744 \uD30C\uC2F1\uD558\uACE0 \uC81C\uD488\uBA85 \uD0A4\uC6CC\uB4DC\uB97C \uAC01 \uBCF4\uD5D8\uC0AC \uACF5\uC2DD \uAC80\uC0C9 \uAD6C\uC870\uB85C \uBCF4\uB0C5\uB2C8\uB2E4.",
    items: ["\uBCC4\uCE6D \uC778\uC2DD", "\uD0A4\uC6CC\uB4DC \uC815\uB9AC", "\uACB0\uACFC \uB7AD\uD0B9 \uD6C4 \uC0C1\uC138 \uD655\uC7A5"],
  },
  {
    title: "\uB2E4\uC74C \uD655\uC7A5",
    body: "\uD604\uB300\uD574\uC0C1, \uC0BC\uC131\uD654\uC7AC, \uB86F\uB370\uC190\uD574\uBCF4\uD5D8 \uB4F1\uC740 \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uAD6C\uC870 \uBD84\uC11D\uC744 \uC774\uC5B4\uC11C \uCD94\uAC00 \uC5B4\uB311\uD130\uB97C \uBD99\uC774\uBA74 \uB429\uB2C8\uB2E4.",
    items: ["\uBCF4\uD5D8\uC0AC\uBCC4 \uC804\uC6A9 \uC5B4\uB311\uD130", "\uC815\uAE30 \uB9C1\uD06C \uAC80\uC99D", "\uCE90\uC2DC/\uC778\uB371\uC2A4 \uCD94\uAC00"],
  },
];

const LABELS = {
  all: "\uC804\uCCB4",
  searching: "\uCD94\uCC9C \uAC80\uC0C9\uC5B4\uB97C \uB20C\uB7EC \uC2DC\uC791\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4",
  searched: (query) => `"${query}" \uAC80\uC0C9 \uACB0\uACFC`,
  resultTitle: "\uAC00\uC7A5 \uC77C\uCE58\uD558\uB294 \uACF5\uC2DD \uBB38\uC11C\uB97C \uCC3E\uC558\uC2B5\uB2C8\uB2E4",
  noResultTitle: "\uC6D0\uD558\uC2DC\uB294 \uC0C1\uD488\uC774 \uC544\uB2C8\uC2E0\uAC00\uC694?",
  beforeDetail: "\uC0C1\uD488\uC744 \uC120\uD0DD\uD558\uBA74 \uC0C1\uC138 \uBB38\uC11C\uC640 \uD6C4\uC18D \uC561\uC158\uC774 \uC5EC\uAE30\uC5D0 \uD45C\uC2DC\uB429\uB2C8\uB2E4.",
  beforeDetailHint: "\uD604\uC7AC\uB294 KB\uC190\uD574\uBCF4\uD5D8, DB\uC190\uD574\uBCF4\uD5D8, \uD604\uB300\uD574\uC0C1\uC744 \uC2E4\uC81C \uD06C\uB864\uB9C1\uD558\uACE0 \uC788\uACE0, \uB098\uBA38\uC9C0 \uBCF4\uD5D8\uC0AC\uB294 \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0 \uC911\uC2EC\uC73C\uB85C \uAD6C\uC131\uB429\uB2C8\uB2E4.",
  currentSale: "\uD604\uC7AC \uD310\uB9E4",
};

const state = {
  query: "",
  selectedProductId: null,
  selectedInsurer: null,
  filters: { insurer: LABELS.all, docType: LABELS.all, status: LABELS.all, sort: "score" },
  rawResults: [],
  results: [],
};

const elements = {
  form: document.getElementById("search-form"),
  input: document.getElementById("search-input"),
  resultsContainer: document.getElementById("results-container"),
  detailContainer: document.getElementById("detail-container"),
  resultsTitle: document.getElementById("results-title"),
  resultCount: document.getElementById("result-count"),
  queryDisplay: document.getElementById("query-display"),
  emptyState: document.getElementById("empty-state"),
  emptySuggestions: document.getElementById("empty-suggestions"),
  retrySimilar: document.getElementById("retry-similar"),
  suggestedKeywords: document.getElementById("suggested-keywords"),
  insurerFilter: document.getElementById("insurer-filter"),
  docTypeFilter: document.getElementById("doc-type-filter"),
  statusFilter: document.getElementById("status-filter"),
  sortFilter: document.getElementById("sort-filter"),
  adminGrid: document.getElementById("admin-grid"),
  selectedInsurer: document.getElementById("selected-insurer"),
};

function normalizeText(value) {
  return value.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
}

function tokenize(text) {
  return text.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").split(/\s+/).filter(Boolean);
}

function formatDate(dateText) {
  return dateText || LABELS.currentSale;
}

function getStatusClass(status) {
  if (status === "\uD310\uB9E4\uC911\uC9C0") return "status-stopped";
  if (status === "\uACFC\uAC70\uC0C1\uD488") return "status-legacy";
  return "";
}

function fillSelect(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join("");
}

function renderSuggestedKeywords() {
  elements.suggestedKeywords.innerHTML = suggestedQueries.map((query) => `<button class="chip" type="button" data-query="${query}">${query}</button>`).join("");
}

function renderAdmin() {
  elements.adminGrid.innerHTML = adminCards
    .map((card) => `<article class="admin-panel"><h4>${card.title}</h4><p class="admin-meta">${card.body}</p><ul>${card.items.map((item) => `<li>${item}</li>`).join("")}</ul></article>`)
    .join("");
}

function renderSelectedInsurer() {
  if (!state.selectedInsurer) {
    elements.selectedInsurer.classList.add("hidden");
    elements.selectedInsurer.innerHTML = "";
    return;
  }
  elements.selectedInsurer.classList.remove("hidden");
  elements.selectedInsurer.innerHTML = `
    <span class="pill">${state.selectedInsurer.name} \uC120\uD0DD\uB428</span>
    <span class="helper-text">\uC774\uC81C \uC0C1\uD488\uBA85\uC744 \uC774\uC5B4\uC11C \uC785\uB825\uD558\uBA74 \uD574\uB2F9 \uBCF4\uD5D8\uC0AC \uAE30\uC900\uC73C\uB85C \uAC80\uC0C9\uD569\uB2C8\uB2E4.</span>
    <button type="button" class="chip" data-clear-insurer="true">\uC120\uD0DD \uD574\uC81C</button>
  `;
}

function stripGenericTerms(text) {
  let value = text;
  for (const term of genericTerms) value = value.replaceAll(term, " ");
  return value.replace(/\s+/g, " ").trim();
}

function insurerMatchScore(insurer, query) {
  const normalizedQuery = normalizeText(query);
  let score = 0;
  const targets = [insurer.name, ...insurer.aliases];
  for (const target of targets) {
    const normalizedTarget = normalizeText(target);
    if (!normalizedTarget) continue;
    if (normalizedTarget.includes(normalizedQuery) || normalizedQuery.includes(normalizedTarget)) score += 10;
    for (const token of tokenize(query)) {
      const normalizedToken = normalizeText(token);
      if (normalizedToken && normalizedTarget.includes(normalizedToken)) score += 4;
    }
  }
  return score;
}

function findMatchingInsurers(query) {
  const compact = normalizeText(query);
  if (!compact) return [];
  return insurers
    .map((insurer) => ({ insurer, score: insurerMatchScore(insurer, query) }))
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || a.insurer.name.localeCompare(b.insurer.name))
    .map((item) => item.insurer);
}

function isInsurerOnlyQuery(query) {
  const matches = findMatchingInsurers(query);
  if (!matches.length) return false;
  let stripped = query;
  for (const alias of [matches[0].name, ...matches[0].aliases]) {
    stripped = stripped.replace(new RegExp(alias, "ig"), " ");
  }
  stripped = stripGenericTerms(stripped);
  return !stripped;
}

function toInsurerResult(insurer) {
  return {
    id: `insurer-${insurer.key}`,
    resultType: "insurer",
    insurerKey: insurer.key,
    insurerName: insurer.name,
    productName: `${insurer.name} \uBCF4\uD5D8\uC0AC \uAC80\uC0C9`,
    insuranceType: "\uBCF4\uD5D8\uC0AC",
    status: "\uBCF4\uD5D8\uC0AC \uC120\uD0DD",
    sourceUrl: insurer.officialUrl,
    officialSource: `${insurer.name} \uACF5\uC2DD \uC0AC\uC774\uD2B8`,
    documents: [],
    score: insurerMatchScore(insurer, state.query),
    notice: `${insurer.coverage} · \uC774 \uBCF4\uD5D8\uC0AC\uB97C \uB204\uB974\uBA74 \uC120\uD0DD \uC0C1\uD0DC\uB85C \uC0C1\uD488 \uAC80\uC0C9\uC744 \uC774\uC5B4\uAC08 \uC218 \uC788\uC2B5\uB2C8\uB2E4.`,
  };
}

function toViewModel(result, index) {
  return {
    ...result,
    resultType: result.resultType || "product",
    id: result.id ?? `${result.provider || "provider"}-${result.productCode || index}`,
    documents: (result.documents || []).map((doc) => ({
      type: doc.type,
      title: doc.title || doc.type,
      revisionDate: doc.revisionDate || doc.saleStartDate || "",
      url: doc.url,
      format: doc.format || "PDF",
    })),
  };
}

function buildFilters() {
  const productResults = state.rawResults.filter((item) => item.resultType !== "insurer");
  fillSelect(elements.insurerFilter, [LABELS.all, ...new Set(productResults.map((item) => item.insurerName).filter(Boolean))]);
  fillSelect(elements.docTypeFilter, [LABELS.all, ...new Set(productResults.flatMap((item) => (item.documents || []).map((doc) => doc.type)).filter(Boolean))]);
  fillSelect(elements.statusFilter, [LABELS.all, ...new Set(productResults.map((item) => item.status).filter(Boolean))]);
}

function computeScore(product, queryTokens) {
  if (product.resultType === "insurer") return product.score || 0;
  if (!queryTokens.length) return product.score ?? 0;
  const haystack = [product.insurerName, product.productName, product.insuranceType ?? "", ...(product.documents || []).map((doc) => `${doc.type} ${doc.title}`)]
    .join(" ")
    .toLowerCase();
  return queryTokens.reduce((score, token) => (haystack.includes(token) ? score + 4 : score), product.score ?? 0);
}

function applyFilters(items) {
  const insurerCards = items.filter((item) => item.resultType === "insurer");
  let filtered = items.filter((item) => item.resultType !== "insurer");
  if (state.filters.insurer !== LABELS.all) filtered = filtered.filter((item) => item.insurerName === state.filters.insurer);
  if (state.filters.status !== LABELS.all) filtered = filtered.filter((item) => item.status === state.filters.status);
  if (state.filters.docType !== LABELS.all) filtered = filtered.filter((item) => (item.documents || []).some((doc) => doc.type === state.filters.docType));
  if (state.filters.sort === "recent") filtered.sort((a, b) => new Date(b.updatedAt || 0) - new Date(a.updatedAt || 0));
  else filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
  return [...insurerCards, ...filtered];
}

async function fetchSearchResults(query) {
  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("search failed");
  return response.json();
}

function searchProducts(query) {
  const queryTokens = tokenize(query);
  state.results = applyFilters(state.rawResults.map((item) => ({ ...item, score: computeScore(item, queryTokens) })));
  state.selectedProductId = state.results.find((item) => item.resultType !== "insurer")?.id ?? null;
  renderResults();
  renderDetail();
}

function renderResults() {
  const hasResults = state.results.length > 0;
  elements.queryDisplay.textContent = state.query ? LABELS.searched(state.query) : LABELS.searching;
  elements.resultCount.textContent = `${state.results.length}\uAC74`;
  elements.resultsTitle.textContent = hasResults ? LABELS.resultTitle : LABELS.noResultTitle;
  elements.emptyState.classList.toggle("hidden", hasResults);
  if (!hasResults) {
    elements.resultsContainer.innerHTML = "";
    elements.emptySuggestions.innerHTML = suggestedQueries.map((query) => `<button class="chip" type="button" data-query="${query}">${query}</button>`).join("");
    return;
  }
  elements.resultsContainer.innerHTML = state.results
    .map((item, index) => {
      if (item.resultType === "insurer") {
        return `
          <article class="result-card ${index === 0 ? "featured" : ""}">
            <div class="card-top">
              <div>
                <p class="eyebrow">\uBCF4\uD5D8\uC0AC \uAC80\uC0C9 \uACB0\uACFC</p>
                <h3>${item.insurerName}</h3>
              </div>
              <button type="button" data-select-insurer="${item.insurerKey}">\uC774 \uBCF4\uD5D8\uC0AC \uC120\uD0DD</button>
            </div>
            <div class="pill-row">
              <span class="pill">\uBCF4\uD5D8\uC0AC</span>
              <span class="pill">\uAD00\uB828\uB3C4 ${item.score || 0}</span>
            </div>
            <p class="meta-line">${item.notice}</p>
            <div class="action-row">
              <a class="doc-link" href="${item.sourceUrl}" target="_blank" rel="noreferrer">\uACF5\uC2DD \uC0AC\uC774\uD2B8 \uBCF4\uAE30</a>
              <button type="button" data-select-insurer="${item.insurerKey}">\uC120\uD0DD\uD558\uACE0 \uC0C1\uD488 \uAC80\uC0C9</button>
            </div>
          </article>
        `;
      }

      const docs = (item.documents || [])
        .map(
          (doc) => `
            <article class="doc-item">
              <div class="doc-header"><div><p class="eyebrow">${doc.type}</p><h4>${doc.title}</h4></div><span class="pill">${doc.format}</span></div>
              <p class="meta-line">\uAC1C\uC815\uC77C ${doc.revisionDate || "-"} · \uACF5\uC2DD\uCD9C\uCC98 ${item.officialSource}</p>
              <div class="action-row">
                <a class="download-link" href="${doc.url}" target="_blank" rel="noreferrer">\uB2E4\uC6B4\uB85C\uB4DC</a>
                <a class="doc-link" href="${item.sourceUrl}" target="_blank" rel="noreferrer">\uC6D0\uBB38 \uBCF4\uAE30</a>
              </div>
            </article>
          `
        )
        .join("");

      return `
        <article class="result-card ${index === 0 ? "featured" : ""}">
          <div class="card-top"><div><p class="eyebrow">${item.insurerName}</p><h3>${item.productName}</h3></div><button type="button" data-select-product="${item.id}">\uC0C1\uC138 \uBCF4\uAE30</button></div>
          <div class="pill-row">
            <span class="pill ${getStatusClass(item.status)}">${item.status}</span>
            ${item.updatedAt ? `<span class="pill">\uACF5\uC2DC ${item.updatedAt}</span>` : ""}
            <span class="pill">\uAD00\uB828\uB3C4 ${item.score || 0}</span>
          </div>
          <p class="meta-line">\uD310\uB9E4\uAE30\uAC04 ${formatDate(item.saleStartDate)} ~ ${formatDate(item.saleEndDate)}</p>
          ${item.notice ? `<p class="meta-line">${item.notice}</p>` : ""}
          <div class="doc-list">${docs || `<article class="doc-item"><h4>\uC774 \uBCF4\uD5D8\uC0AC\uB294 \uD604\uC7AC \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0 \uC911\uC2EC\uC785\uB2C8\uB2E4.</h4><div class="action-row"><a class="doc-link" href="${item.sourceUrl}" target="_blank" rel="noreferrer">\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC774\uB3D9</a></div></article>`}</div>
          <div class="action-row"><a class="doc-link" href="#detail-section">\uC774 \uC57D\uAD00\uC73C\uB85C \uBD84\uC11D\uD558\uAE30</a><a class="doc-link" href="#detail-section">\uBCF4\uD5D8\uAE08 \uCCAD\uAD6C \uC0C1\uB2F4 \uC5F0\uACB0</a></div>
        </article>
      `;
    })
    .join("");
}

function renderDetail() {
  const product = state.results.find((item) => item.id === state.selectedProductId && item.resultType !== "insurer");
  if (!product) {
    elements.detailContainer.innerHTML = `<article class="detail-card"><h3>${LABELS.beforeDetail}</h3><p class="detail-hint">${LABELS.beforeDetailHint}</p></article>`;
    return;
  }
  elements.detailContainer.innerHTML = `
    <article class="detail-card">
      <p class="eyebrow">${product.insurerName}</p>
      <h3>${product.productName}</h3>
      <div class="detail-meta">
        <span class="pill ${getStatusClass(product.status)}">${product.status}</span>
        ${product.updatedAt ? `<span class="pill">\uACF5\uC2DC \uAE30\uC900\uC77C ${product.updatedAt}</span>` : ""}
        <span class="pill">\uD310\uB9E4\uAE30\uAC04 ${formatDate(product.saleStartDate)} ~ ${formatDate(product.saleEndDate)}</span>
      </div>
      <p class="detail-hint">\uAC00\uC785 \uC2DC\uC810\uBCC4 \uC57D\uAD00 \uCC28\uC774 \uAC00\uB2A5\uC131\uC774 \uC788\uC73C\uBA70, \uD2B9\uC57D \uAD6C\uC131\uC5D0 \uB530\uB77C \uC2E4\uC81C \uBCF4\uC7A5\uC740 \uB2EC\uB77C\uC9C8 \uC218 \uC788\uC2B5\uB2C8\uB2E4.</p>
      <div class="detail-docs">
        ${(product.documents || [])
          .map(
            (doc) => `
              <article class="doc-item">
                <div class="doc-header"><div><p class="eyebrow">${doc.type}</p><h4>${doc.title}</h4></div><span class="pill">${doc.revisionDate || "-"}</span></div>
                <div class="action-row"><a class="download-link" href="${doc.url}" target="_blank" rel="noreferrer">PDF \uB2E4\uC6B4\uB85C\uB4DC</a><a class="doc-link" href="${product.sourceUrl}" target="_blank" rel="noreferrer">\uBCF4\uD5D8\uC0AC \uC6D0\uBB38 \uBCF4\uAE30</a></div>
              </article>
            `
          )
          .join("") || `<article class="doc-item"><h4>\uD604\uC7AC \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uB79C\uB529 \uC5F0\uACB0 \uC911\uC785\uB2C8\uB2E4.</h4><div class="action-row"><a class="doc-link" href="${product.sourceUrl}" target="_blank" rel="noreferrer">\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uBC14\uB85C\uAC00\uAE30</a></div></article>`}
      </div>
      <div class="action-row"><a class="download-link" href="#">\uC774 \uC57D\uAD00\uC73C\uB85C \uBCF4\uC7A5 \uBD84\uC11D\uD558\uAE30</a><a class="doc-link" href="#">\uC218\uC220\uBE44/\uC9C4\uB2E8\uBE44 \uD655\uC778</a><a class="doc-link" href="#">\uBCF4\uD5D8\uAE08 \uCCAD\uAD6C \uC0C1\uB2F4</a></div>
    </article>
  `;
}

async function fetchSearchResults(query) {
  const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("search failed");
  return response.json();
}

function getEffectiveQuery(query) {
  if (!state.selectedInsurer) return query;
  if (query.includes(state.selectedInsurer.name)) return query;
  return `${state.selectedInsurer.name} ${query}`.trim();
}

async function handleSearch(query) {
  state.query = query.trim();
  if (!state.query) {
    state.rawResults = [];
    state.results = [];
    state.selectedProductId = null;
    buildFilters();
    renderSelectedInsurer();
    renderResults();
    renderDetail();
    return;
  }

  renderSelectedInsurer();
  const insurerOnly = isInsurerOnlyQuery(state.query);
  if (insurerOnly) {
    state.rawResults = findMatchingInsurers(state.query).map(toInsurerResult);
    buildFilters();
    searchProducts(state.query);
    return;
  }

  elements.queryDisplay.textContent = "\uACF5\uC2DD \uACF5\uC2DC\uC2E4\uC744 \uC870\uD68C\uD558\uB294 \uC911\uC785\uB2C8\uB2E4";
  elements.resultsTitle.textContent = "\uBCF4\uD5D8\uC0AC \uACF5\uC2DD \uBB38\uC11C\uB97C \uC870\uD68C\uD558\uB294 \uC911\uC785\uB2C8\uB2E4";
  try {
    const payload = await fetchSearchResults(getEffectiveQuery(state.query));
    state.rawResults = (payload.results || []).map(toViewModel);
  } catch (error) {
    state.rawResults = [];
  }
  buildFilters();
  searchProducts(state.query);
}

function bindEvents() {
  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    handleSearch(elements.input.value);
  });

  document.body.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    if (target.dataset.query) {
      elements.input.value = target.dataset.query;
      handleSearch(target.dataset.query);
      document.getElementById("results-section").scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    if (target.dataset.selectProduct) {
      state.selectedProductId = target.dataset.selectProduct;
      renderDetail();
      document.getElementById("detail-section").scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    if (target.dataset.selectInsurer) {
      state.selectedInsurer = insurers.find((item) => item.key === target.dataset.selectInsurer) || null;
      renderSelectedInsurer();
      if (state.selectedInsurer) {
        elements.input.value = `${state.selectedInsurer.name} `;
        elements.input.focus();
        elements.input.setSelectionRange(elements.input.value.length, elements.input.value.length);
      }
      return;
    }

    if (target.dataset.clearInsurer) {
      state.selectedInsurer = null;
      renderSelectedInsurer();
      elements.input.value = "";
      elements.input.focus();
    }
  });

  [elements.insurerFilter, elements.docTypeFilter, elements.statusFilter, elements.sortFilter].forEach((select) => {
    select.addEventListener("change", () => {
      state.filters = {
        insurer: elements.insurerFilter.value,
        docType: elements.docTypeFilter.value,
        status: elements.statusFilter.value,
        sort: elements.sortFilter.value,
      };
      searchProducts(state.query);
    });
  });

  elements.retrySimilar.addEventListener("click", () => {
    elements.emptySuggestions.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

function init() {
  renderSuggestedKeywords();
  renderAdmin();
  fillSelect(elements.insurerFilter, [LABELS.all]);
  fillSelect(elements.docTypeFilter, [LABELS.all]);
  fillSelect(elements.statusFilter, [LABELS.all]);
  renderSelectedInsurer();
  renderResults();
  renderDetail();
  bindEvents();
  handleSearch("DB\uC190\uD574\uBCF4\uD5D8 \uC2E4\uC190");
}

init();
