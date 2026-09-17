"""The only behaviour of PyodideDom provable in this sandbox: CPython genuinely has no `js`
module, so constructing it here really does hit the ImportError -> RuntimeError path -- not
mocked. Everything past that (actual js.document/pyodide.ffi calls) needs a real browser, see
pyodide_dom.py's module docstring."""

import unittest

from ycappuccino.ui_web.pyodide_dom import PyodideDom


class TestPyodideDomOutsidePyodide(unittest.TestCase):
    def test_fails_clearly_outside_pyodide(self):
        with self.assertRaises(RuntimeError) as raised:
            PyodideDom()
        self.assertIn("pyodide", str(raised.exception).lower())
