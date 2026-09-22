# CV CLI Specification

## Purpose

The `cv-cli` capability defines the single unified entry point of the CV generator: the `cv` launcher, the `python -m cvapp` equivalent, the Typer-based subcommands (`tui`, `list`, `render <name>`, `version`), the exit-code and error-reporting contract for headless use, and the consolidation of the legacy entry points (`cv_tui`, `run_cv.sh`, `Generar CV.command`). It guarantees that every path into the application — terminal command, module invocation, Finder double-click — resolves the same project, the same virtualenv, and the same behavior, and that the fragile shell hacks of the old monolith are gone.

## Requirements

### Requirement: Launcher resolves the project without depending on the working directory

The `cv` launcher MUST resolve the project root from its own script location (not from the caller's working directory), MUST use the project's `.venv` Python interpreter, MUST set `PYTHONPATH` so the `cvapp` package inside the project's `src/` directory is importable, MUST pass all command-line arguments through to `python -m cvapp`, and MUST propagate the application's exit code. Invoking the application as `python -m cvapp` with the `.venv` interpreter MUST behave identically to `./cv` for the same arguments.

#### Scenario: Launcher works from the project root

- GIVEN a terminal at the project root
- WHEN the user runs `./cv list`
- THEN the application resolves the project and its virtualenv, lists the CVs, and exits with code 0

#### Scenario: Launcher works from any working directory

- GIVEN a terminal in a directory different from the project root (for example the user's home directory)
- WHEN the user runs the launcher by its absolute path, e.g. `/path/to/project/cv list`
- THEN the application still resolves the project root from the launcher's own location and behaves identically to running it from the project root

#### Scenario: Module invocation is equivalent

- GIVEN the project's `.venv` Python interpreter and a `PYTHONPATH` that includes the project's `src/` directory
- WHEN the user runs `.venv/bin/python -m cvapp list`
- THEN the output and the exit code are identical to `./cv list`

### Requirement: No-argument invocation opens the TUI

Running the unified command with no subcommand MUST open the interactive TUI. An explicit `tui` subcommand MUST do the same. An unknown subcommand MUST produce a usage error and a non-zero exit code.

#### Scenario: No arguments opens the TUI

- GIVEN a terminal at the project root
- WHEN the user runs `./cv` with no subcommand and no flags
- THEN the Textual TUI opens instead of printing a usage message
- AND the process exits with code 0 when the user quits the TUI

#### Scenario: Explicit tui subcommand opens the TUI

- GIVEN a terminal at the project root
- WHEN the user runs `./cv tui`
- THEN the Textual TUI opens, identical to the no-argument case

#### Scenario: Unknown subcommand is rejected

- GIVEN a terminal at the project root
- WHEN the user runs `./cv frobnicate`
- THEN the application prints a usage error that names the unknown subcommand
- AND the process exits with a non-zero code

### Requirement: Headless command lists CV YAML names

The `list` subcommand MUST print the name of every discovered CV, one per line, in the same order the TUI shows them, and MUST exit with code 0. When no CV YAML files are discovered, it MUST print nothing and still exit with code 0.

#### Scenario: CVs are listed one per line

- GIVEN a project with 10+ CV YAML files at the configured source directory
- WHEN the user runs `./cv list`
- THEN every discovered CV name is printed, one per line, in the same order the TUI shows them
- AND the process exits with code 0

#### Scenario: Empty discovery still succeeds

- GIVEN a project whose configured source directory contains no `*.yaml` or `*.yml` files
- WHEN the user runs `./cv list`
- THEN the command prints no CV names
- AND the process exits with code 0

### Requirement: Headless command renders a named CV

The `render <name>` subcommand MUST resolve `<name>` to exactly one CV source among the discovered files, MUST render it through the rendering capability, MUST print the path of the generated PDF, and MUST exit with code 0 on success. If `<name>` matches zero or more than one source, the command MUST print a clear error to stderr, MUST NOT render anything, and MUST exit with a non-zero code.

#### Scenario: Named CV renders successfully

- GIVEN a project containing `Pablo_Gramajo.yaml`
- WHEN the user runs `./cv render Pablo_Gramajo`
- THEN the PDF `Pablo_Gramajo.pdf` is generated in the configured output directory
- AND the command prints the path of the generated PDF to stdout and exits with code 0
- AND the PDF is NOT opened automatically

#### Scenario: Unknown CV name is rejected

- GIVEN a project with no CV whose stem is `No_Existe`
- WHEN the user runs `./cv render No_Existe`
- THEN the command prints a clear error to stderr stating that no CV named `No_Existe` was found
- AND the process exits with a non-zero code and no PDF is generated

#### Scenario: Ambiguous CV name is rejected

- GIVEN a source directory that contains both `Mi_CV.yaml` and `Mi_CV.yml`
- WHEN the user runs `./cv render Mi_CV`
- THEN the command prints a clear error stating that the name matches more than one CV
- AND the process exits with a non-zero code and no PDF is generated

#### Scenario: Failed render exits non-zero

- GIVEN a CV YAML file that RenderCV cannot render (for example a corrupted YAML)
- WHEN the user runs `./cv render <that-cv>`
- THEN the command prints a clear error to stderr referring to the log file for details
- AND the process exits with a non-zero code

### Requirement: Headless command prints the version

The `version` subcommand MUST print the application version and exit with code 0. The version MUST be defined in exactly one place in the codebase (single source of truth), and both the `cv` launcher and `python -m cvapp` MUST read it from that same place.

#### Scenario: Version is printed

- GIVEN the application is installed and importable
- WHEN the user runs `./cv version`
- THEN a version string is printed to stdout and the process exits with code 0
- AND running `.venv/bin/python -m cvapp version` prints the same string

### Requirement: Legacy entry points delegate to the unified command

The `cv_tui` script MUST behave as an alias of `cv`: the same subcommands and the same behavior, opening the TUI when invoked with no arguments. The `Generar CV.command` Finder double-click launcher MUST delegate to the `cv` entry point and MUST keep its window open with a pause after an error, so the user can read the message before the window closes. The `run_cv.sh` script MUST be removed and MUST NOT be referenced by the application or by any remaining script.

#### Scenario: cv_tui behaves like cv

- GIVEN a terminal at the project root
- WHEN the user runs `./cv_tui list`
- THEN the output and exit code are identical to `./cv list`
- AND running `./cv_tui` with no arguments opens the TUI

#### Scenario: Finder double-click launcher pauses on error

- GIVEN a `Generar CV.command` double-click launch that ends in a render error
- WHEN the launcher finishes the failed attempt
- THEN the window shows the error message and waits for a key press before closing

#### Scenario: run_cv.sh is gone

- GIVEN the project directory after the change is applied
- WHEN the repository is searched for references to `run_cv.sh`
- THEN the file and every reference to it are absent

### Requirement: Headless commands report failures with clear messages and exit codes

Headless commands MUST print clear error messages to stderr when an application-level failure occurs and MUST exit with a non-zero code (1). Usage errors (unknown subcommand, missing required argument) MUST exit with a non-zero code. Exiting the TUI normally MUST exit with code 0. The application MUST NOT use exit code 10 for any purpose.

#### Scenario: Missing required argument is a usage error

- GIVEN the `render` subcommand requires a CV name
- WHEN the user runs `./cv render` without a name
- THEN the command prints a usage error explaining the missing argument
- AND the process exits with a non-zero code

#### Scenario: TUI exits cleanly with code 0

- GIVEN a user inside the TUI
- WHEN the user quits the TUI with the quit binding
- THEN the process exits with code 0

### Requirement: Application avoids forbidden runtime patterns

The code under `src/` MUST NOT use `shell=True`, `os.execv`, `osascript`, or the exit code 10. Quitting or restarting any flow MUST NOT close the user's Terminal window.

#### Scenario: No forbidden patterns in the source tree

- GIVEN the final `src/` directory after the change is applied
- WHEN the source tree is scanned for `shell=True`, `os.execv`, `osascript`, and exit code 10
- THEN zero occurrences are found