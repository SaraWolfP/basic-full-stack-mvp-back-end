# Simulador de Financiamento Imobiliário — Back-end

API REST para simular o impacto de amortizações extraordinárias no cronograma de parcelas de um financiamento imobiliário pelo sistema SAC.

## Problema resolvido

Ao realizar um pagamento antecipado em um financiamento, o mutuário pode optar por **reduzir o valor das parcelas** mantendo o prazo original. Esta API simula esse impacto em tempo real: dado um financiamento e uma ou mais amortizações extras, ela recalcula e devolve o novo cronograma completo de parcelas.

## Tecnologias

- Python 3.9+
- Flask 3.0
- SQLite 3
- Flasgger (Swagger/OpenAPI)
- python-dateutil

## Estrutura do projeto

```
basic-full-stack-mvp-back-end/
├── app.py                   # Ponto de entrada da aplicação
├── banco_de_dados.py        # Conexão e operações com o banco SQLite
├── requirements.txt         # Dependências
├── rotas/
│   ├── financiamento.py     # Rotas de financiamentos
│   ├── parcelas.py          # Rotas de parcelas
│   └── amortizacoes.py      # Rotas de amortizações extras
└── servicos/
    └── calculadora.py       # Lógica de cálculo SAC (OOP)
```

## Modelo de dados

```
Financiamentos          Parcelas                  AmortizacoesExtras
──────────────          ────────                  ──────────────────
id (PK)                 id (PK)                   id (PK)
nome (UNIQUE)           financiamento_id (FK) ←   financiamento_id (FK) ←
valor_imovel            numero_parcela            valor_amortizado
entrada                 data_parcela              data_amortizacao
taxa_juros              valor_parcela             tipo (PARCELA|PRAZO)
prazo_meses
data_inicio
modelo (SAC|PRICE)
```

Deleção em cascata: ao deletar um financiamento, todas as parcelas e amortizações são removidas automaticamente.

## Rotas disponíveis

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/financiamento/` | Cria financiamento e calcula parcelas SAC |
| GET | `/financiamento/` | Lista todos os financiamentos |
| GET | `/financiamento/<id>` | Retorna um financiamento por ID |
| DELETE | `/financiamento/<id>` | Deleta financiamento (cascata) |
| GET | `/financiamento/<id>/parcelas` | Lista parcelas de um financiamento |
| POST | `/financiamento/<id>/amortizacoes` | Cria amortização e recalcula parcelas |
| GET | `/financiamento/<id>/amortizacoes` | Lista amortizações de um financiamento |
| DELETE | `/financiamento/<id>/amortizacoes/<id>` | Deleta amortização e reconstrói parcelas |

## Instalação e execução

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd basic-full-stack-mvp-back-end
```

### 2. Crie e ative o ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Inicie o servidor

```bash
python3 app.py
```

O servidor sobe em `http://127.0.0.1:5000`.  
A documentação Swagger estará disponível em `http://127.0.0.1:5000/apidocs`.

> **Nota:** Na primeira execução, o banco `banco_de_dados.db` é criado automaticamente. Se o schema mudar entre versões, delete o arquivo `.db` antes de reiniciar.

## Exemplo de uso

### Criar um financiamento

```bash
curl -X POST http://127.0.0.1:5000/financiamento/ \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Meu Apartamento",
    "valor_imovel": 500000,
    "entrada": 100000,
    "taxa_juros": 0.89,
    "prazo_meses": 360,
    "data_inicio": "2025-01",
    "modelo": "SAC"
  }'
```

> `taxa_juros` é informado em percentual (ex: `0.89` = 0,89% a.m.). O sistema converte para decimal internamente.

### Criar uma amortização extra

```bash
curl -X POST http://127.0.0.1:5000/financiamento/1/amortizacoes \
  -H "Content-Type: application/json" \
  -d '{
    "valor_amortizado": 50000,
    "data_amortizacao": "2026-01",
    "tipo": "PARCELA"
  }'
```

As parcelas são recalculadas automaticamente a partir da data da amortização.
