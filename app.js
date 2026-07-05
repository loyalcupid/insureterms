const suggestedQueries = [];
const ADMIN_STORAGE_KEY = "insurance-admin-authenticated";
const ADMIN_CREDENTIALS = {
  id: "bankme",
  password: "bank1234!",
};

const insurerCategories = [
  { key: "non-life", name: "\uC190\uD574\uBCF4\uD5D8\uD68C\uC0AC", description: "\uD604\uC7AC \uC57D\uAD00\uCC3E\uAE30 \uC9C0\uC6D0 \uBCF4\uD5D8\uC0AC" },
  { key: "life", name: "\uC0DD\uBA85\uBCF4\uD5D8\uD68C\uC0AC", description: "\uD68C\uC0AC \uBAA9\uB85D\uB9CC \uC81C\uACF5, \uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911" },
];

const insurers = [
  { key: "kb", category: "non-life", name: "KB\uC190\uD574\uBCF4\uD5D8", aliases: ["kb", "kb\uC190\uD574\uBCF4\uD5D8", "kb\uC190\uBCF4", "\uCF00\uC774\uBE44"], officialUrl: "https://www.kbinsure.co.kr/CG802030001.ecs", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "db", category: "non-life", name: "DB\uC190\uD574\uBCF4\uD5D8", aliases: ["db", "db\uC190\uD574\uBCF4\uD5D8", "db\uC190\uBCF4", "\uB3D9\uBD80\uD654\uC7AC"], officialUrl: "https://www.idbins.com/FWMAIV1535.do", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "hyundai", category: "non-life", name: "\uD604\uB300\uD574\uC0C1", aliases: ["\uD604\uB300\uD574\uC0C1", "\uD604\uB300", "\uD558\uC774\uCE74"], officialUrl: "https://children.hi.co.kr/bin/CI/ON/CION3200G.jsp", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "samsung", category: "non-life", name: "\uC0BC\uC131\uD654\uC7AC", aliases: ["\uC0BC\uC131\uD654\uC7AC", "\uC0BC\uC131"], officialUrl: "https://www.samsungfire.com/vh/page/VH.REIF0011.do", coverage: "\uC2E4\uC81C \uACF5\uC2DD API + PDF \uC5F0\uACB0", searchEnabled: true },
  { key: "lotte", category: "non-life", name: "\uB86F\uB370\uC190\uD574\uBCF4\uD5D8", aliases: ["\uB86F\uB370\uC190\uD574\uBCF4\uD5D8", "\uB86F\uB370", "\uB86F\uB370\uC190\uBCF4"], officialUrl: "https://www.lotteins.co.kr/web/C/D/H/cdh190.jsp", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "nhfire", category: "non-life", name: "NH\uB18D\uD611\uC190\uD574\uBCF4\uD5D8", aliases: ["nh\uB18D\uD611\uC190\uD574\uBCF4\uD5D8", "nh\uB18D\uD611", "\uB18D\uD611\uC190\uD574\uBCF4\uD5D8", "\uB18D\uD611\uC190\uBCF4", "nh\uC190\uD574\uBCF4\uD5D8", "nh\uC190\uBCF4"], officialUrl: "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "meritz", category: "non-life", name: "\uBA54\uB9AC\uCE20\uD654\uC7AC", aliases: ["\uBA54\uB9AC\uCE20\uD654\uC7AC", "\uBA54\uB9AC\uCE20", "\uBA54\uB9AC\uCE20\uC190\uBCF4"], officialUrl: "https://store.meritzfire.com/disclosure/product.do", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "hanwhafire", category: "non-life", name: "\uD55C\uD654\uC190\uD574\uBCF4\uD5D8", aliases: ["\uD55C\uD654\uC190\uD574\uBCF4\uD5D8", "\uD55C\uD654\uC190\uBCF4", "\uD55C\uD654\uD654\uC7AC"], officialUrl: "https://m.hwgeneralins.com/product/catalog/product-info.do", coverage: "\uC2E4\uC81C \uACF5\uC2DD API + PDF \uC5F0\uACB0", searchEnabled: true },
  { key: "heungkuk", category: "non-life", name: "\uD765\uAD6D\uD654\uC7AC", aliases: ["\uD765\uAD6D\uD654\uC7AC", "\uD765\uAD6D"], officialUrl: "https://m.heungkukfire.co.kr/product/insr/CPDIS0001_M00/CPDIS0001_M00.do", coverage: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0", searchEnabled: true },
  { key: "mg", category: "non-life", name: "MG\uC190\uD574\uBCF4\uD5D8(\uC608\uBCC4\uC190\uD574\uBCF4\uD5D8)", aliases: ["mg\uC190\uD574\uBCF4\uD5D8", "mg\uC190\uBCF4", "mg", "\uC608\uBCC4\uC190\uD574\uBCF4\uD5D8", "\uC608\uBCC4\uC190\uBCF4", "yebyeol", "mggeneral"], officialUrl: "https://www.yebyeol.co.kr/PB031210DM.scp?menuId=MN0803006", coverage: "\uC2E4\uC81C \uACF5\uC2DD AJAX + PDF \uC5F0\uACB0", searchEnabled: true },
  { key: "abl-life", category: "life", name: "ABL\uC0DD\uBA85", aliases: ["abl\uC0DD\uBA85", "abl"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "samsung-life", category: "life", name: "\uC0BC\uC131\uC0DD\uBA85", aliases: ["\uC0BC\uC131\uC0DD\uBA85"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "db-life", category: "life", name: "DB\uC0DD\uBA85", aliases: ["db\uC0DD\uBA85"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "kb-life", category: "life", name: "KB\uB77C\uC774\uD504", aliases: ["kb\uB77C\uC774\uD504", "kb life"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "kyobo-life", category: "life", name: "\uAD50\uBCF4\uC0DD\uBA85", aliases: ["\uAD50\uBCF4\uC0DD\uBA85", "\uAD50\uBCF4"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "metlife", category: "life", name: "\uBA54\uD2B8\uB77C\uC774\uD504", aliases: ["\uBA54\uD2B8\uB77C\uC774\uD504", "metlife"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "shinhan-life", category: "life", name: "\uC2E0\uD55C\uB77C\uC774\uD504", aliases: ["\uC2E0\uD55C\uB77C\uC774\uD504"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "tongyang-life", category: "life", name: "\uB3D9\uC591\uC0DD\uBA85", aliases: ["\uB3D9\uC591\uC0DD\uBA85"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
  { key: "linea-life", category: "life", name: "\uB77C\uC774\uB098\uC0DD\uBA85", aliases: ["\uB77C\uC774\uB098\uC0DD\uBA85", "\uB77C\uC774\uB098"], coverage: "\uC57D\uAD00\uCC3E\uAE30 \uC900\uBE44 \uC911", searchEnabled: false },
];

const insurerCategoryMap = Object.fromEntries(insurerCategories.map((category) => [category.key, category]));
const searchableInsurers = insurers.filter((item) => item.searchEnabled);

const genericTerms = ["\uBCF4\uD5D8", "\uC57D\uAD00", "\uC0C1\uD488", "\uC694\uC57D\uC11C", "\uC0AC\uC5C5\uBC29\uBC95\uC11C", "\uB2E4\uC6B4\uB85C\uB4DC", "\uAC80\uC0C9", "\uCC3E\uAE30", "\uACF5\uC2DC\uC2E4"];

const adminCards = [
  {
    title: "\uBCF4\uD5D8\uC0AC\uBCC4 \uBB38\uC11C \uC218\uC9D1 \uD604\uD669",
    body: "\uC2E4\uC81C \uD06C\uB864\uB9C1 \uC5F0\uACB0\uC740 KB\uC190\uD574\uBCF4\uD5D8, DB\uC190\uD574\uBCF4\uD5D8, \uD604\uB300\uD574\uC0C1, \uC0BC\uC131\uD654\uC7AC, \uB86F\uB370\uC190\uD574\uBCF4\uD5D8, NH\uB18D\uD611\uC190\uD574\uBCF4\uD5D8, \uD765\uAD6D\uD654\uC7AC, \uD55C\uD654\uC190\uD574\uBCF4\uD5D8 \uC5B4\uB311\uD130\uB97C \uC6B0\uC120 \uAD6C\uC131\uD588\uACE0, MG\uC190\uD574\uBCF4\uD5D8(\uC608\uBCC4\uC190\uD574\uBCF4\uD5D8)\uB3C4 \uACF5\uC2DD AJAX + PDF \uBC29\uC2DD\uC73C\uB85C \uCD94\uAC00\uD588\uC2B5\uB2C8\uB2E4.",
    items: ["KB \uC0C1\uC138 \uC57D\uAD00 \uD06C\uB864\uB9C1", "DB \uAC80\uC0C9 API \uC5F0\uACB0", "\uD604\uB300\uD574\uC0C1 \uC804\uCCB4 \uC0C1\uD488\uBAA9\uB85D + PDF \uC5F0\uACB0", "\uC0BC\uC131\uD654\uC7AC \uC0C1\uD488\uACF5\uC2DC API + PDF \uC5F0\uACB0", "\uB86F\uB370\uC190\uD574\uBCF4\uD5D8 \uC0C1\uD488\uBAA9\uB85D + \uD310\uB9E4\uAE30\uAC04 + PDF \uC5F0\uACB0", "NH\uB18D\uD611\uC190\uD574\uBCF4\uD5D8 \uC0C1\uD488\uACF5\uC2DC + \uC0C1\uC138 PDF \uD504\uB85D\uC2DC \uC5F0\uACB0", "\uD765\uAD6D\uD654\uC7AC CSRF \uC138\uC158 + PDF \uD504\uB85D\uC2DC \uC5F0\uACB0", "\uD55C\uD654\uC190\uD574\uBCF4\uD5D8 \uBAA8\uBC14\uC77C \uC0C1\uD488 API + PDF \uC5F0\uACB0", "MG/\uC608\uBCC4 \uC0C1\uD488\uBAA9\uB85D AJAX + \uBB38\uC11C \uD3FC \uB2E4\uC6B4\uB85C\uB4DC \uC5F0\uACB0"],
  },
  {
    title: "\uB9C1\uD06C \uC804\uB7B5",
    body: "\uCD08\uAE30 MVP\uB294 \uACF5\uC2DD \uBB38\uC11C URL \uC5F0\uACB0\uC744 \uC6B0\uC120\uD558\uACE0 \uACF5\uC2DD \uCD9C\uCC98 \uD45C\uC2DC\uB97C \uC720\uC9C0\uD569\uB2C8\uB2E4.",
    items: ["KB: CG802030003.ec", "DB: cYakgwanDown.do", "\uC0BC\uC131: VH.HDIF0103 + publication/pdf", "\uB86F\uB370: CChannelSvl + cdh190_result.jsp", "NH\uB18D\uD611: retrieveProduct + downloadFile.ajax", "\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uBC14\uB85C\uAC00\uAE30"],
  },
  {
    title: "\uAC80\uC0C9 \uD750\uB984",
    body: "\uC790\uC5F0\uC5B4 \uC785\uB825\uC5D0\uC11C \uBCF4\uD5D8\uC0AC \uBCC4\uCE6D\uC744 \uD30C\uC2F1\uD558\uACE0 \uC81C\uD488\uBA85 \uD0A4\uC6CC\uB4DC\uB97C \uAC01 \uBCF4\uD5D8\uC0AC \uACF5\uC2DD \uAC80\uC0C9 \uAD6C\uC870\uB85C \uBCF4\uB0C5\uB2C8\uB2E4.",
    items: ["\uBCC4\uCE6D \uC778\uC2DD", "\uD0A4\uC6CC\uB4DC \uC815\uB9AC", "\uACB0\uACFC \uB7AD\uD0B9 \uD6C4 \uC0C1\uC138 \uD655\uC7A5"],
  },
  {
    title: "\uB2E4\uC74C \uD655\uC7A5",
    body: "\uB098\uBA38\uC9C0 \uBCF4\uD5D8\uC0AC\uB294 \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uAD6C\uC870 \uBD84\uC11D\uC744 \uC774\uC5B4\uC11C \uCD94\uAC00 \uC5B4\uB311\uD130\uB97C \uBD99\uC774\uBA74 \uB429\uB2C8\uB2E4.",
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
  beforeDetailHint: "\uD604\uC7AC\uB294 KB\uC190\uD574\uBCF4\uD5D8, DB\uC190\uD574\uBCF4\uD5D8, \uD604\uB300\uD574\uC0C1, \uC0BC\uC131\uD654\uC7AC, \uB86F\uB370\uC190\uD574\uBCF4\uD5D8, NH\uB18D\uD611\uC190\uD574\uBCF4\uD5D8, \uBA54\uB9AC\uCE20\uD654\uC7AC, \uD765\uAD6D\uD654\uC7AC, \uD55C\uD654\uC190\uD574\uBCF4\uD5D8, MG\uC190\uD574\uBCF4\uD5D8(\uC608\uBCC4\uC190\uD574\uBCF4\uD5D8)\uC744 \uC2E4\uC81C \uC5F0\uACB0\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.",
  currentSale: "\uD604\uC7AC \uD310\uB9E4",
  lifeCategoryNoticeTitle: "\uC0DD\uBA85\uBCF4\uD5D8\uC0AC \uC57D\uAD00\uCC3E\uAE30\uB294 \uC21C\uCC28\uC801\uC73C\uB85C \uCD94\uAC00\uD560 \uC608\uC815\uC785\uB2C8\uB2E4.",
  lifeCategoryNoticeBody: "\uC6D0\uD558\uC2DC\uB294 \uD68C\uC0AC\uB97C \uBA3C\uC800 \uC120\uD0DD\uD574 \uB450\uBA74 \uB2E4\uC74C \uC5F0\uB3D9 \uC6B0\uC120\uC21C\uC704\uB97C \uC815\uD558\uAE30 \uC26C\uC6CC\uC9D1\uB2C8\uB2E4.",
  lifeInsurerSelected: (name) => `${name} \uC57D\uAD00\uCC3E\uAE30\uB294 \uC544\uC9C1 \uC900\uBE44 \uC911\uC785\uB2C8\uB2E4.`,
};

const state = {
  query: "",
  selectedCategory: null,
  selectedInsurer: null,
  rawResults: [],
  results: [],
  hasSearched: false,
  isSearching: false,
};

const elements = {
  form: document.getElementById("search-form"),
  input: document.getElementById("search-input"),
  resultsSection: document.getElementById("results-section"),
  resultsContainer: document.getElementById("results-container"),
  resultsTitle: document.getElementById("results-title"),
  resultCount: document.getElementById("result-count"),
  queryDisplay: document.getElementById("query-display"),
  emptyState: document.getElementById("empty-state"),
  emptySuggestions: document.getElementById("empty-suggestions"),
  retrySimilar: document.getElementById("retry-similar"),
  suggestedKeywords: document.getElementById("suggested-keywords"),
  insurerCategoryButtons: document.getElementById("insurer-category-buttons"),
  insurerButtons: document.getElementById("insurer-buttons"),
  productSearchArea: document.getElementById("product-search-area"),
  lifeInsurerNotice: document.getElementById("life-insurer-notice"),
  adminGrid: document.getElementById("admin-grid"),
  selectedInsurer: document.getElementById("selected-insurer"),
  adminLoginSection: document.getElementById("admin-login-section"),
  adminSection: document.getElementById("admin-section"),
  adminLoginForm: document.getElementById("admin-login-form"),
  adminIdInput: document.getElementById("admin-id"),
  adminPasswordInput: document.getElementById("admin-password"),
  adminLoginMessage: document.getElementById("admin-login-message"),
  adminLogoutButton: document.getElementById("admin-logout-button"),
};

function isAdminPage() {
  return Boolean(elements.adminLoginForm || elements.adminSection);
}

function isAdminAuthenticated() {
  return window.localStorage.getItem(ADMIN_STORAGE_KEY) === "true";
}

function setAdminAuthenticated(value) {
  if (value) {
    window.localStorage.setItem(ADMIN_STORAGE_KEY, "true");
  } else {
    window.localStorage.removeItem(ADMIN_STORAGE_KEY);
  }
}

function setAdminMessage(message, isError = false) {
  if (!elements.adminLoginMessage) return;
  if (!message) {
    elements.adminLoginMessage.textContent = "";
    elements.adminLoginMessage.classList.add("hidden");
    elements.adminLoginMessage.classList.remove("error", "success");
    return;
  }

  elements.adminLoginMessage.textContent = message;
  elements.adminLoginMessage.classList.remove("hidden");
  elements.adminLoginMessage.classList.toggle("error", isError);
  elements.adminLoginMessage.classList.toggle("success", !isError);
}

function updateAdminVisibility() {
  if (!isAdminPage()) return;
  const authenticated = isAdminAuthenticated();
  elements.adminLoginSection?.classList.toggle("hidden", authenticated);
  elements.adminSection?.classList.toggle("hidden", !authenticated);

  if (authenticated) {
    setAdminMessage("");
    renderAdmin();
  } else {
    elements.adminGrid && (elements.adminGrid.innerHTML = "");
  }
}

function handleAdminLogin(event) {
  event.preventDefault();
  const enteredId = elements.adminIdInput?.value?.trim() || "";
  const enteredPassword = elements.adminPasswordInput?.value || "";

  const matches =
    enteredId === ADMIN_CREDENTIALS.id &&
    enteredPassword === ADMIN_CREDENTIALS.password;

  if (!matches) {
    setAdminAuthenticated(false);
    setAdminMessage("아이디 또는 비밀번호가 올바르지 않습니다.", true);
    elements.adminPasswordInput?.focus();
    elements.adminPasswordInput && (elements.adminPasswordInput.value = "");
    updateAdminVisibility();
    return;
  }

  setAdminAuthenticated(true);
  setAdminMessage("로그인되었습니다.");
  elements.adminLoginForm?.reset();
  updateAdminVisibility();
}

function handleAdminLogout() {
  setAdminAuthenticated(false);
  updateAdminVisibility();
  setAdminMessage("");
  elements.adminIdInput?.focus();
}

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

function renderSuggestedKeywords() {
  if (!elements.suggestedKeywords) return;
  elements.suggestedKeywords.innerHTML = suggestedQueries.map((query) => `<button class="chip" type="button" data-query="${query}">${query}</button>`).join("");
}

function getSelectedCategory() {
  return insurerCategoryMap[state.selectedCategory] || null;
}

function getVisibleInsurers() {
  if (!state.selectedCategory) return [];
  return insurers.filter((item) => item.category === state.selectedCategory);
}

function renderInsurerCategoryButtons() {
  if (!elements.insurerCategoryButtons) return;
  elements.insurerCategoryButtons.innerHTML = insurerCategories
    .map(
      (category) => `
        <button
          type="button"
          class="insurer-category-button ${state.selectedCategory === category.key ? "active" : ""}"
          data-select-category="${category.key}"
        >
          <span>${category.name}</span>
          <small>${category.description}</small>
        </button>
      `
    )
    .join("");
}

function renderInsurerButtons() {
  const visibleInsurers = getVisibleInsurers();
  elements.insurerButtons.innerHTML = visibleInsurers
    .map(
      (insurer) => `
        <button
          type="button"
          class="insurer-button ${state.selectedInsurer?.key === insurer.key ? "active" : ""}"
          data-select-insurer="${insurer.key}"
        >
          <span>${insurer.name}</span>
          <small>${insurer.coverage}</small>
        </button>
      `
    )
    .join("");
}

function renderAdmin() {
  if (!elements.adminGrid) return;
  elements.adminGrid.innerHTML = adminCards
    .map((card) => `<article class="admin-panel"><h4>${card.title}</h4><p class="admin-meta">${card.body}</p><ul>${card.items.map((item) => `<li>${item}</li>`).join("")}</ul></article>`)
    .join("");
}

function renderSelectedInsurer() {
  const selectedCategory = getSelectedCategory();
  const selectedInsurer = state.selectedInsurer;
  const isLifeCategory = selectedCategory?.key === "life";
  const canSearch = Boolean(selectedInsurer?.searchEnabled);

  renderInsurerCategoryButtons();
  renderInsurerButtons();

  if (elements.lifeInsurerNotice) {
    if (isLifeCategory) {
      elements.lifeInsurerNotice.classList.remove("hidden");
      elements.lifeInsurerNotice.innerHTML = `
        <strong>${LABELS.lifeCategoryNoticeTitle}</strong>
        <p class="helper-text">${selectedInsurer ? LABELS.lifeInsurerSelected(selectedInsurer.name) : LABELS.lifeCategoryNoticeBody}</p>
      `;
    } else {
      elements.lifeInsurerNotice.classList.add("hidden");
      elements.lifeInsurerNotice.innerHTML = "";
    }
  }

  if (!selectedInsurer) {
    elements.selectedInsurer.classList.add("hidden");
    elements.selectedInsurer.innerHTML = "";
    elements.productSearchArea.classList.add("hidden");
    return;
  }

  elements.selectedInsurer.classList.remove("hidden");
  elements.productSearchArea.classList.toggle("hidden", !canSearch);
  elements.selectedInsurer.innerHTML = `
    <span class="pill">${selectedInsurer.name} \uC120\uD0DD\uB428</span>
    <span class="helper-text">${canSearch ? `${selectedInsurer.name} \uC0C1\uD488\uBA85\uC758 \uC77C\uBD80\uB9CC \uC785\uB825\uD574\uB3C4 \uC720\uC0AC\uD55C \uC57D\uAD00\uC744 \uCC3E\uC2B5\uB2C8\uB2E4.` : LABELS.lifeInsurerSelected(selectedInsurer.name)}</span>
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
  return searchableInsurers
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

function stripInsurerName(query, insurer) {
  let stripped = query;
  for (const alias of [insurer.name, ...insurer.aliases]) {
    stripped = stripped.replace(new RegExp(alias, "ig"), " ");
  }
  return stripGenericTerms(stripped);
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
      title: doc.displayTitle || doc.type || doc.title,
      fileTitle: doc.title || doc.displayTitle || doc.type,
      revisionDate: doc.revisionDate || doc.saleStartDate || "",
      url: doc.url,
      format: doc.format || "PDF",
    })),
  };
}

function computeScore(product, queryTokens) {
  if (product.resultType === "insurer") return product.score || 0;
  if (!queryTokens.length) return product.score ?? 0;
  const haystack = [product.insurerName, product.productName, product.insuranceType ?? "", ...(product.documents || []).map((doc) => `${doc.type} ${doc.title}`)]
    .join(" ")
    .toLowerCase();
  return queryTokens.reduce((score, token) => (haystack.includes(token) ? score + 4 : score), product.score ?? 0);
}

function getRecencyValue(item) {
  const candidates = [
    item.updatedAt,
    item.saleStartDate,
    ...(item.documents || []).map((doc) => doc.revisionDate || doc.saleStartDate || ""),
  ];
  for (const value of candidates) {
    if (!value) continue;
    const numeric = Number(String(value).replace(/\D/g, "").slice(0, 8));
    if (numeric) return numeric;
  }
  return 0;
}

function sortResults(items) {
  const insurerCards = items.filter((item) => item.resultType === "insurer");
  let filtered = items.filter((item) => item.resultType !== "insurer");
  if (state.selectedInsurer) filtered = filtered.filter((item) => item.provider === state.selectedInsurer.key);
  filtered.sort(
    (a, b) =>
      getRecencyValue(b) - getRecencyValue(a) ||
      (b.score || 0) - (a.score || 0) ||
      a.productName.localeCompare(b.productName)
  );
  return [...insurerCards, ...filtered];
}

async function fetchSearchResults(query, insurerKey = null) {
  const params = new URLSearchParams({ q: query });
  if (insurerKey) params.set("insurer", insurerKey);
  const response = await fetch(`/api/search?${params.toString()}`);
  if (!response.ok) throw new Error("search failed");
  return response.json();
}

function searchProducts(query) {
  const queryTokens = tokenize(query);
  state.results = sortResults(state.rawResults.map((item) => ({ ...item, score: computeScore(item, queryTokens) })));
  renderResults();
}

function scrollToResults() {
  elements.resultsSection?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderResults() {
  const hasResults = state.results.length > 0;
  const showResultsSection = state.hasSearched || state.isSearching;
  const showEmptyState = state.hasSearched && !hasResults;
  const displayQuery = [state.selectedInsurer?.name, state.query].filter(Boolean).join(" ");
  elements.resultsSection.classList.toggle("hidden", !showResultsSection);
  elements.queryDisplay.textContent = displayQuery ? LABELS.searched(displayQuery) : LABELS.searching;
  elements.resultCount.textContent = `${state.results.length}\uAC74`;
  elements.resultsTitle.textContent = hasResults ? LABELS.resultTitle : LABELS.noResultTitle;
  elements.emptyState.classList.toggle("hidden", !showEmptyState || state.isSearching);
  if (state.isSearching) {
    elements.resultsTitle.textContent = "보험약관을 찾는 중입니다. 잠시만 기다려주세요";
    elements.queryDisplay.textContent = "공식 공시실을 조회하는 중입니다";
    elements.resultCount.textContent = "";
    elements.resultsContainer.innerHTML = `
      <article class="result-card loading-card">
        <div class="loading-indicator" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p class="meta-line loading-text">열심히 찾고 있어요</p>
      </article>
    `;
    return;
  }
  if (!hasResults) {
    elements.resultsContainer.innerHTML = "";
    if (elements.emptySuggestions) {
      elements.emptySuggestions.innerHTML = suggestedQueries.map((query) => `<button class="chip" type="button" data-query="${query}">${query}</button>`).join("");
    }
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
              </div>
            </article>
          `
        )
        .join("");

      return `
        <article class="result-card ${index === 0 ? "featured" : ""}">
          <div class="card-top"><div><p class="eyebrow">${item.insurerName}</p><h3>${item.productName}</h3></div></div>
          <div class="pill-row">
            <span class="pill ${getStatusClass(item.status)}">${item.status}</span>
            ${item.updatedAt ? `<span class="pill">\uACF5\uC2DC ${item.updatedAt}</span>` : ""}
            <span class="pill">\uAD00\uB828\uB3C4 ${item.score || 0}</span>
          </div>
          <p class="meta-line">\uD310\uB9E4\uAE30\uAC04 ${formatDate(item.saleStartDate)} ~ ${formatDate(item.saleEndDate)}</p>
          ${item.notice ? `<p class="meta-line">${item.notice}</p>` : ""}
          <div class="doc-list">${docs || `<article class="doc-item"><h4>\uC774 \uBCF4\uD5D8\uC0AC\uB294 \uD604\uC7AC \uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC5F0\uACB0 \uC911\uC2EC\uC785\uB2C8\uB2E4.</h4><div class="action-row"><a class="doc-link" href="${item.sourceUrl}" target="_blank" rel="noreferrer">\uACF5\uC2DD \uACF5\uC2DC\uC2E4 \uC774\uB3D9</a></div></article>`}</div>
        </article>
      `;
    })
    .join("");
}

async function handleSearch(query) {
  state.query = query.trim();
  state.hasSearched = Boolean(state.query);
  state.isSearching = false;
  if (!state.query) {
    state.rawResults = [];
    state.results = [];
    renderSelectedInsurer();
    renderResults();
    return;
  }

  renderSelectedInsurer();
  if (!state.selectedInsurer) {
    state.rawResults = [];
    state.results = [];
    renderResults();
    return;
  }
  if (!state.selectedInsurer.searchEnabled) {
    state.rawResults = [];
    state.results = [];
    renderResults();
    return;
  }
  const insurerOnly = isInsurerOnlyQuery(state.query);
  if (insurerOnly) {
    state.rawResults = findMatchingInsurers(state.query).map(toInsurerResult);
    searchProducts(state.query);
    return;
  }

  state.isSearching = true;
  state.rawResults = [];
  state.results = [];
  renderResults();
  scrollToResults();
  try {
    const payload = await fetchSearchResults(state.query, state.selectedInsurer?.key || null);
    state.rawResults = (payload.results || []).map(toViewModel);
  } catch (error) {
    state.rawResults = [];
  } finally {
    state.isSearching = false;
  }
  searchProducts(state.query);
}

function bindEvents() {
  if (elements.form) {
    elements.form.addEventListener("submit", (event) => {
      event.preventDefault();
      handleSearch(elements.input.value);
    });
  }

  if (elements.adminLoginForm) {
    elements.adminLoginForm.addEventListener("submit", handleAdminLogin);
  }

  if (elements.adminLogoutButton) {
    elements.adminLogoutButton.addEventListener("click", handleAdminLogout);
  }

  document.body.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const queryTarget = target.closest("[data-query]");
    const selectCategoryTarget = target.closest("[data-select-category]");
    const selectInsurerTarget = target.closest("[data-select-insurer]");
    const clearInsurerTarget = target.closest("[data-clear-insurer]");

    if (queryTarget instanceof HTMLElement) {
      const { query } = queryTarget.dataset;
      if (!query) return;
      const matchedInsurer = findMatchingInsurers(query)[0] || null;
      if (matchedInsurer) {
        state.selectedCategory = matchedInsurer.category;
        state.selectedInsurer = matchedInsurer;
        const productQuery = stripInsurerName(query, matchedInsurer);
        elements.input.value = productQuery;
        renderSelectedInsurer();
        handleSearch(productQuery);
      } else {
        elements.input.value = query;
        handleSearch(query);
      }
      scrollToResults();
      return;
    }

    if (selectCategoryTarget instanceof HTMLElement) {
      const { selectCategory } = selectCategoryTarget.dataset;
      if (!selectCategory) return;
      state.selectedCategory = selectCategory;
      state.selectedInsurer = null;
      state.query = "";
      state.rawResults = [];
      state.results = [];
      state.hasSearched = false;
      state.isSearching = false;
      renderSelectedInsurer();
      renderResults();
      elements.input.value = "";
      return;
    }

    if (selectInsurerTarget instanceof HTMLElement) {
      const { selectInsurer } = selectInsurerTarget.dataset;
      if (!selectInsurer) return;
      state.selectedInsurer = insurers.find((item) => item.key === selectInsurer) || null;
      state.selectedCategory = state.selectedInsurer?.category || state.selectedCategory;
      state.query = "";
      state.rawResults = [];
      state.results = [];
      state.hasSearched = false;
      state.isSearching = false;
      renderSelectedInsurer();
      renderResults();
      if (state.selectedInsurer?.searchEnabled) {
        elements.input.value = "";
        elements.input.focus();
      }
      return;
    }

    if (clearInsurerTarget instanceof HTMLElement) {
      state.selectedInsurer = null;
      state.query = "";
      state.rawResults = [];
      state.results = [];
      state.hasSearched = false;
      state.isSearching = false;
      renderSelectedInsurer();
      renderResults();
      elements.input.value = "";
    }
  });

  if (elements.retrySimilar && elements.emptySuggestions) {
    elements.retrySimilar.addEventListener("click", () => {
      elements.emptySuggestions.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }
}

function init() {
  if (elements.form) {
    renderSuggestedKeywords();
    renderInsurerCategoryButtons();
    renderInsurerButtons();
    renderSelectedInsurer();
    renderResults();
  }
  updateAdminVisibility();
  bindEvents();
}

init();
