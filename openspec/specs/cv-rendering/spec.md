# CV Rendering Specification

## Purpose

The `cv-rendering` capability defines how CV sources become PDFs: discovery of CV YAML files from the configured source directory, invocation of RenderCV as a safe subprocess (explicit argument list, never a shell string), output to the configured output directory, per-run intermediate cleanup that cannot touch user assets, a configurable timeout, passthrough of extra RenderCV flags, and the macOS-only behavior of opening the generated PDF. RenderCV remains the rendering engine; this capability only wraps it.

## Requirements

### Requirement: CV YAML sources are discovered from the configured directory

Discovery MUST scan the configured source directory (the project root by default) for files matching `*.yaml` and `*.yml`, MUST NOT search recursively, MUST exclude dotfiles, and MUST return only regular files sorted by name. The `list` command, the TUI main screen, and the `render` command MUST all use the same discovery result.

#### Scenario: Standard discovery returns the existing files in order

- GIVEN a project whose root contains 10+ CV YAML files (a mix of `.yaml` and `.yml`)
- WHEN discovery runs against the configured source directory
- THEN every CV file is found, sorted by name, and no other files are included

#### Scenario: Dotfiles are excluded

- GIVEN the source directory containing a file named `.cv_experimental.yaml`
- WHEN discovery runs
- THEN the dotfile is NOT part of the result

#### Scenario: Subdirectories are not scanned

- GIVEN a subdirectory inside the source directory that contains `Otro_CV.yaml`
- WHEN discovery runs
- THEN the file inside the subdirectory is NOT part of the result

#### Scenario: Empty directory yields an empty list

- GIVEN a source directory with no `*.yaml` or `*.yml` files
- WHEN discovery runs
- THEN the result is an empty list (no error)

### Requirement: Renders are executed by RenderCV as a safe subprocess

Rendering MUST invoke RenderCV as a subprocess with an explicit argument list; it MUST NOT use `shell=True` and MUST NOT build the command as a shell string. The invocation MUST render the selected source file with the flags `-nomd`, `-nohtml`, `-nopng` and `--pdf-path` pointing at the configured output file — the same effective flags that work today. The system MUST capture RenderCV's exit code and output. If RenderCV cannot be started (missing executable) or exits with a non-zero code (for example on invalid YAML), the render MUST be reported as failed, with the captured message available for the error reporting and logging flow.

#### Scenario: Successful render produces the PDF

- GIVEN a valid CV YAML file
- WHEN the render of that file is invoked
- THEN RenderCV runs with an explicit argument list including `-nomd`, `-nohtml`, `-nopng` and `--pdf-path`
- AND the render exits with code 0 and the PDF file exists at the expected output path

#### Scenario: Missing RenderCV executable is a clear failure

- GIVEN an environment where the `rendercv` executable cannot be found
- WHEN a render is invoked
- THEN the render is reported as failed with a clear message that RenderCV could not be started
- AND the failure flows into the normal error reporting (non-zero exit headless, error screen in the TUI)

#### Scenario: RenderCV failure is captured

- GIVEN a CV YAML file that RenderCV rejects (for example a corrupted or invalid YAML)
- WHEN the render of that file is invoked
- THEN RenderCV exits with a non-zero code
- AND the render is reported as failed and the captured RenderCV message is included in the error output

### Requirement: Render output lands in the configured output directory

The generated PDF MUST be written to `<output_dir>/<stem>.pdf`, where `<output_dir>` is the configured output directory (default `rendercv_output`) and `<stem>` is the basename of the source file without its extension. The render MUST produce the PDF at that location regardless of the caller's working directory (paths MUST be resolved against the project, not the current working directory). The system SHOULD create the output directory if it does not exist.

#### Scenario: PDF is written to the configured output path

- GIVEN a CV source named `Pablo_Gramajo.yaml` and the default output directory
- WHEN the render succeeds
- THEN the PDF exists at `rendercv_output/Pablo_Gramajo.pdf`

#### Scenario: Render works from any working directory

- GIVEN a render invoked while the shell's working directory is not the project root
- WHEN the render succeeds
- THEN the PDF still lands in the project's configured output directory

#### Scenario: Output directory is created when missing

- GIVEN an output directory that does not exist yet
- WHEN a render succeeds
- THEN the output directory exists and contains the PDF

### Requirement: Intermediate files are cleaned without touching user assets

After a completed render attempt, the system MUST remove only the intermediate files produced by that attempt, and only inside the configured output directory. Cleanup MUST NOT remove the generated PDF, MUST NOT remove any file outside the output directory, MUST NOT remove files produced by another CV's render, and MUST NOT remove user assets such as CV photos — even when their filenames match an intermediate-file pattern (for example `*_*.png`). The output directory path itself MUST be resolved against the project so that cleanup can never reach source files elsewhere.

#### Scenario: Successful render cleans only its own intermediates and keeps the PDF

- GIVEN a successful render of `Mi_CV.yaml`
- WHEN the render finishes
- THEN the intermediate files produced by this run are removed
- AND `Mi_CV.pdf` remains in the output directory

#### Scenario: Rendering one CV does not touch another CV's files

- GIVEN an output directory that contains `Otro_CV.pdf` and other files from a previous render of another CV
- WHEN a render of `Mi_CV.yaml` completes
- THEN `Otro_CV.pdf` and the other files from the other CV are left untouched

#### Scenario: Photo files survive cleanup

- GIVEN a CV photo file such as `foto_2024.png` inside the output directory (matching the `*_*.png` pattern)
- WHEN any render completes and cleanup runs
- THEN the photo file is NOT deleted

#### Scenario: Files outside the output directory are never touched

- GIVEN CV source YAML files and photos located in the project root, outside the output directory
- WHEN any render completes and cleanup runs
- THEN no file outside the output directory is removed, on success or on failure

### Requirement: Renders respect a configurable timeout

The system MUST enforce the configured timeout (default 120 seconds) on each RenderCV run. If the run exceeds the timeout, the system MUST stop it and MUST report a timeout failure with a clear message; headless commands exit non-zero and the TUI shows the error screen.

#### Scenario: Overlong render fails with a timeout message

- GIVEN a render configured with a timeout shorter than the time RenderCV needs
- WHEN the render is invoked
- THEN the run is stopped when the timeout expires
- AND the render is reported as failed with a clear timeout message

### Requirement: Configured extra RenderCV flags are passed through

If the configuration defines extra RenderCV flags, the system MUST append them to the RenderCV argument list after the standard flags, and they MUST be visible in the invocation (which must remain inspectable, for example by a test).

#### Scenario: Extra flags reach the RenderCV invocation

- GIVEN a configuration with `rendercv_extra_flags: ["--flag-a", "valor"]`
- WHEN a render is invoked
- THEN the argument list of the RenderCV subprocess includes `--flag-a` and `valor` after the standard flags

### Requirement: Generated PDF opens on macOS only, when enabled

When the `open_pdf_after` option is enabled, the system MUST open the generated PDF after a successful render in the interactive (TUI) flow, using the macOS `open` command. The system MUST NOT attempt to open PDFs on non-macOS platforms; in that case it MUST log a notice instead. A failure of the open step MUST NOT turn a successful render into a failure: the render stays successful and a warning is logged. The headless `render` command MUST NOT open the PDF automatically, regardless of configuration.

#### Scenario: PDF opens after a successful TUI render on macOS

- GIVEN a macOS machine and `open_pdf_after` enabled
- WHEN a TUI render succeeds
- THEN the generated PDF is opened with the macOS `open` command

#### Scenario: Headless render never opens the PDF

- GIVEN `open_pdf_after` enabled
- WHEN `./cv render <name>` succeeds
- THEN the PDF is NOT opened automatically

#### Scenario: Non-macOS platforms do not attempt to open

- GIVEN a non-macOS platform and `open_pdf_after` enabled
- WHEN a TUI render succeeds
- THEN the system does NOT attempt to open the PDF and logs a notice instead

#### Scenario: Open failure does not fail the render

- GIVEN a macOS machine where the `open` command fails for the generated PDF
- WHEN a TUI render succeeds and the open step fails
- THEN the render is still reported as successful
- AND a warning about the failed open is logged