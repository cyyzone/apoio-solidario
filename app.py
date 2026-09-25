import os
from flask import Flask, render_template, request, jsonify, session
import sqlite3
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

INTEGRITY_ERRORS = (sqlite3.IntegrityError,)
if psycopg is not None:
    INTEGRITY_ERRORS += (psycopg.errors.UniqueViolation,)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'apoio-solidario-dev-key')

def usuario_da_sessao():
    return session.get('usuario_id')

def normalizar_cpf(cpf):
    return ''.join(caractere for caractere in str(cpf or '') if caractere.isdigit())

def cpf_valido(cpf):
    cpf = normalizar_cpf(cpf)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False

    for quantidade in (9, 10):
        soma = sum(
            int(digito) * (quantidade + 1 - indice)
            for indice, digito in enumerate(cpf[:quantidade])
        )
        resto = (soma * 10) % 11
        digito = 0 if resto == 10 else resto
        if int(cpf[quantidade]) != digito:
            return False
    return True

def normalizar_telefone(telefone):
    return ''.join(caractere for caractere in str(telefone or '') if caractere.isdigit())

def acesso_negado(mensagem='Faça login para continuar.'):
    return jsonify({"erro": mensagem}), 401

def usando_supabase():
    return bool(os.environ.get('SUPABASE_DB_URL'))

class CursorCompat:
    def __init__(self, cursor):
        self.cursor = cursor
    def execute(self, consulta, parametros=()):
        return self.cursor.execute(consulta.replace('?', '%s'), parametros)

    def __getattr__(self, nome):
        return getattr(self.cursor, nome)

class ConexaoPostgresCompat:
    def __init__(self, conexao):
        self.conexao = conexao

    def cursor(self):
        return CursorCompat(self.conexao.cursor())

    def commit(self):
        return self.conexao.commit()

    def __enter__(self):
        self.conexao.__enter__()
        return self

    def __exit__(self, tipo, valor, traceback):
        return self.conexao.__exit__(tipo, valor, traceback)

def conectar_banco():
    if usando_supabase():
        if psycopg is None:
            raise RuntimeError('Instale psycopg[binary] para usar o Supabase.')
        conexao = psycopg.connect(os.environ['SUPABASE_DB_URL'], row_factory=dict_row)
        return ConexaoPostgresCompat(conexao)

    conn = sqlite3.connect('app_ajuda.db')
    conn.row_factory = sqlite3.Row
    return conn

def adicionar_notificacao(id_usuario, tipo, mensagem, id_pedido=None, conn=None):
    if id_usuario is None:
        return None

    if conn is None:
        with conectar_banco() as conn_local:
            c = conn_local.cursor()
            c.execute(
                '''
                INSERT INTO notificacoes (id_usuario, tipo, mensagem, id_pedido)
                VALUES (?, ?, ?, ?)
                ''',
                (id_usuario, tipo, mensagem, id_pedido)
            )
            conn_local.commit()
        return None

    c = conn.cursor()
    c.execute(
        '''
        INSERT INTO notificacoes (id_usuario, tipo, mensagem, id_pedido)
        VALUES (?, ?, ?, ?)
        ''',
        (id_usuario, tipo, mensagem, id_pedido)
    )
    return None


def garantir_estrutura_supabase():
    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id_usuario BIGSERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT UNIQUE,
                telefone TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL,
                tipo_perfil TEXT NOT NULL,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION
            )
        ''')
        c.execute('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cpf TEXT')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS usuarios_cpf_idx ON usuarios(cpf) WHERE cpf IS NOT NULL')
        c.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id_pedido BIGSERIAL PRIMARY KEY,
                id_solicitante BIGINT REFERENCES usuarios(id_usuario),
                id_voluntario BIGINT REFERENCES usuarios(id_usuario),
                categoria TEXT NOT NULL,
                descricao_outros TEXT,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                status TEXT DEFAULT 'pendente',
                motivo_cancelamento TEXT,
                criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                aceito_em TIMESTAMPTZ,
                em_andamento TIMESTAMPTZ,
                concluido_em TIMESTAMPTZ
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS mensagens (
                id_mensagem BIGSERIAL PRIMARY KEY,
                id_pedido BIGINT NOT NULL REFERENCES pedidos(id_pedido),
                id_remetente BIGINT NOT NULL REFERENCES usuarios(id_usuario),
                texto TEXT NOT NULL,
                criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS notificacoes (
                id_notificacao BIGSERIAL PRIMARY KEY,
                id_usuario BIGINT NOT NULL REFERENCES usuarios(id_usuario),
                tipo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                id_pedido BIGINT,
                lida BOOLEAN DEFAULT FALSE,
                criado_em TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def garantir_estrutura_banco():
    if usando_supabase():
        garantir_estrutura_supabase()
        return

    with conectar_banco() as conn:
        c = conn.cursor()

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if c.fetchone() is None:
            c.execute('''
                CREATE TABLE usuarios (
                    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    cpf TEXT,
                    telefone TEXT NOT NULL UNIQUE,
                    senha TEXT NOT NULL,
                    tipo_perfil TEXT NOT NULL
                )
            ''')
        else:
            colunas_usuarios = [row[1] for row in c.execute('PRAGMA table_info(usuarios)').fetchall()]
            if 'senha' not in colunas_usuarios:
                c.execute('ALTER TABLE usuarios ADD COLUMN senha TEXT')
            if 'tipo_perfil' not in colunas_usuarios:
                c.execute('ALTER TABLE usuarios ADD COLUMN tipo_perfil TEXT')
            if 'latitude' not in colunas_usuarios:
                c.execute('ALTER TABLE usuarios ADD COLUMN latitude REAL')
            if 'longitude' not in colunas_usuarios:
                c.execute('ALTER TABLE usuarios ADD COLUMN longitude REAL')
            if 'cpf' not in colunas_usuarios:
                c.execute('ALTER TABLE usuarios ADD COLUMN cpf TEXT')

        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS usuarios_cpf_idx ON usuarios(cpf) WHERE cpf IS NOT NULL')

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pedidos'")
        if c.fetchone() is None:
            c.execute('''
                CREATE TABLE pedidos (
                    id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_solicitante INTEGER,
                    id_voluntario INTEGER,
                    categoria TEXT NOT NULL,
                    descricao_outros TEXT,
                    latitude REAL,
                    longitude REAL,
                    status TEXT DEFAULT 'pendente',
                    motivo_cancelamento TEXT,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    aceito_em TEXT,
                    em_andamento TEXT,
                    concluido_em TEXT,
                    FOREIGN KEY (id_solicitante) REFERENCES usuarios(id_usuario),
                    FOREIGN KEY (id_voluntario) REFERENCES usuarios(id_usuario)
                )
            ''')
        else:
            colunas_pedidos = [row[1] for row in c.execute('PRAGMA table_info(pedidos)').fetchall()]
            if 'id_solicitante' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN id_solicitante INTEGER')
            if 'id_voluntario' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN id_voluntario INTEGER')
            if 'latitude' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN latitude REAL')
            if 'longitude' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN longitude REAL')
            if 'motivo_cancelamento' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN motivo_cancelamento TEXT')
            if 'criado_em' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN criado_em TEXT')
            if 'aceito_em' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN aceito_em TEXT')
            if 'em_andamento' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN em_andamento TEXT')
            if 'concluido_em' not in colunas_pedidos:
                c.execute('ALTER TABLE pedidos ADD COLUMN concluido_em TEXT')

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mensagens'")
        if c.fetchone() is None:
            c.execute('''
                CREATE TABLE mensagens (
                    id_mensagem INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_pedido INTEGER NOT NULL,
                    id_remetente INTEGER NOT NULL,
                    texto TEXT NOT NULL,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido),
                    FOREIGN KEY (id_remetente) REFERENCES usuarios(id_usuario)
                )
            ''')

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='notificacoes'")
        if c.fetchone() is None:
            c.execute('''
                CREATE TABLE notificacoes (
                    id_notificacao INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_usuario INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    mensagem TEXT NOT NULL,
                    id_pedido INTEGER,
                    lida INTEGER DEFAULT 0,
                    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
                )
            ''')
        else:
            colunas_notificacoes = [row[1] for row in c.execute('PRAGMA table_info(notificacoes)').fetchall()]
            if 'lida' not in colunas_notificacoes:
                c.execute('ALTER TABLE notificacoes ADD COLUMN lida INTEGER DEFAULT 0')

        conn.commit()

# Cria as tabelas ao iniciar e corrige colunas faltantes em bancos já existentes
garantir_estrutura_banco()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/cadastro', methods=['POST'])
def cadastrar():
    dados = request.json or {}
    cpf = normalizar_cpf(dados.get('cpf'))
    telefone = normalizar_telefone(dados.get('telefone'))
    if not cpf_valido(cpf):
        return jsonify({"erro": "Informe um CPF válido."}), 400
    if len(telefone) < 10:
        return jsonify({"erro": "Informe um telefone válido para contato."}), 400
    latitude = dados.get('latitude')
    longitude = dados.get('longitude')

    try:
        with conectar_banco() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO usuarios (nome, cpf, telefone, senha, tipo_perfil, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['nome'],
                cpf,
                telefone,
                dados['senha'],
                dados['tipo_perfil'],
                latitude,
                longitude,
            ))
            conn.commit()
        return jsonify({"mensagem": "Cadastro realizado!"}), 201
    except INTEGRITY_ERRORS:
        return jsonify({"erro": "CPF ou telefone já cadastrado."}), 400

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.json
    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id_usuario, nome, cpf, telefone, tipo_perfil, latitude, longitude FROM usuarios
            WHERE cpf = ? AND senha = ?
        ''', (normalizar_cpf(dados.get('cpf')), dados.get('senha')))
        usuario = c.fetchone()

    if usuario:
        session['usuario_id'] = usuario['id_usuario']
        session['tipo_perfil'] = usuario['tipo_perfil']
        return jsonify(dict(usuario)), 200
    return jsonify({"erro": "Dados incorretos"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"mensagem": "Sessão encerrada."}), 200

@app.route('/api/pedidos', methods=['POST'])
def criar_pedido():
    id_solicitante = usuario_da_sessao()
    if not id_solicitante:
        return acesso_negado()
    if session.get('tipo_perfil') != 'necessitado':
        return jsonify({"erro": "Somente quem precisa de ajuda pode criar pedidos."}), 403

    dados = request.json or {}
    categoria = dados.get('categoria')
    descricao = dados.get('descricao', '')
    latitude = dados.get('latitude')
    longitude = dados.get('longitude')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO pedidos (id_solicitante, categoria, descricao_outros, latitude, longitude, status)
            VALUES (?, ?, ?, ?, ?, 'pendente')
        ''', (id_solicitante, categoria, descricao, latitude, longitude))
        conn.commit()
    return jsonify({"mensagem": "Pedido salvo com sucesso!"}), 201

@app.route('/api/pedidos', methods=['GET'])
def listar_pedidos():
    if not usuario_da_sessao():
        return acesso_negado()
    if session.get('tipo_perfil') != 'voluntario':
        return jsonify({"erro": "Somente voluntários podem consultar pedidos."}), 403

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT
                p.id_pedido,
                p.id_solicitante,
                p.categoria,
                p.descricao_outros,
                p.latitude,
                p.longitude,
                p.status,
                u.nome AS nome_solicitante,
                u.telefone AS telefone_solicitante
            FROM pedidos p
            LEFT JOIN usuarios u ON u.id_usuario = p.id_solicitante
            WHERE p.status = 'pendente'
            ORDER BY p.id_pedido DESC
        ''')
        pedidos = [dict(row) for row in c.fetchall()]
    return jsonify(pedidos)

@app.route('/api/pedidos/<int:id_pedido>/aceitar', methods=['POST'])
def aceitar_pedido(id_pedido):
    id_voluntario = usuario_da_sessao()
    if not id_voluntario:
        return acesso_negado()
    if session.get('tipo_perfil') != 'voluntario':
        return jsonify({"erro": "Somente voluntários podem aceitar pedidos."}), 403

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id_solicitante, status
            FROM pedidos
            WHERE id_pedido = ?
        ''', (id_pedido,))
        pedido = c.fetchone()
        if not pedido:
            return jsonify({"erro": "Pedido não encontrado."}), 404
        if pedido['id_solicitante'] == id_voluntario:
            return jsonify({"erro": "Você não pode aceitar o seu próprio pedido."}), 409
        if pedido['status'] != 'pendente':
            return jsonify({"erro": "Este pedido já foi aceito ou não está disponível."}), 409

        c.execute('''
            UPDATE pedidos
            SET status = 'aceito', id_voluntario = ?, aceito_em = CURRENT_TIMESTAMP
            WHERE id_pedido = ? AND status = 'pendente'
        ''', (id_voluntario, id_pedido))

        if c.rowcount == 0:
            return jsonify({"erro": "Este pedido já foi aceito ou não existe."}), 409

        c.execute('''
            SELECT u.nome AS voluntario_nome
            FROM usuarios u
            WHERE u.id_usuario = ?
        ''', (id_voluntario,))
        voluntario = c.fetchone()
        nome_voluntario = dict(voluntario)['voluntario_nome'] if voluntario else 'Voluntário'

        c.execute('''
            SELECT p.id_solicitante, u.telefone AS telefone_solicitante
            FROM pedidos p
            LEFT JOIN usuarios u ON u.id_usuario = p.id_solicitante
            WHERE p.id_pedido = ?
        ''', (id_pedido,))
        solicitante = c.fetchone()
        if solicitante and solicitante['id_solicitante']:
            adicionar_notificacao(
                solicitante['id_solicitante'],
                'pedido_aceito',
                f'{nome_voluntario} aceitou o seu pedido e está a caminho.',
                id_pedido,
                conn=conn,
            )
        conn.commit()

    return jsonify({
        "mensagem": "Pedido aceito!",
        "voluntario_nome": nome_voluntario,
        "id_voluntario": id_voluntario,
        "telefone_solicitante": solicitante['telefone_solicitante'] if solicitante else None
    })

@app.route('/api/pedidos/<int:id_pedido>/status', methods=['PUT'])
def atualizar_status_pedido(id_pedido):
    id_usuario = usuario_da_sessao()
    if not id_usuario:
        return acesso_negado()

    dados = request.get_json(silent=True) or {}
    novo_status = dados.get('status')
    status_validos = {'aceito', 'em_andamento', 'concluido', 'cancelado'}
    if novo_status not in status_validos:
        return jsonify({"erro": "Status inválido."}), 400

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT status, id_solicitante, id_voluntario, motivo_cancelamento
            FROM pedidos
            WHERE id_pedido = ?
        ''', (id_pedido,))
        pedido = c.fetchone()

        if not pedido or id_usuario not in (pedido['id_solicitante'], pedido['id_voluntario']):
            return jsonify({"erro": "Você não participa deste pedido."}), 403

        transicoes = {
            'pendente': {'aceito', 'cancelado'},
            'aceito': {'em_andamento', 'concluido', 'cancelado'},
            'em_andamento': {'concluido', 'cancelado'}
        }
        if novo_status not in transicoes.get(pedido['status'], set()):
            return jsonify({"erro": "Essa alteração de status não é permitida."}), 409

        motivo = None
        if novo_status == 'cancelado':
            motivo = (dados.get('motivo') or '').strip()
            if not motivo:
                return jsonify({"erro": "Informe o motivo do cancelamento."}), 400
            c.execute(
                'UPDATE pedidos SET status = ?, motivo_cancelamento = ? WHERE id_pedido = ?',
                (novo_status, motivo, id_pedido)
            )
        else:
            c.execute(
                'UPDATE pedidos SET status = ?, motivo_cancelamento = NULL WHERE id_pedido = ?',
                (novo_status, id_pedido)
            )

        if novo_status == 'em_andamento':
            c.execute(
                'UPDATE pedidos SET em_andamento = CURRENT_TIMESTAMP WHERE id_pedido = ?',
                (id_pedido,)
            )
        if novo_status == 'concluido':
            c.execute(
                'UPDATE pedidos SET concluido_em = CURRENT_TIMESTAMP WHERE id_pedido = ?',
                (id_pedido,)
            )

        for id_alvo in (pedido['id_solicitante'], pedido['id_voluntario']):
            if id_alvo is None or id_alvo == id_usuario:
                continue
            if novo_status == 'cancelado':
                mensagem = f'O pedido foi cancelado. Motivo: {motivo}'
                tipo = 'pedido_cancelado'
            elif novo_status == 'em_andamento':
                mensagem = 'O pedido entrou em andamento.'
                tipo = 'pedido_em_andamento'
            elif novo_status == 'concluido':
                mensagem = 'O pedido foi concluído com sucesso.'
                tipo = 'pedido_concluido'
            else:
                mensagem = 'O status do pedido foi atualizado.'
                tipo = 'pedido_atualizado'
            adicionar_notificacao(id_alvo, tipo, mensagem, id_pedido, conn=conn)

        conn.commit()

    return jsonify({"mensagem": "Status atualizado.", "status": novo_status, "motivo_cancelamento": motivo}), 200

@app.route('/api/usuarios/<int:id_usuario>/localizacao', methods=['PUT'])
def atualizar_localizacao_usuario(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode atualizar sua própria localização.')

    dados = request.json or {}
    latitude = dados.get('latitude')
    longitude = dados.get('longitude')

    if latitude is None or longitude is None:
        return jsonify({"erro": "Latitude e longitude são obrigatórias."}), 400

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE usuarios SET latitude = ?, longitude = ? WHERE id_usuario = ?",
            (latitude, longitude, id_usuario)
        )
        conn.commit()

    return jsonify({"mensagem": "Localização atualizada com sucesso!"}), 200

@app.route('/api/usuarios/<int:id_usuario>', methods=['GET'])
def obter_usuario(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode consultar seu próprio perfil.')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id_usuario, nome, telefone, tipo_perfil, latitude, longitude
            FROM usuarios
            WHERE id_usuario = ?
        ''', (id_usuario,))
        usuario = c.fetchone()

    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    return jsonify(dict(usuario)), 200

@app.route('/api/usuarios/<int:id_usuario>', methods=['PUT'])
def atualizar_usuario(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode atualizar seu próprio perfil.')

    dados = request.json or {}
    nome = dados.get('nome')
    senha = dados.get('senha')
    latitude = dados.get('latitude')
    longitude = dados.get('longitude')

    if not nome and not senha and latitude is None and longitude is None:
        return jsonify({"erro": "Informe nome, senha ou localização para atualizar."}), 400

    campos = []
    valores = []

    if nome:
        campos.append('nome = ?')
        valores.append(nome)
    if senha:
        campos.append('senha = ?')
        valores.append(senha)
    if latitude is not None:
        campos.append('latitude = ?')
        valores.append(latitude)
    if longitude is not None:
        campos.append('longitude = ?')
        valores.append(longitude)

    valores.append(id_usuario)

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute(
            f"UPDATE usuarios SET {', '.join(campos)} WHERE id_usuario = ?",
            tuple(valores)
        )
        conn.commit()

    return jsonify({"mensagem": "Perfil atualizado com sucesso!"}), 200

@app.route('/api/pedidos/minhas/<int:id_usuario>', methods=['GET'])
def listar_minhas_solicitacoes(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode consultar suas próprias solicitações.')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT
                p.id_pedido,
                p.categoria,
                p.descricao_outros,
                p.status,
                p.id_voluntario,
                v.nome AS nome_voluntario,
                p.latitude,
                p.longitude,
                p.motivo_cancelamento,
                p.criado_em,
                p.aceito_em,
                p.em_andamento,
                p.concluido_em
            FROM pedidos p
            LEFT JOIN usuarios v ON v.id_usuario = p.id_voluntario
            WHERE p.id_solicitante = ?
            ORDER BY p.id_pedido DESC
        ''', (id_usuario,))
        pedidos = [dict(row) for row in c.fetchall()]

    return jsonify(pedidos), 200

@app.route('/api/usuarios/<int:id_usuario>/notificacoes', methods=['GET'])
def listar_notificacoes(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode consultar suas próprias notificações.')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id_notificacao, id_usuario, tipo, mensagem, id_pedido, lida, criado_em
            FROM notificacoes
            WHERE id_usuario = ?
            ORDER BY id_notificacao DESC
            LIMIT 20
        ''', (id_usuario,))
        notificacoes = [dict(row) for row in c.fetchall()]

    return jsonify(notificacoes), 200

@app.route('/api/usuarios/<int:id_usuario>/notificacoes', methods=['DELETE'])
def limpar_notificacoes(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode limpar suas próprias notificações.')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM notificacoes WHERE id_usuario = ?', (id_usuario,))
        removidas = c.rowcount
        conn.commit()

    return jsonify({
        'mensagem': 'Notificações limpas com sucesso.',
        'removidas': removidas
    }), 200

@app.route('/api/pedidos/conversas/<int:id_usuario>', methods=['GET'])
def listar_conversas(id_usuario):
    if usuario_da_sessao() != id_usuario:
        return acesso_negado('Você só pode consultar suas próprias conversas.')

    with conectar_banco() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT
                p.id_pedido,
                p.categoria,
                p.status,
                s.nome AS nome_solicitante,
                s.telefone AS telefone_solicitante,
                v.nome AS nome_voluntario,
                v.telefone AS telefone_voluntario
            FROM pedidos p
            LEFT JOIN usuarios s ON s.id_usuario = p.id_solicitante
            LEFT JOIN usuarios v ON v.id_usuario = p.id_voluntario
            WHERE p.status <> 'pendente'
              AND (p.id_solicitante = ? OR p.id_voluntario = ?)
            ORDER BY p.id_pedido DESC
        ''', (id_usuario, id_usuario))
        conversas = [dict(row) for row in c.fetchall()]

    return jsonify(conversas), 200

def usuario_participa_do_pedido(cursor, id_pedido, id_usuario):
    cursor.execute('''
        SELECT id_pedido
        FROM pedidos
        WHERE id_pedido = ?
                    AND status <> 'pendente'
          AND (id_solicitante = ? OR id_voluntario = ?)
    ''', (id_pedido, id_usuario, id_usuario))
    return cursor.fetchone() is not None

@app.route('/api/pedidos/<int:id_pedido>/mensagens', methods=['GET', 'POST'])
def mensagens_do_pedido(id_pedido):
    dados = request.get_json(silent=True) or {}
    id_usuario = usuario_da_sessao()

    if not id_usuario:
        return acesso_negado()

    with conectar_banco() as conn:
        c = conn.cursor()
        if not usuario_participa_do_pedido(c, id_pedido, id_usuario):
            return jsonify({"erro": "Você não participa desta conversa."}), 403

        if request.method == 'POST':
            texto = (dados.get('texto') or '').strip()
            if not texto:
                return jsonify({"erro": "A mensagem não pode ficar vazia."}), 400

            c.execute('''
                INSERT INTO mensagens (id_pedido, id_remetente, texto)
                VALUES (?, ?, ?)
            ''', (id_pedido, id_usuario, texto))

            c.execute('''
                SELECT id_solicitante, id_voluntario
                FROM pedidos
                WHERE id_pedido = ?
            ''', (id_pedido,))
            pedido = c.fetchone()
            if pedido:
                for id_alvo in (pedido['id_solicitante'], pedido['id_voluntario']):
                    if id_alvo and id_alvo != id_usuario:
                        c.execute('''
                            SELECT nome
                            FROM usuarios
                            WHERE id_usuario = ?
                        ''', (id_usuario,))
                        remetente = c.fetchone()
                        nome_remetente = dict(remetente)['nome'] if remetente else 'Usuário'
                        adicionar_notificacao(
                            id_alvo,
                            'mensagem_nova',
                            f'{nome_remetente} enviou uma nova mensagem no pedido #{id_pedido}.',
                            id_pedido,
                            conn=conn,
                        )
            conn.commit()
            return jsonify({"mensagem": "Mensagem enviada."}), 201

        c.execute('''
            SELECT m.id_mensagem, m.id_remetente, u.nome AS nome_remetente,
                   m.texto, m.criado_em
            FROM mensagens m
            JOIN usuarios u ON u.id_usuario = m.id_remetente
            WHERE m.id_pedido = ?
            ORDER BY m.id_mensagem ASC
        ''', (id_pedido,))
        mensagens = [dict(row) for row in c.fetchall()]

    return jsonify(mensagens), 200

if __name__ == '__main__':
    app.run(debug=True)