from dataclasses import dataclass
from dateutil.relativedelta import relativedelta
from datetime import date
from abc import ABC, abstractmethod

@dataclass
class Financiamento:
    nome: str
    valor_imovel: float
    entrada: float
    taxa_juros: float
    prazo_meses: int
    data_inicio: str
    modelo: str

    @property
    def valor_financiado(self) -> float:
        return self.valor_imovel - self.entrada

    def to_dict(self) -> dict:
        return {
            "nome": self.nome,
            "valor_imovel": self.valor_imovel,
            "entrada": self.entrada,
            "taxa_juros": self.taxa_juros,
            "prazo_meses": self.prazo_meses,
            "data_inicio": self.data_inicio,
            "modelo": self.modelo,
        }

@dataclass
class Parcela:
    numero_parcela: int
    data_parcela: str
    valor_parcela: float

    def to_dict(self) -> dict:
        return {
            "numero_parcela": self.numero_parcela,
            "data_parcela":   self.data_parcela,
            "valor_parcela":  self.valor_parcela,
        }

@dataclass
class AmortizacaoExtra:
    valor_amortizado: float
    data_amortizacao: str
    tipo: str


    def to_dict(self) -> dict:
        return {
            "valor_amortizado": self.valor_amortizado,
            "data_amortizacao": self.data_amortizacao,
            "tipo": self.tipo,
        }


class Calculadora(ABC):
    @abstractmethod
    def calcular_parcelas(self, saldo_devedor: float, data_inicio: str, prazo_meses: int, taxa_juros: float) -> list[Parcela]:
        pass

    @abstractmethod
    def recalcular_parcelas(self, financiamento: 'Financiamento', amortizacao_extra: 'AmortizacaoExtra') -> list[Parcela]:
        pass

    @abstractmethod
    def reconstruir_parcelas(self, financiamento: 'Financiamento', amortizacoes: list['AmortizacaoExtra']) -> list[Parcela]:
        pass

class CalculadoraSac(Calculadora):

    def calcular_parcelas(self, valor_financiado: float, data_inicio: str, prazo_meses: int, taxa_juros: float) -> list[Parcela]:
        """
        Calcula as parcelas do financiamento pelo sistema SAC.

        Argumentos:
            valor_financiado: saldo devedor inicial (valor_imovel - entrada).
            data_inicio: data da primeira parcela no formato 'YYYY-MM'.
            prazo_meses: número total de parcelas.
            taxa_juros: taxa mensal em decimal (ex: 0.0089 para 0,89% a.m.).

        Retorna:
            Lista de Parcela ordenada cronologicamente.
        """
        parcelas = []
        amortizacao_mensal = valor_financiado / prazo_meses
        saldo_devedor = valor_financiado

        # date.fromisoformat requer dia — separamos manualmente pois data_inicio é 'YYYY-MM'
        ano, mes = map(int, data_inicio.split("-"))
        data_atual = date(ano, mes, 1)

        for i in range(prazo_meses):
            juros = saldo_devedor * taxa_juros
            valor_parcela = amortizacao_mensal + juros
            parcelas.append(Parcela(
                numero_parcela=i + 1,
                data_parcela=data_atual.strftime("%Y-%m"),
                valor_parcela=round(valor_parcela, 2),
            ))
            saldo_devedor -= amortizacao_mensal
            data_atual += relativedelta(months=1)

        return parcelas


def criar_calculadora(modelo: str) -> Calculadora:
    """
    Instancia e retorna o calculador correto para o modelo informado.

    Argumentos:
        modelo: 'SAC' ou 'PRICE' (PRICE ainda não implementado).

    Retorna:
        Instância de Calculadora correspondente ao modelo.

    Lança:
        ValueError: se o modelo não for reconhecido.
    """
    if modelo == "SAC":
        return CalculadoraSac()
    raise ValueError(f"Modelo '{modelo}' ainda não suportado.")
