#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de seed para popular o banco de dados com filmes de exemplo.
Uso: python seed_data.py
"""

import sys
from datetime import datetime
from app import create_app
from moviedb import db
from moviedb.models.filme import Filme, Genero, FuncoesTecnicas
from moviedb.models.pessoa import Pessoa, Ator
from moviedb.models.relacoes import Atuacoes, EquipeTecnica, FilmeGenero


def criar_generos():
    """Cria os gêneros cinematográficos"""
    print("📝 Criando gêneros...")

    generos_data = [
        {"nome": "Drama", "descricao": "Filmes dramáticos com foco em emoções e desenvolvimento de personagens"},
        {"nome": "Ação", "descricao": "Filmes com cenas de ação, perseguições e combates"},
        {"nome": "Ficção Científica", "descricao": "Filmes que exploram conceitos científicos e tecnológicos futuristas"},
        {"nome": "Crime", "descricao": "Filmes sobre crimes, investigações e criminosos"},
        {"nome": "Suspense", "descricao": "Filmes que mantêm tensão e suspense ao longo da narrativa"},
        {"nome": "Romance", "descricao": "Filmes focados em relacionamentos românticos"},
        {"nome": "Aventura", "descricao": "Filmes com jornadas épicas e exploração"},
        {"nome": "Comédia", "descricao": "Filmes humorísticos que visam entreter e divertir"},
        {"nome": "Fantasia", "descricao": "Filmes com elementos mágicos e sobrenaturais"},
        {"nome": "Guerra", "descricao": "Filmes ambientados em contextos de guerra"},
        {"nome": "Policial", "descricao": "Filmes sobre forças policiais e investigações"},
    ]

    generos = {}
    for g in generos_data:
        genero = Genero.get_first_or_none_by("nome", g["nome"])
        if not genero:
            genero = Genero(nome=g["nome"], descricao=g["descricao"], ativo=True)
            db.session.add(genero)
            print(f"  ✓ {g['nome']}")
        else:
            print(f"  ⊙ {g['nome']} (já existe)")
        generos[g["nome"]] = genero

    db.session.commit()
    return generos


def criar_funcoes_tecnicas():
    """Cria as funções técnicas"""
    print("\n📝 Criando funções técnicas...")

    funcoes_data = [
        {"nome": "Diretor", "descricao": "Responsável pela direção geral do filme"},
        {"nome": "Produtor", "descricao": "Responsável pela produção executiva"},
        {"nome": "Roteirista", "descricao": "Responsável pelo roteiro"},
        {"nome": "Diretor de Fotografia", "descricao": "Responsável pela fotografia e cinematografia"},
        {"nome": "Editor", "descricao": "Responsável pela edição e montagem"},
    ]

    funcoes = {}
    for f in funcoes_data:
        funcao = FuncoesTecnicas.get_first_or_none_by("nome", f["nome"])
        if not funcao:
            funcao = FuncoesTecnicas(nome=f["nome"], descricao=f["descricao"], ativa=True)
            db.session.add(funcao)
            print(f"  ✓ {f['nome']}")
        else:
            print(f"  ⊙ {f['nome']} (já existe)")
        funcoes[f["nome"]] = funcao

    db.session.commit()
    return funcoes


def criar_pessoas_e_atores():
    """Cria as pessoas (atores e equipe técnica)"""
    print("\n📝 Criando pessoas e atores...")

    # Dados de pessoas (equipe técnica e atores)
    pessoas_data = [
        # The Shawshank Redemption
        {"nome": "Tim Robbins", "nacionalidade": "Estados Unidos", "nascimento": "1958-10-16", "e_ator": True, "nome_artistico": "Tim Robbins"},
        {"nome": "Morgan Freeman", "nacionalidade": "Estados Unidos", "nascimento": "1937-06-01", "e_ator": True, "nome_artistico": "Morgan Freeman"},
        {"nome": "Bob Gunton", "nacionalidade": "Estados Unidos", "nascimento": "1945-11-15", "e_ator": True, "nome_artistico": None},
        {"nome": "William Sadler", "nacionalidade": "Estados Unidos", "nascimento": "1950-04-13", "e_ator": True, "nome_artistico": None},
        {"nome": "Clancy Brown", "nacionalidade": "Estados Unidos", "nascimento": "1959-01-05", "e_ator": True, "nome_artistico": None},
        {"nome": "Frank Darabont", "nacionalidade": "França", "nascimento": "1959-01-28", "e_ator": False},
        {"nome": "Niki Marvin", "nacionalidade": "Estados Unidos", "nascimento": None, "e_ator": False},
        {"nome": "Roger Deakins", "nacionalidade": "Reino Unido", "nascimento": "1949-05-24", "e_ator": False},
        {"nome": "Richard Francis-Bruce", "nacionalidade": "Austrália", "nascimento": "1948-01-01", "e_ator": False},

        # The Dark Knight
        {"nome": "Christian Bale", "nacionalidade": "Reino Unido", "nascimento": "1974-01-30", "e_ator": True, "nome_artistico": None},
        {"nome": "Heath Ledger", "nacionalidade": "Austrália", "nascimento": "1979-04-04", "e_ator": True, "nome_artistico": None},
        {"nome": "Aaron Eckhart", "nacionalidade": "Estados Unidos", "nascimento": "1968-03-12", "e_ator": True, "nome_artistico": None},
        {"nome": "Michael Caine", "nacionalidade": "Reino Unido", "nascimento": "1933-03-14", "e_ator": True, "nome_artistico": "Michael Caine"},
        {"nome": "Gary Oldman", "nacionalidade": "Reino Unido", "nascimento": "1958-03-21", "e_ator": True, "nome_artistico": None},
        {"nome": "Christopher Nolan", "nacionalidade": "Reino Unido", "nascimento": "1970-07-30", "e_ator": False},
        {"nome": "Emma Thomas", "nacionalidade": "Reino Unido", "nascimento": "1971-01-01", "e_ator": False},
        {"nome": "Wally Pfister", "nacionalidade": "Estados Unidos", "nascimento": "1961-07-08", "e_ator": False},
        {"nome": "Lee Smith", "nacionalidade": "Austrália", "nascimento": "1960-06-10", "e_ator": False},

        # Inception
        {"nome": "Leonardo DiCaprio", "nacionalidade": "Estados Unidos", "nascimento": "1974-11-11", "e_ator": True, "nome_artistico": None},
        {"nome": "Joseph Gordon-Levitt", "nacionalidade": "Estados Unidos", "nascimento": "1981-02-17", "e_ator": True, "nome_artistico": None},
        {"nome": "Elliot Page", "nacionalidade": "Canadá", "nascimento": "1987-02-21", "e_ator": True, "nome_artistico": "Elliot Page"},
        {"nome": "Tom Hardy", "nacionalidade": "Reino Unido", "nascimento": "1977-09-15", "e_ator": True, "nome_artistico": None},
        {"nome": "Marion Cotillard", "nacionalidade": "França", "nascimento": "1975-09-30", "e_ator": True, "nome_artistico": None},

        # The Matrix
        {"nome": "Keanu Reeves", "nacionalidade": "Canadá", "nascimento": "1964-09-02", "e_ator": True, "nome_artistico": None},
        {"nome": "Laurence Fishburne", "nacionalidade": "Estados Unidos", "nascimento": "1961-07-30", "e_ator": True, "nome_artistico": None},
        {"nome": "Carrie-Anne Moss", "nacionalidade": "Canadá", "nascimento": "1967-08-21", "e_ator": True, "nome_artistico": None},
        {"nome": "Hugo Weaving", "nacionalidade": "Nigéria", "nascimento": "1960-04-04", "e_ator": True, "nome_artistico": None},
        {"nome": "Joe Pantoliano", "nacionalidade": "Estados Unidos", "nascimento": "1951-09-12", "e_ator": True, "nome_artistico": None},
        {"nome": "Lana Wachowski", "nacionalidade": "Estados Unidos", "nascimento": "1965-06-21", "e_ator": False},
        {"nome": "Lilly Wachowski", "nacionalidade": "Estados Unidos", "nascimento": "1967-12-29", "e_ator": False},
        {"nome": "Bill Pope", "nacionalidade": "Estados Unidos", "nascimento": "1952-06-19", "e_ator": False},
        {"nome": "Zach Staenberg", "nacionalidade": "Estados Unidos", "nascimento": "1953-01-01", "e_ator": False},
        {"nome": "Joel Silver", "nacionalidade": "Estados Unidos", "nascimento": "1952-07-14", "e_ator": False},

        # Forrest Gump
        {"nome": "Tom Hanks", "nacionalidade": "Estados Unidos", "nascimento": "1956-07-09", "e_ator": True, "nome_artistico": None},
        {"nome": "Robin Wright", "nacionalidade": "Estados Unidos", "nascimento": "1966-04-08", "e_ator": True, "nome_artistico": None},
        {"nome": "Gary Sinise", "nacionalidade": "Estados Unidos", "nascimento": "1955-03-17", "e_ator": True, "nome_artistico": None},
        {"nome": "Sally Field", "nacionalidade": "Estados Unidos", "nascimento": "1946-11-06", "e_ator": True, "nome_artistico": None},
        {"nome": "Mykelti Williamson", "nacionalidade": "Estados Unidos", "nascimento": "1957-03-04", "e_ator": True, "nome_artistico": None},
        {"nome": "Robert Zemeckis", "nacionalidade": "Estados Unidos", "nascimento": "1952-05-14", "e_ator": False},
        {"nome": "Wendy Finerman", "nacionalidade": "Estados Unidos", "nascimento": "1960-01-01", "e_ator": False},
        {"nome": "Don Burgess", "nacionalidade": "Estados Unidos", "nascimento": "1956-01-01", "e_ator": False},
        {"nome": "Arthur Schmidt", "nacionalidade": "Estados Unidos", "nascimento": "1937-10-17", "e_ator": False},

        # Pulp Fiction
        {"nome": "John Travolta", "nacionalidade": "Estados Unidos", "nascimento": "1954-02-18", "e_ator": True, "nome_artistico": None},
        {"nome": "Samuel L. Jackson", "nacionalidade": "Estados Unidos", "nascimento": "1948-12-21", "e_ator": True, "nome_artistico": None},
        {"nome": "Uma Thurman", "nacionalidade": "Estados Unidos", "nascimento": "1970-04-29", "e_ator": True, "nome_artistico": None},
        {"nome": "Bruce Willis", "nacionalidade": "Alemanha", "nascimento": "1955-03-19", "e_ator": True, "nome_artistico": None},
        {"nome": "Tim Roth", "nacionalidade": "Reino Unido", "nascimento": "1961-05-14", "e_ator": True, "nome_artistico": None},
        {"nome": "Quentin Tarantino", "nacionalidade": "Estados Unidos", "nascimento": "1963-03-27", "e_ator": False},
        {"nome": "Lawrence Bender", "nacionalidade": "Estados Unidos", "nascimento": "1957-10-17", "e_ator": False},
        {"nome": "Andrzej Sekula", "nacionalidade": "Polônia", "nascimento": "1954-12-15", "e_ator": False},
        {"nome": "Sally Menke", "nacionalidade": "Estados Unidos", "nascimento": "1953-12-17", "e_ator": False},

        # The Godfather
        {"nome": "Marlon Brando", "nacionalidade": "Estados Unidos", "nascimento": "1924-04-03", "e_ator": True, "nome_artistico": None},
        {"nome": "Al Pacino", "nacionalidade": "Estados Unidos", "nascimento": "1940-04-25", "e_ator": True, "nome_artistico": None},
        {"nome": "James Caan", "nacionalidade": "Estados Unidos", "nascimento": "1940-03-26", "e_ator": True, "nome_artistico": None},
        {"nome": "Robert Duvall", "nacionalidade": "Estados Unidos", "nascimento": "1931-01-05", "e_ator": True, "nome_artistico": None},
        {"nome": "Diane Keaton", "nacionalidade": "Estados Unidos", "nascimento": "1946-01-05", "e_ator": True, "nome_artistico": None},
        {"nome": "Francis Ford Coppola", "nacionalidade": "Estados Unidos", "nascimento": "1939-04-07", "e_ator": False},
        {"nome": "Albert S. Ruddy", "nacionalidade": "Canadá", "nascimento": "1930-03-28", "e_ator": False},
        {"nome": "Gordon Willis", "nacionalidade": "Estados Unidos", "nascimento": "1931-05-28", "e_ator": False},
        {"nome": "William Reynolds", "nacionalidade": "Estados Unidos", "nascimento": "1910-06-14", "e_ator": False},

        # Schindler's List
        {"nome": "Liam Neeson", "nacionalidade": "Irlanda", "nascimento": "1952-06-07", "e_ator": True, "nome_artistico": None},
        {"nome": "Ben Kingsley", "nacionalidade": "Reino Unido", "nascimento": "1943-12-31", "e_ator": True, "nome_artistico": "Ben Kingsley"},
        {"nome": "Ralph Fiennes", "nacionalidade": "Reino Unido", "nascimento": "1962-12-22", "e_ator": True, "nome_artistico": None},
        {"nome": "Caroline Goodall", "nacionalidade": "Reino Unido", "nascimento": "1959-11-13", "e_ator": True, "nome_artistico": None},
        {"nome": "Jonathan Sagall", "nacionalidade": "Canadá", "nascimento": "1959-06-23", "e_ator": True, "nome_artistico": None},
        {"nome": "Steven Spielberg", "nacionalidade": "Estados Unidos", "nascimento": "1946-12-18", "e_ator": False},
        {"nome": "Gerald R. Molen", "nacionalidade": "Estados Unidos", "nascimento": "1935-01-06", "e_ator": False},
        {"nome": "Janusz Kaminski", "nacionalidade": "Polônia", "nascimento": "1959-06-27", "e_ator": False},
        {"nome": "Michael Kahn", "nacionalidade": "Estados Unidos", "nascimento": "1935-12-08", "e_ator": False},

        # The Lord of the Rings: The Return of the King
        {"nome": "Elijah Wood", "nacionalidade": "Estados Unidos", "nascimento": "1981-01-28", "e_ator": True, "nome_artistico": None},
        {"nome": "Ian McKellen", "nacionalidade": "Reino Unido", "nascimento": "1939-05-25", "e_ator": True, "nome_artistico": "Ian McKellen"},
        {"nome": "Viggo Mortensen", "nacionalidade": "Estados Unidos", "nascimento": "1958-10-20", "e_ator": True, "nome_artistico": None},
        {"nome": "Sean Astin", "nacionalidade": "Estados Unidos", "nascimento": "1971-02-25", "e_ator": True, "nome_artistico": None},
        {"nome": "Andy Serkis", "nacionalidade": "Reino Unido", "nascimento": "1964-04-20", "e_ator": True, "nome_artistico": None},
        {"nome": "Peter Jackson", "nacionalidade": "Nova Zelândia", "nascimento": "1961-10-31", "e_ator": False},
        {"nome": "Barrie M. Osborne", "nacionalidade": "Estados Unidos", "nascimento": "1944-02-07", "e_ator": False},
        {"nome": "Andrew Lesnie", "nacionalidade": "Austrália", "nascimento": "1956-01-01", "e_ator": False},
        {"nome": "Jamie Selkirk", "nacionalidade": "Nova Zelândia", "nascimento": "1946-01-01", "e_ator": False},

        # Gladiator
        {"nome": "Russell Crowe", "nacionalidade": "Nova Zelândia", "nascimento": "1964-04-07", "e_ator": True, "nome_artistico": None},
        {"nome": "Joaquin Phoenix", "nacionalidade": "Porto Rico", "nascimento": "1974-10-28", "e_ator": True, "nome_artistico": None},
        {"nome": "Connie Nielsen", "nacionalidade": "Dinamarca", "nascimento": "1965-07-03", "e_ator": True, "nome_artistico": None},
        {"nome": "Oliver Reed", "nacionalidade": "Reino Unido", "nascimento": "1938-02-13", "e_ator": True, "nome_artistico": None},
        {"nome": "Richard Harris", "nacionalidade": "Irlanda", "nascimento": "1930-10-01", "e_ator": True, "nome_artistico": None},
        {"nome": "Ridley Scott", "nacionalidade": "Reino Unido", "nascimento": "1937-11-30", "e_ator": False},
        {"nome": "Douglas Wick", "nacionalidade": "Estados Unidos", "nascimento": "1954-10-14", "e_ator": False},
        {"nome": "John Mathieson", "nacionalidade": "Reino Unido", "nascimento": "1961-05-03", "e_ator": False},
        {"nome": "Pietro Scalia", "nacionalidade": "Itália", "nascimento": "1960-03-17", "e_ator": False},

        # Tropa de Elite
        {"nome": "Wagner Moura", "nacionalidade": "Brasil", "nascimento": "1976-06-27", "e_ator": True, "nome_artistico": None},
        {"nome": "Caio Junqueira", "nacionalidade": "Brasil", "nascimento": "1975-03-07", "e_ator": True, "nome_artistico": None},
        {"nome": "André Ramiro", "nacionalidade": "Brasil", "nascimento": "1976-12-15", "e_ator": True, "nome_artistico": None},
        {"nome": "Fernanda Machado", "nacionalidade": "Brasil", "nascimento": "1980-10-03", "e_ator": True, "nome_artistico": None},
        {"nome": "Maria Ribeiro", "nacionalidade": "Brasil", "nascimento": "1975-06-09", "e_ator": True, "nome_artistico": None},
        {"nome": "José Padilha", "nacionalidade": "Brasil", "nascimento": "1967-08-01", "e_ator": False},
        {"nome": "Marcos Prado", "nacionalidade": "Brasil", "nascimento": "1961-01-01", "e_ator": False},
        {"nome": "Lula Carvalho", "nacionalidade": "Brasil", "nascimento": "1949-01-01", "e_ator": False},
        {"nome": "Daniel Rezende", "nacionalidade": "Brasil", "nascimento": "1969-01-01", "e_ator": False},

        # Deus é Brasileiro
        {"nome": "Antônio Fagundes", "nacionalidade": "Brasil", "nascimento": "1949-04-18", "e_ator": True, "nome_artistico": None},
        {"nome": "Paloma Duarte", "nacionalidade": "Brasil", "nascimento": "1977-09-21", "e_ator": True, "nome_artistico": None},
        {"nome": "Wagner Moura", "nacionalidade": "Brasil", "nascimento": "1976-06-27", "e_ator": True, "nome_artistico": None},  # Já existe
        {"nome": "Bruce Gomlevsky", "nacionalidade": "Brasil", "nascimento": "1960-01-01", "e_ator": True, "nome_artistico": None},
        {"nome": "Stepan Nercessian", "nacionalidade": "Brasil", "nascimento": "1948-12-02", "e_ator": True, "nome_artistico": None},
        {"nome": "Cacá Diegues", "nacionalidade": "Brasil", "nascimento": "1940-05-19", "e_ator": False},
        {"nome": "Renata Almeida Magalhães", "nacionalidade": "Brasil", "nascimento": None, "e_ator": False},
        {"nome": "Breno Silveira", "nacionalidade": "Brasil", "nascimento": "1964-09-11", "e_ator": False},
        {"nome": "Sérgio Mekler", "nacionalidade": "Brasil", "nascimento": "1950-01-01", "e_ator": False},
    ]

    pessoas = {}
    atores = {}

    for p in pessoas_data:
        # Verificar se pessoa já existe
        pessoa = Pessoa.get_first_or_none_by("nome", p["nome"])

        if not pessoa:
            nascimento = datetime.strptime(p["nascimento"], "%Y-%m-%d") if p["nascimento"] else None

            if p["e_ator"]:
                # Criar ator
                ator = Ator(
                    nome=p["nome"],
                    nacionalidade=p["nacionalidade"],
                    dta_nascimento=nascimento,
                    nome_artistico=p.get("nome_artistico")
                )
                db.session.add(ator)
                atores[p["nome"]] = ator
                print(f"  ✓ {p['nome']} (ator)")
            else:
                # Criar pessoa comum
                pessoa = Pessoa(
                    nome=p["nome"],
                    nacionalidade=p["nacionalidade"],
                    dta_nascimento=nascimento,
                    e_ator=False
                )
                db.session.add(pessoa)
                print(f"  ✓ {p['nome']} (técnico)")
        else:
            print(f"  ⊙ {p['nome']} (já existe)")
            if p["e_ator"]:
                atores[p["nome"]] = pessoa

        pessoas[p["nome"]] = pessoa if not p["e_ator"] else atores.get(p["nome"])

    db.session.commit()
    return pessoas, atores


def criar_filmes(generos, pessoas, atores, funcoes):
    """Cria os filmes com elenco e equipe técnica"""
    print("\n📽️  Criando filmes...")

    filmes_data = [
        {
            "titulo_original": "The Shawshank Redemption",
            "titulo_portugues": "Um Sonho de Liberdade",
            "ano_lancamento": 1994,
            "duracao_minutos": 142,
            "lancado": True,
            "sinopse": "Dois homens presos se reúnem ao longo de vários anos, encontrando consolo e eventual redenção através de atos de decência comum.",
            "generos": ["Drama", "Crime"],
            "elenco": [
                {"ator": "Tim Robbins", "personagem": "Andy Dufresne"},
                {"ator": "Morgan Freeman", "personagem": "Ellis Boyd 'Red' Redding"},
                {"ator": "Bob Gunton", "personagem": "Warden Norton"},
                {"ator": "William Sadler", "personagem": "Heywood"},
                {"ator": "Clancy Brown", "personagem": "Captain Hadley"},
            ],
            "equipe": [
                {"pessoa": "Frank Darabont", "funcao": "Diretor"},
                {"pessoa": "Frank Darabont", "funcao": "Roteirista"},
                {"pessoa": "Niki Marvin", "funcao": "Produtor"},
                {"pessoa": "Roger Deakins", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Richard Francis-Bruce", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "The Dark Knight",
            "titulo_portugues": "Batman: O Cavaleiro das Trevas",
            "ano_lancamento": 2008,
            "duracao_minutos": 152,
            "lancado": True,
            "sinopse": "Quando a ameaça conhecida como o Coringa surge e causa estragos e caos nas pessoas de Gotham, Batman deve aceitar um dos maiores testes psicológicos e físicos de sua capacidade de lutar contra a injustiça.",
            "generos": ["Ação", "Crime", "Drama"],
            "elenco": [
                {"ator": "Christian Bale", "personagem": "Bruce Wayne / Batman"},
                {"ator": "Heath Ledger", "personagem": "Joker"},
                {"ator": "Aaron Eckhart", "personagem": "Harvey Dent / Two-Face"},
                {"ator": "Michael Caine", "personagem": "Alfred Pennyworth"},
                {"ator": "Gary Oldman", "personagem": "James Gordon"},
            ],
            "equipe": [
                {"pessoa": "Christopher Nolan", "funcao": "Diretor"},
                {"pessoa": "Christopher Nolan", "funcao": "Roteirista"},
                {"pessoa": "Emma Thomas", "funcao": "Produtor"},
                {"pessoa": "Wally Pfister", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Lee Smith", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Inception",
            "titulo_portugues": "A Origem",
            "ano_lancamento": 2010,
            "duracao_minutos": 148,
            "lancado": True,
            "sinopse": "Um ladrão que rouba segredos corporativos através do uso da tecnologia de compartilhamento de sonhos recebe a tarefa inversa de plantar uma ideia na mente de um CEO.",
            "generos": ["Ação", "Ficção Científica", "Suspense"],
            "elenco": [
                {"ator": "Leonardo DiCaprio", "personagem": "Dom Cobb"},
                {"ator": "Joseph Gordon-Levitt", "personagem": "Arthur"},
                {"ator": "Elliot Page", "personagem": "Ariadne"},
                {"ator": "Tom Hardy", "personagem": "Eames"},
                {"ator": "Marion Cotillard", "personagem": "Mal"},
            ],
            "equipe": [
                {"pessoa": "Christopher Nolan", "funcao": "Diretor"},
                {"pessoa": "Christopher Nolan", "funcao": "Roteirista"},
                {"pessoa": "Emma Thomas", "funcao": "Produtor"},
                {"pessoa": "Wally Pfister", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Lee Smith", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "The Matrix",
            "titulo_portugues": "Matrix",
            "ano_lancamento": 1999,
            "duracao_minutos": 136,
            "lancado": True,
            "sinopse": "Um hacker de computador aprende com misteriosos rebeldes sobre a verdadeira natureza de sua realidade e seu papel na guerra contra seus controladores.",
            "generos": ["Ação", "Ficção Científica"],
            "elenco": [
                {"ator": "Keanu Reeves", "personagem": "Neo"},
                {"ator": "Laurence Fishburne", "personagem": "Morpheus"},
                {"ator": "Carrie-Anne Moss", "personagem": "Trinity"},
                {"ator": "Hugo Weaving", "personagem": "Agent Smith"},
                {"ator": "Joe Pantoliano", "personagem": "Cypher"},
            ],
            "equipe": [
                {"pessoa": "Lana Wachowski", "funcao": "Diretor"},
                {"pessoa": "Lilly Wachowski", "funcao": "Diretor"},
                {"pessoa": "Joel Silver", "funcao": "Produtor"},
                {"pessoa": "Bill Pope", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Zach Staenberg", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Forrest Gump",
            "titulo_portugues": "Forrest Gump: O Contador de Histórias",
            "ano_lancamento": 1994,
            "duracao_minutos": 142,
            "lancado": True,
            "sinopse": "As presidências de Kennedy e Johnson, a guerra do Vietnã, o escândalo de Watergate e outros eventos históricos se desenrolam da perspectiva de um homem do Alabama com um QI de 75.",
            "generos": ["Drama", "Romance"],
            "elenco": [
                {"ator": "Tom Hanks", "personagem": "Forrest Gump"},
                {"ator": "Robin Wright", "personagem": "Jenny Curran"},
                {"ator": "Gary Sinise", "personagem": "Lieutenant Dan Taylor"},
                {"ator": "Sally Field", "personagem": "Mrs. Gump"},
                {"ator": "Mykelti Williamson", "personagem": "Bubba Blue"},
            ],
            "equipe": [
                {"pessoa": "Robert Zemeckis", "funcao": "Diretor"},
                {"pessoa": "Wendy Finerman", "funcao": "Produtor"},
                {"pessoa": "Don Burgess", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Arthur Schmidt", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Pulp Fiction",
            "titulo_portugues": "Pulp Fiction: Tempo de Violência",
            "ano_lancamento": 1994,
            "duracao_minutos": 154,
            "lancado": True,
            "sinopse": "As vidas de dois assassinos da máfia, um boxeador, a esposa de um gângster e dois bandidos se entrelaçam em quatro histórias de violência e redenção.",
            "generos": ["Crime", "Drama"],
            "elenco": [
                {"ator": "John Travolta", "personagem": "Vincent Vega"},
                {"ator": "Samuel L. Jackson", "personagem": "Jules Winnfield"},
                {"ator": "Uma Thurman", "personagem": "Mia Wallace"},
                {"ator": "Bruce Willis", "personagem": "Butch Coolidge"},
                {"ator": "Tim Roth", "personagem": "Pumpkin"},
            ],
            "equipe": [
                {"pessoa": "Quentin Tarantino", "funcao": "Diretor"},
                {"pessoa": "Quentin Tarantino", "funcao": "Roteirista"},
                {"pessoa": "Lawrence Bender", "funcao": "Produtor"},
                {"pessoa": "Andrzej Sekula", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Sally Menke", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "The Godfather",
            "titulo_portugues": "O Poderoso Chefão",
            "ano_lancamento": 1972,
            "duracao_minutos": 175,
            "lancado": True,
            "sinopse": "O patriarca envelhecido de uma dinastia do crime organizado transfere o controle de seu império clandestino para seu filho relutante.",
            "generos": ["Crime", "Drama"],
            "elenco": [
                {"ator": "Marlon Brando", "personagem": "Don Vito Corleone"},
                {"ator": "Al Pacino", "personagem": "Michael Corleone"},
                {"ator": "James Caan", "personagem": "Sonny Corleone"},
                {"ator": "Robert Duvall", "personagem": "Tom Hagen"},
                {"ator": "Diane Keaton", "personagem": "Kay Adams"},
            ],
            "equipe": [
                {"pessoa": "Francis Ford Coppola", "funcao": "Diretor"},
                {"pessoa": "Francis Ford Coppola", "funcao": "Roteirista"},
                {"pessoa": "Albert S. Ruddy", "funcao": "Produtor"},
                {"pessoa": "Gordon Willis", "funcao": "Diretor de Fotografia"},
                {"pessoa": "William Reynolds", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Schindler's List",
            "titulo_portugues": "A Lista de Schindler",
            "ano_lancamento": 1993,
            "duracao_minutos": 195,
            "lancado": True,
            "sinopse": "Na Polônia ocupada pelos alemães durante a Segunda Guerra Mundial, o industrial Oskar Schindler gradualmente se preocupa com sua força de trabalho judia depois de testemunhar sua perseguição pelos nazistas.",
            "generos": ["Drama", "Guerra"],
            "elenco": [
                {"ator": "Liam Neeson", "personagem": "Oskar Schindler"},
                {"ator": "Ben Kingsley", "personagem": "Itzhak Stern"},
                {"ator": "Ralph Fiennes", "personagem": "Amon Goeth"},
                {"ator": "Caroline Goodall", "personagem": "Emilie Schindler"},
                {"ator": "Jonathan Sagall", "personagem": "Poldek Pfefferberg"},
            ],
            "equipe": [
                {"pessoa": "Steven Spielberg", "funcao": "Diretor"},
                {"pessoa": "Gerald R. Molen", "funcao": "Produtor"},
                {"pessoa": "Janusz Kaminski", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Michael Kahn", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "The Lord of the Rings: The Return of the King",
            "titulo_portugues": "O Senhor dos Anéis: O Retorno do Rei",
            "ano_lancamento": 2003,
            "duracao_minutos": 201,
            "lancado": True,
            "sinopse": "Gandalf e Aragorn lideram o Mundo dos Homens contra o exército de Sauron para distrair seu olhar de Frodo e Sam enquanto eles se aproximam da Montanha da Perdição com o Um Anel.",
            "generos": ["Aventura", "Drama", "Fantasia"],
            "elenco": [
                {"ator": "Elijah Wood", "personagem": "Frodo Baggins"},
                {"ator": "Ian McKellen", "personagem": "Gandalf"},
                {"ator": "Viggo Mortensen", "personagem": "Aragorn"},
                {"ator": "Sean Astin", "personagem": "Samwise Gamgee"},
                {"ator": "Andy Serkis", "personagem": "Gollum"},
            ],
            "equipe": [
                {"pessoa": "Peter Jackson", "funcao": "Diretor"},
                {"pessoa": "Peter Jackson", "funcao": "Roteirista"},
                {"pessoa": "Barrie M. Osborne", "funcao": "Produtor"},
                {"pessoa": "Andrew Lesnie", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Jamie Selkirk", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Gladiator",
            "titulo_portugues": "Gladiador",
            "ano_lancamento": 2000,
            "duracao_minutos": 155,
            "lancado": True,
            "sinopse": "Um general romano é traído e sua família assassinada pelo filho corrupto do imperador. Ele retorna a Roma como um gladiador para se vingar.",
            "generos": ["Ação", "Aventura", "Drama"],
            "elenco": [
                {"ator": "Russell Crowe", "personagem": "Maximus"},
                {"ator": "Joaquin Phoenix", "personagem": "Commodus"},
                {"ator": "Connie Nielsen", "personagem": "Lucilla"},
                {"ator": "Oliver Reed", "personagem": "Proximo"},
                {"ator": "Richard Harris", "personagem": "Marcus Aurelius"},
            ],
            "equipe": [
                {"pessoa": "Ridley Scott", "funcao": "Diretor"},
                {"pessoa": "Douglas Wick", "funcao": "Produtor"},
                {"pessoa": "John Mathieson", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Pietro Scalia", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Tropa de Elite",
            "titulo_portugues": "Tropa de Elite",
            "ano_lancamento": 2007,
            "duracao_minutos": 115,
            "lancado": True,
            "sinopse": "Em 1997, antes da visita do Papa ao Rio de Janeiro, o Capitão Nascimento do BOPE precisa encontrar um substituto para sua posição enquanto tenta combater o tráfico de drogas nas favelas.",
            "generos": ["Ação", "Crime", "Drama", "Policial"],
            "elenco": [
                {"ator": "Wagner Moura", "personagem": "Capitão Nascimento"},
                {"ator": "Caio Junqueira", "personagem": "Capitão Matias"},
                {"ator": "André Ramiro", "personagem": "André Matias"},
                {"ator": "Fernanda Machado", "personagem": "Maria"},
                {"ator": "Maria Ribeiro", "personagem": "Rosane"},
            ],
            "equipe": [
                {"pessoa": "José Padilha", "funcao": "Diretor"},
                {"pessoa": "José Padilha", "funcao": "Roteirista"},
                {"pessoa": "Marcos Prado", "funcao": "Produtor"},
                {"pessoa": "Lula Carvalho", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Daniel Rezende", "funcao": "Editor"},
            ]
        },
        {
            "titulo_original": "Deus é Brasileiro",
            "titulo_portugues": "Deus é Brasileiro",
            "ano_lancamento": 2003,
            "duracao_minutos": 110,
            "lancado": True,
            "sinopse": "Deus decide tirar férias e precisa encontrar um santo para substituí-lo. Ele viaja pelo Brasil procurando o candidato perfeito.",
            "generos": ["Aventura", "Comédia", "Fantasia"],
            "elenco": [
                {"ator": "Antônio Fagundes", "personagem": "Deus"},
                {"ator": "Paloma Duarte", "personagem": "Madá"},
                {"ator": "Wagner Moura", "personagem": "Taoca"},
                {"ator": "Bruce Gomlevsky", "personagem": "Quinca das Mulas"},
                {"ator": "Stepan Nercessian", "personagem": "Deão"},
            ],
            "equipe": [
                {"pessoa": "Cacá Diegues", "funcao": "Diretor"},
                {"pessoa": "Cacá Diegues", "funcao": "Roteirista"},
                {"pessoa": "Renata Almeida Magalhães", "funcao": "Produtor"},
                {"pessoa": "Breno Silveira", "funcao": "Diretor de Fotografia"},
                {"pessoa": "Sérgio Mekler", "funcao": "Editor"},
            ]
        },
    ]

    filmes = []

    for f_data in filmes_data:
        # Verificar se filme já existe
        filme = Filme.get_first_or_none_by("titulo_original", f_data["titulo_original"])

        if filme:
            print(f"\n  ⊙ {f_data['titulo_original']} (já existe)")
            continue

        # Criar filme
        filme = Filme(
            titulo_original=f_data["titulo_original"],
            titulo_portugues=f_data["titulo_portugues"],
            ano_lancamento=f_data["ano_lancamento"],
            duracao_minutos=f_data["duracao_minutos"],
            lancado=f_data["lancado"],
            sinopse=f_data["sinopse"]
        )
        db.session.add(filme)
        db.session.flush()  # Para obter o ID do filme

        print(f"\n  ✓ {f_data['titulo_original']}")

        # Adicionar gêneros
        for genero_nome in f_data["generos"]:
            genero = generos[genero_nome]
            filme_genero = FilmeGenero(filme_id=filme.id, genero_id=genero.id)
            db.session.add(filme_genero)
        print(f"    Gêneros: {', '.join(f_data['generos'])}")

        # Adicionar elenco
        print(f"    Elenco:")
        for atuacao_data in f_data["elenco"]:
            ator = atores[atuacao_data["ator"]]
            atuacao = Atuacoes(
                filme_id=filme.id,
                ator_id=ator.id,
                personagem=atuacao_data["personagem"]
            )
            db.session.add(atuacao)
            print(f"      • {atuacao_data['ator']} como {atuacao_data['personagem']}")

        # Adicionar equipe técnica
        print(f"    Equipe técnica:")
        for equipe_data in f_data["equipe"]:
            pessoa = pessoas[equipe_data["pessoa"]]
            funcao = funcoes[equipe_data["funcao"]]
            equipe = EquipeTecnica(
                filme_id=filme.id,
                pessoa_id=pessoa.id,
                funcao_id=funcao.id
            )
            db.session.add(equipe)
            print(f"      • {equipe_data['pessoa']} - {equipe_data['funcao']}")

        filmes.append(filme)

    db.session.commit()
    return filmes


def main():
    """Função principal"""
    print("=" * 80)
    print("SEED DE DADOS - MYMOVIEDB")
    print("=" * 80)
    print()

    # Criar app e contexto
    app = create_app()

    with app.app_context():
        try:
            # Criar dados
            generos = criar_generos()
            funcoes = criar_funcoes_tecnicas()
            pessoas, atores = criar_pessoas_e_atores()
            filmes = criar_filmes(generos, pessoas, atores, funcoes)

            print("\n" + "=" * 80)
            print("✅ SEED CONCLUÍDO COM SUCESSO!")
            print("=" * 80)
            print(f"\nResumo:")
            print(f"  • {len(generos)} gêneros")
            print(f"  • {len(funcoes)} funções técnicas")
            print(f"  • {len(pessoas)} pessoas/atores")
            print(f"  • {len(filmes)} filmes")
            print()

        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
