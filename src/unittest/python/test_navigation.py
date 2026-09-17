import unittest

from fake_dom import FakeDom, texts

from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.navigation import Navigator


class FakeTransport:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def call(self, service, method, path, params, body):
        self.calls.append((service, method, path, params, body))
        return self.result


def _screen(title):
    return Screen(
        title=title,
        fields=(Field(name="name", label="Nom"),),
        actions=(Action(name="submit", label="Valider", endpoint=Endpoint(service="svc")),),
    )


class TestNavigator(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.dom = FakeDom()
        self.mount = self.dom.create_element("div")
        self.navigator = Navigator(self.dom, self.mount)

    def test_showing_a_screen_replaces_what_was_shown(self):
        self.navigator.show_screen(_screen("Premier"), FakeTransport())
        self.navigator.show_screen(_screen("Second"), FakeTransport())

        self.assertIn("Second", texts(self.mount))
        self.assertNotIn("Premier", texts(self.mount))

    async def test_a_result_can_navigate_to_the_next_screen(self):
        async def next_screen(result):
            self.navigator.show_screen(_screen(f"Bienvenue {result}"), FakeTransport())

        view = self.navigator.show_screen(_screen("Connexion"), FakeTransport(result="alice"), on_result=next_screen)

        await self.dom.click(view.action_elements["submit"])

        self.assertIn("Bienvenue alice", texts(self.mount))
        self.assertNotIn("Connexion", texts(self.mount))

    async def test_a_menu_shows_one_button_per_entry_and_runs_the_chosen_one(self):
        chosen = []

        async def choose(label):
            chosen.append(label)

        buttons = self.navigator.show_menu(
            "Administration",
            [("Créer un rôle", lambda: choose("role")), ("Se déconnecter", lambda: choose("logout"))],
        )

        await self.dom.click(buttons["Se déconnecter"])

        self.assertEqual(texts(self.mount), ["Administration", "Créer un rôle", "Se déconnecter"])
        self.assertEqual(chosen, ["logout"])

    def test_a_message_is_shown_alone_with_a_way_back(self):
        buttons = self.navigator.show_message("Utilisateur créé", back=("Retour au menu", None))

        self.assertEqual(texts(self.mount), ["Utilisateur créé", "Retour au menu"])
        self.assertIn("Retour au menu", buttons)


if __name__ == "__main__":
    unittest.main()
