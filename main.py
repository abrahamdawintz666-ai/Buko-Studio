"""BuKo Mobile v0.9 — interface prototype for Android, powered by Kivy."""
from pathlib import Path
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window

from buko_engine_v0_6 import execute, BuKoError

EXAMPLE = '''AF afficher "Bonjour depuis BuKo Mobile !".\nAF afficher "Mon premier programme".\n'''

class BuKoMobile(App):
    title = "BuKo Studio Mobile"

    def build(self):
        self.current_path = None
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.add_widget(Label(text="[b]BuKo Studio Mobile[/b]  •  Prototype 0.9", markup=True,
                              size_hint_y=None, height=dp(34)))
        self.filename = TextInput(text="bonjour.buko", hint_text="Nom du fichier (ex. bonjour.buko)",
                                  multiline=False, size_hint_y=None, height=dp(44))
        root.add_widget(self.filename)

        actions = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        for label, callback in (("Nouveau", self.new_file), ("Ouvrir", self.open_dialog),
                                ("Enregistrer", self.save_file), ("▶ Exécuter", self.run_code)):
            btn = Button(text=label)
            btn.bind(on_release=callback)
            actions.add_widget(btn)
        root.add_widget(actions)

        root.add_widget(Label(text="Éditeur BuKo", size_hint_y=None, height=dp(24), halign="left"))
        self.editor = TextInput(text=EXAMPLE, multiline=True, font_size="16sp",
                                size_hint_y=0.62, background_color=(0.08, 0.10, 0.14, 1),
                                foreground_color=(0.92, 0.95, 1, 1), cursor_color=(0.35, 0.65, 1, 1))
        root.add_widget(self.editor)
        root.add_widget(Label(text="Résultats et erreurs", size_hint_y=None, height=dp(24)))
        self.output = TextInput(text="Prêt. Appuie sur Exécuter pour lancer le programme.",
                                readonly=True, multiline=True, size_hint_y=0.25, font_size="14sp")
        root.add_widget(self.output)
        self.status = Label(text="Les fichiers sont enregistrés dans l'espace privé de l'application.",
                            size_hint_y=None, height=dp(32), font_size="11sp")
        root.add_widget(self.status)
        Window.softinput_mode = "below_target"
        return root

    def project_dir(self):
        path = Path(self.user_data_dir) / "projets"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def safe_filename(self):
        name = self.filename.text.strip()
        if not name:
            name = "sans_nom.buko"
        if not Path(name).suffix:
            name += ".buko"
        # Keep project files inside the app's own project folder.
        name = Path(name).name
        self.filename.text = name
        return name

    def new_file(self, *_):
        self.current_path = None
        self.filename.text = "nouveau.buko"
        self.editor.text = ""
        self.output.text = "Nouveau fichier. Écris ton programme BuKo ici."

    def save_file(self, *_):
        path = self.project_dir() / self.safe_filename()
        try:
            path.write_text(self.editor.text, encoding="utf-8")
            self.current_path = path
            self.output.text = f"Fichier enregistré : {path.name}"
            self.status.text = "Enregistré dans le dossier privé BuKo."
        except OSError as exc:
            self.show_message("Erreur d'enregistrement", str(exc))

    def open_dialog(self, *_):
        chooser = FileChooserListView(path=str(self.project_dir()), filters=["*.buko", "*.txt"],
                                      dirselect=False)
        layout = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        layout.add_widget(chooser)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        popup = Popup(title="Ouvrir un fichier BuKo", content=layout, size_hint=(0.95, 0.9))
        cancel = Button(text="Annuler")
        open_btn = Button(text="Ouvrir")
        cancel.bind(on_release=popup.dismiss)
        def open_selected(*_):
            if chooser.selection:
                path = Path(chooser.selection[0])
                try:
                    self.editor.text = path.read_text(encoding="utf-8-sig")
                    self.filename.text = path.name
                    self.current_path = path
                    self.output.text = f"Fichier ouvert : {path.name}"
                    popup.dismiss()
                except (OSError, UnicodeError) as exc:
                    self.show_message("Impossible d'ouvrir", str(exc))
        open_btn.bind(on_release=open_selected)
        row.add_widget(cancel); row.add_widget(open_btn)
        layout.add_widget(row)
        popup.open()

    def run_code(self, *_):
        try:
            result = execute(self.editor.text)
            self.output.text = "\n".join(str(line) for line in result) or "Programme exécuté sans sortie."
            self.status.text = "Exécution terminée."
        except BuKoError as exc:
            self.output.text = exc.formatted(self.filename.text or "<éditeur>")
            self.status.text = "Corrige l'erreur puis réessaie."
        except Exception as exc:
            self.output.text = f"Erreur inattendue ({type(exc).__name__}) : {exc}"
            self.status.text = "Échec de l'exécution."

    def show_message(self, title, message):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        box.add_widget(Label(text=message))
        close = Button(text="OK", size_hint_y=None, height=dp(42))
        box.add_widget(close)
        popup = Popup(title=title, content=box, size_hint=(0.88, 0.4))
        close.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == "__main__":
    BuKoMobile().run()
