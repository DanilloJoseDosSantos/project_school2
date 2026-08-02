import sqlite3
import re
from datetime import datetime

class GerenciadorEscola:
    def __init__(self, db_name="escola.db"):
        self.db_name = db_name
        self.criar_tabelas()

    def conectar(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def criar_tabelas(self):
        with self.conectar() as conn:
            # Tabela de Alunos
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alunos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    matricula TEXT UNIQUE NOT NULL,
                    email TEXT,
                    serie TEXT NOT NULL,
                    turma TEXT NOT NULL,
                    data_nascimento TEXT,
                    cpf TEXT UNIQUE,
                    responsavel TEXT,
                    responsavel_cpf TEXT,
                    responsavel_telefone TEXT,
                    status TEXT DEFAULT 'arquivado',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de Professores
            conn.execute('''
                CREATE TABLE IF NOT EXISTS professores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    telefone TEXT,
                    especialidade TEXT NOT NULL,
                    disciplinas TEXT,
                    data_nascimento TEXT,
                    genero TEXT,
                    data_admissao TEXT,
                    salario REAL,
                    endereco TEXT,
                    cidade TEXT,
                    estado TEXT,
                    status TEXT DEFAULT 'ativo',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de Colaboradores
            conn.execute('''
                CREATE TABLE IF NOT EXISTS colaboradores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    funcao TEXT NOT NULL,
                    endereco TEXT NOT NULL,
                    status TEXT DEFAULT 'ativo',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    @staticmethod
    def validar_cpf(cpf):
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
            digito = ((soma * 10) % 11) % 10
            if digito != int(cpf[i]):
                return False
        return True

    @staticmethod
    def validar_email(email):
        padrao = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(padrao, email) is not None

    def cpf_existe(self, tabela, cpf, id_atual=None):
        cpf_limpo = re.sub(r'\D', '', cpf)
        with self.conectar() as conn:
            if id_atual:
                cursor = conn.execute(f"SELECT id FROM {tabela} WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ? AND id != ?", (cpf_limpo, id_atual))
            else:
                cursor = conn.execute(f"SELECT id FROM {tabela} WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ?", (cpf_limpo,))
            return cursor.fetchone() is not None

    def gerar_matricula(self, tipo):
        prefixo = {"aluno": "ALU", "professor": "PROF", "colaborador": "COL"}.get(tipo, "REG")
        return f"{prefixo}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def contar_total(self, tabela):
        with self.conectar() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {tabela}")
            return cursor.fetchone()[0]

    def buscar_registros(self, tabela, termo=""):
        with self.conectar() as conn:
            if termo:
                query = f"SELECT * FROM {tabela} WHERE nome LIKE ? OR email LIKE ? ORDER BY id DESC"
                return [dict(row) for row in conn.execute(query, (f"%{termo}%", f"%{termo}%"))]
            return [dict(row) for row in conn.execute(f"SELECT * FROM {tabela} ORDER BY id DESC").fetchall()]

    def buscar_por_id(self, tabela, registro_id):
        with self.conectar() as conn:
            cursor = conn.execute(f"SELECT * FROM {tabela} WHERE id = ?", (registro_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def inserir_aluno(self, dados):
        if dados.get('cpf') and self.cpf_existe('alunos', dados.get('cpf')):
            raise ValueError("Este CPF já está cadastrado para outro aluno.")
        with self.conectar() as conn:
            conn.execute('''
                INSERT INTO alunos (nome, matricula, email, serie, turma, data_nascimento, cpf, responsavel, responsavel_cpf, responsavel_telefone, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'arquivado')
            ''', (
                dados.get('nome'), self.gerar_matricula('aluno'), dados.get('email'),
                dados.get('serie'), dados.get('turma'), dados.get('data_nascimento'),
                dados.get('cpf'), dados.get('responsavel_nome'), dados.get('responsavel_cpf'),
                dados.get('responsavel_telefone')
            ))
            conn.commit()

    def atualizar_aluno(self, id_aluno, dados):
        # Valida se o CPF já pertence a outro aluno
        if self.cpf_existe('alunos', dados.get('cpf'), id_aluno):
            raise ValueError("Este CPF já pertence a outro aluno.")
            
        with self.conectar() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE alunos 
                SET nome = ?, cpf = ?, data_nascimento = ?, serie = ?, turma = ?, email = ?, responsavel = ?, responsavel_cpf = ?, responsavel_telefone = ?
                WHERE id = ?
            ''', (
                dados.get('nome'), 
                dados.get('cpf'), 
                dados.get('data_nascimento'), 
                dados.get('serie'), 
                dados.get('turma'), 
                dados.get('email'), 
                dados.get('responsavel_nome'),      # Ajustado para bater com name="responsavel_nome" do HTML
                dados.get('responsavel_cpf'),       # Ajustado para bater com name="responsavel_cpf" do HTML
                dados.get('responsavel_telefone'),  # Ajustado para bater com name="responsavel_telefone" do HTML
                id_aluno
            ))
            conn.commit()

    def inserir_professor(self, dados):
        if self.cpf_existe('professores', dados.get('cpf')):
            raise ValueError("Este CPF já pertence a outro professor.")
        with self.conectar() as conn:
            conn.execute('''
                INSERT INTO professores (nome, cpf, email, especialidade, disciplinas, salario, endereco)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados.get('nome'), 
                dados.get('cpf'), 
                dados.get('email'), 
                dados.get('especialidade'), 
                dados.get('disciplinas'), 
                dados.get('salario'), 
                dados.get('endereco')
            ))
            conn.commit()

    def atualizar_professor(self, id_professor, dados):
        if self.cpf_existe('professores', dados.get('cpf'), id_professor):
            raise ValueError("Este CPF já pertence a outro professor.")
        with self.conectar() as conn:
            conn.execute('''
                UPDATE professores 
                SET nome = ?, cpf = ?, email = ?, especialidade = ?, disciplinas = ?, salario = ?, endereco = ?
                WHERE id = ?
            ''', (
                dados.get('nome'), 
                dados.get('cpf'), 
                dados.get('email'), 
                dados.get('especialidade'), 
                dados.get('disciplinas'), 
                dados.get('salario'), 
                dados.get('endereco'),
                id_professor
            ))
            conn.commit()

    def inserir_colaborador(self, dados):
        if self.cpf_existe('colaboradores', dados.get('cpf')):
            raise ValueError("Este CPF já está cadastrado para outro colaborador.")
        with self.conectar() as conn:
            conn.execute('''
                INSERT INTO colaboradores (nome, cpf, email, funcao, endereco)
                VALUES (?, ?, ?, ?, ?)
            ''', (dados.get('nome'), dados.get('cpf'), dados.get('email'), dados.get('funcao'), dados.get('endereco')))
            conn.commit()

    def atualizar_colaborador(self, id_colab, dados):
        if self.cpf_existe('colaboradores', dados.get('cpf'), id_colab):
            raise ValueError("Este CPF já pertence a outro colaborador.")
        with self.conectar() as conn:
            conn.execute('''
                UPDATE colaboradores SET nome = ?, cpf = ?, email = ?, funcao = ?, endereco = ?
                WHERE id = ?
            ''', (dados.get('nome'), dados.get('cpf'), dados.get('email'), dados.get('funcao'), dados.get('endereco'), id_colab))
            conn.commit()