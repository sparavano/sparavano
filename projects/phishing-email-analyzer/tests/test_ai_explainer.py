"""Contrato IA con fixtures locales; no mide la calidad de un modelo real."""

import copy
import hashlib
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import ai_explainer as ai
import phishing_analyzer as analyzer

ROOT = Path(__file__).resolve().parents[1]


def sample_report():
    return {"findings": [{"rule": "urgent_subject"}, {"rule": "http_link"}]}


def valid_response(bundle):
    return {
        "request_id": bundle["request_id"],
        "review_required": True,
        "explanations": [
            {
                "finding_id": item["finding_id"],
                "rule": item["rule"],
                "explanation": "Esta observación necesita revisión humana antes de sacar conclusiones.",
                "manual_checks": ["Revisar el contexto del hallazgo."],
            }
            for item in bundle["findings"]
        ],
    }


class RequestTests(unittest.TestCase):
    def test_bundle_uses_only_ids_and_fixed_catalogue(self):
        marker = "DATO_FICTICIO_QUE_NO_DEBE_SALIR"
        report = {
            "file": marker,
            "sha256": marker,
            "headers": {"from": marker, "subject": marker},
            "body": marker,
            "urls": [marker],
            "attachments": [{"filename": marker}],
            "findings": [{"rule": "urgent_subject", "title": marker, "evidence": marker}],
        }
        bundle = ai.build_ai_request(report)
        self.assertNotIn(marker, json.dumps(bundle))
        self.assertEqual(set(bundle), {"request_id", "findings", "instructions", "response_schema"})
        self.assertEqual(bundle["findings"], [{
            "finding_id": "F001", "rule": "urgent_subject",
            "observation": ai.RULE_CATALOG["urgent_subject"],
        }])

    def test_request_id_depends_on_safe_facts_not_mail_content(self):
        first = sample_report()
        second = copy.deepcopy(first)
        first.update({"sha256": "a" * 64, "headers": {"subject": "ficticio uno"}})
        second.update({"sha256": "b" * 64, "headers": {"subject": "ficticio dos"}})
        first["findings"][0]["evidence"] = "CONTENIDO_FICTICIO_UNO"
        second["findings"][0]["evidence"] = "CONTENIDO_FICTICIO_DOS"
        bundle = ai.build_ai_request(first)
        self.assertEqual(bundle, ai.build_ai_request(second))
        canonical = json.dumps(
            {"contract_version": "0.2", "findings": bundle["findings"]},
            ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(bundle["request_id"], hashlib.sha256(canonical).hexdigest())
        self.assertNotIn(bundle["request_id"], {first["sha256"], second["sha256"]})

    def test_unknown_rules_and_invalid_findings_are_rejected(self):
        for findings in ([{"rule": "invented_rule"}], ["urgent_subject"], [{"rule": []}], None):
            with self.subTest(findings=findings), self.assertRaises(ai.ExplanationError):
                ai.build_ai_request({"findings": findings})

    def test_finding_limit_and_duplicate_known_rules(self):
        report = {"findings": [{"rule": "http_link"}] * ai.MAX_FINDINGS}
        bundle = ai.build_ai_request(report)
        self.assertEqual(bundle["findings"][-1]["finding_id"], f"F{ai.MAX_FINDINGS:03d}")
        report["findings"].append({"rule": "http_link"})
        with self.assertRaises(ai.ExplanationError):
            ai.build_ai_request(report)

    def test_saved_request_does_not_overwrite_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "correo.eml"
            source.write_bytes(b"contenido ficticio")
            with self.assertRaises(ai.ExplanationError):
                ai.save_request(ai.build_ai_request(sample_report()), source, source)
            self.assertEqual(source.read_bytes(), b"contenido ficticio")


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.bundle = ai.build_ai_request(sample_report())
        self.response = valid_response(self.bundle)

    def assert_rejected(self, response):
        with self.assertRaises(ai.ExplanationError):
            ai.validate_response(response, self.bundle)

    def test_valid_response_preserves_finding_order_and_review(self):
        self.response["explanations"].reverse()
        validated = ai.validate_response(self.response, self.bundle)
        self.assertEqual([item["finding_id"] for item in validated["explanations"]], ["F001", "F002"])
        self.assertIs(validated["review_required"], True)
        self.assertIn("no está verificada", validated["validation_scope"])

    def test_stale_or_wrong_request_id_is_rejected(self):
        for value in ("0" * 64, None, [], 1):
            with self.subTest(value=value):
                response = copy.deepcopy(self.response)
                response["request_id"] = value
                self.assert_rejected(response)

    def test_missing_duplicate_unknown_ids_and_wrong_rule_are_rejected(self):
        variants = []
        missing = copy.deepcopy(self.response)
        missing["explanations"].pop()
        variants.append(missing)
        duplicate = copy.deepcopy(self.response)
        duplicate["explanations"][1] = copy.deepcopy(duplicate["explanations"][0])
        variants.append(duplicate)
        for value in ("F999", [], 1):
            unknown = copy.deepcopy(self.response)
            unknown["explanations"][0]["finding_id"] = value
            variants.append(unknown)
        wrong_rule = copy.deepcopy(self.response)
        wrong_rule["explanations"][0]["rule"] = "ip_link"
        variants.append(wrong_rule)
        for index, response in enumerate(variants):
            with self.subTest(index=index):
                self.assert_rejected(response)

    def test_extra_and_missing_fields_are_rejected_at_both_levels(self):
        for level in ("root", "item"):
            for change in ("extra", "missing"):
                with self.subTest(level=level, change=change):
                    response = copy.deepcopy(self.response)
                    target = response if level == "root" else response["explanations"][0]
                    if change == "extra":
                        target["unexpected"] = "valor ficticio"
                    else:
                        target.pop("request_id" if level == "root" else "rule")
                    self.assert_rejected(response)

    def test_review_required_must_be_boolean_true(self):
        for value in (False, 1, "true", None):
            with self.subTest(value=value):
                response = copy.deepcopy(self.response)
                response["review_required"] = value
                self.assert_rejected(response)

    def test_wrong_container_types_are_rejected(self):
        self.assert_rejected([])
        for value in (None, {}, "texto"):
            with self.subTest(value=value):
                response = copy.deepcopy(self.response)
                response["explanations"] = value
                self.assert_rejected(response)

    def test_explanation_length_and_type_boundaries(self):
        for value in ("x" * 15, "x" * 700):
            response = copy.deepcopy(self.response)
            response["explanations"][0]["explanation"] = value
            ai.validate_response(response, self.bundle)
        for value in ("x" * 14, "x" * 701, " " * 20, None, 42):
            with self.subTest(value_type=type(value).__name__, length=len(value) if isinstance(value, str) else None):
                response = copy.deepcopy(self.response)
                response["explanations"][0]["explanation"] = value
                self.assert_rejected(response)

    def test_manual_check_count_length_and_types(self):
        for value in ([], ["Revisar."] * 4, "Revisar", [None], [""], ["x" * 301]):
            with self.subTest(value=value):
                response = copy.deepcopy(self.response)
                response["explanations"][0]["manual_checks"] = value
                self.assert_rejected(response)
        response = copy.deepcopy(self.response)
        response["explanations"][0]["manual_checks"] = ["x" * 300] * 3
        ai.validate_response(response, self.bundle)

    def test_control_and_hidden_format_characters_are_rejected(self):
        for character in ("\x1b", "\n", "\r", "\x00", "\u202e", "\u200b"):
            for field in ("explanation", "manual_checks"):
                with self.subTest(character=repr(character), field=field):
                    response = copy.deepcopy(self.response)
                    text = "Revisar el contexto" + character + "del hallazgo."
                    response["explanations"][0][field] = text if field == "explanation" else [text]
                    self.assert_rejected(response)

    def test_recognized_new_indicators_are_rejected_in_both_text_fields(self):
        indicators = (
            "https://ficticio.test/", "hxxps://ficticio[.]test/", "www.ficticio.test",
            "persona@example.test", "192.0.2.10", "[2001:db8::1]", "ficticio[.]example",
        )
        for indicator in indicators:
            for field in ("explanation", "manual_checks"):
                with self.subTest(indicator=indicator, field=field):
                    response = copy.deepcopy(self.response)
                    text = "Comprobar este indicador ficticio: " + indicator
                    response["explanations"][0][field] = text if field == "explanation" else [text]
                    self.assert_rejected(response)

    def test_zero_findings_accepts_only_an_empty_explanation_list(self):
        bundle = ai.build_ai_request({"findings": []})
        self.assertEqual(ai.validate_response(valid_response(bundle), bundle)["explanations"], [])
        response = valid_response(bundle)
        response["explanations"] = [copy.deepcopy(self.response["explanations"][0])]
        with self.assertRaises(ai.ExplanationError):
            ai.validate_response(response, bundle)

    def test_known_semantic_falsehood_can_pass_structural_validation(self):
        # Control de limitación: no confundir aceptación de contrato con verdad.
        self.response["explanations"][0]["explanation"] = "La verificación DKIM falló"
        validated = ai.validate_response(self.response, self.bundle)
        self.assertEqual(validated["explanations"][0]["explanation"], "La verificación DKIM falló")
        self.assertIn("veracidad semántica", validated["validation_scope"])


class ResponseFileTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected_at_root_and_nested_levels(self):
        documents = ('{"request_id":"uno","request_id":"dos"}', '{"item":{"rule":"uno","rule":"dos"}}')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "respuesta.json"
            for document in documents:
                with self.subTest(document=document):
                    path.write_text(document, encoding="utf-8")
                    with self.assertRaises(ai.ExplanationError):
                        ai.load_response(path)

    def test_bom_valid_json_and_malformed_or_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "respuesta.json"
            path.write_text('{"review_required":true}', encoding="utf-8-sig")
            self.assertEqual(ai.load_response(path), {"review_required": True})
            for data in (b"not json", b"\xff", b"```json\n{}\n```"):
                path.write_bytes(data)
                with self.assertRaises(ai.ExplanationError):
                    ai.load_response(path)
            path.write_bytes(b" " * 17)
            with patch.object(ai, "MAX_JSON_BYTES", 16), self.assertRaises(ai.ExplanationError):
                ai.load_response(path)


class CommandTests(unittest.TestCase):
    def call_main(self, args):
        output = io.StringIO()
        error = io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            result = analyzer.main(args)
        return result, output.getvalue(), error.getvalue()

    def test_zero_findings_does_not_call_provider(self):
        provider = types.ModuleType("openai_provider")
        provider.request_explanation = Mock(side_effect=AssertionError("No debe consultar un modelo"))
        with patch.dict(sys.modules, {"openai_provider": provider}):
            code, output, error = self.call_main([str(ROOT / "examples" / "normal.eml"), "--ai-openai", "--json"])
        self.assertEqual(code, 0, error)
        provider.request_explanation.assert_not_called()
        report = json.loads(output)
        self.assertEqual(report["ai_explanation"]["explanations"], [])
        self.assertIn("omitido", report["ai_explanation"]["mode"])

    def test_default_and_export_modes_do_not_call_provider(self):
        provider = types.ModuleType("openai_provider")
        provider.request_explanation = Mock(side_effect=AssertionError("Modo offline"))
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"openai_provider": provider}):
            path = Path(directory) / "solicitud.json"
            code, output, error = self.call_main([str(ROOT / "examples" / "sospechoso.eml"), "--export-ai-request", str(path), "--json"])
            self.assertEqual(code, 0, error)
            self.assertTrue(path.exists())
            self.assertNotIn("headers", json.loads(path.read_text(encoding="utf-8")))
            code, output, error = self.call_main([str(ROOT / "examples" / "sospechoso.eml"), "--json"])
            self.assertEqual(code, 0, error)
            self.assertNotIn("ai_explanation", json.loads(output))
        provider.request_explanation.assert_not_called()

    def test_manual_response_mode_is_offline(self):
        report = analyzer.analyze_file(ROOT / "examples" / "sospechoso.eml")
        bundle = ai.build_ai_request(report)
        provider = types.ModuleType("openai_provider")
        provider.request_explanation = Mock(side_effect=AssertionError("Importación offline"))
        with tempfile.TemporaryDirectory() as directory, patch.dict(sys.modules, {"openai_provider": provider}):
            path = Path(directory) / "respuesta.json"
            path.write_text(json.dumps(valid_response(bundle)), encoding="utf-8")
            code, output, error = self.call_main([str(ROOT / "examples" / "sospechoso.eml"), "--ai-response", str(path), "--json"])
        self.assertEqual(code, 0, error)
        provider.request_explanation.assert_not_called()
        self.assertIn("sin nueva inferencia", json.loads(output)["ai_explanation"]["mode"])

    def test_ai_cli_modes_are_mutually_exclusive(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                analyzer.main([str(ROOT / "examples" / "normal.eml"), "--ai-openai", "--ai-response", "respuesta.json"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
