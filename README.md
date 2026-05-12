# Simulador de Batalha Pokémon

[![tests](https://github.com/GuilhermeAraujoDeCastro/Batalhapokemonpython/actions/workflows/tests.yml/badge.svg)](https://github.com/GuilhermeAraujoDeCastro/Batalhapokemonpython/actions/workflows/tests.yml)

Jogo de batalha Pokémon por turnos. Nasceu como um exercício de Python puro, sem framework, sem biblioteca de jogo, sem sprite: o ponto do projeto era reproduzir com fidelidade a fórmula de dano e a tabela de efetividade de tipos dos jogos oficiais da Nintendo, com o cálculo acontecendo de verdade a cada turno. Isso ainda é verdade pro modo texto (`main.py`).

O projeto ganhou depois um modo gráfico (`main_gui.py`) bem mais ambicioso: interface em Tkinter, sprites de verdade baixados da PokeAPI, o Pokédex inteiro em vez de um roster fixo, times de até 6 Pokémon, IV/EV/natureza de verdade, habilidades com efeito mecânico, XP/level up/evolução, uma sequência de 8 ginásios com insígnias, save em disco e animação de golpe na tela de batalha. Depois entraram mecânicas de combate mais fundas (prioridade, recuo, dreno de HP, golpes que sobem e descem atributo, clima, ataques carregados de dois turnos), uma PokéMart de verdade, personalização do treinador (nome, Pokémon inicial, apelido), dificuldade e personalidade de IA pros treinadores adversários, e um sisteminha de missões com NPCs fixos. Isso quebra o "zero dependência" original de propósito. Numa leva mais recente entraram modo torneio, PvP local, itens segurados, mega evolução, troca entre saves, som, avatar do treinador, replay de batalha, treino de EV, IA adaptativa, exportar/importar time, uma terceira interface web (Flask) reaproveitando o roster fixo, Pokémon shiny, mais habilidades com efeito real, conquistas, modo Nuzlocke e CI no GitHub Actions, tudo detalhado mais abaixo. Os modos convivem no mesmo repositório porque compartilham a mesma lógica de batalha (`pokebattle/battle.py`); só a interface (e o tanto de mecânica em cima) muda.

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

### Avatar, som e barra de HP animada

Junto da cor escolhida na tela de time (um círculo colorido com a inicial do nome, sem sprite de terceiro nenhum, do mesmo jeito que o resto do projeto nunca usa asset visual de fora da PokeAPI), o avatar aparece na tela de time e no painel de batalha do jogador (`pokebattle/avatar.py`). O modo gráfico ganhou som (`pokebattle/audio.py`): efeitos de golpe acertando, desmaio, vitória e um jingle de ginásio, todos sintetizados na hora com a biblioteca padrão (tons puros de onda senoidal, via `wave`) e cacheados em `.pokecache/audio/`, sem asset de terceiro e sem problema de direito autoral, e tocados com `pygame.mixer` de um jeito à prova de ambiente sem placa de som (sem dispositivo, o jogo continua rodando em silêncio, nunca trava). A barra de HP deixou de saltar direto pro valor novo: agora ela anima em pequenos passos (tween) até o valor certo, mesmo padrão de `after()` que a animação de dano já usava.

### Itens segurados, mega evolução e loja de Pokémon

Um Pokémon pode segurar um item o tempo todo, com efeito mecânico durante a batalha inteira, diferente da Mochila, que é consumida manualmente num turno. Só um conjunto curado tem efeito real (`pokebattle/held_items.py`, no mesmo espírito de `abilities.py`): Leftovers cura 1/16 do HP máximo no fim do turno, Choice Band aumenta 50% o dano de golpes físicos, e berries curam um status específico sozinhas (ou qualquer um, no caso do Mirtilo Lum), se consumindo no processo. Segurar a Mega Stone certa (também um item segurado) mega evolui um punhado de espécies bem conhecidas (Charizard, Mewtwo, Gyarados, Lucario, Alakazam) no início da batalha; a mega evolução é temporária e reverte no fim, do jeito que os jogos fazem (`pokebattle/mega.py`). Os itens segurados são comprados na PokéMart e equipados na tela de time; a mesma loja ganhou uma seção de "Loja de Pokémon", onde um Pokémon aleatório de verdade entra pra sua coleção por um preço bem mais alto que qualquer item ($8000), guardado no save e disponível na tela de time pra entrar no time sem precisar buscar.

### PvP local, torneio, treino de EV e IA adaptativa

O PvP local (hot-seat) deixa dois jogadores no mesmo computador se enfrentarem sem rede nenhuma: cada um escolhe 1 Pokémon, e os dois escolhem golpe por turno numa tela que se alterna, com um intervalo de "passe o computador" entre um jogador e o outro. O modo torneio (`pokebattle/tournament.py`) monta um bracket de eliminação simples com o jogador e 3 rivais controlados por IA; as partidas do jogador acontecem na tela de batalha de sempre, e as que não envolvem o jogador são simuladas na hora, turno a turno, reaproveitando `Battle` e a mesma `ai.choose_move` que já decide o golpe dos treinadores adversários. O treino de EV deixa gastar itens como Proteína e Ferro num Pokémon do time atual pra reforçar um stat específico, em vez de só ganhar EV passivamente ao vencer batalha. Isso usa o Pokémon já montado da sessão, então só funciona depois de começar pelo menos uma batalha. E a IA dos treinadores fora de ginásio deixou de sortear a personalidade só uniformemente: agora ela pesa pela taxa de vitória/derrota do jogador salva no save (`ai.adaptive_personality`), favorecendo um perfil mais estratégico quando o jogador está mandando bem e um mais brando quando está apanhando bastante.

### Troca, exportar/importar time e replay

Dá pra trocar um Pokémon com um amigo exportando ele pra um arquivo (`pokebattle/trade.py`) e mandando por fora, sem precisar sincronizar dois `savegame.json` ao mesmo tempo. O time inteiro também pode ser exportado/importado como texto, num formato parecido com o do Pokémon Showdown (`pokebattle/teamcodec.py`), pra compartilhar uma build sem mandar o save inteiro. E toda batalha jogada até o fim salva um replay em JSON (`pokebattle/replay.py`, pasta `replays/`, fora do git), e uma tela própria lista os replays salvos e reproduz o log turno a turno.

### Shiny, mais habilidades e conquistas

Todo Pokémon montado no modo gráfico tem 1/4096 de chance de ser shiny (a mesma raridade dos jogos principais modernos), com a variante de sprite da própria PokeAPI e destaque visual (✨ e nome dourado) na tela de batalha. O conjunto curado de habilidades com efeito mecânico cresceu: Wonder Guard (só toma dano de golpe super efetivo), Speed Boost (sobe Velocidade sozinho no fim de cada turno), Sand Veil (reduz a precisão de quem ataca na tempestade de areia), Water Absorb/Volt Absorb (imunidade ao tipo + cura) e Poison Heal (cura em vez de sofrer o dano residual do veneno). E um sistema de conquistas (`pokebattle/achievements.py`) desbloqueia sozinho (sem botão de resgatar, diferente das missões) em marcos como vencer sem perder ninguém, completar a Pokédex, vencer os 8 ginásios, encontrar o primeiro shiny ou ser campeão de um torneio.

### Ambiente por local de batalha e modo Nuzlocke

Cada arena pode favorecer um tipo, tratado como um "clima fixo" que não expira sozinho (`pokebattle/locations.py`): vulcão favorece Fogo, lago favorece Água, caverna/deserto favorecem Pedra/Terra/Aço, geleira favorece Gelo. Ginásios de tipo óbvio já nascem numa arena correspondente (o de Blaine no vulcão, o de Misty no lago), e batalhas comuns sorteiam um local a cada vez (a maioria continua em campo aberto, sem efeito nenhum). O modo Nuzlocke, opcional (checkbox na tela de time), muda uma regra só: quem desmaia numa batalha é removido permanentemente do time, e Revive para de funcionar, sem mexer em nada da lógica de batalha em si.

O modo texto (`main.py`) e o roster fixo de 41 Pokémon (`pokebattle/data.py`) continuam existindo do jeito que sempre existiram, sem precisar de internet nem das dependências novas. São o que os testes automatizados usam, e também a base da versão web, abaixo.

## Modo web (`web/app.py`): a mesma lógica, de novo, numa terceira interface

```bash
pip install -r requirements.txt
python3 web/app.py
# abre http://127.0.0.1:5000 no navegador
```

Servidor Flask reaproveitando exatamente o roster fixo de `pokebattle/data.py` e a classe `Battle` de `pokebattle/battle.py`: a mesma lógica pura dos outros dois modos, sem duplicação. É a terceira prova de que separar lógica de interface valeu a pena: primeiro apareceu o modo gráfico reaproveitando a `Battle` do modo texto, agora aparece uma interface web reaproveitando a mesma `Battle` de novo, dessa vez com HTTP em vez de Tkinter ou terminal. Cada partida fica guardada em memória de processo, por sessão (cookie), não em banco nem em disco, então reiniciar o servidor zera as partidas em andamento; é um app de demonstração local, não pensado pra escala. Os templates (`web/templates/`) usam a mesma paleta de cor do modo gráfico, pra parecer a mesma família visual apesar da interface totalmente diferente.

## Rodando os testes

```bash
pip install -r requirements.txt
python3 -m pytest -v
```

São 266 testes automatizados, todos sobre lógica pura (não tocam na PokeAPI nem abrem janela nenhuma, e a versão web é testada com `app.test_client()` do Flask, que também não abre socket de verdade): a tabela de tipos, a fórmula de dano (imunidade, erro, STAB e crítico), os efeitos de status, as regras de turno da batalha (troca, item, fuga, prioridade, recuo, dreno, mudança de atributo, clima fixo de local, ataque carregado, habilidades reagindo a golpes, itens segurados), o cálculo de stats com IV/EV/natureza, o save em disco, a progressão pós-batalha (XP, level up, evolução), os ginásios, os itens da loja, a IA dos treinadores (dificuldade cruzada com personalidade, e a variante adaptativa), as missões, as conquistas, o modo Nuzlocke, a mega evolução, o bracket de torneio, exportar/importar time e troca, e as rotas da versão web. Tem também um script de fumaça manual pro modo gráfico (`tests/manual_gui_smoke.py`, roda com `xvfb-run -a python3 tests/manual_gui_smoke.py` num Linux sem tela, ou direto num Windows/Mac com tela de verdade): ele abre a janela de verdade e navega pelas telas (batalha, seleção de time, Pokédex, ginásio, loja, missões, onboarding, progressão pós-vitória, PvP local, torneio, Nuzlocke, mega evolução, conquistas, treino de EV, replay, avatar, troca) com dados falsos, pra pegar erro de layout ou exceção antes de jogar. Não entra na suíte do pytest porque abre janela de verdade.

## Arquitetura

```
main.py                  # casca do modo texto (só print()/input())
main_gui.py               # casca do modo gráfico (janela Tkinter)
web/
  app.py                 # casca da versão web (Flask), reaproveita data.py + battle.py
  templates/             # choose.html, battle.html, base.html (Jinja2)
  static/style.css       # mesma paleta de cor do modo gráfico
pokebattle/
  types_chart.py         # tabela de efetividade (dados puros)
  moves.py                # classe Move (golpe): dano, status, prioridade, dreno, atributo, clima, carga
  pokemon.py              # classe Pokemon: stats (com IV/EV/natureza), status, estágios de stat
  natures.py              # as 25 naturezas oficiais e o multiplicador de 10% que cada uma dá
  status.py               # efeitos de status: aplicar, checar se pode agir, dano residual
  abilities.py            # conjunto curado de habilidades com efeito mecânico de verdade
  held_items.py           # itens segurados: Leftovers, Choice Band, berries que curam status
  mega.py                  # mega evolução curada a um punhado de espécies, ativada por item segurado
  locations.py            # arenas com "clima fixo" (vulcão, lago, caverna, geleira)
  nuzlocke.py              # regra pura do modo Nuzlocke (quem sobrevive, Revive desabilitado)
  achievements.py          # catálogo de conquistas, desbloqueadas sozinhas a partir do save
  tournament.py            # bracket de eliminação simples + simulação de partida IA-vs-IA
  teamcodec.py             # exportar/importar time como texto (formato tipo Showdown)
  trade.py                 # exportar/importar um único Pokémon pra troca entre saves
  avatar.py                 # paleta/inicial do avatar do treinador (o desenho fica no main_gui.py)
  audio.py                  # síntese e cache dos efeitos sonoros (sem asset de terceiro)
  replay.py                 # grava/lê o log de uma batalha turno a turno, em JSON
  battle.py               # calculate_damage() e a classe Battle: turnos, troca, item, fuga, clima, local
  ai.py                   # escolha de golpe por dificuldade/personalidade + personalidade adaptativa
  items.py                # catálogo da PokéMart (cura, EV) e a lógica de usar cada item
  quests.py               # NPCs fixos com missão, progresso e recompensa
  progression.py          # XP, EV ganho em batalha, level up, aprender golpe, evolução
  save.py                 # save em JSON: Pokédex, insígnias, dinheiro, itens, conquistas, Nuzlocke...
  gyms.py                 # sequência fixa de ginásios (líder, time, insígnia, recompensa, personalidade, local)
  data.py                 # roster fixo (41 Pokémon, só dano) + seletor por letra do modo texto/web
  ui.py                   # barra de HP e banners de texto do modo texto
  pokeapi.py              # cliente da PokeAPI com cache em disco
  roster.py               # monta um Pokemon a partir da PokeAPI (stats, golpes, habilidade, shiny)
  sprites.py              # baixa e cacheia a ilustração de um Pokémon (normal e shiny)
tests/
  test_types_chart.py
  test_damage.py
  test_battle.py
  test_battle_mechanics.py # prioridade, dreno, atributo, clima, ataque carregado
  test_battle_hooks.py     # itens segurados e clima fixo de local dentro da Battle
  test_data.py            # roster e o seletor por letra do modo texto
  test_status.py          # efeitos de status isolados
  test_team_battle.py     # time, troca, item e fuga na Battle
  test_natures_and_stats.py
  test_abilities.py       # inclui Wonder Guard, Speed Boost, Sand Veil, absorção de tipo, Poison Heal
  test_roster.py          # shiny (1/4096) e overrides de IV/natureza do build_pokemon
  test_roster_ability.py
  test_roster_moves.py    # extração de prioridade/dreno/atributo/clima/carga da PokeAPI
  test_pokeapi.py
  test_save.py
  test_progression.py
  test_gyms.py            # inclui o local de cada ginásio
  test_ai.py              # escolha de golpe por dificuldade/personalidade + personalidade adaptativa
  test_items.py           # catálogo, uso de item da PokéMart e itens de treino de EV
  test_held_items.py
  test_mega.py
  test_locations.py
  test_nuzlocke.py
  test_achievements.py
  test_tournament.py
  test_teamcodec.py
  test_trade.py
  test_avatar.py
  test_audio.py
  test_replay.py
  test_quests.py          # progresso e resgate de missão
  test_web.py              # rotas da versão web, via app.test_client() do Flask
  manual_gui_smoke.py     # script manual (não é pytest) pra testar as telas do modo gráfico
```

`battle.py` continua sem nenhum `print()` ou `input()` de propósito: dá pra testar a fórmula de dano e as regras de turno chamando as funções direto, sem precisar simular teclado nem abrir janela. Os testes de `test_damage.py` e `test_status.py`, por exemplo, usam RNGs falsos (`FixedRNG`/`StubRNG`) que trocam o `random` de verdade por valores fixos, pra conseguir afirmar coisas como "um golpe paralisado às vezes não consegue agir" sem depender de sorte na hora de rodar o teste.

`pokeapi.py` e `roster.py` ficam separados de `data.py` de propósito: um lado é o roster estático que não depende de rede, o outro é a integração com a PokeAPI que alimenta o modo gráfico e a web. `progression.py`, `save.py`, `gyms.py`, `items.py` e `quests.py` também ficam de fora de `battle.py` de propósito: são coisas que só fazem sentido no modo gráfico (o modo texto não tem save, loja, ginásio nem missão), então misturar isso na lógica pura de turno só complicaria o que o modo texto usa. `status.py` não importa nada do resto do pacote (só recebe os objetos `Pokemon` já prontos), o que evita dependência circular com `pokemon.py` (que importa as constantes de status pra calcular ataque/velocidade efetivos). `ai.py` segue o mesmo raciocínio: importa só `types_chart.py`, não sabe nada de Tkinter nem de save, e devolve o `Move` escolhido pra quem chamou decidir o que fazer com ele.

A leva mais recente de módulos segue o mesmo molde: `held_items.py`, `locations.py`, `nuzlocke.py` e `achievements.py` são hooks aditivos que `battle.py`/`main_gui.py` chamam, mas que não mudam nada do comportamento já testado quando não se aplicam (um Pokémon sem item segurado, uma batalha sem local especial). `mega.py` reaproveita `roster._STAT_KEYS` do mesmo jeito que `progression.evolve_pokemon` já fazia, porque mega evoluir é, mecanicamente, o mesmo tipo de operação (trocar tipo/stats a partir de dados já buscados). `tournament.py` só entende "nomes de participante" no bracket em si (quem é o jogador e quem é IA fica por conta de `main_gui.py`), pra poder testar o avanço de fase sem precisar montar Pokémon de verdade. `teamcodec.py` e `trade.py` compartilham a mesma "ficha" de Pokémon (um dict só com tipos primitivos), porque exportar um time inteiro e trocar um único Pokémon são, no fundo, a mesma serialização aplicada a tamanhos diferentes. `audio.py` sintetiza os próprios efeitos sonoros com a biblioteca padrão em vez de embutir um asset de terceiro, e todo o caminho de reprodução é protegido por try/except. Sem isso, o CI (que roda sem placa de som) quebraria.

## O que eu treinei com esse projeto

Programação orientada a objetos (as classes `Pokemon`, `Move`, `Battle`), modelagem de uma regra de negócio real com bastante matemática (a fórmula de dano tem uns 6 fatores diferentes se multiplicando, e o cálculo de stats soma IV, EV e natureza por cima disso), e separação entre lógica pura e interface. Essa separação se provou valiosa de novo quando apareceu uma segunda interface (o modo gráfico) reaproveitando exatamente a mesma `Battle`. Isso trouxe de bônus a possibilidade de testar tudo com injeção de dependência (o parâmetro `rng`), sem precisar mockar `input()` nem abrir janela nenhuma.

Na parte nova, treinei consumir uma API HTTP de verdade com cache em disco (pra não maltratar a PokeAPI nem deixar o jogo lento depois da primeira vez), paralelizar chamadas de rede com `ThreadPoolExecutor` (buscar os golpes candidatos de um Pokémon um por um seria bem mais lento), rodar trabalho de rede numa thread separada sem travar a interface gráfica (o padrão fica em `run_in_background`, no `main_gui.py`), modelar uma máquina de estados de status (o que cada status impede, cura ou causa de dano, e como isso se combina com confusão, que é independente do status "maior"), e desenhar animação simples com Canvas e `after()` do Tkinter sem travar o resto da interface. Também mexi bastante com persistência simples (o save em JSON) e com sequenciar uma progressão inteira (time > XP > evolução > ginásio > insígnia) em cima de módulos que, cada um sozinho, continuam pequenos e testáveis.

Na leva mais recente, `items.py` e `quests.py` repetem o molde de `abilities.py`: uma lista fixa de dataclasses e algumas funções puras em cima dela, fácil de testar sem depender de nada externo. A novidade foi escrever a primeira heurística de decisão do projeto (`ai.py`): em vez de só calcular dano, precisei pensar em quando um treinador troca de estratégia (HP baixo, personalidade defensiva) e como comparar golpes por dano esperado em vez de poder bruto.

Na leva mais recente de todas, o destaque foi `web/app.py`: montar uma terceira interface HTTP em cima da mesma `Battle` provou de novo que a separação lógica/interface do início do projeto continua compensando, dessa vez com o estado da partida guardado em memória por sessão (cookie) em vez de objeto Python direto na tela. `tournament.py` foi a primeira vez que precisei simular uma batalha inteira sem interface nenhuma no meio (turno a turno, os dois lados por IA, até sobrar um vencedor), o que também me ensinou a tratar o caso de borda de um bracket parcialmente resolvido sem estourar índice. E `audio.py` foi um jeito diferente de resolver "preciso de um asset": em vez de baixar ou empacotar um arquivo de som de verdade, sintetizei tons puros com a biblioteca padrão (`wave` + seno), o que resolve o problema de direito autoral de vez e ainda cacheia como qualquer outro asset gerado do projeto.

## Próximos passos possíveis

Esse projeto é o primeiro da minha trilogia Pokémon. A tabela de efetividade e a lógica de dano daqui reaparecem no Team Builder (o segundo), que cruza os tipos de um time inteiro em vez de 1x1, e o Extrator de Dados fecha a trilogia do lado de análise. Pra esse simulador especificamente, a lista de ideias antigas (golpes de status, seletor com filtro ao vivo, times maiores, save, ginásios, clima, loja, IA com personalidade, missões, torneio, local de batalha, avatar, loja de Pokémon, PvP local, itens segurados, mega evolução, troca, som, HP animado, replay, treino de EV, IA adaptativa, exportar/importar time, versão web, mais habilidades, shiny, conquistas, Nuzlocke, CI) já saiu do papel inteira. O que ainda fica de fora, pensando num próximo lote: mega evolução em formas alternativas regionais, um modo torneio com times maiores que 3 rivais, e sincronizar a versão web com o mesmo save.json do modo gráfico (hoje as duas partes de estado vivem separadas de propósito, cada uma na sua interface).
