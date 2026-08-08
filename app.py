from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from gerenciador_escola import GerenciadorEscola

try:
    from reconhecimento_facial import comparar_rosto_por_orb
    RECONHECIMENTO_DISPONIVEL = True
except Exception:
    comparar_rosto_por_orb = None
    RECONHECIMENTO_DISPONIVEL = False

app = Flask(__name__)
app.secret_key = "chave_secreta_sistema_escolar"
db = GerenciadorEscola()
ADMIN_USER = 'admin'
ADMIN_PASSWORD = '1234'
PASTA_FOTOS_REFERENCIA = Path('static') / 'fotos_referencia'
PASTA_FOTOS_REFERENCIA.mkdir(parents=True, exist_ok=True)

def usuario_logado():
    return session.get('usuario_logado', False)

def professor_logado():
    return session.get('professor_logado', False)

def usuario_atual_para_auditoria():
    if professor_logado():
        return f"Professor: {session.get('professor_nome', 'Desconhecido')}"
    if usuario_logado():
        return f"Administrador: {session.get('usuario_nome', 'Desconhecido')}"
    return "Sistema"

def definir_mensagem(tipo, texto):
    session['mensagem_tipo'] = tipo
    session['mensagem_texto'] = texto

def salvar_foto_referencia_aluno(arquivo, aluno_id):
    if not arquivo or not arquivo.filename:
        return None

    extensao = Path(secure_filename(arquivo.filename)).suffix.lower()
    if extensao not in ['.jpg', '.jpeg', '.png', '.webp']:
        raise ValueError('Formato de foto inválido. Use JPG, PNG ou WEBP.')

    destino = PASTA_FOTOS_REFERENCIA / f"aluno_{aluno_id}{extensao}"
    arquivo.save(destino)
    return str(destino).replace('\\', '/')

@app.route('/')
def raiz():
    if professor_logado():
        return redirect(url_for('diario'))
    if usuario_logado():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        papel = request.form.get('papel')
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        if papel == 'admin' and usuario == ADMIN_USER and senha == ADMIN_PASSWORD:
            session.clear()
            session['usuario_logado'] = True
            session['usuario_nome'] = 'Administrador'
            return redirect(url_for('dashboard'))

        if papel == 'docente':
            professor = db.autenticar_professor(usuario, senha)
            if professor:
                session.clear()
                session['professor_logado'] = True
                session['professor_id'] = professor['id']
                session['professor_nome'] = professor['nome']
                return redirect(url_for('diario'))

        return render_template('login.html', erro='Usuário, senha ou tipo de acesso inválidos!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def calcular_trimestre(data):
    month = data.month
    if month <= 3:
        return 1
    if month <= 6:
        return 2
    if month <= 9:
        return 3
    return 4

@app.route('/dashboard')
def dashboard():
    if not usuario_logado():
        return redirect(url_for('login'))

    mensagem = {
        'tipo': session.pop('mensagem_tipo', None),
        'texto': session.pop('mensagem_texto', None)
    }
    
    totais = {
        'alunos': db.contar_total('alunos'),
        'professores': db.contar_total('professores'),
        'colaboradores': db.contar_total('colaboradores')
    }
    
    return render_template(
        'index.html',
        usuario_nome=session.get('usuario_nome', 'Usuário'),
        mensagem=mensagem,
        limiar_reconhecimento=db.buscar_config_float('limiar_reconhecimento', 0.20),
        totais=totais,
        alunos=db.buscar_registros('alunos'),
        professores=db.buscar_registros('professores'),
        colaboradores=db.buscar_registros('colaboradores')
    )

@app.route('/config/reconhecimento', methods=['POST'])
def configurar_reconhecimento():
    if not usuario_logado():
        return redirect(url_for('login'))

    limiar_raw = (request.form.get('limiar_reconhecimento') or '').replace(',', '.')
    try:
        limiar = float(limiar_raw)
    except ValueError:
        definir_mensagem('erro', 'Limiar inválido. Informe um número entre 0.05 e 0.95.')
        return redirect(url_for('dashboard'))

    if limiar < 0.05 or limiar > 0.95:
        definir_mensagem('erro', 'Limiar fora do intervalo permitido (0.05 a 0.95).')
        return redirect(url_for('dashboard'))

    db.salvar_config('limiar_reconhecimento', f'{limiar:.2f}')
    db.registrar_auditoria(
        acao='CONFIG_RECONHECIMENTO',
        entidade='configuracoes',
        entidade_id=None,
        usuario=usuario_atual_para_auditoria(),
        detalhes=f'Limiar atualizado para {limiar:.2f}'
    )
    definir_mensagem('sucesso', f'Limiar de reconhecimento atualizado para {limiar:.2f}.')
    return redirect(url_for('dashboard'))

@app.route('/diario')
def diario():
    if not professor_logado():
        return redirect(url_for('login'))

    mensagem = {
        'tipo': session.pop('mensagem_tipo', None),
        'texto': session.pop('mensagem_texto', None)
    }

    professor_id = session.get('professor_id')
    professor = db.buscar_por_id('professores', professor_id)
    disciplinas = [d.strip() for d in (professor.get('disciplinas') or '').split(',') if d.strip()]
    if not disciplinas:
        disciplinas = [professor.get('especialidade') or 'Geral']

    materia_param = request.args.get('materia')
    materia = materia_param if materia_param in disciplinas else disciplinas[0]

    data_param = request.args.get('data')
    try:
        data_ref = datetime.strptime(data_param, '%Y-%m-%d').date() if data_param else datetime.today().date()
    except ValueError:
        data_ref = datetime.today().date()

    serie_atual = (request.args.get('serie') or '').strip()
    turma_atual = (request.args.get('turma') or '').strip()
    todos_alunos = db.buscar_registros('alunos')
    series_disponiveis = sorted({(a.get('serie') or '').strip() for a in todos_alunos if (a.get('serie') or '').strip()})
    turmas_disponiveis = sorted({(a.get('turma') or '').strip() for a in todos_alunos if (a.get('turma') or '').strip()})
    alunos = todos_alunos
    if serie_atual:
        alunos = [a for a in alunos if (a.get('serie') or '').strip() == serie_atual]
    if turma_atual:
        alunos = [a for a in alunos if (a.get('turma') or '').strip() == turma_atual]

    trimestre = calcular_trimestre(data_ref)
    resumo_por_aluno = {item['aluno_id']: item for item in db.buscar_resumo_diario(professor_id, materia, trimestre)}
    lancamentos_dia = db.buscar_lancamentos_diario(professor_id, materia, data_ref.isoformat())

    return render_template(
        'diario.html',
        professor_nome=session.get('professor_nome'),
        disciplinas=disciplinas,
        materia_atual=materia,
        trimestre=trimestre,
        hoje=data_ref.isoformat(),
        serie_atual=serie_atual,
        series_disponiveis=series_disponiveis,
        turma_atual=turma_atual,
        turmas_disponiveis=turmas_disponiveis,
        limiar_reconhecimento=db.buscar_config_float('limiar_reconhecimento', 0.20),
        mensagem=mensagem,
        alunos=alunos,
        lancamentos_dia=lancamentos_dia,
        resumo_por_aluno=resumo_por_aluno,
        reconhecimento_disponivel=RECONHECIMENTO_DISPONIVEL
    )

@app.route('/diario/visualizacao')
def diario_visualizacao():
    if not usuario_logado():
        return redirect(url_for('login'))

    professores = db.buscar_registros('professores')
    if not professores:
        definir_mensagem('erro', 'Nenhum professor cadastrado para visualização do diário.')
        return redirect(url_for('dashboard'))

    professor_id_raw = request.args.get('professor_id')
    professor_id = int(professor_id_raw) if professor_id_raw and professor_id_raw.isdigit() else professores[0]['id']
    professor = db.buscar_por_id('professores', professor_id)
    if not professor:
        professor = professores[0]
        professor_id = professor['id']

    disciplinas = [d.strip() for d in (professor.get('disciplinas') or '').split(',') if d.strip()]
    if not disciplinas:
        disciplinas = [professor.get('especialidade') or 'Geral']

    materia_param = request.args.get('materia')
    materia = materia_param if materia_param in disciplinas else disciplinas[0]

    data_param = request.args.get('data')
    try:
        data_ref = datetime.strptime(data_param, '%Y-%m-%d').date() if data_param else datetime.today().date()
    except ValueError:
        data_ref = datetime.today().date()

    serie_atual = (request.args.get('serie') or '').strip()
    turma_atual = (request.args.get('turma') or '').strip()
    todos_alunos = db.buscar_registros('alunos')
    series_disponiveis = sorted({(a.get('serie') or '').strip() for a in todos_alunos if (a.get('serie') or '').strip()})
    turmas_disponiveis = sorted({(a.get('turma') or '').strip() for a in todos_alunos if (a.get('turma') or '').strip()})
    alunos = todos_alunos
    if serie_atual:
        alunos = [a for a in alunos if (a.get('serie') or '').strip() == serie_atual]
    if turma_atual:
        alunos = [a for a in alunos if (a.get('turma') or '').strip() == turma_atual]

    trimestre = calcular_trimestre(data_ref)
    resumo_por_aluno = {item['aluno_id']: item for item in db.buscar_resumo_diario(professor_id, materia, trimestre)}
    lancamentos_dia = db.buscar_lancamentos_diario(professor_id, materia, data_ref.isoformat())

    return render_template(
        'diario.html',
        professor_nome=professor.get('nome'),
        disciplinas=disciplinas,
        materia_atual=materia,
        trimestre=trimestre,
        hoje=data_ref.isoformat(),
        serie_atual=serie_atual,
        series_disponiveis=series_disponiveis,
        turma_atual=turma_atual,
        turmas_disponiveis=turmas_disponiveis,
        limiar_reconhecimento=db.buscar_config_float('limiar_reconhecimento', 0.20),
        alunos=alunos,
        lancamentos_dia=lancamentos_dia,
        resumo_por_aluno=resumo_por_aluno,
        modo_visualizacao=True,
        professores=professores,
        professor_id_atual=professor_id,
        reconhecimento_disponivel=RECONHECIMENTO_DISPONIVEL
    )

@app.route('/diario/reconhecimento', methods=['POST'])
def diario_reconhecimento():
    if not professor_logado():
        return jsonify({'ok': False, 'erro': 'Acesso negado.'}), 403

    if not RECONHECIMENTO_DISPONIVEL or comparar_rosto_por_orb is None:
        return jsonify({'ok': False, 'erro': 'Reconhecimento facial indisponível no servidor.'}), 503

    payload_json = request.get_json(silent=True) if request.is_json else None
    aluno_id_raw = (payload_json or {}).get('aluno_id') or request.form.get('aluno_id')
    materia = (payload_json or {}).get('materia') or request.form.get('materia') or 'Geral'
    data_aula = (payload_json or {}).get('data_aula') or request.form.get('data_aula') or datetime.today().date().isoformat()

    capturas = []
    if payload_json and isinstance(payload_json.get('capturas'), list):
        capturas = [item for item in payload_json.get('capturas') if isinstance(item, str) and item.strip()]
    else:
        foto_capturada_data = request.form.get('foto_capturada_data')
        if foto_capturada_data:
            capturas = [foto_capturada_data]

    if not aluno_id_raw or not aluno_id_raw.isdigit():
        return jsonify({'ok': False, 'erro': 'Aluno inválido para reconhecimento.'}), 400

    if not capturas:
        return jsonify({'ok': False, 'erro': 'Nenhuma imagem capturada foi enviada.'}), 400

    aluno_id = int(aluno_id_raw)
    aluno = db.buscar_por_id('alunos', aluno_id)
    if not aluno:
        return jsonify({'ok': False, 'erro': 'Aluno não encontrado.'}), 404

    foto_referencia = aluno.get('foto_referencia')
    if not foto_referencia:
        return jsonify({'ok': False, 'erro': 'Aluno sem foto de referência cadastrada.'}), 400

    limiar = db.buscar_config_float('limiar_reconhecimento', 0.20)

    try:
        resultados = [comparar_rosto_por_orb(foto_referencia, captura, limiar=limiar) for captura in capturas]
    except Exception as erro:
        return jsonify({'ok': False, 'erro': f'Falha no reconhecimento: {erro}'}), 500

    total_capturas = len(resultados)
    total_matches = sum(1 for r in resultados if r.get('match'))
    score_medio = sum(float(r.get('score', 0.0)) for r in resultados) / total_capturas
    sugestao_presenca = 1 if total_matches > (total_capturas / 2) else 0

    professor_id = session.get('professor_id')
    db.registrar_evento_reconhecimento(
        professor_id=professor_id,
        aluno_id=aluno_id,
        materia=materia,
        data_aula=data_aula,
        total_capturas=total_capturas,
        total_matches=total_matches,
        score_medio=score_medio,
        limiar_utilizado=limiar,
        sugestao_presenca=sugestao_presenca
    )

    db.registrar_auditoria(
        acao='RECONHECIMENTO_FACIAL',
        entidade='alunos',
        entidade_id=aluno_id,
        usuario=usuario_atual_para_auditoria(),
        detalhes=f"Aluno: {aluno.get('nome')}, capturas={total_capturas}, matches={total_matches}, score_medio={round(score_medio, 4)}, limiar={limiar}"
    )

    return jsonify({
        'ok': True,
        'aluno_id': aluno_id,
        'aluno_nome': aluno.get('nome'),
        'match': bool(sugestao_presenca),
        'sugestao_presenca': bool(sugestao_presenca),
        'qtd_capturas': total_capturas,
        'qtd_matches': total_matches,
        'score_medio': round(score_medio, 4),
        'limiar': limiar,
        'mensagem': 'Presença sugerida automaticamente.' if sugestao_presenca else 'Presença não sugerida; validar manualmente.'
    })

@app.route('/diario/salvar', methods=['POST'])
def salvar_diario():
    if not professor_logado():
        return redirect(url_for('login'))

    professor_id = session.get('professor_id')
    materia = request.form.get('materia')
    trimestre = int(request.form.get('trimestre') or calcular_trimestre(datetime.today().date()))
    data_aula = request.form.get('data_aula') or datetime.today().date().isoformat()
    serie_atual = (request.form.get('serie') or '').strip()
    turma_atual = (request.form.get('turma') or '').strip()

    professor = db.buscar_por_id('professores', professor_id)
    disciplinas = [d.strip() for d in (professor.get('disciplinas') or '').split(',') if d.strip()]
    if not disciplinas:
        disciplinas = [professor.get('especialidade') or 'Geral']

    if materia not in disciplinas:
        definir_mensagem('erro', 'Matéria inválida para este professor.')
        return redirect(url_for('diario'))

    registros = []
    pendentes_confirmacao = []
    alunos_base = db.buscar_registros('alunos')
    if serie_atual:
        alunos_base = [a for a in alunos_base if (a.get('serie') or '').strip() == serie_atual]
    if turma_atual:
        alunos_base = [a for a in alunos_base if (a.get('turma') or '').strip() == turma_atual]

    for aluno in alunos_base:
        presente = 1 if request.form.get(f"presente_{aluno['id']}") == 'on' else 0
        auto_presenca = 1 if request.form.get(f"auto_presenca_{aluno['id']}") == '1' else 0
        confirmado_presenca = 1 if request.form.get(f"confirmado_presenca_{aluno['id']}") == '1' else 0

        if auto_presenca and presente and not confirmado_presenca:
            pendentes_confirmacao.append(aluno.get('nome'))

        nota_raw = request.form.get(f"nota_{aluno['id']}")
        nota = None
        if nota_raw and nota_raw.strip():
            try:
                nota = float(nota_raw.replace(',', '.'))
            except ValueError:
                nota = None
        registros.append({
            'aluno_id': aluno['id'],
            'presente': presente,
            'nota': nota,
            'data_aula': data_aula,
            'trimestre': trimestre
        })
        db.atualizar_validacao_evento_reconhecimento(
            professor_id=professor_id,
            aluno_id=aluno['id'],
            materia=materia,
            data_aula=data_aula,
            presenca_validada=presente
        )

    if pendentes_confirmacao:
        nomes = ', '.join(pendentes_confirmacao[:3])
        sufixo = '...' if len(pendentes_confirmacao) > 3 else ''
        definir_mensagem('erro', f'Confirme manualmente as presenças sugeridas antes de salvar. Pendentes: {nomes}{sufixo}')
        return redirect(url_for('diario', materia=materia, data=data_aula, serie=serie_atual, turma=turma_atual))

    db.salvar_diario_entradas(professor_id, materia, registros)
    db.registrar_auditoria(
        acao='SALVAR_DIARIO',
        entidade='diario_entradas',
        entidade_id=professor_id,
        usuario=usuario_atual_para_auditoria(),
        detalhes=f"Matéria: {materia}, Data: {data_aula}, Trimestre: {trimestre}, Registros: {len(registros)}"
    )
    definir_mensagem('sucesso', 'Diário salvo com sucesso.')
    return redirect(url_for('diario', materia=materia, data=data_aula, serie=serie_atual, turma=turma_atual))

@app.route('/salvar/aluno', methods=['POST'])
def salvar_aluno():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        novo_id = db.inserir_aluno(request.form)
        foto_aluno = request.files.get('foto_referencia')
        if foto_aluno and foto_aluno.filename:
            caminho_foto = salvar_foto_referencia_aluno(foto_aluno, novo_id)
            db.atualizar_foto_referencia_aluno(novo_id, caminho_foto)
        db.registrar_auditoria(
            acao='CRIAR',
            entidade='alunos',
            entidade_id=novo_id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Cadastro de aluno: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Aluno cadastrado com sucesso.')
    except ValueError as e:
        return render_template(
            'index.html', 
            erro_aluno=str(e), 
            mensagem={'tipo': None, 'texto': None},
            totais={'alunos': db.contar_total('alunos'), 'professores': db.contar_total('professores'), 'colaboradores': db.contar_total('colaboradores')}, 
            alunos=db.buscar_registros('alunos'), 
            professores=db.buscar_registros('professores'), 
            colaboradores=db.buscar_registros('colaboradores'), 
            usuario_nome=session.get('usuario_nome')
        )
    return redirect(url_for('dashboard'))
@app.route('/atualizar/aluno/<int:id>', methods=['POST'])
def atualizar_aluno(id):
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.atualizar_aluno(id, request.form)
        foto_aluno = request.files.get('foto_referencia')
        if foto_aluno and foto_aluno.filename:
            caminho_foto = salvar_foto_referencia_aluno(foto_aluno, id)
            db.atualizar_foto_referencia_aluno(id, caminho_foto)
        db.registrar_auditoria(
            acao='ATUALIZAR',
            entidade='alunos',
            entidade_id=id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Atualização de aluno: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Aluno atualizado com sucesso.')
    except ValueError as erro:
        definir_mensagem('erro', str(erro))
    # Redireciona mantendo a âncora da seção de alunos no dashboard
    return redirect(url_for('dashboard') + '#alunos')

@app.route('/salvar/professor', methods=['POST'])
def salvar_professor():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        novo_id = db.inserir_professor(request.form)
        db.registrar_auditoria(
            acao='CRIAR',
            entidade='professores',
            entidade_id=novo_id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Cadastro de professor: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Professor cadastrado com sucesso.')
    except ValueError:
        definir_mensagem('erro', 'Não foi possível cadastrar o professor. Verifique CPF e email.')
    return redirect(url_for('dashboard'))

@app.route('/atualizar/professor/<int:id>', methods=['POST'])
def atualizar_professor(id):
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.atualizar_professor(id, request.form)
        db.registrar_auditoria(
            acao='ATUALIZAR',
            entidade='professores',
            entidade_id=id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Atualização de professor: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Professor atualizado com sucesso.')
    except ValueError:
        definir_mensagem('erro', 'Não foi possível atualizar o professor. Verifique os dados informados.')
    # Redireciona mantendo a âncora da seção de professores
    return redirect(url_for('dashboard') + '#professores')

def validar_confirmacao_admin(senha_digitada):
    return senha_digitada == ADMIN_PASSWORD

@app.route('/excluir/aluno/<int:id>', methods=['POST'])
def excluir_aluno(id):
    if not usuario_logado():
        return redirect(url_for('login'))

    if not validar_confirmacao_admin(request.form.get('senha_admin_confirmacao', '')):
        definir_mensagem('erro', 'Confirmação de segurança inválida. Operação cancelada.')
        return redirect(url_for('dashboard') + '#alunos')

    db.excluir_aluno(id)
    db.registrar_auditoria(
        acao='ARQUIVAR',
        entidade='alunos',
        entidade_id=id,
        usuario=usuario_atual_para_auditoria(),
        detalhes='Aluno arquivado (exclusão lógica).'
    )
    definir_mensagem('sucesso', 'Aluno arquivado com sucesso. Registro preservado para auditoria.')
    return redirect(url_for('dashboard') + '#alunos')

@app.route('/excluir/professor/<int:id>', methods=['POST'])
def excluir_professor(id):
    if not usuario_logado():
        return redirect(url_for('login'))

    if not validar_confirmacao_admin(request.form.get('senha_admin_confirmacao', '')):
        definir_mensagem('erro', 'Confirmação de segurança inválida. Operação cancelada.')
        return redirect(url_for('dashboard') + '#professores')

    db.excluir_professor(id)
    db.registrar_auditoria(
        acao='INATIVAR',
        entidade='professores',
        entidade_id=id,
        usuario=usuario_atual_para_auditoria(),
        detalhes='Professor inativado (exclusão lógica).'
    )
    definir_mensagem('sucesso', 'Professor inativado com sucesso. Registro preservado para auditoria.')
    return redirect(url_for('dashboard') + '#professores')

@app.route('/excluir/colaborador/<int:id>', methods=['POST'])
def excluir_colaborador(id):
    if not usuario_logado():
        return redirect(url_for('login'))

    if not validar_confirmacao_admin(request.form.get('senha_admin_confirmacao', '')):
        definir_mensagem('erro', 'Confirmação de segurança inválida. Operação cancelada.')
        return redirect(url_for('dashboard') + '#colaboradores')

    db.excluir_colaborador(id)
    db.registrar_auditoria(
        acao='INATIVAR',
        entidade='colaboradores',
        entidade_id=id,
        usuario=usuario_atual_para_auditoria(),
        detalhes='Colaborador inativado (exclusão lógica).'
    )
    definir_mensagem('sucesso', 'Colaborador inativado com sucesso. Registro preservado para auditoria.')
    return redirect(url_for('dashboard') + '#colaboradores')

@app.route('/salvar/colaborador', methods=['POST'])
def salvar_colaborador():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        novo_id = db.inserir_colaborador(request.form)
        db.registrar_auditoria(
            acao='CRIAR',
            entidade='colaboradores',
            entidade_id=novo_id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Cadastro de colaborador: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Colaborador cadastrado com sucesso.')
    except ValueError:
        definir_mensagem('erro', 'Não foi possível cadastrar o colaborador. Verifique CPF e email.')
    return redirect(url_for('dashboard'))

@app.route('/atualizar/colaborador/<int:id>', methods=['POST'])
def atualizar_colaborador(id):
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.atualizar_colaborador(id, request.form)
        db.registrar_auditoria(
            acao='ATUALIZAR',
            entidade='colaboradores',
            entidade_id=id,
            usuario=usuario_atual_para_auditoria(),
            detalhes=f"Atualização de colaborador: {request.form.get('nome')}"
        )
        definir_mensagem('sucesso', 'Colaborador atualizado com sucesso.')
    except ValueError:
        definir_mensagem('erro', 'Não foi possível atualizar o colaborador. Verifique os dados informados.')
    # Redireciona mantendo a âncora da seção de colaboradores
    return redirect(url_for('dashboard') + '#colaboradores')

@app.route('/relatorio/<tipo>')
def relatorio(tipo):
    if not usuario_logado():
        return redirect(url_for('login'))

    if tipo not in ('alunos', 'professores', 'colaboradores', 'auditoria', 'reconhecimento'):
        definir_mensagem('erro', 'Tipo de relatório inválido.')
        return redirect(url_for('dashboard'))

    if tipo == 'auditoria':
        registros = db.buscar_logs_auditoria()
    elif tipo == 'reconhecimento':
        registros = db.buscar_relatorio_reconhecimento()
    else:
        registros = db.buscar_registros_com_inativos(tipo)

    return render_template('relatorio.html', tipo=tipo, registros=registros, gerado_em=datetime.now())

if __name__ == '__main__':
    app.run(debug=True, port=5000)