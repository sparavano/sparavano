# Primeros pasos

El objetivo de esta primera etapa es que puedas ejecutar el proyecto, entender cada regla y explicar sus resultados. La ubicación pública del laboratorio es [sparavano/sparavano · projects/phishing-email-analyzer](https://github.com/sparavano/sparavano/tree/main/projects/phishing-email-analyzer).

## 1. Ejecutar los dos ejemplos

Para la primera prueba en esta PC, hacé doble clic en `demo.cmd`. Se abrirá una consola con ambos resultados. Después podés pasar a los comandos y ejercicios de esta guía.

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

## 5. Trabajar con el laboratorio en GitHub

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
git add phishing_analyzer.py demo.cmd README.md .gitignore examples tests docs
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

## 6. Describir lo que hiciste

Después de ejecutar y entender la primera versión, podés adaptar esta descripción a lo que efectivamente hayas trabajado:

> Laboratorio educativo en Python para revisar señales de phishing en archivos `.eml`. Analiza encabezados, enlaces y nombres de adjuntos de forma local. Incluye ejemplos ficticios, pruebas y documentación de sus límites.

Agregá qué parte revisaste o modificaste y qué aprendiste. La descripción debe reflejar el alcance de las reglas y los resultados que comprobaste.
