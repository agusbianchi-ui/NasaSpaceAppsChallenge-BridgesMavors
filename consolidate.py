import os
import shutil

proyecto = r'D:\Nasa SpaceApps Challenge - Bridges Mavors'

print("=== CONSOLIDACION OPCION 1: WebApp como carpeta principal ===\n")

# 1. Crear estructura WebApp
print("1. Creando estructura base WebApp...")
os.makedirs(os.path.join(proyecto, 'WebApp'), exist_ok=True)
os.makedirs(os.path.join(proyecto, 'WebApp', 'frontend'), exist_ok=True)
os.makedirs(os.path.join(proyecto, 'WebApp', 'backend'), exist_ok=True)
print("   Estructura creada\n")

# 2. Mover frontend/src
print("2. Moviendo frontend/src...")
ops_frontend_src = os.path.join(proyecto, 'ops_mars-main', 'frontend', 'src')
webapp_frontend_dst = os.path.join(proyecto, 'WebApp', 'frontend')

if os.path.exists(ops_frontend_src):
    print("   - Listing items in src directory...")
    items = os.listdir(ops_frontend_src)
    print(f"   - Found {len(items)} items: {items[:15]}")
    
    for item in items:
        src = os.path.join(ops_frontend_src, item)
        dst = os.path.join(webapp_frontend_dst, item)
        print(f"     Processing: {item} (is_dir={os.path.isdir(src)})")
        
        if os.path.isdir(src):
            if item.lower() == 'node_modules':
                print(f"       - Skipping {item}/ (will be installed later)")
                continue
            if os.path.exists(dst):
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            print(f"       - Moved {item}/")
        elif os.path.isfile(src):
            # It's a file, copy it
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)
            print(f"       - Moved {item} (file)")
        else:
            print(f"       - Skipping {item} (not a file or directory)")
    
    # Mover package.json, package-lock.json, vite.config.ts desde la raíz de frontend
    print("   - Moving frontend configuration...")
    for f in ['package.json', 'package-lock.json', 'vite.config.ts']:
        src = os.path.join(proyecto, 'ops_mars-main', 'frontend', f)
        dst = os.path.join(webapp_frontend_dst, f)
        if os.path.exists(src):
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)
            print(f"       - Moved {f}")
else:
    print("   - ops_mars-main/frontend/src not found")

# 3. Mover backend/app
print("\n3. Moviendo backend/app...")
ops_backend_src = os.path.join(proyecto, 'ops_mars-main', 'backend', 'app')
webapp_backend_dst = os.path.join(proyecto, 'WebApp', 'backend')

if os.path.exists(ops_backend_src):
    for root, dirs, files in os.walk(ops_backend_src):
        rel_path = os.path.relpath(root, ops_backend_src)
        dst_root = os.path.join(webapp_backend_dst, rel_path)
        os.makedirs(dst_root, exist_ok=True)
        
        for f in files:
            src_file = os.path.join(root, f)
            # Solo .py y .json, no __pycache__ ni archivos deep .venv
            if f.endswith(('.py', '.json')) and not f.startswith('__'):
                dst_file = os.path.join(dst_root, f)
                shutil.copy2(src_file, dst_file)
    print("   - backend/app moved\n")
else:
    print("   - ops_mars-main/backend/app not found\n")

# 4. Mover archivos esenciales del backend (main.py, etc.)
print("4. Moviendo archivos esenciales del backend...")
for f in ['main.py', 'requirements.txt']:
    src = os.path.join(proyecto, 'ops_mars-main', 'backend', f)
    dst = os.path.join(webapp_backend_dst, f)
    if os.path.exists(src):
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copy2(src, dst)
        print(f"   - Moved {f}")

# 5. Mover configuración importante
print("\n5. Moving additional configuration...")
# .env.example
for f in ['.env.example']:
    src = os.path.join(proyecto, 'ops_mars-main', 'backend', f)
    dst = os.path.join(proyecto, 'WebApp', 'backend', f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"   - Moved {f}")

# 6. Mover lo que sobra de ops_mars-main a recursosU
print("\n6. Moving excess to recursosU...")
# node_modules del frontend
ops_node = os.path.join(proyecto, 'ops_mars-main', 'frontend', 'node_modules')
recursosU_node = os.path.join(proyecto, 'recursosU', 'node_modules')
if os.path.exists(ops_node):
    if os.path.exists(recursosU_node):
        shutil.rmtree(recursosU_node, ignore_errors=True)
    shutil.copytree(ops_node, recursosU_node)
    print("   - node_modules moved to recursosU/")

# dist y public del frontend
ops_dist = os.path.join(proyecto, 'ops_mars-main', 'frontend', 'dist')
recursosU_dist = os.path.join(proyecto, 'recursosU', 'dist')
if os.path.exists(ops_dist):
    if os.path.exists(recursosU_dist):
        shutil.rmtree(recursosU_dist, ignore_errors=True)
    shutil.copytree(ops_dist, recursosU_dist)
    print("   - dist/ moved to recursosU/")

ops_public = os.path.join(proyecto, 'ops_mars-main', 'frontend', 'public')
recursosU_public = os.path.join(proyecto, 'recursosU', 'public')
if os.path.exists(ops_public):
    if os.path.exists(recursosU_public):
        shutil.rmtree(recursosU_public, ignore_errors=True)
    shutil.copytree(ops_public, recursosU_public)
    print("   - public/ moved to recursosU/")

# 7. Verificar estado final
print("\n7. Verifying final state...")

print("\nWebApp/frontend/:")
code_count = 0
for root, dirs, files in os.walk(os.path.join(proyecto, 'WebApp', 'frontend')):
    depth = root.replace(os.path.join(proyecto, 'WebApp', 'frontend'), '').count(os.sep)
    if depth == 0:
        print(f"   Root: {len(os.listdir(root))} items")
    elif depth == 1:
        code_files = [f for f in files if f.endswith(('.py', '.js', '.jsx', '.css', '.json'))]
        code_count += len(code_files)
        if code_files:
            print(f"   {os.path.basename(root)}/: {len(code_files)} code files")
    elif depth == 2:
        code_files = [f for f in files if f.endswith(('.js', '.jsx', '.css'))]
        if code_files:
            print(f"   {os.path.basename(root)}/: {len(code_files)} js/css files")

print(f"\nTotal code files in WebApp/frontend: {code_count}")

print("\nWebApp/backend/:")
py_count = 0
for root, dirs, files in os.walk(os.path.join(proyecto, 'WebApp', 'backend')):
    depth = root.replace(os.path.join(proyecto, 'WebApp', 'backend'), '').count(os.sep)
    if depth <= 1:
        py_files = [f for f in files if f.endswith('.py') and not f.startswith('__')]
        py_count += len(py_files)
        print(f"   {os.path.basename(root) if depth == 1 else 'Root'}: {len(py_files)} .py files")

print(f"\nTotal .py files in WebApp/backend: {py_count}")

print("\nrecursosU/ tiene:")
recursosU_total = sum(len(files) for _, _, files in os.walk(os.path.join(proyecto, 'recursosU')))
print(f"   {recursosU_total} items totales")

print("\nops_mars-main/ status:")
if os.path.exists(os.path.join(proyecto, 'ops_mars-main')):
    # Contar items restantes
    remaining = 0
    for root, dirs, files in os.walk(os.path.join(proyecto, 'ops_mars-main')):
        remaining += len(dirs) + len(files)
    print(f"   Still has {remaining} items (minimal structure)")
    # Remover node_modules, dist, public del frontend
    for removable in ['frontend/node_modules', 'frontend/dist', 'frontend/public']:
        path = os.path.join(proyecto, 'ops_mars-main', removable)
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
            print(f"   - Removed {removable}")
else:
    print("   No existe (consolidado completamente)")

print("\n=== CONSOLIDACION COMPLETADA ===")
print("\nWebApp/ ahora es la carpeta principal para ejecutar la webapp")
print("  - WebApp/frontend/ tiene el source code React")
print("  - WebApp/backend/ tiene el código FastAPI")
print("  - recursosU/ tiene todos los datos auxiliares, docs, GLB, scripts")
print("  - ops_mars-main/ tiene estructura reducida (opcional)")
print("\nPara ejecutar:")
print("  1. cd WebApp/frontend && npm run dev  (puerto 5173)")
print("  2. cd WebApp/backend && uvicorn app.main:app --port 8000")
print("  3. Abrir http://localhost:5173")