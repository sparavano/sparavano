# Señal de urgencia en un caso benigno sintético

Fecha: 25 de octubre de 2026. Versión: 0.2.0.

Se construyó un aviso autorizado de cambio de aula que usa la palabra «URGENTE». En este ejercicio, la legitimidad forma parte del escenario definido por quien prepara el caso. No se trata de un correo real cuya autenticidad haya sido verificada.

## Comparación controlada

Los dos archivos son idénticos salvo el prefijo del asunto: `URGENTE:` se sustituye por `Aviso:`. El cuerpo, los encabezados restantes y el identificador de mensaje se conservan para aislar esa variable; son variantes de un mismo fixture, no dos entregas reales.

| Variante | Asunto | Resultado del analizador |
|---|---|---|
| [Aviso con urgencia](../examples/aviso_legitimo_urgente.eml) | URGENTE: cambio de aula de la clase de hoy | Un hallazgo: `F001 / urgent_subject` |
| [Control sin urgencia](../examples/aviso_legitimo_sin_urgencia.eml) | Aviso: cambio de aula de la clase de hoy | Cero hallazgos |

La [ejecución reproducible](../evals/urgency_context.py) comprueba la única diferencia entre archivos, las reglas observadas en cada variante, la coincidencia de la solicitud guardada y las referencias de la respuesta de IA. Las cinco comprobaciones dieron el resultado esperado; los detalles y hashes de los fixtures están en [CASO_URGENCIA_RESULTADOS.json](CASO_URGENCIA_RESULTADOS.json).

## Qué demuestra

La regla encuentra una palabra de urgencia aunque el escenario sea benigno. Si alguien convirtiera esa señal en el veredicto «es phishing», produciría un falso positivo respecto de la etiqueta de este ejercicio. El analizador sólo emite señales y no realiza esa clasificación.

Esta pareja sintética permite observar el efecto de un cambio controlado. No permite estimar una tasa de falsos positivos, la precisión de detección en correos reales ni la calidad general de un modelo. El control con cero hallazgos tampoco demuestra seguridad.

Los dominios coincidentes, el texto que afirma ser un aviso autorizado o la ausencia de adjuntos no prueban autenticidad en un correo real. En una revisión real habría que contrastar el contexto por un canal conocido y examinar otras evidencias pertinentes.

## Intercambio manual con IA

Se exportó la [solicitud minimizada](../examples/solicitud_urgencia.json) y se entregó a un agente de esta sesión sin historial heredado. Recibió el paquete y las instrucciones de formato, sin herramientas. No recibió el correo, el asunto literal, sus dominios ni la etiqueta benigna del escenario.

El agente produjo una [respuesta nueva](../examples/respuesta_urgencia.json), que pasó la validación local de estructura y referencias. Indicó que la urgencia también aparece en mensajes legítimos y propuso revisar su justificación y confirmar el contexto por un canal independiente. No afirmó conocer la intención de este mensaje.

La validación no demuestra la verdad del texto. La revisión humana sigue siendo necesaria. El `request_id` se deriva de los hechos minimizados; otros correos que produzcan el mismo hallazgo y catálogo pueden compartirlo. No identifica este correo ni reemplaza su hash.

La generación ocurrió durante el intercambio manual de esta sesión. El programa no llamó a una API. Las ejecuciones con el JSON publicado importan la respuesta guardada, sin generar otra. La [salida conservada](CASO_URGENCIA_SALIDA.txt) muestra ese modo de reproducción.

## Reproducir en Windows

Desde la carpeta del proyecto:

```powershell
py -3 phishing_analyzer.py examples\aviso_legitimo_urgente.eml
py -3 phishing_analyzer.py examples\aviso_legitimo_sin_urgencia.eml
py -3 phishing_analyzer.py examples\aviso_legitimo_urgente.eml --ai-response examples\respuesta_urgencia.json
py -3 evals\urgency_context.py
```

Para obtener otra explicación mediante el asistente, abrí `modo_manual.cmd`, elegí 1 e indicá `examples\aviso_legitimo_urgente.eml`. Copiá el texto preparado a la herramienta de chat elegida, guardá su JSON y validalo con la opción 2 usando ese mismo correo.

## Ejercicio de interpretación

Identificá qué palabra activa la regla y qué evidencia adicional necesitarías para evaluar la intención. Explicá después qué parte resuelve el código, qué parte redacta la IA y qué parte exige tu revisión.
