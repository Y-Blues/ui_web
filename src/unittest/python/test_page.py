import asyncio
from pathlib import Path
import inspect
import unittest

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.ui_web.page import IWebPage, PyodidePage, install_stylesheet
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


    def test_a_stylesheet_given_by_the_application_goes_in_the_head(self):
        dom = FakeDom()
        head = dom.create_element("head")

        install_stylesheet(dom, head, ".yc-nav { color: red; }")

        (style,) = head.children
        self.assertEqual((style.tag, style.text), ("style", ".yc-nav { color: red; }"))

    def test_the_library_ships_no_theme(self):
        import ycappuccino.ui_web

        package = Path(ycappuccino.ui_web.__file__).parent
        self.assertEqual(list(package.glob("*.css")), [])
        self.assertIn("add_stylesheet", IWebPage.__abstractmethods__)

if __name__ == "__main__":
    unittest.main()
