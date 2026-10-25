# Analizador de correos de phishing

Una herramienta educativa en Python que lee un archivo de correo `.eml` y muestra señales que conviene revisar. Cada hallazgo incluye su motivo y la evidencia encontrada.

**Estado:** versión 0.1.0, preparada con asistencia de IA. Incluye ejemplos ficticios, 18 pruebas automatizadas y una guía para ejecutar y modificar cada regla.

## Qué hace

- Compara los dominios de `From` y `Reply-To`.
- Busca expresiones de urgencia en el asunto.
- Revisa enlaces HTTP(S): uso de HTTP, direcciones IP y credenciales dentro de la URL.
- Compara el dominio de una URL visible en un enlace HTML con el destino del enlace.
- Señala nombres de adjuntos con extensiones que pueden ejecutar código.
- Permite obtener la salida en JSON.

El análisis ocurre en tu PC. La herramienta no hace consultas de red ni abre enlaces. Tampoco extrae o ejecuta adjuntos.

## Empezar en Windows

En esta PC podés abrir **`demo.cmd` con doble clic** para ejecutar los dos ejemplos. El lanzador busca el Python incluido con Codex o el lanzador `py` de Windows. No instala programas ni cambia la configuración del equipo.

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

## Ejecutar las pruebas

```powershell
py -3 -m unittest discover -s tests -v
```

Las pruebas ayudan a comprobar casos concretos. No demuestran que el analizador detecte todos los correos de phishing.

## Cómo interpretar los resultados

Un hallazgo es una **señal para revisar**, no un veredicto. Por ejemplo, una empresa puede usar legítimamente un dominio distinto para recibir respuestas. La urgencia también aparece en mensajes auténticos.

Cero hallazgos significa que estas reglas no encontraron señales. No significa que el correo sea seguro.

## Límites de esta versión

- No calcula un puntaje ni decide si un correo es phishing.
- No verifica SPF, DKIM ni DMARC.
- No consulta DNS, reputación de dominios o bases de amenazas.
- Compara dominios completos. No usa la Public Suffix List ni decide si dos subdominios pertenecen a una misma organización.
- Sólo inspecciona enlaces HTTP(S). El análisis HTML es estático: no ejecuta JavaScript ni sigue redirecciones.
- No es un antivirus. Una extensión llamativa no demuestra que un adjunto sea malicioso, y una extensión habitual no demuestra que sea seguro.

## Privacidad y GitHub

Usá los ejemplos ficticios para aprender y mostrar el proyecto. Un correo real puede contener nombres, direcciones, identificadores, enlaces de acceso y otros datos privados.

`.gitignore` excluye los archivos `.eml`, salvo los de `examples/`, además de `private/` y `reports/`. No guardes correos reales en `examples/`. Revisá siempre lo que vas a subir: `.gitignore` no elimina archivos ya incluidos en Git.

La ubicación pública del laboratorio es [sparavano/sparavano · projects/phishing-email-analyzer](https://github.com/sparavano/sparavano/tree/main/projects/phishing-email-analyzer). La guía [Primeros pasos](docs/PRIMEROS_PASOS.md) incluye ejercicios y los pasos para clonar el repositorio y actualizar este laboratorio.

## Aprendizajes para trabajar

Este proyecto permite practicar lectura de archivos, estructura de un correo, funciones, condiciones, análisis básico de URL y pruebas automatizadas. Para describirlo en tu perfil, primero completá los ejercicios y explicá con tus palabras qué hace y qué límites tiene.

## Fuentes

- Inspiración: [video de The Social Dork sobre cuatro laboratorios de ciberseguridad](https://www.youtube.com/watch?v=nuYT-fZgAVk).
- [Documentación oficial de `email.parser`](https://docs.python.org/3/library/email.parser.html).
- [Documentación oficial de `urllib.parse`](https://docs.python.org/3/library/urllib.parse.html).

La implementación de este repositorio es una adaptación educativa; no es una transcripción del código del video.
