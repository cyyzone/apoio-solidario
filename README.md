# Apoio Solidário

Este projeto é uma aplicação web para conectar pessoas que precisam de ajuda com voluntários que podem oferecer apoio.

A ideia é simples: uma pessoa cria um pedido de ajuda, outro usuário pode aceitar esse pedido, conversar sobre o caso e acompanhar o progresso até a conclusão.

---

## O que a aplicação faz

### 1. Cadastro e login
- Usuários podem se cadastrar como:
  - necessitado
  - voluntário
- Cada pessoa entra com CPF e senha.
- O telefone fica disponível para contato, inclusive pelo WhatsApp.
- A sessão do usuário é salva no sistema para manter o acesso.

### 2. Criação de pedidos
- Quem precisa de ajuda pode criar um pedido.
- O pedido tem categoria, descrição e localização.
- A categoria ajuda a organizar os pedidos por tipo de necessidade.

### 3. Aceite de pedido por voluntário
- Voluntários podem ver os pedidos abertos.
- Eles podem aceitar um pedido que não seja deles.
- O pedido muda de status para aceito.

### 4. Atualização de status
O pedido pode seguir um fluxo de progresso:
- pendente
- aceito
- em andamento
- concluído
- cancelado

Isso ajuda a mostrar o andamento da ajuda de forma clara.

### 5. Cancelamento com motivo
- Se alguém cancelar o pedido, precisa informar o motivo.
- Esse motivo fica registrado no pedido.
- Isso aumenta a transparência e ajuda na organização do processo.

### 6. Mensagens entre as partes
- Depois que o pedido é aceito, o solicitante e o voluntário podem conversar dentro do mesmo pedido.
- As mensagens ficam guardadas no banco de dados.

### 7. Notificações
- Quando há mudança no pedido, o sistema gera notificações.
- Exemplo:
  - pedido aceito
  - pedido em andamento
  - pedido concluído
  - nova mensagem
  - pedido cancelado
- O usuário pode ver essas notificações na tela.

### 8. Histórico e localização
- O sistema guarda data e hora de eventos importantes.
- Também é possível registrar a localização do usuário.
- Isso é útil para quem precisa de ajuda e para quem vai ajudar.

---

## Fluxo principal do projeto

### Para quem precisa de ajuda
1. Cria uma conta como necessitado.
2. Faz login.
3. Cria um pedido de ajuda.
4. Aguarda o voluntário aceitar.
5. Recebe notificações e conversa com o voluntário.
6. Pode acompanhar o status do pedido.

### Para quem quer ajudar
1. Cria uma conta como voluntário.
2. Faz login.
3. Vê os pedidos disponíveis.
4. Aceita um pedido.
5. Mantém contato com a pessoa que pediu ajuda.
6. Atualiza o status conforme o apoio vai evoluindo.

---

## Estrutura do projeto

### Arquivos principais

- app.py: contém toda a lógica do backend, rotas da API, regras de negócio e acesso ao banco.
- templates/index.html: interface do frontend, com telas de login, cadastro, pedidos, notificações e chat.
- requirements.txt: lista as dependências do projeto.
- supabase_schema.sql: estrutura do schema PostgreSQL usado no Supabase.

---

## Tecnologias usadas

- Python
- Flask
- PostgreSQL via Supabase
- HTML
- JavaScript
- Tailwind CSS
- Leaflet (para mapa/localização)

---

## Regras de negócio importantes

- Só quem é necessitado pode criar pedido.
- Só quem é voluntário pode aceitar pedido.
- Um voluntário não pode aceitar o próprio pedido.
- Apenas usuários envolvidos no pedido podem ver e usar a conversa.
- Cancelamento exige motivo.
- Status só pode mudar em sequência válida.
- Notificações são geradas quando algo importante acontece.

---

## Como rodar o projeto

1. Abra o terminal na pasta do projeto.
2. Crie e ative um ambiente virtual:

  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```

3. Instale as dependências:

  ```powershell
  pip install -r requirements.txt
  Copy-Item .env.example .env
  ```

4. Inicie a aplicação:

  ```powershell
  python app.py
  ```

5. Abra `http://127.0.0.1:5000` no navegador.

O Supabase é obrigatório. Configure `SUPABASE_DB_URL` no `.env` local ou nas variáveis de ambiente do Render e execute [`supabase_schema.sql`](supabase_schema.sql) no banco antes do primeiro deploy. Nunca publique o arquivo `.env` ou credenciais do banco.

## Testes

```powershell
python -m pytest
```

Os testes cobrem cancelamento, notificações e mensagens usando o cliente de testes do Flask.

---

## Como o projeto foi evoluído

Durante o desenvolvimento, o projeto recebeu melhorias em várias áreas:

- integração do banco PostgreSQL com Supabase e Render
- ajuste de regras do fluxo de ajuda
- criação de histórico de pedidos
- adição de notificações visíveis na interface
- melhoria na experiência do usuário (UX)
- organização da comunicação entre solicitante e voluntário

---

## Objetivo do projeto

O objetivo principal é facilitar a ajuda entre pessoas de forma simples, rápida e organizada, tornando o processo mais transparente para quem precisa de apoio e para quem está disposto a ajudar.

---

## Em resumo

Este projeto funciona como uma plataforma simples de ajuda solidária, com:
- cadastro de usuários
- criação de pedidos
- aceitação por voluntários
- comunicação por mensagens
- notificações automáticas
- acompanhamento do status
- registro de histórico e motivos de cancelamento

É uma solução prática, fácil de entender e pronta para evoluir com mais funcionalidades no futuro.

## Publicar no GitHub

O repositório local já está inicializado. Crie um repositório vazio no GitHub e execute:

```powershell
git add .
git commit -m "Organiza projeto para publicacao"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/apoio-solidario.git
git push -u origin main
```

Antes do `git add`, confirme que `.env` e `.venv` não aparecem no `git status`.
