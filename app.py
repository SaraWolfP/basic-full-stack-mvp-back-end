from flask import Flask
from flask_cors import CORS

import banco_de_dados as bd
from rotas.financiamento import bp as financiamento_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(financiamento_bp)

if __name__ == '__main__':
    bd.inicializa_db()
    app.run(debug=True)
