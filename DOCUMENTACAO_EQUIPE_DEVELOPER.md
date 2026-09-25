# Documentação para equipe e desenvolvimento

## Introdução
Este projeto é uma aplicação web em Flask para gestão de pedidos de ajuda solidária.

O sistema conecta duas partes principais:
- solicitante: pessoa que precisa de ajuda
- voluntário: pessoa que oferece ajuda

A lógica de negócio foi implementada em Python e a interface foi construída em HTML + JavaScript com integração ao backend via API REST.

---

## Objetivo do sistema
O projeto busca:
- simplificar a solicitação de ajuda
- organizar o atendimento por voluntários
- controlar o status da demanda
- permitir comunicação direta entre as partes
- manter histórico e notificações

---

## Arquitetura geral

### Backend
Arquivo principal:
- app.py

Responsabilidades:
- cadastro e login de usuários
- criação e listagem de pedidos
- aceite de pedidos
- atualização de status
- envio de mensagens
- geração de notificações
- acesso ao banco de dados

### Frontend
Arquivo principal:
- templates/index.html

Responsabilidades:
- telas de login e cadastro
- listagem de pedidos
- painel do usuário
- notificações visuais
- área de conversa
- atualização de status da demanda

### Banco de dados
- SQLite para ambiente local
- estrutura compatível com esquema SQL e integração com Supabase

---

## Entidades principais

### Usuários
A tabela usuarios armazena:
- id_usuario
- nome
- cpf
- telefone
- senha
- tipo_perfil
- latitude
- longitude

Tipos de perfil:
- necessitado
- voluntario

### Pedidos
A tabela pedidos armazena:
- id_pedido
- id_solicitante
- id_voluntario
- categoria
- descricao_outros
- latitude
- longitude
- status
- motivo_cancelamento
- criado_em
- aceito_em
- em_andamento
- concluido_em

### Mensagens
A tabela mensagens guarda:
- id_mensagem
- id_pedido
- id_remetente
- texto
- criado_em

### Notificações
A tabela notificacoes guarda:
- id_notificacao
- id_usuario
- tipo
- mensagem
- id_pedido
- lida
- criado_em

---

## Fluxo de negócio

### Cadastro
- usuário envia nome, CPF, telefone de contato e senha
- o backend valida os dados
- o perfil define as permissões do usuário

### Login
- o sistema verifica CPF e senha
- cria a sessão do usuário
- retorna os dados do usuário autenticado

### Criação do pedido
- apenas necessitados podem criar pedido
- o pedido recebe categoria, descrição e localização
- o pedido entra com status pendente

### Aceite do pedido
- apenas voluntários podem aceitar pedidos
- o pedido precisa estar pendente
- o voluntário não pode aceitar o próprio pedido
- ao aceitar, o status passa para aceito
- o solicitante recebe uma notificação

### Status do pedido
Os status permitidos são:
- pendente
- aceito
- em_andamento
- concluido
- cancelado

As regras de transição foram implementadas para evitar mudanças inválidas.

### Cancelamento
- o cancelamento exige motivo
- o motivo fica salvo no pedido
- o sistema avisa as partes envolvidas

### Mensagens
- a conversa foi limitada aos usuários participantes do pedido
- mensagens são salvas no banco
- o remetente recebe uma notificação para o outro participante

### Notificações
Notificações são geradas sempre que acontece algo importante, como:
- pedido aceito
- pedido em andamento
- pedido concluído
- pedido cancelado
- nova mensagem

---

## Endpoints principais

### Autenticação
- POST /api/cadastro
- POST /api/login
- POST /api/logout

### Pedidos
- POST /api/pedidos
- GET /api/pedidos
- POST /api/pedidos/<id>/aceitar
- PUT /api/pedidos/<id>/status
- GET /api/pedidos/minhas/<id>
- GET /api/pedidos/conversas/<id>
- GET /api/pedidos/<id>/mensagens
- POST /api/pedidos/<id>/mensagens

### Usuários
- GET /api/usuarios/<id>
- PUT /api/usuarios/<id>
- PUT /api/usuarios/<id>/localizacao
- GET /api/usuarios/<id>/notificacoes

---

## Regras de segurança e validação
- usuário precisa estar autenticado para acessar a maioria das rotas
- cada ação verifica o perfil do usuário
- o sistema garante que usuário só veja dados pessoais próprios
- usuários só podem participar de pedidos nos quais estão envolvidos
- mensagens e status são validados antes de persistirem

---

## Observações de UX
Foram adicionados ajustes importantes para melhorar a experiência:
- notificações na interface
- filtro por categoria
- mensagens mais claras ao usuário
- melhor visualização de pedidos vazios e estados do fluxo
- feedback de erros em ações comuns

---

## Ajustes importantes já implementados
- correção de compatibilidade do banco SQLite
- criação de campos de histórico do pedido
- geração de notificações por evento
- registro de motivo de cancelamento
- reforço das regras do fluxo de ajuda
- padronização do código para facilitar manutenção

---

## Como rodar localmente
1. Instale as dependências:

   pip install -r requirements.txt

2. Execute a aplicação:

   python app.py

3. Use o navegador para acessar a interface local do Flask.

---

## Pontos de melhoria futuros
- autenticação com token JWT
- melhor separação em módulos e services
- testes automatizados mais robustos
- deploy em produção
- painel administrativo
- suporte a notificações push
- mapa mais dinâmico e visualização de rotas

---

## Conclusão
Esse projeto é uma aplicação funcional de apoio comunitário, com backend em Flask, frontend em HTML/JS e regras de negócio centralizadas no fluxo de ajuda. Ele já entrega a base para um sistema de voluntariado com comunicação, notificações e acompanhamento de demandas.
