# Revisão do AniPlay Experimental 2.7.40

## Pacote, aparelho e método

- O pacote distribuído confirma a versão **2.7.40** no addon.xml. CRC válido para os 98 arquivos e SHA-256 979c96261a7cc1d41b5e6d732856a55226fa56809890dfe10a9a627b62533e10. O commit da distribuição é 3f8a264122fdf9215e466c3d2d50704feff004b4. Ajustes posteriores ficaram fora da revisão. [ZIP testado](https://raw.githubusercontent.com/hugoferroz2525-stack/animesplay/3f8a264122fdf9215e466c3d2d50704feff004b4/AniPlay-2.7.40-experimental.zip)
- A instalação Android acessível pelo armazenamento é **Kodi 21.2, Estuary e AniPlay Experimental 2.7.37**. A versão do Kodi veio do cabeçalho do log. A versão do addon veio do manifesto instalado. Dez arquivos diferem do ZIP, incluindo multisite, playback, network, views e os extratores. O Android negou acesso ao estado gráfico pelo dumpsys e o screencap gerou arquivo vazio. As portas locais 8080 e 9090 estavam fechadas na sondagem. O pacote instalado e o perfil do Kodi foram preservados.
- O ZIP da auditoria anterior passou no CRC. Foram reaproveitados os quatro JSONs e listas de episódios oriundos da travessia de 4.617 páginas. O catálogo inteiro ficou como referência e a amostra de rede desta revisão foi consultada novamente em 24 de novembro de 2026 pelo Termux no celular. [Auditoria de catálogo](https://github.com/hugoferroz2525-stack/animesplay/tree/3d9b14ffea0662617ad28bfd35f23d3830268e65/auditoria/aniplay-2.7.40)
- Nos testes com dublê, o código extraído rodou com módulos mínimos da API do Kodi e perfil SQLite temporário. A matriz distingue respostas de rede, chamadas registradas pelo dublê e conclusões de leitura. Validação de mídia significa assinatura MP4 ou HLS reconhecida pelo resolvedor do pacote. Nos MP4, a altura vem da leitura dos metadados pelo próprio addon. A reprodução, a faixa audível e o resultado visual em Estuary ficaram pendentes no Kodi. Não há capturas do aparelho.
- [Dados de teste em JSON](dados.json) incluem as URLs públicas dos episódios, tempos, erros sanitizados e propriedades enviadas ao dublê. Os arquivos de cache, cabeçalhos privados, URLs de mídia e configurações pessoais ficaram fora da entrega.

## Matriz de testes

| ID | Tela ou fluxo | Método | Resultado |
|---|---|---|---|
| N01 | Menu principal, busca, filtros, continuar, assistidos, histórico, lista e configurações | Dublê | 11 entradas no menu. Rotas, rótulos, ícones e abertura de configurações registrados. Telas vazias de perfil novo exibiram caminhos de saída. |
| N02 | Catálogo e busca | Rede e código | Busca One Piece nas quatro fontes retornou 181 linhas antes do agrupamento. O catálogo inicial usa páginas iniciais externas e índice local; próxima página repete a enumeração. |
| N03 | Gênero, formato, ano e status | Dublê e HTML arquivado | Quatro grupos de filtros, opções de formato e URLs construídas. A execução de cada combinação da interface ficou pendente. |
| N04 | Lançamentos e calendário | Rede e dublê | A home do Bakashi forneceu 16 cards de episódios e a API 137 entradas em 8 dias na amostra. O dublê confirmou agrupamento por data e eliminação de duplicatas com mesma data, título e episódio. |
| N05 | Anime → Áudio → Servidor → Temporada → Episódio → Qualidade | Dublê com dados da auditoria e rede nas pontas | Áudio explícito filtra o servidor e o desconhecido permanece separado. Birdie Wing expõe o segundo bloco como temporada 2. O cancelamento de qualidade impediu a entrega de mídia. |
| N06 | Favoritos, histórico de reprodução e menu de contexto | Dublê e código | Adição de favorito e menus gerados no perfil temporário. Contexto de obra oferece salvar, semelhantes, elenco, trailer, exportar e identificar. Episódio recebe ajuste de abertura. Histórico depende de onAVStarted no serviço real. |
| P01 | Página, obtenção de mídia e reprodução | Rede | 18 páginas de episódio abriram; em 14 houve pelo menos uma opção com mídia validada. Início e tempo de reprodução no Kodi ficaram pendentes em todos os casos. |
| P02 | Cancelar qualidade e retomar, link indisponível | Dublê e rede | Cancelar qualidade ou retomada gera setResolvedUrl(False). Falha simulada HTTP 404 gera aviso e resolução falsa. Em HinataSoul e AniTube um player realmente retornou 404 em One Piece dublado ep. 1. |
| P03 | Episódio certo, áudio e resolução | Rede | Títulos públicos conferem com o episódio solicitado na amostra. MP4 reconhecidos têm 360, 480, 720 ou 1080 linhas. Áudio vem dos rótulos das páginas e players; decodificação e audição no Kodi pendentes. |
| G01 | Digimon, Birdie Wing, Slime e Cosmos | Termux com dados da auditoria | Agrupamento reproduzido pelo código do ZIP. IDs, grupos e divergências detalhados abaixo. |
| G02 | One Piece e Naruto Shippuden | Termux com episódios arquivados | Registros com o mesmo número perderam opção individual em One Piece. Lacunas em Naruto dublado preservaram 309 cards no HinataSoul. |
| M01 | Série, filme, temporada, episódio e ficha | Worker, TMDB público arquivado e dublê | IDs, japonês, duração, data, elenco e arte rastreados; título decorado na lista e título puro na ficha. Comparação visual no Kodi pendente. |
| M02 | Capa, nota, miniatura, selos e amarelo | Código e dublê | Nota e arte podem existir na tag mesmo sem selo. Posição, redundância visual, contraste e renderização real ficaram pendentes em Estuary. |
| C01 | Frio, reabertura, expiração, rede indisponível e limpar | Rede e SQLite de teste | Rede, cache quente e cache antigo reproduzidos. Limpeza preservou favorito e retomada do perfil de teste. |
| C02 | Retomar, visto e persistência | Dublê e SQLite | 9 s descartados; posição de 25 s retomável e preservada após limpar; 110/120 s marcaram visto. Eventos do player real e alternância entre fontes pendentes no Kodi. |

## Rede e reprodução por fonte

Na tabela, cada linha representa a página pública de um episódio. A primeira página de lista abriu em todas as edições amostradas. Os retornos HLS do Bakashi foram verificados como manifestos. A amostra não mediu altura das variantes HLS. As opções do MP4 foram avaliadas separadamente e as falhas preservadas no JSON.

| Fonte e edição | Episódio | Mídia validada no Termux | Resultado Kodi |
|---|---|---|---|
| Bakashi · Naruto Shippuden | [Episodio 1](https://bakashi.top/ep/naruto-shippuden-1-episodio-1) | Legendado HLS | pendente |
| Bakashi · Naruto Shippuden | [Episodio 500](https://bakashi.top/ep/naruto-shippuden-1-episodio-500) | Legendado HLS | pendente |
| Bakashi · One Piece | [Episodio 1](https://bakashi.top/ep/one-piece-1-episodio-1) | Legendado HLS | pendente |
| Bakashi · One Piece | [Episodio 1180](https://bakashi.top/ep/one-piece-1-episodio-1180) | Legendado HLS | pendente |
| Bakashi · One Piece Dublado | [Episodio 1](https://bakashi.top/ep/one-piece-dublado-1-episodio-1) | Dublado HLS | pendente |
| Bakashi · One Piece Dublado | [Episodio 891](https://bakashi.top/ep/one-piece-dublado-1-episodio-891) | Dublado HLS | pendente |
| HinataSoul · One Piece - Dublado | [One Piece - Dublado ep 1](https://www.hinatasoul.com/videos/492294) | 360p, 720p · falha HTTP 404 | pendente |
| HinataSoul · One Piece - Dublado | [One Piece - Dublado ep 849](https://www.hinatasoul.com/videos/557129) | 480p, 720p, 1080p | pendente |
| HinataSoul · One Piece | [One Piece ep 1](https://www.hinatasoul.com/videos/509115) | 360p, 720p, 1080p | pendente |
| HinataSoul · One Piece | [One Piece ep 1180](https://www.hinatasoul.com/videos/580081) | 480p, 720p, 1080p | pendente |
| AniTube22 · One Piece - Dublado | [Assistir One Piece - Dublado ep 1 - Anitube](https://www.anitube22.vip/video/492294) | nenhuma · mídia ausente nas opções | pendente |
| AniTube22 · One Piece - Dublado | [Assistir One Piece - Dublado ep 849 - Anitube](https://www.anitube22.vip/video/557129) | nenhuma · mídia ausente nas opções | pendente |
| AniTube22 · One Piece | [Assistir One Piece ep 1 - Anitube](https://www.anitube22.vip/video/509115) | nenhuma · mídia ausente nas opções | pendente |
| AniTube22 · One Piece | [Assistir One Piece ep 1180 - Anitube](https://www.anitube22.vip/video/580081) | nenhuma · mídia ausente nas opções | pendente |
| AniTube · One Piece - Dublado | [Assistir One Piece - Dublado ep 1 - Anitube](https://www.anitube.vip/video/492294) | 360p, 720p · falha HTTP 404 | pendente |
| AniTube · One Piece - Dublado | [Assistir One Piece - Dublado ep 849 - Anitube](https://www.anitube.vip/video/557129) | 480p, 720p, 1080p | pendente |
| AniTube · One Piece | [Assistir One Piece ep 1 - Anitube](https://www.anitube.vip/video/509115) | 360p, 720p, 1080p | pendente |
| AniTube · One Piece | [Assistir One Piece ep 1180 - Anitube](https://www.anitube.vip/video/580081) | 480p, 720p, 1080p | pendente |

HinataSoul e AniTube retornaram 360p e 720p no episódio dublado inicial e 480p, 720p e 1080p no episódio dublado 849. O mesmo ordinal de player tem altura diferente por episódio. No HinataSoul, as três alturas especiais que o pacote declara para o episódio 509115 foram confirmadas nessa página. A atribuição de medida a outras páginas deve usar a própria resposta do player. As três opções do AniTube22 permaneceram genéricas na amostra e todas falharam com mídia ausente, sem falha na lista ou no título do episódio. 

## TMDB, VideoInfoTag e cache

O Worker retornou 137390 para Birdie Wing, com uma temporada, 24 min como duração de episódio, sinopse, pôster, nota 6,583 e 17 entradas de elenco. Retornou dois filmes distintos para Cosmos. A parte 1 tem ID 968868, 81 min e data 2023-06-09. A parte 2 tem ID 968870, 82 min e data 2023-06-30. Os títulos originais em japonês constam no JSON. O TMDB público arquivado confirma o tipo e a identidade desses registros. A API direta, sem credencial, respondeu 401. O perfil instalado não apresentou arquivo de configurações do addon. O Worker foi testado com a opção ativada no perfil isolado, que corresponde ao padrão do XML distribuído. [Birdie Wing](https://www.themoviedb.org/tv/137390/seasons) · [Cosmos 1](https://www.themoviedb.org/movie/968868) · [Cosmos 2](https://www.themoviedb.org/movie/968870)

O ensaio de metadados entregou IDs únicos, título original japonês, sinopse, data, duração em segundos, nota, pôster e elenco com papel ao dublê. Na ficha de episódio, o título textual preservou o acento e o japonês. A listagem enviou também o prefixo numérico e o destaque amarelo no campo Title. A miniatura ficou no still e a temporada/episódio numéricos ficaram em campos separados. Sinopse real de episódio, tradução ou fallback de elenco em material indisponível pela API e exibição em Estuary continuam pendentes. O progresso é aplicado na finalização da lista por URL e depende de eventos do Kodi para ser coletado no uso real.

| Medição no Termux | Tempo (s) | Registros |
|---|---:|---:|
| busca One Piece nas quatro fontes · fria | 6.5653 | 181 |
| busca One Piece nas quatro fontes · reabertura | 1.3439 | 181 |
| Naruto Shippuden dublado HinataSoul · fria | 33.8321 | 309 |
| Naruto Shippuden dublado HinataSoul · reabertura | 0.0026 | 309 |
| Worker · tv/137390 · fria | 1.744 | 1 |
| Worker · tv/137390 · reabertura | 0.004 | 1 |

A medição de série longa incluiu pausa de 0,65 s a cada página para poupar a fonte. A segunda leitura usou o snapshot de episódios, que evita reabrir a lista. No teste controlado da API TMDB, a primeira abertura consumiu uma consulta, a segunda veio do cache e a expiração disparou nova consulta. Diante de falha após expiração, o cache antigo serviu o registro. O caminho cached_only recusou a entrada expirada e o caminho frio ficou vazio. Os números medem latência de funções no Termux e variam com rede, CPU e conteúdo. A expiração foi testada envelhecendo a entrada em SQLite. Com rede falhando, o código retornou o cache antigo; uma URL sem entrada propagou o erro. A limpeza por menu esvaziou as duas tabelas de resposta. Favoritos e progresso sobreviveram porque são persistidos separadamente. O teste não limpou os dados reais do Kodi.

## Problemas e correções por impacto

Todos os registros abaixo referem-se ao pacote **2.7.40** do commit informado no começo. Nos casos de mídia, o alvo é a navegação e o resolvedor original do ZIP.

### P1 · Seleção explícita de áudio pode trocar de edição sem confirmação

- Fonte e exemplo. Bakashi, One Piece ep. 1, em teste controlado com uma única opção Legendado.
- Reprodução. Abrir play com preferred_audio Dublado e um HTML cujo único grupo seja Legendado. O caso executa o fluxo real com a resolução e a entrega de mídia simuladas.
- Esperado. Interromper ou confirmar a mudança de idioma.
- Observado. finish_playback recebeu Legendado e nenhum diálogo foi chamado.
- Código e correção. aniplay/playback.py, play. Quando requested foi informado, tratá-lo como uma restrição até uma escolha explícita de fallback. Aplicar o mesmo contrato nas variantes de Bakashi e nas externas.

### P1 · AniTube22 lista players, mas não resolveu a amostra

- Fonte e exemplo. AniTube22, One Piece episódios 1, 849 dublado e 1180 da edição sem áudio indicado.
- Reprodução. Abrir as URLs da tabela e chamar episode_page e get_player para cada opção anunciada. O teste foi feito na rede do celular.
- Esperado. Validar pelo menos um player quando a fonte disponibiliza mídia para aquele episódio; caso contrário, o diagnóstico precisa identificar a etapa.
- Observado. Quatro páginas abriram e as doze opções terminaram com mídia ausente. As páginas correspondentes do AniTube resolveram pelo menos duas opções. A causa no servidor remoto permanece aberta.
- Código e correção. aniplay/providers/scraper.py, Resolver.get_player, _follow e _resolve_anitube. Registrar, sem URLs assinadas, quando nenhum formato de player foi reconhecido, quando a autorização falhou e quando a mídia foi recusada. Usar respostas de teste por variante do site e manter diagnóstico de relação com o episódio.

### P1 · Número repetido esconde opções de episódio em One Piece

- Fonte e exemplo. HinataSoul, One Piece dublado. 842 IDs na auditoria viraram 837 cards; números 30, 50, 611, 612 e 613 disputam o mesmo card. A edição sem indicação produziu 1.171 cards para 1.185 IDs. Nos dois AniTube também houve colisões.
- Reprodução. Aplicar episode_numbers e variant_rows às páginas arquivadas e abrir a temporada resultante. O pacote usa options[0] para montar a rota e guarda alternativas só quando há mais de um rótulo de áudio.
- Esperado. IDs distintos com numeração reaproveitada devem continuar acessíveis e com metadados próprios.
- Observado. O balde usa a numeração local como chave, e áudio igual colapsa em audio_variants. A regra de intervalos do TMDB também recusa a sequência com duplicatas. IDs ausentes no card não comprovam que sejam dublagens ou especiais equivalentes.
- Código e correção. aniplay/multisite.py, group_episodes, variant_rows, audio_variants e seasons, e aniplay/episode_order.py, flat_season_ranges. Separar especial e variante por identidade, conservar alternativas por URL quando a identidade estiver em disputa e testar distribuição por arco.

### P1 · Digimon de 1999 e remake usam o mesmo ID

- Fonte e exemplo. Bakashi, Digimon Adventure e Digimon Adventure (2020), com propagação aos correspondentes externos.
- Reprodução. Passar as entradas reais ao grouped com o índice do ZIP.
- Esperado. tv/31654 para o original do TMDB e tv/98034 para o remake.
- Observado. Um grupo tv:98034 com cinco entradas na amostra. A escolha do representante pode fornecer metadados do remake para uma rota de 1999.
- Código e correção. resources/data/tmdb-index.json, aniplay/multisite.py grouped e aniplay/providers/grouping.py. Corrigir o índice e usar tipo e ano antes de propagar um ID por nome.

### P1 · Temporada local de Birdie Wing consulta temporada inexistente

- Fonte e exemplo. HinataSoul e os dois AniTube, Birdie Wing 13+12. O dublê usou os cards da auditoria e as contagens verificadas.
- Reprodução. Abrir a obra, a fonte externa e o segundo bloco. Capturar season_details e a tag do primeiro episódio.
- Esperado. Mapear o segundo bloco à temporada 1, começando no episódio 14 se for mantida a ordem publicada.
- Observado. A consulta pediu temporada 2 e o card enviou temporada 2/episódio 1, com título genérico sem metadados correspondentes.
- Código e correção. aniplay/providers/grouping.py identity e aniplay/multisite.py variant_rows/seasons. Registrar deslocamentos de segmentos por provedor e preservar número publicado e número TMDB em campos separados.

### P1 · Cosmos precisa de dois vínculos de filme

- Fonte e exemplo. HinataSoul, AniTube e AniTube22 têm um card para Sailor Moon Cosmos Movie e dois itens internos.
- Reprodução. Processar os dois itens pelo fluxo de uma obra externa, mesmo quando lookup retorna um dos filmes.
- Esperado. Cada item deve ter o movie_id correspondente e tags de filme.
- Observado. O dublê montou dois episódios da temporada 1. A rota externa de seasons só obtém show_id para TV e não constrói movie_id por item. O Worker distingue 968868 de 968870.
- Código e correção. aniplay/multisite.py seasons e aniplay/videotag.py episode_fields. Adicionar um mapeamento de mídia composta por título/posição e ID confirmado, com testes de ambos os filmes.

### P2 · Slime separado em dois grupos e lacunas exigem escopo explícito

- Fonte e exemplo. Tensei shitara Slime Datta Ken 2nd Season e 2nd Season Part 2 nas fontes externas. Naruto Shippuden dublado no HinataSoul.
- Reprodução. Rodar identity e grouped nos dois cards de Slime e reaplicar variant_rows aos rótulos arquivados de Naruto.
- Esperado. Juntar blocos verificados de uma temporada com os intervalos correspondentes. Conservar a numeração de Naruto com lacunas e verificar a posição antes de anexar texto oficial.
- Observado. Slime produziu dois grupos, com Part 2 preservado na chave. Em Naruto dublado, 309 IDs e números até 316 conviveram sem colisões. A função de intervalos aceita lacunas com allow_gaps; confirmações de episódio por episódio no player ficaram pendentes.
- Código e correção. aniplay/providers/grouping.py identity, aniplay/multisite.py group_episodes e aniplay/episode_order.py. Cadastrar partes e exceções por obra, sem transformar a posição do card em número de episódio.

### P2 · Evidência editorial de áudio se perde fora do título

- Fonte e exemplo. Dai Sentai Goggle-V, slug goggle-five-v-legendado nos dois AniTube.
- Reprodução. Comparar titulo_visivel, imagem, secao_url e áudio do agrupador no JSON da auditoria e aplicar identity ao título extraído.
- Esperado. Conservar a evidência do slug com sua origem. Se a evidência for insuficiente, deixar desconhecido.
- Observado. A URL traz Legendado, mas o título enviado não contém a indicação e o agrupador devolve áudio vazio. Em N03 uma edição realmente sem marcador ficou corretamente em Áudio não informado.
- Código e correção. aniplay/providers/catalog.py e grouping.py. Produzir áudio e evidências estruturadas por provedor, com precedência entre rótulo, seção e slug. O player e seus avisos devem depender da edição escolhida.

### P2 · Metadado decorado na lista e perda de contexto em rotas recentes

- Fonte e exemplo. Todas; dublê com Épisode 青い空 e metadados simulados.
- Reprodução. Gerar um ListItem de episódio com views.item, comparar sua tag com Dialog.info e verificar o caminho de um registro de recentes gravado no serviço.
- Esperado. Separar título canônico, rótulo com cor, ordem e estado. Preservar identificadores ao reabrir a partir do histórico.
- Observado. A lista escreveu o prefixo e as marcações COLOR no campo Title. A ficha recebeu título puro e o número continuou separado. Pelo código, recentes guardam URL, título e ícone, enquanto continuar recupera mais campos de History. Uma reabertura que depende de restaurar temporada/episódio pode perder metadados quando não há snapshot compatível.
- Código e correção. aniplay/views.py item/flush, aniplay/info.py display, aniplay/navigation.py handle_continue/handle_favorites, aniplay/kodi/progress.py onAVStarted e aniplay/episode_context.py. Manter os campos sem cor e reusar um modelo persistido de identificação e contexto. Confirmar em Estuary quais views usam Label e Title.

### P2 · Repetição de consultas e cobertura limitada no catálogo principal

- Fonte e exemplo. Todas; busca One Piece e abertura de Naruto dublado no HinataSoul.
- Reprodução. Buscar, avançar no catálogo, abrir servidor, temporada e página seguinte. Medir frio e quente.
- Esperado. Reutilizar resultados paginados e snapshots, com indicação quando a busca terminou parcialmente.
- Observado. browse dispara query_sources a cada página e expand refaz busca e agrupamento. seasons pode enumerar de novo as fontes e episódios a cada abertura, embora o snapshot reduza o custo de rede. A fase fria da série longa foi de cerca de 34 s na amostra. A busca externa tem janela de 12 s e a navegação sem termo se limita às homes e ao índice embutido.
- Código e correção. aniplay/multisite.py search_source, browse, expand, provider_season_sources e load_episodes. Cachear consulta paginada e resultado de expansão com escopo por fonte. Diferenciar lista parcial de vazia e carregar páginas com cancelamento e progresso quando o Kodi oferecer suporte.

### P3 · Selos ausentes quando a renderização de capas está indisponível

- Fonte e exemplo. Todas, menu de servidores e capa com nota.
- Reprodução. Ativar poster_badges sem Pillow ou abrir enquanto a capa está na fila de renderização. No Termux, pillow() retornou vazio.
- Esperado. Manter a nota e a identificação do servidor legíveis enquanto o selo estiver indisponível.
- Observado no dublê. Sem Pillow e com a opção ativa, Birdie Wing ficou com nota 6,5 na tag e sem nota no rótulo. get_poster retorna vazio, e rated suprime a nota textual pelo ajuste. O nome genérico Servidor N ainda é exibido. O resultado visual no Kodi depende da skin e do Pillow instalado.
- Código e correção. aniplay/poster_badges.py get_poster e aniplay/views.py rated/item. Fazer o fallback depender do selo efetivamente renderizado, evitar repetir notas e manter distintivos e nome da fonte acessíveis.

## Estrutura e diagnóstico

- A separação entre providers, metadata, episode_context, videotag e storage facilita testes isolados. As regras de identidade se repetem em agrupamento, inferência do player, reabertura e associação de episódios. Consolidar a identidade da obra, edição, segmento e episódio em contratos explícitos reduzirá divergências.
- Cache de fontes e TMDB em SQLite já separa respostas de dados pessoais. Os tempos quentes confirmaram o valor do cache. Revisar o custo de consultas em vizinhança de temporada e o ciclo de vida de snapshots, capas e resultados do Worker. A limpeza atual tem escopo por tabela e não equivale a uma limpeza de todos os artefatos.
- Preservar os logs sanitizados por fonte, etapa, estado do cache e duração. Complementar a saída com contagem de candidatos, estado de paginação e distinção entre erro de extração e resposta sem mídia. Endereços de reprodução, credenciais e respostas completas de players devem ficar fora dos diagnósticos compartilhados.
- Os testes restantes no aparelho são: instalar o pacote auditado em perfil separado com autorização, percorrer a matriz em Estuary, comparar ficha e lista com capturas, reproduzir brevemente uma amostra verificada, ouvir a edição escolhida, conferir a resolução decodificada e exercitar os eventos reais de início, cancelamento, retomada e visto. A API TMDB autenticada e o efeito de limpeza no perfil real também ficaram pendentes.

