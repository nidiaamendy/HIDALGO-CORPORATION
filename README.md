# Reporte de Meta Ads · Hidalgo Tours

Reporte interactivo publicado con GitHub Pages: vista anual y un reporte por mes.

- `index.html`: la página publicada. Se genera, no se edita a mano.
- `data.json`: los datos por mes (totales, diario, campañas, plataformas, audiencia, países y creativos).
- `build/template.html`: el diseño del reporte.
- `build/build_data.py`: convierte las extracciones de Meta Ads en `data.json` y agrega o reemplaza los meses.
- `build/render.py`: genera `index.html` a partir de `data.json` y la plantilla.

## Actualizar un mes

```
python3 build/build_data.py RAW_DIR data.json
python3 build/render.py data.json build/template.html index.html
```

`RAW_DIR` contiene las respuestas de Meta Ads del mes. Los nombres de archivo de cada tipo están documentados al inicio de `build_data.py`.
Los hallazgos de un mes se pueden escribir a mano en `data.json` → `months["AAAA-MM"].findings`. Si no hay, el reporte los calcula solo.

## Mes en curso

El reporte se actualiza todos los días con el mes en curso hasta el día anterior. Ese mes se marca como parcial (`partial`), se compara contra los mismos días del mes anterior (`cmpPrev`, archivos `cmpacct_AAAA-MM.json` y `cmpcamps_AAAA-MM.json`) y muestra una sección con el rendimiento del último día frente al promedio de los 7 días anteriores. Cuando el mes se completa, la comparación vuelve a ser contra el mes anterior completo.
