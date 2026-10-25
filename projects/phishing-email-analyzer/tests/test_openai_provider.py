"""Responses transport tests use mocked HTTP only; no API key or network needed."""

import contextlib
import copy
import io
import json
import os
import traceback
import unittest
from http.client import HTTPException
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

import openai_provider as provider


SECRET = "test-secret-never-print"
MODEL = "configured-model"
BUNDLE = {
    "request_id": "request-1",
    "instructions": "Explicar únicamente los hallazgos suministrados.",
    "findings": [{"finding_id": "f1", "rule": "http_link", "observation": "Se detectó HTTP."}],
    "response_schema": {"type": "object", "properties": {}, "additionalProperties": False},
}


def completed(text=None):
    if text is None:
        text = json.dumps({"request_id": "request-1", "findings": []})
    return {"status": "completed", "output": [{
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": text}],
    }]}


class FakeResponse(io.BytesIO):
    def __init__(self, data, status=200):
        super().__init__(data)
        self.code = status
        self.requested_size = None

    def getcode(self):
        return self.code

    def read(self, size=-1):
        self.requested_size = size
        return super().read(size)


class ProviderTests(unittest.TestCase):
    def request(self, response=None, *, raw=None, status=200):
        if raw is None:
            raw = json.dumps(completed() if response is None else response).encode("utf-8")
        stream = FakeResponse(raw, status)
        opener = Mock()
        opener.open.return_value = stream
        with patch.object(provider, "build_opener", return_value=opener) as factory:
            result = provider.request_explanation(BUNDLE, api_key=SECRET, model=MODEL)
        return result, opener, factory, stream

    def test_success_and_minimized_request_configuration(self):
        bundle = copy.deepcopy(BUNDLE)
        bundle["raw_email"] = "Do not send this email body"
        bundle["findings"][0]["raw_url"] = "https://private.example/path"
        stream = FakeResponse(json.dumps(completed()).encode())
        opener = Mock()
        opener.open.return_value = stream
        with patch.object(provider, "build_opener", return_value=opener) as factory:
            result = provider.request_explanation(bundle, api_key=SECRET, model=MODEL)
        request = opener.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer " + SECRET)
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 30)
        self.assertIsInstance(factory.call_args.args[0], provider._NoRedirect)
        self.assertEqual(payload["model"], MODEL)
        self.assertEqual(payload["instructions"], BUNDLE["instructions"])
        self.assertEqual(json.loads(payload["input"]), {"request_id": "request-1", "findings": BUNDLE["findings"]})
        self.assertEqual(payload["text"]["format"], {
            "type": "json_schema", "name": "phishing_explanation",
            "schema": BUNDLE["response_schema"], "strict": True,
        })
        self.assertIs(payload["store"], False)
        self.assertEqual(payload["max_output_tokens"], 3000)
        self.assertNotIn("tools", payload)
        self.assertNotIn(SECRET, request.data.decode())
        self.assertNotIn("raw_email", request.data.decode())
        self.assertNotIn("raw_url", request.data.decode())
        self.assertEqual(stream.requested_size, 1024 * 1024 + 1)
        self.assertTrue(stream.closed)
        self.assertEqual(result, {"request_id": "request-1", "findings": []})

    def test_environment_configuration_and_explicit_override(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": SECRET, "OPENAI_MODEL": MODEL}, clear=True):
            stream = FakeResponse(json.dumps(completed()).encode())
            opener = Mock()
            opener.open.return_value = stream
            with patch.object(provider, "build_opener", return_value=opener):
                provider.request_explanation(BUNDLE)
            payload = json.loads(opener.open.call_args.args[0].data)
            self.assertEqual(payload["model"], MODEL)
            self.assertEqual(opener.open.call_args.args[0].get_header("Authorization"), "Bearer " + SECRET)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "environment-key", "OPENAI_MODEL": "environment-model"}, clear=True):
            _, opener, _, _ = self.request()
            self.assertEqual(json.loads(opener.open.call_args.args[0].data)["model"], MODEL)

    def test_missing_configuration_does_not_open_network(self):
        cases = [(None, MODEL), ("", MODEL), ("  ", MODEL), (SECRET, None), (SECRET, ""), (SECRET, "  ")]
        with patch.dict(os.environ, {}, clear=True), patch.object(provider, "build_opener") as factory:
            for key, model in cases:
                with self.subTest(key_present=bool(key), model_present=bool(model)):
                    with self.assertRaises(provider.ProviderError):
                        provider.request_explanation(BUNDLE, api_key=key, model=model)
            factory.assert_not_called()

    def test_invalid_credentials_do_not_expose_values(self):
        with patch.object(provider, "build_opener") as factory:
            for key, model in [(SECRET + "\r\nextra", MODEL), (SECRET, MODEL + "\nextra"), (123, MODEL), (SECRET, 123)]:
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.request_explanation(BUNDLE, api_key=key, model=model)
                self.assertNotIn(SECRET, str(caught.exception))
            factory.assert_not_called()

    def test_invalid_bundle_does_not_open_network(self):
        cases = [None, {}, {**BUNDLE, "request_id": None}, {**BUNDLE, "instructions": ""},
                 {**BUNDLE, "findings": [None]}, {**BUNDLE, "findings": [{"rule": "x"}]},
                 {**BUNDLE, "findings": [{"finding_id": 1, "rule": "x", "observation": "x"}]},
                 {**BUNDLE, "response_schema": []}]
        with patch.object(provider, "build_opener") as factory:
            for bundle in cases:
                with self.subTest(bundle=bundle):
                    with self.assertRaises(provider.ProviderError):
                        provider.request_explanation(bundle, api_key=SECRET, model=MODEL)
            factory.assert_not_called()

    def test_network_and_http_errors_hide_body_key_and_traceback_context(self):
        errors = [URLError(SECRET), TimeoutError(SECRET), OSError(SECRET),
                  HTTPException(SECRET), ValueError(SECRET),
                  HTTPError(provider.ENDPOINT, 401, SECRET, {"X-Error": SECRET}, io.BytesIO(SECRET.encode()))]
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            for error in errors:
                opener = Mock()
                opener.open.side_effect = error
                with self.subTest(error_type=type(error).__name__), patch.object(provider, "build_opener", return_value=opener):
                    try:
                        provider.request_explanation(BUNDLE, api_key=SECRET, model=MODEL)
                    except provider.ProviderError as caught:
                        rendered = "".join(traceback.format_exception(caught))
                        self.assertNotIn(SECRET, rendered)
                        self.assertNotIn("X-Error", rendered)
                    else:
                        self.fail("ProviderError expected")
        self.assertEqual(captured.getvalue(), "")

    def test_unexpected_http_status_is_rejected(self):
        with self.assertRaises(provider.ProviderError):
            self.request(status=302)

    def test_redirect_handler_denies_every_redirect_destination(self):
        handler = provider._NoRedirect()
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code), self.assertRaises(provider.ProviderError):
                handler.redirect_request(Request(provider.ENDPOINT), None, code, "redirect", {}, "https://elsewhere.example/")

    def test_response_size_limit(self):
        with self.assertRaisesRegex(provider.ProviderError, "tamaño"):
            self.request(raw=b" " * (provider.MAX_RESPONSE_BYTES + 1))

    def test_invalid_response_json_is_rejected(self):
        for raw in (b"{", b"\xff", b"[]", b"null", b'{"status":"completed","status":"incomplete","output":[]}', b'{"value":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(provider.ProviderError):
                self.request(raw=raw)

    def test_incomplete_failed_or_missing_status_is_rejected(self):
        for status in ("incomplete", "failed", "in_progress", None):
            data = completed()
            data["status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(provider.ProviderError, "no completó"):
                self.request(data)

    def test_refusal_is_rejected_even_when_text_also_exists(self):
        data = completed()
        data["output"][0]["content"].append({"type": "refusal", "refusal": SECRET})
        with self.assertRaisesRegex(provider.ProviderError, "rechazó") as caught:
            self.request(data)
        self.assertNotIn(SECRET, str(caught.exception))

    def test_invalid_output_structure_and_missing_text(self):
        cases = [None, {}, [], [None], [{}], [{"type": "message"}],
                 [{"type": "message", "content": [None]}],
                 [{"type": "message", "content": [{"type": "output_text", "text": 3}]}],
                 [{"type": "message", "content": [{"type": "unexpected", "text": "{}"}]}],
                 [{"type": "message", "status": "incomplete", "content": []}]]
        for output in cases:
            with self.subTest(output=output), self.assertRaises(provider.ProviderError):
                self.request({"status": "completed", "output": output})

    def test_explanation_must_be_one_valid_json_object(self):
        for text in ("", "not JSON", "[]", "null", "{}{}", '{"x":1,"x":2}', '{"x":NaN}'):
            with self.subTest(text=text), self.assertRaises(provider.ProviderError):
                self.request(completed(text))

    def test_reasoning_item_is_skipped_and_output_text_parts_are_joined(self):
        data = completed()
        data["output"].insert(0, {"type": "reasoning", "summary": []})
        data["output"][1]["content"] = [
            {"type": "output_text", "text": '{"request_id":'},
            {"type": "output_text", "text": '"request-1","findings":[]}'},
        ]
        result, _, _, _ = self.request(data)
        self.assertEqual(result, {"request_id": "request-1", "findings": []})


if __name__ == "__main__":
    unittest.main()
