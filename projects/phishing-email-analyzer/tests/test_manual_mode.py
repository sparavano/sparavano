import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import manual_mode
from ai_explainer import ExplanationError

ROOT = Path(__file__).resolve().parents[1]
EMAIL = ROOT / "examples" / "revision_enlace.eml"
RESPONSE = ROOT / "examples" / "respuesta_manual.json"


class ManualModeTests(unittest.TestCase):
    def test_prepare_exports_only_safe_data_and_never_calls_api(self):
        with tempfile.TemporaryDirectory() as temp, patch("openai_provider.request_explanation", side_effect=AssertionError("No API")) as provider:
            request, prompt = manual_mode.prepare(EMAIL, Path(temp))
            request_text = request.read_text(encoding="utf-8")
            prompt_text = prompt.read_text(encoding="utf-8")
            self.assertEqual(json.loads(request_text)["findings"][0]["rule"], "userinfo_link")
            for raw in ("universidad.example", "material.test", "biblioteca@", "Material del laboratorio"):
                self.assertNotIn(raw, request_text)
                self.assertNotIn(raw, prompt_text)
            provider.assert_not_called()

    def test_validate_creates_traceable_reports_offline(self):
        with tempfile.TemporaryDirectory() as temp, patch("openai_provider.request_explanation", side_effect=AssertionError("No API")) as provider:
            report, json_path, text_path = manual_mode.validate(EMAIL, RESPONSE, Path(temp))
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["ai_explanation"]["explanations"][0]["finding_id"], "F001")
            self.assertEqual(saved["findings"][0]["finding_id"], "F001")
            self.assertIn("intercambio manual", text_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ai_explanation"]["review_required"])
            provider.assert_not_called()

    def test_invalid_response_never_creates_success_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            bad = json.loads(RESPONSE.read_text(encoding="utf-8"))
            bad["explanations"][0]["finding_id"] = "F999"
            response = folder / "bad.json"
            response.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ExplanationError):
                manual_mode.validate(EMAIL, response, folder)
            self.assertFalse((folder / "informe_manual.json").exists())
            self.assertFalse((folder / "informe_manual.txt").exists())

    def test_prepare_does_not_overwrite_input(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "LEEME_IA.txt"
            original = EMAIL.read_bytes()
            source.write_bytes(original)
            with self.assertRaises(ValueError):
                manual_mode.prepare(source, folder)
            self.assertEqual(source.read_bytes(), original)

    def test_validate_does_not_overwrite_input_response(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            response = folder / "informe_manual.json"
            original = RESPONSE.read_bytes()
            response.write_bytes(original)
            with self.assertRaises(ValueError):
                manual_mode.validate(EMAIL, response, folder)
            self.assertEqual(response.read_bytes(), original)

    def test_prepare_does_not_overwrite_input_through_hardlink(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            source = folder / "correo.eml"
            original = EMAIL.read_bytes()
            source.write_bytes(original)
            os.link(source, folder / "solicitud_ia.json")
            with self.assertRaises(ValueError):
                manual_mode.prepare(source, folder)
            self.assertEqual(source.read_bytes(), original)

    def test_saved_demo_preserves_previous_review_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            previous = folder / "informe_manual.txt"
            previous.write_text("Revisión anterior", encoding="utf-8")
            with patch.object(manual_mode, "REPORTS", folder), patch("builtins.print"):
                self.assertEqual(manual_mode.main(["--demo"]), 0)
            self.assertEqual(previous.read_text(encoding="utf-8"), "Revisión anterior")
            self.assertTrue((folder / "demo" / "informe_manual.txt").exists())

    def test_interactive_quit_never_calls_api(self):
        with patch("builtins.input", return_value="0"), patch("builtins.print"), patch("openai_provider.request_explanation") as provider:
            self.assertEqual(manual_mode.interactive(), 0)
            provider.assert_not_called()

    def test_cli_rejects_conflicting_actions(self):
        result = subprocess.run([sys.executable, str(ROOT / "manual_mode.py"), "--prepare", str(EMAIL), "--demo"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
