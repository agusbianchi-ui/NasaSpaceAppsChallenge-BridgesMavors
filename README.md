# Bridges Mavors

**Bridges Mavors** es una plataforma interactiva para explorar el terreno marciano y apoyar la planificación de misiones hipotéticas en la región de Jezero. El proyecto combina mapas orbitales de la NASA, un modelo 3D del terreno, datos científicos y herramientas de análisis en una interfaz inspirada en un centro de control de misión.

[**Abrir la aplicación**](https://agusbianchi-ui.github.io/NasaSpaceAppsChallenge-BridgesMavors/) · [Documentación de la API](https://bridges-mavors-api.onrender.com/docs) · [Fuentes y atribuciones](SOURCES.md)

## ¿Qué permite hacer?

- **Explorar Marte en 2D:** consultar mosaicos orbitales y capas de Mars Trek, con sus metadatos y fuentes.
- **Recorrer el terreno en 3D:** navegar por un modelo voxelizado de la región, inspeccionar puntos y crear o importar una ruta de referencia.
- **Planificar rutas:** definir condiciones de misión, comparar alternativas calculadas con A*, visualizar perfiles de elevación y exportar o importar una misión en JSON.
- **Consultar información científica:** explorar elevación, pendiente, orientación, rugosidad y otras variables disponibles, junto con su procedencia y limitaciones. La inercia térmica aparente TES de día y noche está disponible para consultas por posición.
- **Analizar dinámica eólica:** consultar catálogos y ejecutar análisis de observaciones cuando se cuenta con imágenes, máscaras y metadatos locales adecuados.
- **Organizar una misión:** usar un tablero de tareas y un asistente que responde con información disponible del sistema.

Para probar el recorrido principal, abrí **Mars Explorer**, elegí **Load 3D terrain**, después **Import preliminary route**, **Use endpoints only** y **Calculate routes**. La carga inicial del modelo es progresiva y descarga aproximadamente 52 MiB.

## Datos y alcance

El mapa 2D consulta imágenes de NASA Mars Trek. El terreno científico utiliza un modelo de elevación HRSC/MOLA remuestreado a 250 m y sus derivados; la altura del modelo 3D tiene una exageración visual de 3×. La planificación utiliza las muestras científicas, no la altura visual exagerada. También se incluye un escenario histórico regional de polvo MY36 de resolución gruesa.

La telemetría, los eventos, el progreso de misión y algunos objetivos de la interfaz son **simulados**. Las condiciones y umbrales de planificación son hipótesis editables; el sistema no certifica la transitabilidad ni reemplaza la evaluación científica o de seguridad de una misión real. Cuando faltan datos, la aplicación los muestra como no disponibles.

El asistente actual usa respuestas deterministas basadas en información del sistema; no requiere una clave de IA. El módulo eólico no incluye un modelo predictivo entrenado y validado ni todas las imágenes necesarias para ejecutar análisis propios. Los resultados y las tareas del servidor se almacenan en memoria y pueden perderse al reiniciarse.

Consultá las [limitaciones científicas](docs/SCIENTIFIC_LIMITATIONS.md), el [diccionario de datos](docs/DATA_DICTIONARY.md) y las [fuentes](SOURCES.md) para conocer el alcance de cada producto.

## Tecnologías

- **Frontend:** React, Vite, React Router, Three.js y OpenLayers.
- **Backend:** Python, FastAPI y Uvicorn.
- **Análisis científico:** NumPy, SciPy, Rasterio y el paquete `mars_ml`.
- **Despliegue:** GitHub Pages para el frontend y Render para la API.

## Ejecutar el proyecto localmente

### Requisitos

- Node.js 22 y npm.
- Python 3.14 y Git.
- Los archivos de terreno y datos científicos incluidos en el repositorio. Si faltan, consultá la [guía de despliegue](docs/DEPLOYMENT.md).

### 1. Preparar y ejecutar la API

Desde la raíz del proyecto:

```bash
python -m venv .venv
```

Activá el entorno virtual y ejecutá:

```bash
python -m pip install -r WebApp/backend/requirements.txt
cd WebApp/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La API estará disponible en `http://127.0.0.1:8000` y su documentación interactiva en `http://127.0.0.1:8000/docs`.

### 2. Preparar y ejecutar el frontend

En otra terminal:

```bash
cd WebApp/frontend
npm ci
npm run dev
```

Abrí la dirección que indique Vite, normalmente `http://localhost:5173`. Por defecto, el frontend consulta la API local en el puerto 8000. Los ejemplos de configuración están en [`WebApp/frontend/.env.example`](WebApp/frontend/.env.example) y [`WebApp/backend/.env.example`](WebApp/backend/.env.example).

En Windows también podés usar `Start-BridgesMavors.ps1` desde la raíz para iniciar los servicios locales. El script sirve la última compilación del frontend; ejecutá `npm run build` en `WebApp/frontend` después de modificarlo.

## Estructura del repositorio

```text
WebApp/
├── frontend/          Interfaz, mapas, visor 3D y planificación
├── backend/           API, consultas científicas y servicios
└── mars_ml/           Herramientas de análisis e investigación eólica
data/                  Productos científicos adicionales
output-stage4/         Datos regionales derivados para consultas y rutas
docs/                  Arquitectura, fuentes, limitaciones y despliegue
recursosU/             Fuentes y materiales históricos del terreno
```

La aplicación activa está en `WebApp/`. Las carpetas `backend/` y `ops_mars-main/` de la raíz son copias históricas, no los servidores principales. Los scripts históricos `reorganize.py` y `consolidate.py` mueven o eliminan archivos y no son necesarios para ejecutar la aplicación.

## Verificación y despliegue

Desde `WebApp/frontend`:

```bash
npm run lint
npm run build
npm run test:terrain
```

Para ejecutar las pruebas del backend y de `mars_ml`, desde `WebApp/backend`, incluí `WebApp` y `WebApp/backend` en `PYTHONPATH` y ejecutá `python -m pytest tests ../mars_ml/tests -q`.

La aplicación publicada usa el plan gratuito de Render: el backend puede tardar en responder después de un período de inactividad. Para configurar otro despliegue, consultá [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). No incluyas credenciales en el código ni en variables `VITE_*`, que quedan expuestas en el frontend.
