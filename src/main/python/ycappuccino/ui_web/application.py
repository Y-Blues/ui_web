"""
WebApplication: renders a ycappuccino.ui.application.Application on a Navigator -- the login screen, then
the menu, each entry's chained screens (prefilled from the previous one), the saved message and sign-out.
ui_shell's ShellApplication renders the same Application in a terminal.
"""

from typing import Any, Awaitable, Callable

from ycappuccino.ui.application import Application, Step, prefill_values
from ycappuccino.ui.model import Screen
from ycappuccino.ui.transport import Transport
from ycappuccino.ui_web.navigation import Navigator


class WebApplication:

    def __init__(
        self,
        application: Application,
        navigator: Navigator,
        screens: Callable[[str], Screen],
        transports: dict[str, Transport],
        on_signed_in: Callable[[Any], Awaitable[None]],
        on_signed_out: Callable[[], Awaitable[None]],
    ) -> None:
        """on_signed_in receives the login step's result (e.g. a token), on_signed_out runs on sign-out"""
        self._application = application
        self._navigator = navigator
        self._screens = screens
        self._transports = transports
        self._on_signed_in = on_signed_in
        self._on_signed_out = on_signed_out

    def start(self) -> None:
        self.show_login()

    def show_login(self) -> None:
        login = self._application.login

        async def signed_in(result: Any) -> None:
            await self._on_signed_in(result)
            self.show_menu()

        self._navigator.show_screen(self._screens(login.screen), self._transports[login.transport], on_result=signed_in)

    def show_menu(self) -> None:
        entries = [(entry.label, self._runner(entry.steps)) for entry in self._application.menu]
        entries.append((self._application.sign_out, self._sign_out))
        self._navigator.show_menu(self._application.title, entries)

    def _runner(self, steps: tuple[Step, ...]) -> Callable[[], Awaitable[None]]:
        async def run() -> None:
            self._show_step(steps, 0, {}, None)

        return run

    def _show_step(self, steps: tuple[Step, ...], index: int, previous_values: dict, previous_result: Any) -> None:
        step = steps[index]

        async def done(result: Any) -> None:
            if index + 1 < len(steps):
                self._show_step(steps, index + 1, view.last_values, result)
            else:
                self._navigator.show_message(self._application.saved, back=(self._application.back, self._back))

        view = self._navigator.show_screen(self._screens(step.screen), self._transports[step.transport], on_result=done)
        for field_name, value in prefill_values(step, previous_values, previous_result).items():
            view.set_value(field_name, value)

    async def _back(self) -> None:
        self.show_menu()

    async def _sign_out(self) -> None:
        await self._on_signed_out()
        self.show_login()
