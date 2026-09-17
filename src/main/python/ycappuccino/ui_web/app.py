"""Renders a Screen as real DOM elements via a DomBinding: one input per Field, one button per
Action, validated (ycappuccino.ui.validation.validate_screen) then dispatched through
perform_action() -- same shape as ycappuccino-ui-shell's ScreenApp, DOM instead of textual
widgets. Depends only on DomBinding (dom.py), never on js/pyodide directly -- that binding is
pyodide_dom.py's job, so this module is testable with FakeDom, no browser required."""

from typing import Any

from ycappuccino.ui.model import Action, Field, Screen
from ycappuccino.ui.transport import Transport, perform_action
from ycappuccino.ui.validation import validate_screen

from ycappuccino.ui_web.dom import DomBinding

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
    ):
        self._screen = screen
        self._transport = transport
        self._dom = dom
        self.field_elements = field_elements
        self.error_elements = error_elements
        self.action_elements = action_elements
        self.last_values: dict[str, Any] = {}
        self.last_errors: dict[str, str] = {}
        self.last_result: Any = None

    async def submit(self, action: Action) -> None:
        values = self._collect_values()
        errors = validate_screen(self._screen, values)
        self.last_values = values
        self.last_errors = errors
        self._render_errors(errors)
        if errors:
            return
        self.last_result = await perform_action(action, values, self._transport)

    def _collect_values(self) -> dict[str, Any]:
        return {
            a_field.name: _read_value(self._dom, a_field, self.field_elements[a_field.name])
            for a_field in self._screen.fields
        }

    def _render_errors(self, errors: dict[str, str]) -> None:
        for a_field in self._screen.fields:
            self._dom.set_text(self.error_elements[a_field.name], errors.get(a_field.name, ""))


def render_screen(screen: Screen, transport: Transport, dom: DomBinding, mount: Any) -> ScreenView:
    field_elements = {}
    error_elements = {}
    action_elements = {}

    for a_field in screen.fields:
        label = dom.create_element("label")
        dom.set_text(label, a_field.label)
        dom.append_child(mount, label)

        input_element = dom.create_element(_input_tag(a_field))
        dom.set_attribute(input_element, "type", _FIELD_INPUT_TYPES.get(a_field.type, "text"))
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

    view = ScreenView(screen, transport, dom, field_elements, error_elements, action_elements)

    for action in screen.actions:
        button = dom.create_element("button")
        dom.set_text(button, action.label)
        dom.append_child(mount, button)
        action_elements[action.name] = button
        dom.on_click(button, _submit_handler(view, action))

    return view


def _submit_handler(view: ScreenView, action: Action):
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


def _to_number(raw: str):
    try:
        return int(raw)
    except ValueError:
        return float(raw)
