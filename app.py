from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

import banco_de_dados as bd
from rotas.financiamento import bp as financiamento_bp
from rotas.parcelas import bp as parcelas_bp
from rotas.amortizacoes import bp as amortizacoes_bp

app = Flask(__name__)
CORS(app)
Swagger(app)

app.register_blueprint(financiamento_bp)
app.register_blueprint(parcelas_bp)
app.register_blueprint(amortizacoes_bp)

if __name__ == '__main__':
    bd.inicializa_db()
    app.run(debug=True)
