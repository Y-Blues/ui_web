"""
IWebPage: the page an application component draws into, injected like any other service, so the
component never touches js/pyodide and is tested with a FakeDom. PyodidePage is the browser one: it
mounts on the element matching mount_selector and links the stylesheets the deployment configures, both
component properties:

    components:
      PyodidePage:
        mount_selector: "#app"
        stylesheets: "style.css"          # comma separated URLs, relative to the page

The library ships no theme: it only puts yc-* classes on its elements, the application's configuration
styles them.
"""

from abc import ABC, abstractmethod
from typing import Any

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.ui_web.dom import DomBinding
from ycappuccino.ui_web.navigation import Navigator
from ycappuccino.ui_web.pyodide_dom import PyodideDom


def link_stylesheets(dom: DomBinding, head: Any, stylesheets: str) -> None:
    """one link rel=stylesheet in the head per comma separated URL"""
    for href in (part.strip() for part in stylesheets.split(",")):
        if not href:
            continue
        link = dom.create_element("link")
        dom.set_attribute(link, "rel", "stylesheet")
        dom.set_attribute(link, "href", href)
        dom.append_child(head, link)


class IWebPage(YCappuccinoComponent, ABC):

    @abstractmethod
    def navigator(self) -> Navigator:
        """the navigator showing screens, menus and messages on this page"""


class PyodidePage(IWebPage):

    def __init__(self, mount_selector: str = "#app", stylesheets: str = "") -> None:
        self._mount_selector = mount_selector
        self._stylesheets = stylesheets
        self._navigator: Navigator | None = None

    async def start(self) -> None:
        dom = PyodideDom()
        mount = dom.query(self._mount_selector)
        if mount is None:
            raise RuntimeError(f"no element matches {self._mount_selector!r} on this page")
        link_stylesheets(dom, dom.query("head"), self._stylesheets)
        self._navigator = Navigator(dom, mount)

    async def stop(self) -> None:
        pass

    def navigator(self) -> Navigator:
        return self._navigator
