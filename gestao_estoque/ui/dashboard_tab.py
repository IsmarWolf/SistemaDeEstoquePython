# ui/dashboard_tab.py (COMPLETO E CORRIGIDO)

import customtkinter as ctk
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import colorsys
import matplotlib.patheffects as path_effects

class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent, fg_color="transparent")
        self.db_manager = db_manager
        self.product_map = {}
        self.bar_metadata = []
        self.selected_pid = None
        self.hovered_bar_info = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=300)
        
        controls_frame = ctk.CTkFrame(self); controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(controls_frame, text="Filtrar por Produto:").pack(side="left", padx=(10, 5), pady=10)
        self.product_filter_combo = ctk.CTkComboBox(controls_frame, width=250, command=self.update_graph)
        self.product_filter_combo.pack(side="left", padx=(0, 20), pady=10)
        ctk.CTkLabel(controls_frame, text="Visualizar:").pack(side="left", padx=(10, 5), pady=10)
        self.view_mode_var = ctk.StringVar(value="Valor")
        self.radio_valor = ctk.CTkRadioButton(controls_frame, text="Valor (R$)", variable=self.view_mode_var, value="Valor", command=self.update_graph)
        self.radio_valor.pack(side="left", padx=5)
        self.radio_qtd = ctk.CTkRadioButton(controls_frame, text="Quantidade", variable=self.view_mode_var, value="Quantidade", command=self.update_graph)
        self.radio_qtd.pack(side="left", padx=5)
        
        self.graph_frame = ctk.CTkFrame(self); self.graph_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.info_panel = ctk.CTkTextbox(self, width=300, state="disabled", wrap="word")
        self.info_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))
        
        # <--- CORREÇÃO AQUI: Usando opções permitidas para destaque ---
        self.info_panel.tag_config("header", underline=True, spacing1=5)
        self.info_panel.tag_config("profit", foreground="green")
        self.info_panel.tag_config("loss", foreground="red")

        self.fig = Figure(figsize=(8, 4), dpi=100); self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget(); self.canvas_widget.pack(side="top", fill="both", expand=True)
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas.mpl_connect("button_press_event", self.on_click)
        
        self._populate_product_filter()

    def _populate_product_filter(self):
        products = self.db_manager.get_all_products()
        self.product_map = {f"{p[0]} - {p[1]}": p[0] for p in products}
        product_list = ["Todos os Produtos"] + list(self.product_map.keys())
        self.product_filter_combo.configure(values=product_list)
        self.product_filter_combo.set("Todos os Produtos")

    def update_graph(self, event=None):
        self.ax.clear()
        self.bar_metadata.clear()
        self.selected_pid = None
        self.hovered_bar_info = None
        self.update_info_panel(None)
        
        selected_product_str = self.product_filter_combo.get()
        if selected_product_str == "Todos os Produtos":
            self._plot_all_products_comparison()
        else:
            product_id = self.product_map.get(selected_product_str)
            if product_id:
                self._plot_single_product(product_id)
        self.update_theme()
        self.canvas.draw()

    def on_hover(self, event):
        if self.selected_pid: return
        
        found_bar = None
        if event.inaxes == self.ax:
            for bar_info in self.bar_metadata:
                contains, _ = bar_info['bar_e'].contains(event)
                if not contains:
                    contains, _ = bar_info['bar_s'].contains(event)
                if contains:
                    found_bar = bar_info
                    break
        
        if found_bar != self.hovered_bar_info:
            self.hovered_bar_info = found_bar
            self.update_bar_visuals()
            self.update_info_panel(found_bar)
            self.canvas.draw_idle()

    def on_click(self, event):
        clicked_bar_info = None
        if event.inaxes == self.ax:
            for bar_info in self.bar_metadata:
                contains, _ = bar_info['bar_e'].contains(event)
                if not contains:
                    contains, _ = bar_info['bar_s'].contains(event)
                if contains:
                    clicked_bar_info = bar_info
                    break
        
        if clicked_bar_info and self.selected_pid == clicked_bar_info['pid']:
            self.selected_pid = None
        else:
            self.selected_pid = clicked_bar_info['pid'] if clicked_bar_info else None
        
        self.update_bar_visuals()
        self.update_info_panel(clicked_bar_info or self.hovered_bar_info)
        self.canvas.draw_idle()

    def update_bar_visuals(self):
        for bar_info in self.bar_metadata:
            pid = bar_info['pid']
            bar_e = bar_info['bar_e']
            bar_s = bar_info['bar_s']
            
            is_selected = (self.selected_pid == pid)
            is_hovered = (self.hovered_bar_info and self.hovered_bar_info['pid'] == pid)
            
            alpha = 1.0 if is_selected or is_hovered else 0.6
            edgecolor = 'yellow' if is_selected else None
            linewidth = 1.5 if is_selected else 0
            
            bar_e.set_alpha(alpha)
            bar_s.set_alpha(alpha)
            bar_e.set_edgecolor(edgecolor); bar_e.set_linewidth(linewidth)
            bar_s.set_edgecolor(edgecolor); bar_s.set_linewidth(linewidth)

    def update_info_panel(self, bar_info):
        self.info_panel.configure(state="normal")
        self.info_panel.delete("1.0", "end")
        
        if not bar_info:
            self.info_panel.insert("1.0", "Passe o mouse sobre uma barra para ver os detalhes.")
            self.info_panel.configure(state="disabled")
            return

        pid = bar_info['pid']
        financials = self.db_manager.get_product_financials(pid)
        product_data = self.db_manager.get_product_by_id(pid)
        
        total_gasto = financials[0] or 0
        total_vendido = financials[1] or 0
        total_itens_vendidos = financials[2] or 0
        estoque_atual = product_data[4]
        lucro = total_vendido - total_gasto

        self.info_panel.insert("end", f"Produto: {product_data[1]}\n", "header")
        self.info_panel.insert("end", f"\nEstoque Atual: {estoque_atual}\n")
        self.info_panel.insert("end", f"Total de Itens Vendidos: {total_itens_vendidos}\n\n")
        self.info_panel.insert("end", f"Total Gasto (Custo): R$ {total_gasto:.2f}\n")
        self.info_panel.insert("end", f"Total Faturado (Venda): R$ {total_vendido:.2f}\n")
        
        lucro_tag = "profit" if lucro >= 0 else "loss"
        self.info_panel.insert("end", f"Lucro Total: R$ {lucro:.2f}", lucro_tag)
        
        self.info_panel.configure(state="disabled")

    def _plot_all_products_comparison(self):
        data = self.db_manager.get_summary_for_all_products(); view_mode = self.view_mode_var.get()
        if not data:
            self.ax.text(0.5, 0.5, 'Sem movimentações para exibir.', ha='center', va='center', transform=self.ax.transAxes); return
        data_map = defaultdict(lambda: defaultdict(lambda: {'valor_e': 0, 'valor_s': 0, 'qtd_e': 0, 'qtd_s': 0}))
        product_names = {}; all_days = set()
        for day, pid, name, ve, vs, qe, qs in data:
            data_map[day][pid] = {'valor_e': ve, 'valor_s': vs, 'qtd_e': qe, 'qtd_s': qs}
            product_names[pid] = name; all_days.add(day)
        days = sorted(list(all_days)); product_ids = sorted(list(product_names.keys())); num_products = len(product_ids)
        x = np.arange(len(days)); bar_width = 0.8 / (num_products * 2)
        minor_tick_positions = []; minor_tick_labels = []
        for i, pid in enumerate(product_ids):
            product_offset = (i - (num_products - 1) / 2) * (bar_width * 2.2)
            if view_mode == "Valor":
                entradas = [data_map[day][pid]['valor_e'] for day in days]; saidas = [data_map[day][pid]['valor_s'] for day in days]
            else:
                entradas = [data_map[day][pid]['qtd_e'] for day in days]; saidas = [data_map[day][pid]['qtd_s'] for day in days]
            pos_entrada = x + product_offset - bar_width / 2; pos_saida = x + product_offset + bar_width / 2
            minor_tick_positions.extend(x + product_offset)
            short_name = (product_names[pid][:10] + '..') if len(product_names[pid]) > 12 else product_names[pid]
            minor_tick_labels.extend([short_name] * len(days))
            
            bars_e = self.ax.bar(pos_entrada, entradas, width=bar_width, color='#d9534f')
            bars_s = self.ax.bar(pos_saida, saidas, width=bar_width, color='#5cb85c')
            
            for bar_e, bar_s in zip(bars_e, bars_s):
                self.bar_metadata.append({'bar_e': bar_e, 'bar_s': bar_s, 'pid': pid})

        if view_mode == "Valor":
            self.ax.set_ylabel("Valor Movimentado (R$)"); self.ax.set_title("Comparativo de Movimentação Financeira por Produto")
        else:
            self.ax.set_ylabel("Quantidade Movimentada"); self.ax.set_title("Comparativo de Movimentação de Estoque por Produto")
        self.ax.set_xticks(x); self.ax.set_xticklabels(days, rotation=30, ha="right")
        self.ax.tick_params(axis='x', which='major', pad=20)
        self.ax.set_xticks(minor_tick_positions, minor=True)
        self.ax.set_xticklabels(minor_tick_labels, minor=True, rotation=0, ha='center', fontsize=9)
        for label in self.ax.get_xticklabels(minor=True):
            label.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground='white')])
        self.ax.tick_params(axis='x', which='minor', length=0)
        self.fig.tight_layout()

    def _plot_single_product(self, product_id):
        data = self.db_manager.get_summary_for_single_product(product_id); view_mode = self.view_mode_var.get()
        if not data:
            self.ax.text(0.5, 0.5, 'Sem movimentações para este produto.', ha='center', va='center', transform=self.ax.transAxes); return
        days = [row[0] for row in data]
        if view_mode == "Valor":
            entradas = [row[1] for row in data]; saidas = [row[2] for row in data]
            self.ax.set_ylabel("Valor Movimentado (R$)"); self.ax.set_title(f"Movimentação Financeira do Produto")
        else:
            entradas = [row[3] for row in data]; saidas = [row[4] for row in data]
            self.ax.set_ylabel("Quantidade Movimentada"); self.ax.set_title(f"Movimentação de Estoque do Produto")
        x = np.arange(len(days)); width = 0.35
        bars_e = self.ax.bar(x - width/2, entradas, width, label='Compras (Entrada)', color='#d9534f')
        bars_s = self.ax.bar(x + width/2, saidas, width, label='Vendas (Saída)', color='#5cb85c')
        for bar_e, bar_s in zip(bars_e, bars_s):
            self.bar_metadata.append({'bar_e': bar_e, 'bar_s': bar_s, 'pid': product_id})
        self.ax.set_xticks(x); self.ax.set_xticklabels(days, rotation=45, ha="right")
        self.ax.legend()
        self.fig.tight_layout()

    def update_theme(self):
        bg_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        bg_rgb = self.winfo_rgb(bg_color_name); text_rgb = self.winfo_rgb(text_color_name)
        bg_color_mpl = (bg_rgb[0] / 65535.0, bg_rgb[1] / 65535.0, bg_rgb[2] / 65535.0)
        text_color_mpl = (text_rgb[0] / 65535.0, text_rgb[1] / 65535.0, text_rgb[2] / 65535.0)
        self.fig.patch.set_facecolor(bg_color_mpl); self.ax.set_facecolor(bg_color_mpl)
        self.ax.tick_params(colors=text_color_mpl)
        self.ax.spines['bottom'].set_color(text_color_mpl); self.ax.spines['top'].set_color(text_color_mpl)
        self.ax.spines['left'].set_color(text_color_mpl); self.ax.spines['right'].set_color(text_color_mpl)
        self.ax.yaxis.label.set_color(text_color_mpl); self.ax.title.set_color(text_color_mpl)
        legend = self.ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(bg_color_mpl)
            for text in legend.get_texts():
                text.set_color(text_color_mpl)
        border_color = 'white' if ctk.get_appearance_mode() == "Dark" else 'black'
        for label in self.ax.get_xticklabels(minor=True):
            label.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground=border_color)])
        self.canvas.draw()