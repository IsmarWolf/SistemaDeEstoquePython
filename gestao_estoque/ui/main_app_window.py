# ui/main_app_window.py (COMPLETO E CORRIGIDO)

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import collections
from ui.dashboard_tab import DashboardTab
import re
import csv
import os
from datetime import datetime
import threading
import unicodedata
import requests

# Note: heavy imports for camera/vision are done lazily inside ScannerWindow to allow the app
# to run even if the optional dependencies are not installed.

class ValidatedForm(ctk.CTkToplevel):
    def __init__(self, parent, title, fields, on_save_callback, existing_data=None):
        super().__init__(parent)
        self.title(title); self.geometry("450x550"); self.transient(parent); self.grab_set()
        self.fields_config = fields; self.on_save = on_save_callback; self.existing_data = existing_data
        self.widgets = {}; self.grid_columnconfigure(1, weight=1)
        for i, (label, config) in enumerate(fields.items()):
            ctk.CTkLabel(self, text=f"{label}:").grid(row=i, column=0, padx=10, pady=5, sticky="w")
            widget_type = config.get("widget", "entry")
            if widget_type == "combobox":
                widget = ctk.CTkComboBox(self, values=config.get("values", []))
                widget.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            else:
                show_char = "*" if config.get("type") == "password" else None
                widget = ctk.CTkEntry(self, show=show_char)
                widget.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                widget.bind("<KeyRelease>", lambda event, w=widget: self.clear_error(w))
            self.widgets[label] = widget
        if existing_data: self.fill_form()
        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        ctk.CTkButton(btn_frame, text="Salvar", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancelar", command=self.destroy, fg_color="#d9534f").pack(side="left", padx=10)

    def fill_form(self):
        field_map = {'Nome': 1, 'SKU': 2, 'Descrição': 3, 'Quantidade Inicial': 4, 'Estoque Atual': 4, 'CPF/CNPJ': 2, 'Telefone': 3, 'Email': 4, 'Endereço': 5, 'Contato': 2, 'Usuário': 1, 'Nível de Acesso': 2}
        for label, widget in self.widgets.items():
            if label in field_map and field_map[label] < len(self.existing_data):
                value = self.existing_data[field_map[label]]
                if value is not None:
                    if isinstance(widget, ctk.CTkComboBox): widget.set(str(value))
                    else: widget.insert(0, str(value))

    def validate_and_get_data(self):
        is_valid = True; data = {}
        for label, widget in self.widgets.items():
            value = widget.get().strip(); config = self.fields_config[label]
            if isinstance(widget, ctk.CTkEntry): self.clear_error(widget)
            if config.get("required") and not value:
                self.show_error(widget, f"{label} é obrigatório."); is_valid = False; continue
            if value:
                max_len = config.get("max_len")
                if max_len and len(value) > max_len:
                    self.show_error(widget, f"{label} não pode ter mais de {max_len} caracteres."); is_valid = False; continue
                validation = config.get("validation")
                if validation and not re.match(validation["pattern"], value):
                    self.show_error(widget, validation["message"]); is_valid = False; continue
                if config["type"] == "int":
                    try: data[label] = int(value)
                    except ValueError: self.show_error(widget, f"{label} deve ser um número inteiro."); is_valid = False; continue
                elif config["type"] == "float":
                    try: data[label] = float(value.replace(',', '.'))
                    except ValueError: self.show_error(widget, f"{label} deve ser um número válido."); is_valid = False; continue
                else: data[label] = value
            else: data[label] = value
        return data if is_valid else None

    def save(self):
        validated_data = self.validate_and_get_data()
        if validated_data:
            if self.existing_data: validated_data['id'] = self.existing_data[0]
            result = self.on_save(validated_data)
            if result == "Success":
                self.destroy()
            elif result:
                messagebox.showerror("Erro ao Salvar", result, parent=self)
    
    def show_error(self, widget, message):
        if isinstance(widget, ctk.CTkEntry): widget.configure(border_color="red")
        messagebox.showwarning("Erro de Validação", message, parent=self)
    def clear_error(self, widget):
        if isinstance(widget, ctk.CTkEntry): widget.configure(border_color=ctk.ThemeManager.theme["CTkEntry"]["border_color"])

class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, db_manager, product_id, product_name, movement_type):
        super().__init__(parent)
        self.db_manager = db_manager
        # Always show both Compras (entrada) and Vendas (saida) in separate tabs.
        type_str = "Vendas" if movement_type == "saida" else "Compras"
        self.title(f"Histórico de {type_str} - {product_name}")
        self.geometry("900x500"); self.transient(parent); self.grab_set()
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)

        # Create tabview with two tabs: Compras and Vendas
        tabview = ctk.CTkTabview(self)
        tabview.add("Compras"); tabview.add("Vendas")
        tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        columns = ["Data/Hora", "Quantidade", "Preço Unit.", "Usuário", "Cliente/Fornecedor"]
        widths = [160, 80, 100, 140, 200]

        def _create_tree(parent_frame):
            frame = ctk.CTkFrame(parent_frame); frame.pack(fill="both", expand=True)
            tree = ttk.Treeview(frame, columns=columns, show="headings")
            for col, width in zip(columns, widths):
                tree.heading(col, text=col); tree.column(col, width=width, anchor="center")
            tree.pack(fill="both", expand=True)
            return tree

        purchases_tree = _create_tree(tabview.tab("Compras"))
        sales_tree = _create_tree(tabview.tab("Vendas"))

        purchases = self.db_manager.get_movements_for_product(product_id, "entrada")
        for row in purchases:
            purchases_tree.insert("", "end", values=row)

        sales = self.db_manager.get_movements_for_product(product_id, "saida")
        for row in sales:
            sales_tree.insert("", "end", values=row)

        # Set the active tab according to the requested movement_type, but both are available.
        if movement_type == "saida":
            tabview.set("Vendas")
        else:
            tabview.set("Compras")

class ExportDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_export_callback):
        super().__init__(parent)
        self.on_export = on_export_callback
        self.title("Exportar Dados"); self.geometry("300x150"); self.transient(parent); self.grab_set()
        ctk.CTkLabel(self, text="Selecione o formato de exportação:").pack(pady=10)
        ctk.CTkButton(self, text="Exportar para CSV (Dados Brutos)", command=lambda: self.export("csv")).pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self, text="Exportar para PDF (Relatório Visual)", command=lambda: self.export("pdf")).pack(pady=5, padx=20, fill="x")

    def export(self, file_type):
        self.destroy()
        self.on_export(file_type)


class AddProductFromSKU(ctk.CTkToplevel):
    """Simple dialog to create a product when a scanned SKU is not found.

    Accepts optional `prefill` dict with keys: name, sku, desc, qty.
    """
    def __init__(self, parent, db_manager, sku, on_created=None, prefill=None):
        super().__init__(parent)
        self.db_manager = db_manager; self.on_created = on_created
        self.title("Adicionar Produto (via Leitura)")
        self.geometry("420x300"); self.transient(parent); self.grab_set()
        ctk.CTkLabel(self, text="Nome:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.name_entry = ctk.CTkEntry(self); self.name_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        ctk.CTkLabel(self, text="SKU:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.sku_entry = ctk.CTkEntry(self); self.sku_entry.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
        self.sku_entry.insert(0, sku)

        ctk.CTkLabel(self, text="Código de Barras:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
        self.barcode_entry = ctk.CTkEntry(self); self.barcode_entry.grid(row=2, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(self, text="Descrição:").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        self.desc_entry = ctk.CTkEntry(self); self.desc_entry.grid(row=3, column=1, padx=10, pady=8, sticky="ew")

        ctk.CTkLabel(self, text="Quantidade Inicial:").grid(row=4, column=0, sticky="w", padx=10, pady=8)
        self.qty_entry = ctk.CTkEntry(self); self.qty_entry.grid(row=4, column=1, padx=10, pady=8, sticky="ew")
        # Default initial stock should be 0 (it's current stock, not package quantity)
        self.qty_entry.insert(0, "0")

        # apply prefill values if provided (but do NOT use prefill.qty as stock)
        if prefill:
            try:
                if prefill.get('name'):
                    self.name_entry.insert(0, prefill.get('name'))
                if prefill.get('sku'):
                    self.sku_entry.delete(0, 'end'); self.sku_entry.insert(0, prefill.get('sku'))
                if prefill.get('desc'):
                    self.desc_entry.insert(0, prefill.get('desc'))
                if prefill.get('barcode'):  # Handle barcode prefill
                    self.barcode_entry.insert(0, prefill.get('barcode'))
                # Do not set qty from prefill (quantity in OFF is package size, not stock)
                # If a forced qty is provided explicitly, allow it via key 'force_qty'.
                if prefill.get('force_qty') is True and prefill.get('qty') is not None:
                    self.qty_entry.delete(0, 'end'); self.qty_entry.insert(0, str(prefill.get('qty')))
            except Exception:
                pass



        btn_frame = ctk.CTkFrame(self, fg_color="transparent"); btn_frame.grid(row=5, column=0, columnspan=2, pady=12)
        ctk.CTkButton(btn_frame, text="Criar", command=self._create).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color="#d9534f", command=self.destroy).pack(side="left", padx=8)

    def _create(self):
        name = self.name_entry.get().strip()
        sku = self.sku_entry.get().strip()
        desc = self.desc_entry.get().strip()
        barcode = self.barcode_entry.get().strip()
        
        # Validation
        if not name or not sku:
            messagebox.showwarning("Dados incompletos", "Nome e SKU são obrigatórios.", parent=self)
            return
            
        try:
            qty = int(self.qty_entry.get().strip())
            if qty < 0:
                raise ValueError("Quantidade não pode ser negativa")
        except Exception as e:
            messagebox.showerror("Erro", f"Quantidade inválida: {str(e)}", parent=self)
            return
            
        # If a barcode is provided, check if it's already in use
        if barcode:
            existing = self.db_manager.get_product_by_barcode(barcode)
            if existing:
                messagebox.showerror("Erro", 
                                   f"Este código de barras já está cadastrado no produto: {existing[1]}", 
                                   parent=self)
                return
                
        # Try to create the product
        res = self.db_manager.add_product(
            nome=name,
            sku=sku,
            desc=desc,
            qtd=qty,
            codigo_barra=barcode if barcode else None
        )
        
        if isinstance(res, str):
            messagebox.showerror("Erro ao criar", res, parent=self)
            return
            
        if self.on_created:
            self.on_created(res)
            
        success_msg = f"Produto '{name}' criado com sucesso."
        if barcode:
            success_msg += f"\nCódigo de barras registrado: {barcode}"
        messagebox.showinfo("Sucesso", success_msg, parent=self)
        self.destroy()


class ScannerWindow(ctk.CTkToplevel):
    """A lightweight webcam barcode scanner using OpenCV + pyzbar.

    The heavy libs are imported lazily and a clear message is shown if they're missing.
    When a barcode is detected, `on_detect(code_str)` is called with the decoded string.
    """
    def __init__(self, parent, on_detect):
        super().__init__(parent)
        self.on_detect = on_detect; self.title("Scanner de Código de Barras"); self.geometry("640x520")
        self.transient(parent); self.grab_set()
        self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(0, weight=1)
        self.preview_label = ctk.CTkLabel(self)
        self.preview_label.grid(row=0, column=0, padx=10, pady=10)
        self.info_label = ctk.CTkLabel(self, text="Aguardando leitura...")
        self.info_label.grid(row=1, column=0, pady=(0,10))
        self._cap = None; self._running = False
        # Lazy imports
        try:
            import cv2
            from pyzbar import pyzbar
            from PIL import Image, ImageTk
            self._cv2 = cv2; self._pyzbar = pyzbar; self._Image = Image; self._ImageTk = ImageTk
        except Exception as e:
            messagebox.showerror("Dependência ausente", f"Bibliotecas necessárias não encontradas:\n{e}\nInstale opencv-python, pyzbar e Pillow.", parent=self)
            self.destroy(); return

        try:
            self._cap = self._cv2.VideoCapture(0, cv2.CAP_DSHOW)
        except Exception:
            try:
                self._cap = self._cv2.VideoCapture(0)
            except Exception:
                messagebox.showerror("Erro", "Não foi possível acessar a câmera.", parent=self); self.destroy(); return

        self._running = True
        self.after(30, self._update_frame)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _update_frame(self):
        if not self._running or not self._cap:
            return
        ret, frame = self._cap.read()
        if not ret:
            self.info_label.configure(text="Erro ao ler câmera")
            self.after(200, self._update_frame); return

        # Detect barcodes
        barcodes = self._pyzbar.decode(frame)
        if barcodes:
            code = barcodes[0].data.decode('utf-8')
            self.info_label.configure(text=f"Detectado: {code}")
            # Call callback and stop
            try:
                self.on_detect(code)
            except Exception as e:
                print(f"Erro no callback do scanner: {e}")
            self._close(); return

        # Convert to PhotoImage and show
        rgb = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        img = self._Image.fromarray(rgb)
        img = img.resize((600, 420))
        photo = self._ImageTk.PhotoImage(img)
        # Keep reference
        self.preview_label.image = photo
        self.preview_label.configure(image=photo)
        self.after(30, self._update_frame)

    def _close(self):
        self._running = False
        try:
            if self._cap:
                self._cap.release()
        except Exception:
            pass
        try: self.destroy()
        except Exception: pass

    
def fetch_openfoodfacts_product(code):
    """Query OpenFoodFacts for the given EAN/UPC code.

    Try common variants (strip non-digits, UPC-A <-> EAN13 adjustments) and return
    the first product dict found or None.
    """
    def _try_code(c):
        try:
            url = f"https://world.openfoodfacts.org/api/v0/product/{c}.json"
            print(f"[OFF] Trying code: {c} -> {url}")
            resp = requests.get(url, timeout=6)
            if resp.status_code != 200:
                print(f"[OFF] HTTP {resp.status_code} for code {c}")
                return None
            data = resp.json()
            if data.get('status') == 1:
                print(f"[OFF] Found product for code {c}")
                return data.get('product', {})
            else:
                print(f"[OFF] No product (status != 1) for code {c}")
                return None
        except Exception as e:
            print(f"[OFF] Exception querying code {c}: {e}")
            return None

    orig = str(code or '').strip()
    # normalize to digits only
    digits = re.sub(r'\D', '', orig)
    candidates = []
    if digits:
        candidates.append(digits)
        # UPC-A (12) -> EAN13 by prefixing 0
        if len(digits) == 12:
            candidates.append('0' + digits)
        # EAN13 starting with 0 -> try without leading zero (12)
        if len(digits) == 13 and digits.startswith('0'):
            candidates.append(digits[1:])
        # try with and without common leading zeros
        if len(digits) < 12:
            # pad to 12/13 (best-effort) - rarely useful but harmless
            candidates.append(digits.zfill(12))
            candidates.append(digits.zfill(13))
    # also try original unmodified
    if orig not in candidates:
        candidates.insert(0, orig)

    tried = set()
    for c in candidates:
        if not c or c in tried: continue
        tried.add(c)
        prod = _try_code(c)
        if prod:
            return prod
    return None


def deduce_category_from_name(name):
    name_l = (name or '').lower()
    mapping = {
        'BEB': ['refrigerante','suco','água','agua','cerveja','vinho','bebida','leite'],
        'ALI': ['biscoito','bolacha','pão','pao','arroz','feijão','feijao','carne','frango','pizza','salgad','biscoitos','snack'],
        'LIM': ['sabão','sabao','detergente','limp','limpeza','desinf','sabonete'],
        'CUI': ['shampoo','condicionador','sabonete','creme','hidratante','dent','desodorante'],
        'MED': ['remédio','remedio','medicamento','ibuprofeno','paracetamol','dipirona','analgésico','analgesico','antitermico','antitérmico']
    }
    for code, kws in mapping.items():
        for kw in kws:
            if kw in name_l:
                return code
    return 'OUT'


def normalize_text(s):
    if not s: return ''
    s = unicodedata.normalize('NFKD', s)
    s = ''.join([c for c in s if not unicodedata.combining(c)])
    # Keep letters and digits only
    return re.sub(r'[^A-Za-z0-9]', '', s)


def extract_variation(product):
    # Prefer product['quantity'] then try to parse from product_name
    qty = product.get('quantity') if isinstance(product, dict) else None
    if qty:
        return str(qty).upper().replace(' ', '')
    name = product.get('product_name', '')
    m = re.search(r"(\d+[\.,]?\d*\s*(?:ml|l|g|kg|mg))", name, flags=re.I)
    if m:
        return m.group(1).upper().replace(' ', '')
    return 'VAR'


def fetch_product_from_url(url):
    """Fetch a product page and try to extract a sensible title/brand/description.

    Returns a dict with keys 'name' and 'desc' when found, otherwise None.
    This is a lightweight fallback that looks for og:title or <title> in HTML.
    """
    try:
        if not url.lower().startswith('http'):
            url = 'http://' + url
        resp = requests.get(url, timeout=6)
        if resp.status_code != 200:
            return None
        html = resp.text
        # Try og:title
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            title = m.group(1).strip()
            return {'name': title, 'desc': url}
        # Try meta name="title"
        m = re.search(r'<meta[^>]+name=["\']title["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.I)
        if m:
            title = m.group(1).strip()
            return {'name': title, 'desc': url}
        # Fallback to <title>
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, flags=re.I)
        if m:
            title = m.group(1).strip()
            return {'name': title, 'desc': url}
    except Exception as e:
        print(f"[URL Fetch] error fetching {url}: {e}")
    return None


def generate_sku_from_off(product):
    # product: dict from OpenFoodFacts
    brand = (product.get('brands') or '').split(',')[0].strip()
    brand_abbr = normalize_text(brand).upper()[:4]
    brand_abbr = brand_abbr.ljust(4, 'X') if brand_abbr else 'UNKN'
    name = product.get('product_name') or product.get('generic_name') or ''
    name_abbr = normalize_text(name).upper()[:4]
    name_abbr = name_abbr.ljust(4, 'X') if name_abbr else 'PROD'
    variation = extract_variation(product)
    category = deduce_category_from_name(name)
    sku = f"{category}-{brand_abbr}-{name_abbr}-{variation}"
    return sku, {
        'name': name,
        'brand': brand,
        'quantity': product.get('quantity'),
        'category': category,
        'variation': variation
    }

class MainAppWindow(ctk.CTk):
    def __init__(self, db_manager, user_id, config):
        super().__init__()
        self.db_manager = db_manager; self.current_user_id = user_id; self.config = config
        self.current_user_data = self.db_manager.get_user_by_id(self.current_user_id)
        self.current_user_level = self.current_user_data[3]
        self.level_hierarchy = {'Administrador': 3, 'Supervisor': 2, 'Operador': 1}
        self.title(f"Sistema de Gestão - Usuário: {self.current_user_data[1]} ({self.current_user_level})")
        self.geometry("1300x750"); self.grid_rowconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1)
        
        menu_frame = ctk.CTkFrame(self, width=180, corner_radius=0); menu_frame.grid(row=0, column=0, sticky="nsw")
        ctk.CTkLabel(menu_frame, text="Menu", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        self.notifications_button = ctk.CTkButton(menu_frame, text="Notificações", command=self.show_notifications_tab)
        self.notifications_button.pack(pady=10, padx=20)
        self.export_button = ctk.CTkButton(menu_frame, text="Exportar Dados", command=self.open_export_dialog)
        self.export_button.pack(pady=10, padx=20)
        self.scanner_button = ctk.CTkButton(menu_frame, text="Scanner (Câmera)", command=self.open_scanner)
        self.scanner_button.pack(pady=10, padx=20)
        self.theme_switch = ctk.CTkSwitch(menu_frame, text="Tema Escuro", command=self.toggle_theme)
        self.theme_switch.pack(pady=(20,10), padx=20)
        if self.config.get('Settings', 'default_theme', fallback='dark') == 'dark': self.theme_switch.select()
        
        self.tab_view = ctk.CTkTabview(self, corner_radius=8, command=self.on_tab_change); self.tab_view.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.tabs = {}
        self.notification_widgets = {}
        
        self.create_dashboard_tab()
        self.create_tab("Produtos", ["ID", "Nome", "SKU", "Descrição", "Qtd em Estoque"], [40, 250, 120, 300, 100], self.db_manager.get_all_products, self.open_product_form, self.open_product_form, self.delete_product)
        self.create_tab("Clientes", ["ID", "Nome", "CPF/CNPJ", "Telefone", "Email"], [50, 200, 150, 120, 200], self.db_manager.get_all_clients, self.open_client_form, self.open_client_form, self.delete_client)
        self.create_tab("Fornecedores", ["ID", "Nome", "Contato", "Endereço"], [50, 200, 150, 300], self.db_manager.get_all_suppliers, self.open_supplier_form, self.open_supplier_form, self.delete_supplier)
        self.create_movement_tab()
        self.create_tab("Usuários", ["ID", "Usuário", "Nível de Acesso"], [50, 200, 150], self.db_manager.get_all_users, self.open_user_form, self.open_user_form, self.delete_user)
        self.create_notifications_tab()
        
        self.setup_styles(); self.toggle_theme()
        self.after(100, self.dashboard_tab_instance.update_graph)
        self.apply_permissions()
        self.check_inactivity_notifications()
        self.update_notifications_button()

    def apply_permissions(self):
        level = self.current_user_level
        self.on_tab_change()
        if level == 'Operador':
            for tab_name in ["Produtos", "Clientes", "Fornecedores", "Usuários", "Notificações"]:
                try: self.tab_view.delete(tab_name)
                except Exception: pass
            self.notifications_button.pack_forget()
            self.export_button.pack_forget()
        if level == 'Supervisor':
            try: self.tab_view.delete("Usuários")
            except Exception: pass
            if "Produtos" in self.tabs:
                product_tab_controls = self.tabs["Produtos"]['frame'].winfo_children()[0]
                for button in product_tab_controls.winfo_children():
                    if "Excluir" in button.cget("text"): button.configure(state="disabled")
        if level != 'Administrador' and hasattr(self, 'reverse_mov_button'):
            self.reverse_mov_button.pack_forget()

    def on_tab_change(self):
        current_tab = self.tab_view.get()
        notif_button = self.tab_view._segmented_button._buttons_dict.get("Notificações")
        if notif_button:
            if current_tab != "Notificações":
                notif_button.grid_forget()

    def create_dashboard_tab(self):
        dashboard_frame = self.tab_view.add("Dashboard"); self.dashboard_tab_instance = DashboardTab(parent=dashboard_frame, db_manager=self.db_manager, main_app=self); self.dashboard_tab_instance.pack(fill="both", expand=True)
    def create_tab(self, name, columns, widths, fetch_func, add_cmd, edit_cmd, del_cmd):
        tab = self.tab_view.add(name); tab.grid_rowconfigure(1, weight=1); tab.grid_columnconfigure(0, weight=1)
        controls_frame = ctk.CTkFrame(tab); controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(controls_frame, text=f"Adicionar {name[:-1]}", command=add_cmd).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text=f"Editar Selecionado", command=lambda: edit_cmd(edit=True)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text=f"Excluir Selecionado", command=del_cmd, fg_color="#d9534f").pack(side="left", padx=10, pady=10)
        tree_frame = ctk.CTkFrame(tab); tree_frame.grid(row=1, column=0, sticky="nsew"); tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, width in zip(columns, widths): tree.heading(col, text=col); tree.column(col, width=width, anchor="center")
        tree.grid(row=0, column=0, sticky="nsew"); scrollbar = ctk.CTkScrollbar(tree_frame, command=tree.yview); scrollbar.grid(row=0, column=1, sticky="ns"); tree.configure(yscrollcommand=scrollbar.set)
        self.tabs[name] = {'frame': tab, 'fetch': fetch_func, 'tree': tree}; self.refresh_tab(name)
    
    def create_movement_tab(self):
        name = "Movimentações"; tab = self.tab_view.add(name); tab.grid_rowconfigure(1, weight=1); tab.grid_columnconfigure(0, weight=1)
        top_frame = ctk.CTkFrame(tab); top_frame.grid(row=0, column=0, sticky="ew")
        row1_frame = ctk.CTkFrame(top_frame, fg_color="transparent"); row1_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(row1_frame, text="Produto:", width=60).pack(side="left", padx=(5,0)); self.mov_prod_combo = ctk.CTkComboBox(row1_frame, values=[], width=200); self.mov_prod_combo.pack(side="left", padx=5)
        ctk.CTkLabel(row1_frame, text="Tipo:", width=40).pack(side="left", padx=(10,0)); self.mov_type_combo = ctk.CTkComboBox(row1_frame, values=["Entrada", "Saida"], width=100, command=self.update_origin_dest_list); self.mov_type_combo.pack(side="left", padx=5)
        ctk.CTkLabel(row1_frame, text="Qtd:", width=30).pack(side="left", padx=(10,0)); self.mov_qtd_entry = ctk.CTkEntry(row1_frame, width=80); self.mov_qtd_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row1_frame, text="Preço Unit.:", width=80).pack(side="left", padx=(10,0)); self.mov_price_entry = ctk.CTkEntry(row1_frame, width=100, placeholder_text="Obrigatório"); self.mov_price_entry.pack(side="left", padx=5)
        row2_frame = ctk.CTkFrame(top_frame, fg_color="transparent"); row2_frame.pack(fill="x", padx=5, pady=2)
        self.origin_dest_label = ctk.CTkLabel(row2_frame, text="Fornecedor:", width=80); self.origin_dest_label.pack(side="left", padx=(5,0))
        self.origin_dest_combo = ctk.CTkComboBox(row2_frame, values=[], width=200); self.origin_dest_combo.pack(side="left", padx=5)
        ctk.CTkButton(row2_frame, text="Registrar", command=self.add_movement).pack(side="left", padx=(20, 10))
        self.reverse_mov_button = ctk.CTkButton(row2_frame, text="Reverter Selecionada", command=self.reverse_movement, fg_color="#ffc107", text_color="black")
        self.reverse_mov_button.pack(side="left", padx=10)
        columns = ["ID", "Produto", "Usuário", "Tipo", "Qtd", "Preço Unit.", "Origem/Destino", "Data/Hora"]; widths = [40, 150, 100, 80, 60, 100, 150, 150]
        tree_frame = ctk.CTkFrame(tab); tree_frame.grid(row=1, column=0, sticky="nsew"); tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, width in zip(columns, widths): tree.heading(col, text=col); tree.column(col, width=width, anchor="center")
        tree.grid(row=0, column=0, sticky="nsew"); self.tabs[name] = {'frame': tab, 'fetch': self.db_manager.get_all_movements, 'tree': tree}; self.refresh_tab(name); self.update_movement_product_list()
        self.update_origin_dest_list()

    def create_notifications_tab(self):
        name = "Notificações"; tab = self.tab_view.add(name); tab.grid_rowconfigure(1, weight=1); tab.grid_columnconfigure(0, weight=1)
        controls_frame = ctk.CTkFrame(tab); controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(controls_frame, text="Marcar Selecionada como Lida", command=self.mark_notification_read).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(controls_frame, text="Limpar Notificações Lidas", command=self.clear_read_notifications, fg_color="#d9534f").pack(side="left", padx=10, pady=10)
        columns = ["ID", "Mensagem", "Data/Hora", "Status"]; widths = [40, 600, 150, 100]
        tree_frame = ctk.CTkFrame(tab); tree_frame.grid(row=1, column=0, sticky="nsew"); tree_frame.grid_rowconfigure(0, weight=1); tree_frame.grid_columnconfigure(0, weight=1)
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col, width in zip(columns, widths): tree.heading(col, text=col); tree.column(col, width=width, anchor="w" if col == "Mensagem" else "center")
        tree.grid(row=0, column=0, sticky="nsew")
        self.notification_widgets = {'frame': tab, 'fetch': self.db_manager.get_all_notifications, 'tree': tree}
        self.refresh_notifications()
    
    def refresh_notifications(self):
        tree = self.notification_widgets['tree']; fetch_func = self.notification_widgets['fetch']
        for item in tree.get_children(): tree.delete(item)
        for row in fetch_func(): tree.insert("", "end", values=row)

    def show_notifications_tab(self):
        self.refresh_notifications()
        self.tab_view.set("Notificações")

    def open_scanner(self):
        """Open the ScannerWindow which will call back with the detected barcode string."""
        try:
            ScannerWindow(self, self._on_barcode_scanned)
        except Exception as e:
            messagebox.showerror("Erro no Scanner", f"Não foi possível iniciar o scanner:\n{e}")

    def _on_barcode_scanned(self, code_str):
        """Handle barcode results: treat code_str as EAN/UPC barcode.

        Flow:
        - Check if product exists by barcode
        - If not found, try OpenFoodFacts lookup by barcode
        - If found in OFF, prefill creation form with OFF data, generated SKU, and barcode
        - If URL detected, try to fetch product info and create with appropriate fields
        - If still not found, offer to create a product with unique SKU and store barcode
        """
        code = code_str.strip()
        
        # First check if the product already exists by barcode
        existing_product = self.db_manager.get_product_by_barcode(code)
        if existing_product:
            messagebox.showinfo("Produto Encontrado", f"Produto já cadastrado: {existing_product[1]}")
            return

        # If scanner returned a URL, try to fetch product info from the page
        if 'http' in code.lower() or ('/' in code and '.' in code):
            url_info = fetch_product_from_url(code)
            if url_info:
                name = url_info.get('name')
                desc = url_info.get('desc') or code
                category = deduce_category_from_name(name)
                brand_abbr = 'UNKN'
                name_abbr = normalize_text(name).upper()[:4] if name else 'PROD'
                variation = 'VAR'
                suggested_sku = f"{category}-{brand_abbr}-{name_abbr}-{variation}"
                prefill = {
                    'name': name, 
                    'sku': suggested_sku, 
                    'desc': desc,
                    'barcode': code  # Store the URL as barcode for reference
                }
                if messagebox.askyesno("Produto via URL", f"Detectei um link de produto: '{name}'. Deseja criar com os dados encontrados?"):
                    def _on_created(new_id):
                        self.update_movement_product_list()
                        try: self.refresh_tab("Produtos")
                        except Exception: pass
                        try:
                            if hasattr(self, 'dashboard_tab_instance'):
                                self.dashboard_tab_instance._populate_product_filter()
                        except Exception: pass
                        p = self.db_manager.get_product_by_id(new_id)
                        if p:
                            try: self.mov_prod_combo.set(f"{p[0]} - {p[1]}")
                            except Exception: pass
                    AddProductFromSKU(self, self.db_manager, suggested_sku, on_created=_on_created, prefill=prefill)
                    return
                    
        # Try to look up barcode in multiple product databases
        try:
            # Setup common request parameters
            timeout = 5  # 5 seconds timeout
            headers = {'User-Agent': 'SistemaDeEstoque/1.0'}  # Custom user agent
            
            # Try Brazilian version of OpenFoodFacts first (for better Brazilian product coverage)
            br_off_url = f"https://br.openfoodfacts.org/api/v0/product/{code}.json"
            try:
                response = requests.get(br_off_url, headers=headers, timeout=timeout)
                data = response.json()
            except (requests.RequestException, ValueError) as e:
                print(f"Error with BR OpenFoodFacts: {e}")
                data = {'status': 0}
            
            # If not found, try global OpenFoodFacts
            if data.get('status') != 1:
                off_url = f"https://world.openfoodfacts.org/api/v0/product/{code}.json"
                try:
                    response = requests.get(off_url, headers=headers, timeout=timeout)
                    data = response.json()
                except (requests.RequestException, ValueError) as e:
                    print(f"Error with OpenFoodFacts: {e}")
                    data = {'status': 0}
            
            # If not found, try OpenBeautyFacts
            if data.get('status') != 1:
                obf_url = f"https://world.openbeautyfacts.org/api/v0/product/{code}.json"
                try:
                    response = requests.get(obf_url, headers=headers, timeout=timeout)
                    data = response.json()
                except (requests.RequestException, ValueError) as e:
                    print(f"Error with OpenBeautyFacts: {e}")
                    data = {'status': 0}
            
            # If still not found, try Cosméticos Info (Brazilian products)
            if data.get('status') != 1:
                try:
                    cosm_url = f"https://api.cosmos.bluesoft.com.br/gtins/{code}"
                    cosmos_headers = {
                        "X-Cosmos-Token": "TW15RE6jMpm_wPYh1tYFOQ",
                        "Content-Type": "application/json",
                        "User-Agent": "SistemaDeEstoque/1.0"
                    }
                    response = requests.get(cosm_url, headers=cosmos_headers, timeout=timeout)
                    cosm_data = response.json()
                    
                    if cosm_data and 'description' in cosm_data:
                        # Convert Cosmos data to our format
                        # Handle common Brazilian brand names
                        brand = cosm_data.get('brand', {}).get('name', '')
                        if isinstance(brand, str):
                            # Map common variations to standard names
                            brand_map = {
                                'UNILEVER': 'Unilever',
                                'SEDA': 'Seda',
                                'DOVE': 'Dove',
                                'NATURA': 'Natura',
                                'AVON': 'Avon',
                                'BOTICARIO': 'O Boticário'
                            }
                            brand = brand_map.get(brand.upper(), brand)
                        
                        data = {
                            'status': 1,
                            'product': {
                                'product_name': cosm_data.get('description', ''),
                                'brands': brand or 'UNKN',
                                'generic_name': cosm_data.get('commercial_unit', {}).get('description', ''),
                                'quantity': cosm_data.get('net_weight', ''),
                                'categories_tags': ['Cosméticos', 'Higiene Pessoal']  # Add relevant categories
                            }
                        }
                except Exception as ce:
                    print(f"Cosmos API error: {ce}")
            
            if data.get('status') == 1 and data.get('product'):
                api_source = "Cosméticos Info" if 'cosmos.bluesoft' in response.url else (
                    "OpenBeautyFacts" if "openbeautyfacts" in response.url else "OpenFoodFacts")
                sku, prefill = generate_sku_from_off(data['product'])
                prefill['barcode'] = code  # Store original barcode
                
                # Update category based on API source
                if api_source in ["OpenBeautyFacts", "Cosméticos Info"]:
                    sku = sku.replace("UNKN-", "BEAU-")  # Change unknown category to beauty
                
                # Prepare detailed message with product info
                msg = f"Produto encontrado no {api_source}:\n\n"
                msg += f"Nome: {prefill['name']}\n"
                if prefill.get('brand'):
                    msg += f"Marca: {prefill['brand']}\n"
                if data['product'].get('quantity'):
                    msg += f"Quantidade: {data['product']['quantity']}\n"
                msg += f"\nSKU Sugerido: {sku}\n"
                msg += "\nDeseja criar com os dados encontrados?"

                if messagebox.askyesno("Produto Encontrado", msg):
                    def _on_created(new_id):
                        self.update_movement_product_list()
                        try: self.refresh_tab("Produtos")
                        except Exception: pass
                        try:
                            if hasattr(self, 'dashboard_tab_instance'):
                                self.dashboard_tab_instance._populate_product_filter()
                        except Exception: pass
                        p = self.db_manager.get_product_by_id(new_id)
                        if p:
                            try: self.mov_prod_combo.set(f"{p[0]} - {p[1]}")
                            except Exception: pass
                    AddProductFromSKU(self, self.db_manager, sku, on_created=_on_created, prefill=prefill)
                    return
        except Exception as e:
            print(f"Error fetching product data: {e}")

        # First try OpenFoodFacts (EAN/UPC)
        off_prod = fetch_openfoodfacts_product(code)
        if off_prod:
            sku_suggested, meta = generate_sku_from_off(off_prod)
            prefill = {
                'name': meta.get('name') or off_prod.get('product_name'),
                'sku': sku_suggested,
                'desc': off_prod.get('brands') or '',
                'qty': off_prod.get('quantity')
            }
            # If SKU generated already exists in DB, select it
            existing = self.db_manager.get_product_by_sku(sku_suggested)
            if existing:
                prod_id, prod_name = existing[0], existing[1]
                self.update_movement_product_list()
                try: self.mov_prod_combo.set(f"{prod_id} - {prod_name}")
                except Exception: pass
                messagebox.showinfo("Produto Encontrado", f"Produto já cadastrado: {prod_name}\nSelecionado para movimentação.")
                return
            # otherwise open creation dialog with prefill
            if messagebox.askyesno("Produto encontrado no OpenFoodFacts", f"Produto '{prefill['name']}' encontrado. Deseja criar com os dados sugeridos?"):
                def _on_created(new_id):
                    # Refresh movement product combo, products tab and dashboard filter
                    self.update_movement_product_list()
                    try: self.refresh_tab("Produtos")
                    except Exception: pass
                    try:
                        if hasattr(self, 'dashboard_tab_instance'):
                            self.dashboard_tab_instance._populate_product_filter()
                    except Exception: pass
                    p = self.db_manager.get_product_by_id(new_id)
                    if p:
                        try: self.mov_prod_combo.set(f"{p[0]} - {p[1]}")
                        except Exception: pass
                AddProductFromSKU(self, self.db_manager, sku_suggested, on_created=_on_created, prefill=prefill)
            return

        # Final fallback: Generate a unique SKU and store the barcode
        category = 'GEN'  # Generic category
        brand_abbr = 'UNKN'  # Unknown brand
        name_abbr = 'PROD'  # Generic product
        variation = datetime.now().strftime('%m%d')  # Use date for variation to ensure uniqueness
        suggested_sku = f"{category}-{brand_abbr}-{name_abbr}-{variation}"
        msg = f"Código de barras '{code}' não encontrado nas bases de dados.\n\n" + \
              "Deseja cadastrar um novo produto?\n" + \
              "O código será armazenado como código de barras do produto."
        prefill = {'barcode': code}  # Guarda o código de barras
        
        if messagebox.askyesno("Cadastrar Produto", msg):
            def _on_created(new_id):
                self.update_movement_product_list()
                try: self.refresh_tab("Produtos")
                except Exception: pass
                try:
                    if hasattr(self, 'dashboard_tab_instance'):
                        self.dashboard_tab_instance._populate_product_filter()
                except Exception: pass
                p = self.db_manager.get_product_by_id(new_id)
                if p:
                    try: self.mov_prod_combo.set(f"{p[0]} - {p[1]}")
                    except Exception: pass
            # Passa os dados de preenchimento incluindo o código de barras
            AddProductFromSKU(self, self.db_manager, suggested_sku, on_created=_on_created, prefill=prefill)

    def update_notifications_button(self):
        count = self.db_manager.get_unread_notification_count()
        if count > 0: self.notifications_button.configure(text=f"Notificações ({count})", fg_color="#d9534f")
        else: self.notifications_button.configure(text="Notificações", fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"])
    
    def show_history_window(self, product_id, product_name, movement_type):
        """Open a HistoryWindow for the given product and movement type.

        This is called by other UI components (e.g. DashboardTab) so they
        don't need to import/instantiate HistoryWindow directly.
        """
        HistoryWindow(self, self.db_manager, product_id, product_name, movement_type)
    def mark_notification_read(self):
        selected_item = self.notification_widgets['tree'].focus()
        if not selected_item:
            messagebox.showwarning("Nenhuma Seleção", "Por favor, selecione uma notificação na lista."); return
        notif_id = self.notification_widgets['tree'].item(selected_item)['values'][0]
        self.db_manager.mark_notification_as_read(notif_id)
        self.refresh_notifications(); self.update_notifications_button()
    def clear_read_notifications(self):
        if messagebox.askyesno("Confirmar", "Deseja limpar todas as notificações que já foram lidas?"):
            self.db_manager.clear_read_notifications(); self.refresh_notifications()
    def check_inactivity_notifications(self):
        days = self.config.getint('Settings', 'inactivity_days', fallback=20)
        inactive_products = self.db_manager.get_inactive_products(days)
        for pid, name in inactive_products:
            self.db_manager.add_notification(f"INATIVIDADE: Produto '{name}' não tem movimentação há mais de {days} dias.")
        if inactive_products: self.update_notifications_button()

    def refresh_tab(self, name):
        if name not in self.tabs or not self.tabs[name].get('tree'): return
        tree = self.tabs[name]['tree']; fetch_func = self.tabs[name]['fetch']
        for item in tree.get_children(): tree.delete(item)
        for row in fetch_func(): tree.insert("", "end", values=row)
    def get_selected_item(self, tab_name):
        tree = self.tabs[tab_name]['tree']; selected_item = tree.focus()
        if not selected_item: messagebox.showwarning("Nenhuma Seleção", f"Por favor, selecione um item na lista de {tab_name}."); return None
        return tree.item(selected_item)['values']

    def open_product_form(self, edit=False):
        data = self.get_selected_item("Produtos") if edit else None
        if edit and not data: return
        qty_label = "Estoque Atual" if edit else "Quantidade Inicial"
        fields = collections.OrderedDict([
            ("Nome", {"type": "text", "required": True, "max_len": 60}), 
            ("SKU", {"type": "text", "required": True}), 
            ("Código de Barras", {"type": "text", "required": False}),
            ("Descrição", {"type": "text", "required": False}),
            (qty_label, {"type": "int", "required": True})
        ])
        title = "Editar Produto" if edit else "Adicionar Produto"
        ValidatedForm(self, title, fields, self.save_product, data)
    def save_product(self, data):
        try:
            qty = data.get("Quantidade Inicial", data.get("Estoque Atual"))
            barcode = data.get("Código de Barras", "")
            if 'id' in data: result = self.db_manager.update_product(data['id'], data['Nome'], data['SKU'], data['Descrição'], qty, barcode)
            else: result = self.db_manager.add_product(data['Nome'], data['SKU'], data['Descrição'], qty, barcode)
            if isinstance(result, str): return result
            self.refresh_tab("Produtos"); self.update_movement_product_list()
            self.dashboard_tab_instance._populate_product_filter()
            return "Success"
        except Exception as e: return str(e)
    def delete_product(self):
        data = self.get_selected_item("Produtos")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o produto '{data[1]}'?"):
            self.db_manager.delete_product(data[0]); self.refresh_tab("Produtos"); self.update_movement_product_list()
            self.dashboard_tab_instance._populate_product_filter()
    
    def open_client_form(self, edit=False):
        data = self.get_selected_item("Clientes") if edit else None
        if edit and not data: return
        fields = collections.OrderedDict([
            ("Nome", {"type": "text", "required": True, "max_len": 60}), 
            ("CPF/CNPJ", {"type": "text", "required": False, "validation": {"pattern": r"^\d{11}$|^\d{14}$", "message": "CPF (11 dígitos) ou CNPJ (14 dígitos) inválido."}}), 
            ("Telefone", {"type": "text", "required": False, "validation": {"pattern": r"^\d{10,11}$", "message": "Telefone inválido. Use apenas números (10 ou 11 dígitos)."}}), 
            ("Email", {"type": "text", "required": False, "validation": {"pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", "message": "Formato de e-mail inválido."}}), 
            ("Endereço", {"type": "text", "required": False})
        ])
        title = "Editar Cliente" if edit else "Adicionar Cliente"
        ValidatedForm(self, title, fields, self.save_client, data)
    def save_client(self, data):
        try:
            if 'id' in data: result = self.db_manager.update_client(data['id'], data['Nome'], data['CPF/CNPJ'], data['Telefone'], data['Email'], data['Endereço'])
            else: result = self.db_manager.add_client(data['Nome'], data['CPF/CNPJ'], data['Telefone'], data['Email'], data['Endereço'])
            if isinstance(result, str): return result
            self.refresh_tab("Clientes"); self.update_origin_dest_list()
            return "Success"
        except Exception as e: return str(e)
    def delete_client(self):
        data = self.get_selected_item("Clientes")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o cliente '{data[1]}'?"):
            self.db_manager.delete_client(data[0]); self.refresh_tab("Clientes"); self.update_origin_dest_list()
    
    def open_supplier_form(self, edit=False):
        data = self.get_selected_item("Fornecedores") if edit else None
        if edit and not data: return
        fields = collections.OrderedDict([
            ("Nome", {"type": "text", "required": True, "max_len": 60}), 
            ("Contato", {"type": "text", "required": False}), 
            ("Endereço", {"type": "text", "required": False})
        ])
        title = "Editar Fornecedor" if edit else "Adicionar Fornecedor"
        ValidatedForm(self, title, fields, self.save_supplier, data)
    def save_supplier(self, data):
        try:
            if 'id' in data: result = self.db_manager.update_supplier(data['id'], data['Nome'], data['Contato'], data['Endereço'])
            else: result = self.db_manager.add_supplier(data['Nome'], data['Contato'], data['Endereço'])
            if isinstance(result, str): return result
            self.refresh_tab("Fornecedores"); self.update_origin_dest_list()
            return "Success"
        except Exception as e: return str(e)
    def delete_supplier(self):
        data = self.get_selected_item("Fornecedores")
        if data and messagebox.askyesno("Confirmar", f"Deseja excluir o fornecedor '{data[1]}'?"):
            self.db_manager.delete_supplier(data[0]); self.refresh_tab("Fornecedores"); self.update_origin_dest_list()
    
    def open_user_form(self, edit=False):
        data = self.get_selected_item("Usuários") if edit else None
        if edit and not data: return
        fields = collections.OrderedDict([
            ("Usuário", {"type": "text", "required": True}), 
            ("Senha", {"type": "password", "required": not edit}),
            ("Nível de Acesso", {"type": "text", "required": True, "widget": "combobox", "values": ["Operador", "Supervisor", "Administrador"]})
        ])
        title = "Editar Usuário" if edit else "Adicionar Usuário"
        ValidatedForm(self, title, fields, self.save_user, data)
    def save_user(self, data):
        target_user_id = data.get('id')
        if target_user_id == self.current_user_id:
            return "Você não pode editar seu próprio usuário."
        if target_user_id:
            target_user_data = self.db_manager.get_user_by_id(target_user_id)
            target_level = target_user_data[3]
            if self.level_hierarchy[target_level] >= self.level_hierarchy[self.current_user_level]:
                return "Você não pode editar um usuário de nível igual ou superior."
        try:
            if 'id' in data: result = self.db_manager.update_user(data['id'], data['Usuário'], data['Senha'], data['Nível de Acesso'])
            else: result = self.db_manager.add_user(data['Usuário'], data['Senha'], data['Nível de Acesso'])
            if isinstance(result, str): return result
            self.refresh_tab("Usuários"); self.update_notifications_button()
            return "Success"
        except Exception as e: return str(e)
    def delete_user(self):
        data = self.get_selected_item("Usuários")
        if not data: return
        target_user_id = data[0]
        if target_user_id == self.current_user_id:
            messagebox.showerror("Acesso Negado", "Você não pode excluir seu próprio usuário."); return
        target_level = data[2]
        if self.level_hierarchy[target_level] >= self.level_hierarchy[self.current_user_level]:
            messagebox.showerror("Acesso Negado", "Você não pode excluir um usuário de nível igual ou superior."); return
        if messagebox.askyesno("Confirmar", f"Deseja excluir o usuário '{data[1]}'?"):
            self.db_manager.delete_user(target_user_id); self.refresh_tab("Usuários")
    
    def update_movement_product_list(self):
        products = self.db_manager.get_all_products(); self.product_map = {f"{p[0]} - {p[1]}": p[0] for p in products}; product_list = list(self.product_map.keys())
        self.mov_prod_combo.configure(values=product_list)
        if product_list: self.mov_prod_combo.set(product_list[0])
        else: self.mov_prod_combo.set("")
    
    def update_origin_dest_list(self, event=None):
        mov_type = self.mov_type_combo.get()
        if mov_type == "Entrada":
            self.origin_dest_label.configure(text="Fornecedor:")
            suppliers = self.db_manager.get_all_suppliers()
            self.origin_dest_map = {f"{s[0]} - {s[1]}": s[0] for s in suppliers}
        else:
            self.origin_dest_label.configure(text="Cliente:")
            clients = self.db_manager.get_all_clients()
            self.origin_dest_map = {f"{c[0]} - {c[1]}": c[0] for c in clients}
        
        values = list(self.origin_dest_map.keys())
        self.origin_dest_combo.configure(values=values)
        if values: self.origin_dest_combo.set(values[0])
        else: self.origin_dest_combo.set("")

    def add_movement(self):
        prod_selection = self.mov_prod_combo.get(); tipo = self.mov_type_combo.get()
        qtd_str = self.mov_qtd_entry.get(); price_str = self.mov_price_entry.get()
        origin_dest_selection = self.origin_dest_combo.get()
        if not all([prod_selection, tipo, qtd_str, price_str, origin_dest_selection]):
            messagebox.showerror("Erro", "Todos os campos são obrigatórios."); return
        confirm_msg = f"Confirma o registro de uma '{tipo.upper()}' de {qtd_str} unidade(s) de '{prod_selection.split(' - ')[-1]}' ao preço de R$ {price_str} cada?"
        if not messagebox.askyesno("Confirmar Movimentação", confirm_msg):
            return
        prod_id = self.product_map.get(prod_selection)
        origin_dest_id = self.origin_dest_map.get(origin_dest_selection)
        if prod_id is None or origin_dest_id is None: messagebox.showerror("Erro", "Seleção inválida."); return
        try:
            qtd = int(qtd_str)
            if qtd <= 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Erro de Formato", "Quantidade deve ser um número inteiro positivo."); return
        try:
            preco = float(price_str.replace(',', '.'))
            if preco < 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Erro de Formato", "Preço Unitário deve ser um número válido e não negativo."); return
        id_cliente, id_fornecedor = (None, origin_dest_id) if tipo == "Entrada" else (origin_dest_id, None)
        result = self.db_manager.add_movement(prod_id, self.current_user_id, tipo.lower(), qtd, preco, id_cliente, id_fornecedor)
        if result == "Sucesso":
            messagebox.showinfo("Sucesso", "Movimentação registrada.")
            self.refresh_tab("Movimentações"); self.refresh_tab("Produtos")
            self.mov_qtd_entry.delete(0, 'end'); self.mov_price_entry.delete(0, 'end')
            self.dashboard_tab_instance.update_graph(); self.update_notifications_button()
        else:
            messagebox.showerror("Erro na Movimentação", result)

    def reverse_movement(self):
        selected = self.get_selected_item("Movimentações")
        if not selected: return
        mov_id = selected[0]
        warning_msg = "AVISO: Reverter uma movimentação irá deletar o registro e ajustar o estoque do produto. Esta ação não pode ser desfeita e pode afetar a precisão de relatórios financeiros. Use apenas para corrigir erros claros.\n\nDeseja continuar e reverter esta movimentação?"
        if not messagebox.askyesno("Confirmar Reversão", warning_msg):
            return
        result = self.db_manager.reverse_movement(mov_id)
        if result == "Sucesso":
            messagebox.showinfo("Sucesso", "Movimentação revertida.")
            self.refresh_tab("Movimentações"); self.refresh_tab("Produtos")
            self.dashboard_tab_instance.update_graph(); self.update_notifications_button()
        else:
            messagebox.showerror("Erro", result)

    def open_export_dialog(self):
        ExportDialog(parent=self, on_export_callback=self.handle_export)

    def handle_export(self, file_type):
        if file_type == "csv":
            self.export_data_to_csv()
        elif file_type == "pdf":
            self.dashboard_tab_instance.export_to_pdf()

    def export_data_to_csv(self):
        export_path = self.config.get('Settings', 'export_path', fallback='./exports')
        if not os.path.exists(export_path):
            os.makedirs(export_path)
        filepath = os.path.join(export_path, f"export_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                tables_to_export = {
                    "PRODUTOS": (self.db_manager.get_all_products, ["ID", "Nome", "SKU", "Descrição", "Qtd em Estoque"]),
                    "CLIENTES": (self.db_manager.get_all_clients, ["ID", "Nome", "CPF/CNPJ", "Telefone", "Email"]),
                    "FORNECEDORES": (self.db_manager.get_all_suppliers, ["ID", "Nome", "Contato", "Endereço"]),
                    "MOVIMENTACOES": (self.db_manager.get_all_movements, ["ID", "Produto", "Usuário", "Tipo", "Qtd", "Preço Unit.", "Origem/Destino", "Data/Hora"]),
                    "USUARIOS": (self.db_manager.get_all_users, ["ID", "Usuário", "Nível de Acesso"])
                }
                for table_title, (fetch_func, headers) in tables_to_export.items():
                    writer.writerow([f"--- DADOS DE {table_title} ---"])
                    writer.writerow(headers)
                    data = fetch_func()
                    if data: writer.writerows(data)
                    writer.writerow([])
            messagebox.showinfo("Sucesso", f"Dados exportados com sucesso para:\n{filepath}")
            self.db_manager.add_notification("Dados do sistema foram exportados para CSV.")
            self.update_notifications_button()
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Ocorreu um erro: {e}")

    def setup_styles(self):
        self.style = ttk.Style(); self.style.theme_use("default")
    def toggle_theme(self):
        mode = "dark" if self.theme_switch.get() == 1 else "light"; ctk.set_appearance_mode(mode)
        bg_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"]); text_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"]); selected_color = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"]); header_bg = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["top_fg_color"])
        self.style.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color, borderwidth=0); self.style.map('Treeview', background=[('selected', selected_color)])
        self.style.configure("Treeview.Heading", background=header_bg, foreground=text_color, relief="flat", font=('Calibri', 10, 'bold')); self.style.map("Treeview.Heading", background=[('active', '#3484F0')])
        if hasattr(self, 'dashboard_tab_instance'): self.dashboard_tab_instance.update_theme()