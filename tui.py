"""DarkReconX TUI - Enhanced with Sprint A features (profile/module interactivity, search, validation).

Fully interactive TUI with:
- Module/profile tooltips and descriptions
- Module search/filter functionality
- Target field validation (domain/IP/email)
- Simple autocomplete for common TLDs
- Orchestrator-backed async scanning with live progress
- Color-coded results and logs
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import importlib
import inspect
from pathlib import Path

from rich.pretty import Pretty
from rich.text import Text

if TYPE_CHECKING:
    # Provide names for static type checking (Pylance/mypy) without importing Textual at runtime
    from textual.app import App, ComposeResult  # type: ignore
    from textual.widgets import Header, Footer, Static, Button, Checkbox, Input, Select, TextLog, ScrollView, ProgressBar, Label  # type: ignore
    from textual.containers import Horizontal, Vertical, Container  # type: ignore
else:
    try:
        from importlib import import_module
        textual_app = import_module("textual.app")
        textual_widgets = import_module("textual.widgets")
        textual_containers = import_module("textual.containers")
        App = getattr(textual_app, "App", None)
        ComposeResult = getattr(textual_app, "ComposeResult", None)
        Header = getattr(textual_widgets, "Header", None)
        Footer = getattr(textual_widgets, "Footer", None)
        Static = getattr(textual_widgets, "Static", None)
        Button = getattr(textual_widgets, "Button", None)
        Checkbox = getattr(textual_widgets, "Checkbox", None)
        Input = getattr(textual_widgets, "Input", None)
        Select = getattr(textual_widgets, "Select", None)
        TextLog = getattr(textual_widgets, "TextLog", None)
        ScrollView = getattr(textual_widgets, "ScrollView", None)
        ProgressBar = getattr(textual_widgets, "ProgressBar", None)
        Label = getattr(textual_widgets, "Label", None)
        Horizontal = getattr(textual_containers, "Horizontal", None)
        Vertical = getattr(textual_containers, "Vertical", None)
    except Exception as _exc:
        # For debugging: print why the Textual imports failed during module import.
        try:
            import traceback, sys

            traceback.print_exc()
        except Exception:
            pass
        # Ensure these module references exist even when import fails to avoid NameError later
        textual_app = None
        textual_widgets = None
        textual_containers = None
        App = None
        ComposeResult = None
        Header = Footer = Static = Button = Checkbox = Input = Select = TextLog = ScrollView = ProgressBar = Label = None
        Horizontal = Vertical = None


# Module metadata and descriptions
MODULE_DESCRIPTIONS = {
    "whois_lookup": "WHOIS lookup for domain registration info",
    "subdomain_finder": "Find subdomains via DNS and passive sources",
    "ip_geo_tracker": "Geolocate IP addresses and show ISP info",
    "email_recon": "Analyze email addresses and validate MX/SPF/DKIM",
    "username_recon": "Search for usernames across public databases",
    "hash_identifier": "Identify hash types and crack common hashes",
    "github_osint": "Fetch GitHub public profile and repositories",
    "email_osint": "Check email address across public sources",
    "ssl_info": "Extract TLS certificate metadata",
    "breach_lookup": "Check if data appears in known breaches",
    "phishing_kit_detector": "Detect phishing kits in URLs",
    "tor_exit_monitor": "Monitor Tor exit node IPs",
    "onion_site_crawler": "Crawl Tor hidden services",
}

# Profile descriptions
PROFILE_DESCRIPTIONS = {
    "quick": "Fast scan (DNS, basic SSL, WHOIS) - ~15 sec",
    "full": "Complete scan (all modules) - ~2-5 min",
    "privacy": "Privacy-focused scan (Tor, DNS checks only) - ~30 sec",
    "developer": "Developer profile (GitHub, email, SSL) - ~1 min",
}

# Common TLDs for autocomplete
COMMON_TLDS = ["com", "org", "net", "edu", "gov", "io", "co", "uk", "de", "fr", "us", "ca", "au", "jp", "cn", "in", "br", "ru", "nl", "se", "ch"]


def _safe_discover_modules() -> List[str]:
    try:
        from core.loader import discover_modules
        mods = discover_modules()
        return sorted(list(mods.keys()))
    except Exception:
        return []


def _safe_load_profiles() -> Dict[str, Any]:
    try:
        from core.profiles import load_profiles
        return load_profiles()
    except Exception:
        return {}


def _validate_target(target: str) -> tuple[bool, str]:
    """Validate target as domain, IP, or email. Returns (is_valid, message)."""
    target = target.strip()
    if not target:
        return False, "Target cannot be empty"
    
    # Email pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, target):
        return True, f"✓ Email: {target}"
    
    # IP pattern (simple)
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, target):
        parts = target.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            return True, f"✓ IP: {target}"
        return False, "Invalid IP address (octets must be 0-255)"
    
    # Domain pattern (basic)
    domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})?$'
    if re.match(domain_pattern, target) and '.' in target:
        return True, f"✓ Domain: {target}"
    
    return False, f"⚠ Invalid format (domain, IP, or email expected)"


def _autocomplete_tlds(partial: str) -> List[str]:
    """Return autocomplete suggestions for TLDs."""
    partial_lower = partial.lower()
    if '.' in partial:
        # User is typing TLD after domain
        return [tld for tld in COMMON_TLDS if tld.startswith(partial_lower.split('.')[-1])]
    return []
if App is not None:
    # Provide fallbacks for widget API differences across Textual releases
    TextLog = TextLog or getattr(textual_widgets, "Log", None)
    # If ScrollView is unavailable, fall back to Static as a simple scrollable container
    ScrollView = ScrollView or getattr(textual_widgets, "ScrollView", None) or Static

    # Assert only critical widgets are present; optional widgets may be None
    assert Static is not None
    assert Checkbox is not None
    assert Select is not None

    class ModuleCheckbox(Checkbox):
        """Enhanced checkbox with module description."""
        def __init__(self, module_name: str, description: str = "", **kwargs):
            super().__init__(module_name, **kwargs)
            self.module_name = module_name
            self.description = description or MODULE_DESCRIPTIONS.get(module_name, "No description")


    class TUIMainApp(App):
        # Avoid loading the provided CSS by default to prevent stylesheet
        # parsing errors on different Textual versions. The TUI will still
        # function with default terminal styling.
        CSS_PATH = None
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("r", "run_scan", "Run Scan"),
            ("m", "toggle_modules", "Toggle Modules"),
            ("p", "toggle_profiles", "Toggle Profiles"),
            ("l", "toggle_logs", "Toggle Logs"),
            ("e", "toggle_errors", "Toggle Errors"),
            ("t", "toggle_view", "Toggle View"),
            ("c", "clear_results", "Clear Results"),
            ("ctrl+e", "export_results", "Export"),
            ("ctrl+t", "toggle_theme", "Toggle Theme"),
            ("h", "show_help", "Help"),
        ]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.view_mode = "json"  # json or table
            self.errors_list: List[Dict[str, Any]] = []
            # store theme preference locally without setting App.theme (may be unregistered)
            self._theme = self._load_theme_preference()
            self.scan_results: List[Dict[str, Any]] = []  # for export

        def _load_theme_preference(self) -> str:
            """Load theme preference from file (~/.darkreconx_theme)."""
            try:
                theme_file = Path.home() / ".darkreconx_theme"
                if theme_file.exists():
                        return theme_file.read_text().strip() or "light"
            except Exception:
                pass
            return "light"

        def _save_theme_preference(self, theme: str) -> None:
            """Save theme preference to file."""
            try:
                theme_file = Path.home() / ".darkreconx_theme"
                theme_file.write_text(theme)
            except Exception:
                pass

        def _reload_css(self, theme: str) -> None:
            """Reload CSS based on theme."""
            try:
                if theme == "light":
                    self.STYLESHEET = "tui_light.css"
                else:
                    self.STYLESHEET = "tui.css"
                # Recompose may be a coroutine in some Textual versions; handle both cases
                res = self.recompose()
                if asyncio.iscoroutine(res):
                    # Try to schedule on the running loop, otherwise run to completion
                    try:
                        asyncio.create_task(res)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(res)
                        finally:
                            loop.close()
            except Exception:
                pass

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            yield Static("[b]DarkReconX TUI[/b] — R:Run  M:Modules  P:Profiles  L:Logs  E:Errors  T:View  C:Clear  H:Help  Q:Quit", id="topbar")
            with Horizontal():
                with Vertical(id="left-pane"):
                    yield Static("[b]Modules[/b]", id="modules-title")
                    # Module search/filter
                    self.module_search = Input(placeholder="search modules...", id="module-search")
                    yield self.module_search
                    self.module_container = ScrollView(id="modules-list")
                    yield self.module_container
                    yield Static("[b]Profile[/b]", id="profiles-title")
                    # Profile with description display
                    self.profile_select = Select(options=[], id="profile-select")
                    yield self.profile_select
                    self.profile_desc = Static("Select a profile", id="profile-desc")
                    yield self.profile_desc
                    yield Static("[b]Target[/b]", id="target-title")
                    self.target_input = Input(placeholder="domain/IP/email", id="target-input")
                    yield self.target_input
                    # Target validation feedback
                    self.target_feedback = Static("Enter target to validate", id="target-feedback", classes="status-warn")
                    yield self.target_feedback
                    # Progress bar
                    yield Static("[b]Progress[/b]", id="progress-title")
                    self.progress_bar = ProgressBar(total=100, id="progress-bar")
                    yield self.progress_bar
                    self.progress_label = Static("0%", id="progress-label")
                    yield self.progress_label
                    yield Button("Run Scan", id="run-btn")
                with Vertical(id="right-pane"):
                    # View toggle indicator
                    self.view_indicator = Static("[b]Results[/b] (JSON)", id="results-title")
                    yield self.view_indicator
                    self.results_view = ScrollView(id="results-view")
                    yield self.results_view
                    # Errors panel (hidden by default)
                    self.errors_panel = ScrollView(id="errors-view")
                    self.errors_panel.visible = False
                    yield self.errors_panel
                    yield Static("[b]Logs[/b]", id="logs-title")
                    # Create logs widget with compatibility across Textual versions.
                    def _create_logs_widget():
                        # Try TextLog or Log with common kwargs, falling back on simpler constructors.
                        candidates = [TextLog, getattr(textual_widgets, "Log", None)]
                        for cls in candidates:
                            if cls is None:
                                continue
                            try:
                                return cls(highlight=True, markup=True, id="logs-view")
                            except TypeError:
                                try:
                                    return cls(highlight=True, id="logs-view")
                                except TypeError:
                                    try:
                                        return cls(id="logs-view")
                                    except Exception:
                                        continue

                        # Fallback: a Static-based simple logger with a write() method.
                        class SimpleLog(Static):
                            def __init__(self, *a, **k):
                                # initialize with empty content
                                super().__init__("", *a, **k)
                                self._buffer = ""

                            def write(self, text: str) -> None:
                                try:
                                    self._buffer += str(text) + "\n"
                                    # update replaces content; keep it simple
                                    self.update(self._buffer)
                                except Exception:
                                    pass

                        try:
                            return SimpleLog(id="logs-view")
                        except Exception:
                            # As a last resort, return a Static instance
                            return Static("Logs unavailable", id="logs-view")

                    self.logs_widget = _create_logs_widget()
                    yield self.logs_widget
            # Status bar at bottom
            self.status_bar = Static("Ready", id="status-bar")
            yield self.status_bar
            yield Footer()

        async def on_mount(self) -> None:
            # Populate modules with descriptions
            modules = _safe_discover_modules()
            if not modules:
                self.module_container.update("No modules found")
            else:
                for m in modules:
                    desc = MODULE_DESCRIPTIONS.get(m, "")
                    cb = ModuleCheckbox(m, description=desc, value=False)
                    await self.module_container.mount(cb)

            # Populate profiles with descriptions
            profiles = _safe_load_profiles()
            profile_opts = [(name, name) for name in profiles.keys()]
            if not profile_opts:
                profile_opts = [("quick", "quick"), ("full", "full"), ("privacy", "privacy")]
            # Use setattr to avoid static type-checkers complaining about Select.options
            setattr(self.profile_select, "options", profile_opts)
            if profile_opts:
                # Some Textual Select implementations validate assigned values strictly
                # and may raise for plain strings. Try to assign, but don't fail if it
                # raises — we'll still update the profile description for the UI.
                try:
                    self.profile_select.value = profile_opts[0][1]
                except Exception:
                    pass
                try:
                    self._update_profile_desc(profile_opts[0][1])
                except Exception:
                    pass

            # Initial results message
            try:
                await self.results_view.mount(Static("Results will appear here. Select providers, enter a target, and press R or click Run Scan.", classes="pretty"))
            except Exception:
                pass

            # Focus target input (handle both sync and async focus() across Textual versions)
            try:
                res = self.target_input.focus()
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass

            self.logs_widget.write("[green]TUI ready. Press R to scan or H for help.[/green]")

        async def on_input_changed(self, event) -> None:
            """Handle input changes for target field validation and module search."""
            if event.input.id == "target-input":
                # Validate target
                target = event.input.value.strip()
                if target:
                    valid, msg = _validate_target(target)
                    if valid:
                        self.target_feedback.update(Text(msg, style="green bold"))
                    else:
                        self.target_feedback.update(Text(msg, style="red bold"))
                else:
                    self.target_feedback.update(Text("Enter target to validate", style="yellow bold"))

            elif event.input.id == "module-search":
                # Filter modules based on search
                search = event.input.value.lower()
                for child in self.module_container.children:
                    if isinstance(child, ModuleCheckbox):
                        # Show/hide based on search match
                        match = search in child.module_name.lower() or search in child.description.lower()
                        child.display = match

        async def on_select_changed(self, event) -> None:
            """Update profile description when profile is selected."""
            if event.select.id == "profile-select" and event.select.value:
                self._update_profile_desc(event.select.value)

        def _update_profile_desc(self, profile_name: str):
            """Update the displayed profile description."""
            desc = PROFILE_DESCRIPTIONS.get(profile_name, "No description available")
            self.profile_desc.update(Text(f"• {desc}", style="cyan"))

        async def action_show_help(self) -> None:
            """Display help menu."""
            help_text = """
[b cyan]DarkReconX TUI Help[/b cyan]

[b yellow]Keyboard Shortcuts:[/b yellow]
  R       - Run Scan
  M       - Toggle Modules panel
  P       - Toggle Profiles panel
  L       - Toggle Logs panel
  E       - Toggle Errors panel
  T       - Toggle Results View (JSON/Table)
  C       - Clear Results
  Ctrl+E  - Export Results (JSON/CSV)
  Ctrl+T  - Toggle Theme (Dark/Light)
  H       - Show this Help
  Q       - Quit

[b yellow]How to Use:[/b yellow]
1. Select modules from the left panel (checkboxes)
2. Choose a scan profile (quick, full, privacy, developer)
3. Enter target: domain (example.com), IP (1.2.3.4), or email (user@example.com)
4. Press R or click "Run Scan"
5. Results stream into the right panel as providers complete
6. Check logs and errors panel for progress and failures

[b yellow]Module Search:[/b yellow]
  Type in the "search modules..." field to filter available modules

[b yellow]Target Validation:[/b yellow]
  Field shows validation status (green=valid, red=invalid, yellow=pending)

[b yellow]View Modes:[/b yellow]
  Press T to toggle between JSON (full data) and Table (summary) views

[b yellow]Errors & Status:[/b yellow]
  Press E to toggle the errors panel which surfaces module failures with suggestions
  Status bar at bottom shows scan progress and current state

[b yellow]Export:[/b yellow]
  Press Ctrl+E to export scan results to JSON and CSV formats

[b yellow]Theme:[/b yellow]
  Press Ctrl+T to toggle between Dark and Light themes (persists between sessions)
"""
            self.logs_widget.write(help_text)

        async def action_toggle_errors(self) -> None:
            """Toggle errors panel visibility."""
            try:
                visible = self.errors_panel.visible
                self.errors_panel.visible = not visible
                if not visible and not self.errors_list:
                    await self.errors_panel.mount(Static("No errors yet.", classes="pretty"))
                self.logs_widget.write(f"[cyan]Errors panel {'shown' if not visible else 'hidden'}.[/cyan]")
            except Exception:
                pass

        async def action_toggle_view(self) -> None:
            """Toggle between JSON and Table view modes."""
            self.view_mode = "table" if self.view_mode == "json" else "json"
            try:
                mode_text = "Table" if self.view_mode == "table" else "JSON"
                self.view_indicator.update(f"[b]Results[/b] ({mode_text})")
                self.logs_widget.write(f"[cyan]Switched to {mode_text} view.[/cyan]")
            except Exception:
                pass

        async def action_toggle_theme(self) -> None:
            """Toggle between Dark and Light themes (Ctrl+T)."""
            new_theme = "light" if self._theme == "dark" else "dark"
            self._theme = new_theme
            self._save_theme_preference(new_theme)
            self._reload_css(new_theme)
            self.logs_widget.write(f"[cyan]Switched to {new_theme.upper()} theme. Restart TUI to fully apply.[/cyan]")

        def _flatten_dict(self, d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, str]:
            """Flatten nested dict for CSV export."""
            items: List = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(self._flatten_dict(v, new_key, sep=sep).items())
                elif isinstance(v, (list, tuple)):
                    items.append((new_key, json.dumps(v)))
                else:
                    items.append((new_key, str(v)))
            return dict(items)

        async def action_export_results(self) -> None:
            """Export results to JSON or CSV."""
            if not self.scan_results:
                self.logs_widget.write("[yellow]No results to export.[/yellow]")
                return

            try:
                import csv
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                # JSON export
                json_file = Path(f"scan_results_{timestamp}.json")
                with open(json_file, "w") as f:
                    json.dump(self.scan_results, f, indent=2)
                self.logs_widget.write(f"[green]✓ Results exported to {json_file}[/green]")

                # CSV export (flattened)
                csv_file = Path(f"scan_results_{timestamp}.csv")
                if self.scan_results:
                    flat_results = [self._flatten_dict(r) for r in self.scan_results]
                    if flat_results:
                        fieldnames = set()
                        for r in flat_results:
                            fieldnames.update(r.keys())
                        with open(csv_file, "w", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                            writer.writeheader()
                            writer.writerows(flat_results)
                        self.logs_widget.write(f"[green]✓ Results exported to {csv_file}[/green]")
            except Exception as e:
                self.logs_widget.write(f"[red]Export failed: {e}[/red]")

        def _update_status_bar(self, status: str) -> None:
            """Update the status bar at the bottom."""
            try:
                timestamp = time.strftime("%H:%M:%S")
                self.status_bar.update(f"[cyan]{timestamp}[/cyan] | {status}")
            except Exception:
                pass

        async def _add_error_entry(self, provider: str, error_msg: str, suggestion: str = "") -> None:
            """Add an error to the errors panel."""
            error_entry = {
                "provider": provider,
                "error": error_msg,
                "suggestion": suggestion,
                "timestamp": time.time()
            }
            self.errors_list.append(error_entry)
            
            error_text = f"[red]✗ {provider}:[/red] {error_msg}"
            if suggestion:
                error_text += f"\n  [yellow]→ {suggestion}[/yellow]"
            
            try:
                # Clear placeholder if this is the first error
                if len(self.errors_list) == 1:
                    self.errors_panel.children.clear()
                await self.errors_panel.mount(Static(error_text, classes="result-entry"))
            except Exception:
                pass

        async def action_clear_results(self) -> None:
            """Clear all results from the results view."""
            self.results_view.children.clear()
            await self.results_view.mount(Static("Results cleared. Run a new scan to populate.", classes="pretty"))
            self.logs_widget.write("[cyan]Results cleared.[/cyan]")

        async def action_run_scan(self) -> None:
            # Collect selected modules
            selected: List[str] = []
            for child in self.module_container.children:
                try:
                    if isinstance(child, ModuleCheckbox) and child.value and child.display:
                        # use module_name (a string) instead of label (Content) to avoid type errors
                        selected.append(getattr(child, "module_name", str(child.label)))
                except Exception:
                    continue

            # Ensure profile is a plain string (Select.value can be a non-str sentinel in some Textual versions)
            profile_val = getattr(self.profile_select, "value", None)
            profile = profile_val if isinstance(profile_val, str) else "quick"
            target = (self.target_input.value or "").strip()
            
            # Validate target
            valid, msg = _validate_target(target)
            if not valid:
                self.logs_widget.write(f"[red]{msg}[/red]")
                return

            self.logs_widget.write(f"[cyan]Running scan: profile={profile} target={target} modules={len(selected)}[/cyan]")
            self._update_status_bar(f"Running scan with {len(selected)} modules...")
            asyncio.create_task(self._run_scan_background(target, selected, profile))

        async def _run_scan_background(self, target: str, modules: List[str], profile: str):
            """Run scan using orchestrator stream API with error tracking."""
            try:
                from core.orchestrator import run_scan_stream
            except Exception as e:
                self.logs_widget.write(f"[red]Failed to import orchestrator: {e}[/red]")
                self._update_status_bar(f"Error: Failed to import orchestrator")
                return

            # Reset progress and errors
            completed = 0
            total_est = len(modules) if modules else 5
            self.errors_list.clear()
            self.scan_results.clear()
            try:
                self.progress_bar.update(total=100, progress=0)
                self.progress_label.update("0%")
            except Exception:
                pass

            async def _consume_stream():
                nonlocal completed
                try:
                    async for item in run_scan_stream(target, profile=profile):
                        if isinstance(item, dict) and item.get("_final"):
                            merged = item.get("merged")
                            self.logs_widget.write("[bold cyan]✓ Scan complete[/bold cyan]")
                            self._update_status_bar(f"Scan complete: {len(self.errors_list)} errors, {completed} successful")
                            try:
                                self.progress_bar.update(progress=100)
                                self.progress_label.update("100%")
                            except Exception:
                                pass
                            await self.results_view.mount(Static(Pretty(merged)))
                            break

                        if isinstance(item, dict):
                            provider = item.get("provider") or item.get("module") or "unknown"
                            if "status" in item or "module" in item:
                                envelope = item
                            else:
                                if item.get("success", False):
                                    envelope = {"module": provider, "status": "ok", "data": item.get("data")}
                                else:
                                    envelope = {"module": provider, "status": "error", "message": item.get("error")}

                            if envelope.get("status") == "ok":
                                self.logs_widget.write(f"[green]✓ {provider} completed[/green]")
                                self._update_status_bar(f"Running: {provider} completed")
                            else:
                                error_msg = envelope.get("message") or "Unknown error"
                                self.logs_widget.write(f"[red]✗ {provider} error: {error_msg}[/red]")
                                # Provide intelligent suggestions for common errors
                                suggestion = ""
                                if "timeout" in error_msg.lower():
                                    suggestion = "Check your internet connection or increase the timeout."
                                elif "api key" in error_msg.lower() or "not found" in error_msg.lower():
                                    suggestion = "Configure API keys in core/keys.py or config files."
                                elif "invalid" in error_msg.lower():
                                    suggestion = "Verify the target format and try again."
                                await self._add_error_entry(provider, error_msg, suggestion)
                                self._update_status_bar(f"Error in {provider}")

                            await self.results_view.mount(Static(Pretty(envelope)))

                            # Store result for export
                            self.scan_results.append(envelope)

                            completed += 1
                            try:
                                pct = int((completed / total_est) * 100)
                                self.progress_bar.update(progress=min(pct, 99))
                                self.progress_label.update(f"{min(pct, 99)}%")
                            except Exception:
                                pass
                except Exception as e:
                    self.logs_widget.write(f"[red]Orchestrator stream failed: {e}[/red]")
                    self._update_status_bar(f"Error: {str(e)[:50]}")

            asyncio.create_task(_consume_stream())

        async def action_toggle_modules(self) -> None:
            try:
                widget = self.query_one("#modules-list", ScrollView)
                widget.visible = not widget.visible
            except Exception:
                pass

        async def action_toggle_profiles(self) -> None:
            try:
                sel = self.query_one("#profile-select", Select)
                sel.visible = not sel.visible
            except Exception:
                pass

        async def action_toggle_logs(self) -> None:
            try:
                self.logs_widget.visible = not self.logs_widget.visible
            except Exception:
                pass

        async def on_button_pressed(self, event) -> None:
            if event.button.id == "run-btn":
                await self.action_run_scan()


def launch_tui():
    if App is None:
        print("Textual is not installed. Install it with: pip install textual rich")
        return
    TUIMainApp().run()


if __name__ == "__main__":
    launch_tui()
