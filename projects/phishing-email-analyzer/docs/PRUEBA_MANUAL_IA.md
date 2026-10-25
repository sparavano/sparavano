# Prueba de intercambio manual con una respuesta nueva de IA

Fecha: 25 de octubre de 2026. Versión del programa: 0.2.0.

Se analizó un correo ficticio diferente del ejemplo de demostración original. Se exportó una solicitud minimizada y se entregaron sus hechos y contrato a un agente de IA de esta sesión, sin heredar el historial de la conversación. El agente no usó herramientas ni recibió el archivo de correo o su evidencia textual.

Esta fue una generación nueva durante el intercambio manual. No fue una llamada del programa a OpenAI Responses API. Las ejecuciones posteriores con el JSON publicado reproducen la respuesta guardada.

## Archivos para reproducir

- Correo ficticio: [revision_enlace.eml](../examples/revision_enlace.eml).
- Solicitud minimizada: [solicitud_manual.json](../examples/solicitud_manual.json).
- Respuesta generada: [respuesta_manual.json](../examples/respuesta_manual.json).
- Salida del programa: [PRUEBA_MANUAL_SALIDA.txt](PRUEBA_MANUAL_SALIDA.txt).

## Resultados observados

| Comprobación | Resultado |
|---|---|
| Reglas del analizador | Un hallazgo: `F001 / userinfo_link` |
| Respuesta nueva de IA | Una explicación referida a ese ID y a esa regla |
| Validación local de estructura y referencias | Aceptada |
| Control negativo: sustituir el ID por `F999` | Rechazado |
| Ejecución completa de la CLI con la respuesta guardada | Completada |
| Llamada real a la API de OpenAI | No realizada |

La solicitud sólo contiene identificadores, descripciones fijas, instrucciones y esquema de respuesta. El identificador de solicitud es `07c35f92e4668c097d343a0ebe09885695b66fec35e9c8afb68959cdabbf0ffb` y se deriva de los hechos minimizados, no del contenido ni de la identidad del correo.

## Explicación recibida

> El texto anterior al signo @ corresponde a información de usuario. Para identificar el destino del enlace, hay que distinguir ese texto del host real, situado después del separador.

## Revisión humana del ejemplo

La explicación es consistente con el hallazgo de este caso: la URL ficticia contiene información de usuario en la autoridad, antes de `@`, y el host de destino es el componente posterior. La revisión contrasta la explicación con la URL del ejemplo y con el análisis local; no establece quién controla el destino ni emite un veredicto sobre phishing.

Esta observación corresponde a una única muestra. No mide precisión de detección ni demuestra resistencia general a alucinaciones o inyecciones. El caso de falsedad semántica que pasa controles sigue documentado en [EVALUACION.md](EVALUACION.md).

## Reproducir sin red

Desde la carpeta del laboratorio:

```powershell
py -3 phishing_analyzer.py examples\revision_enlace.eml --ai-response examples\respuesta_manual.json
```

Para obtener otra respuesta, exportá una solicitud con `--export-ai-request`, usá el intercambio manual con la herramienta elegida y guardá el JSON nuevo. La integración automática `--ai-openai` requiere una credencial y su prueba real sigue pendiente.
