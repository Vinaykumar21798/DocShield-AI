(function () {
  const STORAGE_KEY = "docshield-ui-state-v1";
  const POLL_MS = 4000;

  const els = {
    apiBase: document.getElementById("apiBase"),
    healthBtn: document.getElementById("healthBtn"),
    healthBadge: document.getElementById("healthBadge"),
    uploadForm: document.getElementById("uploadForm"),
    fileInput: document.getElementById("fileInput"),
    fileSummary: document.getElementById("fileSummary"),
    fileList: document.getElementById("fileList"),
    dropZone: document.getElementById("dropZone"),
    documentList: document.getElementById("documentList"),
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
      llmAudit: { accepted: [], rejected: [] },
    },
    revealValues: false,
    activeReviewFilter: "all",
    activeLlmTab: "accepted",
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

  function normalizeBase(value) {
    return (value || "").trim().replace(/\/+$/, "");
  }

  async function apiFetch(path, options) {
    const requestOptions = options || {};
    const headers = new Headers(requestOptions.headers || {});
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
      const error = new Error(detail);
      error.status = response.status;
      throw error;
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

    els.fileList.innerHTML = files.map((file) => `
      <div class="file-item">
        <span title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
        <small>${escapeHtml(formatBytes(file.size))}</small>
      </div>
    `).join("");
  }

  function upsertDocuments(documents) {
    const incoming = documents.map((document) => ({
      id: document.document_id,
      filename: document.filename || document.document_id,
      status: document.status || document.document_status || "UPLOADED",
      uploadedAt: new Date().toISOString(),
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
    renderStatus(null);
    renderText(null);
    renderReviews([], []);
    renderMetrics([], [], [], []);
    renderArtifacts([], []);
    renderWorkflow(0);
  }

  function renderDocumentList() {
    els.recentCount.textContent = state.documents.length
      ? `${state.documents.length} tracked document${state.documents.length === 1 ? "" : "s"}.`
      : "No tracked documents.";

    if (!state.documents.length) {
      els.documentList.innerHTML = `<div class="empty-state">Uploaded documents appear here.</div>`;
      return;
    }

    els.documentList.innerHTML = state.documents.map((document) => `
      <button class="document-item ${document.id === state.activeDocumentId ? "is-active" : ""}" type="button" data-document-id="${escapeHtml(document.id)}">
        <span class="document-main">
          <strong title="${escapeHtml(document.filename)}">${escapeHtml(document.filename)}</strong>
          <span class="document-id">${escapeHtml(truncate(document.id, 30))}</span>
        </span>
        <span class="status-pill ${statusTone(document.status)}">${escapeHtml(document.status || "Uploaded")}</span>
      </button>
    `).join("");
  }

  function renderStatus(status) {
    state.dashboard.status = status || null;

    if (!status) {
      els.activeFilename.textContent = "Select or upload a document.";
      setBadge(els.processingBadge, "Idle", "neutral");
      els.statusDetails.innerHTML = `
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

  function renderMetrics(reviews, reports, redactions, entities) {
    if (Array.isArray(entities)) {
      state.dashboard.entities = entities;
    }

    const latestReport = reports[0] || null;
    const entityRows = getDisplayEntities();
    const pendingReviews = reviews.filter((review) => normalizeReviewStatus(review) === "PENDING").length;
    const piiCount = entityRows.length
      ? entityRows.filter((entity) => normalizeCategory(entity.privacy_category) === "PII").length
      : (latestReport ? latestReport.total_pii : 0);
    const phiCount = entityRows.length
      ? entityRows.filter((entity) => normalizeCategory(entity.privacy_category) === "PHI").length
      : (latestReport ? latestReport.total_phi : 0);
    const entityCount = entityRows.length || (latestReport ? latestReport.total_entities : 0);

    els.metricEntities.textContent = entityCount || 0;
    els.metricPii.textContent = piiCount || 0;
    els.metricPhi.textContent = phiCount || 0;
    els.metricPending.textContent = pendingReviews || 0;

    if (latestReport) {
      const redactionCount = latestReport.total_redactions || redactions.length || 0;
      els.reportTimestamp.textContent = `${redactionCount} redaction${redactionCount === 1 ? "" : "s"} logged. Report created ${formatDate(latestReport.created_at)}.`;
    } else if (entityRows.length || reviews.length || redactions.length) {
      els.reportTimestamp.textContent = `${entityRows.length} detected entit${entityRows.length === 1 ? "y" : "ies"}; ${reviews.length} review item${reviews.length === 1 ? "" : "s"}.`;
    } else {
      els.reportTimestamp.textContent = "Waiting for report data.";
    }
  }

  function renderReviews(reviews, entities) {
    if (Array.isArray(reviews)) {
      state.dashboard.reviews = reviews;
    }
    if (Array.isArray(entities)) {
      state.dashboard.entities = entities;
    }

    const filterLabel = REVIEW_FILTERS[state.activeReviewFilter] || REVIEW_FILTERS.all;
    const showReviewColumns = state.activeReviewFilter === "pending";
    const colSpan = showReviewColumns ? 6 : 4;
    const rows = getFilteredFindingRows();
    const pending = getPendingReviews().length;

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
        <tr>
          <td>
            <span class="entity-type">
              <strong>${escapeHtml(entity.entity_type || "Entity")}</strong>
              <small>${escapeHtml(detector)}</small>
            </span>
          </td>
          <td><span class="entity-value" title="${state.revealValues ? "" : "Masked"}">${escapeHtml(maskValue(entity.entity_value))}</span></td>
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

    if (!currentItems.length) {
      els.llmAuditBody.innerHTML = `<tr><td colspan="6" class="empty-state">No ${state.activeLlmTab} LLM candidates for this document.</td></tr>`;
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
          <td>${escapeHtml(confidencePct)}</td>
          <td><small>${escapeHtml(item.detector || "Qwen3:4b")}</small></td>
          <td style="max-width: 320px; font-size: 0.85rem; line-height: 1.35; color: var(--text-muted, #475569);">${escapeHtml(item.reasoning || item.reason || "-")}</td>
        </tr>
      `;
    }).join("");
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

  function renderArtifacts(reports, redactions) {
    state.dashboard.reports = reports || [];
    state.dashboard.redactions = redactions || [];

    const items = [];
    state.dashboard.redactions.forEach((redaction) => {
      items.push(`
        <div class="artifact-item">
          <span class="artifact-meta">
            <strong>Redacted text</strong>
            <small>${escapeHtml(redaction.redaction_type || "Text artifact")} &middot; ${escapeHtml(formatDate(redaction.created_at))}</small>
          </span>
          <a class="button ghost compact" href="${escapeHtml(artifactUrl(`/redactions/${redaction.redaction_id}/file`))}" target="_blank" rel="noreferrer">Download</a>
        </div>
      `);
    });

    state.dashboard.reports.forEach((report) => {
      items.push(`
        <div class="artifact-item">
          <span class="artifact-meta">
            <strong>Audit report</strong>
            <small>${escapeHtml(report.report_type || "JSON report")} &middot; ${escapeHtml(formatDate(report.created_at))}</small>
          </span>
          <a class="button ghost compact" href="${escapeHtml(artifactUrl(`/reports/${report.report_id}/file`))}" target="_blank" rel="noreferrer">Download</a>
        </div>
      `);
    });

    els.artifactList.innerHTML = items.length ? items.join("") : `<div class="empty-state">No artifacts loaded.</div>`;
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

    state.activeDocumentId = id;
    els.documentIdInput.value = id;
    persistState();
    renderDocumentList();
    setBadge(els.processingBadge, "Loading", "warning");

    let status;
    try {
      status = await apiFetch(`/documents/${encodeURIComponent(id)}/status`);
    } catch (error) {
      if (error.status === 404) {
        removeTrackedDocument(id);
        stopPolling();
      }
      renderEmptyDashboard();
      if (!quiet) {
        showToast(`Status lookup failed: ${error.message}`, true);
      }
      return;
    }

    const requests = await Promise.allSettled([
      status.has_extracted_text ? apiFetch(`/documents/${encodeURIComponent(id)}/text`) : Promise.resolve(null),
      apiFetch(`/documents/${encodeURIComponent(id)}/entities`),
      apiFetch(`/documents/${encodeURIComponent(id)}/reviews`),
      apiFetch(`/documents/${encodeURIComponent(id)}/reports`),
      apiFetch(`/documents/${encodeURIComponent(id)}/redactions`),
    ]);

    const text = requests[0].status === "fulfilled" ? requests[0].value : null;
    const entities = requests[1].status === "fulfilled" ? requests[1].value : [];
    const reviews = requests[2].status === "fulfilled" ? requests[2].value : [];
    const reports = requests[3].status === "fulfilled" ? requests[3].value : [];
    const redactions = requests[4].status === "fulfilled" ? requests[4].value : [];

    let llmAudit = { accepted: [], rejected: [] };
    if (reports && reports.length > 0) {
      try {
        const reportDetail = await apiFetch(`/reports/${encodeURIComponent(reports[0].report_id)}`);
        if (reportDetail && reportDetail.payload && reportDetail.payload.llm_candidate_audit) {
          llmAudit = reportDetail.payload.llm_candidate_audit;
        }
      } catch (err) {
        // payload load optional
      }
    }

    renderStatus(status);
    renderText(text);
    renderReviews(reviews, entities);
    renderMetrics(reviews, reports, redactions, entities);
    renderArtifacts(reports, redactions);
    renderLlmAudit(llmAudit);
    updateWorkflow(status, reviews, reports, redactions);

    if (status && status.has_extracted_text) {
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
          reviewer: "PoC Reviewer",
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
    els.healthBtn.addEventListener("click", checkHealth);
    els.uploadForm.addEventListener("submit", uploadDocuments);
    els.fileInput.addEventListener("change", renderFiles);

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

    els.metricFilters.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.reviewFilter;
        if (!REVIEW_FILTERS[filter]) return;
        state.activeReviewFilter = filter;
        renderReviews();
      });
    });

    els.clearRecentBtn.addEventListener("click", () => {
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
        piiTabBtn.classList.add("active");
        phiTabBtn.classList.remove("active");
        reviewState.activeTab = "PII";
        renderReviewWorkspaceCards();
      });
      phiTabBtn.addEventListener("click", () => {
        phiTabBtn.classList.add("active");
        piiTabBtn.classList.remove("active");
        reviewState.activeTab = "PHI";
        renderReviewWorkspaceCards();
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
        
        const isGoTo = e.target.classList.contains("go-to-btn");
        handleSelectReviewEntity(entity, isGoTo);
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
        const current = parseInt(reviewState.selectedEntity.page_number) || 1;
        if (current > 1) {
          const nextEntity = reviewState.entities.find(e => e.page_number == current - 1);
          if (nextEntity) {
            handleSelectReviewEntity(nextEntity, true);
          } else {
            // No entity, just scroll page
            const el = document.getElementById(`page-container-${current - 1}`);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }
      });
      nextPageBtn.addEventListener("click", () => {
        if (!reviewState.selectedEntity) return;
        const current = parseInt(reviewState.selectedEntity.page_number) || 1;
        if (current < reviewState.pages.length) {
          const nextEntity = reviewState.entities.find(e => e.page_number == current + 1);
          if (nextEntity) {
            handleSelectReviewEntity(nextEntity, true);
          } else {
            // No entity, just scroll page
            const el = document.getElementById(`page-container-${current + 1}`);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
          }
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
      
      let pageHtmlText = escapeHtml(page.text);
      if (isSelectedPage) {
        const offsetInfo = reviewState.pageOffsets[index];
        const localStart = reviewState.selectedEntity.start_char - offsetInfo.start;
        const localEnd = reviewState.selectedEntity.end_char - offsetInfo.start;

        if (localStart >= 0 && localEnd <= page.text.length) {
          const before = page.text.slice(0, localStart);
          const matchVal = page.text.slice(localStart, localEnd);
          const after = page.text.slice(localEnd);
          pageHtmlText = `${escapeHtml(before)}<span id="active-highlight-span" class="entity-highlight selected-border">${escapeHtml(matchVal)}</span>${escapeHtml(after)}`;
        }
      }

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

    const filtered = reviewState.entities.filter(entity => {
      if (normalizeCategory(entity.privacy_category) !== reviewState.activeTab) return false;

      if (reviewState.searchQuery) {
        const q = reviewState.searchQuery.toLowerCase();
        const valueMatch = (entity.entity_value || "").toLowerCase().includes(q);
        const typeMatch = (entity.entity_type || "").toLowerCase().includes(q);
        const detectorMatch = (entity.detector || "").toLowerCase().includes(q);
        if (!valueMatch && !typeMatch && !detectorMatch) return false;
      }

      if (reviewState.filters.detectors.length > 0) {
        if (!reviewState.filters.detectors.includes((entity.detector || "").toLowerCase())) {
          return false;
        }
      }

      const score = (entity.final_confidence == null ? entity.confidence_score : entity.final_confidence) * 100;
      if (reviewState.filters.confidence === "90-100" && score < 90) return false;
      if (reviewState.filters.confidence === "80-90" && (score < 80 || score >= 90)) return false;
      if (reviewState.filters.confidence === "below-80" && score >= 80) return false;

      if (reviewState.filters.reviewRequired === "yes" && !entity.is_review_required) return false;
      if (reviewState.filters.reviewRequired === "no" && entity.is_review_required) return false;

      return true;
    });

    const piiCount = reviewState.entities.filter(e => normalizeCategory(e.privacy_category) === "PII").length;
    const phiCount = reviewState.entities.filter(e => normalizeCategory(e.privacy_category) === "PHI").length;
    document.getElementById("piiTabCount").textContent = piiCount;
    document.getElementById("phiTabCount").textContent = phiCount;

    if (!filtered.length) {
      listContainer.innerHTML = `<div class="empty-state">No entities match criteria.</div>`;
      return;
    }

    listContainer.innerHTML = filtered.map(entity => {
      const activeClass = reviewState.selectedEntity && reviewState.selectedEntity.id === entity.id ? "active" : "";
      const catClass = normalizeCategory(entity.privacy_category).toLowerCase();
      const confidence = confidenceLabel(entity.final_confidence == null ? entity.confidence_score : entity.final_confidence);
      
      const rStatus = reviewState.reviewMap.has(entity.id) ? reviewState.reviewMap.get(entity.id).review_status : (entity.is_review_required ? "PENDING" : "AUTO APPROVED");
      const displayVal = reviewState.revealValues ? entity.entity_value : maskValue(entity.entity_value);
      const occurrence = occurrenceById.get(entity.id) || { index: 1, total: 1 };
      const occurrenceLabel = occurrence.total > 1
        ? `Occurrence ${occurrence.index} of ${occurrence.total}`
        : "Single occurrence";

      return `
        <div class="entity-card ${activeClass}" data-entity-id="${entity.id}">
          <div class="card-header-row">
            <span class="card-label">${escapeHtml(entity.entity_type)}</span>
            <span class="card-badge ${catClass}">${escapeHtml(entity.privacy_category)}</span>
          </div>
          <div class="card-details">
            <div><strong>Value:</strong> ${escapeHtml(displayVal)}</div>
            <div><strong>Detector:</strong> ${escapeHtml(entity.detector)}</div>
            <div><strong>Confidence:</strong> ${escapeHtml(confidence)} &middot; <span class="status-pill ${statusTone(rStatus)}">${rStatus}</span></div>
            <div><strong>Position:</strong> ${escapeHtml(occurrenceLabel)} &middot; Page ${escapeHtml(entity.page_number)} &middot; chars ${escapeHtml(entity.start_char)}-${escapeHtml(entity.end_char)}</div>
          </div>
          <div class="card-actions">
            <button class="button secondary compact go-to-btn" data-entity-id="${entity.id}" type="button">Go To</button>
          </div>
        </div>
      `;
    }).join("");
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
        reviewer: "UI Auditor",
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
    readStoredState();
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
    bindEvents();
    checkHealth();
    if (state.activeDocumentId) {
      loadDashboard(state.activeDocumentId, { quiet: true });
    }
  }

  init();
})();
