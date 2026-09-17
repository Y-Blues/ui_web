"""FakeDom: a real in-memory DomBinding implementation, not a mock -- tests assert on real tree
state (attrs, children, values) and can actually invoke a registered click callback and await it,
proving the wiring app.py does, not just that some method got called."""

from typing import Any, Awaitable, Callable


class FakeElement:
    def __init__(self, tag: str):
        self.tag = tag
        self.attrs: dict[str, str] = {}
        self.children: list["FakeElement"] = []
        self.text: str = ""
        self.value: str = ""
        self.click_callback: Callable[[], Awaitable[None]] | None = None


class FakeDom:
    def create_element(self, tag: str) -> FakeElement:
        return FakeElement(tag)

    def append_child(self, parent: FakeElement, child: FakeElement) -> None:
        parent.children.append(child)

    def set_text(self, element: FakeElement, text: str) -> None:
        element.text = text

    def set_attribute(self, element: FakeElement, name: str, value: str) -> None:
        element.attrs[name] = value

    def get_value(self, element: FakeElement) -> str:
        return element.value

    def set_value(self, element: FakeElement, value: str) -> None:
        element.value = value

    def on_click(self, element: FakeElement, callback: Callable[[], Awaitable[None]]) -> None:
        element.click_callback = callback

    async def click(self, element: FakeElement) -> Any:
        assert element.click_callback is not None, "no click callback registered on this element"
        return await element.click_callback()
