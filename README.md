# 🎓 Sistema de Gerenciamento Escolar

Sistema completo e intuitivo para gerenciamento de dados escolares, incluindo alunos, professores e colaboradores.

## ✨ Funcionalidades

### 📊 Dashboard
- Visualização de estatísticas gerais
- Total de alunos, professores e colaboradores
- Integração com banco de dados em tempo real

### 👥 Gerenciamento de Alunos
- Criar, editar, visualizar e deletar alunos
- Campos: nome, matrícula, email, série, turma, data de nascimento, gênero, responsável
- Busca e filtros por nome, matrícula ou série
- Status do aluno (ativo/inativo)

### 👨‍🏫 Gerenciamento de Professores
- Criar, editar, visualizar e deletar professores
- Campos: nome, CPF, email, especialidade, disciplinas, salário
- Registro de data de admissão
- Busca por nome, especialidade ou disciplina
- Status (ativo/inativo)

### 👷 Gerenciamento de Colaboradores
- Criar, editar, visualizar e deletar colaboradores
- Campos: nome, CPF, email, cargo, departamento, salário
- Registro de data de admissão
- Busca por nome, cargo ou departamento
- Status (ativo/inativo)

### 🔐 Autenticação
- Login seguro para administradores
- Gerenciamento de sessões
- Logout automático

## 🛠 Tecnologias Utilizadas

- **Backend**: Python 3.8+ com Flask
- **Banco de Dados**: SQLite (sem configurações externas)
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **API**: RESTful JSON
- **Estilos**: CSS com variáveis e design responsivo

## 📋 Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## 📦 Instalação

1. **Clone ou baixe o projeto**:
```bash
cd escola_project
```

2. **Instale as dependências**:
```bash
pip install -r requirements.txt
```

3. **Execute o aplicativo**:
```bash
python run_app.py
```

## 🚀 Uso

1. Abra o navegador e acesse: `http://127.0.0.1:5000`

2. **Login padrão**:
   - Email: `admin`
   - Senha: '1234`

3. **No Dashboard**:
   - Use o menu lateral para navegar entre as seções
   - Clique em "+ Novo" para adicionar registros
   - Use os botões de ação para editar ou deletar

## 📁 Estrutura de Arquivos

```
escola_project/
├── gerenciador_escola.py      # Classe principal do banco de dados
├── app.py               # Aplicativo Flask com rotas API
├── requirements.txt            # Dependências Python
├── templates/
│   ├── login.html             # Página de login
│   └── index.html      # Dashboard principal
|                               # Lógica JavaScript
└── escola.db                  # Banco de dados SQLite (criado automaticamente)
```

## 🔐 Segurança

- Passwords armazenadas em texto (importante: implementar hash em produção)
- Validação de entrada no backend
- Proteção contra SQL injection com prepared statements
- Sessões seguras do Flask

## 💾 Banco de Dados

O sistema usa SQLite, que cria automaticamente um arquivo `escola.db` na primeira execução. Não requer configuração de servidor externo.

### Tabelas:
- **usuarios**: Armazena dados de administradores
- **alunos**: Dados dos alunos
- **professores**: Informações dos professores
- **colaboradores**: Dados dos colaboradores

## 📝 Exemplos de Uso

### Adicionar um novo aluno
1. Clique em "Alunos" no menu
2. Clique em "+ Novo Aluno"
3. Preencha os formulários com os dados
4. Clique em "✓ Salvar Aluno"

### Buscar alunos
1. No campo de busca, digite o nome, matrícula ou série
2. Clique em "🔍 Buscar"

### Editar registro
1. Clique no botão "✎ Editar" da linha desejada
2. Modifique os dados
3. Clique em "✓ Salvar"

### Deletar registro
1. Clique no botão "✕ Deletar" da linha desejada
2. Confirme a ação

## 🤝 Contribuindo

Para melhorias e sugestões, entre em contato.

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique se todas as dependências estão instaladas
2. Certifique-se de que a porta 5000 está disponível
3. Limpe o cache do navegador
4. Reinicie a aplicação

## 📄 Licença

Projeto criado para fins educacionais.

## ✅ Changelog

### v1.0.0
- Sistema completo de gerenciamento escolar
- Interface web responsiva
- CRUD completo para alunos, professores e colaboradores
- Dashboard com estatísticas
- Autenticação básica

---

**Desenvolvido com ❤️ para educação**
