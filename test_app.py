import uuid

import app


def criar_usuario(client, nome, telefone, senha, tipo_perfil):
    resp = client.post(
        '/api/cadastro',
        json={
            'nome': nome,
            'telefone': telefone,
            'senha': senha,
            'tipo_perfil': tipo_perfil,
        },
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    login = client.post('/api/login', json={'telefone': telefone, 'senha': senha})
    assert login.status_code == 200, login.get_data(as_text=True)
    return login.get_json()


def test_cancelamento_salva_motivo_e_restricoes_basicas():
    requester = app.app.test_client()
    volunteer = app.app.test_client()

    suffix = uuid.uuid4().hex[:8]
    requester_user = criar_usuario(requester, 'Pessoa', '61' + suffix, '123', 'necessitado')
    volunteer_user = criar_usuario(volunteer, 'Voluntario', '62' + suffix, '123', 'voluntario')

    with requester.session_transaction() as sess:
        sess['usuario_id'] = requester_user['id_usuario']
        sess['tipo_perfil'] = requester_user['tipo_perfil']

    with volunteer.session_transaction() as sess:
        sess['usuario_id'] = volunteer_user['id_usuario']
        sess['tipo_perfil'] = volunteer_user['tipo_perfil']

    pedido = requester.post('/api/pedidos', json={'categoria': 'Teste cancelamento', 'descricao': 'Preciso de ajuda'})
    assert pedido.status_code == 201, pedido.get_data(as_text=True)

    conn = app.conectar_banco()
    pedido_id = conn.execute(
        'SELECT id_pedido FROM pedidos WHERE id_solicitante = ? ORDER BY id_pedido DESC LIMIT 1',
        (requester_user['id_usuario'],),
    ).fetchone()['id_pedido']
    conn.close()

    aceite = volunteer.post(f'/api/pedidos/{pedido_id}/aceitar', json={'voluntario_id': volunteer_user['id_usuario']})
    assert aceite.status_code == 200, aceite.get_data(as_text=True)

    cancel = requester.put(
        f'/api/pedidos/{pedido_id}/status',
        json={'status': 'cancelado', 'motivo': 'Pedido cancelado por mudança de planos'},
    )
    assert cancel.status_code == 200, cancel.get_data(as_text=True)
    payload = cancel.get_json()
    assert payload['status'] == 'cancelado'

    conn = app.conectar_banco()
    row = conn.execute('SELECT motivo_cancelamento FROM pedidos WHERE id_pedido = ?', (pedido_id,)).fetchone()
    conn.close()
    assert row['motivo_cancelamento'] == 'Pedido cancelado por mudança de planos'


def test_notificacoes_sao_geradas_para_ambos_os_lados():
    requester = app.app.test_client()
    volunteer = app.app.test_client()

    suffix = uuid.uuid4().hex[:8]
    requester_user = criar_usuario(requester, 'Pessoa 2', '71' + suffix, '123', 'necessitado')
    volunteer_user = criar_usuario(volunteer, 'Voluntario 2', '72' + suffix, '123', 'voluntario')

    with requester.session_transaction() as sess:
        sess['usuario_id'] = requester_user['id_usuario']
        sess['tipo_perfil'] = requester_user['tipo_perfil']

    with volunteer.session_transaction() as sess:
        sess['usuario_id'] = volunteer_user['id_usuario']
        sess['tipo_perfil'] = volunteer_user['tipo_perfil']

    pedido = requester.post('/api/pedidos', json={'categoria': 'Teste notificacao', 'descricao': 'Ajuda'} )
    assert pedido.status_code == 201, pedido.get_data(as_text=True)

    conn = app.conectar_banco()
    pedido_id = conn.execute(
        'SELECT id_pedido FROM pedidos WHERE id_solicitante = ? ORDER BY id_pedido DESC LIMIT 1',
        (requester_user['id_usuario'],),
    ).fetchone()['id_pedido']
    conn.close()

    aceite = volunteer.post(f'/api/pedidos/{pedido_id}/aceitar', json={'voluntario_id': volunteer_user['id_usuario']})
    assert aceite.status_code == 200, aceite.get_data(as_text=True)

    resp = requester.get(f'/api/usuarios/{requester_user["id_usuario"]}/notificacoes')
    assert resp.status_code == 200, resp.get_data(as_text=True)
    notificacoes = resp.get_json()
    assert any(item['tipo'] == 'pedido_aceito' for item in notificacoes)

    msg = volunteer.post(
        f'/api/pedidos/{pedido_id}/mensagens',
        json={'id_usuario': volunteer_user['id_usuario'], 'texto': 'Cheguei na sua casa'},
    )
    assert msg.status_code == 201, msg.get_data(as_text=True)

    resp2 = requester.get(f'/api/usuarios/{requester_user["id_usuario"]}/notificacoes')
    assert resp2.status_code == 200, resp2.get_data(as_text=True)
    tipos = {item['tipo'] for item in resp2.get_json()}
    assert 'mensagem_nova' in tipos
