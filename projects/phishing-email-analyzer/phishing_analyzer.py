"""Analizador educativo de .eml, local y sin dependencias externas."""

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
URGENCY_PATTERN = re.compile(
    r"\b(urgente|urgent|inmediato|immediately|suspendid[ao]|suspended)\b",
    re.IGNORECASE,
)
EXECUTABLE_EXTENSIONS = {".exe", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi", ".com", ".lnk"}


def clean_text(value):
    """Impide que datos del correo controlen el formato de la terminal."""
    text = str(value)
    return "".join(ch if ch.isprintable() else " " for ch in text)


def defang(value):
    """Desactiva enlaces en la salida para reducir aperturas accidentales."""
    text = clean_text(value)
    text = re.sub(r"https://", "hxxps://", text, flags=re.IGNORECASE)
    text = re.sub(r"http://", "hxxp://", text, flags=re.IGNORECASE)
    return text.replace(".", "[.]")


def hostname(url):
    """Lee el host sin abrir la URL ni resolver DNS."""
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() not in {"http", "https"}:
            return None
        host = parts.hostname
        return host.rstrip(".").encode("idna").decode("ascii").lower() if host else None
    except (ValueError, UnicodeError):
        return None


def address_domain(value):
    addresses = getaddresses([str(value or "")])
    if len(addresses) != 1 or "@" not in addresses[0][1]:
        return None
    domain = addresses[0][1].rsplit("@", 1)[1].rstrip(".")
    try:
        return domain.encode("idna").decode("ascii").lower() or None
    except UnicodeError:
        return None


class LinkExtractor(HTMLParser):
    """Extrae anclas estáticas; no renderiza HTML ni ejecuta JavaScript."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.text_chunks = []
        self.current_link = None

    def finish_link(self):
        if self.current_link is not None:
            href, chunks = self.current_link
            self.links.append((href, "".join(chunks).strip()))
            self.current_link = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.finish_link()
            href = dict(attrs).get("href", "") or ""
            self.current_link = (href.strip(), [])

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link[1].append(data)
        else:
            self.text_chunks.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a":
            self.finish_link()

    def close(self):
        super().close()
        self.finish_link()


def message_parts(part):
    """Recorre el cuerpo sin entrar en adjuntos, incluidos mensajes .eml."""
    yield part
    if part.get_filename() is not None or part.get_content_disposition() == "attachment":
        return
    if part.is_multipart():
        for child in part.iter_parts():
            yield from message_parts(child)


def analyze_bytes(data, filename="correo.eml"):
    """Devuelve metadatos y señales observables, nunca un veredicto."""
    if len(data) > MAX_BYTES:
        raise ValueError("El archivo supera el límite de 10 MiB.")
    if not data.strip():
        raise ValueError("El archivo está vacío.")

    message = BytesParser(policy=policy.default).parsebytes(data)
    findings = []
    notes = []
    urls = set()
    attachments = []
    seen_findings = set()

    def add(rule, title, evidence):
        key = (rule, evidence)
        if key not in seen_findings:
            seen_findings.add(key)
            findings.append({"rule": rule, "title": title, "evidence": clean_text(evidence)})

    sender = str(message.get("From", ""))
    reply = str(message.get("Reply-To", ""))
    subject = str(message.get("Subject", ""))
    sender_domain = address_domain(sender)
    reply_domain = address_domain(reply)

    if not sender_domain:
        notes.append("From ausente, múltiple o no interpretable: no se pudo comparar el dominio.")
    if reply and not reply_domain:
        notes.append("Reply-To múltiple o no interpretable: no se pudo comparar el dominio.")
    if sender_domain and reply_domain and sender_domain != reply_domain:
        add("reply_to_domain", "From y Reply-To tienen dominios distintos",
            f"From: {defang(sender_domain)}; Reply-To: {defang(reply_domain)}")
    urgency_words = sorted({match.group(0).lower() for match in URGENCY_PATTERN.finditer(subject)})
    if urgency_words:
        add("urgent_subject", "El asunto contiene lenguaje de urgencia", ", ".join(urgency_words))

    for part in message_parts(message):
        if part.defects:
            notes.append("El parser encontró un problema MIME; el análisis puede estar incompleto.")
        disposition = part.get_content_disposition()
        name = part.get_filename()
        if name is not None or disposition == "attachment":
            attachments.append({"filename": defang(name or "(sin nombre)"), "content_type": clean_text(part.get_content_type())})
            if name:
                # Se comprueba la extensión final, también en factura.pdf.exe.
                normalized_name = name.rstrip(" .")
                extension = Path(normalized_name).suffix.lower()
                if extension in EXECUTABLE_EXTENSIONS:
                    add("executable_attachment", "Adjunto con extensión de ejecución", defang(name))
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue
        try:
            text = part.get_content()
        except (LookupError, UnicodeError, ValueError, KeyError):
            notes.append("Una parte del cuerpo no se pudo decodificar; no se analizó.")
            continue
        if not isinstance(text, str):
            continue
        if part.get_content_type() == "text/html":
            extractor = LinkExtractor()
            extractor.feed(text)
            extractor.close()
            for target, label in extractor.links:
                if re.match(r"^https?://", target, re.IGNORECASE):
                    urls.add(target)
                    label_host = hostname(label)
                    target_host = hostname(target)
                    if label_host and target_host and label_host != target_host:
                        add("link_label_mismatch", "El enlace muestra un dominio y apunta a otro",
                            f"Texto: {defang(label)}; destino: {defang(target)}")
            text = " ".join(extractor.text_chunks)
        for match in URL_PATTERN.finditer(text):
            urls.add(match.group(0).rstrip(".,;!?)"))

    for url in sorted(urls):
        host = hostname(url)
        if not host:
            notes.append("Se encontró una URL HTTP(S) que no se pudo interpretar.")
            continue
        parts = urlsplit(url)
        evidence = defang(url)
        if parts.scheme.lower() == "http":
            add("http_link", "Enlace HTTP sin cifrado de transporte", evidence)
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            add("ip_link", "El enlace usa una dirección IP como destino", evidence)
        if parts.username is not None or parts.password is not None:
            add("userinfo_link", "El enlace contiene información de usuario antes de @", evidence)

    return {
        "version": VERSION,
        "file": clean_text(Path(filename).name),
        "sha256": hashlib.sha256(data).hexdigest(),
        "headers": {"from": defang(sender), "reply_to": defang(reply), "subject": defang(subject)},
        "urls": [defang(url) for url in sorted(urls)],
        "attachments": attachments,
        "findings": findings,
        "notes": sorted(set(notes)),
        "limitation": "Las señales requieren revisión humana. Cero señales no demuestra legitimidad. No se verifica SPF, DKIM ni DMARC.",
    }


def analyze_file(path):
    # Lectura acotada: rechaza también archivos que crezcan durante la lectura.
    with Path(path).open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    return analyze_bytes(data, Path(path).name)


def format_report(report):
    lines = [
        f"Analizador de phishing v{report['version']}",
        f"Archivo: {report['file']}",
        f"SHA-256: {report['sha256']}",
        f"From: {report['headers']['from'] or '(ausente)'}",
        f"Reply-To: {report['headers']['reply_to'] or '(ausente)'}",
        f"Asunto: {report['headers']['subject'] or '(ausente)'}",
        f"\nSeñales encontradas: {len(report['findings'])}",
    ]
    for finding in report["findings"]:
        lines.append(f"- [{finding['rule']}] {finding['title']}: {finding['evidence']}")
    if not report["findings"]:
        lines.append("- No se encontraron señales con las reglas de esta versión.")
    lines.append(f"\nEnlaces HTTP(S): {len(report['urls'])}")
    lines.extend(f"- {url}" for url in report["urls"])
    lines.append(f"\nAdjuntos (sólo metadatos): {len(report['attachments'])}")
    lines.extend(f"- {item['filename']} ({item['content_type']})" for item in report["attachments"])
    lines.extend(f"Nota: {note}" for note in report["notes"])
    lines.append(f"\n{report['limitation']}")
    return "\n".join(lines)


def main(argv=None):
    # Windows puede usar una codificación heredada al redirigir a un archivo.
    # UTF-8 mantiene legibles las tildes tanto en consola como en JSON.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="Archivo .eml para revisar localmente")
    parser.add_argument("--json", action="store_true", help="Emite el informe en JSON")
    args = parser.parse_args(argv)
    try:
        report = analyze_file(args.file)
    except (OSError, ValueError, RecursionError) as error:
        print(f"No se pudo analizar el correo: {clean_text(error)}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
