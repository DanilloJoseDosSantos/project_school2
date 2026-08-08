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
                    foto_referencia TEXT,
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
                    senha TEXT,
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
                    senha TEXT,
                    funcao TEXT NOT NULL,
                    endereco TEXT NOT NULL,
                    status TEXT DEFAULT 'ativo',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Tabela de Diário de Classe
            conn.execute('''
                CREATE TABLE IF NOT EXISTS diario_entradas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aluno_id INTEGER NOT NULL,
                    professor_id INTEGER NOT NULL,
                    materia TEXT NOT NULL,
                    data_aula TEXT NOT NULL,
                    trimestre INTEGER NOT NULL,
                    presente INTEGER NOT NULL,
                    nota REAL,
                    observacao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (aluno_id) REFERENCES alunos(id),
                    FOREIGN KEY (professor_id) REFERENCES professores(id)
                )
            ''')
            # Tabela de Auditoria
            conn.execute('''
                CREATE TABLE IF NOT EXISTS auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acao TEXT NOT NULL,
                    entidade TEXT NOT NULL,
                    entidade_id INTEGER,
                    usuario TEXT NOT NULL,
                    detalhes TEXT,
                    data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Configurações do sistema
            conn.execute('''
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Eventos de reconhecimento facial (piloto)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reconhecimento_eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    professor_id INTEGER NOT NULL,
                    aluno_id INTEGER NOT NULL,
                    materia TEXT NOT NULL,
                    data_aula TEXT NOT NULL,
                    total_capturas INTEGER NOT NULL,
                    total_matches INTEGER NOT NULL,
                    score_medio REAL NOT NULL,
                    limiar_utilizado REAL NOT NULL,
                    sugestao_presenca INTEGER NOT NULL,
                    validado_presenca INTEGER,
                    acertou INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (professor_id) REFERENCES professores(id),
                    FOREIGN KEY (aluno_id) REFERENCES alunos(id)
                )
            ''')
            conn.commit()
            self._garantir_colaborador_senha_coluna(conn)
            self._garantir_aluno_foto_referencia_coluna(conn)
            self._garantir_configuracao_padrao(conn)
            conn.commit()

    def _garantir_colaborador_senha_coluna(self, conn):
        cursor = conn.execute("PRAGMA table_info(colaboradores)")
        colunas = [row['name'] for row in cursor.fetchall()]
        if 'senha' not in colunas:
            conn.execute('ALTER TABLE colaboradores ADD COLUMN senha TEXT')

    def _garantir_aluno_foto_referencia_coluna(self, conn):
        cursor = conn.execute("PRAGMA table_info(alunos)")
        colunas = [row['name'] for row in cursor.fetchall()]
        if 'foto_referencia' not in colunas:
            conn.execute('ALTER TABLE alunos ADD COLUMN foto_referencia TEXT')

    def _garantir_configuracao_padrao(self, conn):
        conn.execute('''
            INSERT OR IGNORE INTO configuracoes (chave, valor)
            VALUES ('limiar_reconhecimento', '0.20')
        ''')

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
            if tabela == 'alunos':
                cursor = conn.execute("SELECT COUNT(*) FROM alunos WHERE status = 'arquivado'")
            else:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {tabela} WHERE status = 'ativo'")
            return cursor.fetchone()[0]

    def buscar_registros(self, tabela, termo=""):
        with self.conectar() as conn:
            where_status = "status = 'arquivado'" if tabela == 'alunos' else "status = 'ativo'"
            if termo:
                query = f"SELECT * FROM {tabela} WHERE ({where_status}) AND (nome LIKE ? OR email LIKE ?) ORDER BY id DESC"
                return [dict(row) for row in conn.execute(query, (f"%{termo}%", f"%{termo}%"))]
            return [dict(row) for row in conn.execute(f"SELECT * FROM {tabela} WHERE {where_status} ORDER BY id DESC").fetchall()]

    def buscar_registros_com_inativos(self, tabela):
        with self.conectar() as conn:
            return [dict(row) for row in conn.execute(f"SELECT * FROM {tabela} ORDER BY id DESC").fetchall()]

    def buscar_por_id(self, tabela, registro_id):
        with self.conectar() as conn:
            cursor = conn.execute(f"SELECT * FROM {tabela} WHERE id = ?", (registro_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def autenticar_professor(self, usuario, senha):
        with self.conectar() as conn:
            cursor = conn.execute('''
                SELECT * FROM professores
                WHERE (email = ? OR cpf = ? OR nome = ?) AND senha = ?
            ''', (usuario, usuario, usuario, senha))
            row = cursor.fetchone()
            return dict(row) if row else None

    def salvar_diario_entradas(self, professor_id, materia, registros):
        with self.conectar() as conn:
            for registro in registros:
                conn.execute('''
                    DELETE FROM diario_entradas
                    WHERE professor_id = ? AND aluno_id = ? AND materia = ? AND data_aula = ?
                ''', (
                    professor_id,
                    registro['aluno_id'],
                    materia,
                    registro['data_aula']
                ))
                conn.execute('''
                    INSERT INTO diario_entradas (aluno_id, professor_id, materia, data_aula, trimestre, presente, nota, observacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    registro['aluno_id'],
                    professor_id,
                    materia,
                    registro['data_aula'],
                    registro['trimestre'],
                    registro['presente'],
                    registro['nota'],
                    registro.get('observacao')
                ))
            conn.commit()

    def registrar_auditoria(self, acao, entidade, entidade_id, usuario, detalhes=""):
        with self.conectar() as conn:
            conn.execute('''
                INSERT INTO auditoria (acao, entidade, entidade_id, usuario, detalhes)
                VALUES (?, ?, ?, ?, ?)
            ''', (acao, entidade, entidade_id, usuario, detalhes))
            conn.commit()

    def buscar_logs_auditoria(self):
        with self.conectar() as conn:
            cursor = conn.execute('''
                SELECT * FROM auditoria
                ORDER BY data_evento DESC, id DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]

    def buscar_config(self, chave, valor_padrao=None):
        with self.conectar() as conn:
            cursor = conn.execute('SELECT valor FROM configuracoes WHERE chave = ?', (chave,))
            row = cursor.fetchone()
            return row['valor'] if row else valor_padrao

    def buscar_config_float(self, chave, valor_padrao):
        valor = self.buscar_config(chave, str(valor_padrao))
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(valor_padrao)

    def salvar_config(self, chave, valor):
        with self.conectar() as conn:
            conn.execute('''
                INSERT INTO configuracoes (chave, valor, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor, updated_at = CURRENT_TIMESTAMP
            ''', (chave, str(valor)))
            conn.commit()

    def registrar_evento_reconhecimento(self, professor_id, aluno_id, materia, data_aula, total_capturas, total_matches, score_medio, limiar_utilizado, sugestao_presenca):
        with self.conectar() as conn:
            cursor = conn.execute('''
                INSERT INTO reconhecimento_eventos (
                    professor_id, aluno_id, materia, data_aula,
                    total_capturas, total_matches, score_medio,
                    limiar_utilizado, sugestao_presenca
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                professor_id,
                aluno_id,
                materia,
                data_aula,
                total_capturas,
                total_matches,
                score_medio,
                limiar_utilizado,
                sugestao_presenca
            ))
            conn.commit()
            return cursor.lastrowid

    def atualizar_validacao_evento_reconhecimento(self, professor_id, aluno_id, materia, data_aula, presenca_validada):
        with self.conectar() as conn:
            conn.execute('''
                UPDATE reconhecimento_eventos
                SET validado_presenca = ?,
                    acertou = CASE WHEN sugestao_presenca = ? THEN 1 ELSE 0 END
                WHERE id = (
                    SELECT id
                    FROM reconhecimento_eventos
                    WHERE professor_id = ?
                      AND aluno_id = ?
                      AND materia = ?
                      AND data_aula = ?
                      AND validado_presenca IS NULL
                    ORDER BY id DESC
                    LIMIT 1
                )
            ''', (
                presenca_validada,
                presenca_validada,
                professor_id,
                aluno_id,
                materia,
                data_aula
            ))
            conn.commit()

    def buscar_relatorio_reconhecimento(self):
        with self.conectar() as conn:
            cursor = conn.execute('''
                SELECT
                    re.data_aula,
                    re.materia,
                    p.nome AS professor_nome,
                    COUNT(re.id) AS total_tentativas,
                    SUM(CASE WHEN re.validado_presenca IS NOT NULL THEN 1 ELSE 0 END) AS total_validadas,
                    SUM(CASE WHEN re.acertou = 1 THEN 1 ELSE 0 END) AS total_acertos,
                    AVG(re.score_medio) AS score_medio_geral,
                    AVG(re.total_capturas) AS media_capturas,
                    AVG(re.limiar_utilizado) AS limiar_medio
                FROM reconhecimento_eventos re
                INNER JOIN professores p ON p.id = re.professor_id
                GROUP BY re.data_aula, re.materia, p.nome
                ORDER BY re.data_aula DESC, re.materia ASC
            ''')

            resultados = []
            for row in cursor.fetchall():
                total_validadas = row['total_validadas'] or 0
                total_acertos = row['total_acertos'] or 0
                taxa = round((total_acertos / total_validadas) * 100, 2) if total_validadas else 0.0
                resultados.append({
                    'data_aula': row['data_aula'],
                    'materia': row['materia'],
                    'professor_nome': row['professor_nome'],
                    'total_tentativas': row['total_tentativas'] or 0,
                    'total_validadas': total_validadas,
                    'total_acertos': total_acertos,
                    'taxa_acerto_percentual': taxa,
                    'score_medio_geral': round(row['score_medio_geral'] or 0.0, 4),
                    'media_capturas': round(row['media_capturas'] or 0.0, 2),
                    'limiar_medio': round(row['limiar_medio'] or 0.0, 4)
                })
            return resultados

    def buscar_resumo_diario(self, professor_id, materia, trimestre):
        with self.conectar() as conn:
            cursor = conn.execute('''
                SELECT a.id as aluno_id,
                       a.matricula,
                       a.nome,
                       AVG(de.nota) as media,
                       SUM(de.presente) as presencas,
                       COUNT(de.id) as total_chamadas
                FROM alunos a
                LEFT JOIN diario_entradas de
                  ON a.id = de.aluno_id
                  AND de.professor_id = ?
                  AND de.materia = ?
                  AND de.trimestre = ?
                GROUP BY a.id
                ORDER BY a.nome
            ''', (professor_id, materia, trimestre))
            resultados = []
            for row in cursor.fetchall():
                media = row['media'] if row['media'] is not None else 0.0
                total = row['total_chamadas'] or 0
                presencas = row['presencas'] or 0
                presenca_percentual = round((presencas / total) * 100, 1) if total > 0 else 0.0
                apto = (media >= 70 and presenca_percentual >= 75) if total > 0 else None
                resultados.append({
                    'aluno_id': row['aluno_id'],
                    'matricula': row['matricula'],
                    'nome': row['nome'],
                    'media': round(media, 2),
                    'presenca_percentual': presenca_percentual,
                    'total_chamadas': total,
                    'apto': apto
                })
            return resultados

    def buscar_lancamentos_diario(self, professor_id, materia, data_aula):
        with self.conectar() as conn:
            cursor = conn.execute('''
                SELECT aluno_id, presente, nota
                FROM diario_entradas
                WHERE professor_id = ?
                  AND materia = ?
                  AND data_aula = ?
            ''', (professor_id, materia, data_aula))

            return {
                row['aluno_id']: {
                    'presente': int(row['presente']) == 1,
                    'nota': row['nota']
                }
                for row in cursor.fetchall()
            }

    def inserir_aluno(self, dados):
        if dados.get('cpf') and self.cpf_existe('alunos', dados.get('cpf')):
            raise ValueError("Este CPF já está cadastrado para outro aluno.")
        with self.conectar() as conn:
            cursor = conn.execute('''
                INSERT INTO alunos (nome, matricula, email, serie, turma, data_nascimento, cpf, responsavel, responsavel_cpf, responsavel_telefone, foto_referencia, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'arquivado')
            ''', (
                dados.get('nome'), self.gerar_matricula('aluno'), dados.get('email'),
                dados.get('serie'), dados.get('turma'), dados.get('data_nascimento'),
                dados.get('cpf'), dados.get('responsavel_nome'), dados.get('responsavel_cpf'),
                dados.get('responsavel_telefone'), dados.get('foto_referencia')
            ))
            conn.commit()
            return cursor.lastrowid

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

    def atualizar_foto_referencia_aluno(self, id_aluno, caminho_foto):
        with self.conectar() as conn:
            conn.execute('UPDATE alunos SET foto_referencia = ? WHERE id = ?', (caminho_foto, id_aluno))
            conn.commit()

    def inserir_professor(self, dados):
        if self.cpf_existe('professores', dados.get('cpf')):
            raise ValueError("Este CPF já pertence a outro professor.")
        senha = dados.get('senha') or dados.get('cpf')
        with self.conectar() as conn:
            cursor = conn.execute('''
                INSERT INTO professores (nome, cpf, email, senha, especialidade, disciplinas, salario, endereco)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados.get('nome'), 
                dados.get('cpf'), 
                dados.get('email'), 
                senha,
                dados.get('especialidade'), 
                dados.get('disciplinas'), 
                dados.get('salario'), 
                dados.get('endereco')
            ))
            conn.commit()
            return cursor.lastrowid

    def atualizar_professor(self, id_professor, dados):
        if self.cpf_existe('professores', dados.get('cpf'), id_professor):
            raise ValueError("Este CPF já pertence a outro professor.")
        senha = dados.get('senha')
        with self.conectar() as conn:
            if senha:
                conn.execute('''
                    UPDATE professores 
                    SET nome = ?, cpf = ?, email = ?, senha = ?, especialidade = ?, disciplinas = ?, salario = ?, endereco = ?
                    WHERE id = ?
                ''', (
                    dados.get('nome'), 
                    dados.get('cpf'), 
                    dados.get('email'), 
                    senha,
                    dados.get('especialidade'), 
                    dados.get('disciplinas'), 
                    dados.get('salario'), 
                    dados.get('endereco'),
                    id_professor
                ))
            else:
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

    def excluir_aluno(self, id_aluno):
        with self.conectar() as conn:
            conn.execute("UPDATE alunos SET status = 'inativo' WHERE id = ?", (id_aluno,))
            conn.commit()

    def excluir_professor(self, id_professor):
        with self.conectar() as conn:
            conn.execute("UPDATE professores SET status = 'inativo' WHERE id = ?", (id_professor,))
            conn.commit()

    def excluir_colaborador(self, id_colab):
        with self.conectar() as conn:
            conn.execute("UPDATE colaboradores SET status = 'inativo' WHERE id = ?", (id_colab,))
            conn.commit()

    def inserir_colaborador(self, dados):
        if self.cpf_existe('colaboradores', dados.get('cpf')):
            raise ValueError("Este CPF já está cadastrado para outro colaborador.")
        with self.conectar() as conn:
            cursor = conn.execute('''
                INSERT INTO colaboradores (nome, cpf, email, funcao, endereco)
                VALUES (?, ?, ?, ?, ?)
            ''', (dados.get('nome'), dados.get('cpf'), dados.get('email'), dados.get('funcao'), dados.get('endereco')))
            conn.commit()
            return cursor.lastrowid

    def atualizar_colaborador(self, id_colab, dados):
        if self.cpf_existe('colaboradores', dados.get('cpf'), id_colab):
            raise ValueError("Este CPF já pertence a outro colaborador.")
        with self.conectar() as conn:
            conn.execute('''
                UPDATE colaboradores SET nome = ?, cpf = ?, email = ?, funcao = ?, endereco = ?
                WHERE id = ?
            ''', (dados.get('nome'), dados.get('cpf'), dados.get('email'), dados.get('funcao'), dados.get('endereco'), id_colab))
            conn.commit()