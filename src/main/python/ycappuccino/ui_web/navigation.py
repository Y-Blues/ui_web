"""
Navigator: one mount element showing one thing at a time -- a screen, a menu or a message. Each show_*
replaces what was shown; the flow between them is the application's (a screen's on_result showing the
next one, a menu entry showing a screen).
"""

from typing import Any, Awaitable, Callable, Sequence

from ycappuccino.ui.model import Screen
from ycappuccino.ui.transport import Transport
from ycappuccino.ui_web.app import OnResult, ScreenView, render_screen
from ycappuccino.ui_web.dom import DomBinding

Choice = Callable[[], Awaitable[None]]


class Navigator:

    def __init__(self, dom: DomBinding, mount: Any) -> None:
        self.dom = dom
        self.mount = mount

    def show_screen(self, screen: Screen, transport: Transport, on_result: OnResult | None = None) -> ScreenView:
        self.dom.clear(self.mount)
        return render_screen(screen, transport, self.dom, self.mount, on_result=on_result)

    def show_menu(self, title: str, entries: Sequence[tuple[str, Choice]]) -> dict[str, Any]:
        """label -> button; clicking one runs its choice"""
        self.dom.clear(self.mount)
        heading = self.dom.create_element("h2")
        self.dom.set_text(heading, title)
        self.dom.append_child(self.mount, heading)
        return {label: self._button(label, choice) for label, choice in entries}

    def show_message(self, text: str, back: tuple[str, Choice | None]) -> dict[str, Any]:
        self.dom.clear(self.mount)
        message = self.dom.create_element("p")
        self.dom.set_text(message, text)
        self.dom.append_child(self.mount, message)
        label, choice = back
        return {label: self._button(label, choice)}

    def _button(self, label: str, choice: Choice | None) -> Any:
        button = self.dom.create_element("button")
        self.dom.set_text(button, label)
        self.dom.append_child(self.mount, button)
        if choice is not None:
            self.dom.on_click(button, choice)
        return button
