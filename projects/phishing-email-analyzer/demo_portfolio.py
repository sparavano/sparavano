"""Reproduce cinco casos ficticios y los controles locales, sin consultar una API."""
import argparse
import copy
import json
from pathlib import Path
import sys

from ai_explainer import ExplanationError, build_ai_request, load_response, validate_response
from evals.offline_suite import run_suite
from evals.urgency_context import run_case
from phishing_analyzer import analyze_file

ROOT = Path(__file__).resolve().parent
CASES = (
    ("normal", "Correo normal de control", "normal.eml", [], None),
    ("userinfo", "Enlace con información antes de @", "revision_enlace.eml", ["userinfo_link"], "respuesta_manual.json"),
    ("multiple", "Correo con varias señales preparadas", "sospechoso.eml", ["reply_to_domain", "urgent_subject", "link_label_mismatch", "executable_attachment", "http_link", "ip_link", "http_link"], "ai_response_demo.json"),
    ("benign_urgent", "Aviso benigno sintético con urgencia", "aviso_legitimo_urgente.eml", ["urgent_subject"], "respuesta_urgencia.json"),
    ("benign_control", "Mismo aviso sin la palabra de urgencia", "aviso_legitimo_sin_urgencia.eml", [], None),
)


def build_results():
    cases = []
    for case_id, title, filename, expected, response_file in CASES:
        report = analyze_file(ROOT / "examples" / filename)
        rules = [finding["rule"] for finding in report["findings"]]
        saved_response = None
        if response_file:
            validate_response(load_response(ROOT / "examples" / response_file), build_ai_request(report))
            saved_response = {"path": "examples/" + response_file, "contract_validation": "accepted"}
        cases.append({
            "id": case_id, "title": title, "path": "examples/" + filename,
            "sha256": report["sha256"], "expected_rules": expected, "observed_rules": rules,
            "finding_count": len(rules), "matches_expected_rules": rules == expected,
            "saved_ai_response": saved_response,
        })
    reference_bundle = build_ai_request(analyze_file(ROOT / "examples" / "revision_enlace.eml"))
    invalid = copy.deepcopy(load_response(ROOT / "examples" / "respuesta_manual.json"))
    invalid["explanations"][0]["finding_id"] = "F999"
    try:
        validate_response(invalid, reference_bundle)
        invalid_reference_rejected = False
    except ExplanationError:
        invalid_reference_rejected = True
    urgency = run_case()
    contract = run_suite()
    checks = {
        "five_cases_match_expected_rules": all(case["matches_expected_rules"] for case in cases),
        "nonexistent_reference_rejected": invalid_reference_rejected,
        "urgency_comparison_checks_passed": urgency["all_checks_passed"],
        "synthetic_contract_cases_passed": contract["contract_checks"]["failed"] == 0,
    }
    return {
        "demo": "Recorrido reproducible del laboratorio educativo",
        "all_samples_are_synthetic": True,
        "application_called_provider_api": False,
        "new_inference_during_demo": False,
        "saved_response_provenance": "Las respuestas se generaron durante el desarrollo o intercambios manuales anteriores. Esta ejecución sólo importa los JSON. Consultar docs/PROVENIENCIA_IA.md, docs/PRUEBA_MANUAL_IA.md y docs/CASO_URGENCIA_BENIGNA.md.",
        "cases": cases,
        "checks": checks,
        "all_expected_checks_passed": all(checks.values()),
        "contract_evaluation": {key: contract["contract_checks"][key] for key in ("total", "passed", "failed")},
        "semantic_limit_control": contract["semantic_limit_control"],
        "semantic_truth_automatically_verified": False,
        "human_review_required": True,
        "scope": "Reproducción de fixtures y controles locales. No mide precisión de detección, tasa de falsos positivos ni calidad general de un modelo. Las señales no son veredictos; cero hallazgos no garantiza seguridad.",
    }


def summary_markdown(result):
    lines = ["# Resultado del recorrido", "", "Cinco correos ficticios. Ejecución sin API y sin una nueva inferencia de IA.", "", "| Caso | Hallazgos | Coincide con las reglas esperadas |", "|---|---:|---|"]
    for case in result["cases"]:
        lines.append(f"| {case['title']} | {case['finding_count']} | {'Sí' if case['matches_expected_rules'] else 'No'} |")
    lines.extend(["", "## Controles locales", ""])
    labels = {
        "five_cases_match_expected_rules": "Los cinco casos producen las reglas previstas",
        "nonexistent_reference_rejected": "Se rechaza la referencia inexistente F999",
        "urgency_comparison_checks_passed": "La comparación de urgencia cumple sus cinco comprobaciones",
        "synthetic_contract_cases_passed": "La evaluación sintética de contrato cumple el comportamiento esperado",
    }
    for key, description in labels.items():
        lines.append(f"- {description}: {'cumplido' if result['checks'][key] else 'falló'}.")
    contract = result["contract_evaluation"]
    lines.extend(["", f"Casos de contrato: {contract['passed']}/{contract['total']}. Esta cifra describe esos fixtures; no es una tasa de precisión.", "", "## Límite semántico observado", ""])
    if result["semantic_limit_control"]["known_semantic_falsehood_accepted"]:
        lines.append("El control separado confirma que una afirmación falsa puede conservar IDs y formato y ser aceptada. Es una limitación del validador y requiere revisión humana; no se cuenta como una explicación correcta.")
    else:
        lines.append("La afirmación falsa del control separado fue rechazada. Ese único caso no demuestra veracidad general del texto.")
    lines.extend(["", result["scope"], "", "Los JSON de explicación son respuestas guardadas. Su procedencia está documentada en el proyecto. Para solicitar otra explicación, usá el intercambio manual con modo_manual.cmd.", ""])
    return "\n".join(lines)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-public-snapshot", action="store_true", help="Actualizar docs/RESULTADOS_RECORRIDO.json con estos fixtures ficticios")
    args = parser.parse_args(argv)
    try:
        result = build_results()
        serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        summary = summary_markdown(result)
        folder = ROOT / "reports" / "demo_portfolio"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "resultados.json").write_text(serialized, encoding="utf-8")
        (folder / "RESUMEN.md").write_text(summary, encoding="utf-8")
        if args.write_public_snapshot:
            (ROOT / "docs" / "RESULTADOS_RECORRIDO.json").write_text(serialized, encoding="utf-8")
        print(summary)
        print("Resumen local: " + str(folder / "RESUMEN.md"))
        return 0 if result["all_expected_checks_passed"] else 1
    except (OSError, ValueError, RecursionError) as error:
        print("No se completó el recorrido: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
