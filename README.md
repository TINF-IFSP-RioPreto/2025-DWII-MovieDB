# Preparando a aplicação

Todas as operações devem ser executadas:
1. Dentro do ambiente virtual da aplicação.
2. No diretório raiz da aplicação (onde está o arquivo `app.py`)

## O Abiente virtual

Para verificar se o ambiente virutal está ativo, o prompt do terminal deve estar
precedido pelo nome do ambiente virtual, por exemplo: `(.venv) user@machine:~/path/to/project$` no linux
ou `(.venv) C:\path\to\project>` no Windows.

Se o ambiente virtual não estiver ativo, ative-o com o comando:
- No Linux:
  ```bash
  source .venv/bin/activate
  ```
- No Windows:
  ```bash
  .\.venv\Scripts\activate.ps1
  ```
  
Se o ambiente virtual ainda não estiver criado (não existir o diretório `.venv`), crie-o com o comando:
- No Linux:
  ```bash
  python3 -m venv .venv
  ```
- No Windows:
  ```bash
  python -m venv .venv
  ```

No PyCharm, você pode configurar o ambiente virtual nas configurações do projeto, ou na tela principal do editor na parte mais inferior à direita.

## Configuração da aplicação

Para que a aplicação possa ser executado, é preciso que haja um arquivo JSON de configuração chamado
`config.dev.json` no diretório `instance`. Você pode criar esse arquivo copiando o conteúdo do
arquivo `config.sample.json` e ajustando os valores conforme necessário.

1. Instale as dependências do projeto:
   ```bash
   pip install -r requirements.txt
   ```

## Migração do banco de dados

A migração do banco de dados, agora, está sendo feita pelo Flask-Migrate. Para preparar a aplicação,
você deve seguir os seguintes passos:

1. Configure a variável de ambiente `FLASK_APP` para apontar para o arquivo principal da aplicação:
   ```bash
   export FLASK_APP=app.py  # No Windows use: set FLASK_APP=app.py
   ```
2. Inicialize o repositório de migrações:
   ```bash
   flask db init
   ```
3. Faça as alterações necessárias no arquivo `migrations/env.py` para configurar o `target_metada` e carregar os modelos da aplicação (por volta da linha 30):
   ```python
   from moviedb import db
   import moviedb.models # noqa: F401
   target_metadata = db.metadata
   ```
4. Crie a primeira migração:
   ```bash
   flask db migrate -m "Migracao inicial"
   ```
5. Aplique a migração ao banco de dados:
   ```bash
   flask db upgrade
   ```
**Se a sua aplicação já tem migrações criadas (há arquivos no diretório `migrations\versions`), não execute os passos 2, 3 e 4. Apenas execute o passo 5 para aplicar as migrações ao banco de dados.**

## Execução da aplicação

1. Agora, você pode rodar a aplicação:
   ```bash
   flask run
   ```

## Executando o Celery

A aplicação utiliza Celery para executar tarefas assíncronas e agendadas. Para que as tarefas funcionem corretamente, você precisa executar dois processos do Celery:

### Worker (Processa as tarefas)

O worker é responsável por executar as tarefas assíncronas. Execute o seguinte comando:

- No Windows:
  ```bash
  celery -A celery_app:celery_app worker --loglevel=info --pool=gevent --concurrency=10 --without-gossip --without-mingle --without-heartbeat -E
  ```

- No Linux:
  ```bash
  celery -A celery_app:celery_app worker --loglevel=info --concurrency=10 --without-gossip --without-mingle --without-heartbeat -E
  ```

### Beat (Agendador de tarefas)

O beat é responsável por agendar e disparar tarefas periódicas listados no arquivo de configuração da aplicação. Execute em outro terminal:

```bash
celery -A celery_app:celery_app beat --loglevel=info
```

**Nota:** Você precisará de três terminais abertos simultaneamente:
1. Um para o Flask (`flask run`)
2. Um para o Celery Worker
3. Um para o Celery Beat

**Requisito:** Certifique-se de que o Redis esteja rodando antes de iniciar o Celery (conforme configurado em `broker_url` e `result_backend` no arquivo de configuração).
