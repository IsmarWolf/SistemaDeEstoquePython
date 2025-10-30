# ui/login_window.py

import customtkinter as ctk
from tkinter import messagebox
from ui.register_window import RegisterWindow # <--- NOVO IMPORT

class LoginWindow(ctk.CTk):
    def __init__(self, db_manager, on_login_success):
        super().__init__()
        self.db_manager = db_manager
        self.on_login_success = on_login_success
        self.login_successful = False

        self.title("Login - Sistema de Gestão de Estoque")
        self.geometry("350x250") # Aumentei um pouco a altura
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) # Espaço para o novo botão
        
        ctk.CTkLabel(self, text="Login de Acesso", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Usuário (admin)")
        self.username_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Senha (admin)", show="*")
        self.password_entry.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        login_button = ctk.CTkButton(self, text="Entrar", command=self.attempt_login)
        login_button.grid(row=3, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        # <--- BOTÃO DE CRIAR CONTA ADICIONADO ---
        register_button = ctk.CTkButton(self, text="Criar Conta", command=self.open_register_window, fg_color="transparent", border_width=1)
        register_button.grid(row=4, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        self.eval('tk::PlaceWindow . center')

    def open_register_window(self):
        # Abre a janela de registro como uma Toplevel
        RegisterWindow(self, self.db_manager)

    def attempt_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Erro de Login", "Usuário e senha são obrigatórios.")
            return

        user = self.db_manager.validate_login(username, password)
        if user:
            user_id = user[0]
            self.login_successful = True
            self.destroy()
            self.on_login_success(user_id)
        else:
            messagebox.showerror("Erro de Login", "Credenciais inválidas.")

    def on_closing(self):
        self.destroy()