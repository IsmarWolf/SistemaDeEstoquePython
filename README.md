# 🧭 Novo Sistema de Estoque

Este é um sistema de **gerenciamento de estoque** desenvolvido em **Python**, com **interface gráfica** moderna e recursos avançados como leitura de código de barras, geração de relatórios e visualização de gráficos.

---

## ⚙️ Como executar o projeto

### 1. Clone o repositório  
No **VS Code**, abra o **PowerShell** e execute:
```powershell
git clone <URL_DO_REPOSITORIO>
```

### 2. Acesse a pasta do projeto  
```powershell
cd <NOME_DA_PASTA_DO_PROJETO>
```

### 3. Crie o ambiente virtual  
```powershell
python -m venv venv
```

### 4. Ative o ambiente virtual  
```powershell
.venv\Scripts\Activate
```

> 💡 **Dica:** se o PowerShell bloquear a execução, use:  
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```

### 5. Instale as dependências  
```powershell
pip install -r requirements.txt
```

### 6. Execute o aplicativo  
```powershell
python main.py
```

---

## 🧩 Tecnologias Utilizadas

- **Python**
- **PyQt5** — Interface gráfica
- **customtkinter** — Interface alternativa moderna
- **matplotlib** — Gráficos e visualizações
- **reportlab** — Geração de relatórios em PDF
- **opencv-python** — Processamento de imagem
- **pyzbar** — Leitura de código de barras
- **Pillow** — Manipulação de imagens
- **requests** — Integração com APIs externas
- **SQLite** — Banco de dados local

---

## 🧾 Dependências (requirements.txt)
```
PyQt5
customtkinter
matplotlib
reportlab
opencv-python
pyzbar
Pillow
requests
```

---

## 💡 Observação
Pra seguir esse "tutorial" todos os comandos devem ser executados pelo **PowerShell integrado do VS Code**, dentro da pasta do projeto.
