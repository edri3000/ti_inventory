from flask import Flask, render_template, request, redirect, url_for, jsonify
import platform
import subprocess
import json
import os
from collections import defaultdict

app = Flask(__name__)

JSON_FILE = 'inventario.json'

# --- Funções de carregar/salvar dados (sem alteração) ---
def carregar_dados():
    if not os.path.exists(JSON_FILE): return []
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return []
def salvar_dados(dados):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
def get_proximo_id():
    inventario = carregar_dados()
    if not inventario: return 1
    return max(item['id'] for item in inventario) + 1
def get_tipos_unicos():
    inventario = carregar_dados()
    return sorted(list(set(item['tipo'] for item in inventario)))

# --- Dicionários (sem alteração) ---
ICONE_POR_TIPO = {
    'PC': 'fa-solid fa-computer',
    'Notebook': 'fa-solid fa-laptop',
    'Impressora': 'fa-solid fa-print',
    'Switch': 'fa-solid fa-network-wired',
    'Roteador': 'fa-solid fa-wifi',
    'Servidor': 'fa-solid fa-server',
    'Leitor RFID': 'fa-solid fa-id-card-clip',
    'Telefone IP': 'fa-solid fa-phone',
    'Relogio': 'fa-solid fa-clock',
    'Catraca': 'fa-solid fa-road-barrier',
    'default': 'fa-solid fa-hdd'
}
PLURAL_POR_TIPO = {
    'Impressora': 'Impressoras', 'Leitor RFID': 'Leitores RFID',
    'PC': 'PCs', 'Notebook': 'Notebooks', 'Switch': 'Switches', 'Roteador': 'Roteadores',
    'Servidor': 'Servidores', 'Relogio': 'Relógios', 'Telefone IP': 'Telefones IP', 
    'Catraca': 'Catracas'
}

# --- Rotas Principais (sem alteração) ---
@app.route('/')
@app.route('/inventario/<string:tipo>')
def index(tipo='todos'):
    inventario = carregar_dados()
    tipos_menu = get_tipos_unicos()
    
    # --- MELHORIA 1: ORDENAÇÃO ---
    # Ordena a lista inteira por Setor (case-insensitive) e depois por Nome como critério de desempate.
    inventario.sort(key=lambda item: (item.get('setor', '').lower(), item.get('nome', '').lower()))
    
    if tipo == 'todos':
        equipamentos_agrupados = defaultdict(list)
        for item in inventario:
            equipamentos_agrupados[item['tipo']].append(item)
            
        # --- MELHORIA 2: LIMITAÇÃO ---
        # Primeiro, guardamos a contagem total antes de limitar a exibição
        total_por_tipo = {tipo_grupo: len(lista) for tipo_grupo, lista in equipamentos_agrupados.items()}
        
        # Agora, limitamos a lista de cada grupo para no máximo 5 itens
        for tipo_grupo, lista_equipamentos in equipamentos_agrupados.items():
            equipamentos_agrupados[tipo_grupo] = lista_equipamentos[:5]
        
        return render_template(
            'index.html', 
            equipamentos_agrupados=equipamentos_agrupados,
            tipos=tipos_menu,
            titulo='Dashboard de Equipamentos',
            view_mode='dashboard',
            icones=ICONE_POR_TIPO,
            plurais=PLURAL_POR_TIPO,
            total_por_tipo=total_por_tipo # Passa a contagem total para o template
        )
    else:
        # A visão de lista filtrada já se beneficia da ordenação feita no início
        equipamentos_filtrados = [item for item in inventario if item['tipo'] == tipo]
        titulo_plural = PLURAL_POR_TIPO.get(tipo, tipo)
        
        return render_template(
            'index.html', 
            equipamentos=equipamentos_filtrados,
            tipos=tipos_menu,
            titulo=f"Inventário: {titulo_plural}",
            view_mode='lista',
            icones=ICONE_POR_TIPO,
            plurais=PLURAL_POR_TIPO
        )

# --- Rota de Adicionar (COM CORREÇÃO) ---
@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar_item():
    if request.method == 'POST':
        inventario = carregar_dados()
        novo_item = {
            'id': get_proximo_id(), 'tipo': request.form['tipo'], 'nome': request.form['nome'],
            'ip': request.form['ip'], 'setor': request.form['setor'], 'patrimonio': request.form['patrimonio'],
            'configuracao': request.form['configuracao']
        }
        inventario.append(novo_item)
        salvar_dados(inventario)
        return redirect(url_for('index', tipo=request.form['tipo']))
    
    # A correção está na linha abaixo:
    return render_template('adicionar.html', tipos=get_tipos_unicos(), plurais=PLURAL_POR_TIPO, icones=ICONE_POR_TIPO)

# --- Rota de Editar (COM CORREÇÃO) ---
@app.route('/editar/<int:item_id>', methods=['GET', 'POST'])
def editar_item(item_id):
    inventario = carregar_dados()
    item = next((item for item in inventario if item['id'] == item_id), None)
    if not item:
        return redirect(url_for('index'))

    if request.method == 'POST':
        item['tipo'] = request.form['tipo']
        item['nome'] = request.form['nome']
        item['ip'] = request.form['ip']
        item['setor'] = request.form['setor']
        item['patrimonio'] = request.form['patrimonio']
        item['configuracao'] = request.form['configuracao']
        salvar_dados(inventario)
        return redirect(url_for('index', tipo=item['tipo']))
    
    # A correção foi feita na linha abaixo
    return render_template('editar.html', item=item, tipos=get_tipos_unicos(), plurais=PLURAL_POR_TIPO, icones=ICONE_POR_TIPO)

# --- Rota de Deletar (sem alteração) ---
@app.route('/deletar/<int:item_id>')
def deletar_item(item_id):
    inventario = carregar_dados()
    inventario_atualizado = [item for item in inventario if item['id'] != item_id]
    salvar_dados(inventario_atualizado)
    return redirect(request.referrer or url_for('index'))

# --- Funções de Status (sem alteração) ---
def verifica_ping(ip):
    # Etapa 1: Validação básica para evitar pingar em strings vazias ou inválidas.
    if not ip or len(ip.split('.')) != 4:
        return False

    try:
        # Parâmetro de contagem ('-n 1' para Windows, '-c 1' para outros)
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        
        # Comando a ser executado
        comando = ['ping', param, '1', ip]
        
        # Executa o comando com um timeout de 1 segundo.
        # Se o comando demorar mais que isso, ele levanta uma exceção e falha.
        resultado = subprocess.run(
            comando,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1  # Timeout crucial!
        )
        
        # Retorna True apenas se o código de saída for 0 (sucesso)
        return resultado.returncode == 0
        
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # Se o ping demorar demais, ou se o comando 'ping' não for encontrado,
        # ou qualquer outro erro de SO, consideramos offline.
        return False
@app.route('/status/<string:ip>')
def status_ip(ip):
    if verifica_ping(ip): return jsonify({'status': 'online'})
    else: return jsonify({'status': 'offline'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug=True)