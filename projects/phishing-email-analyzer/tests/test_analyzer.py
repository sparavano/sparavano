"""Pruebas de comportamiento con mensajes sintéticos; no requieren red."""

import hashlib
import json
import subprocess
import sys
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch

import phishing_analyzer as analyzer

ROOT = Path(__file__).resolve().parents[1]


def message_bytes(body="Mensaje de prueba.", **headers):
    message = EmailMessage()
    message["From"] = "Docente <docente@universidad.example>"
    message["Subject"] = "Material de clase"
    for name, value in headers.items():
        if name in message:
            message.replace_header(name, value)
        else:
            message[name] = value
    message.set_content(body)
    return message.as_bytes()


def rules(report):
    return {finding["rule"] for finding in report["findings"]}


class AnalyzerTests(unittest.TestCase):
    def test_normal_example_has_no_findings_and_exact_hash(self):
        path = ROOT / "examples" / "normal.eml"
        report = analyzer.analyze_file(path)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_suspicious_fixture_has_explained_findings(self):
        report = analyzer.analyze_file(ROOT / "examples" / "sospechoso.eml")
        self.assertEqual(rules(report), {"reply_to_domain", "urgent_subject", "link_label_mismatch", "http_link", "ip_link", "executable_attachment"})
        self.assertEqual(len(report["attachments"]), 1)

    def test_reply_domain_comparison_is_case_insensitive(self):
        report = analyzer.analyze_bytes(message_bytes(**{"Reply-To": "ayuda@UNIVERSIDAD.EXAMPLE"}))
        self.assertNotIn("reply_to_domain", rules(report))

    def test_different_reply_domain_only_records_a_signal(self):
        report = analyzer.analyze_bytes(message_bytes(**{"Reply-To": "ayuda@otro.test"}))
        self.assertEqual(rules(report), {"reply_to_domain"})
        self.assertNotIn("verdict", report)

    def test_html_mismatch_and_equivalent_host_with_port(self):
        message = EmailMessage()
        message["From"] = "docente@universidad.example"
        message.set_content('<a href="https://otro.test/">https://universidad.example</a><a href="https://UNIVERSIDAD.example:443/">https://universidad.example</a>', subtype="html")
        report = analyzer.analyze_bytes(message.as_bytes())
        self.assertEqual(sum(f["rule"] == "link_label_mismatch" for f in report["findings"]), 1)

    def test_ipv4_ipv6_http_and_userinfo_are_detected(self):
        report = analyzer.analyze_bytes(message_bytes("http://192.0.2.1/a https://[2001:db8::1]/b https://universidad.example@otro.test/"))
        self.assertEqual(rules(report), {"ip_link", "http_link", "userinfo_link"})
        self.assertEqual(sum(f["rule"] == "ip_link" for f in report["findings"]), 2)

    def test_mime_base64_and_encoded_attachment_filename(self):
        message = EmailMessage()
        message["From"] = "docente@universidad.example"
        message.set_content("http://cuenta.test/revision", cte="base64")
        message.add_attachment(b"http://ignorar.test/", maintype="application", subtype="octet-stream", filename="facturación.PDF.EXE")
        report = analyzer.analyze_bytes(message.as_bytes())
        self.assertEqual(rules(report), {"http_link", "executable_attachment"})
        self.assertEqual(len(report["urls"]), 1)

    def test_safe_pdf_attachment_is_not_executable(self):
        message = EmailMessage()
        message["From"] = "docente@universidad.example"
        message.set_content("Texto de prueba.")
        message.add_attachment(b"contenido ficticio", maintype="application", subtype="pdf", filename="lectura.pdf")
        self.assertEqual(analyzer.analyze_bytes(message.as_bytes())["findings"], [])

    def test_attached_email_body_is_not_inspected(self):
        nested = EmailMessage()
        nested["From"] = "prueba@example.test"
        nested.set_content("http://192.0.2.1/adjunto")
        outer = EmailMessage()
        outer["From"] = "docente@universidad.example"
        outer.set_content("Consultar con el laboratorio.")
        outer.add_attachment(nested, filename="adjunto.eml")
        report = analyzer.analyze_bytes(outer.as_bytes())
        self.assertEqual(report["urls"], [])
        self.assertEqual(len(report["attachments"]), 1)

    def test_content_type_cannot_inject_terminal_controls(self):
        data = b'From: a@example.test\nContent-Type: application/\x1b[31m\nContent-Disposition: attachment; filename="prueba.txt"\n\ntexto'
        report = analyzer.analyze_bytes(data)
        self.assertNotIn("\x1b", analyzer.format_report(report))

    def test_html_label_is_not_counted_as_actual_destination(self):
        message = EmailMessage()
        message["From"] = "docente@universidad.example"
        message.set_content('<a href="https://otro.test/">http://192.0.2.1/</a>', subtype="html")
        report = analyzer.analyze_bytes(message.as_bytes())
        self.assertEqual(report["urls"], ["hxxps://otro[.]test/"])
        self.assertEqual(rules(report), {"link_label_mismatch"})

    def test_missing_headers_produce_partial_report(self):
        report = analyzer.analyze_bytes(b"Solo texto sin cabeceras\n")
        self.assertTrue(report["notes"])
        self.assertEqual(report["headers"]["from"], "")

    def test_bad_url_does_not_crash(self):
        report = analyzer.analyze_bytes(message_bytes("http://[direccion-invalida]/"))
        self.assertTrue(report["notes"])

    def test_terminal_controls_removed_and_links_defanged(self):
        data = b"From: prueba@example.test\nSubject: \x1b[31mPrueba\n\nhttp://cuenta.test/\n"
        report = analyzer.analyze_bytes(data)
        text = analyzer.format_report(report)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("http://", text)
        self.assertEqual(json.loads(json.dumps(report)), report)

    def test_unsupported_charset_skips_body_with_note(self):
        data = b"From: a@example.test\nContent-Type: text/plain; charset=charset-inexistente\n\ntexto\n"
        self.assertTrue(analyzer.analyze_bytes(data)["notes"])

    def test_authentication_results_are_not_treated_as_validation(self):
        report = analyzer.analyze_bytes(message_bytes(**{"Authentication-Results": "untrusted.test; spf=pass; dkim=pass; dmarc=pass"}))
        self.assertIn("No se verifica SPF", report["limitation"])
        self.assertNotIn("authentication_validated", report)

    def test_input_size_and_empty_input_rejected(self):
        with patch.object(analyzer, "MAX_BYTES", 8):
            with self.assertRaises(ValueError):
                analyzer.analyze_bytes(b"123456789")
        with self.assertRaises(ValueError):
            analyzer.analyze_bytes(b"")

    def test_json_cli_output_and_missing_file_error(self):
        result = subprocess.run([sys.executable, str(ROOT / "phishing_analyzer.py"), str(ROOT / "examples" / "normal.eml"), "--json"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["findings"], [])
        missing = subprocess.run([sys.executable, str(ROOT / "phishing_analyzer.py"), str(ROOT / "examples" / "inexistente.eml")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn("Traceback", missing.stderr)


if __name__ == "__main__":
    unittest.main()
