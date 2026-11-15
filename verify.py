import os

proyecto = r'D:\Nasa SpaceApps Challenge - Bridges Mavors'

print("=== VERIFICACION FINAL DE ESTRUCTURA ===\n")

# WebApp structure
print("1. WebApp/ structure:")
for item in sorted(os.listdir(os.path.join(proyecto, 'WebApp'))):
    full = os.path.join(proyecto, 'WebApp', item)
    if os.path.isdir(full):
        count = sum(len(files) for _, _, files in os.walk(full))
        print(f"   {item}/: {count} items")
    else:
        size = os.path.getsize(full)
        print(f"   {item} ({size} bytes)")

print("\n2. WebApp/frontend/src key files:")
frontend_src = os.path.join(proyecto, 'WebApp', 'frontend', 'src')
if os.path.exists(frontend_src):
    key_files = [f for f in os.listdir(frontend_src) if f.endswith(('.jsx', '.js', '.css', '.json'))]
    print(f"   {len(frontend_src)} has: {key_files}")

# Check backend
print("\n3. WebApp/backend key files:")
backend_app = os.path.join(proyecto, 'WebApp', 'backend', 'app')
if os.path.exists(backend_app):
    py_files = [f for f in os.listdir(backend_app) if f.endswith('.py')]
    print(f"   {len(py_files)} .py files: {py_files}")

# Check recursosU
print("\n4. recursosU/ key directories:")
for d in ['data', 'docs', 'scripts', 'tools']:
    path = os.path.join(proyecto, 'recursosU', d)
    if os.path.exists(path):
        count = sum(len(files) for _, _, files in os.walk(path))
        print(f"   {d}/: {count} items")

# Check ops_mars-main reduced
print("\n5. ops_mars-main/ (reduced):")
om = os.path.join(proyecto, 'ops_mars-main')
if os.path.exists(om):
    for check in ['frontend/node_modules', 'frontend/dist', 'frontend/public']:
        path = os.path.join(om, check)
        print(f"   {check}: {'EXISTS' if os.path.exists(path) else 'REMOVED'}")

print("\n=== ESTRUCTURA CORRECTA ===")
print("WebApp/ = carpeta principal de la webapp")
print("WebApp/frontend/ = source code React (src/, package.json, vite.config.ts)")
print("WebApp/backend/ = codigo FastAPI (main.py, services/, api/v1/)")
print("recursosU/ = datos auxiliares, docs, GLB, scripts, stages")
print("ops_mars-main/ = estructura reducida (node_modules, dist, public removidos)")

# Execution instructions
print("\n=== INSTRUCCIONES PARA EJECUTAR ===")
print("1. Backend:")
print(f"   cd {proyecto}\\WebApp\\backend")
print(f"   .venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000")
print("   -> Puerto 8000")

print("\n2. Frontend:")
print(f"   cd {proyecto}\\WebApp\\frontend")
print("   npm run dev")
print("   -> Puerto 5173")

print("\n3. Acceder:")
print("   http://localhost:5173")
print("\nEndpoints clave disponibles:")
print("  GET /api/v1/terrain/metadata")
print("  GET /api/v1/terrain/point?x=0&z=0&mars_year=36&sol=1")
print("  POST /api/v1/plan/route (Etapa 6)")
print("  GET /api/v1/plan/strategies (Etapa 6)")
print("  GET /api/v1/science/variables")
print("  GET /api/v1/mission/scenarios")