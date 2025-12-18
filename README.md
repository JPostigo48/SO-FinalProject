# Aplicación de Planificación de CPU

Esta aplicación web permite simular dos algoritmos de planificación de CPU — **Round&nbsp;Robin** (RR) y **Shortest Remaining Time First** (SRTF) — utilizando procesos reales observados del sistema operativo Linux.

## Arquitectura

La aplicación está dividida en tres componentes principales:

1. **Backend web (Node.js + Express)**: se encarga de servir la interfaz web y de gestionar las peticiones del usuario. Al recibir una solicitud de simulación, invoca el motor de planificación en Python y espera la salida en formato JSON para renderizarla con plantillas EJS.

2. **Motor de planificación (Python)**: localizado en `python/simulate.py`, este script realiza dos tareas:
   - *Muestreo de procesos*: lee información de los procesos activos en `/proc`, descarta hilos del kernel (`kworker`, `rcu*` y `kthreadd`) y calcula una ráfaga observada (`burst_obs`) a partir de la diferencia en `utime + stime` entre dos lecturas separadas por un intervalo de 0.1 s. Sólo se consideran procesos con delta positivo.
   - *Simulación de algoritmos*: con la lista de tareas generada, simula Round&nbsp;Robin (con quantum configurable) y SRTF. Para cada algoritmo construye una línea de tiempo de ejecución, calcula métricas por proceso (tiempos de espera, respuesta, retorno, etc.) y métricas globales (promedio de espera, throughput, número de cambios de contexto, etc.).

3. **Frontend (EJS + TailwindCSS)**: el cliente web utiliza plantillas EJS para mostrar un tablero con los procesos de entrada, métricas y diagramas de Gantt. Tailwind se carga vía CDN para facilitar un diseño moderno. El usuario puede alternar entre las vistas de Round Robin y SRTF con un conmutador en la barra de navegación.

## Estructura de carpetas

```
scheduler-app/
├── package.json       # Dependencias y script de inicio
├── server.js          # Servidor Node/Express
├── README.md          # Este archivo
├── python/
│   └── simulate.py    # Motor de muestreo y simulación
├── views/             # Plantillas EJS
│   ├── layout.ejs
│   ├── index.ejs      # Página de entrada con formulario
│   └── results.ejs    # Panel con resultados
└── public/            # Archivos estáticos (no usados en este ejemplo)
```

## Requisitos

- **Node.js** (>= 14) y **npm** para ejecutar el servidor web.
- **Python 3** para ejecutar el motor de planificación.
- Un sistema Linux que exponga el pseudo‑sistema de archivos `/proc` (la aplicación no funcionará en Windows).

## Instalación y ejecución

1. Instale las dependencias de Node:
   ```bash
   npm install
   ```

2. Inicie el servidor:
   ```bash
   npm start
   ```
   El servidor se levantará en `http://localhost:3000`.

3. Abra un navegador y diríjase a `http://localhost:3000`. Introduzca la cantidad de procesos a muestrear y, opcionalmente, el quantum para Round Robin. Al enviar el formulario, el servidor invocará `python/simulate.py`, procesará los resultados y mostrará las tablas y diagramas correspondientes.

## Notas adicionales

- **Ráfagas observadas**: la aplicación utiliza una estimación de la ráfaga de CPU basada en el incremento de `utime + stime` durante un intervalo corto. Esto no refleja la ráfaga real del proceso, pero ofrece una base razonable para comparar los algoritmos.
- **Contexto educativo**: esta herramienta fue diseñada para fines de aprendizaje en un curso de Sistemas Operativos. No pretende reemplazar a herramientas profesionales de monitoreo.

## Licencia

Este proyecto se distribuye con fines académicos y puede ser reutilizado o modificado libremente.