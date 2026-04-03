# Simulador de Batalha Pokémon (CLI)

Jogo de batalha Pokémon 1x1, por turnos, direto no terminal. Sem framework, sem biblioteca de jogo, sem sprite: é só Python puro. A interface é de propósito a mais simples possível, porque o ponto do projeto não é a tela: é reproduzir com fidelidade a fórmula de dano e a tabela de efetividade de tipos dos jogos oficiais da Nintendo, com o cálculo acontecendo de verdade a cada turno.

## Como jogar

Não tem nenhuma dependência externa pra jogar, só Python 3.10 ou mais novo:

```bash
python3 main.py
```

Você escolhe seu Pokémon entre os 41 disponíveis, o computador escolhe um aleatoriamente pra te enfrentar, e a batalha começa. A cada turno você escolhe um movimento e o computador escolhe o dele. Quem ataca primeiro é definido pela Velocidade de cada Pokémon (empate é sorteado). A batalha acaba quando um dos dois desmaia.

## Escolhendo o Pokémon: o seletor por letra

Com 41 Pokémon, rolar uma lista numerada inteira toda vez ficou ruim de usar, por isso a tela de escolha agora deixa filtrar por letra antes de mostrar a lista:

```
(41 Pokémon disponíveis) Digite uma letra pra filtrar, ou só aperte Enter pra ver todos.

Filtrar por letra: p
  1. Pikachu
  2. Psyduck
  3. Poliwag

Digite o número do Pokémon (ou Enter pra filtrar de novo):
```

Digitar uma letra que não bate com nenhum Pokémon (ex: "x") avisa e deixa tentar de novo, e apertar Enter direto na lista filtrada volta pro filtro em vez de travar.

**Sobre a expectativa de "vai aparecendo conforme eu digito":** um filtro que atualiza a cada tecla digitada (sem precisar apertar Enter) exigiria ler o teclado tecla por tecla, o que em Python significa sair do `input()` simples e entrar numa biblioteca de terminal (`curses`, por exemplo) ou numa dependência externa, o que quebraria o ponto central do projeto, que é ser só Python puro, sem biblioteca nenhuma, rodando igual em qualquer terminal (Windows, Linux, Mac). O que entreguei é o equivalente prático dentro dessa restrição: digita a letra, aperta Enter uma vez, vê os Pokémon daquela letra na hora. Se no futuro você quiser o filtro tecla-a-tecla de verdade, isso é uma reescrita da tela de seleção usando `curses` (só funciona em Linux/Mac sem instalar nada a mais; no Windows precisaria da biblioteca `windows-curses`), o que vale considerar como um projeto à parte já que muda a filosofia "zero dependência" atual.

## Rodando os testes

```bash
pip install -r requirements.txt
python3 -m pytest -v
```

São 24 testes: a tabela de tipos, a fórmula de dano (imunidade, erro, STAB e crítico), as regras de turno da batalha, e o roster/seletor (todo Pokémon tem um moveset válido, sem espécie duplicada, filtro por letra funciona sem diferenciar maiúscula/minúscula, letra sem match devolve lista vazia em vez de quebrar, e o caso especial de nome com apóstrofo do Farfetch'd).

## O que o jogo cobre

O jogo aplica a fórmula de dano oficial: nível do atacante, poder do golpe, Ataque/Defesa (ou Ataque Especial/Defesa Especial, dependendo da categoria do golpe), STAB (bônus de 1.5x quando o golpe é do mesmo tipo de quem ataca), efetividade de tipo, chance de acerto crítico de 1/16 com 1.5x de dano, e a variação aleatória de 85% a 100% que os jogos aplicam em todo golpe. A tabela de efetividade tem os 18 tipos, incluindo Fada, e funciona tanto pra Pokémon de um tipo quanto de dois.

Os stats de cada Pokémon (HP, Ataque, Defesa, Ataque Especial, Defesa Especial, Velocidade) são calculados pela mesma fórmula dos jogos a partir do nível e dos base stats, assumindo IVs e EVs neutros. Não precisei simular a parte de otimização competitiva pra esse projeto, só a base da fórmula. Os turnos seguem a ordem de Velocidade, e um Pokémon que desmaia no meio do turno não chega a atacar.

Na tela, o jogo mostra a barra de HP em ASCII e as mensagens de "é super efetivo!", "não é muito eficaz...", "não afetou...", "o ataque errou!" e "acerto crítico!" conforme o resultado de cada golpe, terminando com vitória ou derrota. O roster tem 41 Pokémon (os 6 originais mais 35 novos, cobrindo boa parte do alfabeto e dos 18 tipos, incluindo os três iniciais evoluídos, as três aves lendárias, as cinco evoluções do Eevee e o Mewtwo), cada um com 4 golpes reais dos jogos, todos nível 50. Todo golpe é um golpe de dano direto de verdade (nome, tipo, poder e precisão reais). Nenhum reproduz efeito secundário, status, recuo ou mecânica de dois turnos, porque a lógica de batalha (`battle.py`) só sabe aplicar dano na hora, a mesma simplificação que os 6 Pokémon originais já usavam (ex: o Iron Tail do Pikachu, sem a chance de baixar Defesa).

## Arquitetura

O projeto separa a lógica do jogo da interface de linha de comando de propósito:

```
main.py                  # única parte que faz print()/input() (a "casca" do jogo)
pokebattle/
  types_chart.py         # tabela de efetividade (dados puros)
  moves.py                # classe Move (golpe)
  pokemon.py              # classe Pokemon (stats calculados a partir do nível)
  battle.py               # calculate_damage() e a classe Battle, 100% lógica, sem I/O
  data.py                 # roster (41 Pokémon com movesets) + seletor por letra
  ui.py                   # barra de HP e banners de texto
tests/
  test_types_chart.py
  test_damage.py
  test_battle.py
  test_data.py            # roster e o seletor por letra
```

O motivo de `battle.py` não ter nenhum `print()` ou `input()` é simples: dá pra testar a fórmula de dano e as regras de turno chamando as funções direto, sem precisar simular teclado. Os testes de `test_damage.py`, por exemplo, usam uma classe `FixedRNG` que troca o `random` de verdade por valores fixos, pra conseguir afirmar coisas como "um golpe do mesmo tipo do Pokémon sempre causa mais dano que um golpe de outro tipo, com tudo mais igual" sem depender de sorte na hora de rodar o teste. O seletor por letra segue a mesma lógica: `list_species_starting_with()` em `data.py` é uma função pura (só filtra uma lista, sem `print`/`input`), então dá pra testar sem simular teclado. Quem lê a letra digitada e mostra a lista na tela é o `main.py`, que continua sendo a única parte sem teste automatizado, do mesmo jeito que já era antes.

## O que eu treinei com esse projeto

Programação orientada a objetos (as classes `Pokemon`, `Move`, `Battle`), modelagem de uma regra de negócio real com bastante matemática (a fórmula de dano tem uns 6 fatores diferentes se multiplicando), e separação entre lógica pura e interface. Isso trouxe de bônus a possibilidade de testar tudo com injeção de dependência (o parâmetro `rng` do `calculate_damage`), sem precisar mockar `input()`. Na expansão do roster, apareceu de novo a mesma separação: o filtro por letra virou uma função pura testável em vez de lógica misturada dentro do loop de `input()` do `main.py`.

## Próximos passos possíveis

Esse projeto é o primeiro de uma trilogia Pokémon que pretendo montar: a tabela de efetividade e a lógica de dano daqui já reaparecem no Team Builder e Analisador de Vantagens (o segundo da trilogia), que cruza os tipos de um time inteiro em vez de 1x1. Pra esse simulador especificamente, as próximas ideias são golpes de status (não só dano), uma IA que escolhe o golpe mais efetivo em vez de aleatório e, se um dia fizer sentido abrir mão do "zero dependência", um seletor de verdade tecla-a-tecla usando `curses`.
