# ui/dashboard_tab.py (COMPLETO E ATUALIZADO COM CALENDÁRIO)

import customtkinter as ctk
from tkinter import filedialog, messagebox
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.patheffects as path_effects
import os
import re
from datetime import datetime
from tkcalendar import Calendar
from reportlab.platypus import SimpleDocTemplate, Image, Spacer, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, db_manager, main_app):
        super().__init__(parent, fg_color="transparent")
        self.db_manager = db_manager
        self.main_app = main_app
        self.product_map = {}
        self.bar_metadata = []
        self.pie_metadata = []
        self.selected_pid = None
        self.hovered_bar_info = None
        self.hovered_wedge_index = -1

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=0, sticky="nsew")
        self.main_panel.grid_rowconfigure(0, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.filter_panel = ctk.CTkFrame(self, width=280)
        self.filter_panel.grid(row=0, column=1, sticky="ns", padx=(10,0), pady=0)
        
        self.tab_view = ctk.CTkTabview(self.main_panel, fg_color="transparent")
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        self.tab_view.add("bar_chart")
        self.tab_view.add("pie_chart")
        self.tab_view._segmented_button.grid_forget()

        ctk.CTkLabel(self.filter_panel, text="Filtros do Dashboard", font=ctk.CTkFont(weight="bold", size=16)).pack(pady=10, padx=10)
        
        # --- NOVO FILTRO DE CALENDÁRIO ---
        date_filter_frame = ctk.CTkFrame(self.filter_panel)
        date_filter_frame.pack(pady=10, padx=10, fill="x")
        
        ctk.CTkLabel(date_filter_frame, text="Filtrar por Data:").pack(anchor="w")
        
        # Data Início
        start_date_frame = ctk.CTkFrame(date_filter_frame, fg_color="transparent")
        start_date_frame.pack(fill="x", pady=(5,0))
        ctk.CTkLabel(start_date_frame, text="Início:", width=50).pack(side="left", padx=5)
        self.start_date_label = ctk.CTkLabel(start_date_frame, text="Nenhuma", width=100, fg_color=("gray80", "gray28"), corner_radius=6)
        self.start_date_label.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(start_date_frame, text="...", width=30, command=lambda: self._open_calendar(self.start_date_label)).pack(side="left", padx=5)

        # Data Fim
        end_date_frame = ctk.CTkFrame(date_filter_frame, fg_color="transparent")
        end_date_frame.pack(fill="x", pady=(5,0))
        ctk.CTkLabel(end_date_frame, text="Fim:", width=50).pack(side="left", padx=5)
        self.end_date_label = ctk.CTkLabel(end_date_frame, text="Nenhuma", width=100, fg_color=("gray80", "gray28"), corner_radius=6)
        self.end_date_label.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(end_date_frame, text="...", width=30, command=lambda: self._open_calendar(self.end_date_label)).pack(side="left", padx=5)
        
        date_buttons_frame = ctk.CTkFrame(date_filter_frame, fg_color="transparent")
        date_buttons_frame.pack(fill="x", pady=10)
        
        ctk.CTkButton(date_buttons_frame, text="Filtrar", command=self.update_graph).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(date_buttons_frame, text="Limpar", command=self.clear_date_filter, fg_color="#555").pack(side="left", expand=True, padx=5)

        # --- Outros Filtros ---
        ctk.CTkLabel(self.filter_panel, text="Filtrar por Produto:").pack(anchor="w", padx=10)
        self.product_filter_combo = ctk.CTkComboBox(self.filter_panel, command=self.on_filter_change)
        self.product_filter_combo.pack(pady=(0, 10), padx=10, fill="x")

        ctk.CTkLabel(self.filter_panel, text="Tipo de Gráfico:").pack(anchor="w", padx=10, pady=(10,0))
        self.chart_type_var = ctk.StringVar(value="Colunas")
        self.radio_bar = ctk.CTkRadioButton(self.filter_panel, text="Colunas", variable=self.chart_type_var, value="Colunas", command=self.update_graph)
        self.radio_bar.pack(anchor="w", padx=20, pady=5)
        self.radio_pie = ctk.CTkRadioButton(self.filter_panel, text="Pizza", variable=self.chart_type_var, value="Pizza", command=self.update_graph)
        self.radio_pie.pack(anchor="w", padx=20, pady=(0,10))
        
        ctk.CTkLabel(self.filter_panel, text="Visualizar Métrica:").pack(anchor="w", padx=10, pady=(10,0))
        self.view_mode_var = ctk.StringVar(value="Valor")
        self.radio_valor = ctk.CTkRadioButton(self.filter_panel, text="Valor (R$)", variable=self.view_mode_var, value="Valor", command=self.update_graph)
        self.radio_valor.pack(anchor="w", padx=20, pady=5)
        self.radio_qtd = ctk.CTkRadioButton(self.filter_panel, text="Quantidade", variable=self.view_mode_var, value="Quantidade", command=self.update_graph)
        self.radio_qtd.pack(anchor="w", padx=20, pady=(0,10))
        
        ctk.CTkLabel(self.filter_panel, text="Detalhes do Produto:", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(20, 5), padx=10)
        self.info_panel = ctk.CTkTextbox(self.filter_panel, state="disabled", wrap="word", height=150, font=("Calibri", 14))
        self.info_panel.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.info_panel.tag_config("header", underline=True, spacing1=5)
        self.info_panel.tag_config("profit", foreground="green")
        self.info_panel.tag_config("loss", foreground="red")

        self.fig_bar = Figure(figsize=(8, 4), dpi=100); self.ax_bar = self.fig_bar.add_subplot(111)
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=self.tab_view.tab("bar_chart"))
        self.canvas_bar.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.canvas_bar.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas_bar.mpl_connect("button_press_event", self.on_click)

        self.fig_pie = Figure(figsize=(8, 4), dpi=100); self.ax_pie = self.fig_pie.add_subplot(111)
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=self.tab_view.tab("pie_chart"))
        self.canvas_pie.get_tk_widget().pack(side="top", fill="both", expand=True)
        self.canvas_pie.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas_pie.mpl_connect("button_press_event", self.on_click)
        
        self._populate_product_filter()


    def export_to_pdf(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")], title="Salvar Relatório do Dashboard")
        if not filepath: return
        temp_image_path = "temp_dashboard_graph.png"
        try:
            fig_to_save = self.fig_pie if self.tab_view.get() == "pie_chart" else self.fig_bar
            fig_to_save.savefig(temp_image_path, dpi=300, bbox_inches='tight')
            
            doc = SimpleDocTemplate(filepath)
            story = []; styles = getSampleStyleSheet()
            title = Paragraph("Relatório de Movimentação do Dashboard", styles['h1'])
            story.append(title); story.append(Spacer(1, 0.2 * inch))

            img = Image(temp_image_path)
            img_width, img_height = img.imageWidth, img.imageHeight
            aspect = img_height / float(img_width)
            display_width = 6.5 * inch; display_height = display_width * aspect
            img.drawWidth = display_width; img.drawHeight = display_height
            story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            start_date, end_date = self._get_dates()
            
            if self.tab_view.get() == "pie_chart":
                data = self.db_manager.get_total_sales_by_product()
                if data:
                    table_data = [["Produto", "Valor (R$)", "Percentual"]]
                    total = sum([row[2] for row in data]) or 1
                    for pid, name, val in data:
                        pct = f"{(val / total) * 100:.1f}%"
                        table_data.append([name, f"R$ {val:.2f}", pct])
                    tbl = Table(table_data, colWidths=[3.5 * inch, 1.5 * inch, 1.5 * inch])
                    tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                    ]))
                    story.append(Paragraph("Dados de Vendas por Produto:", styles['h2']))
                    story.append(Spacer(1, 0.1 * inch))
                    story.append(tbl)
            else:
                selected_product_str = self.product_filter_combo.get()
                if selected_product_str == "Todos os Produtos":
                    data = self.db_manager.get_summary_for_all_products(start_date, end_date)
                    if data:
                        table_data = [["Data", "Produto", "Valor Entrada", "Valor Saida", "Qtd Entrada", "Qtd Saida"]]
                        for day, pid, name, ve, vs, qe, qs in data:
                            table_data.append([day, name, f"R$ {ve:.2f}", f"R$ {vs:.2f}", str(qe), str(qs)])
                        tbl = Table(table_data, colWidths=[1.2*inch, 2.5*inch, 1.2*inch, 1.2*inch, 0.8*inch, 0.8*inch])
                        tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                            ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
                        ]))
                        story.append(Paragraph("Resumo de Movimentações por Dia e Produto:", styles['h2']))
                        story.append(Spacer(1, 0.1 * inch))
                        story.append(tbl)
                else:
                    product_id = self.product_map.get(selected_product_str)
                    if product_id:
                        data = self.db_manager.get_summary_for_single_product(product_id, start_date, end_date)
                        table_data = [["Data", "Valor Entrada", "Valor Saida", "Qtd Entrada", "Qtd Saida"]]
                        for day, ve, vs, qe, qs in data:
                            table_data.append([day, f"R$ {ve:.2f}", f"R$ {vs:.2f}", str(qe), str(qs)])
                        tbl = Table(table_data, colWidths=[1.6*inch, 1.5*inch, 1.5*inch, 1.0*inch, 1.0*inch])
                        tbl.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                        ]))
                        story.append(Paragraph(f"Detalhamento de Movimentações - {selected_product_str}", styles['h2']))
                        story.append(Spacer(1, 0.1 * inch))
                        story.append(tbl)

            doc.build(story)
            messagebox.showinfo("Sucesso", f"Relatório salvo com sucesso em:\n{filepath}")
            self.main_app.db_manager.add_notification("Relatório do dashboard foi exportado para PDF.")
            self.main_app.update_notifications_button()
        except Exception as e:
            messagebox.showerror("Erro na Exportação", f"Ocorreu um erro ao gerar o PDF: {e}")
        finally:
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)



    def _open_calendar(self, date_label):
        top = ctk.CTkToplevel(self)
        top.title("Selecione a Data")
        top.geometry("300x280")
        top.transient(self)
        top.grab_set()

        cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
        cal.pack(pady=10, padx=10, fill="both", expand=True)

        def set_date():
            date_label.configure(text=cal.get_date())
            top.destroy()

        confirm_button = ctk.CTkButton(top, text="Confirmar", command=set_date)
        confirm_button.pack(pady=10)

    def clear_date_filter(self):
        self.start_date_label.configure(text="Nenhuma")
        self.end_date_label.configure(text="Nenhuma")
        self.update_graph()

    def _get_dates(self):
        start_date = self.start_date_label.cget("text")
        end_date = self.end_date_label.cget("text")
        return None if start_date == "Nenhuma" else start_date, None if end_date == "Nenhuma" else end_date

    def on_filter_change(self, choice):
        if choice == "Todos os Produtos":
            self.radio_pie.configure(state="normal")
        else:
            self.chart_type_var.set("Colunas")
            self.radio_pie.configure(state="disabled")
        self.update_graph()

    def update_graph(self, event=None):
        start_date, end_date = self._get_dates()

        self.bar_metadata.clear(); self.pie_metadata.clear()
        self.selected_pid = None; self.hovered_bar_info = None; self.hovered_wedge_index = -1
        self.update_info_panel(None)
        
        chart_type = self.chart_type_var.get()
        if chart_type == "Pizza" and self.product_filter_combo.get() == "Todos os Produtos":
            self.tab_view.set("pie_chart")
            self.ax_pie.clear()
            self._plot_pie_chart()
            self.update_theme(self.fig_pie, self.ax_pie)
            self.canvas_pie.draw()
        else:
            self.tab_view.set("bar_chart")
            self.ax_bar.clear()
            selected_product_str = self.product_filter_combo.get()
            if selected_product_str == "Todos os Produtos":
                self._plot_all_products_comparison(start_date, end_date)
            else:
                product_id = self.product_map.get(selected_product_str)
                if product_id:
                    self._plot_single_product(product_id, start_date, end_date)
            self.update_theme(self.fig_bar, self.ax_bar)
            self.canvas_bar.draw()
            
    def _plot_single_product(self, product_id, start_date=None, end_date=None):
        data = self.db_manager.get_summary_for_single_product(product_id, start_date, end_date)
        view_mode = self.view_mode_var.get()
        if not data:
            self.ax_bar.text(0.5, 0.5, 'Sem movimentações para este produto/período.', ha='center', va='center', transform=self.ax_bar.transAxes)
            return
        product_data = self.db_manager.get_product_by_id(product_id)
        product_name = product_data[1]
        days = [row[0] for row in data]
        if view_mode == "Valor":
            entradas = [row[1] for row in data]; saidas = [row[2] for row in data]
            self.ax_bar.set_ylabel("Valor Movimentado (R$)"); self.ax_bar.set_title(f"Movimentação Financeira - {product_name}")
        else:
            entradas = [row[3] for row in data]; saidas = [row[4] for row in data]
            self.ax_bar.set_ylabel("Quantidade Movimentada"); self.ax_bar.set_title(f"Movimentação de Estoque - {product_name}")
        x = np.arange(len(days)); width = 0.35
        bars_e = self.ax_bar.bar(x - width/2, entradas, width, label='Compras (Entrada)', color='#d9534f')
        bars_s = self.ax_bar.bar(x + width/2, saidas, width, label='Vendas (Saída)', color='#5cb85c')
        for bar_e, bar_s in zip(bars_e, bars_s):
            self.bar_metadata.append({'bar_e': bar_e, 'bar_s': bar_s, 'pid': product_id, 'name': product_name})
        self.ax_bar.set_xticks(x); self.ax_bar.set_xticklabels(days, rotation=45, ha="right")
        self.ax_bar.legend()
        self.fig_bar.tight_layout()
        self.update_bar_visuals()

    def _plot_all_products_comparison(self, start_date=None, end_date=None):
        data = self.db_manager.get_summary_for_all_products(start_date, end_date)
        view_mode = self.view_mode_var.get()
        if not data:
            self.ax_bar.text(0.5, 0.5, 'Sem movimentações para exibir no período.', ha='center', va='center', transform=self.ax_bar.transAxes)
            return
        data_map = defaultdict(lambda: defaultdict(lambda: {'valor_e': 0, 'valor_s': 0, 'qtd_e': 0, 'qtd_s': 0}))
        product_names = {}; all_days = set()
        for day, pid, name, ve, vs, qe, qs in data:
            data_map[day][pid] = {'valor_e': ve, 'valor_s': vs, 'qtd_e': qe, 'qtd_s': qs}
            product_names[pid] = name; all_days.add(day)
        days = sorted(list(all_days)); product_ids = sorted(list(product_names.keys())); num_products = len(product_ids)
        x = np.arange(len(days)); bar_width = 0.8 / (num_products * 2 if num_products > 0 else 1)
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
            bars_e = self.ax_bar.bar(pos_entrada, entradas, width=bar_width, color='#d9534f')
            bars_s = self.ax_bar.bar(pos_saida, saidas, width=bar_width, color='#5cb85c')
            for idx, (bar_e, bar_s) in enumerate(zip(bars_e, bars_s)):
                self.bar_metadata.append({'bar_e': bar_e, 'bar_s': bar_s, 'pid': pid, 'name': product_names[pid], 'day': days[idx]})

        if view_mode == "Valor":
            self.ax_bar.set_ylabel("Valor Movimentado (R$)"); self.ax_bar.set_title("Comparativo de Movimentação Financeira por Produto")
        else:
            self.ax_bar.set_ylabel("Quantidade Movimentada"); self.ax_bar.set_title("Comparativo de Movimentação de Estoque por Produto")
        self.ax_bar.set_xticks(x); self.ax_bar.set_xticklabels(days, rotation=30, ha="right")
        self.ax_bar.tick_params(axis='x', which='major', pad=20)
        if minor_tick_positions:
            self.ax_bar.set_xticks(minor_tick_positions, minor=True)
            self.ax_bar.set_xticklabels(minor_tick_labels, minor=True, rotation=0, ha='center', fontsize=9)
            for label in self.ax_bar.get_xticklabels(minor=True):
                label.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground='white')])
        self.ax_bar.tick_params(axis='x', which='minor', length=0)
        self.fig_bar.tight_layout()
        self.update_bar_visuals()

    def on_double_click(self, event):
        print("--- DEBUG: Double-click detectado! ---") # LINHA DE DEBUG
        if self.tab_view.get() == "pie_chart":
            if self.hovered_wedge_index != -1:
                info = self.pie_metadata[self.hovered_wedge_index]
                print(f"--- DEBUG: Abrindo histórico (pizza) para: {info['name']} ---") # LINHA DE DEBUG
                self.main_app.show_history_window(info['pid'], info['name'], "saida")
            return

        if self.hovered_bar_info:
            pid = self.hovered_bar_info['pid']
            name = self.hovered_bar_info['name']
            bar_e = self.hovered_bar_info['bar_e']
            bar_s = self.hovered_bar_info['bar_s']
            
            contains_e, _ = bar_e.contains(event)
            contains_s, _ = bar_s.contains(event)
            
            if contains_e:
                print(f"--- DEBUG: Abrindo histórico (barra ENTRADA) para: {name} ---") # LINHA DE DEBUG
                self.main_app.show_history_window(pid, name, "entrada")
            elif contains_s:
                print(f"--- DEBUG: Abrindo histórico (barra SAÍDA) para: {name} ---") # LINHA DE DEBUG
                self.main_app.show_history_window(pid, name, "saida")

    # --- O RESTO DO CÓDIGO PERMANECE O MESMO ---

    def _populate_product_filter(self):
        products = self.db_manager.get_all_products()
        self.product_map = {f"{p[0]} - {p[1]}": p[0] for p in products}
        product_list = ["Todos os Produtos"] + list(self.product_map.keys())
        self.product_filter_combo.configure(values=product_list)
        self.product_filter_combo.set("Todos os Produtos")

    def on_hover(self, event):
        if self.selected_pid: return
        
        if self.tab_view.get() == "pie_chart":
            found_wedge_index = -1
            if event.inaxes == self.ax_pie:
                for i, wedge_info in enumerate(self.pie_metadata):
                    if wedge_info['wedge'].contains_point([event.x, event.y]):
                        found_wedge_index = i
                        break
            if found_wedge_index != self.hovered_wedge_index:
                self.hovered_wedge_index = found_wedge_index
                self.update_pie_visuals()
                self.update_info_panel(self.pie_metadata[found_wedge_index] if found_wedge_index != -1 else None)
                self.canvas_pie.draw_idle()
            return

        found_bar = None
        if event.inaxes == self.ax_bar:
            for bar_info in self.bar_metadata:
                contains, _ = bar_info['bar_e'].contains(event)
                if not contains: contains, _ = bar_info['bar_s'].contains(event)
                if contains: found_bar = bar_info; break
        if found_bar != self.hovered_bar_info:
            self.hovered_bar_info = found_bar
            self.update_bar_visuals()
            self.update_info_panel(found_bar)
            self.canvas_bar.draw_idle()

    def on_click(self, event):
        if event.dblclick:
            self.on_double_click(event)
            return

        if self.tab_view.get() == "pie_chart":
            clicked_wedge_index = -1
            if event.inaxes == self.ax_pie:
                for i, wedge_info in enumerate(self.pie_metadata):
                    if wedge_info['wedge'].contains_point([event.x, event.y]):
                        clicked_wedge_index = i
                        break
            if clicked_wedge_index != -1:
                clicked_pid = self.pie_metadata[clicked_wedge_index]['pid']
                self.selected_pid = clicked_pid if self.selected_pid != clicked_pid else None
            else:
                self.selected_pid = None
            
            self._plot_pie_chart()
            self.update_pie_visuals()
            self.update_info_panel(self.pie_metadata[clicked_wedge_index] if self.selected_pid else None)
            self.canvas_pie.draw_idle()
            return

        clicked_bar_info = None
        if event.inaxes == self.ax_bar:
            for bar_info in self.bar_metadata:
                contains, _ = bar_info['bar_e'].contains(event)
                if not contains: contains, _ = bar_info['bar_s'].contains(event)
                if contains: clicked_bar_info = bar_info; break
        if clicked_bar_info and self.selected_pid == clicked_bar_info['pid']:
            self.selected_pid = None
        else:
            self.selected_pid = clicked_bar_info['pid'] if clicked_bar_info else None
        self.update_bar_visuals()
        self.update_info_panel(clicked_bar_info or self.hovered_bar_info)
        self.canvas_bar.draw_idle()

    def update_bar_visuals(self):
        for bar_info in self.bar_metadata:
            pid = bar_info['pid']; bar_e = bar_info['bar_e']; bar_s = bar_info['bar_s']
            is_selected = (self.selected_pid == pid)
            is_hovered = (self.hovered_bar_info and self.hovered_bar_info['pid'] == pid)
            alpha = 1.0 if is_selected or is_hovered else 0.6
            edgecolor = 'yellow' if is_selected else None
            linewidth = 1.5 if is_selected else 0
            bar_e.set_alpha(alpha); bar_s.set_alpha(alpha)
            bar_e.set_edgecolor(edgecolor); bar_e.set_linewidth(linewidth)
            bar_s.set_edgecolor(edgecolor); bar_s.set_linewidth(linewidth)

    def update_pie_visuals(self):
        for i, wedge_info in enumerate(self.pie_metadata):
            wedge = wedge_info['wedge']
            is_selected = (self.selected_pid == wedge_info['pid'])
            is_hovered = (i == self.hovered_wedge_index)
            
            alpha = 1.0 if is_selected or is_hovered else 0.7
            edgecolor = 'yellow' if is_selected else None
            linewidth = 1.5 if is_selected else 0
            
            wedge.set_alpha(alpha)
            wedge.set_edgecolor(edgecolor)
            wedge.set_linewidth(linewidth)

    def update_info_panel(self, item_info):
        self.info_panel.configure(state="normal"); self.info_panel.delete("1.0", "end")
        if not item_info:
            self.info_panel.insert("1.0", "Passe o mouse sobre um item para ver os detalhes.")
            self.info_panel.configure(state="disabled"); return
        pid = item_info['pid']
        financials = self.db_manager.get_product_financials(pid)
        product_data = self.db_manager.get_product_by_id(pid)
        if not financials or not product_data:
            self.info_panel.insert("1.0", "Não há dados financeiros para este produto.")
            self.info_panel.configure(state="disabled"); return
            
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

    def _plot_pie_chart(self):
        self.ax_pie.clear()
        self.pie_metadata.clear()
        data = self.db_manager.get_total_sales_by_product()
        if not data:
            self.ax_pie.text(0.5, 0.5, 'Sem dados de vendas para exibir.', ha='center', va='center', transform=self.ax_pie.transAxes); return
        
        pids = [row[0] for row in data]
        labels = [row[1] for row in data]
        sizes = [row[2] for row in data]
        
        explode = [0.1 if pid == self.selected_pid else 0 for pid in pids]

        wedges, texts, autotexts = self.ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%',
                                                   shadow=False, startangle=90, pctdistance=0.85,
                                                   explode=explode)
        
        for i, wedge in enumerate(wedges):
            self.pie_metadata.append({'wedge': wedge, 'pid': pids[i], 'name': labels[i]})

        self.ax_pie.set_title("Composição de Vendas por Produto")
        plt.setp(autotexts, size=8, weight="bold", path_effects=[path_effects.withStroke(linewidth=1.5, foreground='white')])
        self.ax_pie.axis('equal')
        self.fig_pie.tight_layout()
        self.update_pie_visuals()

    def update_theme(self, fig=None, ax=None):
        if fig is None or ax is None:
            if self.tab_view.get() == "pie_chart":
                fig, ax = self.fig_pie, self.ax_pie
            else:
                fig, ax = self.fig_bar, self.ax_bar
        
        bg_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color_name = self._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"])
        bg_rgb = self.winfo_rgb(bg_color_name); text_rgb = self.winfo_rgb(text_color_name)
        bg_color_mpl = (bg_rgb[0] / 65535.0, bg_rgb[1] / 65535.0, bg_rgb[2] / 65535.0)
        text_color_mpl = (text_rgb[0] / 65535.0, text_rgb[1] / 65535.0, text_rgb[2] / 65535.0)
        fig.patch.set_facecolor(bg_color_mpl); ax.set_facecolor(bg_color_mpl)
        ax.tick_params(colors=text_color_mpl)
        ax.spines['bottom'].set_color(text_color_mpl); ax.spines['top'].set_color(text_color_mpl)
        ax.spines['left'].set_color(text_color_mpl); ax.spines['right'].set_color(text_color_mpl)
        ax.yaxis.label.set_color(text_color_mpl); ax.title.set_color(text_color_mpl)
        legend = ax.get_legend()
        if legend:
            legend.get_frame().set_facecolor(bg_color_mpl)
            for text in legend.get_texts():
                text.set_color(text_color_mpl)
        border_color = 'white' if ctk.get_appearance_mode() == "Dark" else 'black'
        for label in ax.get_xticklabels(minor=True):
            label.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground=border_color)])
        if hasattr(ax, 'texts'):
            for autotext in ax.texts:
                if '%' in autotext.get_text():
                    autotext.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground=border_color)])
        
        if self.tab_view.get() == "pie_chart":
            self.canvas_pie.draw()
        else:
            self.canvas_bar.draw()
