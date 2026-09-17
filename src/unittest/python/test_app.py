import unittest

from ycappuccino.ui.model import Action, Endpoint, Field, Screen

from fake_dom import FakeDom
from ycappuccino.ui_web.app import render_screen


class FakeTransport:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def call(self, service, method, path, params, body):
        self.calls.append((service, method, path, params, body))
        return self.result


def _login_screen():
    return Screen(
        title="Connexion",
        fields=(Field(name="username", label="Nom d'utilisateur", required=True),),
        actions=(Action(name="submit", label="Se connecter", endpoint=Endpoint(service="login")),),
    )


class TestRenderScreen(unittest.TestCase):
    def test_creates_one_input_per_field_and_one_button_per_action(self):
        dom = FakeDom()
        mount = dom.create_element("div")

        view = render_screen(_login_screen(), FakeTransport(), dom, mount)

        self.assertIn("username", view.field_elements)
        self.assertEqual(view.field_elements["username"].tag, "input")
        self.assertIn(view.field_elements["username"], mount.children)

    def test_button_carries_the_action_label(self):
        dom = FakeDom()
        mount = dom.create_element("div")

        view = render_screen(_login_screen(), FakeTransport(), dom, mount)

        self.assertIn("submit", view.action_elements)
        self.assertEqual(view.action_elements["submit"].text, "Se connecter")


class TestFieldTypes(unittest.TestCase):
    def test_choice_field_uses_select_tag(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        screen = Screen(
            title="t",
            fields=(Field(name="role", label="Role", type="choice", choices=("admin", "member")),),
        )

        view = render_screen(screen, FakeTransport(), dom, mount)

        self.assertEqual(view.field_elements["role"].tag, "select")

    def test_choice_field_gets_one_option_per_choice(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        screen = Screen(
            title="t",
            fields=(Field(name="role", label="Role", type="choice", choices=("admin", "member")),),
        )

        view = render_screen(screen, FakeTransport(), dom, mount)

        select = view.field_elements["role"]
        self.assertEqual([option.tag for option in select.children], ["option", "option"])
        self.assertEqual([option.text for option in select.children], ["admin", "member"])
        self.assertEqual([option.attrs["value"] for option in select.children], ["admin", "member"])

    def test_number_field_input_type(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        screen = Screen(title="t", fields=(Field(name="age", label="Age", type="number"),))

        view = render_screen(screen, FakeTransport(), dom, mount)

        self.assertEqual(view.field_elements["age"].attrs["type"], "number")


class TestSubmitFieldCoercion(unittest.IsolatedAsyncioTestCase):
    async def test_number_field_is_coerced_before_the_call(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result=None)
        screen = Screen(
            title="t",
            fields=(Field(name="age", label="Age", type="number"),),
            actions=(Action(name="submit", label="Go", endpoint=Endpoint(service="svc")),),
        )
        view = render_screen(screen, transport, dom, mount)
        dom.set_value(view.field_elements["age"], "42")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("svc", "POST", (), {}, {"age": 42})])

    async def test_choice_field_sends_the_selected_value(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result=None)
        screen = Screen(
            title="t",
            fields=(Field(name="role", label="Role", type="choice", choices=("admin", "member")),),
            actions=(Action(name="submit", label="Go", endpoint=Endpoint(service="svc")),),
        )
        view = render_screen(screen, transport, dom, mount)
        dom.set_value(view.field_elements["role"], "member")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("svc", "POST", (), {}, {"role": "member"})])

    async def test_boolean_field_is_coerced_before_the_call(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result=None)
        screen = Screen(
            title="t",
            fields=(Field(name="active", label="Active", type="boolean"),),
            actions=(Action(name="submit", label="Go", endpoint=Endpoint(service="svc")),),
        )
        view = render_screen(screen, transport, dom, mount)
        dom.set_value(view.field_elements["active"], "true")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("svc", "POST", (), {}, {"active": True})])

    async def test_list_field_is_split_on_comma_before_the_call(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result=None)
        screen = Screen(
            title="t",
            fields=(Field(name="tags", label="Tags", type="list"),),
            actions=(Action(name="submit", label="Go", endpoint=Endpoint(service="svc")),),
        )
        view = render_screen(screen, transport, dom, mount)
        dom.set_value(view.field_elements["tags"], "a, b ,c")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("svc", "POST", (), {}, {"tags": ["a", "b", "c"]})])


class TestSubmit(unittest.IsolatedAsyncioTestCase):
    async def test_valid_submit_calls_transport_and_stores_result(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport(result={"token": "abc"})
        view = render_screen(_login_screen(), transport, dom, mount)
        dom.set_value(view.field_elements["username"], "aurelien")

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [("login", "POST", (), {}, {"username": "aurelien"})])
        self.assertEqual(view.last_result, {"token": "abc"})

    async def test_missing_required_field_blocks_the_call_and_shows_the_error(self):
        dom = FakeDom()
        mount = dom.create_element("div")
        transport = FakeTransport()
        view = render_screen(_login_screen(), transport, dom, mount)

        await dom.click(view.action_elements["submit"])

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            view.error_elements["username"].text,
            "Nom d'utilisateur is required",
        )


if __name__ == "__main__":
    unittest.main()
