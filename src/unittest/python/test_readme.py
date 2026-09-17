"""Every code block in README.md is reproduced here verbatim (PyodideDom() itself is never
called -- no js/pyodide in this sandbox, see test_pyodide_dom.py) -- if this test fails, fix the
code or the README, whichever is wrong; the test is the source of truth."""

import unittest

from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.app import render_screen

from fake_dom import FakeDom


class FakeTransport:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def call(self, service, method, path, params, body):
        self.calls.append((service, method, path, params, body))
        return self.result


class TestLogin(unittest.IsolatedAsyncioTestCase):
    async def test_submits_the_username(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result={"token": "abc"})
        screen = Screen(
            title="Connexion",
            fields=(Field(name="username", label="Nom d'utilisateur", required=True),),
            actions=(Action(name="submit", label="Se connecter", endpoint=Endpoint(service="login")),),
        )
        view = render_screen(screen, transport, dom, mount)
        dom.set_value(view.field_elements["username"], "aurelien")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("login", "POST", (), {}, {"username": "aurelien"})])
        self.assertEqual(view.last_result, {"token": "abc"})
