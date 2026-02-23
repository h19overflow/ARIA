"""
Parse user-provided API specs (OpenAPI 3.x, Swagger 2.x, Postman collections)
into a flat list of endpoint documents for embedding into ChromaDB.
"""

from dataclasses import dataclass


@dataclass
class ApiEndpoint:
    id: str
    source: str
    method: str
    path: str
    summary: str
    description: str
    operation_id: str
    text: str              # the string that gets embedded
    metadata: dict


def parse_api_spec(spec: dict, source_name: str) -> list[ApiEndpoint]:
    """
    Auto-detect spec format and delegate to the appropriate parser.
    Supports: OpenAPI 3.x, Swagger 2.x, Postman Collection v2.x
    """
    if "openapi" in spec:
        return _parse_openapi(spec, source_name)
    if "swagger" in spec:
        return _parse_swagger(spec, source_name)
    if "info" in spec and "item" in spec:
        return _parse_postman(spec, source_name)
    raise ValueError(f"Unrecognised API spec format for source '{source_name}'")


# ---------------------------------------------------------------------------
# OpenAPI 3.x
# ---------------------------------------------------------------------------

def _parse_openapi(spec: dict, source_name: str) -> list[ApiEndpoint]:
    endpoints: list[ApiEndpoint] = []
    base_url = _extract_openapi_base_url(spec)

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            endpoints.append(_build_endpoint(
                source=source_name,
                method=method.upper(),
                path=path,
                summary=operation.get("summary", ""),
                description=operation.get("description", ""),
                operation_id=operation.get("operationId", ""),
                base_url=base_url,
            ))
    return endpoints


def _extract_openapi_base_url(spec: dict) -> str:
    servers = spec.get("servers", [])
    if servers:
        return servers[0].get("url", "")
    return ""


# ---------------------------------------------------------------------------
# Swagger 2.x
# ---------------------------------------------------------------------------

def _parse_swagger(spec: dict, source_name: str) -> list[ApiEndpoint]:
    endpoints: list[ApiEndpoint] = []
    host = spec.get("host", "")
    base_path = spec.get("basePath", "")
    base_url = f"https://{host}{base_path}" if host else ""

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            endpoints.append(_build_endpoint(
                source=source_name,
                method=method.upper(),
                path=path,
                summary=operation.get("summary", ""),
                description=operation.get("description", ""),
                operation_id=operation.get("operationId", ""),
                base_url=base_url,
            ))
    return endpoints


# ---------------------------------------------------------------------------
# Postman Collection v2.x
# ---------------------------------------------------------------------------

def _parse_postman(collection: dict, source_name: str) -> list[ApiEndpoint]:
    endpoints: list[ApiEndpoint] = []
    _extract_postman_items(collection.get("item", []), source_name, endpoints)
    return endpoints


def _extract_postman_items(
    items: list,
    source_name: str,
    acc: list[ApiEndpoint],
) -> None:
    for item in items:
        # Folder — recurse
        if "item" in item:
            _extract_postman_items(item["item"], source_name, acc)
            continue

        request = item.get("request", {})
        if not request:
            continue

        method = request.get("method", "GET").upper()
        url = request.get("url", {})
        raw_url = url.get("raw", "") if isinstance(url, dict) else str(url)
        path = "/" + "/".join(url.get("path", [])) if isinstance(url, dict) else raw_url

        acc.append(_build_endpoint(
            source=source_name,
            method=method,
            path=path,
            summary=item.get("name", ""),
            description=request.get("description", ""),
            operation_id="",
            base_url=raw_url,
        ))


# ---------------------------------------------------------------------------
# Shared builder
# ---------------------------------------------------------------------------

def _build_endpoint(
    source: str,
    method: str,
    path: str,
    summary: str,
    description: str,
    operation_id: str,
    base_url: str,
) -> ApiEndpoint:
    import hashlib
    raw_id = f"{source}::{method}::{path}"
    endpoint_id = hashlib.md5(raw_id.encode()).hexdigest()

    text_parts = [f"{method} {path}"]
    if summary:
        text_parts.append(summary)
    if description:
        text_parts.append(description)
    text = " — ".join(text_parts)

    return ApiEndpoint(
        id=endpoint_id,
        source=source,
        method=method,
        path=path,
        summary=summary,
        description=description,
        operation_id=operation_id,
        text=text,
        metadata={
            "source": source,
            "method": method,
            "path": path,
            "summary": summary,
            "operation_id": operation_id,
            "base_url": base_url,
        },
    )
