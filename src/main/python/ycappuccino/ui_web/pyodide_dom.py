"""
PyodideDom: the DomBinding implementation for a real browser page running under Pyodide -- the
one render_screen() gets in production. Only __init__'s ImportError->RuntimeError fallback is
provable in this sandbox (see test_pyodide_dom.py): there is no browser or Pyodide runtime
available here (no network to fetch it, this module is plain CPython), so every method below has
NOT been exercised against real js/pyodide.ffi objects. Written from the known Pyodide/DOM API
surface (js.document.createElement, Element.appendChild/.textContent/.setAttribute/.value,
Element.addEventListener, pyodide.ffi.create_proxy) -- same honesty discipline as
ycappuccino-client's pyodide_transport.py. Manual verification in a real browser is required
before relying on this in production.

js and pyodide.ffi are imported inside __init__/on_click, never at module import time, so
ycappuccino.ui_web.app stays importable (and unit-testable, see fake_dom.py) in plain CPython.

on_click bridges a synchronous JS click event to an async Python callback via
pyodide.ffi.create_proxy(...) wrapping a sync trampoline that schedules the coroutine with
asyncio.ensure_future(...) -- unverified here: whether Pyodide's own event loop actually drives
that future to completion from inside a JS event callback is exactly the kind of thing that needs
a real browser, not assumed from documentation alone.
"""

from typing import Any, Awaitable, Callable


class PyodideDom:
    def __init__(self):
        try:
            import js
        except ImportError as error:
            raise RuntimeError(
                "no DOM available: ycappuccino.ui_web.pyodide_dom.PyodideDom requires the `js` "
                "module, which is only present when running under Pyodide in a browser. Use "
                "ycappuccino.ui_web's FakeDom (tests) or write your own DomBinding outside a "
                "browser context."
            ) from error
        self._js = js

    def create_element(self, tag: str) -> Any:
        return self._js.document.createElement(tag)

    def append_child(self, parent: Any, child: Any) -> None:
        parent.appendChild(child)

    def set_text(self, element: Any, text: str) -> None:
        element.textContent = text

    def set_attribute(self, element: Any, name: str, value: str) -> None:
        element.setAttribute(name, value)

    def get_value(self, element: Any) -> str:
        return element.value

    def set_value(self, element: Any, value: str) -> None:
        element.value = value

    def on_click(self, element: Any, callback: Callable[[], Awaitable[None]]) -> None:
        import asyncio

        from pyodide.ffi import create_proxy

        def trampoline(_event=None) -> None:
            asyncio.ensure_future(callback())

        # kept alive on the element itself: create_proxy'd callables are only safe to call back
        # from JS as long as something on the Python side still references them (Pyodide docs).
        element._ycappuccino_click_proxy = create_proxy(trampoline)
        element.addEventListener("click", element._ycappuccino_click_proxy)
