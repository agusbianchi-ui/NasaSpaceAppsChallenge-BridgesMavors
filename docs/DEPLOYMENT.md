# Despliegue: GitHub Pages y Render

La aplicación se publica desde la raíz del repositorio. No se han creado servicios ni publicado nada. El workflow publica automáticamente cada push a `main` una vez que Pages esté habilitado; también admite ejecución manual.

## 1. Preparar el repositorio

Esta copia no contiene metadatos Git. Creá o vinculá un repositorio Git y revisá los archivos antes de subirlos. Los datos necesarios ya existen localmente y `.gitignore` permite incluir únicamente los derivados de despliegue:

- `WebApp/frontend/public/terrain/`: manifiesto, 44 chunks GLB, altura visual, máscara y ruta preliminar. Si falta, ejecutá `npm run prepare:terrain` desde `WebApp/frontend` con `output-stage1` y `output-stage3` presentes.
- `output-stage4/`: metadatos, siete `.bin` y `dust-my36-region.npz` usados por la API.
- `data/additional-science/BridgesMavors_science_pack/numeric/`: cuatro TIFF de inercia térmica y calidad.

En esta copia esos conjuntos suman unos 136 MB; el archivo individual mayor es de unos 30 MB. No requieren almacenamiento externo según el límite de 100 MiB por archivo de GitHub. Incluí estos archivos en el commit junto con el código; no uses punteros Git LFS sin configurar también su descarga en ambos servicios. Verificá `git status` y no subas originales, entornos ni credenciales. Si los datos faltan, las compilaciones fallan explícitamente. Los activos del frontend son públicos, igual que el sitio.

## 2. Crear el backend

En Render conectá el repositorio y creá un Blueprint desde `render.yaml`. Elegí el plan y confirmá manualmente cualquier costo antes de crear el servicio. Cuando solicite `CORS_ORIGINS`, ingresá el origen exacto de Pages, por ejemplo `https://USUARIO.github.io` (sin ruta ni barra final). Para dominio propio usá su origen HTTPS; separá varios orígenes con comas. El servicio usa Python 3.14.3, escucha en `$PORT` y expone `/api/health`. Anotá la URL HTTPS del servicio, sin barra final. No definas Root Directory: se necesitan tanto `WebApp` como los datos de la raíz.

La API y las tareas quedan accesibles públicamente; CORS solo controla navegadores y no autentica usuarios. El almacenamiento local del servicio no es persistente entre despliegues o reinicios: no dependas de él para conservar tareas, archivos cargados ni resultados. El análisis eólico requiere imágenes locales adicionales, que no están incluidas. La disponibilidad y recursos de memoria dependen del plan elegido.

El asistente actual funciona con respuestas locales y no requiere credenciales de un proveedor de IA. Nunca pongas claves en `VITE_*`, archivos de frontend, commits o variables públicas de GitHub: si se integra un proveedor, configurá sus secretos exclusivamente en el entorno privado de Render y accedé desde el backend. Los archivos `.env` están ignorados.

## 3. Publicar el frontend

En GitHub, en Settings → Secrets and variables → Actions → Variables, creá `VITE_API_BASE_URL` con la URL HTTPS de Render, por ejemplo `https://mi-api.onrender.com`. Es una URL pública, no una clave. En Settings → Pages elegí **GitHub Actions** como fuente y subí los cambios a `main` o ejecutá el workflow manualmente desde Actions. Si tu rama principal tiene otro nombre, adaptá el workflow.

El workflow determina la base para `https://USUARIO.github.io/REPOSITORIO/` o el sitio raíz `USUARIO.github.io`; las rutas usan `/#/explorer`, etc., para permitir recargar enlaces en Pages. Con dominio personalizado o una ruta distinta, ajustá `VITE_BASE_PATH` en el workflow. Cada cambio de URL de API requiere reconstruir el frontend; cada cambio de origen requiere actualizar CORS en Render.

## 4. Comprobar

Abrí `https://TU-SERVICIO.onrender.com/api/health`, luego el enlace de Pages del workflow. Probá recargar `/#/explorer`, cargar el terreno 3D y la ruta preliminar, consultar un punto científico, calcular una ruta y consultar el asistente. Revisá también el tablero y los mosaicos NASA. En las herramientas del navegador verificá que no haya errores CORS ni solicitudes a localhost. Algunas funciones científicas requieren datos no incluidos y la aplicación debe informar su disponibilidad real.

Para ensayar localmente: desde `WebApp/frontend`, ejecutá `npm ci`, `node scripts/check-deploy-terrain.mjs` y `npm run build`. Desde la raíz ejecutá `python scripts/check-deploy-science.py`. Para producción local configurá `VITE_API_BASE_URL` y, si corresponde, `VITE_BASE_PATH` y `VITE_ROUTER_MODE=hash` antes de compilar. La compilación incorpora estas variables y no secretos.

Referencias: [Vite y Pages](https://vite.dev/guide/static-deploy), [GitHub Actions para Pages](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically), [Render Blueprint](https://render.com/docs/blueprint-spec) y [FastAPI en Render](https://render.com/docs/deploy-fastapi).
