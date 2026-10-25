# Demostración del laboratorio en tres minutos

Este laboratorio educativo en Python fue preparado con asistencia de IA. El recorrido permite mostrar qué detectan sus reglas, cómo se validan explicaciones guardadas y qué límites necesitan revisión humana.

## Ejecutar en Windows

Abrí **`demo_portfolio.cmd` con doble clic** desde la carpeta del proyecto. También podés ejecutar:

```powershell
py -3 demo_portfolio.py
```

Necesitás Python 3.10 o posterior. El recorrido no usa una API ni requiere paquetes externos. Guarda el resumen local en `reports/demo_portfolio/RESUMEN.md` y los datos en `reports/demo_portfolio/resultados.json`. Esa carpeta queda fuera de Git.

El [registro público de referencia](RESULTADOS_RECORRIDO.json) conserva una ejecución con los ejemplos ficticios publicados. Al repetir el comando, revisá el resultado de cada comprobación en tu propia copia.

## Cinco casos para comparar

| Caso ficticio | Hallazgos esperados | Qué mostrar |
|---|---:|---|
| [Correo normal](../examples/normal.eml) | 0 | Las reglas de esta versión no encuentran señales. |
| [Enlace con `@`](../examples/revision_enlace.eml) | 1 | El texto anterior a `@` debe distinguirse del host real. |
| [Varias señales](../examples/sospechoso.eml) | 7 | Encabezados, urgencia, enlaces y nombre de adjunto; seis reglas distintas. |
| [Aviso autorizado con urgencia](../examples/aviso_legitimo_urgente.eml) | 1 | La palabra «URGENTE» activa una regla en un escenario benigno. |
| [Control con «Aviso»](../examples/aviso_legitimo_sin_urgencia.eml) | 0 | Cambiar sólo ese prefijo del asunto elimina aquella señal. |

El recorrido comprueba las referencias de las respuestas guardadas para los casos con hallazgos, compara las dos variantes del aviso y prueba el rechazo de una referencia inexistente, `F999`.

## Guion para acompañar la pantalla

**Primer minuto:** ejecutá el recorrido y mostrale a otra persona los casos de cero y un hallazgo.

> Preparé este laboratorio con asistencia de IA para practicar análisis y evaluación. El código encuentra señales mediante reglas y conserva sus evidencias. En el enlace con `@`, por ejemplo, hay que identificar el host real y distinguirlo del texto que aparece antes.

**Segundo minuto:** abrí el caso con siete hallazgos y una explicación guardada.

> La IA recibe identificadores y observaciones de un catálogo fijo, sin el cuerpo, las direcciones ni los enlaces del correo. Ayuda a redactar explicaciones y comprobaciones manuales. El validador comprueba estructura y referencias; la verdad de cada frase sigue necesitando revisión.

**Tercer minuto:** compará el aviso con «URGENTE» y el control con «Aviso».

> Este aviso es benigno por construcción del ejercicio y aun así activa una regla. Interpretar esa señal como un veredicto de phishing produciría un falso positivo en este caso. Por eso documento los resultados y también lo que permiten concluir.

## Límites para explicar con claridad

Reproducir los JSON guardados no genera respuestas nuevas ni mide el desempeño de una IA. Su procedencia se documenta en [la demo original](PROVENIENCIA_IA.md), [el intercambio manual del enlace](PRUEBA_MANUAL_IA.md) y [el caso de urgencia](CASO_URGENCIA_BENIGNA.md).

Cero hallazgos no garantiza seguridad. El analizador no emite un veredicto de phishing ni calcula un puntaje. Estos cinco ejemplos tampoco permiten calcular tasas de falsos positivos o precisión con correos reales. No se verifican SPF, DKIM ni DMARC.

## Tres preguntas para practicar

1. ¿Qué evidencia produjo el código y qué texto añadió la IA?
2. ¿Por qué hay siete hallazgos de seis reglas distintas en el caso con varias señales?
3. ¿Qué información adicional necesitarías antes de concluir que el aviso con urgencia es malicioso?
