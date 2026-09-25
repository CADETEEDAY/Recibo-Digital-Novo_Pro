import sqlite3
import hashlib
import secrets
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window

Window.clearcolor = (0.07, 0.09, 0.14, 1)  # Tema Slate Dark (#121824)

# ==============================================================================
# SEGURANÇA E BASE DE DADOS
# ==============================================================================
class SecurityHelper:
    @staticmethod
    def gerar_hash(senha: str) -> tuple:
        salt = secrets.token_hex(16)
        senha_hash = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return senha_hash, salt

    @staticmethod
    def verificar_senha(senha: str, hash_salvo: str, salt: str) -> bool:
        teste_hash = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
        return secrets.compare_digest(hash_salvo, teste_hash)

class DatabaseManager:
    def __init__(self, db_name="recibo_mobile.db"):
        self.db_path = db_name
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    nome_completo TEXT NOT NULL,
                    perfil TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS recibos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT NOT NULL,
                    cliente_nome TEXT NOT NULL,
                    valor REAL NOT NULL,
                    referente TEXT NOT NULL,
                    data_recibo TEXT NOT NULL
                )
            """)
            total_users = c.execute("SELECT COUNT(id) FROM usuarios").fetchone()[0]
            if total_users == 0:
                h, s = SecurityHelper.gerar_hash("admin123")
                c.execute("INSERT INTO usuarios (usuario, senha_hash, salt, nome_completo, perfil) VALUES (?, ?, ?, ?, ?)",
                          ("admin", h, s, "Administrador Geral", "ADMIN"))
            conn.commit()

    def autenticar(self, usuario, senha):
        with self.get_connection() as conn:
            user = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),)).fetchone()
            if user and SecurityHelper.verificar_senha(senha, user["senha_hash"], user["salt"]):
                return dict(user)
        return None

# ==============================================================================
# INTERFACE MÓVEL (KIVY)
# ==============================================================================
def popup_aviso(titulo, mensagem):
    box = BoxLayout(orientation='vertical', padding=15, spacing=10)
    box.add_widget(Label(text=mensagem, font_size=14))
    btn = Button(text="Fechar", size_hint=(1, 0.4), background_color=(0.23, 0.51, 0.96, 1))
    box.add_widget(btn)
    p = Popup(title=titulo, content=box, size_hint=(0.8, 0.4))
    btn.bind(on_release=p.dismiss)
    p.open()

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)

        layout.add_widget(Label(text="RECIBO SOFTWARE", font_size=24, bold=True, color=(1, 1, 1, 1), size_hint=(1, 0.2)))
        layout.add_widget(Label(text="Acesso Móvel", font_size=14, color=(0.4, 0.6, 1, 1), size_hint=(1, 0.1)))

        self.txt_user = TextInput(hint_text="Utilizador (ex: admin)", text="admin", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_user)

        self.txt_pass = TextInput(hint_text="Palavra-passe", text="admin123", password=True, multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_pass)

        btn_entrar = Button(text="Entrar no Sistema", font_size=16, bold=True, size_hint=(1, 0.15), background_color=(0.23, 0.51, 0.96, 1))
        btn_entrar.bind(on_release=self.fazer_login)
        layout.add_widget(btn_entrar)

        layout.add_widget(Label(text="Padrão: admin | admin123", font_size=12, color=(0.6, 0.6, 0.6, 1), size_hint=(1, 0.1)))
        self.add_widget(layout)

    def fazer_login(self, *args):
        app = App.get_running_app()
        user = app.db.autenticar(self.txt_user.text, self.txt_pass.text)
        if user:
            app.usuario_logado = user
            self.manager.current = "menu"
        else:
            popup_aviso("Erro", "Utilizador ou palavra-passe inválidos.")

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.layout)

    def on_pre_enter(self):
        self.layout.clear_widgets()
        app = App.get_running_app()
        user = app.usuario_logado or {"nome_completo": "Operador", "perfil": "USER"}

        self.layout.add_widget(Label(text=f"Sessão: {user['nome_completo']} ({user['perfil']})", font_size=16, bold=True, size_hint=(1, 0.15)))

        btn_novo_recibo = Button(text="📄 Emitir Novo Recibo", size_hint=(1, 0.15), background_color=(0.23, 0.51, 0.96, 1))
        btn_novo_recibo.bind(on_release=lambda x: setattr(self.manager, 'current', 'recibo'))
        self.layout.add_widget(btn_novo_recibo)

        btn_listar = Button(text="🔍 Listar Recibos (A-Z)", size_hint=(1, 0.15), background_color=(0.3, 0.4, 0.6, 1))
        btn_listar.bind(on_release=lambda x: setattr(self.manager, 'current', 'lista'))
        self.layout.add_widget(btn_listar)

        # Funcionalidade restrita exclusivamente ao Administrador
        if user["perfil"] == "ADMIN":
            btn_admin_users = Button(text="👤 Gerir Utilizadores (Admin)", size_hint=(1, 0.15), background_color=(0.06, 0.72, 0.5, 1))
            btn_admin_users.bind(on_release=lambda x: setattr(self.manager, 'current', 'usuarios'))
            self.layout.add_widget(btn_admin_users)

        btn_sair = Button(text="Sair da Conta", size_hint=(1, 0.15), background_color=(0.7, 0.2, 0.2, 1))
        btn_sair.bind(on_release=lambda x: setattr(self.manager, 'current', 'login'))
        self.layout.add_widget(btn_sair)

class ReciboScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        layout.add_widget(Label(text="Emissão de Recibo", font_size=18, bold=True, size_hint=(1, 0.1)))

        self.txt_cli = TextInput(hint_text="Nome do Cliente / Beneficiário", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_cli)

        self.txt_val = TextInput(hint_text="Valor (ex: 150.00)", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_val)

        self.txt_ref = TextInput(hint_text="Referente a...", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_ref)

        btn_gravar = Button(text="Gravar Recibo", size_hint=(1, 0.14), background_color=(0.06, 0.72, 0.5, 1))
        btn_gravar.bind(on_release=self.gravar_recibo)
        layout.add_widget(btn_gravar)

        btn_voltar = Button(text="Voltar ao Menu", size_hint=(1, 0.12), background_color=(0.3, 0.4, 0.5, 1))
        btn_voltar.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_voltar)

        self.add_widget(layout)

    def gravar_recibo(self, *args):
        cli = self.txt_cli.text.strip()
        val = self.txt_val.text.strip()
        ref = self.txt_ref.text.strip()

        if not cli or not val:
            popup_aviso("Aviso", "Preencha o cliente e o valor.")
            return

        try:
            val_f = float(val.replace(',', '.'))
        except ValueError:
            popup_aviso("Erro", "Valor inválido.")
            return

        app = App.get_running_app()
        dt = datetime.now().strftime("%d/%m/%Y")
        with app.db.get_connection() as conn:
            num = str(conn.execute("SELECT COUNT(id) FROM recibos").fetchone()[0] + 1)
            conn.execute("INSERT INTO recibos (numero, cliente_nome, valor, referente, data_recibo) VALUES (?, ?, ?, ?, ?)",
                         (num, cli, val_f, ref, dt))
            conn.commit()

        self.txt_cli.text = ""
        self.txt_val.text = ""
        self.txt_ref.text = ""
        popup_aviso("Sucesso", f"Recibo Nº {num} registado com sucesso.")
        self.manager.current = "menu"

class ListaRecibosScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8)
        self.scroll = ScrollView(size_hint=(1, 0.85))
        self.grid = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)

        btn_voltar = Button(text="Voltar ao Menu", size_hint=(1, 0.12), background_color=(0.3, 0.4, 0.5, 1))
        btn_voltar.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))

        self.layout.add_widget(Label(text="Recibos Emitidos (A-Z)", font_size=16, bold=True, size_hint=(1, 0.08)))
        self.layout.add_widget(self.scroll)
        self.layout.add_widget(btn_voltar)
        self.add_widget(self.layout)

    def on_pre_enter(self):
        self.grid.clear_widgets()
        app = App.get_running_app()
        with app.db.get_connection() as conn:
            registos = conn.execute("SELECT * FROM recibos ORDER BY cliente_nome ASC").fetchall()

        if not registos:
            self.grid.add_widget(Label(text="Nenhum recibo emitido.", size_hint_y=None, height=40))
        for r in registos:
            txt = f"Nº {r['numero']} - {r['cliente_nome']} | R$ {r['valor']:.2f}\nData: {r['data_recibo']} | Ref: {r['referente']}"
            lbl = Label(text=txt, size_hint_y=None, height=65, color=(0.85, 0.9, 1, 1))
            self.grid.add_widget(lbl)

class UsuariosAdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        layout.add_widget(Label(text="Adicionar Utilizador (Admin)", font_size=16, bold=True, size_hint=(1, 0.1)))

        self.txt_nome = TextInput(hint_text="Nome Completo", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_nome)

        self.txt_u = TextInput(hint_text="Nome de Utilizador", multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_u)

        self.txt_p = TextInput(hint_text="Palavra-passe", password=True, multiline=False, size_hint=(1, 0.12))
        layout.add_widget(self.txt_p)

        btn_criar = Button(text="+ Criar Operador", size_hint=(1, 0.14), background_color=(0.06, 0.72, 0.5, 1))
        btn_criar.bind(on_release=self.adicionar_usuario)
        layout.add_widget(btn_criar)

        btn_voltar = Button(text="Voltar ao Menu", size_hint=(1, 0.12), background_color=(0.3, 0.4, 0.5, 1))
        btn_voltar.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(btn_voltar)

        self.add_widget(layout)

    def adicionar_usuario(self, *args):
        n = self.txt_nome.text.strip()
        u = self.txt_u.text.strip()
        p = self.txt_p.text.strip()
        if not n or not u or not p:
            popup_aviso("Aviso", "Preencha todos os campos.")
            return

        app = App.get_running_app()
        h, s = SecurityHelper.gerar_hash(p)
        try:
            with app.db.get_connection() as conn:
                conn.execute("INSERT INTO usuarios (usuario, senha_hash, salt, nome_completo, perfil) VALUES (?, ?, ?, ?, ?)",
                             (u, h, s, n, "OPERADOR"))
                conn.commit()
            self.txt_nome.text = ""
            self.txt_u.text = ""
            self.txt_p.text = ""
            popup_aviso("Sucesso", f"Utilizador '{u}' criado com sucesso.")
            self.manager.current = "menu"
        except sqlite3.IntegrityError:
            popup_aviso("Erro", "Nome de utilizador já existente.")

# ==============================================================================
# INICIALIZAÇÃO DA APLICAÇÃO
# ==============================================================================
class ReciboSoftwareMobileApp(App):
    def build(self):
        self.db = DatabaseManager()
        self.usuario_logado = None

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(ReciboScreen(name="recibo"))
        sm.add_widget(ListaRecibosScreen(name="lista"))
        sm.add_widget(UsuariosAdminScreen(name="usuarios"))
        return sm

if __name__ == "__main__":
    ReciboSoftwareMobileApp().run()
