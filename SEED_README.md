# Scripts de Seed - MyMovieDB

Scripts para popular o banco de dados com dados de exemplo.

## 📋 Pré-requisitos

1. Ambiente virtual ativado
2. Banco de dados criado e migrações aplicadas
3. Aplicação configurada (`instance/config.dev.json`)

## 🎬 Script 1: Dados de Filmes

### O que cria:
- ✅ 11 gêneros cinematográficos
- ✅ 5 funções técnicas (Diretor, Produtor, Roteirista, etc.)
- ✅ 107 pessoas (atores e equipe técnica)
- ✅ 12 filmes clássicos com dados completos:

**Filmes Internacionais:**
  - **The Shawshank Redemption** (1994)
  - **The Dark Knight** (2008)
  - **Inception** (2010)
  - **The Matrix** (1999)
  - **Forrest Gump** (1994)
  - **Pulp Fiction** (1994)
  - **The Godfather** (1972)
  - **Schindler's List** (1993)
  - **The Lord of the Rings: The Return of the King** (2003)
  - **Gladiator** (2000)

**Filmes Brasileiros:**
  - **Tropa de Elite** (2007)
  - **Deus é Brasileiro** (2003)

### Como usar:

```bash
# Windows
python seed_data.py

# Linux/Mac
python3 seed_data.py
```

### Dados incluídos para cada filme:
- Título original e em português
- Ano de lançamento e duração
- Sinopse
- Gêneros
- 5 personagens principais (ator + personagem)
- Equipe técnica (direção, produção, fotografia, edição)

## ⭐ Script 2: Avaliações (Opcional)

**IMPORTANTE:** Execute este script **DEPOIS** de:
1. Executar `seed_data.py`
2. Criar pelo menos 1 usuário na aplicação (via interface web)

### O que cria:
- Avaliações aleatórias dos filmes pelos usuários
- Notas de 1 a 10
- Percentual de recomendação
- Alguns comentários (30% das avaliações)

### Como usar:

```bash
# Windows
python seed_avaliacoes.py

# Linux/Mac
python3 seed_avaliacoes.py
```

### Perfis de avaliadores simulados:
- **Crítico rigoroso**: notas mais baixas (6-9), 60% recomendam
- **Entusiasta**: notas mais altas (7-10), 85% recomendam
- **Casual**: notas medianas (5-9), 70% recomendam

## 🔄 Executar novamente

Os scripts verificam se os dados já existem antes de criar. Para popular novamente:

1. **Limpar o banco:**
   ```bash
   flask db downgrade base
   flask db upgrade
   ```

2. **Executar os scripts novamente:**
   ```bash
   python seed_data.py
   python seed_avaliacoes.py
   ```

## ⚠️ Notas Importantes

1. **Dados são do IMDB/TMDB:** Informações reais dos filmes
2. **Datas de nascimento:** Formato ISO (YYYY-MM-DD)
3. **Nomes artísticos:** Apenas quando diferem do nome real
4. **Gêneros múltiplos:** Cada filme pode ter vários gêneros
5. **UniqueConstraints:** Scripts respeitam as constraints do modelo

## 🧪 Testar as Queries

Após executar os scripts, você pode testar as queries de exemplo:

```python
from app import create_app
from moviedb.models.filme import Filme
from moviedb.models.pessoa import Ator
from sqlalchemy.orm import joinedload

app = create_app()
with app.app_context():
    # Listar elenco de um filme
    filme = Filme.query.filter_by(titulo_original="The Matrix").first()
    for atuacao in filme.atuacoes:
        print(f"{atuacao.ator.nome} como {atuacao.personagem}")

    # Listar filmografia de um ator
    ator = Ator.query.filter_by(nome="Leonardo DiCaprio").first()
    for atuacao in ator.atuacoes:
        print(f"{atuacao.filme.titulo_original} - {atuacao.personagem}")
```

## 📊 Estatísticas Esperadas

Após executar ambos os scripts com pelo menos 3 usuários:

**Filmes Internacionais:**
- **The Shawshank Redemption**: ~9.1/10 (altamente recomendado)
- **The Godfather**: ~9.0/10
- **Schindler's List**: ~8.9/10
- **The Dark Knight**: ~8.8/10
- **LOTR: Return of the King**: ~8.8/10
- **Pulp Fiction**: ~8.7/10
- **Inception**: ~8.7/10
- **The Matrix**: ~8.5/10
- **Gladiator**: ~8.3/10
- **Forrest Gump**: ~8.3/10

**Filmes Brasileiros:**
- **Tropa de Elite**: ~8.4/10
- **Deus é Brasileiro**: ~7.8/10

## 🐛 Troubleshooting

### Erro: "No module named 'app'"
**Solução:** Execute no diretório raiz do projeto onde está `app.py`

### Erro: "Unable to open database file"
**Solução:**
1. Verifique se o banco foi criado: `flask db upgrade`
2. Verifique o caminho em `config.dev.json`

### Erro: "Pessoa X já existe"
**Solução:** Isso é normal! O script pula registros duplicados.

### Nenhuma avaliação criada
**Solução:**
1. Execute `seed_data.py` primeiro
2. Crie pelo menos 1 usuário na aplicação web
3. Execute `seed_avaliacoes.py` novamente

## 📝 Personalizar os Dados

Para adicionar seus próprios filmes, edite `seed_data.py`:

```python
filmes_data = [
    {
        "titulo_original": "Seu Filme",
        "titulo_portugues": "Nome em Português",
        "ano_lancamento": 2024,
        "duracao_minutos": 120,
        "lancado": True,
        "sinopse": "Sua sinopse aqui...",
        "generos": ["Drama", "Ação"],
        "elenco": [
            {"ator": "Nome do Ator", "personagem": "Nome do Personagem"},
            # ... mais atores
        ],
        "equipe": [
            {"pessoa": "Nome da Pessoa", "funcao": "Diretor"},
            # ... mais equipe
        ]
    },
    # ... mais filmes
]
```

Lembre-se de adicionar as pessoas correspondentes em `pessoas_data`!

## 🎯 Próximos Passos

Após popular o banco:

1. ✅ Explore a aplicação web
2. ✅ Crie usuários e teste avaliações
3. ✅ Teste as queries de exemplo do tutorial
4. ✅ Experimente adicionar mais filmes manualmente

---

**Dúvidas?** Consulte a documentação principal em `README.md`