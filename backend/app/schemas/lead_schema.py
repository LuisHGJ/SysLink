"""Schemas Pydantic para leads — validação de entrada/saída."""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StatusEnum(str, Enum):
    nao_contatado = "Não contatado"
    aguardando_resposta = "Aguardando resposta"
    negociando = "Negociando"
    negado = "Negado"
    fechado = "Fechado"
    em_desenvolvimento = "Em desenvolvimento"
    finalizado = "Finalizado"


class DificuldadeEnum(str, Enum):
    facil = "Fácil"
    medio = "Médio"
    dificil = "Difícil"


class ProdutoEnum(str, Enum):
    portfolio = "Portfólio"
    pagina_venda = "Página de vendas"
    sistema = "Sistema"
    link_tree = "Link Tree"


class LeadBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    empresa: str | None = Field(None, max_length=255)
    contato: str | None = Field(None, max_length=255)
    instagram: str | None = Field(None, max_length=255)
    produto: ProdutoEnum
    dificuldade: DificuldadeEnum
    status: StatusEnum = StatusEnum.nao_contatado
    motivo_perda: str | None = Field(None, max_length=2000)
    ultimo_contato: str | None = Field(None, max_length=30)
    arquivos: list[str] = Field(default_factory=list)


class LeadCreate(LeadBase):
    model_config = ConfigDict(extra="forbid")


class LeadUpdate(LeadBase):
    model_config = ConfigDict(extra="forbid")


class LeadPatch(BaseModel):
    """Atualização parcial — apenas campos informados são alterados."""
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(None, min_length=1, max_length=255)
    empresa: str | None = Field(None, max_length=255)
    contato: str | None = Field(None, max_length=255)
    instagram: str | None = Field(None, max_length=255)
    produto: ProdutoEnum | None = None
    dificuldade: DificuldadeEnum | None = None
    status: StatusEnum | None = None
    motivo_perda: str | None = Field(None, max_length=2000)
    ultimo_contato: str | None = Field(None, max_length=30)
    arquivos: list[str] | None = None


class LeadResponse(LeadBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
