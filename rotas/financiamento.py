from datetime import datetime
from sqlite3 import IntegrityError

import banco_de_dados as bd

from flask import Blueprint, jsonify, request
from servicos.calculadora import Financiamento, criar_calculadora

bp = Blueprint('financiamento', __name__, url_prefix='/financiamento')

@bp.route('/', methods=['POST'])
def criar_financiamento():
    """
    Cria um novo financiamento e calcula suas parcelas pelo sistema SAC.
    ---
    tags:
      - Financiamentos
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nome, valor_imovel, entrada, taxa_juros, prazo_meses, data_inicio, modelo]
          properties:
            nome:          { type: string,  example: "Meu Apartamento" }
            valor_imovel:  { type: number,  example: 500000 }
            entrada:       { type: number,  example: 100000 }
            taxa_juros:    { type: number,  example: 0.89, description: "Percentual mensal (0.89 = 0,89% a.m.)" }
            prazo_meses:   { type: integer, example: 360 }
            data_inicio:   { type: string,  example: "2025-01" }
            modelo:        { type: string,  enum: [SAC, PRICE], example: SAC }
    responses:
      201: { description: Financiamento criado com sucesso. }
      400: { description: Dados inválidos ou ausentes. }
      409: { description: Já existe um financiamento com esse nome. }
    """
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({"erro": "Corpo da requisição ausente ou inválido."}), 400

    # verifica campos obrigatórios
    campos_obrigatorios = ['nome', 'valor_imovel', 'entrada', 'taxa_juros', 'prazo_meses', 'data_inicio', 'modelo']
    faltando = [c for c in campos_obrigatorios if c not in dados]
    if faltando:
        return jsonify({"erro": f"Campos obrigatórios ausentes: {faltando}"}), 400

    # valida modelo
    if dados.get('modelo') not in ['SAC', 'PRICE']:
        return jsonify({"erro": "modelo deve ser 'SAC' ou 'PRICE'."}), 400

    if dados.get('modelo') == 'PRICE':
        return jsonify({"erro": "Modelo PRICE ainda não suportado."}), 400

    # valida tipos numéricos
    try:
        valor_imovel = float(dados['valor_imovel'])
        entrada      = float(dados['entrada'])
        taxa_juros   = float(dados['taxa_juros'])
        prazo_meses  = int(dados['prazo_meses'])
    except (ValueError, TypeError):
        return jsonify({"erro": "valor_imovel, entrada e taxa_juros devem ser números. prazo_meses deve ser inteiro."}), 400

    # valida regras de negócio
    if valor_imovel <= 0:
        return jsonify({"erro": "valor_imovel deve ser positivo."}), 400

    if entrada <= 0:
        return jsonify({"erro": "entrada deve ser positiva."}), 400

    if entrada >= valor_imovel:
        return jsonify({"erro": "entrada deve ser menor que valor_imovel."}), 400

    if prazo_meses <= 0:
        return jsonify({"erro": "prazo_meses deve ser um inteiro positivo."}), 400

    # taxa recebida em percentual — converte para decimal antes de persistir
    if taxa_juros <= 0 or taxa_juros >= 100:
        return jsonify({"erro": "taxa_juros deve ser um percentual positivo menor que 100."}), 400

    # valida formato de data_inicio
    try:
        datetime.strptime(dados['data_inicio'], "%Y-%m")
    except ValueError:
        return jsonify({"erro": "data_inicio deve estar no formato 'YYYY-MM' (ex: '2025-01')."}), 400

    conn = bd.conecta_db()
    try:
        financiamento = Financiamento(
            nome=dados['nome'],
            valor_imovel=valor_imovel,
            entrada=entrada,
            taxa_juros=taxa_juros / 100,
            prazo_meses=prazo_meses,
            data_inicio=dados['data_inicio'],
            modelo=dados['modelo'],
        )
        financiamento_id = bd.insere_dado(conn, 'Financiamentos', financiamento.to_dict())

    except IntegrityError:
        conn.close()
        return jsonify({"erro": f"Já existe um financiamento com o nome '{dados['nome']}'."}), 409

    calculadora = criar_calculadora(financiamento.modelo)
    parcelas = calculadora.calcular_parcelas(
        financiamento.valor_financiado,
        financiamento.data_inicio,
        financiamento.prazo_meses,
        financiamento.taxa_juros,
    )

    for parcela in parcelas:
        dados_parcela = parcela.to_dict()
        dados_parcela["financiamento_id"] = financiamento_id
        bd.insere_dado(conn, 'Parcelas', dados_parcela)

    conn.close()
    return jsonify({"id": financiamento_id, "mensagem": "Financiamento criado com sucesso."}), 201


@bp.route('/', methods=['GET'])
def listar_financiamentos():
    """
    Lista todos os financiamentos cadastrados.
    ---
    tags:
      - Financiamentos
    responses:
      200: { description: Lista de financiamentos (vazia se nenhum cadastrado). }
    """
    conn = bd.conecta_db()
    financiamentos = bd.obtem_dados(conn, 'Financiamentos')
    conn.close()

    if not financiamentos:
        return jsonify([]), 200

    financiamentos_dict = [dict(financiamento) for financiamento in financiamentos]
    return jsonify(financiamentos_dict), 200

@bp.route('/<int:id_financiamento>', methods=['DELETE'])
def deletar_financiamento(id_financiamento: int):
    """
    Deleta um financiamento e todas as suas parcelas e amortizações.
    ---
    tags:
      - Financiamentos
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
    responses:
      200: { description: Financiamento deletado com sucesso. }
      404: { description: Financiamento não encontrado. }
    """
    conn = bd.conecta_db()
    linhas_afetadas = bd.deleta_dados(conn, 'Financiamentos', valor=id_financiamento)
    conn.close()

    if linhas_afetadas == 0:
        return jsonify({"erro": "Financiamento não encontrado."}), 404

    return jsonify({"mensagem": "Financiamento deletado com sucesso."}), 200

@bp.route('/<int:id_financiamento>', methods=['GET'])
def obter_financiamento(id_financiamento: int):
    """
    Retorna um financiamento pelo ID.
    ---
    tags:
      - Financiamentos
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
    responses:
      200: { description: Financiamento encontrado. }
      404: { description: Financiamento não encontrado. }
    """
    conn = bd.conecta_db()
    resultado = bd.obtem_dados(conn, 'Financiamentos', coluna='id', valor=id_financiamento)
    conn.close()

    if not resultado:
        return jsonify({"erro": "Financiamento não encontrado."}), 404

    return jsonify(dict(resultado[0])), 200