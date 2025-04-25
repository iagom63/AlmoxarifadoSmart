from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
from flask_socketio import SocketIO
import json
import os
import time
import pandas as pd
from io import BytesIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SAIDA_FILE = 'saida.json'
saidas = []

def carregar_saidas():
    global saidas
    if os.path.exists(SAIDA_FILE):
        with open(SAIDA_FILE, 'r', encoding='utf-8') as f:
            try:
                saidas = json.load(f)
            except json.JSONDecodeError:
                saidas = []
    else:
        saidas = []

def salvar_saidas():
    with open(SAIDA_FILE, 'w', encoding='utf-8') as f:
        json.dump(saidas, f, ensure_ascii=False, indent=2)

# carrega ao iniciar
carregar_saidas()

@app.route('/')
def index():
    return redirect(url_for('solicitacao'))

@app.route('/solicitacao', methods=['GET', 'POST'])
def solicitacao():
    if request.method == 'POST':
        solicitante = request.form['solicitante']
        destino     = request.form['destino']
        autorizado  = request.form['autorizado']
        count       = int(request.form['count'])
        return redirect(url_for('itens',
                                solicitante=solicitante,
                                destino=destino,
                                autorizado=autorizado,
                                count=count))
    return render_template('solicitacao.html')

@app.route('/itens', methods=['GET', 'POST'])
def itens():
    solicitante = request.args.get('solicitante')
    destino     = request.args.get('destino')
    autorizado  = request.args.get('autorizado')
    count       = int(request.args.get('count', 0))

    if request.method == 'POST':
        for i in range(count):
            tipo = request.form[f'tipo_{i}']
            desc = request.form[f'descricao_{i}']
            qtd  = request.form[f'quantidade_{i}']
            und  = request.form[f'unidade_{i}']
            item = {
                'nome':        solicitante,
                'descricao':   desc,
                'quantidade':  qtd,
                'unidade':     und,
                'observacao':  destino,
                'responsavel': autorizado,
                'tipo':        tipo,
                'delivered':   False,
                'timestamp':   int(time.time() * 1000)
            }
            saidas.append(item)
        salvar_saidas()
        socketio.emit('update')
        return redirect(url_for('solicitacao'))

    return render_template(
        'itens.html',
        solicitante=solicitante,
        destino=destino,
        autorizado=autorizado,
        count=count
    )

@app.route('/dashboard')
def dashboard():
    materiais = []
    equipamentos = []
    for idx, item in enumerate(saidas):
        if item['tipo'] == 'material':
            materiais.append({'index': idx, 'item': item})
        else:
            equipamentos.append({'index': idx, 'item': item})
    return render_template(
        'dashboard.html',
        materiais=materiais,
        equipamentos=equipamentos
    )

@app.route('/remover/<int:index>', methods=['POST'])
def remover(index):
    if 0 <= index < len(saidas):
        saidas.pop(index)
        salvar_saidas()
        socketio.emit('update')
    return redirect(url_for('dashboard'))

@app.route('/reordenar/<int:index>', methods=['POST'])
def reordenar(index):
    if 0 <= index < len(saidas):
        item = saidas.pop(index)
        item['delivered'] = True
        saidas.append(item)
        salvar_saidas()
        socketio.emit('update')
    return redirect(url_for('dashboard'))

@app.route('/tela')
def tela():
    return render_template('tela.html')

@app.route('/api/saidas')
def api_saidas():
    return jsonify(saidas)

@app.route('/exportar')
def exportar():
    df = pd.DataFrame(saidas)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Saidas')
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="saidas.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    # usa SocketIO para websockets; Eventlet habilita concurrency
    socketio.run(app, debug=True, host='0.0.0.0')
