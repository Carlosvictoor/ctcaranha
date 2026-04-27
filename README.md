# CTC Aranha

Sistema web para controle da academia de muay thai CTC Aranha.

## Recursos

- Login administrativo
- Cadastro e gestão de alunos
- Cadastro de planos comerciais e turmas com horarios
- Controle de mensalidades com status e vencimento
- Dashboard com métricas operacionais
- Relatórios financeiros e operacionais com exportação CSV e PDF
- Avisos por WhatsApp em dois modos: manual por clique sem custo de API ou automático via Twilio quando configurado
- Backup manual do banco e troca de senha do administrador pelo painel
- Layout ajustado para uso móvel com navegação otimizada para celular
- Suporte a instalação como PWA com manifest, service worker e fallback offline
- Tarefa pronta no VS Code para subir o servidor local

## Execução local

1. Crie e ative um ambiente virtual Python.
2. Instale as dependências com `pip install -r requirements.txt`.
3. Crie o arquivo `.env` a partir de `.env.example` se quiser personalizar chave secreta e WhatsApp.
4. Inicie com `python run.py` ou execute a tarefa `Iniciar CTC Aranha` no VS Code.
5. Acesse `http://127.0.0.1:5000`.

## Login padrão

- Usuário: `admin`
- Senha: `ctc123`

## Configuração do WhatsApp

Sem as credenciais do Twilio, o sistema funciona em modo manual por clique.

No modo manual:

- O botão `Abrir WhatsApp` gera a mensagem pronta e abre a conversa do aluno.
- O clique fica registrado no histórico de avisos.
- Não existe envio automático agendado sem API configurada.

Pelo menu de configurações do painel é possível alterar:

- Nome exibido da academia
- Quantos dias antes do vencimento o lembrete automático será disparado
- Template da mensagem usando os placeholders `student_name`, `gym_name`, `amount` e `due_date`
- Senha do administrador
- Geração e download de backups do banco SQLite

## Variáveis opcionais

- `SECRET_KEY`
- `DATABASE_URL` para produção com banco persistente, como PostgreSQL
- `SQLITE_PATH` para apontar o SQLite para um volume persistente quando não usar PostgreSQL
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_WHATSAPP_FROM`
- `DISABLE_SCHEDULER` para desligar o scheduler em testes e rotinas utilitárias

## Rotina automática

- Ao iniciar a aplicação, o sistema garante as mensalidades do mês atual para alunos ativos.
- O scheduler roda diariamente às 09:00 para processar lembretes pendentes apenas quando a Twilio estiver configurada, incluindo antecipação padrão de 3 dias antes do vencimento.
- Também é possível disparar a rotina manualmente pelo dashboard ou pela tela de mensalidades.

## Operação do painel

- O menu `Planos e Turmas` centraliza os cadastros comerciais e a grade de aulas.
- A tela de `Relatorios` permite baixar CSV e PDF com financeiro, turmas e avisos.
- A tela de `Configuracoes` agora concentra personalização, segurança e backup.

## Produção

- Troque a senha padrão do admin no primeiro acesso.
- Mantenha backups periódicos da pasta `backups`.
- Em produção, use um servidor WSGI e mantenha `DISABLE_SCHEDULER=0` para processar lembretes automáticos.
- Para o deploy nao parecer um reset, nao use o SQLite interno da pasta da app em hospedagens com filesystem efemero.
- Prefira configurar `DATABASE_URL` com PostgreSQL do provedor.
- Se for manter SQLite, configure `SQLITE_PATH` apontando para um volume persistente fora do pacote publicado.
- Com banco persistente, novos deploys reiniciam apenas o processo web, sem recriar seus dados.
- Para a instalacao como PWA funcionar melhor, publique sempre em HTTPS.

## Railway

- O projeto agora inclui `railway.toml` com start em `gunicorn run:app --bind 0.0.0.0:$PORT`.
- Tambem existe `app.py` na raiz para compatibilidade extra com detectores automaticos de entrypoint.
- No painel do Railway, configure pelo menos `SECRET_KEY` e `DATABASE_URL`.
- O `PORT` e fornecido automaticamente pelo Railway e nao precisa ser definido manualmente.
- Se o banco for PostgreSQL do proprio Railway, use a URL entregue pelo plugin sem alterar manualmente.
- Em producao no Railway, evite usar o SQLite interno da aplicacao porque o filesystem pode ser recriado a cada deploy.