# AniPlay Experimental 2.7.40 — investigação parcial

A análise encontrou a configuração de três fontes e riscos concretos na chave de agrupamento do código Python publicado. A coleta pela rede móvel e a comparação direta com o TMDB ficaram bloqueadas. As amostras abaixo vêm de páginas indexadas e não medem a disponibilidade atual dos catálogos.

## Código da versão

A [release v2.7.40-experimental](https://github.com/hugoferroz2525-stack/animesplay/releases/tag/v2.7.40-experimental) e a tag apontam para o commit `3f8a264122fdf9215e466c3d2d50704feff004b4`. A release anuncia seleção de áudio antes dos servidores e revisão da divisão de temporadas pelo TMDB. O commit contém três módulos Python avulsos e um ZIP para Kodi. A inspeção foi dos módulos avulsos. O conector GitHub entrega texto e o shell não pôde iniciar, portanto o conteúdo do ZIP e a equivalência entre os módulos e o complemento instalado ficaram sem verificação.

- [catalogo_multisite.py](https://github.com/hugoferroz2525-stack/animesplay/blob/3f8a264122fdf9215e466c3d2d50704feff004b4/fontes-multisite/catalogo_multisite.py) define as três origens. A busca usa `/busca?busca=...` na HinataSoul e `/busca?s=...` nas duas AniTube. Sem termo, o módulo lê apenas a inicial. Os extratores dão preferência ao título ou texto alternativo da imagem sobre o rótulo visível e coletam título, URL e imagem. As páginas de episódios usam classes específicas por família de fonte. A extração não usa ano, tipo, título alternativo nem vínculos de temporada.
- [agrupamento_animes.py](https://github.com/hugoferroz2525-stack/animesplay/blob/3f8a264122fdf9215e466c3d2d50704feff004b4/fontes-multisite/agrupamento_animes.py) iguala caixa, acentos, pontuação e variantes de palavras explícitas de áudio. Mantém na chave tanto o áudio quanto marcadores de temporada e subtítulos. Dentro do grupo elimina repetições por site e URL e usa o primeiro título encontrado como rótulo.
- [scraper.py](https://github.com/hugoferroz2525-stack/animesplay/blob/3f8a264122fdf9215e466c3d2d50704feff004b4/fontes-multisite/scraper.py) procura o próximo número maior na mesma seção. Na busca espera `?page=N`. Nas demais páginas espera que `/page/N` esteja no fim do caminho. Uma rota com `/page/2/letra/t` fica fora desse padrão.

## Cobertura e falhas

| Fonte configurada | Resultado da consulta web |
|---|---|
| [HinataSoul](https://www.hinatasoul.com/) | Inicial retornou 403. A [página 30 de animes](https://www.hinatasoul.com/animes/page/30) estava indexada, mas a abertura direta deu cache miss. A [página 31](https://www.hinatasoul.com/animes/page/31) ficou inacessível. |
| HinataSoul, catálogo dublado | A [página 2 da letra t](https://www.hinatasoul.com/anime-dublado/page/2/letra/t) estava indexada, com navegação de 1 a 4. A abertura direta falhou. A [rota correspondente da página 3](https://www.hinatasoul.com/anime-dublado/page/3/letra/t) deu cache miss. O lote indexado mostrou títulos, mas não expôs todas as URLs de itens. |
| [AniTube22](https://www.anitube22.vip/) | Inicial e [busca por Naruto](https://www.anitube22.vip/busca?s=Naruto) inacessíveis pela ferramenta. Nenhuma página de catálogo ou de anime confirmada. |
| [AniTube](https://anitube.vip/) | A inicial redirecionou a consulta web para o Google. A [busca por Naruto](https://anitube.vip/busca?s=Naruto) ficou inacessível. O código rejeitaria um redirecionamento para outro domínio na inicial. Nenhuma convenção editorial confirmada. |
| TMDB | O navegador de pesquisa reportou bloqueio por robots.txt para o domínio. As consultas diretas a [One-Punch Man](https://www.themoviedb.org/tv/63926-one-punch-man) e [Naruto Shippuden](https://www.themoviedb.org/tv/31910-naruto-shippuden) ficaram inacessíveis. Sem conferência de temporadas, especiais ou contagens pelo TMDB. |

O Bubblewrap do ambiente local rejeitou uma montagem do diretório do socket do servidor antes de iniciar o shell. Não houve rota disponível para executar a coleta a partir do celular. As amostras indexadas representam dois recortes paginados, sem uma varredura sequencial ou completa.

## Sinais e casos reais

| Evidência | Efeito ou risco no código inspecionado |
|---|---|
| [One Punch Man - Dublado](https://www.hinatasoul.com/anime-dublado/f4663dd2269c70f8de9edb36a0e9623b292b46f8) usa sufixo de áudio, rota `/anime-dublado/`, tipo TV, título alternativo e campo de temporada com valor Verão. O catálogo geral observado usa o rótulo `anime`, sem marcar explicitamente legendado. | A chave para a edição dublada difere da chave do título-base. O campo Verão é estação do ano e não fornece número de temporada. A edição correspondente sem o sufixo ficou sem confirmação nesta amostra. |
| `Birdie Wing: Golf Girls' Story` (13) e `Birdie Wing: Golf Girls' Story Season 2` (12), na [página 30 de animes](https://www.hinatasoul.com/animes/page/30). | Se ambas forem retornadas no mesmo resultado, o agrupador as mantém em cartões diferentes. A contagem de cada bloco ajuda a validar o vínculo com temporadas após confirmar a identidade no TMDB. |
| `Tensei shitara Slime Datta Ken 2nd Season Part 2 - Dublado`, `Tensei shitara Slime Datta Ken 3rd Season - Dublado`, `Tensei shitara Slime Datta Ken Movie: Guren no Kizuna-hen - Dublado` e `Tensei shitara Slime Datta Ken OVA - Dublado` aparecem [no mesmo recorte dublado](https://www.hinatasoul.com/anime-dublado/page/2/letra/t). | A chave separa todos. A parte 2 deve ser avaliada como segmento da segunda temporada. O filme e o OVA precisam de classificação própria. Remover todos os sufixos sem verificar o tipo criaria uma fusão indevida. |
| `Bishoujo Senshi Sailor Moon` e `Bishoujo Senshi Sailor Moon Crystal`, `Bishoujo Senshi Sailor Moon Crystal 2` e `Bishoujo Senshi Sailor Moon Crystal 3` aparecem [no mesmo catálogo](https://www.hinatasoul.com/animes/page/30), ao lado de entradas Movie. | A chave atual separa essas entradas. Um agrupamento futuro por prefixo confundiria a série original com Crystal. É um caso de regressão para a correção, sem evidência de uma fusão atual. |
| [Tonikaku Kawaii: SNS - Dublado](https://www.hinatasoul.com/anime-dublado/tonikaku-kawaii-sns-dublado) tem tipo OVA e um episódio. A página oferece navegação para temporadas adjacentes. | O texto de navegação é sinal de relação editorial, insuficiente para tratar o OVA como episódio regular. |
| [Kimetsu no Yaiba Movie: Mugen Jou-hen - Dublado](https://www.hinatasoul.com/anime-dublado/kimetsu-no-yaiba-movie-mugen-jou-hen-dublado) tem o campo Tipo vazio no índice e lista um filme como `Episódio 01`. | Número 01 e campo Tipo vazio também ocorrem fora de séries. O título, o texto do item e a classificação externa precisam ser considerados em conjunto. |
| `Naruto Shippuden - Dublado` aparece com os números [112](https://www.hinatasoul.com/videos/103656) e [169](https://www.hinatasoul.com/videos/524966). | São evidências de rótulos absolutos altos na fonte, sem comprovar toda a continuidade nem a fronteira de temporada. O módulo agrupa pelo número terminal sem temporada. Uma fonte reiniciada em 1 e outra com numeração absoluta poderiam colidir no episódio 1 ou deixar equivalentes separados. |

No extrator de episódios, quando o texto examinado termina em `ep 12 - FINAL`, a expressão regular não reconhece o número. Esse rótulo aparece na página de One Punch Man acima. Se o elemento efetivamente extraído contiver apenas `Episódio 12`, a expressão reconhece o número. O índice exibe os dois rótulos e não permite confirmar qual texto está no seletor em produção. Itens sem número reconhecido são agrupados pela URL.

Não foi possível confirmar duas obras distintas já mescladas no complemento instalado. No código avulso, títulos iguais após normalização podem se fundir mesmo com anos e tipos distintos, pois esses campos não entram na chave. Também não houve evidência suficiente para afirmar como cada AniTube indica áudio, temporadas, filmes ou especiais.

## Correções sugeridas

1. Preservar o título visível, o título da imagem, a URL, o site e os campos de detalhe. Registrar tipo, ano, título alternativo, marcador de áudio e origem de cada evidência. Usar áudio desconhecido quando não houver rótulo confiável. Deixar áudio como variante de uma obra confirmada.
2. Confirmar identidade e tipo no TMDB antes de unir entradas diferentes. Usar tipo e ID do TMDB com ano e aliases para desambiguar. Relacionar filmes e derivados à franquia com IDs próprios. Resolver OVA e especiais com evidência individual.
3. Guardar o número da origem e o par temporada/episódio confirmado. Traduzir numeração absoluta por mapa validado de episódios ou arcos, verificando ordem, datas e contagens. Manter entradas ambíguas separadas até confirmar o mapa. Cobrir o sufixo `FINAL` com um teste do HTML real.
4. Ler o link da próxima página na navegação e validar a origem e a seção. Testar as rotas de busca e a paginação por letra, detectar repetição de URL e distinguir página vazia válida de seletor quebrado. Registrar falhas por URL.
5. Antes de aplicar a correção, conferir o ZIP efetivamente distribuído. Repetir as três coletas em rede móvel e verificar no TMDB as temporadas de Birdie Wing, as partes de Slime, a distinção de Sailor Moon e a correspondência dos números de Naruto Shippuden.

O código e o repositório não foram alterados.
