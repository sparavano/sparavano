"""Reproduce un caso benigno sintético con una única variación de asunto."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai_explainer import build_ai_request, load_response, validate_response
from phishing_analyzer import analyze_file


def run_case():
    urgent_path = ROOT / "examples" / "aviso_legitimo_urgente.eml"
    control_path = ROOT / "examples" / "aviso_legitimo_sin_urgencia.eml"
    urgent_bytes = urgent_path.read_bytes()
    control_bytes = control_path.read_bytes()
    old = b"Subject: URGENTE:"
    new = b"Subject: Aviso:"
    only_subject_change = urgent_bytes.count(old) == 1 and urgent_bytes.replace(old, new, 1) == control_bytes
    urgent = analyze_file(urgent_path)
    control = analyze_file(control_path)
    bundle = build_ai_request(urgent)
    stored_bundle = json.loads((ROOT / "examples" / "solicitud_urgencia.json").read_text(encoding="utf-8"))
    explanation = validate_response(load_response(ROOT / "examples" / "respuesta_urgencia.json"), bundle)
    checks = {
        "only_subject_prefix_changed": only_subject_change,
        "urgent_has_one_expected_finding": [f["rule"] for f in urgent["findings"]] == ["urgent_subject"],
        "control_has_zero_findings": len(control["findings"]) == 0,
        "stored_request_matches_current_bundle": stored_bundle == bundle,
        "saved_response_has_expected_reference": [e["finding_id"] for e in explanation["explanations"]] == ["F001"],
    }
    return {
        "case": "Señal de urgencia en un caso benigno sintético",
        "fixture_design_date": "2026-10-25",
        "scenario_label": "Aviso autorizado de cambio de aula, definido por construcción del ejercicio; no es una verificación de autenticidad de un correo real.",
        "response_source": "Nueva respuesta generada por un agente de esta sesión sin historial heredado. Recibió sólo el paquete minimizado y las instrucciones de formato; no recibió el correo ni la etiqueta benigna y no usó herramientas. La reproducción importa ese JSON guardado.",
        "application_called_provider_api": False,
        "semantic_truth_automatically_verified": False,
        "human_review_required": True,
        "request_id": bundle["request_id"],
        "cases": [
            {"path": "examples/aviso_legitimo_urgente.eml", "expected_rules": ["urgent_subject"], "observed_rules": [f["rule"] for f in urgent["findings"]], "sha256": urgent["sha256"]},
            {"path": "examples/aviso_legitimo_sin_urgencia.eml", "expected_rules": [], "observed_rules": [f["rule"] for f in control["findings"]], "sha256": control["sha256"]},
        ],
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "scope": "Una comparación controlada. No mide tasa de falsos positivos, autenticidad ni precisión del modelo. El analizador emite señales, no un veredicto de phishing.",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    result = run_case()
    destination = ROOT / "docs" / "CASO_URGENCIA_RESULTADOS.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
