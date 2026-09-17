import unittest

from ycappuccino.ui.application import load_application_yaml
from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.application import WebApplication
from ycappuccino.ui_web.navigation import Navigator
from ycappuccino.ui_web.testing import FakeDom, find_button, find_field, texts

APPLICATION = load_application_yaml("""
title: Administration
login: {screen: login, transport: auth, user: user}
menu:
  - label: Rôles
    entries:
      - label: Créer un rôle
        steps:
          - {screen: role, transport: data}
  - label: Utilisateurs
    entries:
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


def _by_class(element, name):
    found = [element] if element.attrs.get("class", "").split().count(name) else []
    for child in element.children:
        found.extend(_by_class(child, name))
    return found


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

        WebApplication(
            APPLICATION, Navigator(self.dom, self.mount), SCREENS.__getitem__,
            {"auth": self.auth, "data": self.data}, signed_in, signed_out,
        ).start()

    async def _submit(self, **values):
        for name, value in values.items():
            self.dom.set_value(find_field(self.mount, name), value)
        await self.dom.click(find_button(self.mount, "Valider"))

    async def _choose(self, label):
        await self.dom.click(find_button(self.mount, label))

    def _content(self):
        (content,) = _by_class(self.mount, "yc-content")
        return content

    def test_before_login_the_bar_only_names_the_site(self):
        (nav,) = _by_class(self.mount, "yc-nav")
        self.assertEqual(texts(nav), ["Administration"])
        self.assertEqual(_by_class(nav, "yc-menu"), [])
        self.assertIn("login", texts(self._content()))

    async def test_login_shows_the_bar_with_one_dropdown_per_section_the_user_and_the_welcome(self):
        await self._submit(user="alice")

        self.assertEqual(self.events, [("in", {"_id": "login-1"})])
        (nav,) = _by_class(self.mount, "yc-nav")
        dropdowns = _by_class(nav, "yc-menu")
        self.assertEqual([dropdown.tag for dropdown in dropdowns], ["details", "details"])
        self.assertEqual(
            [texts(dropdown) for dropdown in dropdowns], [["Rôles", "Créer un rôle"], ["Utilisateurs", "Créer un utilisateur"]]
        )
        self.assertEqual([texts(user) for user in _by_class(nav, "yc-user")], [["alice"]])
        self.assertIsNotNone(find_button(nav, "Se déconnecter"))
        self.assertEqual(texts(self._content()), ["Bienvenue alice."])

    async def test_opening_a_dropdown_closes_the_other_ones(self):
        await self._submit(user="alice")
        roles, users = _by_class(self.mount, "yc-menu")
        roles.attrs["open"] = ""

        await self.dom.click(_by_class(users, "yc-menu-label")[0])

        self.assertNotIn("open", roles.attrs)

    async def test_a_refused_login_stays_on_the_login_screen(self):
        self.auth.fail = True

        await self._submit(user="alice")

        self.assertEqual(self.events, [])
        self.assertIn("refused", texts(self.mount))

    async def test_an_entry_closes_its_dropdown_runs_its_step_and_keeps_the_bar(self):
        await self._submit(user="alice")
        (dropdown, _) = _by_class(self.mount, "yc-menu")
        dropdown.attrs["open"] = ""

        await self._choose("Créer un rôle")
        self.assertNotIn("open", dropdown.attrs)
        await self._submit(name="editor")

        self.assertEqual(self.data.calls, [("role", {"name": "editor"})])
        self.assertEqual(texts(self._content()), ["Enregistré."])
        self.assertEqual(len(_by_class(self.mount, "yc-nav")), 1)

    async def test_chained_steps_are_prefilled_from_the_previous_one(self):
        await self._submit(user="alice")
        await self._choose("Créer un utilisateur")
        await self._submit(login="bob")

        self.assertEqual((find_field(self.mount, "login").value, find_field(self.mount, "id").value), ("bob", "credentials-1"))
        await self._submit(name="Bob")
        self.assertEqual(self.data.calls[-1], ("profile", {"login": "bob", "id": "credentials-1", "name": "Bob"}))
        self.assertEqual(texts(self._content()), ["Enregistré."])

    async def test_sign_out_removes_the_menus_and_returns_to_the_login_screen(self):
        await self._submit(user="alice")

        await self._choose("Se déconnecter")

        self.assertEqual(self.events[-1], ("out",))
        self.assertEqual(_by_class(self.mount, "yc-menu"), [])
        self.assertIsNotNone(find_field(self.mount, "user"))
