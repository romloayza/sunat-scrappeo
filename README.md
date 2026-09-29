# Base de datos de contrataciones públicas empresa–GORE

La base principal del proyecto es:

`data/data_final.csv`

Cada fila representa una contratación o proyecto correspondiente a los años 2021, 2022 o 2024.

La estructura general es:

`id | gore | monto | fecha | ruc1 | ruc2 | ... | ruc9`

Cada columna `ruc1` a `ruc9` contiene un objeto JSON con información de la empresa participante y sus métricas de red.

## Diccionario de datos

### Variables del proyecto

| Variable | Descripción |
|---|---|
| `id` | Identificador único del proyecto. |
| `gore` | Gobierno Regional asociado a la contratación. |
| `monto` | Monto total registrado para el proyecto. Si participan varias empresas, no se conoce qué proporción corresponde a cada una. |
| `fecha` | Fecha de la contratación. |
| `ruc1` – `ruc9` | Empresas participantes en el proyecto. Cada celda contiene un objeto JSON con los atributos de la empresa. |

### Variables dentro de cada RUC

| Variable | Descripción |
|---|---|
| `ruc` | Registro Único de Contribuyentes de la empresa. Funciona como identificador. |
| `antiguedad_empresa` | Número de años entre el inicio de actividades registrado en SUNAT y el año de la contratación. |
| `cmc` | Capacidad Máxima de Contratación registrada para la empresa. |
| `cantidad_rubros` | Cantidad de actividades económicas registradas para la empresa en SUNAT. |
| `actividad_principal` | Actividad económica principal registrada en SUNAT. |
| `penalidades_acum` | Número acumulado de penalidades registrado para la empresa. No se dispone de la fecha individual de cada penalidad. |
| `sanciones_tcp_acum` | Número acumulado de sanciones registrado para la empresa. No se dispone de la fecha individual de cada sanción. |
| `estado` | Estado del contribuyente registrado en SUNAT al momento de la consulta. |
| `condicion` | Condición del contribuyente registrada en SUNAT al momento de la consulta. |
| `degree_centrality` | Centralidad de grado normalizada de la empresa en la red empresa–GORE del año. Mide la proporción de GORE presentes en la red anual con los que la empresa está conectada. |
| `weighted_degree` | Número total de participaciones contractuales de la empresa durante el año. Considera la repetición de contratos con un mismo GORE. |
| `closeness_centrality` | Centralidad de cercanía de la empresa en la red anual. Mide su cercanía estructural respecto de los demás nodos alcanzables de la red. |
| `hhi_gore` | Índice Herfindahl–Hirschman del GORE en el año. Mide la concentración de las participaciones contractuales entre sus empresas proveedoras. |
| `supplier_share_gore` | Mayor participación contractual de una empresa dentro del total de participaciones del GORE en ese año. |
| `dependencia_empresa_gore` | Proporción de las contrataciones anuales de la empresa que corresponden al GORE del proyecto. |
| `dependencia_gore_empresa` | Proporción de las participaciones contractuales del GORE que corresponden a esa empresa. |
| `duracion_vinculo` | Número de períodos observados —2021, 2022 y 2024— en los que aparece la relación entre la misma empresa y el mismo GORE. |
| `n_gores_atendidos` | Número de Gobiernos Regionales distintos con los que la empresa tuvo al menos una contratación considerando conjuntamente 2021, 2022 y 2024. |
