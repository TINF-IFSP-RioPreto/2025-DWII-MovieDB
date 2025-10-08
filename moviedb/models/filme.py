import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from moviedb import db
from .mixins import AuditMixin, BasicRepositoryMixin


class Filme(db.Model, BasicRepositoryMixin, AuditMixin):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    titulo_original: Mapped[str] = mapped_column(String(100))
    titulo_portugues: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    ano_lancamento: Mapped[Optional[int]] = mapped_column(default=None)
    lancado: Mapped[bool] = mapped_column(default=False, server_default='false')
    duracao_minutos: Mapped[Optional[int]] = mapped_column(default=None)
    sinopse: Mapped[Optional[str]] = mapped_column(Text, default=None)
    poster_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    poster_mime: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    orcamento_milhares: Mapped[Optional[Decimal]] = mapped_column(
            DECIMAL(precision=10, scale=2),
            default=None
    )
    receita_lancamento_milhares: Mapped[Optional[Decimal]] = mapped_column(
            DECIMAL(precision=10, scale=2),
            default=None
    )
    link_trailer: Mapped[Optional[str]] = mapped_column(String(200), default=None)

    # Relacionamentos: um filme pode ter vários atores e membros da equipe técnica
    atuacoes: Mapped[list["Atuacoes"]] = relationship(back_populates="filme",
                                                      cascade="all, delete-orphan")
    equipes_tecnicas: Mapped[list["EquipeTecnica"]] = relationship(back_populates="filme",
                                                                   cascade="all, delete-orphan")

    # Relacionamentos: um filme pode ter vários gêneros (via tabela de associação)
    filme_generos: Mapped[list["FilmeGenero"]] = relationship(back_populates="filme",
                                                              cascade="all, delete-orphan")

    # Relacionamentos: um filme pode ter várias avaliações de usuários
    avaliacoes: Mapped[list["Avaliacao"]] = relationship(back_populates="filme",
                                                         cascade="all, delete-orphan")


class Genero(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'generos'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, default=None)
    ativo: Mapped[bool] = mapped_column(default=True, server_default='true')

    # Relacionamentos: um gênero pode estar associado a vários filmes (via tabela de associação)
    filme_generos: Mapped[list["FilmeGenero"]] = relationship(back_populates="genero",
                                                              cascade="all, delete-orphan")


class FuncoesTecnicas(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'funcoes_tecnicas'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, default=None)
    ativa: Mapped[bool] = mapped_column(default=True, server_default='true')

    # Relacionamentos: uma função técnica pode ser usada em várias equipes técnicas
    equipes_tecnicas: Mapped[list["EquipeTecnica"]] = relationship(back_populates="funcao",
                                                                   cascade="all, delete-orphan")
