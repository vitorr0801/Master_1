# Sprint 1
![Diagrama de Heartbeat TCP](/Imagens/Imagem1.png)

Este diagrama representa o funcionamento do mecanismo de *heartbeat* entre o Worker (cliente) e o Master (servidor), cuja principal função é verificar continuamente se o servidor está disponível. A comunicação ocorre por meio de conexões TCP e envio de mensagens no formato JSON.

A cada 30 segundos, o Worker inicia uma conexão com o Master e envia uma requisição contendo a tarefa de *heartbeat*. Ao receber essa mensagem, o Master realiza o processamento e validação dos dados. Se estiver funcionando corretamente, ele responde com um status indicando que está ativo. Com isso, o Worker registra que o servidor está online e segue aguardando o próximo ciclo de verificação.

Caso ocorra alguma falha, como erro de conexão ou tempo de resposta excedido, o Worker interpreta que o Master está indisponível. Nesse cenário, ele registra o status como offline e passa a tentar se reconectar nas próximas execuções do ciclo. Esse processo se repete continuamente, garantindo um monitoramento constante da disponibilidade do servidor e contribuindo para a confiabilidade do sistema.

# Sprint 2
![Diagrama de Comunicação Worker-Master](/Imagens/Imagem2.png)

Este diagrama apresenta o fluxo de comunicação entre o Worker (cliente) e o Master (servidor) para solicitação, processamento e conclusão de tarefas em um sistema distribuído.

O processo se inicia quando o Worker se apresenta ao Master informando que está ativo e pronto para trabalhar, enviando seus identificadores. Ao receber essa solicitação, o Master verifica a fila de tarefas disponível. Caso exista alguma tarefa pendente, ele a envia ao Worker, que realiza o processamento — podendo envolver cálculos, consultas ou outras operações.

Após concluir a execução, o Worker retorna ao Master um relatório com o status da tarefa, indicando sucesso ou falha. O Master então registra esse resultado e envia uma confirmação final (ACK), liberando o Worker para iniciar um novo ciclo de trabalho.

Se não houver tarefas disponíveis na fila, o Master informa ao Worker que não há trabalho no momento. Nesse caso, o Worker permanece em espera até o próximo ciclo, quando fará uma nova solicitação.

Esse fluxo garante uma comunicação organizada e contínua entre cliente e servidor, permitindo a distribuição eficiente de tarefas e o controle do processamento no sistema.