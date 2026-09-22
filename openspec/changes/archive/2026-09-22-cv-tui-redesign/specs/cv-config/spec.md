# CV Configuration Specification

## Purpose

The `cv-config` capability defines how the application is configured: the optional `cvapp.yaml` file at the project root, its recognized keys with their defaults, the minimal validation that fails fast with clear messages, and the logging configuration. With no config file present, the application behaves exactly like the current project structure: CV sources live at the project root and PDFs go to `rendercv_output/`.

## Requirements

### Requirement: Optional config file is discovered at the project root

The system MUST look for `cvapp.yaml` at the project root, resolved from the launcher's own location (not from the caller's working directory). If the file is absent, all configuration defaults apply and the system behaves exactly like the current project (CVs discovered at the project root, PDFs written to `rendercv_output/`). If the file is present, its values MUST be merged over the defaults.

#### Scenario: Missing config uses defaults compatible with today's structure

- GIVEN a project without a `cvapp.yaml` file
- WHEN the application starts
- THEN CV sources are discovered at the project root and PDFs are written to `rendercv_output/`, exactly as the current project behaves

#### Scenario: Present config is merged over defaults

- GIVEN a `cvapp.yaml` at the project root that sets only `output_dir`
- WHEN the application starts
- THEN the configured output directory takes effect
- AND every other option keeps its documented default

#### Scenario: Config is found regardless of the working directory

- GIVEN a project with `cvapp.yaml` at its root
- WHEN the application is launched from a different working directory
- THEN the root config file is still loaded (no dependence on the caller's cwd)

### Requirement: Configuration options control behavior with documented defaults

The system MUST support the following optional keys. Every key has a documented default, so a config file needs to state only what differs. Each key MUST take effect on the corresponding behavior: the source directory for discovery, the output directory for PDFs, PDF opening, intermediate cleanup, extra RenderCV flags, render timeout, and log level.

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `cvs_dir` | string (path) | project root | Directory scanned for CV YAML sources |
| `output_dir` | string (path) | `rendercv_output` | Directory where generated PDFs are written |
| `open_pdf_after` | boolean | `true` | Open the PDF after a successful TUI render (macOS only) |
| `cleanup_intermediate` | boolean | `true` | Remove the render's intermediate files after a completed attempt |
| `rendercv_extra_flags` | list of strings | `[]` | Extra flags appended to the RenderCV invocation |
| `timeout_seconds` | number (seconds) | `120` | Maximum duration of a single render |
| `log_level` | string (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | Verbosity of the log file |

#### Scenario: Full config takes effect on every behavior

- GIVEN a `cvapp.yaml` that sets all seven keys to non-default values
- WHEN the application runs a render
- THEN discovery uses the configured source directory, the PDF lands in the configured output directory, the PDF opening, cleanup, extra flags, timeout, and log level all follow the configured values

#### Scenario: Partial config falls back to defaults for the rest

- GIVEN a `cvapp.yaml` that sets only `cvs_dir`
- WHEN the application runs
- THEN discovery uses the configured source directory
- AND all other options use their documented defaults

### Requirement: Config errors fail fast with clear messages

If `cvapp.yaml` exists but is malformed YAML, or a recognized key has an invalid value (for example `open_pdf_after: "si"` instead of a boolean), the system MUST report a clear error that names the file and the offending key or value, and MUST NOT proceed with rendering (headless commands exit non-zero; the TUI shows the error screen). Unknown keys MUST NOT break the application: they SHOULD be ignored (at most a log warning), so configs written for other versions remain compatible.

#### Scenario: Malformed YAML aborts with a clear error

- GIVEN a `cvapp.yaml` whose content is not valid YAML
- WHEN the application starts or a command runs
- THEN the user sees a clear error naming the file and the parse problem
- AND no rendering is attempted and headless commands exit non-zero

#### Scenario: Invalid value for a known key names the key

- GIVEN a `cvapp.yaml` with `open_pdf_after: "si"` (a string where a boolean is required)
- WHEN the application starts or a command runs
- THEN the user sees a clear error naming the offending key
- AND no rendering is attempted

#### Scenario: Unknown keys are ignored

- GIVEN a `cvapp.yaml` containing a key the application does not recognize (for example `futuro_ajuste`)
- WHEN the application starts
- THEN the application runs normally with the recognized keys applied and the unknown key ignored

### Requirement: Logging level is configurable and tracebacks land in a log file

The system MUST write log output to `cvapp.log` at the project root, in append mode. Errors MUST append the full traceback to the log file. The log level MUST default to `INFO`, MUST be settable through the `log_level` config key, and MUST be overridable through the `CVAPP_LOG_LEVEL` environment variable (the environment variable wins over the config key).

#### Scenario: Errors append a full traceback to the log file

- GIVEN an application error (for example a failed render)
- WHEN the error is reported
- THEN the full traceback is appended to `cvapp.log` at the project root
- AND the log file keeps previous entries (append, not overwrite)

#### Scenario: Environment variable overrides the config key

- GIVEN a config with `log_level: WARNING` and the environment variable `CVAPP_LOG_LEVEL=DEBUG`
- WHEN the application starts
- THEN the effective log level is `DEBUG`

#### Scenario: Default log level is INFO

- GIVEN a project with no config and no `CVAPP_LOG_LEVEL` environment variable
- WHEN the application starts
- THEN the effective log level is `INFO`