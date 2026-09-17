"""Renders a Screen as real DOM elements via a DomBinding: one input per Field, one button per
Action, validated (ycappuccino.ui.validation.validate_screen) then dispatched through
perform_action() -- same shape as ycappuccino-ui-shell's ScreenApp, DOM instead of textual
widgets. Depends only on DomBinding (dom.py), never on js/pyodide directly -- that binding is
pyodide_dom.py's job, so this module is testable with FakeDom, no browser required."""

import logging
from typing import Any, Awaitable, Callable

from ycappuccino.ui.model import Action, Field, Screen
from ycappuccino.ui.transport import Transport, perform_action
from ycappuccino.ui.validation import validate_screen

from ycappuccino.ui_web.dom import DomBinding

_logger = logging.getLogger(__name__)

OnResult = Callable[[Any], Awaitable[None]]

_FIELD_INPUT_TYPES = {"boolean": "checkbox", "password": "password", "number": "number", "date": "date"}


class ScreenView:
    def __init__(
        self,
        screen: Screen,
        transport: Transport,
        dom: DomBinding,
        field_elements: dict,
        error_elements: dict,
        action_elements: dict,
        status_element: Any = None,
        on_result: OnResult | None = None,
    ) -> None:
        self._screen = screen
        self._transport = transport
        self._dom = dom
        self.field_elements = field_elements
        self.error_elements = error_elements
        self.action_elements = action_elements
        self.status_element = status_element
        self._on_result = on_result
        self.last_values: dict[str, Any] = {}
        self.last_errors: dict[str, str] = {}
        self.last_result: Any = None
        self.last_error: str | None = None

    async def submit(self, action: Action) -> None:
        values = self._collect_values()
        errors = validate_screen(self._screen, values)
        self.last_values = values
        self.last_errors = errors
        self._render_errors(errors)
        if errors:
            return
        try:
            result = await perform_action(action, values, self._transport)
        except Exception as error:
            # a refused call (wrong password, forbidden, invalid...) is shown on the screen, which stays
            _logger.info("action %s failed", action.name, exc_info=True)
            self._show_status(str(error) or type(error).__name__)
            return
        self._show_status(None)
        self.last_result = result
        if self._on_result is not None:
            await self._on_result(result)

    def _show_status(self, message: str | None) -> None:
        self.last_error = message
        if self.status_element is not None:
            self._dom.set_text(self.status_element, message or "")

    def _collect_values(self) -> dict[str, Any]:
        return {
            a_field.name: _read_value(self._dom, a_field, self.field_elements[a_field.name])
            for a_field in self._screen.fields
        }

    def _render_errors(self, errors: dict[str, str]) -> None:
        for a_field in self._screen.fields:
            self._dom.set_text(self.error_elements[a_field.name], errors.get(a_field.name, ""))


def render_screen(
    screen: Screen, transport: Transport, dom: DomBinding, mount: Any, on_result: OnResult | None = None
) -> ScreenView:
    """on_result receives the result of every successful action, e.g. to show the next screen"""
    field_elements = {}
    error_elements = {}
    action_elements = {}

    title = dom.create_element("h2")
    dom.set_text(title, screen.title)
    dom.append_child(mount, title)

    for a_field in screen.fields:
        label = dom.create_element("label")
        dom.set_text(label, a_field.label)
        dom.append_child(mount, label)

        input_element = dom.create_element(_input_tag(a_field))
        dom.set_attribute(input_element, "type", _FIELD_INPUT_TYPES.get(a_field.type, "text"))
        dom.set_attribute(input_element, "name", a_field.name)
        if a_field.type == "choice":
            for choice in a_field.choices:
                option = dom.create_element("option")
                dom.set_text(option, choice)
                dom.set_attribute(option, "value", choice)
                dom.append_child(input_element, option)
        dom.append_child(mount, input_element)
        field_elements[a_field.name] = input_element

        error_element = dom.create_element("span")
        dom.append_child(mount, error_element)
        error_elements[a_field.name] = error_element

    status_element = dom.create_element("p")
    dom.set_attribute(status_element, "role", "alert")
    view = ScreenView(
        screen, transport, dom, field_elements, error_elements, action_elements, status_element, on_result
    )

    for action in screen.actions:
        button = dom.create_element("button")
        dom.set_text(button, action.label)
        dom.append_child(mount, button)
        action_elements[action.name] = button
        dom.on_click(button, _submit_handler(view, action))

    dom.append_child(mount, status_element)
    return view


def _submit_handler(view: ScreenView, action: Action) -> Callable:
    async def handler() -> None:
        await view.submit(action)

    return handler


def _input_tag(a_field: Field) -> str:
    return "select" if a_field.type == "choice" else "input"


def _read_value(dom: DomBinding, a_field: Field, element: Any) -> Any:
    raw = dom.get_value(element)
    if a_field.type == "boolean":
        return raw in ("true", "True", "1", True)
    if a_field.type == "number":
        return None if raw == "" else _to_number(raw)
    if a_field.type == "list":
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def _to_number(raw: str) -> int | float:
    try:
        return int(raw)
    except ValueError:
        return float(raw)
