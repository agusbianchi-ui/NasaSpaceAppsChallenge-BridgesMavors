import os
import shutil

proyecto = r'D:\Nasa SpaceApps Challenge - Bridges Mavors'

# Limpiar carpetas destino si existen
for carpetas in ['WebApp', 'recursosU']:
    ruta = os.path.join(proyecto, carpetas)
    if os.path.exists(ruta):
        shutil.rmtree(ruta, ignore_errors=True)
        print("Limpieza:" + carpetas + " removida")

os.makedirs(os.path.join(proyecto, 'WebApp'), exist_ok=True)
os.makedirs(os.path.join(proyecto, 'recursosU'), exist_ok=True)

print("=== ORGANIZACIÓN DEL PROYECTO ===\n")

# 1. Mover estructura WEBAPP
# frontend/src/
frontend_src = os.path.join(proyecto, 'ops_mars-main', 'frontend', 'src')
dest_frontend = os.path.join(proyecto, 'WebApp', 'frontend')
os.makedirs(dest_frontend, exist_ok=True)

if os.path.exists(frontend_src):
    for item in os.listdir(frontend_src):
        src_item = os.path.join(frontend_src, item)
        dst_item = os.path.join(dest_frontend, item)
        if os.path.isdir(src_item):
            # Usar dirs_exist_ok=True para Python 3.8+
            shutil.copytree(src_item, dst_item, 
                          ignore=shutil.ignore_patterns('node_modules'),
                          dirs_exist_ok=True)
            print("frontend/src/" + item + " -> WebApp/frontend/")
        elif os.path.isfile(src_item):
            shutil.copy2(src_item, dst_item)
            print("frontend/src/" + item + " -> WebApp/frontend/")
    # Mover package.json y vite.config.ts
    for f in ['package.json', 'package-lock.json', 'vite.config.ts']:
        src = os.path.join(proyecto, 'ops_mars-main', 'frontend', f)
        dst = os.path.join(dest_frontend, f)
        if os.path.exists(src):
            # Si el archivo ya existe, reemplazarlo
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copy2(src, dst)
            print(f + " -> WebApp/frontend/")

# backend/app/
backend_src = os.path.join(proyecto, 'ops_mars-main', 'backend', 'app')
dest_backend = os.path.join(proyecto, 'WebApp', 'backend')
os.makedirs(dest_backend, exist_ok=True)

if os.path.exists(backend_src):
    for root, dirs, files in os.walk(backend_src):
        rel_path = os.path.relpath(root, backend_src)
        dest_root = os.path.join(dest_backend, rel_path)
        os.makedirs(dest_root, exist_ok=True)
        for f in files:
            src_file = os.path.join(root, f)
            # Solo .py y .json esenciales, no .venv ni __pycache__
            if f.endswith(('.py', '.json')) and not f.startswith('__') and '.venv' not in rel_path:
                dst_file = os.path.join(dest_root, f)
                shutil.copy2(src_file, dst_file)
                print("" + os.path.relpath(src_file, backend_src) + " -> WebApp/backend/")

# Mover archivos de raíz del backend principales
for f in ['main.py']:
    src = os.path.join(proyecto, 'ops_mars-main', 'backend', f)
    dst = os.path.join(dest_backend, f)
    if os.path.exists(src):
        if os.path.exists(dst):
            os.remove(dst)
        shutil.copy2(src, dst)
        print(f + " -> WebApp/backend/")

print()

# 2. Mover lo que NO es webapp a recursosU
# output-stage*
for stage in ['stage1', 'stage2', 'stage3', 'stage4']:
    src = os.path.join(proyecto, 'output-stage' + stage)
    dst = os.path.join(proyecto, 'recursosU', 'output-stage' + stage)
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst)
        print("output-stage" + stage + " -> recursosU/")

# data/raw/
src = os.path.join(proyecto, 'data', 'raw')
if os.path.exists(src):
    dst = os.path.join(proyecto, 'recursosU', 'data', 'raw')
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
            os.remove(src_item)
    print("data/raw -> recursosU/")

# data/science/
src = os.path.join(proyecto, 'data', 'science')
if os.path.exists(src):
    dst = os.path.join(proyecto, 'recursosU', 'data', 'science')
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
            os.remove(src_item)
    print("data/science -> recursosU/")

# docs/
src = os.path.join(proyecto, 'docs')
if os.path.exists(src):
    dst = os.path.join(proyecto, 'recursosU', 'docs')
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
            os.remove(src_item)
    print("docs -> recursosU/")

# scripts/
src = os.path.join(proyecto, 'scripts')
if os.path.exists(src):
    dst = os.path.join(proyecto, 'recursosU', 'scripts')
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
            os.remove(src_item)
    print("scripts -> recursosU/")

# tools/
src = os.path.join(proyecto, 'tools')
if os.path.exists(src):
    dst = os.path.join(proyecto, 'recursosU', 'tools')
    os.makedirs(dst, exist_ok=True)
    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)
        if os.path.isdir(src_item):
            if os.path.exists(dst_item):
                shutil.rmtree(dst_item, ignore_errors=True)
            shutil.copytree(src_item, dst_item)
        else:
            shutil.copy2(src_item, dst_item)
            os.remove(src_item)
    print("tools -> recursosU/")

# Archivos en raíz del proyecto (excepto los que ya fueron movidos)
archivos_raiz = ['AGENTS.md', 'SOURCES.md', 'IMPLEMENTATION_STATUS.md', 
                 'PROJECT_SPEC.md', 'SCIENTIFIC_LIMITATIONS.md', 
                 'DATA_DICTIONARY.md', 'DESIGN_GUIDELINES.md',
                 'README.md', 'VALIDATION.md']
for f in archivos_raiz:
    src = os.path.join(proyecto, f)
    dst = os.path.join(proyecto, 'recursosU', f)
    if os.path.exists(src):
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(src, dst)
        print(f + " -> recursosU/")

# Archivos .glb, .blend, .zip en raíz
for f in os.listdir(proyecto):
    if f.endswith(('.glb', '.blend', '.zip')):
        src = os.path.join(proyecto, f)
        dst = os.path.join(proyecto, 'recursosU', f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.move(src, dst)
            print(f + " -> recursosU/")

print()
print("=== ORGANIZACIÓN COMPLETADA ===")

# Verificar estructura
print("\n--- ESTRUCTURA WebApp ---")
webapp_dir = os.path.join(proyecto, 'WebApp')
for root, dirs, files in os.walk(webapp_dir):
    depth = root.replace(webapp_dir, '').count(os.sep)
    prefix = "  " * depth
    for d in dirs:
        print(prefix + d + "/")
    file_count = min(len(files), 5)
    for i in range(file_count):
        prefix2 = "  " * (depth + 1)
        print(prefix2 + files[i])
    if len(files) > 5:
        print(prefix2 + "...(otros " + str(len(files) - 5) + " files)")
    if depth > 4:
        break

print("\n--- ESTRUCTURA recursosU ---")
recursosU_dir = os.path.join(proyecto, 'recursosU')
for root, dirs, files in os.walk(recursosU_dir):
    depth = root.replace(recursosU_dir, '').count(os.sep)
    prefix = "  " * depth
    for d in dirs:
        print(prefix + d + "/")
    file_count = min(len(files), 5)
    for i in range(file_count):
        prefix2 = "  " * (depth + 1)
        print(prefix2 + files[i])
    if len(files) > 5:
        print(prefix2 + "...(otros " + str(len(files) - 5) + " files)")
    if depth > 4:
        break