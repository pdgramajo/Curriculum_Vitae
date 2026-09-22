# CV TUI Specification

## Purpose

The `cv-tui` capability defines the Textual interface that is the default entry point of the app: a main screen listing the available CVs with keyboard navigation, a status view while a render runs in the background, a result screen with next actions, an error screen with retry, a clear empty state when no CVs exist, and a clean quit behavior that never touches the user's Terminal. All user-facing copy is in Spanish (Rioplatense) per the project convention. The TUI is a thin presentation layer: it delegates discovery and rendering to the other capabilities and never re-implements them.

## Requirements

### Requirement: TUI lists CV YAML files with keyboard navigation

The main screen MUST show every discovered CV (the same set and order shown by `cv list`), MUST display the application title and current state in a header, and MUST display the available key bindings in a footer. The user MUST be able to move the selection up and down with the arrow keys (↑/↓) and MUST be able to start rendering the selected CV with Enter. Wrapping of the selection MUST NOT occur: the selection stays at the first item when moving up from the top and at the last item when moving down from the bottom.

#### Scenario: Main screen matches the headless list

- GIVEN a project with 10+ CV YAML files
- WHEN the TUI opens
- THEN the main screen lists exactly the same CV names, in the same order, as `./cv list`

#### Scenario: Keyboard navigation moves the selection

- GIVEN the TUI main screen showing several CVs with the first one selected
- WHEN the user presses ↓
- THEN the selection moves to the next CV and the highlight follows
- WHEN the user presses ↑ at the first item
- THEN the selection stays on the first item

#### Scenario: Enter starts rendering the selected CV

- GIVEN the TUI main screen with a CV selected
- WHEN the user presses Enter
- THEN the selected CV is rendered and the TUI moves to the status view

### Requirement: TUI shows a clear empty state when no CV YAML files exist

When discovery finds zero CVs, the TUI MUST NOT show an empty list silently: it MUST display a clear message in Spanish indicating that no CVs were found in the configured source directory, MUST offer an action to re-scan the directory (refresh), and MUST offer the quit action. After a refresh that newly finds files, the main list MUST appear normally.

#### Scenario: Empty state with refresh and quit actions

- GIVEN a configured source directory containing no `*.yaml` or `*.yml` files
- WHEN the TUI opens
- THEN the user sees a clear Spanish message such as "No se encontraron CVs en <directorio>"
- AND the user can trigger a re-scan (refresh) and can quit

#### Scenario: Refresh discovers newly added files

- GIVEN the empty-state screen shown because no CVs existed
- WHEN a new `Mi_CV.yaml` file is added to the source directory and the user triggers refresh
- THEN the main list appears showing `Mi_CV` without restarting the application

### Requirement: TUI keeps responding and shows status while rendering

Rendering MUST run in the background (worker) so the TUI stays responsive during the render. While a render is in progress, the TUI MUST show a status view with a progress indicator (for example a spinner) and a Spanish message identifying the CV being generated, such as "Generando <nombre>…". The user MUST NOT be able to start a second render while one is already in progress.

#### Scenario: Status is shown and the interface stays responsive

- GIVEN the user has selected a CV and the render started
- WHEN the render is running
- THEN the status view shows the spinner and "Generando <nombre>…"
- AND the interface remains responsive (it does not freeze while waiting for RenderCV)

#### Scenario: Concurrent renders are prevented

- GIVEN a render in progress
- WHEN the user presses Enter again
- THEN no second render starts until the first one finishes

### Requirement: TUI shows a result screen with next actions after a successful render

After a successful render, the TUI MUST show a result screen with a success message, the path of the generated PDF, and exactly three actions with clear key bindings shown in the footer: regenerate another CV, open the PDF, and quit. The "regenerate another" action MUST return to the main list within the same process (no re-execution of the application). The "open PDF" action MUST request the PDF-opening behavior defined by the rendering capability. The quit action MUST exit the TUI.

#### Scenario: Success screen offers regenerate, open and quit

- GIVEN a render that finished successfully
- WHEN the result screen is shown
- THEN it displays a success message and the generated PDF path
- AND the footer shows the bindings for "Regenerar otro", "Abrir PDF" and "Salir"

#### Scenario: Regenerate another resets in-process

- GIVEN the success screen
- WHEN the user triggers "Regenerar otro"
- THEN the TUI returns to the main list with the full CV list reloaded
- AND the application process is the same one (no process restart, no `os.execv`)

#### Scenario: Open PDF action requests the PDF opening behavior

- GIVEN the success screen on a macOS machine
- WHEN the user triggers "Abrir PDF"
- THEN the TUI requests the rendering capability to open the generated PDF
- AND the TUI stays alive (opening the PDF does not close the application)

#### Scenario: Quit from the success screen

- GIVEN the success screen
- WHEN the user triggers the quit binding
- THEN the TUI exits with code 0

### Requirement: TUI shows an error screen with retry after a failed render

If a render fails (for example a corrupted YAML or a missing RenderCV executable), the TUI MUST NOT crash and MUST show an error screen with a friendly message in Spanish, a note pointing to the log file that contains the full traceback, and actions with clear bindings: retry the same CV (re-runs the render), go back to the main list, and quit. The full traceback MUST be written to the log file.

#### Scenario: Failed render shows error screen with retry

- GIVEN a CV whose render fails
- WHEN the render finishes with a failure
- THEN the TUI shows the error screen with a friendly Spanish message instead of a raw traceback
- AND the screen indicates that details were written to the log file
- AND the user can retry (re-run the same CV), go back to the list, or quit
- AND the application process is still running normally

#### Scenario: Retry succeeds after a transient failure

- GIVEN the error screen caused by a transient render failure (for example a one-time RenderCV error)
- WHEN the user triggers retry and the underlying cause is gone
- THEN the render runs again
- AND a successful render leads to the success screen

#### Scenario: Back to the list discards the failed selection

- GIVEN the error screen
- WHEN the user triggers the back action
- THEN the TUI returns to the main list and no render is running

### Requirement: TUI quits cleanly without closing the Terminal

The quit bindings (q and esc) MUST exit the TUI only, with exit code 0. The TUI MUST NOT use `osascript`, MUST NOT close the user's Terminal window, MUST NOT use `os.execv`, and MUST NOT use exit code 10.

#### Scenario: Quitting leaves the Terminal open

- GIVEN the TUI running inside the user's Terminal
- WHEN the user presses q
- THEN the TUI exits with code 0
- AND the Terminal window stays open and the shell prompt returns

#### Scenario: Esc quits from the main screen

- GIVEN the TUI main screen
- WHEN the user presses esc
- THEN the TUI exits with code 0 and the Terminal stays open

### Requirement: TUI user-facing copy is in Spanish (Rioplatense)

All user-visible copy in the TUI — titles, messages, hints, footer bindings, empty state, status text, result and error screens — MUST be written in Spanish (Rioplatense), following the project convention. Technical values such as file names, paths and key names MAY remain in their original form.

#### Scenario: Every screen speaks Spanish

- GIVEN each TUI screen (main list, empty state, status, success, error)
- WHEN the screen is shown to the user
- THEN every label and message is in Spanish (Rioplatense)