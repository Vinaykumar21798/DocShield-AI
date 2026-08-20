(function () {
  const STORAGE_KEY = "docshield-ui-state-v1";
  const THEME_KEY = "docshield-ui-theme";
  const AUTH_KEY = "docshield-ui-auth";
  const POLL_MS = 4000;

  const els = {
    apiBase: document.getElementById("apiBase"),
    apiMenuTrigger: document.getElementById("apiMenuTrigger"),
    apiMenu: document.getElementById("apiMenu"),
    healthBtn: document.getElementById("healthBtn"),
    healthBadge: document.getElementById("healthBadge"),
    uploadForm: document.getElementById("uploadForm"),
    fileInput: document.getElementById("fileInput"),
    fileSummary: document.getElementById("fileSummary"),
    fileList: document.getElementById("fileList"),
    dropZone: document.getElementById("dropZone"),
    documentList: document.getElementById("documentList"),
    documentListBody: document.getElementById("documentListBody"),
    recentCount: document.getElementById("recentCount"),
    clearRecentBtn: document.getElementById("clearRecentBtn"),
    documentIdInput: document.getElementById("documentIdInput"),
    loadDocumentBtn: document.getElementById("loadDocumentBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    activeFilename: document.getElementById("activeFilename"),
    processingBadge: document.getElementById("processingBadge"),
    statusDetails: document.getElementById("statusDetails"),
    reportTimestamp: document.getElementById("reportTimestamp"),
    metricEntities: document.getElementById("metricEntities"),
    metricPii: document.getElementById("metricPii"),
    metricPhi: document.getElementById("metricPhi"),
    metricPending: document.getElementById("metricPending"),
    metricFilters: Array.from(document.querySelectorAll("[data-review-filter]")),
    reviewSummary: document.getElementById("reviewSummary"),
    reviewsHead: document.getElementById("reviewsHead"),
    reviewsBody: document.getElementById("reviewsBody"),
    toggleValuesBtn: document.getElementById("toggleValuesBtn"),
    llmAuditSummary: document.getElementById("llmAuditSummary"),
    llmAuditBody: document.getElementById("llmAuditBody"),
    tabLlmAccepted: document.getElementById("tabLlmAccepted"),
    tabLlmRejected: document.getElementById("tabLlmRejected"),
    countLlmAccepted: document.getElementById("countLlmAccepted"),
    countLlmRejected: document.getElementById("countLlmRejected"),
    textMeta: document.getElementById("textMeta"),
    textPreview: document.getElementById("textPreview"),
    copyTextBtn: document.getElementById("copyTextBtn"),
    artifactList: document.getElementById("artifactList"),
    toast: document.getElementById("toast"),
    workflowItems: Array.from(document.querySelectorAll(".workflow-item")),
    themeToggle: document.getElementById("themeToggle"),
    profileMenuTrigger: document.getElementById("profileMenuTrigger"),
    profileMenu: document.getElementById("profileMenu"),
    userInitials: document.getElementById("userInitials"),
  };

  const state = {
    apiBase: defaultApiBase(),
    documents: [],
    activeDocumentId: "",
    dashboard: {
      status: null,
      text: null,
      reviews: [],
      entities: [],
      reports: [],
      redactions: [],
      reportDetail: null,
      llmAudit: { accepted: [], rejected: [] },
    },
    revealValues: false,
    activeReviewFilter: "all",
    activeLlmTab: "accepted",
    admin: { users: [], loading: false },
    recentDocumentsLoading: false,
    recentDocumentsError: "",
    dashboardLoadSequence: 0,
    pollTimer: null,
  };

  const REVIEW_FILTERS = {
    all: "Total entities",
    pii: "PII",
    phi: "PHI",
    pending: "Pending review",
  };

  const COMPLETED_REVIEW_STATUSES = [
    "APPROVED",
    "CONFIRMED",
    "CORRECTED",
    "REJECTED",
    "SKIPPED",
  ];
  function defaultApiBase() {
    if (window.location.protocol === "file:") {
      return "http://localhost:8001";
    }
    return window.location.origin;
  }

  function getAuth() {
    try {
      const parsed = JSON.parse(localStorage.getItem(AUTH_KEY) || "null");
      if (parsed && parsed.token && parsed.user) {
        return parsed;
      }
    } catch (error) {
      /* ignore corrupt storage */
    }
    return null;
  }

  function setAuth(token, user) {
    localStorage.setItem(AUTH_KEY, JSON.stringify({ token, user }));
  }

  function clearAuth() {
    localStorage.removeItem(AUTH_KEY);
  }

  function redirectToLogin() {
    window.location.href = "login.html";
  }

  function isAuthenticated() {
    return Boolean(getAuth());
  }

  function currentRole() {
    const auth = getAuth();
    return auth && auth.user ? auth.user.role : null;
  }

  function renderUserChip() {
    const auth = getAuth();
    const chip = document.getElementById("userChip");
    const nameEl = document.getElementById("userName");
    const roleEl = document.getElementById("userRole");
    if (!auth || !chip) return;
    const displayName = auth.user.name || auth.user.email || "User";
    if (nameEl) nameEl.textContent = displayName;
    if (roleEl) roleEl.textContent = auth.user.role || "USER";
    if (els.userInitials) {
      const nameParts = displayName.trim().split(/\s+/).filter(Boolean);
      const initials = nameParts.length > 1
        ? `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`
        : displayName.slice(0, 2);
      els.userInitials.textContent = initials.toUpperCase();
    }
    if (els.profileMenuTrigger) {
      els.profileMenuTrigger.setAttribute("aria-label", `Open profile menu for ${displayName}`);
    }
    chip.style.display = "flex";
    document.body.setAttribute("data-role", auth.user.role || "USER");
  }

  function applyRoleVisibility() {
    const role = currentRole();
    if (!role) return;
    document.body.setAttribute("data-role", role);

    const adminPanel = document.getElementById("adminPanel");
    if (adminPanel) {
      adminPanel.classList.toggle("is-visible", role === "ADMIN");
    }
    if (role === "ADMIN") {
      loadAdminPanel();
    }
    if (role === "REVIEWER") {
      state.activeReviewFilter = "all";
      renderReviews();
    }
    els.metricFilters.forEach((button) => {
      const isUserMetric = role === "USER";
      button.disabled = isUserMetric;
      button.setAttribute("aria-disabled", String(isUserMetric));
    });
  }

  function renderAdminDocuments(documents) {
    const body = document.getElementById("adminDocumentsBody");
    if (!body) return;
    if (!Array.isArray(documents) || !documents.length) {
      body.innerHTML = `<tr><td colspan="5" class="empty-state">No documents have been uploaded yet.</td></tr>`;
      return;
    }
    body.innerHTML = documents.map((documentItem) => `
      <tr>
        <td>
          <strong class="admin-document-name">${escapeHtml(documentItem.filename)}</strong>
          <small>${escapeHtml(truncate(documentItem.document_id, 18))}</small>
        </td>
        <td class="admin-truncate" title="${escapeHtml(documentItem.owner)}">${escapeHtml(documentItem.owner)}</td>
        <td><span class="status-pill ${statusTone(documentItem.status)}">${escapeHtml(documentItem.status)}</span></td>
        <td>${escapeHtml(documentItem.entity_count)}</td>
        <td>${escapeHtml(formatDate(documentItem.created_at))}</td>
      </tr>
    `).join("");
  }

  function renderAdminStats(stats) {
    const grid = document.getElementById("adminStatsGrid");
    const metrics = [
      ["Users", stats.total_users],
      ["Documents", stats.total_documents],
      ["Entities", stats.total_entities],
      ["Pending reviews", stats.pending_reviews],
    ];
    if (grid) {
      grid.innerHTML = metrics.map(([label, value]) => `
        <article class="admin-stat">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </article>
      `).join("");
    }

    renderAdminDocuments(stats.recent_documents || []);
  }

  function renderAdminUsers() {
    const body = document.getElementById("adminUsersBody");
    if (!body) return;
    const search = String(document.getElementById("adminUserSearch")?.value || "").trim().toLowerCase();
    const role = String(document.getElementById("adminRoleFilter")?.value || "").toUpperCase();
    const status = String(document.getElementById("adminStatusFilter")?.value || "");
    const users = state.admin.users.filter((user) => {
      const matchesSearch = !search || `${user.name || ""} ${user.email || ""}`.toLowerCase().includes(search);
      const matchesRole = !role || user.role === role;
      const matchesStatus = !status || (status === "active" ? user.is_active : !user.is_active);
      return matchesSearch && matchesRole && matchesStatus;
    });

    if (!state.admin.users.length) {
      body.innerHTML = `<tr><td colspan="5" class="empty-state">No users found.</td></tr>`;
      return;
    }
    if (!users.length) {
      body.innerHTML = `<tr><td colspan="5" class="empty-state">No users match the selected filters.</td></tr>`;
      return;
    }

    body.innerHTML = users.map((user) => `
      <tr data-user-id="${escapeHtml(user.id)}">
        <td><strong>${escapeHtml(user.name)}</strong></td>
        <td class="admin-truncate" title="${escapeHtml(user.email)}">${escapeHtml(user.email)}</td>
        <td>
          <select class="admin-role-select" data-role-select aria-label="Role for ${escapeHtml(user.name)}">
            <option value="USER" ${user.role === "USER" ? "selected" : ""}>USER</option>
            <option value="REVIEWER" ${user.role === "REVIEWER" ? "selected" : ""}>REVIEWER</option>
            <option value="ADMIN" ${user.role === "ADMIN" ? "selected" : ""}>ADMIN</option>
          </select>
        </td>
        <td><span class="status-pill ${user.is_active ? "success" : "danger"}">${user.is_active ? "Active" : "Inactive"}</span></td>
        <td><button class="button secondary compact" type="button" data-activate-user>${user.is_active ? "Deactivate" : "Activate"}</button></td>
      </tr>
    `).join("");

    body.querySelectorAll("[data-role-select]").forEach((select) => {
      select.addEventListener("change", async () => {
        const row = select.closest("tr[data-user-id]");
        select.disabled = true;
        try {
          await apiFetch(`/admin/users/${encodeURIComponent(row.dataset.userId)}/role`, {
            method: "PATCH",
            body: { role: select.value },
          });
          showToast("User role updated.");
          await loadAdminPanel();
        } catch (error) {
          showToast(`Role update failed: ${error.message}`, true);
          renderAdminUsers();
        }
      });
    });

    body.querySelectorAll("[data-activate-user]").forEach((button) => {
      button.addEventListener("click", async () => {
        const row = button.closest("tr[data-user-id]");
        const user = state.admin.users.find((entry) => entry.id === row.dataset.userId);
        if (!user) return;
        button.disabled = true;
        try {
          await apiFetch(`/admin/users/${encodeURIComponent(user.id)}/active`, {
            method: "PATCH",
            body: { is_active: !user.is_active },
          });
          showToast(`User ${user.is_active ? "deactivated" : "activated"}.`);
          await loadAdminPanel();
        } catch (error) {
          showToast(`Status update failed: ${error.message}`, true);
          renderAdminUsers();
        }
      });
    });
  }

  async function loadAdminPanel() {
    const adminPanel = document.getElementById("adminPanel");
    if (!adminPanel || currentRole() !== "ADMIN" || state.admin.loading) return;
    state.admin.loading = true;
    const refreshButton = document.getElementById("adminRefreshBtn");
    if (refreshButton) refreshButton.disabled = true;
    document.getElementById("adminStatsGrid").innerHTML = `<div class="admin-stat is-loading"><span>Loading dashboard metrics...</span></div>`;
    document.getElementById("adminDocumentsBody").innerHTML = `<tr><td colspan="5" class="empty-state">Loading documents...</td></tr>`;
    document.getElementById("adminUsersBody").innerHTML = `<tr><td colspan="5" class="empty-state">Loading users...</td></tr>`;

    try {
      const [statsResult, usersResult] = await Promise.allSettled([
        apiFetch("/admin/stats"),
        apiFetch("/admin/users"),
      ]);

      if (statsResult.status === "fulfilled") {
        renderAdminStats(statsResult.value);
      } else {
        document.getElementById("adminStatsGrid").innerHTML = `<div class="admin-error-state">Dashboard metrics could not be loaded.</div>`;
        document.getElementById("adminDocumentsBody").innerHTML = `<tr><td colspan="5" class="empty-state">Recent documents could not be loaded.</td></tr>`;
      }

      if (usersResult.status === "fulfilled" && Array.isArray(usersResult.value)) {
        state.admin.users = usersResult.value;
        renderAdminUsers();
      } else {
        state.admin.users = [];
        const message = usersResult.status === "rejected" ? usersResult.reason.message : "Failed to load users.";
        document.getElementById("adminUsersBody").innerHTML = `<tr><td colspan="5" class="empty-state">${escapeHtml(message)}</td></tr>`;
      }
    } finally {
      state.admin.loading = false;
      if (refreshButton) refreshButton.disabled = false;
    }
  }

  async function logout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (error) {
      /* best-effort server-side invalidation */
    } finally {
      clearAuth();
      redirectToLogin();
    }
  }

  function readStoredState() {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      if (stored.apiBase) {
        state.apiBase = stored.apiBase;
      }
      if (Array.isArray(stored.documents)) {
        state.documents = stored.documents.slice(0, 12);
      }
      if (stored.activeDocumentId) {
        state.activeDocumentId = stored.activeDocumentId;
      }
    } catch (error) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  function persistState() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        apiBase: state.apiBase,
        documents: state.documents,
        activeDocumentId: state.activeDocumentId,
      })
    );
  }

  function savedTheme() {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch (error) {
      return null;
    }
  }

  function preferredTheme() {
    const saved = savedTheme();
    if (saved === "dark" || saved === "light") {
      return saved;
    }
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    const resolved = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", resolved);
    try {
      localStorage.setItem(THEME_KEY, resolved);
    } catch (error) {
      /* ignore storage failures */
    }
    if (els.themeToggle) {
      els.themeToggle.setAttribute("aria-pressed", resolved === "dark" ? "true" : "false");
      els.themeToggle.setAttribute("aria-label", resolved === "dark" ? "Switch to light mode" : "Switch to dark mode");
    }
  }

  function toggleTheme() {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
  }

  function setHeaderMenuOpen(trigger, menu, isOpen) {
    if (!trigger || !menu) return;
    trigger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    menu.hidden = !isOpen;
  }

  function closeHeaderMenus(exceptMenu) {
    [
      [els.apiMenuTrigger, els.apiMenu],
      [els.profileMenuTrigger, els.profileMenu],
    ].forEach(([trigger, menu]) => {
      if (menu !== exceptMenu) {
        setHeaderMenuOpen(trigger, menu, false);
      }
    });
  }

  function toggleHeaderMenu(trigger, menu) {
    if (!trigger || !menu) return;
    const willOpen = menu.hidden;
    closeHeaderMenus(menu);
    setHeaderMenuOpen(trigger, menu, willOpen);
  }

  function normalizeBase(value) {
    return (value || "").trim().replace(/\/+$/, "");
  }

  async function apiFetch(path, options) {
    const requestOptions = options || {};
    const headers = new Headers(requestOptions.headers || {});
    const auth = getAuth();
    if (auth && auth.token) {
      headers.set("Authorization", `Bearer ${auth.token}`);
    }
    const init = Object.assign({}, requestOptions, { headers });

    if (init.body && !(init.body instanceof FormData) && typeof init.body !== "string") {
      headers.set("Content-Type", "application/json");
      init.body = JSON.stringify(init.body);
    }

    const response = await fetch(`${state.apiBase}${path}`, init);
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const payload = await response.json();
        detail = payload.detail || payload.message || detail;
      } catch (error) {
        try {
          detail = await response.text();
        } catch (textError) {
          // Keep the HTTP status detail.
        }
      }
      if (response.status === 401) {
        clearAuth();
        redirectToLogin();
      }
      const error = new Error(detail);
      error.status = response.status;
      throw error;
    }

    if (response.status === 204) {
      return null;
    }

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return response.json();
    }
    return response.text();
  }

  function showToast(message, isError) {
    els.toast.textContent = message;
    els.toast.classList.toggle("is-error", Boolean(isError));
    els.toast.classList.add("is-visible");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      els.toast.classList.remove("is-visible");
    }, 3600);
  }

  function setBadge(element, text, type) {
    element.textContent = text;
    element.className = `status-pill ${type || "neutral"}`;
  }

  function statusTone(value) {
    const normalized = String(value || "").toUpperCase();
    if (/(FAILED|ERROR|REJECTED)/.test(normalized)) return "danger";
    if (/(DONE|COMPLETE|COMPLETED|SUCCESS|APPROVED|HEALTHY)/.test(normalized)) return "success";
    if (/(RUNNING|PROCESSING|PENDING|QUEUED|UPLOADED|STARTED)/.test(normalized)) return "warning";
    return "neutral";
  }

  function formatDate(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString(undefined, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function truncate(value, size) {
    const text = String(value || "");
    if (text.length <= size) return text;
    return `${text.slice(0, size - 1)}...`;
  }

  function maskValue(value) {
    const text = String(value || "").trim();
    if (!text) return "-";
    if (state.revealValues) return text;
    if (text.length <= 4) return "*".repeat(text.length);
    return `${text.slice(0, 1)}${"*".repeat(Math.min(8, text.length - 3))}${text.slice(-2)}`;
  }

  function confidenceLabel(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "-";
    return `${Math.round(number * 100)}%`;
  }

  function emptyRow(message, colSpan) {
    return `<tr><td colspan="${colSpan || 6}" class="empty-state">${escapeHtml(message)}</td></tr>`;
  }

  function renderFiles() {
    const files = Array.from(els.fileInput.files || []);
    els.fileSummary.textContent = files.length
      ? `${files.length} file${files.length === 1 ? "" : "s"} selected`
      : "No files selected";

    if (!files.length) {
      els.fileList.innerHTML = "";
      return;
    }

    els.fileList.innerHTML = files.map((file, index) => `
      <div class="file-item">
        <div class="file-item-details">
          <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
          <small>${escapeHtml(formatBytes(file.size))}</small>
        </div>
        <button class="file-remove-button" type="button" data-file-index="${index}" aria-label="Remove ${escapeHtml(file.name)}" title="Remove file">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    `).join("");
  }

  function removeSelectedFile(index) {
    const files = Array.from(els.fileInput.files || []);
    if (index < 0 || index >= files.length) return;

    const remainingFiles = new DataTransfer();
    files.forEach((file, fileIndex) => {
      if (fileIndex !== index) remainingFiles.items.add(file);
    });
    els.fileInput.files = remainingFiles.files;
    renderFiles();
  }

  function upsertDocuments(documents) {
    const incoming = documents.map((document) => ({
      id: document.document_id,
      filename: document.filename || document.document_id,
      status: document.status || document.document_status || null,
      createdAt: document.created_at || null,
      entityCount: document.total_entities == null ? null : document.total_entities,
    })).filter((document) => document.id);

    incoming.forEach((document) => {
      state.documents = state.documents.filter((item) => item.id !== document.id);
      state.documents.unshift(document);
    });
    state.documents = state.documents.slice(0, 12);

    if (incoming[0]) {
      state.activeDocumentId = incoming[0].id;
      els.documentIdInput.value = incoming[0].id;
    }
    persistState();
    renderDocumentList();
  }

  function updateDocumentStatus(status) {
    if (!status || !status.document_id) return;
    const match = state.documents.find((document) => document.id === status.document_id);
    if (match) {
      match.filename = status.filename || match.filename;
      match.status = status.processing_status || status.document_status || match.status;
      match.createdAt = status.created_at || match.createdAt || null;
      persistState();
      renderDocumentList();
    }
  }

  function removeTrackedDocument(documentId) {
    state.documents = state.documents.filter((document) => document.id !== documentId);
    if (state.activeDocumentId === documentId) {
      state.activeDocumentId = "";
      state.activeReviewFilter = "all";
      els.documentIdInput.value = "";
    }
    persistState();
    renderDocumentList();
  }

  function renderEmptyDashboard() {
    state.dashboard.reportDetail = null;
    renderStatus(null);
    renderText(null);
    renderReviews([], []);
    renderMetrics([], [], [], []);
    renderArtifacts([], []);
    renderLlmAudit({ accepted: [], rejected: [] });
    renderWorkflow(0);
  }

  function renderDocumentList() {
    if (state.recentDocumentsLoading) {
      els.recentCount.textContent = "Refreshing from your workspace...";
      els.documentListBody.innerHTML = emptyRow("Loading your documents...", 4);
      return;
    }

    els.recentCount.textContent = state.recentDocumentsError
      ? state.recentDocumentsError
      : (state.documents.length
        ? `${state.documents.length} recent document${state.documents.length === 1 ? "" : "s"}.`
        : "No recent documents.");

    if (!state.documents.length) {
      els.documentListBody.innerHTML = emptyRow("Your uploaded documents appear here.", 4);
      return;
    }

    els.documentListBody.innerHTML = state.documents.map((document) => `
      <tr class="${document.id === state.activeDocumentId ? "is-active" : ""}">
        <td>
          <button class="document-select" type="button" data-document-id="${escapeHtml(document.id)}">
            <strong title="${escapeHtml(document.filename)}">${escapeHtml(document.filename)}</strong>
            <small title="${escapeHtml(document.id)}">${escapeHtml(truncate(document.id, 22))}</small>
          </button>
        </td>
        <td><span class="status-pill ${statusTone(document.status)}">${escapeHtml(document.status || "-")}</span></td>
        <td>${document.entityCount == null ? "-" : escapeHtml(document.entityCount)}</td>
        <td>${escapeHtml(formatDate(document.createdAt))}</td>
      </tr>
    `).join("");
  }

  async function syncUserDocuments() {
    if (currentRole() !== "USER" || state.recentDocumentsLoading || !state.documents.length) {
      return;
    }

    state.recentDocumentsLoading = true;
    state.recentDocumentsError = "";
    renderDocumentList();

    const trackedIds = new Set(state.documents.map((document) => document.id));
    const results = await Promise.all(state.documents.map(async (document) => {
      const documentId = encodeURIComponent(document.id);
      const [statusResult, reportsResult] = await Promise.allSettled([
        apiFetch(`/documents/${documentId}/status`),
        apiFetch(`/documents/${documentId}/reports`),
      ]);

      if (statusResult.status === "rejected") {
        if (statusResult.reason.status === 403 || statusResult.reason.status === 404) {
          return null;
        }
        return Object.assign({}, document, { syncError: true });
      }

      const status = statusResult.value;
      const reports = reportsResult.status === "fulfilled" ? reportsResult.value : [];
      const latestReport = Array.isArray(reports) && reports.length ? reports[0] : null;
      return {
        id: status.document_id,
        filename: status.filename || document.filename,
        status: status.processing_status || status.document_status || document.status,
        createdAt: status.created_at || null,
        entityCount: latestReport && latestReport.total_entities != null
          ? latestReport.total_entities
          : null,
        syncError: reportsResult.status === "rejected",
      };
    }));

    state.documents = results.filter(Boolean);
    if (
      state.activeDocumentId
      && trackedIds.has(state.activeDocumentId)
      && !state.documents.some((document) => document.id === state.activeDocumentId)
    ) {
      state.activeDocumentId = "";
      els.documentIdInput.value = "";
      renderEmptyDashboard();
    }
    const failedCount = state.documents.filter((document) => document.syncError).length;
    state.documents.forEach((document) => delete document.syncError);
    state.recentDocumentsError = failedCount
      ? `${failedCount} document${failedCount === 1 ? "" : "s"} could not be fully refreshed.`
      : "";
    state.recentDocumentsLoading = false;
    persistState();
    renderDocumentList();
  }

  function renderReviewerContext(status, stateLabel) {
    const fields = {
      reviewerContextName: status && status.filename,
      reviewerContextOwner: status && status.owner,
      reviewerContextStatus: status && status.document_status,
      reviewerContextId: status && status.document_id,
      reviewerContextProcessing: status && (status.processing_status || status.workflow_stage),
      reviewerContextOcr: status && (
        status.extraction_method
        || (status.has_extracted_text ? "Available" : "Pending")
      ),
    };

    Object.entries(fields).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (!element) return;
      const displayValue = id === "reviewerContextId" && value
        ? value
        : (stateLabel || value || "-");
      element.textContent = displayValue;
      element.title = value || "";
    });
  }

  function renderStatus(status) {
    state.dashboard.status = status || null;
    renderReviewerContext(status);

    if (!status) {
      els.activeFilename.textContent = "Select or upload a document.";
      setBadge(els.processingBadge, "Idle", "neutral");
      els.statusDetails.innerHTML = `
        <div><dt>Document ID</dt><dd>-</dd></div>
        <div><dt>Status</dt><dd>-</dd></div>
        <div><dt>Stage</dt><dd>-</dd></div>
        <div><dt>OCR</dt><dd>-</dd></div>
        <div><dt>Retries</dt><dd>-</dd></div>
      `;
      renderWorkflow(0);
      return;
    }

    const primaryStatus = status.processing_status || status.document_status || "Unknown";
    els.activeFilename.textContent = status.filename || status.document_id;
    setBadge(els.processingBadge, primaryStatus, statusTone(primaryStatus));
    els.statusDetails.innerHTML = `
      <div><dt>Document ID</dt><dd title="${escapeHtml(status.document_id)}">${escapeHtml(status.document_id || "-")}</dd></div>
      <div><dt>Status</dt><dd>${escapeHtml(status.document_status || "-")}</dd></div>
      <div><dt>Stage</dt><dd>${escapeHtml(status.workflow_stage || status.processing_status || "-")}</dd></div>
      <div><dt>OCR</dt><dd>${status.has_extracted_text ? "Available" : escapeHtml(status.extraction_method || "Pending")}</dd></div>
      <div><dt>Retries</dt><dd>${escapeHtml(status.retry_count == null ? "-" : status.retry_count)}</dd></div>
    `;
    updateDocumentStatus(status);
  }

  function normalizeCategory(value) {
    return String(value || "").toUpperCase();
  }

  function normalizeReviewStatus(review) {
    return String(review && review.review_status || "").toUpperCase();
  }

  function getEntityId(entity) {
    return entity && (entity.entity_id || entity.id);
  }

  function getReviewEntity(review) {
    return review && review.entity ? review.entity : {};
  }

  function getConfidence(entity) {
    return entity.final_confidence == null ? entity.confidence_score : entity.final_confidence;
  }

  function getPendingReviews() {
    return state.dashboard.reviews.filter((review) => normalizeReviewStatus(review) === "PENDING");
  }

  function getDisplayEntities() {
    if (state.dashboard.entities.length) {
      return state.dashboard.entities;
    }
    return state.dashboard.reviews
      .map((review) => review.entity)
      .filter(Boolean);
  }

  function getReviewMap() {
    const reviewsByEntityId = new Map();
    state.dashboard.reviews.forEach((review) => {
      const id = getEntityId(getReviewEntity(review));
      if (id) {
        reviewsByEntityId.set(id, review);
      }
    });
    return reviewsByEntityId;
  }

  function getFilteredFindingRows() {
    const filter = REVIEW_FILTERS[state.activeReviewFilter]
      ? state.activeReviewFilter
      : "all";

    if (filter === "pending") {
      return getPendingReviews().map((review) => ({
        entity: getReviewEntity(review),
        review,
      }));
    }

    const reviewMap = getReviewMap();
    let entities = getDisplayEntities();
    if (filter === "pii" || filter === "phi") {
      entities = entities.filter((entity) => normalizeCategory(entity.privacy_category) === filter.toUpperCase());
    }

    return entities.map((entity) => ({
      entity,
      review: reviewMap.get(getEntityId(entity)) || null,
    }));
  }

  function renderReviewHeader(showReviewColumns) {
    els.reviewsHead.innerHTML = `
      <tr>
        <th>Entity</th>
        <th>Value</th>
        <th>Category</th>
        <th>Confidence</th>
        ${showReviewColumns ? "<th>Status</th><th>Decision</th>" : ""}
      </tr>
    `;
  }

  function renderMetricFilterState() {
    els.metricFilters.forEach((button) => {
      const isActive = button.dataset.reviewFilter === state.activeReviewFilter;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function renderMetrics(reviews, reports, redactions, entities, reportDetail) {
    if (Array.isArray(entities)) {
      state.dashboard.entities = entities;
    }

    const latestReport = reports[0] || null;
    const isUserDashboard = currentRole() === "USER";
    const reportPayload = reportDetail && reportDetail.payload ? reportDetail.payload : null;
    const entityRows = getDisplayEntities();
    const pendingFromReport = reportPayload && Number.isFinite(Number(reportPayload.pending_reviews))
      ? Number(reportPayload.pending_reviews)
      : null;
    const pendingReviews = isUserDashboard
      ? pendingFromReport
      : reviews.filter((review) => normalizeReviewStatus(review) === "PENDING").length;
    const piiCount = isUserDashboard
      ? (latestReport && latestReport.total_pii != null ? latestReport.total_pii : null)
      : (entityRows.length
        ? entityRows.filter((entity) => normalizeCategory(entity.privacy_category) === "PII").length
        : (latestReport ? latestReport.total_pii : 0));
    const phiCount = isUserDashboard
      ? (latestReport && latestReport.total_phi != null ? latestReport.total_phi : null)
      : (entityRows.length
        ? entityRows.filter((entity) => normalizeCategory(entity.privacy_category) === "PHI").length
        : (latestReport ? latestReport.total_phi : 0));
    const entityCount = isUserDashboard
      ? (latestReport && latestReport.total_entities != null ? latestReport.total_entities : null)
      : (entityRows.length || (latestReport ? latestReport.total_entities : 0));

    const metricValue = (value) => value == null ? "-" : value;
    els.metricEntities.textContent = metricValue(entityCount);
    els.metricPii.textContent = metricValue(piiCount);
    els.metricPhi.textContent = metricValue(phiCount);
    els.metricPending.textContent = metricValue(pendingReviews);

    const reviewerPending = document.getElementById("reviewerMetricPending");
    const reviewerFindings = document.getElementById("reviewerMetricFindings");
    const reviewerCompleted = document.getElementById("reviewerMetricCompleted");
    const completedReviews = reviews.filter((review) =>
      COMPLETED_REVIEW_STATUSES.includes(normalizeReviewStatus(review))
    ).length;
    if (reviewerPending) reviewerPending.textContent = pendingReviews == null ? "-" : pendingReviews;
    if (reviewerFindings) reviewerFindings.textContent = entityCount || 0;
    if (reviewerCompleted) reviewerCompleted.textContent = completedReviews;

    if (latestReport) {
      const redactionCount = latestReport.total_redactions || redactions.length || 0;
      els.reportTimestamp.textContent = `${redactionCount} redaction${redactionCount === 1 ? "" : "s"} logged. Report created ${formatDate(latestReport.created_at)}.`;
    } else if (entityRows.length || reviews.length || redactions.length) {
      els.reportTimestamp.textContent = `${entityRows.length} detected entit${entityRows.length === 1 ? "y" : "ies"}; ${reviews.length} review item${reviews.length === 1 ? "" : "s"}.`;
    } else {
      els.reportTimestamp.textContent = "Waiting for report data.";
    }
  }

  function renderReviewerActivity(reviews) {
    const body = document.getElementById("reviewerActivityBody");
    if (!body) return;
    if (!state.activeDocumentId) {
      body.innerHTML = emptyRow("No document selected.", 4);
      return;
    }

    const completed = (Array.isArray(reviews) ? reviews : [])
      .filter((review) => COMPLETED_REVIEW_STATUSES.includes(normalizeReviewStatus(review)))
      .sort((left, right) => {
        const leftTime = new Date(left.reviewed_at || left.created_at || 0).getTime();
        const rightTime = new Date(right.reviewed_at || right.created_at || 0).getTime();
        return rightTime - leftTime;
      })
      .slice(0, 8);

    if (!completed.length) {
      body.innerHTML = emptyRow("No completed review activity for this document.", 4);
      return;
    }

    body.innerHTML = completed.map((review) => {
      const entity = getReviewEntity(review);
      const status = normalizeReviewStatus(review);
      return `
        <tr>
          <td>
            <span class="entity-type">
              <strong>${escapeHtml(entity.entity_type || "Entity")}</strong>
              <small>${escapeHtml(maskValue(entity.entity_value))}</small>
            </span>
          </td>
          <td><span class="status-pill ${statusTone(status)}">${escapeHtml(status)}</span></td>
          <td class="reviewer-activity-truncate">${escapeHtml(review.reviewer || "-")}</td>
          <td>${escapeHtml(formatDate(review.reviewed_at || review.created_at))}</td>
        </tr>
      `;
    }).join("");
  }

  function renderReviews(reviews, entities) {
    if (Array.isArray(reviews)) {
      state.dashboard.reviews = reviews;
    }
    if (Array.isArray(entities)) {
      state.dashboard.entities = entities;
    }

    const filterLabel = REVIEW_FILTERS[state.activeReviewFilter] || REVIEW_FILTERS.all;
    const showReviewColumns = currentRole() === "REVIEWER" || state.activeReviewFilter === "pending";
    const colSpan = showReviewColumns ? 6 : 4;
    const rows = getFilteredFindingRows();
    const pending = getPendingReviews().length;
    renderReviewerActivity(state.dashboard.reviews);

    renderReviewHeader(showReviewColumns);
    renderMetricFilterState();
    els.toggleValuesBtn.textContent = state.revealValues ? "Mask values" : "Reveal values";

    if (!state.activeDocumentId) {
      els.reviewSummary.textContent = "No review items loaded.";
      els.reviewsBody.innerHTML = emptyRow("No document selected.", colSpan);
      return;
    }

    els.reviewSummary.textContent = `${filterLabel}: ${rows.length} finding${rows.length === 1 ? "" : "s"}; ${pending} pending.`;

    if (!rows.length) {
      const message = state.activeReviewFilter === "pending"
        ? "No pending review records."
        : `No ${filterLabel.toLowerCase()} entity records are available yet.`;
      els.reviewsBody.innerHTML = emptyRow(message, colSpan);
      return;
    }

    els.reviewsBody.innerHTML = rows.map(({ entity, review }) => {
      const status = review && review.review_status ? review.review_status : (entity.is_review_required ? "PENDING" : "AUTO APPROVED");
      const detector = entity.detector ? `Detector: ${entity.detector}` : "Detector unavailable";
      const confidence = getConfidence(entity);
      const isComplete = COMPLETED_REVIEW_STATUSES.includes(String(status).toUpperCase());
      const reviewId = review && review.review_id;
      return `
        <tr class="${String(status).toUpperCase() === "PENDING" ? "is-review-pending" : ""}">
          <td>
            <span class="entity-type">
              <strong>${escapeHtml(entity.entity_type || "Entity")}</strong>
              <small>${escapeHtml(detector)}</small>
            </span>
          </td>
          <td><span class="entity-value" title="${state.revealValues ? "" : "Masked"}">${escapeHtml(state.revealValues ? entity.entity_value : maskValue(entity.entity_value))}</span></td>
          <td>${escapeHtml(entity.privacy_category || "-")}</td>
          <td>${escapeHtml(confidenceLabel(confidence))}</td>
          ${showReviewColumns ? `
            <td><span class="status-pill ${statusTone(status)}">${escapeHtml(status)}</span></td>
            <td>
              <span class="decision-group">
                <button class="button secondary compact" type="button" data-review-id="${escapeHtml(reviewId || "")}" data-decision="APPROVED" ${isComplete || !reviewId ? "disabled" : ""}>Approve</button>
                <button class="button danger compact" type="button" data-review-id="${escapeHtml(reviewId || "")}" data-decision="REJECTED" ${isComplete || !reviewId ? "disabled" : ""}>Reject</button>
              </span>
            </td>
          ` : ""}
        </tr>
      `;
    }).join("");
  }

  function renderLlmAudit(auditData) {
    state.dashboard.llmAudit = auditData || { accepted: [], rejected: [] };
    const acceptedList = (state.dashboard.llmAudit.accepted || []);
    const rejectedList = (state.dashboard.llmAudit.rejected || []);

    if (els.countLlmAccepted) els.countLlmAccepted.textContent = acceptedList.length;
    if (els.countLlmRejected) els.countLlmRejected.textContent = rejectedList.length;

    if (els.tabLlmAccepted) {
      els.tabLlmAccepted.classList.toggle("is-active", state.activeLlmTab === "accepted");
    }
    if (els.tabLlmRejected) {
      els.tabLlmRejected.classList.toggle("is-active", state.activeLlmTab === "rejected");
    }

    const currentItems = state.activeLlmTab === "accepted" ? acceptedList : rejectedList;

    if (els.llmAuditSummary) {
      els.llmAuditSummary.textContent = `${acceptedList.length} candidate(s) accepted, ${rejectedList.length} candidate(s) rejected by AI.`;
    }

    if (!els.llmAuditBody) return;

    if (!acceptedList.length && !rejectedList.length) {
      els.llmAuditBody.innerHTML = `<tr><td colspan="6" class="empty-state">No AI/LLM candidates for this document.</td></tr>`;
      return;
    }

    if (!currentItems.length) {
      els.llmAuditBody.innerHTML = `<tr><td colspan="6" class="empty-state">No ${state.activeLlmTab} AI/LLM candidates for this document.</td></tr>`;
      return;
    }

    els.llmAuditBody.innerHTML = currentItems.map((item) => {
      const decision = String(item.decision || "UNKNOWN").toUpperCase();
      let tone = "neutral";
      if (decision === "CONFIRM" || decision === "ACCEPT") tone = "success";
      else if (decision === "RECLASSIFY") tone = "warning";
      else if (decision === "REJECT") tone = "danger";

      const confidencePct = item.confidence != null ? `${Math.round(item.confidence * 100)}%` : "-";

      return `
        <tr>
          <td>
            <span class="entity-type">
              <strong>${escapeHtml(item.entity_type || item.original_type || "Entity")}</strong>
              ${item.original_type && item.original_type !== item.entity_type ? `<small>orig: ${escapeHtml(item.original_type)}</small>` : ""}
            </span>
          </td>
          <td><span class="entity-value">${escapeHtml(item.candidate_value || item.entity_value || "-")}</span></td>
          <td><span class="status-pill ${tone}">${escapeHtml(decision)}</span></td>
          <td><strong>${escapeHtml(confidencePct)}</strong></td>
          <td><small style="color: #64748b; font-weight: 600;">${escapeHtml(item.detector || "-")}</small></td>
          <td>
            <div class="llm-reason-box">${escapeHtml(item.reasoning || item.reason || "-")}</div>
          </td>
        </tr>
      `;
    }).join("");
  }

  function renderLlmAuditUnavailable(message) {
    state.dashboard.llmAudit = { accepted: [], rejected: [] };
    if (els.countLlmAccepted) els.countLlmAccepted.textContent = 0;
    if (els.countLlmRejected) els.countLlmRejected.textContent = 0;
    if (els.llmAuditSummary) {
      els.llmAuditSummary.textContent = message;
    }
    if (els.llmAuditBody) {
      els.llmAuditBody.innerHTML = `<tr><td colspan="6" class="empty-state">${escapeHtml(message)}</td></tr>`;
    }
  }

  function renderText(textPayload) {
    state.dashboard.text = textPayload || null;
    if (!textPayload || !textPayload.extracted_text) {
      els.textMeta.textContent = state.activeDocumentId ? "Text is not available yet." : "Text appears after extraction completes.";
      els.textPreview.textContent = state.activeDocumentId ? "Extraction output is not ready." : "No extracted text loaded.";
      return;
    }

    const pageCount = textPayload.page_count ? `${textPayload.page_count} page${textPayload.page_count === 1 ? "" : "s"}` : "Page count unavailable";
    const confidence = textPayload.confidence_score == null ? "confidence unavailable" : `${confidenceLabel(textPayload.confidence_score)} confidence`;
    els.textMeta.textContent = `${textPayload.extraction_method || "Extraction"} &middot; ${pageCount} &middot; ${confidence}`.replace(/&middot;/g, "-");
    els.textPreview.textContent = textPayload.extracted_text;
  }

  function artifactUrl(path) {
    return `${state.apiBase}${path}`;
  }

  function getDownloadFilename(contentDisposition) {
    const value = String(contentDisposition || "");
    const encodedMatch = value.match(/filename\*=UTF-8''([^;]+)/i);
    const quotedMatch = value.match(/filename="([^"]+)"/i);
    const plainMatch = value.match(/filename=([^;]+)/i);
    const candidate = encodedMatch
      ? encodedMatch[1]
      : (quotedMatch ? quotedMatch[1] : (plainMatch ? plainMatch[1].trim() : ""));
    if (!candidate) return "";

    let decoded = candidate;
    try {
      decoded = decodeURIComponent(candidate);
    } catch (error) {
      /* Use the server-provided filename as-is when it is not URI encoded. */
    }
    return decoded.split(/[\\/]/).pop() || "";
  }

  async function getDownloadError(response) {
    const fallback = `${response.status} ${response.statusText}`.trim();
    try {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = await response.json();
        return payload.detail || payload.message || fallback;
      }
      return (await response.text()) || fallback;
    } catch (error) {
      return fallback;
    }
  }

  async function downloadUserArtifact(button) {
    if (currentRole() !== "USER" || !button) return;

    const artifactId = button.dataset.artifactId;
    const artifactKind = button.dataset.artifactKind;
    if (!artifactId || !["redaction", "report"].includes(artifactKind)) {
      showToast("This artifact is not available for download.", true);
      return;
    }

    const path = artifactKind === "redaction"
      ? `/redactions/${encodeURIComponent(artifactId)}/file`
      : `/reports/${encodeURIComponent(artifactId)}/file`;
    const auth = getAuth();
    if (!auth || !auth.token) {
      redirectToLogin();
      return;
    }

    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Downloading...";

    try {
      const response = await fetch(artifactUrl(path), {
        headers: { Authorization: `Bearer ${auth.token}` },
      });
      if (!response.ok) {
        if (response.status === 401) {
          clearAuth();
          redirectToLogin();
        }
        const error = new Error(await getDownloadError(response));
        error.status = response.status;
        throw error;
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const downloadLink = document.createElement("a");
      const filename = getDownloadFilename(response.headers.get("content-disposition"));
      downloadLink.href = objectUrl;
      downloadLink.download = filename;
      downloadLink.hidden = true;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      downloadLink.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      showToast("Artifact download started.");
    } catch (error) {
      showToast(`Download failed: ${error.message}`, true);
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    }
  }

  function renderArtifacts(reports, redactions) {
    state.dashboard.reports = reports || [];
    state.dashboard.redactions = redactions || [];

    const isUserDashboard = currentRole() === "USER";
    const visibleRedactions = isUserDashboard
      ? state.dashboard.redactions.filter((redaction) => (
        redaction.redaction_id && redaction.redacted_file_path
      )).slice(0, 1)
      : state.dashboard.redactions;
    const visibleReports = isUserDashboard
      ? state.dashboard.reports.filter((report) => (
        report.report_id && report.report_path
      )).slice(0, 1)
      : state.dashboard.reports;
    const items = [];
    visibleRedactions.forEach((redaction) => {
      items.push(`
        <div class="artifact-item">
          <span class="artifact-meta">
            <strong>Redacted text</strong>
            ${isUserDashboard ? "" : `<small>${escapeHtml(redaction.redaction_type || "Text artifact")} &middot; ${escapeHtml(formatDate(redaction.created_at))}</small>`}
          </span>
          ${isUserDashboard
            ? `<button class="button ghost compact" type="button" data-artifact-kind="redaction" data-artifact-id="${escapeHtml(redaction.redaction_id)}">Download</button>`
            : `<a class="button ghost compact" href="${escapeHtml(artifactUrl(`/redactions/${redaction.redaction_id}/file`))}" target="_blank" rel="noreferrer">Download</a>`}
        </div>
      `);
    });

    visibleReports.forEach((report) => {
      items.push(`
        <div class="artifact-item">
          <span class="artifact-meta">
            <strong>Audit report</strong>
            ${isUserDashboard ? "" : `<small>${escapeHtml(report.report_type || "JSON report")} &middot; ${escapeHtml(formatDate(report.created_at))}</small>`}
          </span>
          ${isUserDashboard
            ? `<button class="button ghost compact" type="button" data-artifact-kind="report" data-artifact-id="${escapeHtml(report.report_id)}">Download</button>`
            : `<a class="button ghost compact" href="${escapeHtml(artifactUrl(`/reports/${report.report_id}/file`))}" target="_blank" rel="noreferrer">Download</a>`}
        </div>
      `);
    });

    els.artifactList.innerHTML = items.length ? items.join("") : `<div class="empty-state">No artifacts loaded.</div>`;
    const artifactsPanel = els.artifactList.closest(".artifacts-panel");
    if (artifactsPanel && isUserDashboard) {
      artifactsPanel.hidden = !items.length;
    } else if (artifactsPanel) {
      artifactsPanel.hidden = false;
    }
  }

  function renderWorkflow(index) {
    els.workflowItems.forEach((item, itemIndex) => {
      item.classList.toggle("is-active", itemIndex === index);
    });
  }

  function updateWorkflow(status, reviews, reports, redactions) {
    if (!state.activeDocumentId) {
      renderWorkflow(0);
      return;
    }
    if ((reports && reports.length) || (redactions && redactions.length)) {
      renderWorkflow(3);
      return;
    }
    if ((reviews && reviews.length) || (status && status.has_extracted_text)) {
      renderWorkflow(2);
      return;
    }
    renderWorkflow(1);
  }

  function isTerminalStatus(status) {
    const value = `${status && status.processing_status || ""} ${status && status.document_status || ""}`.toUpperCase();
    return /(COMPLETE|COMPLETED|DONE|SUCCESS|FAILED|ERROR)/.test(value);
  }

  function startPolling() {
    stopPolling();
    if (!state.activeDocumentId) return;
    state.pollTimer = window.setInterval(() => {
      loadDashboard(state.activeDocumentId, { quiet: true });
    }, POLL_MS);
  }

  function stopPolling() {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  async function checkHealth() {
    try {
      setBadge(els.healthBadge, "Checking", "warning");
      const health = await apiFetch("/health/");
      setBadge(els.healthBadge, health.status || "Healthy", statusTone(health.status || "healthy"));
    } catch (error) {
      setBadge(els.healthBadge, "Offline", "danger");
      showToast(`API check failed: ${error.message}`, true);
    }
  }

  async function uploadDocuments(event) {
    event.preventDefault();
    const files = Array.from(els.fileInput.files || []);
    if (!files.length) {
      showToast("Select at least one document.", true);
      return;
    }

    const formData = new FormData();
    const isBulk = files.length > 1;
    files.forEach((file) => formData.append(isBulk ? "files" : "file", file, file.name));

    const submitButton = els.uploadForm.querySelector("button[type='submit']");
    submitButton.disabled = true;
    submitButton.textContent = "Uploading";

    try {
      const payload = await apiFetch(isBulk ? "/upload/bulk" : "/upload/", {
        method: "POST",
        body: formData,
      });
      const documents = payload.documents || (payload.document ? [payload.document] : []);
      upsertDocuments(documents);
      els.fileInput.value = "";
      renderFiles();
      showToast(payload.message || "Upload complete.");
      await loadDashboard(state.activeDocumentId, { quiet: true });
      startPolling();
    } catch (error) {
      showToast(`Upload failed: ${error.message}`, true);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Upload documents";
    }
  }

  async function loadDashboard(documentId, options) {
    const quiet = options && options.quiet;
    const id = String(documentId || "").trim();
    if (!id) {
      showToast("Enter a document ID.", true);
      return;
    }

    const loadSequence = ++state.dashboardLoadSequence;
    state.activeDocumentId = id;
    els.documentIdInput.value = id;
    persistState();
    renderDocumentList();
    setBadge(els.processingBadge, "Loading", "warning");
    if (currentRole() === "USER") {
      [els.metricEntities, els.metricPii, els.metricPhi, els.metricPending].forEach((metric) => {
        metric.textContent = "...";
      });
      renderArtifacts([], []);
    }
    renderLlmAuditUnavailable("Loading AI candidate audit...");
    renderReviewerContext({ document_id: id }, "Loading...");
    ["reviewerMetricPending", "reviewerMetricFindings", "reviewerMetricCompleted"].forEach((metricId) => {
      const metric = document.getElementById(metricId);
      if (metric) metric.textContent = "...";
    });
    els.reviewSummary.textContent = "Loading review records...";
    const reviewerActivityBody = document.getElementById("reviewerActivityBody");
    if (currentRole() === "REVIEWER" && reviewerActivityBody) {
      reviewerActivityBody.innerHTML = emptyRow("Loading review activity...", 4);
    }

    let status;
    try {
      status = await apiFetch(`/documents/${encodeURIComponent(id)}/status`);
    } catch (error) {
      if (loadSequence !== state.dashboardLoadSequence) return;
      if (error.status === 403 || error.status === 404) {
        removeTrackedDocument(id);
        stopPolling();
      }
      renderEmptyDashboard();
      renderReviewerContext({ document_id: id }, "Unavailable");
      if (!quiet) {
        showToast(`Status lookup failed: ${error.message}`, true);
      }
      return;
    }

    if (loadSequence !== state.dashboardLoadSequence) return;

    if (currentRole() === "USER" && !state.documents.some((document) => document.id === status.document_id)) {
      state.documents.unshift({
        id: status.document_id,
        filename: status.filename || status.document_id,
        status: status.processing_status || status.document_status || null,
        createdAt: status.created_at || null,
        entityCount: null,
      });
      state.documents = state.documents.slice(0, 12);
      persistState();
      renderDocumentList();
    }

    const canLoadReviewData = currentRole() !== "USER";
    const requests = await Promise.allSettled([
      status.has_extracted_text ? apiFetch(`/documents/${encodeURIComponent(id)}/text`) : Promise.resolve(null),
      canLoadReviewData ? apiFetch(`/documents/${encodeURIComponent(id)}/entities`) : Promise.resolve([]),
      canLoadReviewData ? apiFetch(`/documents/${encodeURIComponent(id)}/reviews`) : Promise.resolve([]),
      apiFetch(`/documents/${encodeURIComponent(id)}/reports`),
      apiFetch(`/documents/${encodeURIComponent(id)}/redactions`),
    ]);

    const text = requests[0].status === "fulfilled" ? requests[0].value : null;
    const entities = requests[1].status === "fulfilled" ? requests[1].value : [];
    const reviews = requests[2].status === "fulfilled" ? requests[2].value : [];
    const reports = requests[3].status === "fulfilled" ? requests[3].value : [];
    const redactions = requests[4].status === "fulfilled" ? requests[4].value : [];

    if (loadSequence !== state.dashboardLoadSequence) return;

    const latestReport = reports && reports.length ? reports[0] : null;
    const reportMatchesDocument = !latestReport || latestReport.document_id === id;
    const llmAudit = latestReport && latestReport.llm_candidate_audit;
    let reportDetail = null;
    if (currentRole() === "USER" && latestReport && reportMatchesDocument) {
      try {
        reportDetail = await apiFetch(`/reports/${encodeURIComponent(latestReport.report_id)}`);
      } catch (error) {
        reportDetail = null;
      }
    }

    if (loadSequence !== state.dashboardLoadSequence) return;

    state.dashboard.reportDetail = reportDetail;
    const recentDocument = state.documents.find((document) => document.id === id);
    if (recentDocument) {
      recentDocument.createdAt = status.created_at || null;
      recentDocument.entityCount = latestReport && latestReport.total_entities != null
        ? latestReport.total_entities
        : null;
    }

    renderStatus(status);
    renderText(text);
    renderReviews(reviews, entities);
    if (requests[2].status === "rejected" && reviewerActivityBody) {
      reviewerActivityBody.innerHTML = emptyRow("Review activity could not be loaded.", 4);
    }
    renderMetrics(reviews, reports, redactions, entities, reportDetail);
    if (requests[2].status === "rejected") {
      els.reviewSummary.textContent = "Review records could not be loaded.";
      const pendingMetric = document.getElementById("reviewerMetricPending");
      const completedMetric = document.getElementById("reviewerMetricCompleted");
      if (pendingMetric) pendingMetric.textContent = "-";
      if (completedMetric) completedMetric.textContent = "-";
    }
    renderArtifacts(reports, redactions);
    if (requests[3].status === "rejected" || !reportMatchesDocument) {
      renderLlmAuditUnavailable("AI candidate audit could not be loaded for this document.");
    } else if (latestReport && llmAudit == null) {
      renderLlmAuditUnavailable("Persisted AI candidate audit is unavailable for this document.");
    } else {
      renderLlmAudit(llmAudit || { accepted: [], rejected: [] });
    }
    updateWorkflow(status, reviews, reports, redactions);

    if (currentRole() !== "USER" && status && status.has_extracted_text) {
      document.getElementById("openReviewBtn").style.display = "block";
    } else {
      document.getElementById("openReviewBtn").style.display = "none";
    }

    if (isTerminalStatus(status)) {
      stopPolling();
    }
  }

  async function submitReviewDecision(reviewId, decision) {
    try {
      await apiFetch(`/reviews/${encodeURIComponent(reviewId)}`, {
        method: "PATCH",
        body: {
          review_status: decision,
          review_comment: `Marked ${decision.toLowerCase()} from the PoC UI.`,
        },
      });
      showToast(`Review ${decision.toLowerCase()}.`);
      await loadDashboard(state.activeDocumentId, { quiet: true });
    } catch (error) {
      showToast(`Review update failed: ${error.message}`, true);
    }
  }

  function bindEvents() {
    if (els.themeToggle) {
      els.themeToggle.addEventListener("click", toggleTheme);
    }
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", logout);
    }
    const adminRefreshBtn = document.getElementById("adminRefreshBtn");
    if (adminRefreshBtn) {
      adminRefreshBtn.addEventListener("click", loadAdminPanel);
    }
    ["adminUserSearch", "adminRoleFilter", "adminStatusFilter"].forEach((id) => {
      const filter = document.getElementById(id);
      if (filter) {
        filter.addEventListener(id === "adminUserSearch" ? "input" : "change", renderAdminUsers);
      }
    });
    if (els.apiMenuTrigger && els.apiMenu) {
      els.apiMenuTrigger.addEventListener("click", () => {
        toggleHeaderMenu(els.apiMenuTrigger, els.apiMenu);
      });
    }
    if (els.profileMenuTrigger && els.profileMenu) {
      els.profileMenuTrigger.addEventListener("click", () => {
        toggleHeaderMenu(els.profileMenuTrigger, els.profileMenu);
      });
    }
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".authenticated-header .header-menu")) {
        closeHeaderMenus();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeHeaderMenus();
      }
    });
    els.healthBtn.addEventListener("click", checkHealth);
    els.uploadForm.addEventListener("submit", uploadDocuments);
    els.fileInput.addEventListener("change", renderFiles);
    els.fileList.addEventListener("click", (event) => {
      const removeButton = event.target.closest("[data-file-index]");
      if (!removeButton) return;
      removeSelectedFile(Number(removeButton.dataset.fileIndex));
    });

    if (els.tabLlmAccepted) {
      els.tabLlmAccepted.addEventListener("click", () => {
        state.activeLlmTab = "accepted";
        renderLlmAudit(state.dashboard.llmAudit);
      });
    }
    if (els.tabLlmRejected) {
      els.tabLlmRejected.addEventListener("click", () => {
        state.activeLlmTab = "rejected";
        renderLlmAudit(state.dashboard.llmAudit);
      });
    }

    ["dragenter", "dragover"].forEach((eventName) => {
      els.dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        els.dropZone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      els.dropZone.addEventListener(eventName, () => {
        els.dropZone.classList.remove("is-dragover");
      });
    });

    els.dropZone.addEventListener("drop", (event) => {
      event.preventDefault();
      if (event.dataTransfer && event.dataTransfer.files.length) {
        els.fileInput.files = event.dataTransfer.files;
        renderFiles();
      }
    });

    els.apiBase.addEventListener("change", () => {
      state.apiBase = normalizeBase(els.apiBase.value) || defaultApiBase();
      els.apiBase.value = state.apiBase;
      persistState();
      checkHealth();
    });

    els.loadDocumentBtn.addEventListener("click", () => loadDashboard(els.documentIdInput.value));
    els.refreshBtn.addEventListener("click", () => loadDashboard(state.activeDocumentId || els.documentIdInput.value));
    els.documentIdInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        loadDashboard(els.documentIdInput.value);
      }
    });

    els.documentList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-document-id]");
      if (!button) return;
      loadDashboard(button.dataset.documentId);
    });

    els.artifactList.addEventListener("click", (event) => {
      const button = event.target.closest("[data-artifact-kind][data-artifact-id]");
      if (!button) return;
      downloadUserArtifact(button);
    });

    els.metricFilters.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.reviewFilter;
        if (!REVIEW_FILTERS[filter]) return;
        state.activeReviewFilter = filter;
        renderReviews();
      });
    });

    els.clearRecentBtn.addEventListener("click", () => {
      state.dashboardLoadSequence += 1;
      state.documents = [];
      state.activeDocumentId = "";
      state.activeReviewFilter = "all";
      els.documentIdInput.value = "";
      persistState();
      renderDocumentList();
      renderStatus(null);
      renderReviews([], []);
      renderText(null);
      renderMetrics([], [], [], []);
      renderArtifacts([], []);
      renderLlmAudit({ accepted: [], rejected: [] });
      stopPolling();
    });

    els.toggleValuesBtn.addEventListener("click", () => {
      state.revealValues = !state.revealValues;
      renderReviews();
    });

    els.reviewsBody.addEventListener("click", (event) => {
      const button = event.target.closest("[data-review-id][data-decision]");
      if (!button) return;
      submitReviewDecision(button.dataset.reviewId, button.dataset.decision);
    });

    els.copyTextBtn.addEventListener("click", async () => {
      const text = state.dashboard.text && state.dashboard.text.extracted_text;
      if (!text) {
        showToast("No extracted text to copy.", true);
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showToast("Extracted text copied.");
      } catch (error) {
        showToast("Clipboard permission was not available.", true);
      }
    });

    // --- WORKSPACE REVIEW BINDINGS ---
    const openReviewBtn = document.getElementById("openReviewBtn");
    if (openReviewBtn) {
      openReviewBtn.addEventListener("click", openReviewWorkspace);
    }
    const backToWorkspaceBtn = document.getElementById("backToWorkspaceBtn");
    if (backToWorkspaceBtn) {
      backToWorkspaceBtn.addEventListener("click", closeReviewWorkspace);
    }

    const toggleReviewRevealBtn = document.getElementById("toggleReviewRevealBtn");
    if (toggleReviewRevealBtn) {
      toggleReviewRevealBtn.addEventListener("click", () => {
        reviewState.revealValues = !reviewState.revealValues;
        toggleReviewRevealBtn.textContent = reviewState.revealValues ? "Mask values" : "Reveal values";
        renderReviewWorkspaceCards();
        renderReviewWorkspaceDetails();
      });
    }

    const piiTabBtn = document.getElementById("piiTabBtn");
    const phiTabBtn = document.getElementById("phiTabBtn");
    if (piiTabBtn && phiTabBtn) {
      piiTabBtn.addEventListener("click", () => {
        setReviewActiveTab("PII");
      });
      phiTabBtn.addEventListener("click", () => {
        setReviewActiveTab("PHI");
      });
    }

    const reviewSearchInput = document.getElementById("reviewSearchInput");
    if (reviewSearchInput) {
      reviewSearchInput.addEventListener("input", () => {
        reviewState.searchQuery = reviewSearchInput.value;
        renderReviewWorkspaceCards();
      });
    }

    const toggleFilterPanelBtn = document.getElementById("toggleFilterPanelBtn");
    const filterPanelOverlay = document.getElementById("filterPanelOverlay");
    if (toggleFilterPanelBtn && filterPanelOverlay) {
      toggleFilterPanelBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const display = filterPanelOverlay.style.display;
        filterPanelOverlay.style.display = display === "none" ? "block" : "none";
      });
      document.addEventListener("click", (e) => {
        if (!filterPanelOverlay.contains(e.target) && e.target !== toggleFilterPanelBtn) {
          filterPanelOverlay.style.display = "none";
        }
      });
    }

    const applyFiltersBtn = document.getElementById("applyFiltersBtn");
    if (applyFiltersBtn) {
      applyFiltersBtn.addEventListener("click", () => {
        const detectors = Array.from(document.querySelectorAll(".detector-check:checked")).map(el => el.value);
        const confidence = document.querySelector('input[name="confFilter"]:checked').value;
        const reviewRequired = document.querySelector('input[name="revFilter"]:checked').value;
        reviewState.filters = { detectors, confidence, reviewRequired };
        filterPanelOverlay.style.display = "none";
        renderReviewWorkspaceCards();
      });
    }

    const resetFiltersBtn = document.getElementById("resetFiltersBtn");
    if (resetFiltersBtn) {
      resetFiltersBtn.addEventListener("click", () => {
        Array.from(document.querySelectorAll(".detector-check")).forEach(el => el.checked = false);
        document.querySelector('input[name="confFilter"][value="all"]').checked = true;
        document.querySelector('input[name="revFilter"][value="all"]').checked = true;
        reviewState.filters = { detectors: [], confidence: "all", reviewRequired: "all" };
        renderReviewWorkspaceCards();
      });
    }

    const cardsListContainer = document.getElementById("cardsListContainer");
    if (cardsListContainer) {
      cardsListContainer.addEventListener("click", (e) => {
        const card = e.target.closest(".entity-card");
        if (!card) return;
        const entId = card.dataset.entityId;
        const entity = reviewState.entities.find(ent => ent.id === entId);
        if (!entity) return;
        
        if (e.target.closest(".previous-entity-btn")) {
          navigateReviewEntity(-1, entity);
          return;
        }
        if (e.target.closest(".next-entity-btn")) {
          navigateReviewEntity(1, entity);
          return;
        }
        handleSelectReviewEntity(entity, true);
      });
    }

    const pagesScrollContainer = document.getElementById("pagesScrollContainer");
    if (pagesScrollContainer) {
      pagesScrollContainer.addEventListener("click", (event) => {
        const highlight = event.target.closest("[data-review-entity-id]");
        if (!highlight) return;
        const entity = reviewState.entities.find((item) => item.id === highlight.dataset.reviewEntityId);
        if (entity) handleSelectReviewEntity(entity, true);
      });
    }

    // Detail Action Row Handlers
    const detailApproveBtn = document.getElementById("detailApproveBtn");
    if (detailApproveBtn) {
      detailApproveBtn.addEventListener("click", () => submitDecisionInWorkspace("APPROVED"));
    }
    const detailRejectBtn = document.getElementById("detailRejectBtn");
    if (detailRejectBtn) {
      detailRejectBtn.addEventListener("click", () => submitDecisionInWorkspace("REJECTED"));
    }
    const detailFlagBtn = document.getElementById("detailFlagBtn");
    if (detailFlagBtn) {
      detailFlagBtn.addEventListener("click", () => submitDecisionInWorkspace("PENDING"));
    }
    const detailEditBtn = document.getElementById("detailEditBtn");
    if (detailEditBtn) {
      detailEditBtn.addEventListener("click", () => {
        const input = document.getElementById("detailValueInput");
        input.readOnly = false;
        input.focus();
        document.getElementById("detailSaveBtn").style.display = "inline-block";
        detailApproveBtn.style.display = "none";
        detailRejectBtn.style.display = "none";
        detailEditBtn.style.display = "none";
        detailFlagBtn.style.display = "none";
      });
    }
    const detailSaveBtn = document.getElementById("detailSaveBtn");
    if (detailSaveBtn) {
      detailSaveBtn.addEventListener("click", () => {
        const val = document.getElementById("detailValueInput").value;
        submitDecisionInWorkspace("CORRECTED", val);
      });
    }

    // Page navigation
    const prevPageBtn = document.getElementById("prevPageBtn");
    const nextPageBtn = document.getElementById("nextPageBtn");
    if (prevPageBtn && nextPageBtn) {
      prevPageBtn.addEventListener("click", () => {
        if (!reviewState.selectedEntity) return;
        const currentPage = parseInt(reviewState.selectedEntity.page_number) || 1;
        if (currentPage <= 1) return;
        const targetPage = currentPage - 1;
        const entity = reviewState.entities.find((item) => Number(item.page_number) === targetPage);
        if (entity) {
          handleSelectReviewEntity(entity, true);
        } else {
          document.getElementById(`page-container-${targetPage}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
      nextPageBtn.addEventListener("click", () => {
        if (!reviewState.selectedEntity) return;
        const currentPage = parseInt(reviewState.selectedEntity.page_number) || 1;
        if (currentPage >= reviewState.pages.length) return;
        const targetPage = currentPage + 1;
        const entity = reviewState.entities.find((item) => Number(item.page_number) === targetPage);
        if (entity) {
          handleSelectReviewEntity(entity, true);
        } else {
          document.getElementById(`page-container-${targetPage}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    }
  }

  // Review Workspace Logic & State
  const reviewState = {
    pages: [],
    pageOffsets: [],
    entities: [],
    selectedEntity: null,
    activeTab: "PII",
    searchQuery: "",
    filters: {
      detectors: [],
      confidence: "all",
      reviewRequired: "all"
    },
    reviewMap: new Map(),
    revealValues: false
  };

  function computePageOffsets(pages) {
    let cumulative = 0;
    const separatorLength = 5; // \n\n\f\n\n
    return pages.map(page => {
      const start = cumulative;
      const end = start + page.text.length;
      cumulative = end + separatorLength;
      return { start, end };
    });
  }

  function getFilteredReviewEntities() {
    return reviewState.entities.filter((entity) => {
      if (normalizeCategory(entity.privacy_category) !== reviewState.activeTab) return false;

      if (reviewState.searchQuery) {
        const query = reviewState.searchQuery.toLowerCase();
        const matchesSearch = [entity.entity_value, entity.entity_type, entity.detector]
          .some((value) => String(value || "").toLowerCase().includes(query));
        if (!matchesSearch) return false;
      }

      if (
        reviewState.filters.detectors.length
        && !reviewState.filters.detectors.includes(String(entity.detector || "").toLowerCase())
      ) return false;

      const confidence = (
        entity.final_confidence == null
          ? entity.confidence_score
          : entity.final_confidence
      ) * 100;
      if (reviewState.filters.confidence === "90-100" && confidence < 90) return false;
      if (reviewState.filters.confidence === "80-90" && (confidence < 80 || confidence >= 90)) return false;
      if (reviewState.filters.confidence === "below-80" && confidence >= 80) return false;
      if (reviewState.filters.reviewRequired === "yes" && !entity.is_review_required) return false;
      if (reviewState.filters.reviewRequired === "no" && entity.is_review_required) return false;
      return true;
    });
  }

  function setReviewActiveTab(category) {
    reviewState.activeTab = category;
    reviewState.selectedEntity = getFilteredReviewEntities()[0] || null;

    document.getElementById("piiTabBtn")?.classList.toggle("active", category === "PII");
    document.getElementById("phiTabBtn")?.classList.toggle("active", category === "PHI");
    renderReviewWorkspaceText();
    renderReviewWorkspaceCards();
    renderReviewWorkspaceDetails();
  }

  function navigateReviewEntity(direction, fromEntity) {
    const entities = getFilteredReviewEntities();
    if (!entities.length) return;
    const current = fromEntity || reviewState.selectedEntity;
    const currentIndex = current
      ? entities.findIndex((entity) => entity.id === current.id)
      : -1;
    const nextIndex = currentIndex < 0
      ? (direction < 0 ? entities.length - 1 : 0)
      : currentIndex + direction;
    if (nextIndex < 0 || nextIndex >= entities.length) return;
    handleSelectReviewEntity(entities[nextIndex], true);
  }

  function updatePageNavigationControls() {
    const currentPage = reviewState.selectedEntity
      ? (parseInt(reviewState.selectedEntity.page_number) || 1)
      : 1;
    const previousButton = document.getElementById("prevPageBtn");
    const nextButton = document.getElementById("nextPageBtn");
    if (previousButton) previousButton.disabled = !reviewState.selectedEntity || currentPage <= 1;
    if (nextButton) nextButton.disabled = !reviewState.selectedEntity || currentPage >= reviewState.pages.length;
  }

  function renderReviewPageText(page, pageIndex) {
    const offset = reviewState.pageOffsets[pageIndex];
    const pageEntities = reviewState.entities
      .filter((entity) => String(entity.page_number) === String(page.page_number))
      .map((entity) => ({
        entity,
        start: Number(entity.start_char) - offset.start,
        end: Number(entity.end_char) - offset.start,
      }))
      .filter((item) => (
        Number.isFinite(item.start)
        && Number.isFinite(item.end)
        && item.start >= 0
        && item.end > item.start
        && item.end <= page.text.length
      ))
      .sort((left, right) => left.start - right.start || left.end - right.end);

    if (!pageEntities.length) return escapeHtml(page.text);

    let cursor = 0;
    let html = "";
    pageEntities.forEach(({ entity, start, end }) => {
      if (start < cursor) return;
      html += escapeHtml(page.text.slice(cursor, start));
      const isActive = reviewState.selectedEntity && reviewState.selectedEntity.id === entity.id;
      const categoryClass = normalizeCategory(entity.privacy_category).toLowerCase();
      html += `<span ${isActive ? `id="active-highlight-span"` : ""} class="entity-highlight ${categoryClass} ${isActive ? "is-active" : ""}" data-review-entity-id="${escapeHtml(entity.id)}">${escapeHtml(page.text.slice(start, end))}</span>`;
      cursor = end;
    });
    return html + escapeHtml(page.text.slice(cursor));
  }

  function renderReviewWorkspaceText() {
    const container = document.getElementById("pagesScrollContainer");
    if (!container) return;

    if (!reviewState.pages.length) {
      container.innerHTML = `<div class="empty-state">No text pages available.</div>`;
      return;
    }

    container.innerHTML = reviewState.pages.map((page, index) => {
      const pageNum = page.page_number;
      const isSelectedPage = reviewState.selectedEntity && reviewState.selectedEntity.page_number == pageNum;
      
      const pageHtmlText = renderReviewPageText(page, index);

      return `
        <div id="page-container-${pageNum}" class="page-box ${isSelectedPage ? "active-page" : ""}">
          <h4>Page ${pageNum}</h4>
          <pre class="document-text">${pageHtmlText}</pre>
        </div>
      `;
    }).join("");

    const currentNumEl = document.getElementById("currentPageNum");
    const totalNumEl = document.getElementById("totalPageNum");
    if (currentNumEl && totalNumEl) {
      currentNumEl.textContent = reviewState.selectedEntity ? reviewState.selectedEntity.page_number : 1;
      totalNumEl.textContent = reviewState.pages.length;
    }
    updatePageNavigationControls();
  }

  function renderReviewWorkspaceCards() {
    const listContainer = document.getElementById("cardsListContainer");
    if (!listContainer) return;

    const occurrenceTotals = new Map();
    reviewState.entities.forEach(entity => {
      const key = `${entity.entity_type || ""}\u0000${entity.entity_value || ""}`;
      occurrenceTotals.set(key, (occurrenceTotals.get(key) || 0) + 1);
    });
    const occurrenceSeen = new Map();
    const occurrenceById = new Map();
    reviewState.entities.forEach(entity => {
      const key = `${entity.entity_type || ""}\u0000${entity.entity_value || ""}`;
      const index = (occurrenceSeen.get(key) || 0) + 1;
      occurrenceSeen.set(key, index);
      occurrenceById.set(entity.id, {
        index,
        total: occurrenceTotals.get(key) || 1
      });
    });

    const filtered = getFilteredReviewEntities();

    const piiCount = reviewState.entities.filter(e => normalizeCategory(e.privacy_category) === "PII").length;
    const phiCount = reviewState.entities.filter(e => normalizeCategory(e.privacy_category) === "PHI").length;
    document.getElementById("piiTabCount").textContent = piiCount;
    document.getElementById("phiTabCount").textContent = phiCount;

    if (!filtered.length) {
      reviewState.selectedEntity = null;
      listContainer.innerHTML = `<div class="empty-state">No entities match criteria.</div>`;
      renderReviewWorkspaceText();
      renderReviewWorkspaceDetails();
      return;
    }

    let selectedIndex = reviewState.selectedEntity
      ? filtered.findIndex((entity) => entity.id === reviewState.selectedEntity.id)
      : -1;
    if (selectedIndex < 0) {
      selectedIndex = 0;
      reviewState.selectedEntity = filtered[0];
      renderReviewWorkspaceText();
      renderReviewWorkspaceDetails();
    }

    const entity = filtered[selectedIndex];
    const catClass = normalizeCategory(entity.privacy_category).toLowerCase();
    const confidence = confidenceLabel(entity.final_confidence == null ? entity.confidence_score : entity.final_confidence);
    const rStatus = reviewState.reviewMap.has(entity.id)
      ? reviewState.reviewMap.get(entity.id).review_status
      : (entity.is_review_required ? "PENDING" : "AUTO APPROVED");
    const displayVal = reviewState.revealValues ? entity.entity_value : maskValue(entity.entity_value);
    const occurrence = occurrenceById.get(entity.id) || { index: 1, total: 1 };
    const occurrenceLabel = occurrence.total > 1
      ? `Occurrence ${occurrence.index} of ${occurrence.total}`
      : "Single occurrence";

    listContainer.innerHTML = `
      <div class="entity-card active" data-entity-id="${entity.id}">
        <div class="card-header-row">
          <span class="card-label">${escapeHtml(entity.entity_type)}</span>
          <span class="card-badge ${catClass}">${escapeHtml(entity.privacy_category)}</span>
        </div>
        <div class="card-details">
          <div><strong>Value:</strong> ${escapeHtml(displayVal)}</div>
          <div><strong>Detector:</strong> ${escapeHtml(entity.detector)}</div>
          <div><strong>Confidence:</strong> ${escapeHtml(confidence)} &middot; <span class="status-pill ${statusTone(rStatus)}">${escapeHtml(rStatus)}</span></div>
          <div><strong>Position:</strong> ${escapeHtml(occurrenceLabel)} &middot; Page ${escapeHtml(entity.page_number)} &middot; chars ${escapeHtml(entity.start_char)}-${escapeHtml(entity.end_char)}</div>
        </div>
        <div class="card-actions entity-navigation-actions">
          <button class="button secondary compact previous-entity-btn" data-entity-id="${entity.id}" type="button" ${selectedIndex === 0 ? "disabled" : ""}>Previous</button>
          <strong class="entity-position-indicator">${selectedIndex + 1} of ${filtered.length}</strong>
          <button class="button secondary compact next-entity-btn" data-entity-id="${entity.id}" type="button" ${selectedIndex === filtered.length - 1 ? "disabled" : ""}>Next</button>
        </div>
      </div>
    `;
  }

  function renderReviewWorkspaceDetails() {
    const emptyDetails = document.getElementById("emptyDetails");
    const detailsContent = document.getElementById("detailsContent");
    if (!emptyDetails || !detailsContent) return;

    const entity = reviewState.selectedEntity;
    if (!entity) {
      emptyDetails.style.display = "flex";
      detailsContent.style.display = "none";
      return;
    }

    emptyDetails.style.display = "none";
    detailsContent.style.display = "block";

    document.getElementById("detailType").textContent = entity.entity_type;
    document.getElementById("detailCategory").textContent = entity.privacy_category;
    document.getElementById("detailDetector").textContent = entity.detector;
    document.getElementById("detailConfidence").textContent = confidenceLabel(entity.final_confidence == null ? entity.confidence_score : entity.final_confidence);
    document.getElementById("detailPage").textContent = entity.page_number;
    document.getElementById("detailRange").textContent = `${entity.start_char}-${entity.end_char}`;
    
    const input = document.getElementById("detailValueInput");
    input.value = entity.entity_value;
    input.readOnly = true;

    const rObj = reviewState.reviewMap.get(entity.id);
    const rStatus = rObj ? rObj.review_status : (entity.is_review_required ? "PENDING" : "AUTO APPROVED");
    const needsReview = entity.is_review_required === true;
    const actionRow = document.querySelector(".detail-actions-row");

    let statusInfo = document.getElementById("detailStatusInfo");
    if (!needsReview) {
      document.getElementById("detailSaveBtn").style.display = "none";
      document.getElementById("detailApproveBtn").style.display = "none";
      document.getElementById("detailRejectBtn").style.display = "none";
      document.getElementById("detailEditBtn").style.display = "none";
      document.getElementById("detailFlagBtn").style.display = "none";
      
      if (!statusInfo) {
        statusInfo = document.createElement("div");
        statusInfo.id = "detailStatusInfo";
        statusInfo.style.margin = "10px 0";
        statusInfo.style.fontSize = "0.85rem";
        statusInfo.style.fontWeight = "bold";
        actionRow.parentNode.insertBefore(statusInfo, actionRow);
      }
      
      let badgeText = "No Review Required";
      if (rStatus === "APPROVED" || rStatus === "REJECTED" || rStatus === "CORRECTED") {
        badgeText = `Reviewed: ${rStatus}`;
      } else {
        badgeText = "Auto Approved (No Review Required)";
      }
      
      statusInfo.innerHTML = `<span class="status-pill success">${badgeText}</span>`;
      statusInfo.style.display = "block";
    } else {
      document.getElementById("detailSaveBtn").style.display = "none";
      document.getElementById("detailApproveBtn").style.display = "inline-block";
      document.getElementById("detailRejectBtn").style.display = "inline-block";
      document.getElementById("detailEditBtn").style.display = "inline-block";
      document.getElementById("detailFlagBtn").style.display = "inline-block";
      
      if (statusInfo) {
        statusInfo.style.display = "none";
      }
    }
  }

  function handleSelectReviewEntity(entity, shouldScroll) {
    reviewState.selectedEntity = entity;
    reviewState.activeTab = normalizeCategory(entity.privacy_category);
    document.getElementById("piiTabBtn")?.classList.toggle("active", reviewState.activeTab === "PII");
    document.getElementById("phiTabBtn")?.classList.toggle("active", reviewState.activeTab === "PHI");
    
    renderReviewWorkspaceText();
    renderReviewWorkspaceCards();
    renderReviewWorkspaceDetails();

    if (shouldScroll) {
      setTimeout(() => {
        const pageEl = document.getElementById(`page-container-${entity.page_number}`);
        if (pageEl) {
          pageEl.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        
        const highlightEl = document.getElementById("active-highlight-span");
        if (highlightEl) {
          highlightEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        const activeCard = document.querySelector(".entity-card.active");
        if (activeCard) {
          activeCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      }, 100);
    }
  }

  async function openReviewWorkspace() {
    if (!state.activeDocumentId) return;

    try {
      showToast("Loading review workspace...");
      
      const textPayload = await apiFetch(`/documents/${encodeURIComponent(state.activeDocumentId)}/text`);
      const entities = await apiFetch(`/documents/${encodeURIComponent(state.activeDocumentId)}/entities`);
      const status = await apiFetch(`/documents/${encodeURIComponent(state.activeDocumentId)}/status`);
      const reviews = await apiFetch(`/documents/${encodeURIComponent(state.activeDocumentId)}/reviews`);

      document.getElementById("reviewFilename").textContent = status.filename || state.activeDocumentId;

      const rawText = textPayload.extracted_text || "";
      const pageTexts = rawText.split("\n\n\f\n\n");
      reviewState.pages = pageTexts.map((text, idx) => ({
        page_number: idx + 1,
        text: text
      }));
      reviewState.pageOffsets = computePageOffsets(reviewState.pages);

      reviewState.entities = entities.map((ent, idx) => ({
        ...ent,
        id: ent.entity_id || ent.id || `ent-${idx}`
      })).sort((left, right) => {
        const pageDifference = (parseInt(left.page_number) || 0) - (parseInt(right.page_number) || 0);
        if (pageDifference !== 0) return pageDifference;
        const startDifference = (left.start_char ?? Number.MAX_SAFE_INTEGER) - (right.start_char ?? Number.MAX_SAFE_INTEGER);
        if (startDifference !== 0) return startDifference;
        return (left.end_char ?? Number.MAX_SAFE_INTEGER) - (right.end_char ?? Number.MAX_SAFE_INTEGER);
      });
      reviewState.selectedEntity = null;

      // Build review map
      reviewState.reviewMap.clear();
      reviews.forEach(r => {
        const entId = r.entity_id || (r.entity && (r.entity.id || r.entity.entity_id));
        if (entId) reviewState.reviewMap.set(entId, r);
      });

      // Switch screens
      document.querySelector(".app-header").style.display = "none";
      document.querySelector(".app-main").style.display = "none";
      document.getElementById("reviewWorkspace").style.display = "flex";

      renderReviewWorkspaceText();
      renderReviewWorkspaceCards();
      renderReviewWorkspaceDetails();

    } catch (error) {
      showToast(`Failed to load review workspace: ${error.message}`, true);
    }
  }

  function closeReviewWorkspace() {
    document.querySelector(".app-header").style.display = "flex";
    document.querySelector(".app-main").style.display = "block";
    document.getElementById("reviewWorkspace").style.display = "none";
    loadDashboard(state.activeDocumentId, { quiet: true });
  }

  async function submitDecisionInWorkspace(decision, editedVal = null) {
    const entity = reviewState.selectedEntity;
    if (!entity) return;

    const rObj = reviewState.reviewMap.get(entity.id);
    if (!rObj) {
      showToast("No associated review found for this entity.", true);
      return;
    }

    try {
      const payload = {
        review_status: decision,
        review_comment: `Reviewed in workspace. Decision: ${decision}`
      };
      if (editedVal !== null) {
        payload.entity_value = editedVal;
      }
      
      const updatedReview = await apiFetch(`/reviews/${encodeURIComponent(rObj.review_id)}`, {
        method: "PATCH",
        body: payload
      });

      showToast(`Entity marked as ${decision.toLowerCase()}.`);
      
      // Update local state
      rObj.review_status = decision;
      entity.is_review_required = false;
      if (editedVal !== null) {
        entity.entity_value = editedVal;
      }
      
      renderReviewWorkspaceCards();
      renderReviewWorkspaceDetails();
      renderReviewWorkspaceText();

    } catch (error) {
      showToast(`Failed to submit decision: ${error.message}`, true);
    }
  }

  function init() {
    if (!isAuthenticated()) {
      redirectToLogin();
      return;
    }

    readStoredState();
    applyTheme(preferredTheme());
    state.apiBase = normalizeBase(state.apiBase) || defaultApiBase();
    els.apiBase.value = state.apiBase;
    els.documentIdInput.value = state.activeDocumentId;
    renderDocumentList();
    renderFiles();
    renderStatus(null);
    renderReviews([], []);
    renderText(null);
    renderMetrics([], [], [], []);
    renderArtifacts([], []);
    renderLlmAudit({ accepted: [], rejected: [] });
    bindEvents();
    renderUserChip();
    applyRoleVisibility();
    syncUserDocuments();
    checkHealth();
    validateSession();
    if (state.activeDocumentId) {
      loadDashboard(state.activeDocumentId, { quiet: true });
    }
  }

  async function validateSession() {
    try {
      const user = await apiFetch("/auth/me");
      if (user) {
        const auth = getAuth();
        if (auth) {
          setAuth(auth.token, user);
          renderUserChip();
          applyRoleVisibility();
          syncUserDocuments();
        }
      }
    } catch (error) {
      /* apiFetch already redirected on 401 */
    }
  }

  init();
})();
