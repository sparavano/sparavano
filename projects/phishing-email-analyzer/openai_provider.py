"""Optional Responses API transport for already minimized findings.

This module never reads email files or chooses a model. The caller must validate
the returned object against its local explanation policy before displaying it.
"""

from __future__ import annotations

import json
import os
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


ENDPOINT = "https://api.openai.com/v1/responses"
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 1024 * 1024


class ProviderError(ValueError):
    """A safe, user-facing provider failure without upstream response details."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the Authorization header to a redirected destination.
        raise ProviderError("El proveedor devolvió una redirección no permitida.")


def _configuration(api_key, model):
    key = os.environ.get("OPENAI_API_KEY") if api_key is None else api_key
    selected_model = os.environ.get("OPENAI_MODEL") if model is None else model
    if not isinstance(key, str) or not key.strip():
        raise ProviderError("Falta configurar OPENAI_API_KEY para usar OpenAI.")
    if not isinstance(selected_model, str) or not selected_model.strip():
        raise ProviderError("Falta configurar OPENAI_MODEL para usar OpenAI.")
    key = key.strip()
    selected_model = selected_model.strip()
    if any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ProviderError("La configuración de OpenAI no es válida.")
    if any(ord(char) < 32 or ord(char) == 127 for char in selected_model):
        raise ProviderError("La configuración de OpenAI no es válida.")
    return key, selected_model


def _payload(bundle, model):
    try:
        if not isinstance(bundle, dict):
            raise ValueError
        request_id = bundle["request_id"]
        instructions = bundle["instructions"]
        findings = bundle["findings"]
        schema = bundle["response_schema"]
        if not isinstance(request_id, str) or not request_id:
            raise ValueError
        if not isinstance(instructions, str) or not instructions:
            raise ValueError
        if not isinstance(findings, list) or not isinstance(schema, dict):
            raise ValueError
        minimized = []
        for finding in findings:
            if not isinstance(finding, dict):
                raise ValueError
            selected = {name: finding[name] for name in ("finding_id", "rule", "observation")}
            if any(not isinstance(value, str) or not value for value in selected.values()):
                raise ValueError
            minimized.append(selected)
        payload = {
            "model": model,
            "instructions": instructions,
            "input": json.dumps({"request_id": request_id, "findings": minimized}, ensure_ascii=False, allow_nan=False),
            "text": {"format": {
                "type": "json_schema",
                "name": "phishing_explanation",
                "schema": schema,
                "strict": True,
            }},
            "max_output_tokens": 3000,
            "store": False,
        }
        return json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise ProviderError("La solicitud de explicación no es válida.") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError


def _load_json(text):
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)


def _explanation(raw):
    try:
        response = _load_json(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        raise ProviderError("OpenAI devolvió una respuesta no válida.") from None
    if not isinstance(response, dict):
        raise ProviderError("OpenAI devolvió una respuesta no válida.")
    if response.get("status") != "completed":
        raise ProviderError("OpenAI no completó la explicación.")
    output = response.get("output")
    if not isinstance(output, list):
        raise ProviderError("OpenAI devolvió una respuesta no válida.")
    parts = []
    for item in output:
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            raise ProviderError("OpenAI devolvió una respuesta no válida.")
        if item["type"] != "message":
            continue
        if item.get("status", "completed") != "completed":
            raise ProviderError("OpenAI no completó la explicación.")
        content = item.get("content")
        if not isinstance(content, list):
            raise ProviderError("OpenAI devolvió una respuesta no válida.")
        for part in content:
            if not isinstance(part, dict):
                raise ProviderError("OpenAI devolvió una respuesta no válida.")
            if part.get("type") == "refusal":
                raise ProviderError("OpenAI rechazó generar la explicación.")
            if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                raise ProviderError("OpenAI devolvió una respuesta no válida.")
            parts.append(part["text"])
    if not parts:
        raise ProviderError("OpenAI devolvió una respuesta sin explicación.")
    try:
        result = _load_json("".join(parts))
    except (ValueError, RecursionError):
        raise ProviderError("OpenAI devolvió una explicación no válida.") from None
    if not isinstance(result, dict):
        raise ProviderError("OpenAI devolvió una explicación no válida.")
    return result


def request_explanation(bundle, *, api_key=None, model=None):
    """Request a JSON object; the caller must perform local policy validation.

    OPENAI_API_KEY and OPENAI_MODEL are used only when the respective argument
    is None. No request is made unless both settings and the bundle are valid.
    """
    key, selected_model = _configuration(api_key, model)
    body = _payload(bundle, selected_model)
    try:
        request = Request(ENDPOINT, data=body, method="POST", headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        opener = build_opener(_NoRedirect())
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.getcode() != 200:
                raise ProviderError("OpenAI no pudo procesar la solicitud.")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ProviderError("La respuesta de OpenAI excede el tamaño permitido.")
    except ProviderError:
        raise
    except HTTPError as error:
        # Do not read, print, or include the upstream error body or headers.
        error.close()
        raise ProviderError("OpenAI no pudo procesar la solicitud.") from None
    except (URLError, OSError, TimeoutError, HTTPException, ValueError, UnicodeError):
        raise ProviderError("No se pudo conectar con OpenAI o recibir su respuesta.") from None
    return _explanation(raw)
