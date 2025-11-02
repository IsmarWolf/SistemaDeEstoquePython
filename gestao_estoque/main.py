# main.py (COMPLETO E ATUALIZADO)

import customtkinter as ctk
from database.db_manager import DatabaseManager
from ui.login_window import LoginWindow
from ui.main_app_window import MainAppWindow
import configparser # <--- NOVO IMPORT
import os

class App:
    def __init__(self):
        # --- Lógica de Configuração ---
        self.config = configparser.ConfigParser()
        # Cria o arquivo de config se não existir
        if not os.path.exists('config.ini'):
            self.create_default_config()
        self.config.read('config.ini')
        
        default_theme = self.config.get('Settings', 'default_theme', fallback='dark')
        ctk.set_appearance_mode(default_theme)
        ctk.set_default_color_theme("blue")

        self.db_manager = DatabaseManager()
        self.root = None

        self.show_login_window()

    def create_default_config(self):
        self.config['Settings'] = {
            'default_theme': 'dark',
            'export_path': './exports',
            'backup_path': './backups',
            'low_stock_percentage': '30',
            'inactivity_days': '20'
        }
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)

    def show_login_window(self):
        login_win = LoginWindow(self.db_manager, self.on_login_success)
        login_win.mainloop()

    def on_login_success(self, user_id):
        """Callback que recebe o ID do usuário logado."""
        self.root = MainAppWindow(self.db_manager, user_id, self.config) # Passa a config para a janela principal
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        if self.root:
            self.root.destroy()
        self.db_manager.close()

if __name__ == "__main__":
    app = App()