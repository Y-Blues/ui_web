# ycappuccino-ui-web

Rend un `ycappuccino.ui.model.Screen` en vrais éléments DOM, en direct dans le navigateur sous
Pyodide (`ycappuccino-client`) — **pas de génération HTML côté serveur**. Décision utilisateur
explicite du 2026-09-16 (voir
[`remote/docs/superpowers/specs/2026-09-16-ui-screen-library-checkpoint.md`](../remote/docs/superpowers/specs/2026-09-16-ui-screen-library-checkpoint.md)),
qui hérite intégralement des risques d'exécution navigateur déjà documentés dans
[`client/README.md`](../client/README.md) (vrais threads OS sous Pyodide, PyYAML dans la liste
curatée, tension COOP/COEP) — ce dépôt ne referme aucun de ces risques, il en dépend.

Prérequis : lire le README de [ui](../ui/README.md) (le modèle `Screen`/`Field`/`Action`/
`Endpoint`, la validation, `Transport`/`perform_action`) et de [client](../client/README.md) (le
runtime Pyodide dont cet adapter dépend pour tourner réellement dans un navigateur). Ce dépôt
n'ajoute rien au modèle `ui`, il le rend — même rôle que `ycappuccino-ui-shell` pour le terminal.

## `DomBinding` : la seule chose que ce dépôt invente

`client` (`components.py`/`transport.py`/`remote_proxy.py`) ne fournit que des proxys d'accès aux
données (`RemoteCrud`, `RemoteServiceEndpoint`, ...) — **aucune primitive de manipulation du DOM**
n'existait nulle part avant ce dépôt. `ycappuccino.ui_web.dom.DomBinding` est ce `Protocol`
minimal (`create_element`, `append_child`, `set_text`, `set_attribute`, `get_value`, `set_value`,
`on_click`) : `render_screen()` (`app.py`) ne connaît que cette interface, jamais `js`/`pyodide`
directement — exactement le rôle que `Transport` joue pour `ycappuccino.ui`, ou `IHttpFetcher` pour
`client`. Deux implémentations :

- `ycappuccino.ui_web.pyodide_dom.PyodideDom` — la vraie, contre `js.document`/`pyodide.ffi`,
  utilisée en production.
- `FakeDom` (`ycappuccino.ui_web.testing`) — un arbre en mémoire, réel (pas un mock), utilisé
  par tous les tests de ce dépôt et utilisable par ceux d'une application (`find_field(mount, nom)`,
  `find_button(mount, libellé)`) : ils vérifient un vrai état d'arbre (attributs, enfants,
  valeurs) et peuvent réellement déclencher un callback de clic enregistré et l'attendre.

## Afficher un écran

```python
from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.app import render_screen
from ycappuccino.ui_web.pyodide_dom import PyodideDom  # navigateur réel uniquement

screen = Screen(
    title="Connexion",
    fields=(Field(name="username", label="Nom d'utilisateur", required=True),),
    actions=(Action(name="submit", label="Se connecter", endpoint=Endpoint(service="login")),),
)

dom = PyodideDom()
mount = dom.create_element("div")
# dom.append_child(js.document.body, mount)  # attacher au vrai document, navigateur uniquement

view = render_screen(screen, transport, dom, mount)
# view.field_elements["username"], view.action_elements["submit"], view.last_result, ...
```

`transport` est n'importe quel `ycappuccino.ui.transport.Transport`, typiquement un pont de `ui`
(`CrudTransport`, `ServiceEndpointTransport`, `ComponentTransport`) sur une interface backend injectée :
un proxy généré dans un navigateur, l'implémentation elle-même dans le process du backend.

## Valider et soumettre

`render_screen` câble déjà tout : chaque bouton d'action a un callback `on_click` qui collecte les
valeurs des champs (`DomBinding.get_value`, coercée selon `Field.type` — `number`→`int`/`float`,
`boolean`→`bool`, `list`→liste séparée par virgules), les valide
(`ycappuccino.ui.validation.validate_screen`, même règles que tous les adapters), affiche les
erreurs inline (`view.error_elements[name]`) et n'appelle `perform_action` que si tout est valide.
Rien de ceci n'est à réécrire par l'application :

```python
view.field_elements["username"]   # l'élément <input> DOM du champ
view.error_elements["username"]   # l'élément où son message d'erreur est écrit
view.action_elements["submit"]    # le <button> de l'action
view.last_result                  # ce que perform_action() a renvoyé, après le dernier clic réussi
```

## Erreurs et résultat

Un appel refusé par le backend (`InvalidRequest`, `Forbidden`...) n'interrompt rien : son message est écrit
dans `view.status_element` (un `<p role="alert">` sous les boutons), gardé dans `view.last_error`, et l'écran
reste affiché. Un appel réussi efface ce message, remplit `view.last_result` et passe le résultat à
`on_result`, si `render_screen(..., on_result=...)` en a reçu un.

## Plusieurs écrans : `Navigator`

`ycappuccino.ui_web.navigation.Navigator(dom, mount)` montre une chose à la fois dans `mount`, chaque
appel remplaçant la précédente :

```python
navigator.show_screen(login_screen, transport, on_result=signed_in)   # un écran ; signed_in(result)
navigator.show_menu("Administration", [("Créer un rôle", create_role), ("Se déconnecter", sign_out)])
navigator.show_message("Utilisateur créé", back=("Retour au menu", show_menu))
```

Les choix (`create_role`, `sign_out`...) sont des fonctions sans argument qui renvoient une coroutine.

## Une console entière : `WebApplication`

`ycappuccino.ui_web.application.WebApplication(application, navigator, screens, transports, on_signed_in,
on_signed_out)` rend une `ycappuccino.ui.application.Application` (voir le README de `ui`) : écran de
connexion, menu, écrans enchaînés et pré-remplis, message « Enregistré. », déconnexion. `ui_shell` rend la
même `Application` en terminal. `screens` charge un `Screen` par son nom, `transports` associe un nom à un
`Transport` ; `on_signed_in(résultat)` reçoit le résultat de la connexion (un jeton, par exemple).

## La page : `IWebPage`

Un composant applicatif ne crée pas son DOM : il dépend de `ycappuccino.ui_web.page.IWebPage` et dessine
avec `page.navigator()`. `PyodidePage`, publié quand `ycappuccino.ui_web.page` est dans `bundle_prefix`, se
monte sur l'élément `mount_selector` (`#app` par défaut, `components: PyodidePage: mount_selector: ...`).
Un test fournit sa propre `IWebPage` sur un `FakeDom`.

## Tester un écran

Comme `ui_shell`, aucun mock — un vrai arbre `FakeDom`, un vrai callback de clic attendu :

```python
import unittest

from ycappuccino.ui.model import Action, Endpoint, Field, Screen
from ycappuccino.ui_web.app import render_screen

from ycappuccino.ui_web.testing import FakeDom


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
```

## Vérifié dans un vrai navigateur (2026-09-17)

Chromium (Playwright), Pyodide 0.28.3, avec la console web de `permissions_app` : `PyodideDom` et
`PyodidePage` construisent la page, les clics déclenchent les coroutines Python (`create_proxy` +
`asyncio.ensure_future`), les valeurs saisies sont relues, les erreurs du backend s'affichent, `Navigator`
enchaîne écrans, menus et messages. Non vérifiés : Firefox et Safari, et le rendu réel des champs
`date`/`choice`.

## Ce qui n'est pas encore fait

- **Layout au-delà d'une liste verticale simple** (pas de grille/sections/écrans imbriqués) — même
  limite que `ui_shell`, non nécessaire pour prouver le modèle.
- **Bootstrap navigateur** : aucun ici, un déploiement utilise la page générique de `client/static/`.

## Développer ui_web

```bash
uv sync
uv run python -m unittest discover -s src/unittest/python
```
