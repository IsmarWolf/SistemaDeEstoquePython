# ui/register_window.py (COMPLETO E CORRIGIDO)

import customtkinter as ctk
from tkinter import messagebox

class RegisterWindow(ctk.CTkToplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager

        self.title("Criar Nova Conta")
        self.geometry("350x300")
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Registro de Novo Usuário", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        self.username_entry = ctk.CTkEntry(self, placeholder_text="Escolha um nome de usuário")
        self.username_entry.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.password_entry = ctk.CTkEntry(self, placeholder_text="Digite sua senha", show="*")
        self.password_entry.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.confirm_password_entry = ctk.CTkEntry(self, placeholder_text="Confirme sua senha", show="*")
        self.confirm_password_entry.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        register_button = ctk.CTkButton(self, text="Registrar", command=self.attempt_register)
        register_button.grid(row=4, column=0, padx=20, pady=20, sticky="ew")
        
        # <--- CORREÇÃO AQUI ---
        # O método self.eval não existe em CTkToplevel.
        # Esta é a maneira correta de centralizar uma janela Toplevel.
        self.after(10, self.center_window)

    def center_window(self):
        self.update_idletasks()
        parent_geo = self.master.geometry().split('+')
        parent_pos_x = int(parent_geo[1])
        parent_pos_y = int(parent_geo[2])
        
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        
        win_width = self.winfo_width()
        win_height = self.winfo_height()
        
        x = parent_pos_x + (parent_width - win_width) // 2
        y = parent_pos_y + (parent_height - win_height) // 2
        
        self.geometry(f"+{x}+{y}")


    def attempt_register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        if not all([username, password, confirm_password]):
            messagebox.showerror("Erro de Registro", "Todos os campos são obrigatórios.", parent=self)
            return

        if password != confirm_password:
            messagebox.showerror("Erro de Registro", "As senhas não coincidem.", parent=self)
            return
        
        result = self.db_manager.add_user(username, password, 'operador')
        
        if isinstance(result, int):
            messagebox.showinfo("Sucesso", "Usuário registrado com sucesso! Agora você pode fazer login.", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Erro de Registro", result, parent=self)