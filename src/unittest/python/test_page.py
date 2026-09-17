import asyncio
from pathlib import Path
import inspect
import unittest

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.ui_web.page import IWebPage, PyodidePage, link_stylesheets
from ycappuccino.ui_web.testing import FakeDom


class TestWebPage(unittest.TestCase):

    def test_the_page_is_an_abstract_component_giving_a_navigator(self):
        self.assertTrue(issubclass(IWebPage, YCappuccinoComponent))
        self.assertTrue(inspect.isabstract(IWebPage))
        self.assertTrue(issubclass(PyodidePage, IWebPage))

    def test_the_pyodide_page_fails_clearly_outside_a_browser(self):
        page = PyodidePage(mount_selector="#app")

        with self.assertRaises(RuntimeError):
            asyncio.run(page.start())


    def test_the_configured_stylesheets_are_linked_in_the_head(self):
        dom = FakeDom()
        head = dom.create_element("head")

        link_stylesheets(dom, head, "style.css, theme/dark.css")

        self.assertEqual(
            [(link.tag, link.attrs) for link in head.children],
            [
                ("link", {"rel": "stylesheet", "href": "style.css"}),
                ("link", {"rel": "stylesheet", "href": "theme/dark.css"}),
            ],
        )

    def test_no_configured_stylesheet_links_nothing(self):
        dom = FakeDom()
        head = dom.create_element("head")

        link_stylesheets(dom, head, "")

        self.assertEqual(head.children, [])

    def test_the_library_ships_no_theme(self):
        import ycappuccino.ui_web

        package = Path(ycappuccino.ui_web.__file__).parent
        self.assertEqual(list(package.glob("*.css")), [])
        self.assertEqual(inspect.signature(PyodidePage).parameters["stylesheets"].default, "")

if __name__ == "__main__":
    unittest.main()
