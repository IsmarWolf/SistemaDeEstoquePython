# ui/dashboard_tab.py (COMPLETO E CORRIGIDO)

import customtkinter as ctk
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import colorsys

class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, db_manager):
        super().__init__(parent, fg_color="transparent")
        self.db_manager = db_manager
        self.product_map = {}
        self.product_colors = {}
        self.color_index = 0

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # --- Frame de Controles com Filtros ---
        controls_frame = ctk.CTkFrame(self)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(controls_frame, text="Filtrar por Produto:").pack(side="left", padx=(10, 5), pady=10)
        self.product_filter_combo = ctk.CTkComboBox(controls_frame, width=250, command=self.update_graph)
        self.product_filter_combo.pack(side="left", padx=(0, 20), pady=10)

        ctk.CTkLabel(controls_frame, text="Visualizar:").pack(side="left", padx=(10, 5), pady=10)
        self.view_mode_var = ctk.StringVar(value="Valor")
        self.radio_valor = ctk.CTkRadioButton(controls_frame, text="Valor (R$)", variable=self.view_mode_var, value="Valor", command=self.update_graph)
        self.radio_valor.pack(side="left", padx=5)
        self.radio_qtd = ctk.CTkRadioButton(controls_frame, text="Quantidade", variable=self.view_mode_var, value="Quantidade", command=self.update_graph)
        self.radio_qtd.pack(side="left", padx=5)

        # --- Frame do Gráfico ---
        self.graph_frame = ctk.CTkFrame(self)
        self.graph_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.fig = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side="top", fill="both", expand=True)

        self._populate_product_filter()

    def _populate_product_filter(self):
        products = self.db_manager.get_all_products()
        self.product_map = {f"{p[0]} - {p[1]}": p[0] for p in products}
        product_list = ["Todos os Produtos"] + list(self.product_map.keys())
        self.product_filter_combo.configure(values=product_list)
        self.product_filter_combo.set("Todos os Produtos")

    def _get_product_color(self, product_id):
        if product_id not in self.product_colors:
            colormap = plt.cm.get_cmap('gist_rainbow', 300)
            self.product_colors[product_id] = colormap(self.color_index * 15 % 300)
            self.color_index += 1
        return self.product_colors[product_id]

    def update_graph(self, event=None):
        self.ax.clear()
        selected_product_str = self.product_filter_combo.get()
        
        if selected_product_str == "Todos os Produtos":
            self._plot_all_products_comparison()
        else:
            product_id = self.product_map.get(selected_product_str)
            if product_id:
                self._plot_single_product(product_id)

        self.update_theme()
        self.canvas.draw()

    def _plot_all_products_comparison(self):
        data = self.db_manager.get_summary_for_all_products()
        view_mode = self.view_mode_var.get()

        if not data:
            self.ax.text(0.5, 0.5, 'Sem movimentações para exibir.', ha='center', va='center', transform=self.ax.transAxes)
            return

        data_map = defaultdict(lambda: defaultdict(lambda: {'valor_e': 0, 'valor_s': 0, 'qtd_e': 0, 'qtd_s': 0}))
        product_names = {}
        all_days = set()
        for day, pid, name, ve, vs, qe, qs in data:
            data_map[day][pid] = {'valor_e': ve, 'valor_s': vs, 'qtd_e': qe, 'qtd_s': qs}
            product_names[pid] = name
            all_days.add(day)

        days = sorted(list(all_days))
        product_ids = sorted(list(product_names.keys()))
        num_products = len(product_ids)
        
        x = np.arange(len(days))
        bar_width = 0.8 / (num_products * 2)
        
        # --- LÓGICA PARA OS NOMES EMBAIXO DAS COLUNAS ---
        minor_tick_positions = []
        minor_tick_labels = []

        for i, pid in enumerate(product_ids):
            product_offset = (i - (num_products - 1) / 2) * (bar_width * 2.2)

            if view_mode == "Valor":
                entradas = [data_map[day][pid]['valor_e'] for day in days]
                saidas = [data_map[day][pid]['valor_s'] for day in days]
            else:
                entradas = [data_map[day][pid]['qtd_e'] for day in days]
                saidas = [data_map[day][pid]['qtd_s'] for day in days]

            pos_entrada = x + product_offset - bar_width / 2
            pos_saida = x + product_offset + bar_width / 2
            
            # Guarda a posição central do grupo de barras e o nome do produto
            minor_tick_positions.extend(x + product_offset)
            # Quebra o nome do produto se for muito longo
            short_name = (product_names[pid][:8] + '..') if len(product_names[pid]) > 10 else product_names[pid]
            minor_tick_labels.extend([short_name] * len(days))

            # Lógica de cores
            base_color_rgba = self._get_product_color(pid)
            r, g, b, a = base_color_rgba
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            s_saida = max(0, s * 0.8)
            v_saida = v * 0.75
            r_saida, g_saida, b_saida = colorsys.hsv_to_rgb(h, s_saida, v_saida)
            color_saida = (r_saida, g_saida, b_saida, a)

            self.ax.bar(pos_entrada, entradas, width=bar_width, color=base_color_rgba, label=f"{product_names[pid]} - Entrada")
            self.ax.bar(pos_saida, saidas, width=bar_width, color=color_saida, label=f"{product_names[pid]} - Saída")

        if view_mode == "Valor":
            self.ax.set_ylabel("Valor Movimentado (R$)")
            self.ax.set_title("Comparativo de Movimentação Financeira por Produto")
        else:
            self.ax.set_ylabel("Quantidade Movimentada")
            self.ax.set_title("Comparativo de Movimentação de Estoque por Produto")

        # Configura os Ticks Maiores (Datas)
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(days, rotation=30, ha="right")
        self.ax.tick_params(axis='x', which='major', pad=15) # Aumenta o espaço para os nomes

        # Configura os Ticks Menores (Nomes dos Produtos)
        self.ax.set_xticks(minor_tick_positions, minor=True)
        self.ax.set_xticklabels(minor_tick_labels, minor=True, rotation=90, fontsize=7)
        self.ax.tick_params(axis='x', which='minor', length=0) # Esconde a linha do tick menor

        # Remove a legenda, pois os nomes já estão no gráfico
        self.ax.legend().set_visible(False)
        self.fig.tight_layout()

    def _plot_single_product(self, product_id):
        data = self.db_manager.get_summary_for_single_product(product_id)
        view_mode = self.view_mode_var.get()

        if not data:
            self.ax.text(0.5, 0.5, 'Sem movimentações para este produto.', ha='center', va='center', transform=self.ax.transAxes)
            return

        days = [row[0] for row in data]
        if view_mode == "Valor":
            entradas = [row[1] for row in data]
            saidas = [row[2] for row in data]
            self.ax.set_ylabel("Valor Movimentado (R$)")
            self.ax.set_title(f"Movimentação Financeira do Produto ID {product_id}")
        else:
            entradas = [row[3] for row in data]
            saidas = [row[4] for row in data]
            self.ax.set_ylabel("Quantidade Movimentada")
            self.ax.set_title(f"Movimentação de Estoque do Produto ID {product_id}")

        x = np.arange(len(days))
        width = 0.35

        self.ax.bar(x - width/2, entradas, width, label='Compras (Entrada)', color='#28a745')
        self.ax.bar(x + width/2, saidas, width, label='Vendas (Saída)', color='#dc3545')
        
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(days, rotation=45, ha="right")
        self.ax.legend()
        self.fig.tight_layout()

    def update_theme(self):
        bg_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        bg_rgb = self.winfo_rgb(bg_color_name)
        text_rgb = self.winfo_rgb(text_color_name)
        bg_color_mpl = (bg_rgb[0] / 65535.0, bg_rgb[1] / 65535.0, bg_rgb[2] / 65535.0)
        text_color_mpl = (text_rgb[0] / 65535.0, text_rgb[1] / 65535.0, text_rgb[2] / 65535.0)
        
        self.fig.patch.set_facecolor(bg_color_mpl)
        self.ax.set_facecolor(bg_color_mpl)
        self.ax.tick_params(colors=text_color_mpl)
        self.ax.spines['bottom'].set_color(text_color_mpl)
        self.ax.spines['top'].set_color(text_color_mpl)
        self.ax.spines['left'].set_color(text_color_mpl)
        self.ax.spines['right'].set_color(text_color_mpl)
        self.ax.yaxis.label.set_color(text_color_mpl)
        self.ax.title.set_color(text_color_mpl)
        
        legend = self.ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(bg_color_mpl)
            for text in legend.get_texts():
                text.set_color(text_color_mpl)
        self.canvas.draw()