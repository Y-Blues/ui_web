"""
WebApplication: renders a ycappuccino.ui.application.Application as a site -- a bar (header.yc-nav) naming
it above the login screen, then the same bar with one details.yc-menu dropdown per menu section, the
signed-in user and sign-out, above the content (main.yc-content): the welcome, each entry's chained screens (prefilled from the
previous one), the saved message. ui_shell's ShellApplication renders the same Application in a terminal.
"""

from typing import Any, Awaitable, Callable

from ycappuccino.ui.application import Application, MenuGroup, Step, prefill_values
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
        """navigator's mount receives the whole application; on_signed_in receives the login step's result
        (e.g. a token), on_signed_out runs on sign-out"""
        self._application = application
        self._dom = navigator.dom
        self._root = navigator.mount
        self._screens = screens
        self._transports = transports
        self._on_signed_in = on_signed_in
        self._on_signed_out = on_signed_out
        self._content: Navigator | None = None

    def start(self) -> None:
        self.show_login()

    def show_login(self) -> None:
        self._dom.clear(self._root)
        self._bar()
        page = self._element(self._root, "main", "yc-content yc-login")
        login = self._application.login

        async def signed_in(result: Any) -> None:
            await self._on_signed_in(result)
            user = view.last_values.get(self._application.user_field) if self._application.user_field else None
            self.show_home(user)

        view = Navigator(self._dom, page).show_screen(
            self._screens(login.screen), self._transports[login.transport], on_result=signed_in
        )

    def show_home(self, user: str | None) -> None:
        self._dom.clear(self._root)
        nav = self._bar()
        menus = self._element(nav, "nav", "yc-menus")
        dropdowns: list = []
        for group in self._application.menu:
            self._dropdown(menus, group, dropdowns)
        session = self._element(nav, "div", "yc-session")
        if user:
            self._dom.set_text(self._element(session, "span", "yc-user"), user)
        sign_out = self._element(session, "button", "yc-button yc-sign-out")
        self._dom.set_text(sign_out, self._application.sign_out)
        self._dom.on_click(sign_out, self._sign_out)

        self._content = Navigator(self._dom, self._element(self._root, "main", "yc-content"))
        self._content.show_message(self._application.welcome_text(user))

    def _bar(self) -> Any:
        """the site bar, naming the site; once signed in it also holds the menus and the session"""
        nav = self._element(self._root, "header", "yc-nav")
        self._dom.set_text(self._element(nav, "span", "yc-brand"), self._application.title)
        return nav

    def _dropdown(self, parent: Any, group: MenuGroup, dropdowns: list) -> None:
        dropdown = self._element(parent, "details", "yc-menu")
        dropdowns.append(dropdown)
        label = self._element(dropdown, "summary", "yc-menu-label")
        self._dom.set_text(label, group.label)

        async def close_the_others() -> None:
            # the browser toggles this one itself
            for other in dropdowns:
                if other is not dropdown:
                    self._dom.remove_attribute(other, "open")

        self._dom.on_click(label, close_the_others)
        items = self._element(dropdown, "div", "yc-menu-items")
        for entry in group.entries:
            item = self._element(items, "button", "yc-menu-item")
            self._dom.set_text(item, entry.label)
            self._dom.on_click(item, self._runner(dropdown, entry.steps))

    def _runner(self, dropdown: Any, steps: tuple[Step, ...]) -> Callable[[], Awaitable[None]]:
        async def run() -> None:
            self._dom.remove_attribute(dropdown, "open")
            self._show_step(steps, 0, {}, None)

        return run

    def _show_step(self, steps: tuple[Step, ...], index: int, previous_values: dict, previous_result: Any) -> None:
        step = steps[index]

        async def done(result: Any) -> None:
            if index + 1 < len(steps):
                self._show_step(steps, index + 1, view.last_values, result)
            else:
                self._content.show_message(self._application.saved)

        view = self._content.show_screen(self._screens(step.screen), self._transports[step.transport], on_result=done)
        for field_name, value in prefill_values(step, previous_values, previous_result).items():
            view.set_value(field_name, value)

    async def _sign_out(self) -> None:
        await self._on_signed_out()
        self.show_login()

    def _element(self, parent: Any, tag: str, css_class: str) -> Any:
        element = self._dom.create_element(tag)
        self._dom.set_attribute(element, "class", css_class)
        self._dom.append_child(parent, element)
        return element
