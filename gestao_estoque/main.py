# main.py

import customtkinter as ctk
from database.db_manager import DatabaseManager
from ui.login_window import LoginWindow
from ui.main_app_window import MainAppWindow

class App:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.db_manager = DatabaseManager()
        self.root = None

        self.show_login_window()

    def show_login_window(self):
        login_win = LoginWindow(self.db_manager, self.on_login_success)
        login_win.mainloop()

    def on_login_success(self, user_id):
        """Callback que recebe o ID do usuário logado."""
        self.root = MainAppWindow(self.db_manager, user_id)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        if self.root:
            self.root.destroy()
        self.db_manager.close()

if __name__ == "__main__":
    app = App()