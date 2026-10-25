# Procedencia de la demostración de IA

- Fecha de preparación: 25 de octubre de 2026.
- Archivo: `examples/ai_response_demo.json`.
- Origen: texto redactado por el asistente de IA de la sesión durante la implementación de la versión 0.2, a partir de los hechos minimizados del ejemplo ficticio. No se atribuye a un modelo o proveedor específico.
- El asistente también tuvo contexto del desarrollo. No fue una prueba ciega ni una evaluación independiente de un modelo.
- La muestra se guardó como JSON y se comprobó con el validador local. Al ejecutar `--ai-response` se reproduce esa respuesta guardada: no se consulta una IA nueva.
- El identificador corresponde a los hechos minimizados y al catálogo, no al hash ni a la identidad del correo original.
- No se efectuó una llamada real a la API de OpenAI: no hay una clave configurada en esta PC. Las pruebas del transporte usan dobles de prueba, sin red.
- La evaluación en `EVALUACION.md` emplea respuestas sintéticas controladas para probar el contrato. Sus resultados no miden la precisión de detección de phishing de un modelo ni demuestran ausencia de alucinaciones.

Para obtener una respuesta nueva, se puede usar el intercambio manual de JSON con una herramienta de IA elegida o configurar explícitamente el modo opcional `--ai-openai`. La salida debe pasar la validación local y revisarse por una persona.

## Prueba posterior de intercambio manual

El 25 de octubre de 2026 se preparó otra solicitud, con el hallazgo `userinfo_link` de un correo ficticio diferente. Se entregaron sus hechos minimizados y el contrato a un agente sin historial de conversación heredado. Ese agente no usó herramientas ni recibió el correo. Su respuesta nueva se guardó en `examples/respuesta_manual.json` y se comprobó mediante la CLI; una copia con un ID inexistente se rechazó.

La [prueba manual](PRUEBA_MANUAL_IA.md) conserva la solicitud, la respuesta y los resultados. Es una muestra de generación en esta sesión y no una llamada de la aplicación a un proveedor por API. No modifica el estado de la prueba real del adaptador de OpenAI, que sigue pendiente.
