# AniPlay Experimental 2.7.42 · Revisão e testes

## Base e acesso ao aparelho

O commit-base é `1fe11d39891aa3662c338c81a5587b924cca8755`. Os 99 arquivos do checkout conferiram byte a byte com o ZIP 2.7.41 publicado. CRC válido e SHA-256 `cb4bfb77576c1caaebfb33caf22fecf4d9cb406b7fd61566764e5960ce2791cb`. O manifesto instalado foi lido e indicou AniPlay 2.7.41 no Kodi 21.2 com Estuary. O Android negou acesso ao estado da interface pelo Termux, a captura ficou vazia e o controle local não estava acessível. O perfil instalado foi preservado.

Os ensaios no Termux usaram as duas auditorias anteriores, consultas novas pela rede do celular e um dublê da API Python do Kodi com SQLite isolado. O dublê registra chamadas, campos e rotas. As verificações gráficas deste relatório vêm da leitura dos arquivos da Estuary no APK instalado. A vista efetivamente selecionada na tela, a qualidade decodificada e o áudio ouvido ficaram pendentes.

[Pacote-base](https://github.com/hugoferroz2525-stack/animesplay/releases/tag/v2.7.41-experimental) · [Auditoria dos catálogos](https://github.com/hugoferroz2525-stack/animesplay/blob/3d9b14ffea0662617ad28bfd35f23d3830268e65/auditoria/aniplay-2.7.40/relatorio.md) · [Evidências sanitizadas da revisão](EVIDENCIAS-2.7.42.json)

## Contagem, progresso e lista parcial

- No 2.7.41, Birdie Wing no HinataSoul enviou Label “Temporada 1 (25)”, Title “Temporada 1” e TotalEpisodes 25. A Estuary do APK usa ListItem.Label na lista larga e em outras vistas. O InfoWall usa ListItem.Title como título principal da área de vídeo. O banner consulta TotalEpisodes para exibir controles relacionados ao progresso. Por isso, preencher apenas Label deixava parte das vistas sem a contagem.
- No 2.7.42, o dublê recebeu “Temporada 1 (25 eps)” em ambos os rótulos. TotalEpisodes passou a representar os registros da edição e do servidor carregados até o fim. Birdie Wing teve 13+12 e a lista paginada mantém o 25º. O TMDB define intervalos oficiais e o contador usa a lista da fonte. Slime exibiu 26 registros disponíveis na temporada da fonte, com 24 episódios regulares associados e dois episódios 00 preservados.
- Erro de página, fallback vencido, página repetida sem novos itens, link inválido ou limite do paginador mantêm a lista parcial. Nesse caso o fluxo abre a lista disponível com aviso e omite o total completo. Snapshot registra apenas listas completas. Em caso de indisponibilidade do TMDB ou mapeamento inseguro, as páginas seguem a ordem e o rótulo publicados. Nenhuma lista inteira é desviada para “Outros episódios”.
- O cálculo de vistos consulta os URLs reais da lista e suas variantes. O dublê confirmou TotalEpisodes 3 e WatchedEpisodes 1 para três itens, sem depender da contagem do TMDB. O teste de limpeza manteve favorito, visto e posição de retomada no perfil temporário.

## Mapeamentos reproduzidos

A coluna TMDB indica a temporada e o número quando o addon tem evidência suficiente. O índice agregado só dá uma posição candidata para números repetidos. Nesses casos os registros preservam a URL e o título da fonte, sem receber duas fichas iguais. O JSON conserva número bruto, URL pública, temporada de destino, número local e indicador de associação para os casos exercitados.

| Caso | Número publicado e URL | Temporada anunciada localmente | Resultado no 2.7.42 |
|---|---|---|---|
| One Piece dublado | [611](https://www.hinatasoul.com/videos/523268) | sem indicação no card | número repetido, sem ficha atribuída. Posição candidata S15E31 |
| One Piece dublado | [611](https://www.hinatasoul.com/videos/522773) | sem indicação no card | número repetido, sem ficha atribuída. Posição candidata S15E31 |
| One Piece dublado | [612](https://www.hinatasoul.com/videos/523264) | sem indicação no card | número repetido, sem ficha atribuída. Posição candidata S15E32 |
| Naruto Shippuden dublado | [1](https://www.hinatasoul.com/videos/103533) | numeração corrida | TV 31910 · S1E1 · lacunas mantidas |
| Naruto Shippuden dublado | [157](https://www.hinatasoul.com/videos/524934) | numeração corrida | TV 31910 · S8E6 · lacunas mantidas |
| Naruto Shippuden dublado | [316](https://www.hinatasoul.com/videos/528243) | numeração corrida | TV 31910 · S14E21 · lacunas mantidas |
| Birdie Wing, segundo bloco | [1](https://www.hinatasoul.com/videos/237405) | 2 | TV 137390 · S1E14 |
| Birdie Wing, segundo bloco | [12](https://www.hinatasoul.com/videos/271565) | 2 | TV 137390 · S1E25 |
| Slime | [0](https://www.hinatasoul.com/videos/489124) | 2 | episódio 00 preservado sem ficha atribuída |
| Slime | [0](https://www.hinatasoul.com/videos/489177) | 2 | episódio 00 preservado sem ficha atribuída |
| Slime | [1](https://www.hinatasoul.com/videos/495041) | 2 | TV 82684 · S2E13 |
| Slime | [12](https://www.hinatasoul.com/videos/499271) | 2 | TV 82684 · S2E24 |

As três fontes externas preservaram os 842 e 1.185 URLs de One Piece e os 309 e 476 de Naruto Shippuden nas respectivas edições. Para One Piece e Naruto, removi a duplicação somente no cálculo dos intervalos: cada URL permanece. As sequências com registros sem número ou fora dos intervalos entram na lista normal. Os resultados foram reaplicados com as temporadas do Worker; ocorrências sem ficha seguem sem associação. A falta dos intervalos foi reproduzida separadamente no dublê. Para Birdie Wing e Slime, os dois segmentos foram consultados novamente no HinataSoul. Os dois filmes de Cosmos mantêm 968868 e 968870. [Temporadas de One Piece](https://www.themoviedb.org/tv/37854/seasons) · [Temporadas de Naruto Shippuden](https://www.themoviedb.org/tv/31910/seasons) · [Birdie Wing episódio 14](https://www.themoviedb.org/tv/137390/season/1/episode/14) · [Temporada 2 de Slime](https://www.themoviedb.org/tv/82684/season/2)

## Qualidade e regressão de rede

A opção manual Identificar resoluções foi removida do seletor externo. O rótulo considera a declaração da fonte, uma medição confirmada ou o cache daquela página de episódio e player. A ordem do player não determina o rótulo. A sondagem automática tem até dois workers, até três candidatos, 4 s de espera adicional após a página pública e leitura limitada de MP4. A verificação reaproveita o primeiro bloco de mídia para tentar localizar as dimensões. Falha ou limite de espera mantém Player N disponível. Uma tentativa inconclusiva é reutilizada por apenas dois minutos para evitar repetir toda a sondagem na próxima abertura. A cache de medida confirmada dura até 24 h. Só o nome da qualidade ganha cor.

No [episódio 849 dublado do HinataSoul](https://www.hinatasoul.com/videos/557129), as medições de rede independentes confirmaram 480p, 720p e 1080p. Demoraram entre 9 e 11 s por opção na rodada sem o limite do diálogo. Com essas medidas armazenadas no perfil isolado, a reabertura exibiu “Player 1: SD”, “Player 2: HD” e “Player 3: Full HD”. No ensaio frio limitado, os rótulos permaneceram genéricos. Selecionar mapeou a linha ao ID real do player no teste de rota. Cancelar preservou servidor e edição selecionados e encerrou a resolução. A altura validada por leitura de MP4 não é a leitura do decodificador do Kodi.

| Fonte | Páginas abertas | Episódios com mídia validada | Pendência |
|---|---:|---:|---|
| AniTube | 4 | 4 | vídeo, faixa audível e resolução no Kodi pendentes |
| AniTube22 | 4 | 0 | 12 opções sem mídia reconhecível; Kodi pendente |
| Bakashi | 6 | 6 | vídeo, faixa audível e resolução no Kodi pendentes |
| HinataSoul | 4 | 4 | vídeo, faixa audível e resolução no Kodi pendentes |

## Cobertura dos quatro JSONs

As unidades são URLs da auditoria e incluem aliases. Compatível significa referência registrada com tipo nominal compatível, confirmada em rede somente na amostra. “A verificar” inclui candidato por nome sem associação automática e IDs de coleção, OVA, ONA ou especial cuja relação exige verificar temporada ou edição. “Sem referência local” mede a cobertura do pacote, não o catálogo total do TMDB. Um conflito de formato do índice merece comparação com a origem. Dreamland foi marcado como filme no índice de formato antigo, mas a página atual do Bakashi declara TVSeries e API/Worker retornam a série homônima. O conflito ficou documentado, sem troca arbitrária do ID. O anexo detalha a classificação por TV, filme, OVA, ONA, especial e categorias sem formato confirmado.

| Fonte | URLs | Referência compatível | A verificar | Conflito de tipo no índice | Sem referência local |
|---|---:|---:|---:|---:|---:|
| bakashi | 5076 | 4735 | 329 | 2 | 10 |
| hinatasoul | 10058 | 12 | 1620 | 0 | 8426 |
| anitube22 | 10029 | 12 | 1615 | 0 | 8402 |
| anitube | 10029 | 12 | 1615 | 0 | 8402 |

### Origem dos campos na amostra

Foram examinadas 20 amostras, cinco por fonte. O JSON diferencia título e campo disponíveis na origem, ID nominal do pacote, dados recebidos pelo TMDB direto e pelo Worker, dúvidas de escopo e campos encaminhados ao dublê. A repetição das obras entre os dois AniTube e o HinataSoul foi usada para reaproveitar consultas de metadados. Os casos incluem TV, filme, OVA, ONA e especial. Para candidatos sem referência, a busca autenticada foi observada e não se preencheu a ficha automaticamente.

- **Bakashi.** Devils’ Crest retornou o mesmo ID TV por API e Worker. Maiden Rose apareceu como Hyakujitsu no Bara nas duas rotas e exige tratar a edição OVA. Itsuka Tenma no Kuro Usagi Picture Drama usa a temporada 0 da série no índice e não deve receber campos do episódio regular. Dreamland expôs a classificação conflitante descrita acima.
- **HinataSoul, AniTube e AniTube22.** One Piece teve série identificada. Cosmos retornou dois filmes próprios. Babel Nisei (OVA), Aggressive Retsuko (ONA) e Baccano! Specials foram testados na busca direta. A categoria especial e OVA exige identificar a edição ou o episódio antes de usar o candidato de série.
- **Níveis.** Birdie Wing TV 137390 e a temporada 217400 responderam nas duas rotas. O episódio 14 devolveu ID 4352541 pela API direta. O Worker devolveu a temporada agregada, cuja rota pode fornecer a ficha de episódio, e não retornou o card isolado desse endpoint na consulta. O episódio mantém sua URL pública mesmo quando a ficha estiver indisponível. Foram comparados título original, data/ano, sinopse, duração, pôster, still, gêneros, nota, elenco e papéis com a presença de cada campo registrada. A renderização visual da ficha nativa continua pendente.
- **Catálogo com/sem chave.** Birdie Wing e One Piece retornaram 137390 e 37854 pelo Worker com e sem chave. A opção Worker habilitada dá prioridade ao lote de cards no catálogo. Com chave e Worker desligado, a API direta retornou os mesmos IDs. Sem os dois, os cards continuaram sem enriquecimento remoto nessa amostra. Respostas são reaproveitadas no cache de metadados do perfil isolado. Corrigi dois caminhos que podiam usar fallback local do Bakashi em um endereço externo e restringi o uso de card do Worker a tipo/ID coerentes. Também removi a preferência automática pelo slug do Bakashi ao montar as temporadas de um servidor externo.

## Tempos antes e depois

Mesmo aparelho e mesmas consultas. Uma rodada por cenário, com cache inicial isolado e segunda abertura no mesmo perfil de teste. Usei Birdie Wing na busca de quatro fontes, na abertura do servidor e na temporada externa do HinataSoul; o seletor foi cronometrado no episódio 557129. O tempo do seletor termina no cancelamento imediato do dublê. As contagens instrumentam fetch de catálogo/TMDB/Worker e Client.open para player/mídia. Redirecionamentos HTTP internos e requisições do Kodi não entram nessa métrica. O aquecimento da busca reaproveita a lista paginada completa, evitando reanalisar cada HTML. O maior custo adicional é a sondagem automática na primeira abertura.

| Operação | Cache | 2.7.41 (s / req.) | 2.7.42 (s / req.) |
|---|---|---:|---:|
| Busca | frio | 1.988 / 4 | 1.914 / 4 |
| Busca | quente | 0.299 / 0 | 0.093 / 0 |
| Servidor | frio | 1.699 / 1 | 1.098 / 1 |
| Servidor | quente | 0.686 / 0 | 0.562 / 0 |
| Temporada | frio | 3.996 / 2 | 3.817 / 2 |
| Temporada | quente | 0.176 / 0 | 0.065 / 0 |
| Clique até seletor | frio | 2.457 / 1 | 5.999 / 7 |
| Clique até seletor | quente | 2.246 / 1 | 1.704 / 1 |

As pequenas diferenças na rodada fria de busca, servidor e temporada variam com a latência de rede. Na reabertura do player, a tentativa inconclusiva foi reaproveitada, o que evitou repetir a sondagem. O seletor com cache de medidas confirmadas mostrou os três rótulos em 2,332 s. O Worker e o TMDB foram exercitados com dados do perfil isolado. A limpeza de cache foi testada sem tocar no perfil instalado.

## Revisão transversal e pendências

| Achado | Impacto e encaminhamento |
|---|---|
| Estado completo confundido com HTML vazio, página repetida ou fallback vencido | Corrigido no snapshot de episódios. A lista parcial continua acessível e sinalizada. |
| Rótulo e título da temporada divergentes | Corrigido nos dois campos usados pela Estuary. O contador usa a opção de edição escolhida e a lista efetivamente carregada. |
| Inferência de ficha pelo número, inclusive repetido | Corrigido com verificação por linha. Preserva a navegação pela fonte, o rótulo, a URL e um indicador que impede restaurar ficha antiga no fluxo novo. |
| Busca de provedor reparseava HTML quente a cada abertura | Snapshot temporário separado para listas completas, reaproveitado entre catálogo e fluxo de servidores. |
| Escolha manual do TMDB no banco legado usa slug como chave | Uma escolha gravada pode afetar slug igual em outro host. A correção de esquema precisa de migração e verificação de escolhas antigas. Nenhum dado pessoal foi alterado nesta revisão. |
| Exportações e históricos gravados em versões antigas podem carregar números anteriores | A nova navegação bloqueia associações antigas quando a linha está marcada como não mapeada. Entradas .strm anteriores e históricos criados por versões antigas precisam de validação separada no Kodi. |
| AniTube22 ainda envia HTML de player sem fonte reconhecível na amostra | Mantido o diagnóstico do 2.7.41. Os players continuam selecionáveis; reprodução depende de mídia que a fonte disponibilize. |
| fetch de catálogo tem leitura sem limite explícito de tamanho e abertura de listas longas permanece síncrona | Próxima melhoria é limitar o corpo recebido e introduzir carregamento cancelável para listas longas. A sondagem de qualidade tem um limite próprio. |
| As métricas de cobertura são nominais em escala | Ancorar títulos e formatos ambíguos apenas com evidência por provedor. Evitar substituir lacunas por dados de obras parecidas. |

Passaram **26 testes** no Termux, incluindo as regressões de 2.7.41 e novas verificações de contagem, paginação parcial, ordenação, URLs repetidos, cache de qualidade, seleção/cancelamento e preservação de dados pessoais. O ZIP 2.7.42 passou na verificação CRC e os 100 arquivos foram comparados com o checkout. Não houve captura, instalação do 2.7.42 nem reprodução no Kodi Android. Ficaram pendentes no aparelho o fluxo completo Anime → Áudio → Servidor → Temporada → Episódio → Qualidade, áudio ouvido, resolução decodificada, início do vídeo, ficha nativa, progresso real e o teste de limpeza no perfil instalado.
