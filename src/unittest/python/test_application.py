import unittest

from ycappuccino.ui.application import load_application_yaml
from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.application import WebApplication
from ycappuccino.ui_web.navigation import Navigator
from ycappuccino.ui_web.testing import FakeDom, find_button, find_field, texts

APPLICATION = load_application_yaml("""
title: Administration
login: {screen: login, transport: auth}
menu:
  - label: Créer un rôle
    steps:
      - {screen: role, transport: data}
  - label: Créer un utilisateur
    steps:
      - {screen: credentials, transport: data}
      - {screen: profile, transport: data, prefill: {login: values.login, id: result._id}}
""")


def _screen(title, *names):
    return Screen(
        title=title,
        fields=tuple(Field(name=name, label=name) for name in names),
        actions=(Action(name="submit", label="Valider", endpoint=Endpoint(service=title)),),
    )


SCREENS = {
    "login": _screen("login", "user"),
    "role": _screen("role", "name"),
    "credentials": _screen("credentials", "login"),
    "profile": _screen("profile", "login", "id", "name"),
}


class Transport:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def call(self, service, method, path, params, body):
        if self.fail:
            raise ValueError("refused")
        self.calls.append((service, body))
        return {"_id": f"{service}-1"}


class TestWebApplication(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.dom = FakeDom()
        self.mount = self.dom.create_element("div")
        self.auth = Transport()
        self.data = Transport()
        self.events = []

        async def signed_in(result):
            self.events.append(("in", result))

        async def signed_out():
            self.events.append(("out",))

        self.application = WebApplication(
            APPLICATION, Navigator(self.dom, self.mount), SCREENS.__getitem__,
            {"auth": self.auth, "data": self.data}, signed_in, signed_out,
        )
        self.application.start()

    async def _submit(self, **values):
        for name, value in values.items():
            self.dom.set_value(find_field(self.mount, name), value)
        await self.dom.click(find_button(self.mount, "Valider"))

    async def _choose(self, label):
        await self.dom.click(find_button(self.mount, label))

    async def test_login_then_the_menu_with_its_entries_and_sign_out(self):
        await self._submit(user="alice")

        self.assertEqual(self.events, [("in", {"_id": "login-1"})])
        self.assertEqual(texts(self.mount), ["Administration", "Créer un rôle", "Créer un utilisateur", "Se déconnecter"])

    async def test_a_refused_login_stays_on_the_login_screen(self):
        self.auth.fail = True

        await self._submit(user="alice")

        self.assertEqual(self.events, [])
        self.assertIn("refused", texts(self.mount))

    async def test_an_entry_runs_its_step_then_shows_saved_and_back_to_the_menu(self):
        await self._submit(user="alice")
        await self._choose("Créer un rôle")
        await self._submit(name="editor")

        self.assertEqual(self.data.calls, [("role", {"name": "editor"})])
        self.assertEqual(texts(self.mount), ["Enregistré.", "Retour au menu"])
        await self._choose("Retour au menu")
        self.assertIn("Créer un rôle", texts(self.mount))

    async def test_chained_steps_are_prefilled_from_the_previous_one(self):
        await self._submit(user="alice")
        await self._choose("Créer un utilisateur")
        await self._submit(login="bob")

        self.assertEqual((find_field(self.mount, "login").value, find_field(self.mount, "id").value), ("bob", "credentials-1"))
        await self._submit(name="Bob")
        self.assertEqual(self.data.calls[-1], ("profile", {"login": "bob", "id": "credentials-1", "name": "Bob"}))
        self.assertEqual(texts(self.mount), ["Enregistré.", "Retour au menu"])

    async def test_sign_out_returns_to_the_login_screen(self):
        await self._submit(user="alice")

        await self._choose("Se déconnecter")

        self.assertEqual(self.events[-1], ("out",))
        self.assertIn("login", texts(self.mount))


if __name__ == "__main__":
    unittest.main()
