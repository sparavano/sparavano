"""Asistente local para preparar solicitudes e importar explicaciones de IA."""
import argparse
import json
import os
from pathlib import Path
import sys

from ai_explainer import build_ai_request, load_response, save_request, validate_response
from phishing_analyzer import analyze_file, format_report

ROOT = Path(__file__).resolve().parent
DEFAULT_EMAIL = ROOT / "examples" / "revision_enlace.eml"
DEFAULT_RESPONSE = ROOT / "reports" / "respuesta_ia.json"
REPORTS = ROOT / "reports"


def protect_inputs(destinations, inputs):
    protected = {Path(source).resolve() for source in inputs}
    for destination in destinations:
        target = Path(destination).resolve()
        if target in protected or any(
            target.exists() and source.exists() and target.samefile(source)
            for source in protected
        ):
            raise ValueError("La salida no puede sobrescribir el correo ni la respuesta de entrada.")


def prepare(email_path=DEFAULT_EMAIL, output_dir=REPORTS):
    output_dir = Path(output_dir)
    request_path = output_dir / "solicitud_ia.json"
    prompt_path = output_dir / "LEEME_IA.txt"
    protect_inputs([request_path, prompt_path], [email_path])
    bundle = build_ai_request(analyze_file(email_path))
    # Ambos archivos contienen sólo el bundle minimizado, nunca el correo.
    save_request(bundle, request_path, email_path)
    prompt = (
        "Explicá los hallazgos del siguiente paquete respetando sus instrucciones y su esquema. "
        "Devolvé exclusivamente el objeto JSON de respuesta, sin cercos Markdown ni comentarios. "
        "No completes información que no se proporcionó."
        + chr(10) * 2 + json.dumps(bundle, ensure_ascii=False, indent=2) + chr(10)
    )
    prompt_path.write_text(prompt, encoding="utf-8")
    return request_path, prompt_path


def validate(email_path, response_path=DEFAULT_RESPONSE, output_dir=REPORTS):
    output_dir = Path(output_dir)
    json_path = output_dir / "informe_manual.json"
    text_path = output_dir / "informe_manual.txt"
    protect_inputs([json_path, text_path], [email_path, response_path])
    report = analyze_file(email_path)
    explanation = validate_response(load_response(response_path), build_ai_request(report))
    explanation["mode"] = "intercambio manual; respuesta guardada, sin nueva inferencia"
    report["ai_explanation"] = explanation
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    text_path.write_text(format_report(report) + chr(10), encoding="utf-8")
    return report, json_path, text_path


def saved_demo():
    return validate(DEFAULT_EMAIL, ROOT / "examples" / "respuesta_manual.json", REPORTS / "demo")


def chosen_path(prompt, default):
    supplied = input(prompt).strip().strip('"')
    return Path(supplied).expanduser() if supplied else default


def interactive():
    print("MODO MANUAL — sin conexión a la API y sin pedir claves")
    while True:
        print(chr(10) + "1 Preparar solicitud para pegar en ChatGPT")
        print("2 Validar la respuesta JSON que guardaste")
        print("3 Ver el ejemplo ya guardado")
        print("0 Salir")
        option = input("Opción: ").strip()
        try:
            if option == "0":
                return 0
            if option == "1":
                email = chosen_path("Correo .eml (Enter: ejemplo ficticio): ", DEFAULT_EMAIL)
                _, prompt = prepare(email)
                print("Solicitud preparada. Copiá el contenido de " + str(prompt) + " a tu chat.")
                print("Guardá la respuesta JSON en " + str(DEFAULT_RESPONSE) + " y elegí la opción 2.")
                if hasattr(os, "startfile"):
                    try:
                        os.startfile(str(prompt))
                    except OSError:
                        print("Podés abrir ese archivo con tu editor de texto.")
            elif option == "2":
                email = chosen_path("Correo analizado (Enter: ejemplo ficticio): ", DEFAULT_EMAIL)
                response = chosen_path("Respuesta JSON (Enter: reports/respuesta_ia.json): ", DEFAULT_RESPONSE)
                report, _, text_path = validate(email, response)
                print(format_report(report))
                print("Informe guardado en " + str(text_path))
            elif option == "3":
                report, _, _ = saved_demo()
                print("Demostración guardada: esta opción no consulta un modelo nuevo.")
                print(format_report(report))
            else:
                print("Elegí 1, 2, 3 o 0.")
        except (OSError, ValueError, RecursionError) as error:
            print("No se completó esta operación: " + str(error))
        except (EOFError, KeyboardInterrupt):
            return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--prepare", type=Path, metavar="CORREO")
    actions.add_argument("--validate", nargs=2, type=Path, metavar=("CORREO", "RESPUESTA"))
    actions.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.prepare:
            request, prompt = prepare(args.prepare)
            print("Solicitud JSON: " + str(request))
            print("Texto para copiar al chat: " + str(prompt))
        elif args.validate:
            report, json_path, text_path = validate(*args.validate)
            print(format_report(report))
            print("Informes: " + str(text_path) + " / " + str(json_path))
        elif args.demo:
            report, _, _ = saved_demo()
            print("Demostración guardada; sin nueva inferencia ni conexión API.")
            print(format_report(report))
        else:
            return interactive()
    except (OSError, ValueError, RecursionError) as error:
        print("No se completó el modo manual: " + str(error), file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
