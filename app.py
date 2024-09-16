import os

import eventlet
eventlet.monkey_patch()  # Patch necessário para que o eventlet funcione corretamente
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import random
import json



app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='eventlet')  # Usa o eventlet como modo assíncrono

# Carregar as dicas a partir do arquivo JSON com codificação UTF-8
with open('dicas.json', 'r', encoding='utf-8') as f:
    cartas = json.load(f)

# Estrutura de jogo
jogos = {}
historico = []


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('join')
def handle_join(data):
    sala = data['sala']
    jogador = data['jogador']

    join_room(sala)

    if sala not in jogos:
        jogos[sala] = {
            'time1': jogador,
            'time2': None,
            'pontuacao': {jogador: 0},
            'vez': jogador,  # Jogador atual
            'perguntador': None,  # Quem está perguntando
            'respondedor': None,  # Quem está respondendo
            'cartas_usadas': [],  # Lista de cartas já usadas
            'coinflip': None,
            'tema_atual': None,
            'cartas': [],
            'erros': 0,
            'vidas_restantes': 3,  # Limitar o número de erros permitidos por rodada
            'coinflip_usado': False  # Flag para saber se o cara ou coroa já foi feito
        }
    else:
        jogos[sala]['time2'] = jogador
        jogos[sala]['pontuacao'][jogador] = 0

    emit('atualizar_sala', jogos[sala], room=sala)


# Função para selecionar uma carta que ainda não foi usada
def selecionar_carta_unica(tema, cartas_usadas):
    cartas_disponiveis = [carta for carta in cartas[tema] if carta not in cartas_usadas]

    if not cartas_disponiveis:
        # Reiniciar ciclo de cartas se todas já foram usadas ou avisar para adicionar mais cartas
        return None  # Retorna None se não houver mais cartas disponíveis

    carta_selecionada = random.choice(cartas_disponiveis)
    return carta_selecionada


# Coin flip (cara ou coroa)
@socketio.on('coinflip')
def handle_coinflip(data):
    sala = data['sala']

    # Verificar se o coinflip já foi usado
    if jogos[sala]['coinflip_usado']:
        return  # Não permite refazer o cara ou coroa após a primeira vez

    resultado = random.choice(['time1', 'time2'])
    jogos[sala]['coinflip'] = resultado
    jogos[sala]['coinflip_usado'] = True  # Marca que o cara ou coroa foi feito

    if resultado == 'time1':
        jogos[sala]['perguntador'] = jogos[sala]['time2']
        jogos[sala]['respondedor'] = jogos[sala]['time1']
    else:
        jogos[sala]['perguntador'] = jogos[sala]['time1']
        jogos[sala]['respondedor'] = jogos[sala]['time2']

    # Sortear o tema e carta automaticamente para o perguntador
    tema = random.choice(list(cartas.keys()))

    carta_selecionada = selecionar_carta_unica(tema, jogos[sala]['cartas_usadas'])

    if carta_selecionada:
        jogos[sala]['tema_atual'] = tema
        jogos[sala]['cartas'] = carta_selecionada
        jogos[sala]['cartas_usadas'].append(carta_selecionada)  # Adicionar carta à lista de usadas
        jogos[sala]['erros'] = 0
        jogos[sala]['vidas_restantes'] = 3  # Reiniciar as vidas a cada rodada
        emit('iniciar_rodada', {'tema': tema, 'cartas': jogos[sala]['cartas'], 'perguntador': jogos[sala]['perguntador']}, room=sala)
    else:
        emit('alerta', {'mensagem': 'Todas as cartas já foram usadas. Adicione novas cartas.'}, room=sala)


# Ações de acerto e erro
@socketio.on('jogar')
def handle_jogar(data):
    sala = data['sala']
    acao = data['acao']

    if acao == 'acerto':
        jogador_atual = jogos[sala]['respondedor']  # O ponto vai para o time respondedor
        pontuacao_atual = jogos[sala]['pontuacao'][jogador_atual] + 1
        jogos[sala]['pontuacao'][jogador_atual] = pontuacao_atual
        emit('alerta_acerto', {'jogador': jogador_atual, 'pontuacao': pontuacao_atual}, room=sala)
        if pontuacao_atual >= 10:
            historico.append(jogos[sala])
            emit('fim_jogo', jogos[sala], room=sala)
        else:
            # Alternar perguntador e respondedor ao final da rodada
            temp = jogos[sala]['perguntador']
            jogos[sala]['perguntador'] = jogos[sala]['respondedor']
            jogos[sala]['respondedor'] = temp

            tema = random.choice(list(cartas.keys()))
            carta_selecionada = selecionar_carta_unica(tema, jogos[sala]['cartas_usadas'])

            if carta_selecionada:
                jogos[sala]['tema_atual'] = tema
                jogos[sala]['cartas'] = carta_selecionada
                jogos[sala]['cartas_usadas'].append(carta_selecionada)  # Adicionar carta à lista de usadas
                jogos[sala]['erros'] = 0
                jogos[sala]['vidas_restantes'] = 3
                emit('iniciar_rodada', {'tema': tema, 'cartas': jogos[sala]['cartas'], 'perguntador': jogos[sala]['perguntador']}, room=sala)
            else:
                emit('alerta', {'mensagem': 'Todas as cartas já foram usadas. Adicione novas cartas.'}, room=sala)

    elif acao == 'erro':
        jogos[sala]['vidas_restantes'] -= 1
        if jogos[sala]['vidas_restantes'] <= 0:
            # Trocar os times quando não há mais vidas
            temp = jogos[sala]['perguntador']
            jogos[sala]['perguntador'] = jogos[sala]['respondedor']
            jogos[sala]['respondedor'] = temp

            tema = random.choice(list(cartas.keys()))
            carta_selecionada = selecionar_carta_unica(tema, jogos[sala]['cartas_usadas'])

            if carta_selecionada:
                jogos[sala]['tema_atual'] = tema
                jogos[sala]['cartas'] = carta_selecionada
                jogos[sala]['cartas_usadas'].append(carta_selecionada)  # Adicionar carta à lista de usadas
                jogos[sala]['erros'] = 0
                jogos[sala]['vidas_restantes'] = 3
                emit('iniciar_rodada', {'tema': tema, 'cartas': jogos[sala]['cartas'], 'perguntador': jogos[sala]['perguntador']}, room=sala)
            else:
                emit('alerta', {'mensagem': 'Todas as cartas já foram usadas. Adicione novas cartas.'}, room=sala)
        else:
            emit('atualizar_jogo', jogos[sala], room=sala)


# Atualizar pontuação
@socketio.on('atualizar_pontuacao')
def handle_atualizar_pontuacao(data):
    sala = data['sala']
    pontuacao = jogos[sala]['pontuacao']

    emit('atualizar_jogo', {
        'time1': jogos[sala]['time1'],
        'time2': jogos[sala]['time2'],
        'pontuacao': pontuacao
    }, room=sala)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
