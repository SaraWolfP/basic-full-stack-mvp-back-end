import banco_de_dados as bd

from flask import Blueprint, jsonify

bp = Blueprint('parcelas', __name__, url_prefix='/financiamento')

@bp.route('/<int:id_financiamento>/parcelas', methods=['GET'])
def listar_parcelas_por_financiamento(id_financiamento: int):
    """
    Lista todas as parcelas de um financiamento em ordem cronológica.
    ---
    tags:
      - Parcelas
    parameters:
      - { in: path, name: id_financiamento, type: integer, required: true }
    responses:
      200: { description: Lista de parcelas (vazia se nenhuma calculada). }
      404: { description: Financiamento não encontrado. }
    """
    conn = bd.conecta_db()

    financiamento = bd.obtem_dados(conn, 'Financiamentos', coluna='id', valor=id_financiamento)
    if not financiamento:
        conn.close()
        return jsonify({"erro": "Financiamento não encontrado."}), 404

    parcelas = bd.obtem_dados(conn, 'Parcelas', coluna='financiamento_id', valor=id_financiamento, ordem='numero_parcela')
    conn.close()

    return jsonify([dict(p) for p in parcelas]), 200
