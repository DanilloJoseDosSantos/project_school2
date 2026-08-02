from flask import Flask, render_template, request, redirect, url_for, session
from gerenciador_escola import GerenciadorEscola

app = Flask(__name__)
app.secret_key = "chave_secreta_sistema_escolar"
db = GerenciadorEscola()

def usuario_logado():
    return session.get('usuario_logado', False)

@app.route('/')
def raiz():
    if usuario_logado():
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        if usuario == "admin" and senha == "1234":
            session['usuario_logado'] = True
            session['usuario_nome'] = "Administrador"
            return redirect(url_for('dashboard'))
        return render_template('login.html', erro="Usuário ou senha inválidos!")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not usuario_logado():
        return redirect(url_for('login'))
    
    totais = {
        'alunos': db.contar_total('alunos'),
        'professores': db.contar_total('professores'),
        'colaboradores': db.contar_total('colaboradores')
    }
    
    return render_template(
        'index.html',
        usuario_nome=session.get('usuario_nome', 'Usuário'),
        totais=totais,
        alunos=db.buscar_registros('alunos'),
        professores=db.buscar_registros('professores'),
        colaboradores=db.buscar_registros('colaboradores')
    )

@app.route('/salvar/aluno', methods=['POST'])
def salvar_aluno():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.inserir_aluno(request.form)
    except ValueError as e:
        return render_template(
            'index.html', 
            erro_aluno=str(e), 
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
    except ValueError:
        pass
    # Redireciona mantendo a âncora da seção de alunos no dashboard
    return redirect(url_for('dashboard') + '#alunos')

@app.route('/salvar/professor', methods=['POST'])
def salvar_professor():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.inserir_professor(request.form)
    except ValueError:
        pass
    return redirect(url_for('dashboard'))

@app.route('/atualizar/professor/<int:id>', methods=['POST'])
def atualizar_professor(id):
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.atualizar_professor(id, request.form)
    except ValueError:
        pass
    # Redireciona mantendo a âncora da seção de professores
    return redirect(url_for('dashboard') + '#professores')

@app.route('/salvar/colaborador', methods=['POST'])
def salvar_colaborador():
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.inserir_colaborador(request.form)
    except ValueError:
        pass
    return redirect(url_for('dashboard'))

@app.route('/atualizar/colaborador/<int:id>', methods=['POST'])
def atualizar_colaborador(id):
    if not usuario_logado(): return redirect(url_for('login'))
    try:
        db.atualizar_colaborador(id, request.form)
    except ValueError:
        pass
    # Redireciona mantendo a âncora da seção de colaboradores
    return redirect(url_for('dashboard') + '#colaboradores')

if __name__ == '__main__':
    app.run(debug=True, port=5000)