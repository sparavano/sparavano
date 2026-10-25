# Primeros pasos

El objetivo de esta primera etapa es que puedas ejecutar el proyecto, entender cada regla y explicar sus resultados. La ubicación pública del laboratorio es [sparavano/sparavano · projects/phishing-email-analyzer](https://github.com/sparavano/sparavano/tree/main/projects/phishing-email-analyzer).

Para repetir los cinco casos y ver los controles en un solo recorrido, abrí **`demo_portfolio.cmd`**. Se genera un resumen en `reports\demo_portfolio\RESUMEN.md` y los datos en `resultados.json` dentro de esa misma carpeta. La [guía de demostración](RECORRIDO_DEMO.md) explica cómo mostrarlo en tres minutos. Este recorrido importa explicaciones guardadas; no genera una respuesta nueva ni usa una API.

## 1. Empezar con el asistente manual

Hacé doble clic en **`modo_manual.cmd`**. El menú ofrece:

- **1: preparar** una solicitud. El ejemplo predeterminado es `examples\revision_enlace.eml`.
- **2: validar** una respuesta guardada. La ruta de respuesta predeterminada es `reports\respuesta_ia.json`.
- **3: ver** la demo de IA ya guardada. Sus informes se guardan en `reports\demo\`, separados de tu revisión.
- **0: salir**.

Elegí **1** y aceptá el ejemplo para comenzar. El asistente crea `reports\solicitud_ia.json` y `reports\LEEME_IA.txt`. Abrí el segundo archivo en el Bloc de notas y copiá todo su contenido a ChatGPT o a la herramienta de chat elegida.

Guardá la respuesta como **`reports\respuesta_ia.json`**, en UTF-8, con sólo el objeto JSON. Quitá los delimitadores de bloque Markdown si el chat los agregó; no guardes texto introductorio o explicaciones fuera del JSON. En el Bloc de notas, elegí el tipo **Todos los archivos** para conservar la extensión `.json`.

Volvé al asistente y elegí **2**. Usá el mismo correo de la preparación y la respuesta guardada. Si pasa los controles, se generan `reports\informe_manual.json` y `reports\informe_manual.txt`. Abrí el informe de texto y revisá las explicaciones y comprobaciones manuales.

El asistente funciona sin clave ni créditos de API y no hace llamadas de red. La herramienta de chat que elijas puede consumir su propio plan o cuota. Al copiar el texto preparado, compartís el paquete minimizado con ese servicio.

### Análisis local básico

Para ver los ejemplos y la demo guardada directamente, también podés abrir `demo.cmd`. Después podés pasar a los comandos y ejercicios de esta guía.

Abrí PowerShell en la carpeta `phishing-email-analyzer`:

```powershell
py -3 phishing_analyzer.py examples\normal.eml
py -3 phishing_analyzer.py examples\sospechoso.eml
```

El ejemplo normal debe mostrar 0 hallazgos. El sospechoso debe mostrar varias señales. Leé cada motivo y buscá su evidencia dentro del archivo `.eml`, que podés abrir con un editor de texto.

Si `py` no está disponible y tenés Python instalado como `python`, usá ese comando en su lugar.

## 2. Entender el recorrido

Leé el código en este orden:

1. La entrada del programa: cómo recibe la ruta del archivo y la opción `--json`.
2. La lectura del `.eml`: cómo transforma los bytes del archivo en un mensaje.
3. Las funciones que obtienen dominios, enlaces y nombres de adjuntos.
4. Las condiciones que agregan hallazgos.
5. La salida: cómo muestra el motivo y la evidencia.
6. En `ai_explainer.py`, la solicitud minimizada y el validador de respuestas.

En cada función, identificá qué dato recibe, qué devuelve y qué condición evalúa. No hace falta memorizar todas las bibliotecas para entender la decisión que toma una regla.

## 3. Cuatro ejercicios pequeños

Trabajá con copias de los ejemplos ficticios dentro de `private/`, para no modificar los originales:

```powershell
New-Item -ItemType Directory -Force private
Copy-Item examples\sospechoso.eml private\ejercicio.eml
```

1. **Remitente y respuesta.** Cambiá `Reply-To` para que use el mismo dominio que `From`. Ejecutá el análisis y comprobá que desaparezca esa señal. Explicá por qué dominios distintos también pueden ser legítimos.
2. **Urgencia.** Cambiá el asunto por `Información de la cuenta`. Comprobá qué cambia en los hallazgos y buscá en el código las expresiones que activan esa regla.
3. **Texto y destino.** Localizá un enlace HTML que muestre una URL distinta de su destino. Hacé coincidir ambos dominios y comprobá el cambio. La herramienta sólo compara el contenido estático del enlace.
4. **Adjuntos.** Cambiá el nombre ficticio de un adjunto de una extensión ejecutable a `.txt`. Comprobá el cambio y anotá por qué eso no alcanza para asegurar que un adjunto es seguro.

Después ejecutá las pruebas:

```powershell
py -3 -m unittest discover -s tests -v
```

Para cada ejercicio, anotá qué cambiaste, qué esperabas y qué ocurrió. Esas notas son una buena base para explicar el laboratorio con tus palabras.

## 4. Guardar un reporte de ejemplo

```powershell
New-Item -ItemType Directory -Force reports
py -3 phishing_analyzer.py examples\sospechoso.eml --json | Set-Content -Encoding utf8 reports\sospechoso.json
```

Abrí el JSON y relacioná sus hallazgos con los que viste en la consola. Usá datos ficticios si querés compartir un reporte.

## 5. Ver una explicación de IA guardada

```powershell
py -3 phishing_analyzer.py examples\sospechoso.eml --ai-response examples\ai_response_demo.json
```

Este comando carga y valida un JSON existente. No hace una nueva inferencia ni una llamada de red. La demo fue preparada por el asistente durante el desarrollo; consultá su [procedencia](PROVENIENCIA_IA.md).

Compará cada `finding_id` y `rule` con los hallazgos del reporte. Leé las comprobaciones manuales y marcá cuáles podés realizar. La validación del archivo comprueba referencias y formato, pero puede aceptar una afirmación semánticamente falsa.

## 6. Pedir una explicación mediante un intercambio manual

El asistente del inicio también se puede usar desde PowerShell:

```powershell
py -3 manual_mode.py --prepare examples\revision_enlace.eml
notepad reports\LEEME_IA.txt
```

La preparación crea `reports\solicitud_ia.json` y `reports\LEEME_IA.txt`. La solicitud contiene un `request_id`, los hallazgos minimizados, instrucciones y el esquema que debe tener la respuesta. No contiene encabezados, cuerpo, evidencias, URL ni el hash del correo.

Copiá todo `LEEME_IA.txt` al chat elegido. El archivo ya incluye las instrucciones y el paquete para pedir únicamente el JSON del esquema. Ese intercambio ocurre fuera del analizador.

Guardá la respuesta como `reports\respuesta_ia.json`, en UTF-8, sin bloques Markdown ni texto antes o después del JSON. Luego validala usando el mismo correo:

```powershell
py -3 manual_mode.py --validate examples\revision_enlace.eml reports\respuesta_ia.json
notepad reports\informe_manual.txt
```

Si la respuesta no corresponde a la solicitud, omite hallazgos, agrega identificadores o incumple otro control, el validador la rechaza. Si pasa esos controles, guarda `reports\informe_manual.json` y `reports\informe_manual.txt`. Conservá la revisión del contenido: un formato correcto no demuestra que la explicación sea verdadera.

Para trabajar con otro `.eml`, reemplazá la ruta del ejemplo por la ruta del archivo en ambos comandos. El asistente lo lee desde su ubicación y no copia el correo al repositorio. Los informes locales pueden contener evidencia del correo; mantenelos fuera de la publicación.

Los comandos de bajo nivel siguen disponibles:

```powershell
py -3 phishing_analyzer.py examples\revision_enlace.eml --export-ai-request reports\solicitud_ia.json
py -3 phishing_analyzer.py examples\revision_enlace.eml --ai-response reports\respuesta_ia.json
```

El `request_id` deriva de los hechos minimizados y la versión del contrato. No identifica de manera única el correo: mensajes distintos pueden producir la misma solicitud si activan las mismas reglas en el mismo orden.

## 7. Integración opcional con OpenAI

Este es el único modo del programa que realiza una consulta de red. Envía la solicitud minimizada a Responses API; no envía el correo completo.

Requiere estas variables de entorno en la sesión donde ejecutes Python:

- `OPENAI_API_KEY`: tu clave de API, configurada localmente fuera del chat y del repositorio.
- `OPENAI_MODEL`: el identificador del modelo que elijas y al que tenga acceso tu cuenta.

El programa no elige un modelo por defecto ni carga automáticamente archivos `.env`. Una vez configurado el entorno, el comando es:

```powershell
py -3 phishing_analyzer.py examples\sospechoso.eml --ai-openai
```

**Estado en esta entrega:** no hay una prueba exitosa de generación por API en vivo. El flujo principal es manual y no necesita clave ni créditos de API. La demo guardada y las pruebas sin red no prueban el comportamiento real del proveedor.

Con cero hallazgos, el programa omite la consulta al proveedor: no hay señales que explicar. Esto tampoco determina que el correo sea seguro.

## 8. Ejecutar la evaluación sin red

```powershell
py -3 evals\offline_suite.py
```

La suite usa casos sintéticos y guarda los resultados en [EVALUACION.md](EVALUACION.md) y [EVALUACION.json](EVALUACION.json). Revisá qué casos acepta o rechaza y el caso que expone el límite semántico: una explicación puede conservar identificadores y estructura mientras afirma algo falso.

Para practicar evaluación técnica de IA, registrá por separado el comportamiento esperado, el resultado observado y lo que ese caso permite concluir. Estos resultados no miden precisión de detección en correos reales ni calidad de una API remota.

Consultá [Arquitectura de IA](ARQUITECTURA_IA.md) para revisar las fronteras entre reglas, generador de explicaciones y validador.

### Una señal en un caso benigno

Completá el [ejercicio de urgencia en un aviso autorizado ficticio](CASO_URGENCIA_BENIGNA.md). Compara una variante con «URGENTE» y otra idéntica con «Aviso». El objetivo es explicar por qué una regla puede activarse en un escenario benigno y por qué esa señal necesita revisión contextual. Reproducilo con `py -3 evals\urgency_context.py`.

## 9. Trabajar con el laboratorio en GitHub

Si todavía no tenés una copia local del repositorio, abrí PowerShell en la carpeta donde quieras guardarlo:

```powershell
git clone https://github.com/sparavano/sparavano.git
cd sparavano\projects\phishing-email-analyzer
```

Podés clonar y leer el repositorio público. Para subir cambios a `sparavano/sparavano`, necesitás iniciar sesión en GitHub con una cuenta que tenga permiso de escritura. Si ya lo clonaste, entrá directamente a `sparavano\projects\phishing-email-analyzer`.

La carpeta del laboratorio usa el Git del repositorio contenedor. Antes de modificar archivos, obtené los cambios recientes:

```powershell
git pull
```

Después de trabajar en el código o la documentación, prepará los archivos del laboratorio desde esa misma carpeta:

```powershell
git add -- "*.py" demo.cmd modo_manual.cmd demo_portfolio.cmd README.md .gitignore examples tests docs evals
git status --short
git diff --cached --stat
git diff --cached
```

Revisá el contenido preparado. Los ejemplos de `examples/` deben seguir siendo ficticios. Mantené fuera de Git los correos reales, credenciales, reportes privados y datos personales: el contenido de este repositorio es público.

Cuando hayas terminado la revisión, guardá y subí los cambios:

```powershell
git commit -m "Update phishing email analysis lab"
git push
```

Podés revisar el resultado en [el laboratorio público](https://github.com/sparavano/sparavano/tree/main/projects/phishing-email-analyzer). No pegues contraseñas ni tokens dentro del código o del README.

## 10. Describir lo que hiciste

Después de ejecutar y entender la primera versión, podés adaptar esta descripción a lo que efectivamente hayas trabajado:

> Laboratorio educativo en Python para revisar señales de phishing en archivos `.eml`. Combina reglas locales con una capa opcional de explicación por IA, solicitudes minimizadas y validación de respuestas. Incluye ejemplos ficticios y una evaluación con casos sintéticos que documenta el alcance y los límites de los controles.

Agregá qué parte revisaste o modificaste y qué aprendiste. La descripción debe reflejar el alcance de las reglas y los resultados que comprobaste. Distinguí una explicación nueva obtenida por intercambio manual, una demo guardada y una generación por API. En esta entrega no hay una prueba exitosa de generación por API en vivo.
