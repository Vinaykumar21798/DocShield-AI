import html
import json

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.docs import swagger_ui_default_parameters
from fastapi.responses import HTMLResponse

from api.routes import api_router


SWAGGER_UI_BULK_UPLOAD_PATCH = """
<script>
(function () {
    const BULK_UPLOAD_PATH = "/upload/bulk";
    const HIDDEN_CLASS = "bulk-upload-hidden";

    function compactText(element) {
        return (element.textContent || "").replace(/\s+/g, "").trim();
    }

    function getBulkUploadBlock() {
        const blocks = document.querySelectorAll(".swagger-ui .opblock");
        return Array.from(blocks).find(function (block) {
            const path = block.querySelector(".opblock-summary-path");
            return path && compactText(path) === BULK_UPLOAD_PATH;
        });
    }

    function getBulkUploadInput() {
        const block = getBulkUploadBlock();
        return block ? block.querySelector('input[type="file"]') : null;
    }

    function hideSwaggerArrayControls(block) {
        const buttons = block.querySelectorAll("button");
        Array.from(buttons).forEach(function (button) {
            const text = (button.textContent || "").trim();
            if (text === "Add string item" || text === "-") {
                button.classList.add(HIDDEN_CLASS);
                button.setAttribute("aria-hidden", "true");
                button.setAttribute("tabindex", "-1");
            }
        });
    }

    function renameArrayTypeLabel(block) {
        const typeLabels = block.querySelectorAll(".parameter__type");
        Array.from(typeLabels).forEach(function (label) {
            if (compactText(label).toLowerCase() === "array<string>") {
                label.textContent = "array<file>";
            }
        });
    }

    function patchBulkUploadControl() {
        const block = getBulkUploadBlock();
        if (!block) {
            return;
        }

        const input = block.querySelector('input[type="file"]');
        if (input) {
            input.multiple = true;
            input.name = "files";
            input.dataset.bulkUploadInput = "true";
            input.setAttribute("aria-label", "Choose one or more files");
        }

        hideSwaggerArrayControls(block);
        renameArrayTypeLabel(block);
    }

    function isBulkUploadRequest(request) {
        if (!request || !request.url || !request.method) {
            return false;
        }

        try {
            const requestUrl = new URL(request.url, window.location.origin);
            return request.method.toUpperCase() === "POST" && requestUrl.pathname.endsWith(BULK_UPLOAD_PATH);
        } catch (error) {
            return false;
        }
    }

    window.bulkUploadRequestInterceptor = function (request) {
        if (!isBulkUploadRequest(request)) {
            return request;
        }

        const input = getBulkUploadInput();
        if (!input || !input.files || input.files.length === 0) {
            return request;
        }

        const formData = new FormData();
        Array.from(input.files).forEach(function (file) {
            formData.append("files", file, file.name);
        });

        request.body = formData;
        delete request.formData;

        if (request.headers) {
            if (typeof request.headers.delete === "function") {
                request.headers.delete("Content-Type");
                request.headers.delete("content-type");
            } else {
                delete request.headers["Content-Type"];
                delete request.headers["content-type"];
            }
        }

        return request;
    };

    const observer = new MutationObserver(patchBulkUploadControl);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("load", patchBulkUploadControl);
    patchBulkUploadControl();
})();
</script>
"""


SWAGGER_UI_BULK_UPLOAD_STYLE = """
<style>
.swagger-ui .bulk-upload-hidden {
    display: none !important;
}
</style>
"""


app = FastAPI(
    title="PII/PHI Document Intelligence PoC",
    version="1.0.0",
    description="Backend API for document upload, OCR and PHI/PII processing.",
    docs_url=None,
)

app.include_router(api_router)


def _swagger_ui_parameters() -> str:
    parameters = swagger_ui_default_parameters.copy()
    parameter_lines = []

    for key, value in parameters.items():
        encoded_key = json.dumps(key)
        encoded_value = json.dumps(jsonable_encoder(value))
        parameter_lines.append(f"        {encoded_key}: {encoded_value},")

    return "\n".join(parameter_lines)


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui_html(request: Request) -> HTMLResponse:
    title = html.escape(f"{app.title} - Swagger UI")
    root_path = request.scope.get("root_path", "").rstrip("/")
    openapi_url = json.dumps(f"{root_path}{app.openapi_url}")

    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
            <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
            <title>{title}</title>
            {SWAGGER_UI_BULK_UPLOAD_STYLE}
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            {SWAGGER_UI_BULK_UPLOAD_PATCH}
            <script>
            const ui = SwaggerUIBundle({{
                url: {openapi_url},
{_swagger_ui_parameters()}
                requestInterceptor: window.bulkUploadRequestInterceptor,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
            }});
            </script>
        </body>
        </html>
        """
    )


@app.get("/")
def root():
    return {
        "message": "PII/PHI Document Intelligence PoC API"
    }
