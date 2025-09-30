import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Self, Union

import sqlalchemy as sa
from flask import current_app
from sqlalchemy import DateTime, func, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Mapped, mapped_column

from moviedb import db


class BasicRepositoryMixin:
    """Mixin básico para repositórios SQLAlchemy.

    Fornece métodos utilitários para operações comuns de consulta.
    """

    @classmethod
    def count_all(cls) -> int:
        """Conta todos os registros na tabela associada à classe.

        Returns:
            int: Número total de registros.
        """
        sentenca = sa.select(sa.func.count()).select_from(cls)
        return db.session.scalar(sentenca) or 0

    @classmethod
    def is_empty(cls) -> bool:
        """Verifica se a tabela associada à classe está vazia.

        Returns:
            bool: True se não houver registros, False caso contrário.
        """
        return cls.count_all() == 0

    @classmethod
    def get_by_id(cls, cls_id) -> Optional[Self]:
        """Busca um registro pelo seu ID.

        Args:
            cls_id: O identificador do registro (UUID ou outro tipo).

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.
        """
        try:
            obj_id = uuid.UUID(str(cls_id)) if cls_id is not None else None
            if obj_id is None:
                return None
            return db.session.get(cls, obj_id)
        except (ValueError, SQLAlchemyError) as e:
            current_app.logger.error("Erro ao buscar por ID: %s"% (str(e)))
            return None

    @classmethod
    def get_top_n(cls,
                  top_n: int = -1,
                  order_by: Optional[str] = None) -> ScalarResult[Self]:
        """Retorna os top N registros, opcionalmente ordenados por um atributo.

        Args:
            top_n (int): Número de registros a retornar. Se -1, retorna todos.
            order_by (typing.Optional[str]): Nome do atributo para ordenação.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.
        """
        sentenca = sa.select(cls)
        if order_by is not None and hasattr(cls, order_by):
            sentenca = sentenca.order_by(getattr(cls, order_by))
        if top_n > 0:
            sentenca = sentenca.limit(top_n)
        return db.session.scalars(sentenca)

    @classmethod
    def get_all(cls,
                order_by: Optional[str] = None) -> ScalarResult[Self]:
        """Retorna todos os registros, opcionalmente ordenados por um atributo.

        Args:
            order_by (typing.Optional[str]): Nome do atributo para ordenação.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.
        """
        sentenca = sa.select(cls)
        if order_by is not None and hasattr(cls, order_by):
            sentenca = sentenca.order_by(getattr(cls, order_by))
        return db.session.scalars(sentenca)

    @classmethod
    def get_all_by(cls,
                   criteria: Dict[str, Any] = None,
                   order_by: Optional[str] = None) -> ScalarResult[Self]:
        """Retorna todos os registros filtrados, opcionalmente ordenados por um atributo.

        Args:
            criteria (typing.Dict[str, typing.Any]): Dicionário com critérios de filtro
                (atributo: valor).
            order_by (typing.Optional[str]): Nome do atributo para ordenação.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias.
        """
        sentenca = sa.select(cls)
        if criteria is not None:
            for k, v in criteria.items():
                if hasattr(cls, k):
                    if isinstance(v, bool):
                        sentenca = sentenca.where(getattr(cls, k).is_(v))
                    else:
                        sentenca = sentenca.where(getattr(cls, k) == v)
        if order_by is not None and hasattr(cls, order_by):
            sentenca = sentenca.order_by(getattr(cls, order_by))
        return db.session.scalars(sentenca)

    @classmethod
    def get_by_composed_id(cls,
                           cls_dict_id: Dict[str, Any]) -> Optional[Self]:
        """Busca um registro por um ID composto.

        Args:
            cls_dict_id (typing.Dict[str, typing.Any]): Dicionário com os campos do ID composto.

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.
        """
        for k, v in cls_dict_id.items():
            try:
                cls_dict_id[k] = uuid.UUID(str(v))
            except ValueError:
                cls_dict_id[k] = v
        return db.session.get(cls, cls_dict_id)

    @classmethod
    def get_first_or_none_by(cls,
                             atributo: str,
                             valor: Union[str, int, uuid.UUID],
                             casesensitive: bool = True) -> Optional[Self]:
        """Busca o primeiro registro que corresponde ao valor de um atributo.

        Args:
            atributo (str): Nome do atributo para busca.
            valor (typing.Union[str, int, uuid.UUID]): Valor a ser buscado.
            casesensitive (bool): Se a busca deve ser case sensitive.

        Returns:
            typing.Optional[typing.Self]: Instância encontrada ou None.

        Raises:
            TypeError: Se a busca for case insensitive e o valor não for str.
        """
        registro = None
        if hasattr(cls, atributo):
            sentenca = sa.select(cls)
            if casesensitive:
                sentenca = sentenca.where(getattr(cls, atributo) == valor)
            else:
                if isinstance(valor, str):
                    # noinspection PyTypeChecker
                    sentenca = sentenca.where(
                            sa.func.lower(getattr(cls, atributo)) == sa.func.lower(valor))
                else:
                    raise TypeError("Para a operação case insensitive, o "
                                    f"atributo \"{atributo}\" deve ser da classe str")
            sentenca = sentenca.limit(1)
            registro = db.session.scalar(sentenca)
        return registro

    @classmethod
    def get_page(cls,
                 page: int = 1,
                 page_size: int = 10,
                 order_by: Optional[str] = None) -> ScalarResult[Self]:
        """Retorna uma página de registros, com paginação e ordenação opcional.

        Args:
            page (int): Número da página (começa em 1).
            page_size (int): Número de registros por página (default: 10).
            order_by (typing.Optional[str]): Nome do atributo para ordenação.

        Returns:
            sqlalchemy.ScalarResult[typing.Self]: Iterável de instâncias na página.
        """
        page = max(1, min(page, 10000))
        page_size = max(1, min(page_size, 1000))

        sentenca = sa.select(cls)
        if order_by is not None and hasattr(cls, order_by):
            sentenca = sentenca.order_by(getattr(cls, order_by))
        sentenca = sentenca.offset((page - 1) * page_size).limit(page_size)
        return db.session.scalars(sentenca)


class AuditMixin:
    """Mixin para adicionar campos de auditoria a modelos SQLAlchemy.

    Adiciona campos de criação e atualização automaticamente gerenciados.
    """
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(),
                                                 onupdate=func.now())
