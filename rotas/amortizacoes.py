from datetime import datetime
from sqlite3 import IntegrityError

import banco_de_dados as bd

from flask import Blueprint, jsonify, request
from servicos.calculadora import AmortizacaoExtra, Financiamento, criar_calculadora

bp = Blueprint('amortizacoes', __name__, url_prefix='/financiamento')

@bp.route('/<int:id_financiamento>/amortizacoes', methods=['POST'])
def criar_amortizacao_extra(id_financiamento: int):
    """
    Cria uma nova amortização extra e reconstrói as parcelas do financiamento.
    ---
    tags:
      - Amortizações Extras
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [valor_amortizado, data_amortizacao, tipo]
          properties:
            valor_amortizado: { type: number,  example: 50000 }
            data_amortizacao: { type: string,  example: "2026-01" }
            tipo:             { type: string,  enum: [PARCELA, PRAZO], example: PARCELA }
    responses:
      201: { description: Amortização criada e parcelas recalculadas. }
      400: { description: Dados inválidos ou ausentes. }
      404: { description: Financiamento não encontrado. }
      409: { description: Já existe uma amortização nesta data. }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição ausente ou inválido."}), 400

    # verifica campos obrigatórios
    campos_obrigatorios = ['valor_amortizado', 'data_amortizacao', 'tipo']
    faltando = [c for c in campos_obrigatorios if c not in dados]
    if faltando:
        return jsonify({"erro": f"Campos obrigatórios ausentes: {faltando}"}), 400

    if dados.get('tipo') not in ['PARCELA', 'PRAZO']:
        return jsonify({"erro": "tipo deve ser 'PARCELA' ou 'PRAZO'."}), 400

    if dados.get('tipo') == 'PRAZO':
        return jsonify({"erro": "Amortizações por prazo ainda não suportadas."}), 400

    # valida tipos numéricos    
    try:
        valor_amortizado = float(dados['valor_amortizado'])
    except (ValueError, TypeError):
        return jsonify({"erro": "valor_amortizado deve ser um número."}), 400

    if valor_amortizado <= 0:
        return jsonify({"erro": "valor_amortizado deve ser positivo."}), 400

    # valida formato de data_amortizacao
    try:
        datetime.strptime(dados['data_amortizacao'], "%Y-%m")
    except ValueError:
        return jsonify({"erro": "data_amortizacao deve estar no formato 'YYYY-MM' (ex: '2025-01')."}), 400

    conn = bd.conecta_db()

    resultado = bd.obtem_dados(conn, 'Financiamentos', coluna='id', valor=id_financiamento)
    if not resultado:
        conn.close()
        return jsonify({"erro": "Financiamento não encontrado."}), 404

    dados_financiamento = resultado[0]
    financiamento = Financiamento(
        nome=dados_financiamento['nome'],
        valor_imovel=dados_financiamento['valor_imovel'],
        entrada=dados_financiamento['entrada'],
        taxa_juros=dados_financiamento['taxa_juros'],
        prazo_meses=dados_financiamento['prazo_meses'],
        data_inicio=dados_financiamento['data_inicio'],
        modelo=dados_financiamento['modelo'],
    )

    # persiste a nova amortização
    amortizacao = AmortizacaoExtra(
        valor_amortizado=valor_amortizado,
        data_amortizacao=dados['data_amortizacao'],
        tipo=dados['tipo'],
    )
    dados_amortizacao = amortizacao.to_dict()
    dados_amortizacao['financiamento_id'] = id_financiamento

    try:
        amortizacao_id = bd.insere_dado(conn, 'AmortizacoesExtras', dados_amortizacao)
    except IntegrityError:
        conn.close()
        return jsonify({"erro": "Já existe uma amortização extra para este financiamento nesta data."}), 409

    # busca todas as amortizações (incluindo a recém-inserida) para reconstruir as parcelas
    dados_amortizacoes = bd.obtem_dados(conn, 'AmortizacoesExtras', coluna='financiamento_id', valor=id_financiamento)
    amortizacoes = [
        AmortizacaoExtra(
            valor_amortizado=a['valor_amortizado'],
            data_amortizacao=a['data_amortizacao'],
            tipo=a['tipo'],
        )
        for a in dados_amortizacoes
    ]

    # deleta as parcelas antigas e insere as recalculadas
    bd.deleta_dados(conn, 'Parcelas', coluna='financiamento_id', valor=id_financiamento)

    calculadora = criar_calculadora(financiamento.modelo)
    novas_parcelas = calculadora.reconstruir_parcelas(financiamento, amortizacoes)

    for parcela in novas_parcelas:
        dados_parcela = parcela.to_dict()
        dados_parcela['financiamento_id'] = id_financiamento
        bd.insere_dado(conn, 'Parcelas', dados_parcela)

    conn.close()
    return jsonify({"id": amortizacao_id, "mensagem": "Amortização extra criada com sucesso."}), 201

@bp.route('/<int:id_financiamento>/amortizacoes', methods=['GET'])
def listar_amortizacoes_por_financiamento(id_financiamento: int):
    """
    Lista todas as amortizações extras de um financiamento.
    ---
    tags:
      - Amortizações Extras
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
    responses:
      200: { description: Lista de amortizações (vazia se nenhuma cadastrada). }
    """
    conn = bd.conecta_db()
    amortizacoes = bd.obtem_dados(conn, 'AmortizacoesExtras', coluna='financiamento_id', valor=id_financiamento)
    if not amortizacoes:
        conn.close()
        return jsonify([]), 200

    conn.close()

    amortizacoes_dict = [dict(amortizacao) for amortizacao in amortizacoes]
    return jsonify(amortizacoes_dict), 200

@bp.route('/<int:id_financiamento>/amortizacoes/<int:id_amortizacao>', methods=['DELETE'])
def deletar_amortizacao_extra(id_financiamento: int, id_amortizacao: int):
    """
    Deleta uma amortização extra e reconstrói as parcelas do financiamento.
    ---
    tags:
      - Amortizações Extras
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
      - { in: path, name: id_amortizacao,   type: integer, required: true }
    responses:
      200: { description: Amortização deletada e parcelas reconstruídas. }
      404: { description: Amortização ou financiamento não encontrado. }
    """
    conn = bd.conecta_db()

    linhas_afetadas = bd.deleta_dados(conn, 'AmortizacoesExtras', valor=id_amortizacao)
    if linhas_afetadas == 0:
        conn.close()
        return jsonify({"erro": "Amortização extra não encontrada."}), 404

    resultado = bd.obtem_dados(conn, 'Financiamentos', coluna='id', valor=id_financiamento)
    if not resultado:
        conn.close()
        return jsonify({"erro": "Financiamento não encontrado."}), 404

    dados_financiamento = resultado[0]
    financiamento = Financiamento(
        nome=dados_financiamento['nome'],
        valor_imovel=dados_financiamento['valor_imovel'],
        entrada=dados_financiamento['entrada'],
        taxa_juros=dados_financiamento['taxa_juros'],
        prazo_meses=dados_financiamento['prazo_meses'],
        data_inicio=dados_financiamento['data_inicio'],
        modelo=dados_financiamento['modelo'],
    )

    dados_amortizacoes = bd.obtem_dados(conn, 'AmortizacoesExtras', coluna='financiamento_id', valor=id_financiamento)
    amortizacoes = [
        AmortizacaoExtra(
            valor_amortizado=a['valor_amortizado'],
            data_amortizacao=a['data_amortizacao'],
            tipo=a['tipo'],
        )
        for a in dados_amortizacoes
    ]

    bd.deleta_dados(conn, 'Parcelas', coluna='financiamento_id', valor=id_financiamento)

    calculadora = criar_calculadora(financiamento.modelo)
    novas_parcelas = calculadora.reconstruir_parcelas(financiamento, amortizacoes)

    for parcela in novas_parcelas:
        dados_parcela = parcela.to_dict()
        dados_parcela['financiamento_id'] = id_financiamento
        bd.insere_dado(conn, 'Parcelas', dados_parcela)

    conn.close()
    return jsonify({"mensagem": "Amortização extra deletada com sucesso."}), 200