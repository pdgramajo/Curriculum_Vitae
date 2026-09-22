# CV Generator — Generador de CVs con RenderCV

Un comando, una interfaz. `./cv` abre una TUI (Textual) donde elegís tu CV,
presionás Enter y obtenés el PDF listo para abrir. Todo lo que antes hacían
cuatro entry points diferentes — los scripts `cv`, `cv_tui`, `Generar
CV.command` y el launcher shell de respaldo — y un monolito (`cv_tui.py`)
ahora vive en un solo paquete Python: `src/cvapp/`.

## Uso

| Comando | Qué hace |
|---------|----------|
| `./cv` | Abre la TUI interactiva (igual que `./cv tui`) |
| `./cv list` | Lista los CVs disponibles, uno por línea, exit 0 |
| `./cv render <nombre>` | Genera el PDF de `<Nombre>.yaml` en `rendercv_output/`, imprime la ruta y sale con 0. No abre el PDF |
| `./cv version` | Muestra la versión de la aplicación (2.0.0) |
| `./cv <comando-inventado>` | Error de uso que nombra el subcomando, exit 2 |

Equivalencias:

- `.venv/bin/python3 -m cvapp <comando>` es idéntico a `./cv <comando>`
  (corré desde la raíz del proyecto).
- `cv_tui` es un alias de `cv`: `./cv_tui list` se comporta igual que
  `./cv list`, y `./cv_tui` sin argumentos abre la TUI.
- El script shell de respaldo (el que caminaba hacia arriba buscando `.venv`)
  fue **eliminado**: su función la cumple el launcher `cv`, que resuelve la
  raíz del proyecto desde su propia ubicación (funciona desde cualquier
  directorio).
- `Generar CV.command` (doble clic en Finder) delega en `cv` y, si algo
  falla, muestra el error y espera una tecla para que alcances a leerlo.

## Agregar un nuevo CV

1. Creá un archivo `.yaml` en la raíz del proyecto (o en el directorio
   configurado en `cvs_dir`).
2. La app lo detecta automáticamente: aparece en `./cv list` y en la TUI.

## Configuración opcional (`cvapp.yaml`)

Sin `cvapp.yaml`, la app se comporta exactamente como antes: CVs en la raíz,
PDFs en `rendercv_output/`, todo con valores por defecto. Si el archivo
existe, sus valores se combinan sobre los defaults (solo hace falta escribir
lo que cambia).

| Clave | Tipo | Default | Efecto |
|-------|------|---------|--------|
| `cvs_dir` | ruta | raíz del proyecto | Carpeta escaneada para YAMLs de CV (`*.yaml`/`*.yml`, no recursivo, sin dotfiles) |
| `output_dir` | ruta | `rendercv_output` | Carpeta donde se escriben los PDFs (y los intermedios transitorios) |
| `open_pdf_after` | booleano | `true` | Abrir el PDF tras un render exitoso en la TUI (solo macOS) |
| `cleanup_intermediate` | booleano | `true` | Borrar los intermedios de este render (`.typ`, copia de foto) sin tocar tus archivos |
| `rendercv_extra_flags` | lista | `[]` | Flags extra agregados al final del comando de rendercv |
| `timeout_seconds` | entero > 0 | `120` | Máximo de segundos por render |
| `log_level` | `DEBUG`/`INFO`/`WARNING`/`ERROR` | `INFO` | Verbosidad de `cvapp.log` |

Notas:

- Las rutas relativas (`cvs_dir`, `output_dir`) se resuelven contra la raíz
  del proyecto, nunca contra el directorio desde donde corrés el comando.
- Las claves desconocidas se ignoran (con warning en el log).
- `CVAPP_LOG_LEVEL=DEBUG ./cv list` — la variable de entorno gana sobre la
  clave `log_level` del archivo.
- Los errores de configuración fallan rápido con un mensaje claro que nombra
  el archivo y la clave; la traza completa siempre va a `cvapp.log`.

## Cambio de comportamiento (vs. la versión anterior)

- Salir de la TUI (`q` o `esc`) **ya no cierra la Terminal**: solo sale de la
  aplicación (antes se usaba `osascript` para cerrar la ventana, lo que podía
  cerrar tu terminal entera). El `Generar CV.command` queda esperando una
  tecla solo cuando hay un error, para que los usuarios de doble clic no se
  queden sin ver el mensaje.
- La limpieza de intermedios es segura por fotos: renderizar un CV no borra
  las fotos (`foto_*.png`) ni los archivos de otro CV.

## Desarrollo

| Comando | Qué hace |
|---------|----------|
| `make test` | Suite unitaria (`pytest -m "not smoke"`) |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` |
| `make check` | test + lint + format + pyright (todo en uno) |
| `pytest -m smoke` | Render real opt-in: RenderCV de verdad sobre una copia de un CV en un directorio temporal (nunca toca tus CVs ni `rendercv_output/`) |

`pytest` pelado (sin `-m`) también corre solo la suite unitaria: el smoke
queda excluido por configuración y se ejecuta únicamente con `pytest -m smoke`.

## Si algún día falla `rendercv`

Reinstalarlo dentro del entorno virtual:

```bash
.venv/bin/python3 -m pip install "rendercv[full]"
```

## Nota

No borrar `.venv`: ahí está instalado RenderCV y las dependencias de la app.
`rendercv-env/` es un entorno viejo que quedó en disco sin uso (gitignored);
no se referencia desde ningún lado.