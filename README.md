# CV Generator - Generador de PDFs

Este proyecto incluye un script automático para generar PDFs de tu CV usando RenderCV.

## Opciones para generar PDF

Tenés dos formas de usar el sistema:

### Opción 1: TUI Interactiva (Recomendada)

Interfaz visual en la terminal para seleccionar el CV con menú interactivo.

```bash
./cv_tui
```

```
┌─────────────────────────────────────┐
│  🎯 Seleccioná tu CV               │
├─────────────────────────────────────┤
│  > 1. Pablo_Gramajo_Analista...    │
│    2. Pablo_Gramajo_Front_CV       │
│    3. Pablo_Gramajo_Net_CV          │
│    4. Pablo_Gramajo_react_CV        │
├─────────────────────────────────────┤
│  Elegí una opción: [1/2/3/4]       │
└─────────────────────────────────────┘
```

### Opción 2: Script rápido (sin TUI)

Ejecución directa con argumento numérico.

```bash
./cv [número]
```

**Ejemplos:**
```bash
./cv 1      # Genera el CV #1
./cv 2      # Genera el CV #2
./cv 3      # Genera el CV #3
```

## CVs disponibles actualmente

| # | Archivo YAML |
|---|--------------|
| 1 | Pablo_Gramajo_Analista_Automatizacion_Sr.yaml |
| 2 | Pablo_Gramajo_Front_CV.yaml |
| 3 | Pablo_Gramajo_Net_CV.yaml |
| 4 | Pablo_Gramajo_react_CV.yaml |

## Sin argumento

Si ejecutas `./cv` sin número, verás la lista de CVs disponibles:

```bash
./cv
```

```
📄 Seleccioná el CV a generar:

  1) Pablo_Gramajo_Analista_Automatizacion_Sr
  2) Pablo_Gramajo_Front_CV
  3) Pablo_Gramajo_Net_CV
  4) Pablo_Gramajo_react_CV

Usage: ./cv [número]
  ej: ./cv 2
```

## Agregar un nuevo CV

1. Crear un nuevo archivo `.yaml` en la raíz del proyecto
2. El script lo detectará automáticamente

## Método manual (alternativo)

Si preferís el método tradicional, seguí estos pasos:

### 1. Activar el entorno virtual

```bash
source .venv/bin/activate
```

### 2. Generar el PDF

```bash
rendercv render NOMBRE_DEL_CV.yaml
```

### 3. Abrir el PDF

```bash
open rendercv_output/
```

### 4. Salir del entorno virtual

```bash
deactivate
```

---

# RenderCV - Documentación original

## ¿Tengo que instalar RenderCV cada vez?

**No.**  
Solo se instala **una vez** dentro del entorno virtual.

Mientras no borres la carpeta `.venv`, ya queda listo para reutilizar.

---

## Si algún día falla `rendercv`

Reinstalar dentro del entorno:

```bash
source .venv/bin/activate
pip install "rendercv[full]"
```

---

## Nota

No borrar esta carpeta:

```bash
.venv
```

porque ahí está instalado RenderCV.