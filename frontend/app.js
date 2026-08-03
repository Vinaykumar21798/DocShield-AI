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
    },
    revealValues: false,
    activeReviewFilter: "all",
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
      const status = review && review.review_status ? review.review_status : "PENDING";
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
    renderStatus(status);
    renderText(text);
    renderReviews(reviews, entities);
    renderMetrics(reviews, reports, redactions, entities);
    renderArtifacts(reports, redactions);
    updateWorkflow(status, reviews, reports, redactions);

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
