import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from moviedb import db
from .mixins import AuditMixin, BasicRepositoryMixin


class Atuacoes(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'atuacoes'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filme.id'))
    ator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('atores.id'))
    personagem: Mapped[str] = mapped_column(String(100), default="as him/herself",
                                            server_default="as him/herself")

    filme: Mapped["Filme"] = relationship(back_populates="atuacoes")
    ator: Mapped["Ator"] = relationship(back_populates="atuacoes")

    __table_args__ = (
        UniqueConstraint('filme_id', 'ator_id', 'personagem', name='uq_filme_ator_personagem'),
    )


class EquipeTecnica(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'equipes_tecnicas'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filme.id'))
    pessoa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('pessoas.id'))
    funcao_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('funcoes_tecnicas.id'))

    filme: Mapped["Filme"] = relationship(back_populates="equipes_tecnicas")
    pessoa: Mapped["Pessoa"] = relationship(back_populates="equipes_tecnicas")
    funcao: Mapped["FuncoesTecnicas"] = relationship(back_populates="equipes_tecnicas")

    __table_args__ = (
        UniqueConstraint('filme_id', 'pessoa_id', 'funcao_id', name='uq_filme_pessoa_funcao'),
    )


class FilmeGenero(db.Model, BasicRepositoryMixin, AuditMixin):
    """Tabela de associação many-to-many entre Filme e Genero"""
    __tablename__ = 'filme_genero'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filme.id'))
    genero_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('generos.id'))

    # Relacionamentos: tabela de associação
    filme: Mapped["Filme"] = relationship(back_populates="filme_generos")
    genero: Mapped["Genero"] = relationship(back_populates="filme_generos")

    __table_args__ = (
        UniqueConstraint('filme_id', 'genero_id', name='uq_filme_genero'),
    )


class Avaliacao(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'avaliacoes'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filme_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('filme.id'))
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('usuarios.id'))
    nota: Mapped[int] = mapped_column(default=1)
    comentario: Mapped[Optional[str]] = mapped_column(Text, default=None)
    recomenda: Mapped[bool] = mapped_column(default=False, server_default='false')

    filme: Mapped["Filme"] = relationship(back_populates="avaliacoes")
    usuario: Mapped["User"] = relationship(back_populates="avaliacoes")

    __table_args__ = (
        UniqueConstraint('filme_id', 'usuario_id', name='uq_filme_usuario_avaliacao'),
    )
