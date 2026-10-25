"""Evalúa el contrato con respuestas sintéticas; nunca consulta una API.

Ejecutar desde la raíz: python evals/offline_suite.py
Guarda resultados reproducibles y no exporta contenido ni huellas de correos.
"""

import copy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai_explainer as ai


def fixture_response(bundle):
    return {
        "request_id": bundle["request_id"],
        "review_required": True,
        "explanations": [{
            "finding_id": fact["finding_id"],
            "rule": fact["rule"],
            "explanation": "La observación requiere revisar su contexto antes de sacar conclusiones.",
            "manual_checks": ["Contrastar el hallazgo con el contexto del mensaje."],
        } for fact in bundle["findings"]],
    }


def run_suite():
    bundle = ai.build_ai_request({"findings": [{"rule": "urgent_subject"}, {"rule": "http_link"}]})
    baseline = fixture_response(bundle)
    cases = []

    def record(case_id, description, expected, response, request=None):
        try:
            ai.validate_response(response, request or bundle)
            observed = "accepted"
        except ai.ExplanationError:
            observed = "rejected"
        cases.append({
            "id": case_id, "description": description, "expected": expected,
            "observed": observed, "contract_check_passed": observed == expected,
        })

    record("valid_structure", "Respuesta completa con referencias válidas.", "accepted", baseline)
    reverse = copy.deepcopy(baseline)
    reverse["explanations"].reverse()
    record("valid_reordered", "Referencias válidas recibidas en otro orden.", "accepted", reverse)

    edits = [
        ("wrong_request", "Respuesta vinculada a otra solicitud.", lambda r: r.update(request_id="0" * 64)),
        ("extra_root_field", "Campo adicional fuera del contrato.", lambda r: r.update(extra="ficticio")),
        ("missing_root_field", "Campo obligatorio ausente.", lambda r: r.pop("review_required")),
        ("review_disabled", "Se intenta eliminar la revisión humana.", lambda r: r.update(review_required=False)),
        ("review_not_boolean", "Revisión humana con tipo numérico.", lambda r: r.update(review_required=1)),
        ("missing_finding", "Falta una explicación requerida.", lambda r: r["explanations"].pop()),
        ("unknown_finding", "Referencia a un identificador inexistente.", lambda r: r["explanations"][0].update(finding_id="F999")),
        ("duplicate_finding", "Identificador repetido en lugar de cubrir otro hallazgo.", lambda r: r["explanations"].__setitem__(1, copy.deepcopy(r["explanations"][0]))),
        ("wrong_rule", "Regla que no corresponde al identificador.", lambda r: r["explanations"][0].update(rule="ip_link")),
        ("extra_item_field", "Campo adicional dentro de una explicación.", lambda r: r["explanations"][0].update(extra="ficticio")),
        ("short_explanation", "Explicación por debajo de la longitud mínima.", lambda r: r["explanations"][0].update(explanation="Breve")),
        ("long_explanation", "Explicación que excede la longitud máxima.", lambda r: r["explanations"][0].update(explanation="x" * 701)),
        ("wrong_text_type", "Explicación con tipo no textual.", lambda r: r["explanations"][0].update(explanation=42)),
        ("missing_manual_checks", "Lista de comprobaciones manuales vacía.", lambda r: r["explanations"][0].update(manual_checks=[])),
        ("too_many_manual_checks", "Cantidad excesiva de comprobaciones.", lambda r: r["explanations"][0].update(manual_checks=["Revisar."] * 4)),
        ("control_character", "Carácter de control en la explicación.", lambda r: r["explanations"][0].update(explanation="Revisar el contexto\x1b del hallazgo.")),
        ("hidden_format", "Carácter de formato oculto en la explicación.", lambda r: r["explanations"][0].update(explanation="Revisar el contexto\u202e del hallazgo.")),
        ("new_url", "URL añadida en la prosa de respuesta.", lambda r: r["explanations"][0].update(explanation="Comprobar la dirección ficticia https://ficticio.test/")),
        ("new_email", "Dirección de correo añadida en una comprobación.", lambda r: r["explanations"][0].update(manual_checks=["Consultar a persona@example.test"])),
        ("new_ip", "Dirección IP añadida en la prosa de respuesta.", lambda r: r["explanations"][0].update(explanation="Comprobar el destino ficticio 192.0.2.10 antes de seguir.")),
    ]
    for case_id, description, edit in edits:
        response = copy.deepcopy(baseline)
        edit(response)
        record(case_id, description, "rejected", response)

    empty_bundle = ai.build_ai_request({"findings": []})
    record("empty_valid", "Sin hallazgos y sin explicaciones.", "accepted", fixture_response(empty_bundle), empty_bundle)
    extra = fixture_response(empty_bundle)
    extra["explanations"] = [copy.deepcopy(baseline["explanations"][0])]
    record("empty_invented", "Sin hallazgos pero con una explicación añadida.", "rejected", extra, empty_bundle)

    marker = "DATO_SINTETICO_OMITIDO_DEL_BUNDLE"
    report = {
        "findings": [{"rule": "urgent_subject", "title": marker, "evidence": marker}],
        "headers": {"subject": marker, "from": marker}, "body": marker,
        "urls": [marker], "sha256": marker,
    }
    minimized = ai.build_ai_request(report)
    cases.append({
        "id": "minimization", "description": "Metadatos y texto de origen no pasan al bundle.",
        "expected": "omitted", "observed": "omitted" if marker not in json.dumps(minimized) else "present",
        "contract_check_passed": marker not in json.dumps(minimized),
    })
    try:
        ai.build_ai_request({"findings": [{"rule": "unknown_rule"}]})
        unknown_observed = "accepted"
    except ai.ExplanationError:
        unknown_observed = "rejected"
    cases.append({
        "id": "unknown_source_rule", "description": "El bundle rechaza reglas ajenas al catálogo.",
        "expected": "rejected", "observed": unknown_observed,
        "contract_check_passed": unknown_observed == "rejected",
    })
    with tempfile.TemporaryDirectory() as directory:
        response_file = Path(directory) / "synthetic_response.json"
        response_file.write_text('{"review_required":true,"review_required":false}', encoding="utf-8")
        try:
            ai.load_response(response_file)
            duplicate_observed = "accepted"
        except ai.ExplanationError:
            duplicate_observed = "rejected"
    cases.append({
        "id": "duplicate_json_keys", "description": "El importador rechaza claves JSON repetidas.",
        "expected": "rejected", "observed": duplicate_observed,
        "contract_check_passed": duplicate_observed == "rejected",
    })

    semantic_fixture = copy.deepcopy(baseline)
    semantic_fixture["explanations"][0]["explanation"] = "La verificación DKIM falló"
    try:
        ai.validate_response(semantic_fixture, bundle)
        semantic_observed = "accepted"
    except ai.ExplanationError:
        semantic_observed = "rejected"
    passed = sum(case["contract_check_passed"] for case in cases)
    return {
        "metadata": {
            "date": "2026-10-25", "evaluation": "Contrato local con fixtures sintéticas",
            "response_source": "Respuestas sintéticas construidas a mano; no son salidas de un modelo",
            "real_model_inference": False, "live_api_tested": False, "semantic_truth_verified": False,
            "request_id_source": "SHA-256 de hechos minimizados del contrato; no es un hash de correo",
        },
        "request_id": bundle["request_id"],
        "contract_checks": {"total": len(cases), "passed": passed, "failed": len(cases) - passed, "cases": cases},
        "semantic_limit_control": {
            "id": "unsupported_authentication_claim",
            "description": "Una afirmación falsa sobre autenticación conserva IDs y formato válidos.",
            "expected_observed_behavior": "accepted", "observed": semantic_observed,
            "known_semantic_falsehood_accepted": semantic_observed == "accepted",
            "implementation_error": False,
            "interpretation": "Demuestra que aceptar el contrato no acredita verdad semántica. Requiere revisión humana.",
        },
        "scope": "Comprueba casos del contrato y documenta una limitación. No mide detección de phishing, exactitud de un modelo ni resistencia universal a inyecciones o alucinaciones.",
    }


def markdown_report(result):
    checks = result["contract_checks"]
    lines = [
        "# Evaluación offline del contrato IA", "", "Fecha: 2026-10-25.", "",
        "Las respuestas son fixtures sintéticas escritas a mano. No hubo inferencia real ni llamadas a una API.", "",
        f"Comprobaciones de contrato: **{checks['passed']}/{checks['total']}** cumplen el comportamiento esperado; **{checks['failed']}** fallan.", "",
        "Este resultado cubre sólo estos casos. No es una medida de detección de phishing ni un benchmark de un modelo.", "",
        "## Casos de contrato", "", "| Caso | Descripción | Esperado | Observado |", "|---|---|---|---|",
    ]
    for case in checks["cases"]:
        lines.append(f"| `{case['id']}` | {case['description']} | {case['expected']} | {case['observed']} |")
    lines.extend([
        "", "## Control separado del límite semántico", "",
        "Una respuesta afirma falsamente que una comprobación de autenticación falló, aunque sólo se proporcionaron observaciones de reglas y no se verificó autenticación.", "",
        f"Resultado del validador: **{result['semantic_limit_control']['observed']}**. La respuesta conserva el contrato y las referencias. Este caso documenta una falsedad no detectada; no se cuenta como un fallo de implementación ni como una explicación correcta.", "",
        "El validador comprueba estructura, cobertura y referencias. No demuestra que cada frase esté sustentada, ni elimina las alucinaciones. La revisión humana sigue siendo necesaria.", "",
        "## Trazabilidad y límites", "",
        f"Identificador de la solicitud sintética: `{result['request_id']}`. Se deriva de hechos minimizados del contrato, no de bytes ni metadatos de un correo.", "",
        "`live_api_tested=false`; `semantic_truth_verified=false`. No se exportan cuerpos, cabeceras, evidencias ni hashes de correos. Los indicadores nuevos se prueban en formatos expresamente cubiertos; sus ofuscaciones posibles no están cubiertas de forma universal.", "",
        "Reproducir desde la raíz del proyecto: `python evals/offline_suite.py`.", "",
    ])
    return "\n".join(lines)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    result = run_suite()
    directory = ROOT / "docs"
    directory.mkdir(exist_ok=True)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (directory / "EVALUACION.json").write_text(serialized, encoding="utf-8")
    (directory / "EVALUACION.md").write_text(markdown_report(result), encoding="utf-8")
    print(serialized, end="")
    return 0 if result["contract_checks"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
