# ui/main_app_window.py

import customtkinter as ctk
from tkinter import ttk, messagebox

# --- Classe Genérica para Forms (Adicionar/Editar) ---
class GenericForm(ctk.CTkToplevel):
    def __init__(self, parent, title, fields, on_save_callback, existing_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x450")
        self.transient(parent)
        self.grab_set()

        self.fields = fields
        self.on_save = on_save_callback
        self.existing_data = existing_data
        self.entries = {}

        self.grid_columnconfigure(1, weight=1)

        for i, (label, field_type) in enumerate(fields.items()):
            ctk.CTkLabel(self, text=f"{label}:").grid(row=i, column=0, padx=10, pady=10, sticky="w")
            if field_type == "password":
                entry = ctk.CTkEntry(self, show="*")
            else:
                entry = ctk.CTkEntry(self)
            entry.grid(row=i, column=1, padx=10, pady=10, sticky="ew")
            self.entries[label] = entry
        
        if existing_data:
            self.fill_form()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        ctk.CTkButton(btn_frame, text="Salvar", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, fg_color="#d9534f").pack(side="left", padx=10)

    def fill_form(self):
        for i, label in enumerate(self.fields.keys()):
            if i < len(self.existing_data) - 1:
                if self.fields[label] != "password":
                    self.entries[label].insert(0, self.existing_data[i+1])

    def save(self):
        data = {label: entry.get() for label, entry in self.entries.items()}
        if self.existing_data:
            data['id'] = self.existing_data[0]
        
        self.on_save(data)
        self.destroy()

# --- Classe Principal da Aplicação ---
class MainAppWindow(ctk.CTk):
    def __init__(self, db_manager, user_id):
        super().__init__()
        self.db_manager = db_manager
        self.current_user_id = user_id

        self.title("Sistema de Gestão de Estoque")
        self.geometry("1100x700")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        menu_frame = ctk.CTkFrame(self, width=180, corner_radius=0)
        menu_frame.grid(row=0, column=0, sticky="nsw")
        ctk.CTkLabel(menu_frame, text="Menu", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        self.theme_switch = ctk.CTkSwitch(menu_frame, text="Tema Escuro", command=self.toggle_theme)
        self.theme_switch.pack(pady=10, padx=20)
        self.theme_switch.select()

        self.tab_view = ctk.CTkTabview(self, corner_radius=8)
        self.tab_view.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tabs = {}
        self.create_tab("Produtos", 
                        ["ID", "Nome", "SKU", "Qtd", "Preço"], 
                        [50, 250, 150, 100, 120],
                        self.db_manager.get_all_products,
                        self.open_product_form,
                        self.open_product_form,
                        self.delete_product)
        
        self.create_tab("Clientes",
                        ["ID", "Nome", "CPF/CNPJ", "Telefone", "Email"],
                        [50, 200, 150, 120, 200],
                        self.db_manager.get_all_clients,
                        self.open_client_form,
                        self.open_client_form,
                        self.delete_client)

        self.create_tab("Fornecedores",
                        ["ID", "Nome", "Contato", "Endereço"],
                        [50, 200, 150, 300],
                        self.db_manager.get_all_suppliers,
                        self.open_supplier_form,
                        self.open_supplier_form,
                        self.delete_supplier)

        self.create_movement_tab()

        self.create_tab("Usuários",
                        ["ID", "Usuário", "Nível de Acesso"],
                        [50, 200, 150],
                        self.db_manager.get_all_users,
                        self.open_user_form,
                        self.open_user_form,
                        self.delete_user)

        self.setup_styles()
        self.toggle_theme()

    def create_tab(self, name, columns, widths, fetch_func, add_cmd, edit_cmd, del_cmd):
        tab = self.tab_view.add(name)
        self.tabs[name] = {'frame': tab, 'fetch': fetch_func}
        
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ctk.CTkButton(controls_frame, text=f"Adicionar {name[:-1]}", command=add_cmd).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text=f"Editar Selecionado", command=lambda: edit_cmd(edit=True)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text=f"Excluir Selecionado", command=del_cmd, fg_color="#d9534f").pack(side="left", padx=10, pady=10)

        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w" if col == "Nome" else "center")
        
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        
        self.tabs[name]['tree'] = tree
        self.refresh_tab(name)

    def create_movement_tab(self):
        name = "Movimentações"
        tab = self.tab_view.add(name)
        self.tabs[name] = {'frame': tab, 'fetch': self.db_manager.get_all_movements}

        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        controls_frame = ctk.CTkFrame(tab)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        ctk.CTkLabel(controls_frame, text="Produto:").pack(side="left", padx=(10,0), pady=10)
        self.mov_prod_combo = ctk.CTkComboBox(controls_frame, values=[], width=250)
        self.mov_prod_combo.pack(side="left", padx=5, pady=10)
        
        ctk.CTkLabel(controls_frame, text="Tipo:").pack(side="left", padx=(10,0), pady=10)
        self.mov_type_combo = ctk.CTkComboBox(controls_frame, values=["Entrada", "Saida"])
        self.mov_type_combo.pack(side="left", padx=5, pady=10)
        
        ctk.CTkLabel(controls_frame, text="Qtd:").pack(side="left", padx=(10,0), pady=10)
        self.mov_qtd_entry = ctk.CTkEntry(controls_frame, width=80)
        self.mov_qtd_entry.pack(side="left", padx=5, pady=10)

        ctk.CTkButton(controls_frame, text="Registrar Movimentação", command=self.add_movement).pack(side="left", padx=10, pady=10)

        columns = ["ID", "Produto", "Usuário", "Tipo", "Qtd", "Data/Hora"]
        widths = [50, 200, 100, 80, 80, 150]
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="center")
        tree.grid(row=0, column=0, sticky="nsew")
        self.tabs[name]['tree'] = tree
        self.refresh_tab(name)
        self.update_movement_product_list()

    def refresh_tab(self, name):
        tree = self.tabs[name]['tree']
        fetch_func = self.tabs[name]['fetch']
        
        for item in tree.get_children():
            tree.delete(item)
        
        for row in fetch_func():
            tree.insert("", "end", values=row)

    def get_selected_item(self, tab_name):
        tree = self.tabs[tab_name]['tree']
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", f"Por favor, selecione um item na lista de {tab_name}.")
            return None
        return tree.item(selected_item)['values']

    def open_product_form(self, edit=False):
        data = self.get_selected_item("Produtos") if edit else None
        if edit and not data: return
        fields = {"Nome": "text", "SKU": "text", "Descrição": "text", "Quantidade": "number", "Preço": "float"}
        title = "Editar Produto" if edit else "Adicionar Produto"
        GenericForm(self, title, fields, self.save_product, data)

    def save_product(self, data):
        if not all(data.get(k) for k in ["Nome", "SKU", "Quantidade", "Preço"]):
            messagebox.showerror("Erro", "Campos obrigatórios não preenchidos.")
            return
        try:
            if 'id' in data:
                self.db_manager.update_product(data['id'], data['Nome'], data['SKU'], data['Descrição'], int(data['Quantidade']), float(data['Preço']))
            else:
                self.db_manager.add_product(data['Nome'], data['SKU'], data['Descrição'], int(data['Quantidade']), float(data['Preço']))
            self.refresh_tab("Produtos")
            self.update_movement_product_list() # CORREÇÃO: Atualiza a lista de produtos em Movimentações
        except ValueError:
            messagebox.showerror("Erro de Formato", "Quantidade e Preço devem ser números válidos.")
        except Exception as e:
            messagebox.showerror("Erro no Banco de Dados", str(e))

    def delete_product(self):
        data = self.get_selected_item("Produtos")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o produto '{data[1]}'?"):
            self.db_manager.delete_product(data[0])
            self.refresh_tab("Produtos")
            self.update_movement_product_list() # CORREÇÃO: Atualiza a lista de produtos em Movimentações

    def open_client_form(self, edit=False):
        data = self.get_selected_item("Clientes") if edit else None
        if edit and not data: return
        fields = {"Nome": "text", "CPF/CNPJ": "text", "Telefone": "text", "Email": "text", "Endereço": "text"}
        title = "Editar Cliente" if edit else "Adicionar Cliente"
        GenericForm(self, title, fields, self.save_client, data)

    def save_client(self, data):
        if 'id' in data:
            self.db_manager.update_client(data['id'], data['Nome'], data['CPF/CNPJ'], data['Telefone'], data['Email'], data['Endereço'])
        else:
            self.db_manager.add_client(data['Nome'], data['CPF/CNPJ'], data['Telefone'], data['Email'], data['Endereço'])
        self.refresh_tab("Clientes")

    def delete_client(self):
        data = self.get_selected_item("Clientes")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o cliente '{data[1]}'?"):
            self.db_manager.delete_client(data[0])
            self.refresh_tab("Clientes")

    def open_supplier_form(self, edit=False):
        data = self.get_selected_item("Fornecedores") if edit else None
        if edit and not data: return
        fields = {"Nome": "text", "Contato": "text", "Endereço": "text"}
        title = "Editar Fornecedor" if edit else "Adicionar Fornecedor"
        GenericForm(self, title, fields, self.save_supplier, data)

    def save_supplier(self, data):
        if 'id' in data:
            self.db_manager.update_supplier(data['id'], data['Nome'], data['Contato'], data['Endereço'])
        else:
            self.db_manager.add_supplier(data['Nome'], data['Contato'], data['Endereço'])
        self.refresh_tab("Fornecedores")

    def delete_supplier(self):
        data = self.get_selected_item("Fornecedores")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o fornecedor '{data[1]}'?"):
            self.db_manager.delete_supplier(data[0])
            self.refresh_tab("Fornecedores")

    def open_user_form(self, edit=False):
        data = self.get_selected_item("Usuários") if edit else None
        if edit and not data: return
        fields = {"Usuário": "text", "Senha": "password", "Nível de Acesso": "text"}
        title = "Editar Usuário" if edit else "Adicionar Usuário"
        GenericForm(self, title, fields, self.save_user, data)

    def save_user(self, data):
        if 'id' in data:
            self.db_manager.update_user(data['id'], data['Usuário'], data['Senha'], data['Nível de Acesso'])
        else:
            if not data['Senha']:
                messagebox.showerror("Erro", "A senha é obrigatória para novos usuários.")
                return
            self.db_manager.add_user(data['Usuário'], data['Senha'], data['Nível de Acesso'])
        self.refresh_tab("Usuários")

    def delete_user(self):
        data = self.get_selected_item("Usuários")
        if data and data[0] == 1:
            messagebox.showerror("Erro", "Não é possível excluir o usuário administrador.")
            return
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o usuário '{data[1]}'?"):
            self.db_manager.delete_user(data[0])
            self.refresh_tab("Usuários")

    def update_movement_product_list(self):
        products = self.db_manager.get_all_products()
        self.product_map = {f"{p[0]} - {p[1]}": p[0] for p in products}
        product_list = list(self.product_map.keys())
        self.mov_prod_combo.configure(values=product_list)
        if product_list:
            self.mov_prod_combo.set(product_list[0]) # Define um valor padrão
        else:
            self.mov_prod_combo.set("") # Limpa se não houver produtos

    def add_movement(self):
        prod_selection = self.mov_prod_combo.get()
        tipo = self.mov_type_combo.get()
        qtd_str = self.mov_qtd_entry.get()

        if not all([prod_selection, tipo, qtd_str]):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios.")
            return
        
        # CORREÇÃO: Valida se o produto selecionado existe no mapa antes de prosseguir
        prod_id = self.product_map.get(prod_selection)
        if prod_id is None:
            messagebox.showerror("Erro", "Produto selecionado é inválido. Por favor, selecione um da lista.")
            return

        try:
            qtd = int(qtd_str)
            if qtd <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Quantidade deve ser um número inteiro positivo.")
            return
        
        result = self.db_manager.add_movement(prod_id, self.current_user_id, tipo.lower(), qtd)

        if result == "Sucesso":
            messagebox.showinfo("Sucesso", "Movimentação registrada.")
            self.refresh_tab("Movimentações")
            self.refresh_tab("Produtos")
            self.mov_qtd_entry.delete(0, 'end') # Limpa o campo de quantidade
        else:
            messagebox.showerror("Erro na Movimentação", result)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")

    def toggle_theme(self):
        mode = "dark" if self.theme_switch.get() == 1 else "light"
        ctk.set_appearance_mode(mode)
        
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        selected_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"])
        header_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"])
        
        self.style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0)
        self.style.map('Treeview', background=[('selected', selected_color)])
        self.style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat", font=('Calibri', 10, 'bold'))
        self.style.map("Treeview.Heading", background=[('active', '#3484F0')])