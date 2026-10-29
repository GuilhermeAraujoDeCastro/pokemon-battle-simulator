# Campanhas locais e importação

Na seleção de equipe, escolha um dos três slots e use "Salvar equipe no slot". A gravação inclui espécies, golpes completos, níveis, IVs, EVs, natureza, XP, apelidos, equipamentos, HP e progresso da campanha. "Carregar slot" restaura o conjunto salvo sem buscar Pokémon na rede. Fechar o aplicativo atualiza a equipe de uma campanha já salva; mudanças de seleção ainda não montadas devem ser salvas pelo botão antes de sair.

O arquivo `savegame.json` usa schema 2. Slots têm schema 1 e guardam a equipe junto do progresso. Um save antigo continua legível. Na primeira gravação após a atualização, o original ganha uma cópia `savegame.json.legacy.bak`, sem substituição posterior desse backup. O legado não tinha equipe completa para recuperar: monte a equipe e salve em um slot. Faça uma cópia de toda a pasta antes de testar com seu progresso pessoal.

Equipar um item transfere uma unidade do inventário para a seleção em uma gravação. Navegar para Pokédex e voltar mantém o vínculo na sessão. Cancelar a seleção devolve os equipamentos ainda não incorporados a uma campanha salva. Itens consumidos durante a batalha não voltam ao inventário.

A importação de texto valida todos os membros antes de consultar a PokeAPI. Níveis devem ser inteiros de 1 a 100; IVs de 0 a 31; EVs de 0 a 252 por atributo, com soma máxima de 510; e há no máximo quatro golpes. Valores inválidos são rejeitados com o campo indicado. O formato aceita de um a seis membros. A validação dessas faixas não comprova legalidade competitiva dos golpes de uma espécie.

```bash
python -m unittest discover -s tests -v
python -m compileall -q main_gui.py pokebattle web
python main_gui.py
```

As regressões de campanha usam saves temporários e dados locais. Elas verificam inventário, cancelamento repetido, restauração offline, backup legado e rejeição antes de chamadas de rede. Não execute dois processos desktop sobre o mesmo save: a escrita usa substituição atômica e trava entre threads deste processo, sem sincronização entre computadores ou processos.
