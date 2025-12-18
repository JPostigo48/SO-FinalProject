# Aplicación de Planificación de CPU

Esta aplicación web permite simular dos algoritmos de planificación de CPU — **Round&nbsp;Robin** (RR) y **Shortest Remaining Time First** (SRTF) — utilizando procesos reales observados del sistema operativo Linux.

## Arquitectura

La aplicación está dividida en tres componentes principales:

1. **Backend web (Node.js + Express)**: se encarga de servir la interfaz web y de gestionar las peticiones del usuario. Al recibir una solicitud de simulación, invoca el motor de planificación en Python y espera la salida en formato JSON para renderizarla con plantillas EJS.

2. **Motor de planificación (Python)**: localizado en `python/simulate.py`, este script realiza dos tareas:
   - *Muestreo de procesos*: lee información de los procesos activos en `/proc`, descarta hilos del kernel (`kworker`, `rcu*` y `kthreadd`) y calcula una ráfaga observada (`burst_obs`) a partir de la diferencia en `utime + stime` entre dos lecturas separadas por un intervalo de 0.1 s. Sólo se consideran procesos con delta positivo.
   - *Simulación de algoritmos*: con la lista de tareas generada, simula Round&nbsp;Robin (con quantum configurable) y SRTF. Para cada algoritmo construye una línea de tiempo de ejecución, calcula métricas por proceso (tiempos de espera, respuesta, retorno, etc.) y métricas globales (promedio de espera, throughput, número de cambios de contexto, etc.).

3. **Frontend (EJS + TailwindCSS)**: el cliente web utiliza plantillas EJS para mostrar un tablero con los procesos de entrada, métricas y diagramas de Gantt. Tailwind se carga vía CDN para facilitar un diseño moderno. El usuario puede alternar entre las vistas de Round Robin y SRTF con un conmutador en la barra de navegación.

## Notas adicionales

- **Ráfagas observadas**: la aplicación utiliza una estimación de la ráfaga de CPU basada en el incremento de `utime + stime` durante un intervalo corto. Esto no refleja la ráfaga real del proceso, pero ofrece una base razonable para comparar los algoritmos.
- **Contexto educativo**: esta herramienta fue diseñada para fines de aprendizaje en un curso de Sistemas Operativos. No pretende reemplazar a herramientas profesionales de monitoreo.