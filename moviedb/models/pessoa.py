import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from moviedb import db
from .mixins import AuditMixin, BasicRepositoryMixin


class Pessoa(db.Model, BasicRepositoryMixin, AuditMixin):
    __tablename__ = 'pessoas'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(60))
    nacionalidade: Mapped[Optional[str]] = mapped_column(String(60), default=None)
    dta_nascimento: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                               default=None)
    foto_base64: Mapped[Optional[str]] = mapped_column(Text, default=None)
    foto_mime: Mapped[Optional[str]] = mapped_column(String(32), default=None)
    biografia: Mapped[Optional[str]] = mapped_column(Text, default=None)
    e_ator: Mapped[bool] = mapped_column(default=False, server_default='false')
    sexo: Mapped[Optional[str]] = mapped_column(String(1), default=None)

    # Relacionamentos: uma pessoa pode trabalhar em vários filmes como equipe técnica
    equipes_tecnicas: Mapped[list["EquipeTecnica"]] = relationship(back_populates="pessoa",
                                                                   cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_on'      : e_ator,
        'polymorphic_identity': False,
        'with_polymorphic'    : '*'
    }


class Ator(Pessoa):
    __tablename__ = 'atores'
    id: Mapped[uuid.UUID] = mapped_column(ForeignKey('pessoas.id'), primary_key=True)
    nome_artistico: Mapped[Optional[str]] = mapped_column(String(60), default=None)

    # Relacionamentos: um ator pode atuar em vários filmes
    atuacoes: Mapped[list["Atuacoes"]] = relationship(back_populates="ator",
                                                      cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': True,
    }
