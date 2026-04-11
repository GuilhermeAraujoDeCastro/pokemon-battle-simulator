# Simulador de Batalha Pokémon

Jogo de batalha Pokémon por turnos. Nasceu como um exercício de Python puro, sem framework, sem biblioteca de jogo, sem sprite: o ponto do projeto era reproduzir com fidelidade a fórmula de dano e a tabela de efetividade de tipos dos jogos oficiais da Nintendo, com o cálculo acontecendo de verdade a cada turno. Isso ainda é verdade pro **modo texto** (`main.py`).

O projeto ganhou depois um **modo gráfico** (`main_gui.py`) bem mais ambicioso: interface em Tkinter, sprites de verdade baixados da PokeAPI, o Pokédex inteiro em vez de um roster fixo, times de até 6 Pokémon, IV/EV/natureza de verdade, habilidades com efeito mecânico, XP/level up/evolução, uma sequência de 8 ginásios com insígnias, save em disco e animação de golpe na tela de batalha. Depois entraram mecânicas de combate mais fundas (prioridade, recuo, dreno de HP, golpes que sobem e descem atributo, clima, ataques carregados de dois turnos), uma PokéMart de verdade, personalização do treinador (nome, Pokémon inicial, apelido), dificuldade e personalidade de IA pros treinadores adversários, e um sisteminha de missões com NPCs fixos. Isso quebra o "zero dependência" original de propósito. Os dois modos convivem no mesmo repositório porque compartilham a mesma lógica de batalha (`pokebattle/battle.py`); só a interface (e o tanto de mecânica em cima) muda.

## Modo texto (`main.py`): o simulador original

Não tem nenhuma dependência externa pra jogar, só Python 3.10 ou mais novo:

```bash
python3 main.py
```

Você escolhe seu Pokémon entre os 41 disponíveis, o computador escolhe um aleatoriamente pra te enfrentar, e a batalha começa. A cada turno você escolhe um movimento e o computador escolhe o dele. Quem ataca primeiro é definido pela Velocidade de cada Pokémon (empate é sorteado). A batalha acaba quando um dos dois desmaia.

### Escolhendo o Pokémon: o seletor por letra

Com 41 Pokémon, rolar uma lista numerada inteira toda vez ficou ruim de usar, por isso a tela de escolha deixa filtrar por letra antes de mostrar a lista:

```
(41 Pokémon disponíveis) Digite uma letra pra filtrar, ou só aperte Enter pra ver todos.

Filtrar por letra: p
  1. Pikachu
  2. Psyduck
  3. Poliwag

Digite o número do Pokémon (ou Enter pra filtrar de novo):
```

Digitar uma letra que não bate com nenhum Pokémon (ex: "x") avisa e deixa tentar de novo, e apertar Enter direto na lista filtrada volta pro filtro em vez de travar. Esse era o limite do terminal puro: um filtro que atualiza a cada tecla digitada exigiria sair do `input()` simples e entrar numa biblioteca de terminal (`curses`) ou numa dependência externa. O modo gráfico resolve isso de um jeito bem mais direto (ver abaixo).

### O que o modo texto cobre

O jogo aplica a fórmula de dano oficial: nível do atacante, poder do golpe, Ataque/Defesa (ou Ataque Especial/Defesa Especial, dependendo da categoria do golpe), STAB (bônus de 1.5x quando o golpe é do mesmo tipo de quem ataca), efetividade de tipo, chance de acerto crítico de 1/16 com 1.5x de dano, e a variação aleatória de 85% a 100% que os jogos aplicam em todo golpe. A tabela de efetividade tem os 18 tipos, incluindo Fada, e funciona tanto pra Pokémon de um tipo quanto de dois.

Os stats de cada Pokémon (HP, Ataque, Defesa, Ataque Especial, Defesa Especial, Velocidade) são calculados pela mesma fórmula dos jogos a partir do nível e dos base stats, assumindo IVs e EVs neutros. Os turnos seguem a ordem de Velocidade, e um Pokémon que desmaia no meio do turno não chega a atacar.

O roster tem 41 Pokémon (os 6 originais mais 35 novos, cobrindo boa parte do alfabeto e dos 18 tipos), cada um com 4 golpes reais dos jogos, todos nível 50. Todo golpe listado nesse roster fixo é um golpe de dano direto de verdade (nome, tipo, poder e precisão reais); nenhum reproduz efeito secundário, status, recuo ou mecânica de dois turnos, porque essa era a simplificação original do projeto. Golpes de status, habilidades, IV/EV e o resto da mecânica de verdade só existem no modo gráfico (ver abaixo).

## Modo gráfico (`main_gui.py`): Pokédex inteiro, times, progressão, loja e missões

```bash
pip install -r requirements.txt
python3 main_gui.py
```

Precisa de internet na primeira vez que cada Pokémon ou golpe aparece. A PokeAPI é consultada uma vez pra cada um, e a resposta fica salva em `.pokecache/` (criada do lado do projeto, ignorada pelo git) pra não precisar de rede de novo depois. Como o roster inteiro da PokeAPI tem mais de mil espécies e formas, montar um time pela primeira vez busca stats, tipos e uma dúzia de golpes candidatos por Pokémon em paralelo, e ainda assim pode demorar alguns segundos, principalmente pro primeiro time da sessão. O progresso do jogador (Pokédex visto, insígnias, dinheiro, itens, missões, nome do treinador e por aí vai) fica salvo em `savegame.json`, do lado do projeto e fora do git, lido e escrito por completo a cada mudança.

### Personalização: nome, inicial e apelido

Na primeira vez que o jogo abre, ele pergunta seu nome de treinador (fica salvo e aparece depois na tela de montar time) e deixa escolher um dos três iniciais clássicos: Bulbasaur, Charmander ou Squirtle. Esse Pokémon inicial entra sozinho, na frente, toda vez que você monta um time novo; os outros 5 espaços continuam livres pra qualquer Pokémon da PokeAPI. Dá também pra apelidar qualquer Pokémon do time antes da batalha: o apelido substitui o nome dele nos painéis de batalha e no log, do jeito que os jogos fazem.

### Montando o time

Você monta um time de até 6 Pokémon numa tela de busca que filtra a lista conforme você digita, com qualquer Pokémon da PokeAPI, não só um roster fixo. Cada Pokémon vem com IVs (0 a 31) e natureza sorteados aleatoriamente, do jeito que os jogos fazem, então dois Bulbasaur do mesmo nível não têm exatamente os mesmos stats. Os golpes de cada um são escolhidos entre os que ele aprende por nível até o nível 50: um golpe STAB, um de cobertura de outro tipo, um de status quando existe algum entre os candidatos, e o resto preenchido pelos golpes de maior poder. Cada Pokémon aparece com a ilustração oficial dele (a "official artwork" da PokeAPI), baixada e cacheada localmente, e com o nome real da habilidade dele.

### Status, habilidades e o painel de batalha

Os golpes reais trazem os efeitos de status: queimadura, veneno, paralisia, congelamento, sono e confusão, aplicados pelos golpes que os têm de verdade nos jogos (Thunder Wave paralisa, Sleep Powder faz dormir, e por aí vai). As imunidades de tipo valem: Fogo não queima nem congela, Elétrico não paralisa, Veneno/Aço não envenena. Queimadura reduz o Ataque físico à metade e causa 1/16 do HP máximo por turno; veneno causa 1/8; paralisia reduz a Velocidade à metade e tem 25% de chance de travar o turno; sono e congelamento impedem agir até passar; confusão tem 1/3 de chance do próprio Pokémon se acertar em vez de atacar.

Toda habilidade real aparece no painel de batalha, mas só um conjunto curado das mais conhecidas tem efeito mecânico de verdade: Static/Flame Body/Poison Point (chance de status em quem acerta um golpe físico), Levitate (imunidade total a golpes de Terra), Intimidate (baixa o Ataque do oponente ao entrar em campo), Guts (ignora o corte de Ataque da queimadura e ainda ganha bônus com qualquer status), Rough Skin (dano de recuo em quem acerta um golpe físico) e Sturdy (segura o desmaio com 1 HP se estiver com o HP cheio). Implementar as centenas de habilidades da API de forma genérica não valia o esforço; as demais só ficam de enfeite.

Cada golpe que acerta faz o painel do lado atingido piscar e o número do dano subir e sumir, desenhado num Canvas dedicado. O menu de batalha é igual ao dos jogos: Lutar escolhe um golpe, Pokémon troca o ativo (trocar consome o turno, mas o oponente ainda ataca em seguida), Mochila abre o inventário comprado na PokéMart (ver abaixo), mostrando quanto resta de cada item, e Fugir encerra a batalha na hora.

### Mecânicas de combate mais fundas

Golpe com prioridade age antes da ordem normal de Velocidade, do jeito que golpes rápidos funcionam nos jogos. Golpes de recuo e de dreno de HP usam o mesmo campo que a PokeAPI já expõe pra isso: positivo cura o atacante numa porcentagem do dano que ele acabou de causar, negativo causa dano ao próprio atacante. Golpes de status que sobem ou descem atributo (como Growl ou Swords Dance) mexem no mesmo sistema de estágio de -6 a +6 que já existia pra Intimidate. Clima (sol, chuva, tempestade de areia e granizo) dura 5 turnos, multiplica o dano de golpes de Fogo e Água (sol favorece Fogo, chuva favorece Água) e causa dano residual em quem não é imune ao tipo do clima (Pedra/Terra/Aço na areia, Gelo no granizo). Ataques carregados de dois turnos (tipo Solar Beam) gastam o primeiro turno carregando energia sem atacar e batem de verdade só no segundo; trocar de golpe no meio cancela a carga.

### Loja (PokéMart) e economia

Vencer um ginásio dá dinheiro, guardado no save junto com as insígnias. Esse dinheiro serve pra comprar item na PokéMart: Poção (cura 20 HP, $300), Super Poção (50 HP, $700), Hiper Poção (120 HP, $1200) e Revive (metade do HP máximo, só funciona em quem desmaiou, $1500). O inventário comprado fica salvo no mesmo `savegame.json` das insígnias, então continua entre sessões. Todo save novo já começa com 3 Poções, do jeito que o jogo sempre deu antes da loja existir.

### Dificuldade e IA dos treinadores

A tela de montar time tem um seletor de dificuldade (Fácil, Normal, Difícil), salvo no save e usado em toda batalha daí em diante. No Fácil, a IA escolhe um golpe aleatório entre todos os que o Pokémon conhece, do jeito que sempre foi. No Normal e no Difícil, a escolha passa a depender da personalidade do treinador adversário: Agressivo bate sempre com o golpe mais forte, Defensivo troca pra um golpe de status quando o HP cai abaixo de 40%, e Estratégico prioriza o golpe com melhor multiplicador de tipo mesmo que o poder bruto seja menor. No Difícil, os três perfis calculam um dano esperado de verdade (poder vezes efetividade de tipo vezes STAB) em vez de olhar só o poder do golpe. Cada líder de ginásio tem uma personalidade fixa que combina com o estilo dele (Brock é defensivo, Lt. Surge é agressivo, Sabrina é estratégica, e por aí vai); fora dos ginásios, a personalidade do time adversário é sorteada no início de cada batalha.

### XP, level up e evolução

Vencer um Pokémon dá experiência de verdade (o `base_experience` da PokeAPI, com o multiplicador de 1.5x de batalha de treinador) e ponto de esforço (EV) no stat mais alto do derrotado. A curva de XP usada é a "medium fast" (nível+1 ao cubo) pra todo mundo: os jogos variam a curva por espécie, o que exigiria mais uma chamada de rede só pra isso, e a curva única não muda a experiência de jogar o suficiente pra justificar. Subir de nível pode ensinar um golpe novo (com a mesma pergunta "esquecer um golpe?" dos jogos quando já tem 4) e pode evoluir o Pokémon, seguindo a cadeia de evolução real da API restrita a evoluções por nível.

### Pokédex e ginásios

A tela de Pokédex lista todo Pokémon da API com a mesma busca da tela de time, marcando com um ✓ quem já apareceu numa batalha sua. Os ginásios são 8, numa ordem fixa inspirada em Kanto (Brock, Misty, Lt. Surge, Erika, Koga, Sabrina, Blaine e Giovanni), cada um com o time real dele nos níveis originais. Só o próximo ginásio ainda não vencido pode ser desafiado; vencer dá a insígnia e uma recompensa em dinheiro, os dois salvos no arquivo de save.

### Missões e NPCs

A tela de Missões junta 6 NPCs fixos, cada um com uma fala curta e um objetivo simples: vencer um número de batalhas, registrar um número de espécies na Pokédex, ou vencer um ginásio específico. O progresso de cada missão é calculado direto do que já está no save (número de vitórias, tamanho da Pokédex vista, insígnias conquistadas), sem precisar guardar nada duplicado. Completar uma libera um botão de "Reivindicar" que paga a recompensa em dinheiro na hora e marca a missão como cumprida.

O modo texto (`main.py`) e o roster fixo de 41 Pokémon (`pokebattle/data.py`) continuam existindo do jeito que sempre existiram, sem precisar de internet nem das dependências novas. São o que os testes automatizados usam.

## Rodando os testes

```bash
pip install -r requirements.txt
python3 -m pytest -v
```

São 148 testes automatizados, todos sobre lógica pura (não tocam na PokeAPI nem abrem janela nenhuma): a tabela de tipos, a fórmula de dano (imunidade, erro, STAB e crítico), os efeitos de status, as regras de turno da batalha (troca, item, fuga, prioridade, recuo, dreno, mudança de atributo, clima, ataque carregado, habilidades reagindo a golpes), o cálculo de stats com IV/EV/natureza, o save em disco, a progressão pós-batalha (XP, level up, evolução), os ginásios, os itens da loja, a IA dos treinadores (dificuldade cruzada com personalidade) e as missões. Tem também um script de fumaça manual pro modo gráfico (`tests/manual_gui_smoke.py`, roda com `xvfb-run -a python3 tests/manual_gui_smoke.py` num Linux sem tela): ele abre de verdade a janela e navega pelas telas (batalha, seleção de time, Pokédex, ginásio, loja, missões, onboarding de nome/inicial/apelido, progressão pós-vitória) com dados falsos, pra pegar erro de layout ou exceção antes de jogar. Não entra na suíte do pytest porque abre janela de verdade.

## Arquitetura

```
main.py                  # casca do modo texto (só print()/input())
main_gui.py               # casca do modo gráfico (janela Tkinter)
pokebattle/
  types_chart.py         # tabela de efetividade (dados puros)
  moves.py                # classe Move (golpe): dano, status, prioridade, dreno, atributo, clima, carga
  pokemon.py              # classe Pokemon: stats (com IV/EV/natureza), status, estágios de stat
  natures.py              # as 25 naturezas oficiais e o multiplicador de 10% que cada uma dá
  status.py               # efeitos de status: aplicar, checar se pode agir, dano residual
  abilities.py            # conjunto curado de habilidades com efeito mecânico de verdade
  battle.py               # calculate_damage() e a classe Battle: turnos, troca, item, fuga, clima
  ai.py                   # escolha de golpe do treinador adversário por dificuldade e personalidade
  items.py                # catálogo da PokéMart e a lógica de usar cada item
  quests.py               # NPCs fixos com missão, progresso e recompensa
  progression.py          # XP, EV ganho em batalha, level up, aprender golpe, evolução
  save.py                 # save em JSON: Pokédex vista, insígnias, dinheiro, itens, nome, missões
  gyms.py                 # sequência fixa de ginásios (líder, time, insígnia, recompensa, personalidade)
  data.py                 # roster fixo (41 Pokémon, só dano) + seletor por letra do modo texto
  ui.py                   # barra de HP e banners de texto do modo texto
  pokeapi.py              # cliente da PokeAPI com cache em disco
  roster.py               # monta um Pokemon a partir da PokeAPI (stats, golpes e habilidade reais)
  sprites.py              # baixa e cacheia a ilustração de um Pokémon
tests/
  test_types_chart.py
  test_damage.py
  test_battle.py
  test_battle_mechanics.py # prioridade, dreno, atributo, clima, ataque carregado
  test_data.py            # roster e o seletor por letra do modo texto
  test_status.py          # efeitos de status isolados
  test_team_battle.py     # time, troca, item e fuga na Battle
  test_natures_and_stats.py
  test_abilities.py
  test_roster_ability.py
  test_roster_moves.py    # extração de prioridade/dreno/atributo/clima/carga da PokeAPI
  test_pokeapi.py
  test_save.py
  test_progression.py
  test_gyms.py
  test_ai.py              # escolha de golpe por dificuldade e personalidade
  test_items.py           # catálogo e uso de item da PokéMart
  test_quests.py          # progresso e resgate de missão
  manual_gui_smoke.py     # script manual (não é pytest) pra testar as telas do modo gráfico
```

`battle.py` continua sem nenhum `print()` ou `input()` de propósito: dá pra testar a fórmula de dano e as regras de turno chamando as funções direto, sem precisar simular teclado nem abrir janela. Os testes de `test_damage.py` e `test_status.py`, por exemplo, usam RNGs falsos (`FixedRNG`/`StubRNG`) que trocam o `random` de verdade por valores fixos, pra conseguir afirmar coisas como "um golpe paralisado às vezes não consegue agir" sem depender de sorte na hora de rodar o teste.

`pokeapi.py` e `roster.py` ficam separados de `data.py` de propósito: um lado é o roster estático que não depende de rede, o outro é a integração com a PokeAPI que alimenta o modo gráfico. `progression.py`, `save.py`, `gyms.py`, `items.py` e `quests.py` também ficam de fora de `battle.py` de propósito: são coisas que só fazem sentido no modo gráfico (o modo texto não tem save, loja, ginásio nem missão), então misturar isso na lógica pura de turno só complicaria o que o modo texto usa. `status.py` não importa nada do resto do pacote (só recebe os objetos `Pokemon` já prontos), o que evita dependência circular com `pokemon.py` (que importa as constantes de status pra calcular ataque/velocidade efetivos). `ai.py` segue o mesmo raciocínio: importa só `types_chart.py`, não sabe nada de Tkinter nem de save, e devolve o `Move` escolhido pra quem chamou decidir o que fazer com ele.

## O que eu treinei com esse projeto

Programação orientada a objetos (as classes `Pokemon`, `Move`, `Battle`), modelagem de uma regra de negócio real com bastante matemática (a fórmula de dano tem uns 6 fatores diferentes se multiplicando, e o cálculo de stats soma IV, EV e natureza por cima disso), e separação entre lógica pura e interface. Essa separação se provou valiosa de novo quando apareceu uma segunda interface (o modo gráfico) reaproveitando exatamente a mesma `Battle`. Isso trouxe de bônus a possibilidade de testar tudo com injeção de dependência (o parâmetro `rng`), sem precisar mockar `input()` nem abrir janela nenhuma.

Na parte nova, treinei consumir uma API HTTP de verdade com cache em disco (pra não maltratar a PokeAPI nem deixar o jogo lento depois da primeira vez), paralelizar chamadas de rede com `ThreadPoolExecutor` (buscar os golpes candidatos de um Pokémon um por um seria bem mais lento), rodar trabalho de rede numa thread separada sem travar a interface gráfica (o padrão fica em `run_in_background`, no `main_gui.py`), modelar uma máquina de estados de status (o que cada status impede, cura ou causa de dano, e como isso se combina com confusão, que é independente do status "maior"), e desenhar animação simples com Canvas e `after()` do Tkinter sem travar o resto da interface. Também mexi bastante com persistência simples (o save em JSON) e com sequenciar uma progressão inteira (time > XP > evolução > ginásio > insígnia) em cima de módulos que, cada um sozinho, continuam pequenos e testáveis.

Na leva mais recente, `items.py` e `quests.py` repetem o molde de `abilities.py`: uma lista fixa de dataclasses e algumas funções puras em cima dela, fácil de testar sem depender de nada externo. A novidade foi escrever a primeira heurística de decisão do projeto (`ai.py`): em vez de só calcular dano, precisei pensar em quando um treinador troca de estratégia (HP baixo, personalidade defensiva) e como comparar golpes por dano esperado em vez de poder bruto.

## Próximos passos possíveis

Esse projeto é o primeiro de uma trilogia Pokémon que pretendo montar: a tabela de efetividade e a lógica de dano daqui já reaparecem no Team Builder e Analisador de Vantagens (o segundo da trilogia), que cruza os tipos de um time inteiro em vez de 1x1. Pra esse simulador especificamente, boa parte da lista de ideias antigas (golpes de status, seletor com filtro ao vivo, times maiores, save, ginásios, clima, loja, IA com personalidade, missões) já saiu do papel; o que ainda fica de fora é um modo torneio (várias rodadas até um campeão), efeito de ambiente por local de batalha (vulcão favorecendo Fogo, lago favorecendo Água), um avatar/roupa visual pro treinador, e uma loja de Pokémon de verdade em vez de só itens.
