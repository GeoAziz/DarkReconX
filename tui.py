"""Simple Textual TUI for DarkReconX (Day 22 scaffold).

This is a lightweight, safe scaffold that provides:
- Modules list with checkboxes (auto-discovered)
- Profile selector (from core.profiles)
- Results viewer (placeholder)
- Live log console

If `textual` is not installed, the `drx tui` command will show a helpful message.
"""
from __future__ import annotations

import asyncio
import json
import sys
from typing import List

from rich.pretty import Pretty

try:
    from textual.app import App, ComposeResult
    from textual.widgets import Header, Footer, Static, Button, Checkbox, Input, Select, TextLog, ScrollView
    from textual.containers import Horizontal, Vertical
except Exception:  # textual not installed
    App = None


def _safe_discover_modules() -> List[str]:
    try:
        from core.loader import discover_modules

        mods = discover_modules()
        return sorted(list(mods.keys()))
    except Exception:
        return []


def _safe_load_profiles():
    try:
        from core.profiles import load_profiles

        return load_profiles()
    except Exception:
        return {}


if App is not None:

    class ModuleCheckbox(Checkbox):
        pass


    class TUIMainApp(App):
        CSS_PATH = None
        BINDINGS = [("q", "quit", "Quit"), ("r", "run_scan", "Run Scan")]

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal():
                with Vertical(id="left-pane"):
                    yield Static("[b]Modules[/b]", id="modules-title")
                    self.module_container = ScrollView(id="modules-list")
                    yield self.module_container
                    yield Static("[b]Profile[/b]", id="profiles-title")
                    self.profile_select = Select(options=[], id="profile-select")
                    yield self.profile_select
                    yield Button("Run Scan", id="run-btn")
                with Vertical(id="right-pane"):
                    yield Static("[b]Results[/b]", id="results-title")
                    self.results_view = ScrollView(id="results-view")
                    yield self.results_view
                    yield Static("[b]Logs[/b]", id="logs-title")
                    self.log = TextLog(highlight=True, markup=True)
                    yield self.log
            yield Footer()

        async def on_mount(self) -> None:
            # populate modules
            modules = _safe_discover_modules()
            if not modules:
                self.module_container.update(Static("No modules found or autoloader failed."))
            else:
                for m in modules:
                    cb = ModuleCheckbox(m, value=False)
                    await self.module_container.mount(cb)

            # populate profiles
            profiles = _safe_load_profiles()
            opts = [(name, name) for name in profiles.keys()]
            if not opts:
                opts = [("quick", "quick"), ("full", "full")]
            self.profile_select.options = opts

            self.log.write("[green]TUI ready. Press R to run a scan or Q to quit.[/green]")

        async def action_run_scan(self) -> None:
            # Collect selected modules
            selected = []
            for child in self.module_container.children:
                try:
                    if isinstance(child, ModuleCheckbox) and child.value:
                        selected.append(child.label)
                except Exception:
                    continue

            profile = self.profile_select.value or "quick"
            self.log.write(f"[cyan]Running scan (profile={profile}) with modules: {selected}[/cyan]")

            # For demo purposes, run a minimal async task that simulates progress
            await self._simulate_scan(selected)

        async def _simulate_scan(self, modules: List[str]):
            for i, mod in enumerate(modules or ["demo"]):
                self.log.write(f"[yellow]Starting module: {mod}[/yellow]")
                await asyncio.sleep(0.5)
                # simulate result
                res = {"module": mod, "status": "ok", "data": {"sample": True}}
                self.results_view.update(Static(Pretty(res)))
                self.log.write(f"[green]Completed module: {mod}[/green]")

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
