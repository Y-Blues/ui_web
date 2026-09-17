"""
IWebPage: the page an application component draws into, injected like any other service, so the
component never touches js/pyodide and is tested with a FakeDom. PyodidePage is the browser one: it
mounts on the element matching mount_selector (components: PyodidePage: mount_selector: "#main").
"""

from abc import ABC, abstractmethod

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.ui_web.navigation import Navigator
from ycappuccino.ui_web.pyodide_dom import PyodideDom


class IWebPage(YCappuccinoComponent, ABC):

    @abstractmethod
    def navigator(self) -> Navigator:
        """the navigator showing screens, menus and messages on this page"""


class PyodidePage(IWebPage):

    def __init__(self, mount_selector: str = "#app") -> None:
        self._mount_selector = mount_selector
        self._navigator: Navigator | None = None

    async def start(self) -> None:
        dom = PyodideDom()
        mount = dom.query(self._mount_selector)
        if mount is None:
            raise RuntimeError(f"no element matches {self._mount_selector!r} on this page")
        self._navigator = Navigator(dom, mount)

    async def stop(self) -> None:
        pass

    def navigator(self) -> Navigator:
        return self._navigator
