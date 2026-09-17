import asyncio
import inspect
import unittest

from ycappuccino.api.core_base import YCappuccinoComponent
from ycappuccino.ui_web.page import IWebPage, PyodidePage


class TestWebPage(unittest.TestCase):

    def test_the_page_is_an_abstract_component_giving_a_navigator(self):
        self.assertTrue(issubclass(IWebPage, YCappuccinoComponent))
        self.assertTrue(inspect.isabstract(IWebPage))
        self.assertTrue(issubclass(PyodidePage, IWebPage))

    def test_the_pyodide_page_fails_clearly_outside_a_browser(self):
        page = PyodidePage(mount_selector="#app")

        with self.assertRaises(RuntimeError):
            asyncio.run(page.start())


if __name__ == "__main__":
    unittest.main()
