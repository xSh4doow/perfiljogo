document.addEventListener('DOMContentLoaded', (event) => {
    var socket = io();

    // Solicitar o nome da sala e do jogador
    let sala = prompt("Entre com o nome da sala:");
    let jogador = prompt("Entre com o seu nome:");

    // Entrar na sala
    socket.emit('join', { sala: sala, jogador: jogador });

    let timePerguntador = false;  // Variável para saber se é o time perguntador
    let coinflipFeito = false;  // Variável para saber se o cara ou coroa já foi feito

    // Coin Flip (Cara ou Coroa)
    document.getElementById('coinflipButton').addEventListener('click', function() {
        if (!coinflipFeito) {
            socket.emit('coinflip', { sala: sala });
        } else {
            alert("O cara ou coroa já foi realizado!");
        }
    });

    // Iniciar a rodada
    socket.on('iniciar_rodada', function(data) {
        // Desativar o botão de cara ou coroa após o primeiro uso
        coinflipFeito = true;
        document.getElementById('coinflipButton').disabled = true;

        // Verificar se o jogador é o perguntador
        if (data.perguntador === jogador) {
            timePerguntador = true;
            document.body.style.backgroundColor = 'red';  // Mudar fundo para vermelho
            document.getElementById('botaoAcerto').disabled = false;  // Habilitar botões
            document.getElementById('botaoErro').disabled = false;   // para o perguntador

            // Mostrar tema, resposta e dicas para o perguntador
            document.getElementById('temaAtual').innerText = `Tema: ${data.tema} - Resposta: ${data.cartas.resposta}`;
            let dicasList = document.getElementById('dicasList');
            dicasList.innerHTML = ''; // Limpar lista anterior
            data.cartas.dicas.forEach(function(dica, index) {
                let li = document.createElement('li');
                li.innerText = `Dica ${index + 1}: ${dica}`;
                dicasList.appendChild(li);
            });
        } else {
            timePerguntador = false;
            document.body.style.backgroundColor = '';  // Fundo normal para o respondedor
            document.getElementById('botaoAcerto').disabled = true;  // Desabilitar botões
            document.getElementById('botaoErro').disabled = true;   // para o respondedor

            document.getElementById('temaAtual').innerText = '';  // Esconder tema e resposta do respondedor
            document.getElementById('dicasList').innerHTML = '';  // Esconder dicas do respondedor
        }
    });

    // Botões de acerto e erro, habilitados apenas para o perguntador
    document.getElementById('botaoAcerto').addEventListener('click', function() {
        if (timePerguntador) {
            socket.emit('jogar', { acao: 'acerto', sala: sala });
        }
    });

    document.getElementById('botaoErro').addEventListener('click', function() {
        if (timePerguntador) {
            socket.emit('jogar', { acao: 'erro', sala: sala });
        }
    });

    // Alerta de acerto e atualização do placar
    socket.on('alerta_acerto', function(data) {
        alert(`Acerto! ${data.jogador} ganhou um ponto. Pontuação atual: ${data.pontuacao}`);
    });

    // Atualizar o jogo (pontuação e troca de turnos)
    socket.on('atualizar_jogo', function(data) {
        document.getElementById('team1').innerText = data.time1 + ": " + data.pontuacao[data.time1];
        if (data.time2) {
            document.getElementById('team2').innerText = data.time2 + ": " + data.pontuacao[data.time2];
        }
    });

    // Atualizar a pontuação no frontend com um botão
    document.getElementById('atualizarPontuacao').addEventListener('click', function() {
        socket.emit('atualizar_pontuacao', { sala: sala });
    });

    // Fim de rodada
    socket.on('fim_rodada', function(data) {
        alert("Fim da rodada! Agora é a vez do outro time.");
        document.getElementById('dicasList').innerHTML = '';  // Limpar dicas
        document.getElementById('temaAtual').innerText = '';  // Limpar tema
    });

    // Fim de jogo
    socket.on('fim_jogo', function(data) {
        alert("Fim de jogo! O vencedor é: " + data.vez);
    });

    // Atualizar o placar
    socket.on('atualizar_sala', function(data) {
        document.getElementById('team1').innerText = data.time1 + ": " + data.pontuacao[data.time1];
        if (data.time2) {
            document.getElementById('team2').innerText = data.time2 + ": " + data.pontuacao[data.time2];
        }
    });
});
