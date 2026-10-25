# Analizador de correos de phishing

Una herramienta educativa en Python que lee un archivo de correo `.eml` y muestra señales que conviene revisar. Cada hallazgo incluye su motivo y la evidencia encontrada.

**Estado:** versión 0.2, preparada con asistencia de IA. Incluye ejemplos ficticios, pruebas automatizadas, evaluación con casos sintéticos y una capa opcional de explicación por IA.

## Qué hace

- Compara los dominios de `From` y `Reply-To`.
- Busca expresiones de urgencia en el asunto.
- Revisa enlaces HTTP(S): uso de HTTP, direcciones IP y credenciales dentro de la URL.
- Compara el dominio de una URL visible en un enlace HTML con el destino del enlace.
- Señala nombres de adjuntos con extensiones que pueden ejecutar código.
- Permite obtener la salida en JSON.
- Exporta una solicitud minimizada para pedir explicaciones a una IA.
- Importa y valida una respuesta JSON guardada, o consulta opcionalmente la API de OpenAI.

El análisis del correo y las reglas ocurren en tu PC. La herramienta no abre enlaces ni extrae o ejecuta adjuntos. Sólo el modo opcional `--ai-openai` hace una consulta de red. Exportar una solicitud o importar una respuesta guardada funciona sin red.

## Empezar en Windows

En Windows podés abrir **`demo.cmd` con doble clic** para ejecutar los dos correos de ejemplo y reproducir la explicación de IA guardada. El lanzador busca el Python incluido con Codex o el lanzador `py` de Windows. No instala programas ni cambia la configuración del equipo.

Para ejecutar comandos por tu cuenta:

Necesitás Python 3.10 o posterior. No hay paquetes externos para instalar.

Abrí PowerShell dentro de la carpeta del proyecto y ejecutá:

```powershell
py -3 --version
py -3 phishing_analyzer.py examples\normal.eml
py -3 phishing_analyzer.py examples\sospechoso.eml
```

Si tu instalación usa el comando `python`, reemplazá `py -3` por `python`.

Los ejemplos son ficticios y usan dominios `.example` y `.test`. El ejemplo normal debe producir **0 hallazgos**; el sospechoso debe mostrar varias señales y sus motivos.

El ejemplo sospechoso produce **7 hallazgos de 6 reglas distintas**: dos enlaces HTTP, un destino con IP, un dominio de respuesta distinto, urgencia en el asunto, un enlace HTML engañoso y un nombre de adjunto con extensión de ejecución. El adjunto contiene sólo texto ficticio; no es un ejecutable. Podés ver la salida real en [la demostración guardada](docs/DEMO.txt).

Para generar un reporte:

```powershell
New-Item -ItemType Directory -Force reports
py -3 phishing_analyzer.py examples\sospechoso.eml --json | Set-Content -Encoding utf8 reports\sospechoso.json
```

La carpeta `reports/` queda fuera de Git mediante `.gitignore`.

## Explicaciones opcionales con IA

Las reglas encuentran señales. La IA recibe una descripción fija de esas señales y propone explicaciones y comprobaciones manuales. La revisión humana sigue siendo necesaria.

Para ver una respuesta de demostración guardada:

```powershell
py -3 phishing_analyzer.py examples\sospechoso.eml --ai-response examples\ai_response_demo.json
```

Este comando **importa una respuesta existente**; no genera una nueva respuesta ni consulta una API. La demo fue preparada por el asistente durante el desarrollo. Su [procedencia](docs/PROVENIENCIA_IA.md) se documenta por separado.

También está documentada una [prueba de intercambio manual con una respuesta nueva](docs/PRUEBA_MANUAL_IA.md), realizada con otro correo ficticio y un contexto de generación separado. Incluye solicitud, respuesta, salida de la CLI y un control negativo de referencia. Sigue siendo una sola muestra, no un benchmark.

Para trabajar manualmente con la herramienta de IA que elijas:

```powershell
py -3 phishing_analyzer.py examples\sospechoso.eml --export-ai-request reports\solicitud_ia.json
```

El archivo exportado contiene instrucciones, un esquema de respuesta y hallazgos con identificadores y observaciones de un catálogo fijo. **No contiene encabezados, cuerpo, evidencias, URL ni el hash del correo.** Podés copiar ese paquete a la herramienta elegida, guardar su respuesta como JSON puro y cargarla con `--ai-response`. Al copiar el paquete a un servicio externo, lo compartís con ese servicio.

La integración opcional `--ai-openai` usa Responses API. Requiere `OPENAI_API_KEY` y `OPENAI_MODEL` en el entorno; el proyecto no fija un modelo ni carga archivos `.env`. La clave se configura localmente, fuera del chat y del repositorio.

**Estado de esa integración:** no hay una credencial configurada en esta PC y la llamada HTTP real al proveedor no se ha probado. Las pruebas locales y la demo guardada no sustituyen esa prueba. Con cero hallazgos, este modo omite la consulta al proveedor.

Consultá [Primeros pasos](docs/PRIMEROS_PASOS.md) para ejecutar cada modo y [Arquitectura de IA](docs/ARQUITECTURA_IA.md) para revisar el flujo de datos y los controles.

## Ejecutar pruebas y evaluación

```powershell
py -3 -m unittest discover -s tests -v
py -3 evals\offline_suite.py
```

La suite de evaluación registra resultados en [EVALUACION.md](docs/EVALUACION.md) y [EVALUACION.json](docs/EVALUACION.json). Usa casos sintéticos para comprobar el contrato y los controles locales. No es un benchmark de detección sobre correos reales ni una medición de calidad de un proveedor de IA.

El validador comprueba estructura, cobertura, identificadores, reglas, correspondencia de la solicitud y algunos patrones de salida. **No verifica por completo la verdad del texto generado.** Una explicación falsa con referencias válidas puede pasar esos controles.

En la preparación de esta versión pasaron **56 pruebas automatizadas** y **27 casos sintéticos de contrato**. El control semántico se registra por separado y muestra una falsedad aceptada por el validador; no se presenta como una explicación correcta ni como una medición de precisión del modelo.

## Cómo interpretar los resultados

Un hallazgo es una **señal para revisar**, no un veredicto. Por ejemplo, una empresa puede usar legítimamente un dominio distinto para recibir respuestas. La urgencia también aparece en mensajes auténticos.

Cero hallazgos significa que estas reglas no encontraron señales. No significa que el correo sea seguro.

## Límites de esta versión

- No calcula un puntaje ni decide si un correo es phishing.
- No verifica SPF, DKIM ni DMARC.
- No consulta la reputación de los destinos ni verifica sus registros DNS.
- Compara dominios completos. No usa la Public Suffix List ni decide si dos subdominios pertenecen a una misma organización.
- Sólo inspecciona enlaces HTTP(S). El análisis HTML es estático: no ejecuta JavaScript ni sigue redirecciones.
- No es un antivirus. Una extensión llamativa no demuestra que un adjunto sea malicioso, y una extensión habitual no demuestra que sea seguro.
- La explicación de IA puede contener errores. Pasar la validación de formato y referencias no la convierte en un hecho comprobado.

## Privacidad y GitHub

Usá los ejemplos ficticios para aprender y mostrar el proyecto. Un correo real puede contener nombres, direcciones, identificadores, enlaces de acceso y otros datos privados.

`.gitignore` excluye los archivos `.eml`, salvo los de `examples/`, además de `private/` y `reports/`. No guardes correos reales en `examples/`. Revisá siempre lo que vas a subir: `.gitignore` no elimina archivos ya incluidos en Git.

La ubicación pública del laboratorio es [sparavano/sparavano · projects/phishing-email-analyzer](https://github.com/sparavano/sparavano/tree/main/projects/phishing-email-analyzer). La guía [Primeros pasos](docs/PRIMEROS_PASOS.md) incluye ejercicios y los pasos para clonar el repositorio y actualizar este laboratorio.

## Aprendizajes para trabajar

Este proyecto permite practicar lectura de archivos, estructura de un correo, funciones, condiciones, análisis básico de URL y pruebas automatizadas. La capa de IA también permite trabajar minimización de datos, trazabilidad, validación de respuestas y límites de una evaluación técnica.

Para un recorrido orientado a auditoría y evaluación de IA, el ejercicio es distinguir qué controla el software, qué comprueban las pruebas y qué exige revisión humana. Para describirlo en tu perfil, primero completá los ejercicios y explicá con tus palabras qué hiciste y qué límites encontraste.

## Fuentes

- Inspiración: [video de The Social Dork sobre cuatro laboratorios de ciberseguridad](https://www.youtube.com/watch?v=nuYT-fZgAVk).
- [Documentación oficial de `email.parser`](https://docs.python.org/3/library/email.parser.html).
- [Documentación oficial de `urllib.parse`](https://docs.python.org/3/library/urllib.parse.html).
- [Documentación oficial de OpenAI sobre generación de texto y Responses API](https://developers.openai.com/api/docs/guides/text).

La implementación de este repositorio es una adaptación educativa; no es una transcripción del código del video.
