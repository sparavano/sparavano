# Evaluación offline del contrato IA

Fecha: 2026-10-25.

Las respuestas son fixtures sintéticas escritas a mano. No hubo inferencia real ni llamadas a una API.

Comprobaciones de contrato: **27/27** cumplen el comportamiento esperado; **0** fallan.

Este resultado cubre sólo estos casos. No es una medida de detección de phishing ni un benchmark de un modelo.

## Casos de contrato

| Caso | Descripción | Esperado | Observado |
|---|---|---|---|
| `valid_structure` | Respuesta completa con referencias válidas. | accepted | accepted |
| `valid_reordered` | Referencias válidas recibidas en otro orden. | accepted | accepted |
| `wrong_request` | Respuesta vinculada a otra solicitud. | rejected | rejected |
| `extra_root_field` | Campo adicional fuera del contrato. | rejected | rejected |
| `missing_root_field` | Campo obligatorio ausente. | rejected | rejected |
| `review_disabled` | Se intenta eliminar la revisión humana. | rejected | rejected |
| `review_not_boolean` | Revisión humana con tipo numérico. | rejected | rejected |
| `missing_finding` | Falta una explicación requerida. | rejected | rejected |
| `unknown_finding` | Referencia a un identificador inexistente. | rejected | rejected |
| `duplicate_finding` | Identificador repetido en lugar de cubrir otro hallazgo. | rejected | rejected |
| `wrong_rule` | Regla que no corresponde al identificador. | rejected | rejected |
| `extra_item_field` | Campo adicional dentro de una explicación. | rejected | rejected |
| `short_explanation` | Explicación por debajo de la longitud mínima. | rejected | rejected |
| `long_explanation` | Explicación que excede la longitud máxima. | rejected | rejected |
| `wrong_text_type` | Explicación con tipo no textual. | rejected | rejected |
| `missing_manual_checks` | Lista de comprobaciones manuales vacía. | rejected | rejected |
| `too_many_manual_checks` | Cantidad excesiva de comprobaciones. | rejected | rejected |
| `control_character` | Carácter de control en la explicación. | rejected | rejected |
| `hidden_format` | Carácter de formato oculto en la explicación. | rejected | rejected |
| `new_url` | URL añadida en la prosa de respuesta. | rejected | rejected |
| `new_email` | Dirección de correo añadida en una comprobación. | rejected | rejected |
| `new_ip` | Dirección IP añadida en la prosa de respuesta. | rejected | rejected |
| `empty_valid` | Sin hallazgos y sin explicaciones. | accepted | accepted |
| `empty_invented` | Sin hallazgos pero con una explicación añadida. | rejected | rejected |
| `minimization` | Metadatos y texto de origen no pasan al bundle. | omitted | omitted |
| `unknown_source_rule` | El bundle rechaza reglas ajenas al catálogo. | rejected | rejected |
| `duplicate_json_keys` | El importador rechaza claves JSON repetidas. | rejected | rejected |

## Control separado del límite semántico

Una respuesta afirma falsamente que una comprobación de autenticación falló, aunque sólo se proporcionaron observaciones de reglas y no se verificó autenticación.

Resultado del validador: **accepted**. La respuesta conserva el contrato y las referencias. Este caso documenta una falsedad no detectada; no se cuenta como un fallo de implementación ni como una explicación correcta.

El validador comprueba estructura, cobertura y referencias. No demuestra que cada frase esté sustentada, ni elimina las alucinaciones. La revisión humana sigue siendo necesaria.

## Trazabilidad y límites

Identificador de la solicitud sintética: `28b72caa48b54c630ef814d11789ce74754bdb53c51cd632dec2110959ec6bd2`. Se deriva de hechos minimizados del contrato, no de bytes ni metadatos de un correo.

`live_api_tested=false`; `semantic_truth_verified=false`. No se exportan cuerpos, cabeceras, evidencias ni hashes de correos. Los indicadores nuevos se prueban en formatos expresamente cubiertos; sus ofuscaciones posibles no están cubiertas de forma universal.

Reproducir desde la raíz del proyecto: `python evals/offline_suite.py`.
