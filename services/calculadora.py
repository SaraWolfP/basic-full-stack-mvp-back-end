import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Any


# ── Value Object ──────────────────────────────────────────────────────────────

@dataclass
class Parcela:
    """
    Representa uma parcela de um financiamento.

    É um Value Object: imutável após criação, sem identidade própria além
    de seus atributos. Usado internamente pelos calculadores e convertido
    para dict apenas na camada de rotas.
    """

    numero_parcela: int
    data_parcela: str
    valor_parcela: float

    def to_dict(self) -> dict[str, Any]:
        """Converte a parcela para dict serializável pelo Flask (jsonify)."""
        return {
            "numero_parcela": self.numero_parcela,
            "data_parcela": self.data_parcela,
            "valor_parcela": self.valor_parcela,
        }


# ── Classe Base Abstrata ──────────────────────────────────────────────────────

class CalculadoraBase(ABC):
    """
    Define a interface e o comportamento comum para todos os modelos de amortização.

    Métodos abstratos:
        calcular_parcelas: geração das parcelas mensais (implementação difere por modelo).
        calcular_saldo_devedor: saldo após k parcelas pagas (fórmula difere por modelo).
        _calcular_novo_prazo: número de meses restantes após amortização 'Prazo'.

    Métodos concretos (herdados sem alteração):
        recalcular_reducao_parcela: mesmo saldo menor, mesmo prazo → chama calcular_parcelas.
        recalcular_reducao_prazo: mesmo PMT/amort_fixa, prazo menor → usa _calcular_novo_prazo.
        reconstruir_todas_parcelas: reconstrói histórico completo após deleção de amortização.
    """

    def __init__(self, taxa_mensal: float) -> None:
        """
        Args:
            taxa_mensal: taxa de juros mensal em decimal (ex: 0.0089 para 0,89% a.m.).
        """
        self._taxa = taxa_mensal

    # ── Métodos abstratos (cada subclasse implementa à sua maneira) ───────────

    @abstractmethod
    def calcular_parcelas(
        self,
        valor_financiado: float,
        prazo_meses: int,
        data_inicio: str,
        parcela_inicial: int = 1,
    ) -> list[Parcela]:
        """
        Gera a lista de parcelas para um dado saldo devedor e prazo.

        Args:
            valor_financiado: saldo devedor no início do segmento.
            prazo_meses: número de parcelas a gerar.
            data_inicio: data da primeira parcela no formato 'YYYY-MM'.
            parcela_inicial: número sequencial da primeira parcela.

        Returns:
            Lista de Parcela ordenada cronologicamente.
        """

    @abstractmethod
    def calcular_saldo_devedor(
        self,
        valor_segmento: float,
        prazo_segmento: int,
        parcelas_pagas: int,
    ) -> float:
        """
        Calcula o saldo devedor após k parcelas pagas dentro de um segmento.

        Recebe os valores do segmento atual (não necessariamente os originais
        do financiamento), o que permite calcular corretamente após múltiplas
        amortizações extras encadeadas.

        Args:
            valor_segmento: PV do segmento atual.
            prazo_segmento: n do segmento atual.
            parcelas_pagas: quantas parcelas foram pagas neste segmento.

        Returns:
            Saldo devedor arredondado em 2 casas.
        """

    @abstractmethod
    def _calcular_novo_prazo(
        self,
        saldo_devedor: float,
        pmt_atual: float,
        saldo_antes: float,
    ) -> int:
        """
        Calcula o novo número de meses após uma amortização do tipo 'Prazo'.

        Cada modelo usa uma fórmula diferente para encontrar o prazo que
        mantém o valor da parcela (PRICE) ou a amortização fixa (SAC).

        Args:
            saldo_devedor: saldo após a amortização extra.
            pmt_atual: valor da primeira parcela afetada (antes da amortização).
            saldo_antes: saldo imediatamente antes da amortização extra.

        Returns:
            Novo número de meses (inteiro, arredondado para cima).
        """

    # ── Métodos concretos (comportamento comum a todos os modelos) ────────────

    def recalcular_reducao_parcela(
        self,
        saldo_devedor: float,
        prazo_restante: int,
        data_inicio: str,
        parcela_inicial: int,
    ) -> list[Parcela]:
        """
        Recalcula parcelas mantendo o prazo e reduzindo o valor da parcela.

        Basta recalcular com o novo saldo e o mesmo prazo: o dispatcher
        calcular_parcelas já lida com PRICE e SAC corretamente.

        Args:
            saldo_devedor: saldo após a amortização extra.
            prazo_restante: número de meses que restavam antes da amortização.
            data_inicio: data da primeira parcela recalculada.
            parcela_inicial: número sequencial da primeira parcela recalculada.

        Returns:
            Lista de Parcela com novo valor menor.
        """
        return self.calcular_parcelas(
            saldo_devedor, prazo_restante, data_inicio, parcela_inicial
        )

    def recalcular_reducao_prazo(
        self,
        saldo_devedor: float,
        data_inicio: str,
        parcela_inicial: int,
        pmt_atual: float,
        saldo_antes: float,
    ) -> list[Parcela]:
        """
        Recalcula parcelas mantendo o valor da parcela e reduzindo o prazo.

        Delega o cálculo do novo prazo para _calcular_novo_prazo (polimórfico),
        depois gera as parcelas com o mesmo PMT/amort_fixa e o prazo menor.

        Args:
            saldo_devedor: saldo após a amortização extra.
            data_inicio: data da primeira parcela recalculada.
            parcela_inicial: número sequencial da primeira parcela recalculada.
            pmt_atual: valor da parcela a manter (PRICE) ou base para amort_fixa (SAC).
            saldo_antes: saldo antes da amortização extra.

        Returns:
            Lista de Parcela com mesmo valor e prazo reduzido.
        """
        novo_prazo = self._calcular_novo_prazo(saldo_devedor, pmt_atual, saldo_antes)
        return self._gerar_parcelas_pos_reducao_prazo(
            saldo_devedor, novo_prazo, data_inicio, parcela_inicial, pmt_atual, saldo_antes
        )

    @abstractmethod
    def _gerar_parcelas_pos_reducao_prazo(
        self,
        saldo_devedor: float,
        novo_prazo: int,
        data_inicio: str,
        parcela_inicial: int,
        pmt_atual: float,
        saldo_antes: float,
    ) -> list[Parcela]:
        """
        Gera as parcelas após redução de prazo com o novo prazo já calculado.

        Separado de recalcular_reducao_prazo porque PRICE e SAC usam
        estratégias diferentes de geração (fixo vs. decrescente).
        """

    def reconstruir_todas_parcelas(
        self,
        financiamento: dict,
        amortizacoes: list[dict],
    ) -> list[Parcela]:
        """
        Reconstrói o histórico completo de parcelas aplicando amortizações em
        ordem cronológica sobre segmentos encadeados.

        Algoritmo por segmento (corrige bug de usar valor_original global):
            Para cada amortização:
                1. Gera as parcelas do segmento atual com saldo e prazo DO SEGMENTO.
                2. Adiciona ao resultado as parcelas anteriores à amortização.
                3. Calcula saldo_antes usando os valores DO SEGMENTO (não os originais).
                4. Aplica a amortização e determina o próximo segmento.
            Ao final, gera e adiciona as parcelas do último segmento.

        Usar sempre valor_original e prazo_total para calcular saldo seria
        incorreto com múltiplas amortizações, pois ignora que o segmento atual
        pode ter prazo e PV diferentes do financiamento original.

        Args:
            financiamento: dict com os campos do registro Financiamentos.
            amortizacoes: lista de AmortizacoesExtras restantes (qualquer ordem).

        Returns:
            Lista completa de Parcela reconstruída.
        """
        valor_original = financiamento["valor_imovel"] - financiamento["entrada"]

        saldo_segmento = valor_original
        prazo_segmento = financiamento["prazo_meses"]
        data_segmento  = financiamento["data_inicio"]
        parcela_num    = 1
        resultado: list[Parcela] = []

        for amort in sorted(amortizacoes, key=lambda a: a["data_amortizacao"]):
            data_amort = amort["data_amortizacao"]

            parcelas_segmento = self.calcular_parcelas(
                saldo_segmento, prazo_segmento, data_segmento, parcela_num
            )

            antes    = [p for p in parcelas_segmento if p.data_parcela < data_amort]
            afetadas = [p for p in parcelas_segmento if p.data_parcela >= data_amort]

            if not afetadas:
                resultado.extend(parcelas_segmento)
                continue

            resultado.extend(antes)
            n_antes = len(antes)

            saldo_antes = self.calcular_saldo_devedor(
                saldo_segmento, prazo_segmento, n_antes
            )
            saldo_depois  = round(saldo_antes - amort["valor_amortizado"], 2)
            prazo_restante = prazo_segmento - n_antes
            pmt_atual     = afetadas[0].valor_parcela

            parcela_num   += n_antes
            data_segmento  = data_amort

            if amort["tipo_amortizacao"] == "Prazo":
                novo_prazo     = self._calcular_novo_prazo(saldo_depois, pmt_atual, saldo_antes)
                saldo_segmento = saldo_depois
                prazo_segmento = novo_prazo
            else:
                saldo_segmento = saldo_depois
                prazo_segmento = prazo_restante

        parcelas_finais = self.calcular_parcelas(
            saldo_segmento, prazo_segmento, data_segmento, parcela_num
        )
        resultado.extend(parcelas_finais)
        return resultado

    # ── Helpers protegidos (reutilizados pelas subclasses) ────────────────────

    def _gerar_parcelas_fixas(
        self,
        pmt: float,
        n: int,
        data_inicio: str,
        parcela_inicial: int,
    ) -> list[Parcela]:
        """Gera N parcelas de valor fixo, incrementando a data mês a mês."""
        ano, mes = map(int, data_inicio.split("-"))
        data_atual = date(ano, mes, 1)
        parcelas: list[Parcela] = []
        for i in range(n):
            parcelas.append(Parcela(
                numero_parcela=parcela_inicial + i,
                data_parcela=data_atual.strftime("%Y-%m"),
                valor_parcela=round(pmt, 2),
            ))
            data_atual += relativedelta(months=1)
        return parcelas


# ── Subclasse PRICE ───────────────────────────────────────────────────────────

class CalculadoraPrice(CalculadoraBase):
    """
    Implementa o sistema PRICE (Sistema Francês de Amortização).

    Característica principal: parcela fixa ao longo de todo o contrato.
    Os juros são maiores no início e decrescem; a amortização de principal
    é menor no início e cresce — mas a soma (parcela) é sempre igual.
    """

    def calcular_parcelas(
        self,
        valor_financiado: float,
        prazo_meses: int,
        data_inicio: str,
        parcela_inicial: int = 1,
    ) -> list[Parcela]:
        """
        Calcula parcelas fixas pelo sistema PRICE.

        Fórmula: PMT = PV * [i * (1+i)^n] / [(1+i)^n - 1]
        """
        if self._taxa == 0:
            pmt = valor_financiado / prazo_meses
        else:
            fator = (1 + self._taxa) ** prazo_meses
            pmt = valor_financiado * (self._taxa * fator) / (fator - 1)

        return self._gerar_parcelas_fixas(pmt, prazo_meses, data_inicio, parcela_inicial)

    def calcular_saldo_devedor(
        self,
        valor_segmento: float,
        prazo_segmento: int,
        parcelas_pagas: int,
    ) -> float:
        """
        Calcula saldo devedor PRICE analiticamente.

        Fórmula: SD_k = PV * [(1+i)^n - (1+i)^k] / [(1+i)^n - 1]
        """
        if self._taxa == 0:
            return round(valor_segmento * (1 - parcelas_pagas / prazo_segmento), 2)
        fator_total = (1 + self._taxa) ** prazo_segmento
        fator_pago  = (1 + self._taxa) ** parcelas_pagas
        return round(
            valor_segmento * (fator_total - fator_pago) / (fator_total - 1), 2
        )

    def _calcular_novo_prazo(
        self,
        saldo_devedor: float,
        pmt_atual: float,
        saldo_antes: float,
    ) -> int:
        """
        Inverte a fórmula PRICE para encontrar o prazo que mantém o PMT.

        n = ceil( log(PMT / (PMT - saldo * i)) / log(1 + i) )
        """
        if self._taxa == 0:
            return math.ceil(saldo_devedor / pmt_atual)
        return math.ceil(
            math.log(pmt_atual / (pmt_atual - saldo_devedor * self._taxa))
            / math.log(1 + self._taxa)
        )

    def _gerar_parcelas_pos_reducao_prazo(
        self,
        saldo_devedor: float,
        novo_prazo: int,
        data_inicio: str,
        parcela_inicial: int,
        pmt_atual: float,
        saldo_antes: float,
    ) -> list[Parcela]:
        """No PRICE, parcelas continuam fixas com o mesmo PMT e novo prazo."""
        return self._gerar_parcelas_fixas(pmt_atual, novo_prazo, data_inicio, parcela_inicial)


# ── Subclasse SAC ─────────────────────────────────────────────────────────────

class CalculadoraSAC(CalculadoraBase):
    """
    Implementa o SAC (Sistema de Amortização Constante).

    Característica principal: amortização de principal fixa.
    As parcelas são decrescentes porque os juros caem junto com o saldo devedor.
    """

    def calcular_parcelas(
        self,
        valor_financiado: float,
        prazo_meses: int,
        data_inicio: str,
        parcela_inicial: int = 1,
    ) -> list[Parcela]:
        """
        Calcula parcelas decrescentes pelo sistema SAC.

        Fórmulas:
            amortizacao_fixa = PV / n
            juros_k          = saldo_k * i
            parcela_k        = amortizacao_fixa + juros_k
        """
        amort_fixa = valor_financiado / prazo_meses
        saldo = valor_financiado
        ano, mes = map(int, data_inicio.split("-"))
        data_atual = date(ano, mes, 1)
        parcelas: list[Parcela] = []

        for i in range(prazo_meses):
            parcelas.append(Parcela(
                numero_parcela=parcela_inicial + i,
                data_parcela=data_atual.strftime("%Y-%m"),
                valor_parcela=round(amort_fixa + saldo * self._taxa, 2),
            ))
            saldo -= amort_fixa
            data_atual += relativedelta(months=1)

        return parcelas

    def calcular_saldo_devedor(
        self,
        valor_segmento: float,
        prazo_segmento: int,
        parcelas_pagas: int,
    ) -> float:
        """
        Calcula saldo devedor SAC.

        No SAC a amortização é constante, logo o saldo cai linearmente:
            SD_k = PV - (PV / n) * k
        """
        amort_fixa = valor_segmento / prazo_segmento
        return round(valor_segmento - amort_fixa * parcelas_pagas, 2)

    def _calcular_novo_prazo(
        self,
        saldo_devedor: float,
        pmt_atual: float,
        saldo_antes: float,
    ) -> int:
        """
        Encontra o novo prazo mantendo a amortização fixa do segmento.

        amort_fixa = pmt_atual - juros_do_mes = pmt_atual - saldo_antes * i
        n_novo     = ceil(saldo_devedor / amort_fixa)
        """
        amort_fixa = pmt_atual - saldo_antes * self._taxa
        if amort_fixa <= 0:
            return 1
        return math.ceil(saldo_devedor / amort_fixa)

    def _gerar_parcelas_pos_reducao_prazo(
        self,
        saldo_devedor: float,
        novo_prazo: int,
        data_inicio: str,
        parcela_inicial: int,
        pmt_atual: float,
        saldo_antes: float,
    ) -> list[Parcela]:
        """
        No SAC, após redução de prazo as parcelas continuam decrescentes
        mas com a mesma amortização fixa do segmento anterior.
        """
        amort_fixa = pmt_atual - saldo_antes * self._taxa
        if amort_fixa <= 0:
            amort_fixa = saldo_devedor

        saldo = saldo_devedor
        ano, mes = map(int, data_inicio.split("-"))
        data_atual = date(ano, mes, 1)
        parcelas: list[Parcela] = []

        for i in range(novo_prazo):
            parcelas.append(Parcela(
                numero_parcela=parcela_inicial + i,
                data_parcela=data_atual.strftime("%Y-%m"),
                valor_parcela=round(amort_fixa + saldo * self._taxa, 2),
            ))
            saldo -= amort_fixa
            data_atual += relativedelta(months=1)

        return parcelas


# ── Factory ───────────────────────────────────────────────────────────────────

def criar_calculadora(modelo: str, taxa_mensal: float) -> CalculadoraBase:
    """
    Instancia e retorna o calculador correto para o modelo informado.

    Isola as rotas de saber quais subclasses existem (princípio Open/Closed):
    para adicionar um novo modelo no futuro basta criar uma nova subclasse
    e registrá-la aqui, sem alterar nenhuma rota.

    Args:
        modelo: 'PRICE' ou 'SAC'.
        taxa_mensal: taxa mensal em percentual (ex: 0.89); convertida para
                     decimal internamente.

    Returns:
        Instância de CalculadoraPrice ou CalculadoraSAC.

    Raises:
        ValueError: se o modelo não for reconhecido.
    """
    taxa_decimal = taxa_mensal / 100
    if modelo == "PRICE":
        return CalculadoraPrice(taxa_decimal)
    if modelo == "SAC":
        return CalculadoraSAC(taxa_decimal)
    raise ValueError(f"Modelo '{modelo}' inválido. Use 'PRICE' ou 'SAC'.")
