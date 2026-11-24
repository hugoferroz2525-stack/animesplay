# Auditoria do catálogo do AniPlay Experimental 2.7.40

Coleta iniciada em 23 de novembro de 2026 pelo Termux no Android. O Bash nativo executou e recebeu HTTP 301 do GitHub Raw. O ambiente de trabalho usa PRoot aarch64 e o shell iniciou normalmente. O celular baixou o ZIP e acessou as fontes. A interface efetiva da conexão, Wi-Fi ou LTE, ficou sem confirmação.

O addon.xml confirma a versão 2.7.40. O teste de descompressão e CRC passou. SHA-256 979c96261a7cc1d41b5e6d732856a55226fa56809890dfe10a9a627b62533e10. [ZIP do commit auditado](https://raw.githubusercontent.com/hugoferroz2525-stack/animesplay/3f8a264122fdf9215e466c3d2d50704feff004b4/AniPlay-2.7.40-experimental.zip)

## Cobertura

| Fonte | URLs descobertas | URLs coletadas | Listagens HTML | Falhas | Pendentes | Páginas repetidas | URLs de itens | Com título visível | Detalhes HTTP 200 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| [Bakashi](bakashi.json) | 246 | 246 | 241 | 0 | 0 | 24 | 5076 | 2541 | 11/11 |
| [HinataSoul](hinatasoul.json) | 1495 | 1495 | 1494 | 0 | 0 | 556 | 10058 | 10058 | 33/33 |
| [AniTube22](anitube22.json) | 1438 | 1438 | 1437 | 0 | 0 | 563 | 10029 | 10029 | 28/28 |
| [AniTube](anitube.json) | 1438 | 1438 | 1437 | 0 | 0 | 563 | 10029 | 10029 | 28/28 |

A contagem de páginas inclui listagens e mapas XML. Itens são deduplicados por URL na mesma fonte. Páginas repetidas têm o mesmo conjunto de cards. A fila visita cada URL uma vez, além da repetição de erros transitórios. Variações com URL canônica diferente continuam observáveis. Os detalhes foram amostrados. Valores nulos ou listas vazias representam ausência de evidência coletada.

A travessia usou pausa de 1,15 s antes de cada requisição de listagem por domínio, resposta de até 3 MB e prazo de 13 s por operação. Uma resposta 403 ou 429 interrompe a fila correspondente. A amostra de detalhes teve pausa própria de 2,5 s e limite de 2 MB. O coletor acessou HTML e XML, excluindo imagens, vídeos, embeds e downloads.

### Rotas

- **Bakashi.** /lista-de-animes e ?page=N. O formulário tem alfabeto A–Z pelo parâmetro letra e filtros de tipo (TV, filme, OVA, ONA e especial), gênero, ano e status. A lista geral mistura dublados e demais cards. As consultas HTML diretas para TV, filme, OVA, ONA e especial devolveram os mesmos primeiros 25 cards da lista geral. O filtro de letra B retornou uma seleção diferente, e suas páginas foram percorridas junto com as demais letras. Há três mapas XML de anime, além de mapas próprios de desenhos e episódios. O primeiro rel=next aponta para ?page=6, mas traz data-page=2. Links numéricos permitem alcançar as páginas intermediárias. [Catálogo](https://bakashi.top/lista-de-animes) · [Mapa](https://bakashi.top/sitemap.xml)
- **HinataSoul.** /animes e /anime-dublado. As listas incluem /letra/{a-z,numeros,todos}, /page/N e /page/N/letra/{letra}. O menu inclui /donghua, /doramas e /tokusatsus. O XML é dominado por URLs de episódios. [Geral](https://www.hinatasoul.com/animes) · [Dublados](https://www.hinatasoul.com/anime-dublado)
- **AniTube22 e AniTube.** /anime, /animes-dublado, /donghua, /doramas e /tokusatsu, com /page/N antes do filtro de letra. A sondagem inicial de /animes-dublado retornou 404 nos dois hosts. A rota respondeu 200 na consulta seguinte e entrou na travessia. Gênero, calendário e temporada são filtros transversais. [AniTube22](https://www.anitube22.vip/anime) · [AniTube](https://www.anitube.vip/anime)

- **Bakashi.** Listagem concluída nas rotas mapeadas. Falhas 0. Mudanças de domínio 0. URL canônica diferente em 0 detalhes amostrados.
  Exemplo de repetição em [uma listagem](https://bakashi.top/lista-de-animes?page=103) e [sua equivalente](https://bakashi.top/lista-de-animes?page=102).
- **HinataSoul.** Listagem concluída nas rotas mapeadas. Falhas 0. Mudanças de domínio 0. URL canônica diferente em 0 detalhes amostrados.
  As páginas sazonais anunciadas no menu e as demais verificações transversais acrescentaram 29 URLs.
  As 29 URLs extras de temporada têm título e slug idênticos a uma entrada da seção de dublados. As três amostras responderam 200 e declararam a própria rota sazonal como canônica. [Exemplo na temporada](https://www.hinatasoul.com/animes/enen-no-shouboutai-san-no-shou-part-2-dublado) · [Endereço na seção de dublados](https://www.hinatasoul.com/anime-dublado/enen-no-shouboutai-san-no-shou-part-2-dublado).
  Exemplo de repetição em [uma listagem](https://www.hinatasoul.com/animes/letra/todos) e [sua equivalente](https://www.hinatasoul.com/animes).
- **AniTube22.** Listagem concluída nas rotas mapeadas. Falhas 0. Mudanças de domínio 0. URL canônica diferente em 11 detalhes amostrados.
  As páginas sazonais anunciadas no menu e as demais verificações transversais acrescentaram 0 URLs.
  Exemplo de repetição em [uma listagem](https://www.anitube22.vip/anime/letra/todos) e [sua equivalente](https://www.anitube22.vip/anime).
- **AniTube.** Listagem concluída nas rotas mapeadas. Falhas 0. Mudanças de domínio 0. URL canônica diferente em 11 detalhes amostrados.
  As páginas sazonais anunciadas no menu e as demais verificações transversais acrescentaram 0 URLs.
  Exemplo de repetição em [uma listagem](https://www.anitube.vip/anime/letra/todos) e [sua equivalente](https://www.anitube.vip/anime).

A travessia A–Z do Bakashi consultou 138 URLs e reuniu 2507 URLs de título, com 0 adicionais em relação à lista geral e ao mapa.

No Bakashi, 2535 slugs do XML correspondem a slugs de cards quando se remove o sufixo -Na-temporada. A união por essa regra tem 2541 slugs, dos quais 6 aparecem só na listagem e 0 só no mapa. Esta equivalência sintática explica a contagem de URLs e precisa de validação canônica para fusões definitivas.

Os dois hosts AniTube foram percorridos separadamente. Entre cards com título visível, 10029 caminhos aparecem em ambos, 0 só no AniTube e 0 só no AniTube22.

As listas principais das três fontes externas coincidem em 10.029 pares de seção e slug depois de normalizar as grafias das rotas. Os endereços sazonais alternativos foram preservados separadamente.

### Campos disponíveis

| Fonte | Áudio indicado | Tipo | Ano | Alternativos | Contagem de episódios |
|---|---:|---:|---:|---:|---:|
| Bakashi | 2 | 2541 | 21 | 0 | 0 |
| HinataSoul | 1367 | 10058 | 30 | 30 | 10058 |
| AniTube22 | 1338 | 0 | 28 | 28 | 28 |
| AniTube | 1338 | 0 | 28 | 28 | 28 |

A auditoria verificou episódios nas contagens e nos rótulos disponíveis nos catálogos e páginas de detalhe dos casos amostrados. A paginação detalhada de episódios ficou restrita a One Piece e Naruto Shippuden. Os metadados por item foram consultados por amostragem. Uma data ou título alternativo ausente no JSON requer consulta adicional ao detalhe.

## Problemas confirmados no addon

- A busca externa sem termo em multisite.py abre somente a home. Com termo, a paginação tem teto de 12 páginas e prazo de 12 segundos. O modo catálogo complementa apenas o Bakashi com o índice do ZIP. As listas alfabéticas e a seção de dublados dos provedores externos ficam fora dessa enumeração.
- O extrator em providers/catalog.py prefere o título da imagem e seu texto alternativo ao título visível. A função identity em providers/grouping.py determina áudio só pelo título recebido. Ela remove os tokens de áudio e identifica um conjunto limitado de sufixos de temporada. A rota de dublados é uma evidência editorial que essa função ignora.
- O agrupador usa a chave textual normalizada e recebe IDs fixos apenas para o Bakashi. Um ID conhecido pode se propagar a outros itens com a mesma chave sem confirmação de tipo ou ano. A interface usa uma fonte representante para os metadados do grupo. Homônimos, filmes e especiais exigem validação adicional.
- A busca TMDB compara variantes textuais a nomes exatos de resultados e usa ano quando informado. O código solicita títulos alternativos apenas depois de identificar o resultado. Os resolvedores de episódios, players e fontes de áudio foram lidos no ZIP, e a coleta se limitou às rotas de catálogo e detalhes.

### Fusão incorreta reproduzida

O índice do ZIP vincula os cards do Bakashi para Digimon Adventure e Digimon Adventure (2020) ao mesmo grupo tv:98034. O TMDB distingue a série de 1999, tv/31654, do remake de 2020, tv/98034. O agrupador aplicou a mesma chave às duas entradas. [Card de 1999](https://bakashi.top/anime/digimon-adventure-1a-temporada) · [Card de 2020](https://bakashi.top/anime/digimon-adventure-2020-1a-temporada) · [TMDB 1999](https://www.themoviedb.org/tv/31654) · [TMDB 2020](https://www.themoviedb.org/tv/98034)

### Áudio e títulos de imagem


O rótulo web e o índice de formato do ZIP divergem em 178 cards do Bakashi. Um exemplo tem rótulo “TV Anime” e índice “Filme”. [Dreamland](https://bakashi.top/anime/dreamland-1a-temporada).

- **Bakashi.** 0 cards com evidência de áudio e classificação vazia no agrupador, 0 com evidência para as duas indicações e 8 cujo título extraído diverge do visível.
  O extrator escolhe “Midara na Ao-chan wa Benkyou ga Dekinai (Ao-chan Can’t Study!)”. [Midara na Ao-chan wa Benkyou ga Dekinai (Ao-chan Can&#8217;t Study!)](https://bakashi.top/anime/midara-na-ao-chan-wa-benkyou-ga-dekinai-ao-chan-can-8217-t-study-1a-temporada).
- **HinataSoul.** 4 cards com evidência de áudio e classificação vazia no agrupador, 0 com evidência para as duas indicações e 0 cujo título extraído diverge do visível.
  Evidência em slug do item. [Love Live! Nijigasaki Gakuen School Idol Doukoukai OVA](https://www.hinatasoul.com/animes/love-live-nijigasaki-gakuen-school-idol-doukoukai-dublado).
- **AniTube22.** 4 cards com evidência de áudio e classificação vazia no agrupador, 0 com evidência para as duas indicações e 7 cujo título extraído diverge do visível.
  Evidência em slug do item. [Dai Sentai Goggle-V](https://www.anitube22.vip/tokusatsu/goggle-five-v-legendado).
- **AniTube.** 4 cards com evidência de áudio e classificação vazia no agrupador, 0 com evidência para as duas indicações e 7 cujo título extraído diverge do visível.
  Evidência em slug do item. [Dai Sentai Goggle-V](https://www.anitube.vip/tokusatsu/goggle-five-v-legendado).

A presença de “dublado” na categoria ou slug registra a classificação editorial. A ausência de marcador deixa o áudio desconhecido. A verificação da faixa efetiva ficou fora do escopo.

## Casos investigados

O agrupador do ZIP foi reaplicado a 32657 cards com título e gerou 9738 grupos. As chaves abaixo são resultado real do código sobre os cards obtidos.


### One Piece

- **Bakashi.** [One Piece](https://bakashi.top/anime/one-piece-1a-temporada) → tv:37854 · [One Piece Dublado](https://bakashi.top/anime/one-piece-dublado-1a-temporada) (áudio dublado) → tv:37854 · [ONE PIECE: A Série](https://bakashi.top/anime/one-piece-a-serie-1a-temporada) → tv:111110.
- **HinataSoul.** [One Piece](https://www.hinatasoul.com/animes/e1eaa4181415abd4e16cce073629ee329ebd3200) (episódios 1082/???? Episódios) → tv:37854 · [One Piece - Dublado](https://www.hinatasoul.com/anime-dublado/7804b6bdda34932920657ba29e64025244f485c7) (áudio dublado · episódios 849/?? Episódios) → tv:37854 · [One Piece Movie 01](https://www.hinatasoul.com/animes/one-piece-movie-1) (episódios 01/01 Episódios) → title:one piece movie 01 · [One Piece: Heroines](https://www.hinatasoul.com/animes/one-piece-heroines) (episódios 1 Episódios) → title:one piece heroines.
- **AniTube22.** [One Piece](https://www.anitube22.vip/anime/e1eaa4181415abd4e16cce073629ee329ebd3200) → tv:37854 · [One Piece - Dublado](https://www.anitube22.vip/animes-dublado/7804b6bdda34932920657ba29e64025244f485c7) (áudio dublado) → tv:37854 · [One Piece Movie 01](https://www.anitube22.vip/anime/one-piece-movie-1) (episódios 01/01) → title:one piece movie 01 · [One Piece: Heroines](https://www.anitube22.vip/anime/one-piece-heroines) → title:one piece heroines.
- **AniTube.** [One Piece](https://www.anitube.vip/anime/e1eaa4181415abd4e16cce073629ee329ebd3200) → tv:37854 · [One Piece - Dublado](https://www.anitube.vip/animes-dublado/7804b6bdda34932920657ba29e64025244f485c7) (áudio dublado) → tv:37854 · [One Piece Movie 01](https://www.anitube.vip/anime/one-piece-movie-1) (episódios 01/01) → title:one piece movie 01 · [One Piece: Heroines](https://www.anitube.vip/anime/one-piece-heroines) → title:one piece heroines.

A série animada é tv/37854 e suas temporadas seguem arcos. Film Red tem ID próprio movie/900667. Edições dubladas da série, do filme e especiais exigem escopo por obra.

### Birdie Wing

- **Bakashi.** [Birdie Wing -Golf Girls' Story-](https://bakashi.top/anime/birdie-wing-golf-girls-story-1a-temporada) → tv:137390.
- **HinataSoul.** [Birdie Wing: Golf Girls' Story](https://www.hinatasoul.com/animes/birdie-wing-golf-girls-story) (episódios 13/13 Episódios) → tv:137390 · [Birdie Wing: Golf Girls' Story Season 2](https://www.hinatasoul.com/animes/birdie-wing-golf-girls-story-season-2) (episódios 12/12 Episódios) → tv:137390.
- **AniTube22.** [Birdie Wing: Golf Girls' Story](https://www.anitube22.vip/anime/birdie-wing-golf-girls-story) (episódios 13/13) → tv:137390 · [Birdie Wing: Golf Girls' Story Season 2](https://www.anitube22.vip/anime/birdie-wing-golf-girls-story-season-2) (episódios 12/12) → tv:137390.
- **AniTube.** [Birdie Wing: Golf Girls' Story](https://www.anitube.vip/anime/birdie-wing-golf-girls-story) (episódios 13/13) → tv:137390 · [Birdie Wing: Golf Girls' Story Season 2](https://www.anitube.vip/anime/birdie-wing-golf-girls-story-season-2) (episódios 12/12) → tv:137390.

HinataSoul e os dois AniTube dividem os 25 episódios em 13 e 12. O agrupador une os cards, mas atribui temporada 2 ao segundo bloco. O TMDB tem somente temporada 1 nesse ID. O primeiro episódio do segundo bloco local corresponde ao episódio 14 se a ordem observada for mantida.

### Slime

- **Bakashi.** [That Time I Got Reincarnated as a Slime](https://bakashi.top/anime/that-time-i-got-reincarnated-as-a-slime-1a-temporada) → tv:82684 · [I've Been Killing Slimes For 300 Years And Maxed Out My Level](https://bakashi.top/anime/i-ve-been-killing-slimes-for-300-years-and-maxed-out-my-level-1a-temporada) → tv:99073.
- **HinataSoul.** [Tensei Shitara Slime Datta Ken](https://www.hinatasoul.com/animes/792dd460cbf0ea024851e1c25c0db65b2898bd82) (episódios 24/24 Episódios) → title:tensei shitara slime datta ken · [Tensei Shitara Slime Datta Ken - Dublado](https://www.hinatasoul.com/anime-dublado/5b858562589f1bb24bec7ab6c9bf885d3fe6d00f) (áudio dublado · episódios 24/24 Episódios) → title:tensei shitara slime datta ken · [Tensei shitara Slime Datta Ken OVA](https://www.hinatasoul.com/animes/adc40f91b1ed4c632a886d243f5c7c142bc44a20) (episódios 05/05 Episódios) → title:tensei shitara slime datta ken ova · [Tensura Nikki: Tensei shitara Slime Datta Ken](https://www.hinatasoul.com/animes/b2d2b554e17ad3fbb9c6f54b300a76b077b3fd31) (episódios 12/12 Episódios) → title:tensura nikki tensei shitara slime datta ken.
- **AniTube22.** [Tensei Shitara Slime Datta Ken](https://www.anitube22.vip/anime/792dd460cbf0ea024851e1c25c0db65b2898bd82) (episódios 24/24) → title:tensei shitara slime datta ken · [Tensei Shitara Slime Datta Ken - Dublado](https://www.anitube22.vip/animes-dublado/5b858562589f1bb24bec7ab6c9bf885d3fe6d00f) (áudio dublado · episódios 24/24) → title:tensei shitara slime datta ken · [Tensei shitara Slime Datta Ken OVA](https://www.anitube22.vip/anime/adc40f91b1ed4c632a886d243f5c7c142bc44a20) → title:tensei shitara slime datta ken ova · [Tensura Nikki: Tensei shitara Slime Datta Ken](https://www.anitube22.vip/anime/b2d2b554e17ad3fbb9c6f54b300a76b077b3fd31) → title:tensura nikki tensei shitara slime datta ken.
- **AniTube.** [Tensei Shitara Slime Datta Ken](https://www.anitube.vip/anime/792dd460cbf0ea024851e1c25c0db65b2898bd82) (episódios 24/24) → title:tensei shitara slime datta ken · [Tensei Shitara Slime Datta Ken - Dublado](https://www.anitube.vip/animes-dublado/5b858562589f1bb24bec7ab6c9bf885d3fe6d00f) (áudio dublado · episódios 24/24) → title:tensei shitara slime datta ken · [Tensei shitara Slime Datta Ken OVA](https://www.anitube.vip/anime/adc40f91b1ed4c632a886d243f5c7c142bc44a20) → title:tensei shitara slime datta ken ova · [Tensura Nikki: Tensei shitara Slime Datta Ken](https://www.anitube.vip/anime/b2d2b554e17ad3fbb9c6f54b300a76b077b3fd31) → title:tensura nikki tensei shitara slime datta ken.

A série principal tv/82684, Scarlet Bond movie/876792 e a série de 300 anos tv/99073 têm identidades próprias. Part 2 pode ser um bloco da temporada 2. O derivado Tensura Nikki tem série própria e os OVAs precisam de vínculo individual.

O agrupador remove 2nd Season quando está no fim, mas conserva 2nd Season Part 2 como parte da chave. Isso deixa o segundo bloco em outro grupo nas fontes externas. O TMDB publica os 24 episódios na temporada 2, com o segundo bloco a partir do episódio 13, Visitantes. [Card do primeiro bloco](https://www.hinatasoul.com/animes/b6146d534fea1df93fb331751c95534c561b29bd) · [Card do segundo bloco](https://www.hinatasoul.com/animes/aaf08754be3b5dab97813591436ce7954c7c182c).
[Temporada 2 da série principal](https://www.themoviedb.org/tv/82684/season/2) · [Especiais](https://www.themoviedb.org/tv/82684/season/0).

### Sailor Moon

- **Bakashi.** [Sailor Moon](https://bakashi.top/anime/sailor-moon-1a-temporada) → tv:3570 · [Sailor Moon Crystal](https://bakashi.top/anime/sailor-moon-crystal-1a-temporada) → tv:61339.
- **HinataSoul.** [Bishoujo Senshi Sailor Moon](https://www.hinatasoul.com/animes/e1c7e67102df3a6c1f71aad7a6e3600baffd31e3) (episódios 46/46 Episódios) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon - Dublado](https://www.hinatasoul.com/anime-dublado/0903176e0dec7edd85bb0d4460934664bbd667e8) (áudio dublado · episódios 46/46 Episódios) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon SuperS](https://www.hinatasoul.com/animes/ebee48c342d8aa5afc52021fed5108184876d4b2) (episódios 39/39 Episódios) → title:bishoujo senshi sailor moon supers · [Bishoujo Senshi Sailor Moon R](https://www.hinatasoul.com/animes/bishoujo-senshi-sailor-moon-r) (episódios 43/43 Episódios) → title:bishoujo senshi sailor moon r.
- **AniTube22.** [Bishoujo Senshi Sailor Moon](https://www.anitube22.vip/anime/e1c7e67102df3a6c1f71aad7a6e3600baffd31e3) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon - Dublado](https://www.anitube22.vip/animes-dublado/0903176e0dec7edd85bb0d4460934664bbd667e8) (áudio dublado) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon SuperS](https://www.anitube22.vip/anime/ebee48c342d8aa5afc52021fed5108184876d4b2) → title:bishoujo senshi sailor moon supers · [Bishoujo Senshi Sailor Moon R](https://www.anitube22.vip/anime/bishoujo-senshi-sailor-moon-r) (episódios 43/43) → title:bishoujo senshi sailor moon r.
- **AniTube.** [Bishoujo Senshi Sailor Moon](https://www.anitube.vip/anime/e1c7e67102df3a6c1f71aad7a6e3600baffd31e3) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon - Dublado](https://www.anitube.vip/animes-dublado/0903176e0dec7edd85bb0d4460934664bbd667e8) (áudio dublado) → title:bishoujo senshi sailor moon · [Bishoujo Senshi Sailor Moon SuperS](https://www.anitube.vip/anime/ebee48c342d8aa5afc52021fed5108184876d4b2) → title:bishoujo senshi sailor moon supers · [Bishoujo Senshi Sailor Moon R](https://www.anitube.vip/anime/bishoujo-senshi-sailor-moon-r) (episódios 43/43) → title:bishoujo senshi sailor moon r.

R, S, SuperS e Sailor Stars são temporadas de tv/3570. Crystal é tv/61339. Eternal e Cosmos têm dois filmes cada, com IDs separados. Uma regra genérica para os sufixos perderia o contexto.

As três fontes externas exibem Cosmos em um único card de dois episódios. O TMDB publica dois filmes independentes. A correção precisa associar cada episódio local ao ID de seu filme. [HinataSoul](https://www.hinatasoul.com/animes/bishoujo-senshi-sailor-moon-cosmos-movie) · [AniTube22](https://www.anitube22.vip/anime/bishoujo-senshi-sailor-moon-cosmos-movie) · [AniTube](https://www.anitube.vip/anime/bishoujo-senshi-sailor-moon-cosmos-movie).

### Tonikaku Kawaii

- **Bakashi.** [TONIKAWA: Over The Moon For You](https://bakashi.top/anime/tonikawa-over-the-moon-for-you-1a-temporada) → tv:100049.
- **HinataSoul.** [Tonikaku Kawaii](https://www.hinatasoul.com/animes/tonikaku-kawaii) (episódios 12/12 Episódios) → title:tonikaku kawaii · [Tonikaku Kawaii - Dublado](https://www.hinatasoul.com/anime-dublado/tonikaku-kawaii-dublado) (áudio dublado · episódios 12/12 Episódios) → title:tonikaku kawaii · [Tonikaku Kawaii: SNS](https://www.hinatasoul.com/animes/tonikaku-kawaii-sns) (episódios 01/01 Episódios) → title:tonikaku kawaii sns · [Tonikaku Kawaii: Seifuku](https://www.hinatasoul.com/animes/tonikaku-kawaii-seifuku) (episódios 01/01 Episódios) → title:tonikaku kawaii seifuku.
- **AniTube22.** [Tonikaku Kawaii](https://www.anitube22.vip/anime/tonikaku-kawaii) (episódios 12/12) → title:tonikaku kawaii · [Tonikaku Kawaii - Dublado](https://www.anitube22.vip/animes-dublado/tonikaku-kawaii-dublado) (áudio dublado · episódios 12/12) → title:tonikaku kawaii · [Tonikaku Kawaii: SNS](https://www.anitube22.vip/anime/tonikaku-kawaii-sns) → title:tonikaku kawaii sns · [Tonikaku Kawaii: Seifuku](https://www.anitube22.vip/anime/tonikaku-kawaii-seifuku) (episódios 01/01) → title:tonikaku kawaii seifuku.
- **AniTube.** [Tonikaku Kawaii](https://www.anitube.vip/anime/tonikaku-kawaii) (episódios 12/12) → title:tonikaku kawaii · [Tonikaku Kawaii - Dublado](https://www.anitube.vip/animes-dublado/tonikaku-kawaii-dublado) (áudio dublado · episódios 12/12) → title:tonikaku kawaii · [Tonikaku Kawaii: SNS](https://www.anitube.vip/anime/tonikaku-kawaii-sns) → title:tonikaku kawaii sns · [Tonikaku Kawaii: Seifuku](https://www.anitube.vip/anime/tonikaku-kawaii-seifuku) (episódios 01/01) → title:tonikaku kawaii seifuku.

tv/100049 usa TONIKAWA: Over the Moon for You e lista duas temporadas numeradas e especiais. As variantes romanizadas, o título inglês e os especiais precisam de aliases com escopo de episódio.

O TMDB inclui Tonikaku Kawaii, SNS, Seifuku e Joshikou-hen entre os títulos alternativos de tv/100049. Na temporada 0, SNS corresponde ao episódio 14, Redes sociais, e Seifuku ao 15, Uniforme. Os quatro episódios de Joshikou-hen correspondem ao bloco 16–19 pela posição e pelos títulos publicados. O agrupador mantém o título romanizado e o inglês em chaves distintas. [Títulos alternativos](https://www.themoviedb.org/tv/100049/titles) · [Especiais de TONIKAWA](https://www.themoviedb.org/tv/100049/season/0).

### Naruto Shippuden

- **Bakashi.** [Naruto Shippuden](https://bakashi.top/anime/naruto-shippuden-1a-temporada) → tv:31910.
- **HinataSoul.** [Naruto Shippuden](https://www.hinatasoul.com/animes/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) (episódios 500/500 Episódios) → tv:31910 · [Naruto Shippuden - Dublado](https://www.hinatasoul.com/anime-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) (áudio dublado · episódios 112/500 Episódios) → tv:31910 · [Naruto: Shippuden Movie 1](https://www.hinatasoul.com/animes/b93d597efdd5b1e2c97164ff26c6cc2082db76bc) (episódios 01/01 Episódios) → title:naruto shippuden movie 1 · [Naruto: Shippuden Movie 2 - Kizuna](https://www.hinatasoul.com/animes/0b63fb3b76c56cb13171ab135f78c28f7ed8e83f) (episódios 01/01 Episódios) → title:naruto shippuden movie 2 kizuna.
- **AniTube22.** [Naruto Shippuden](https://www.anitube22.vip/anime/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) → tv:31910 · [Naruto Shippuden - Dublado](https://www.anitube22.vip/animes-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) (áudio dublado) → tv:31910 · [Naruto: Shippuden Movie 1](https://www.anitube22.vip/anime/b93d597efdd5b1e2c97164ff26c6cc2082db76bc) → title:naruto shippuden movie 1 · [Naruto: Shippuden Movie 2 - Kizuna](https://www.anitube22.vip/anime/0b63fb3b76c56cb13171ab135f78c28f7ed8e83f) (episódios 01/01) → title:naruto shippuden movie 2 kizuna.
- **AniTube.** [Naruto Shippuden](https://www.anitube.vip/anime/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) → tv:31910 · [Naruto Shippuden - Dublado](https://www.anitube.vip/animes-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) (áudio dublado) → tv:31910 · [Naruto: Shippuden Movie 1](https://www.anitube.vip/anime/b93d597efdd5b1e2c97164ff26c6cc2082db76bc) → title:naruto shippuden movie 1 · [Naruto: Shippuden Movie 2 - Kizuna](https://www.anitube.vip/anime/0b63fb3b76c56cb13171ab135f78c28f7ed8e83f) (episódios 01/01) → title:naruto shippuden movie 2 kizuna.

A série é tv/31910, Naruto anterior tv/46260, Kizuna/Bonds movie/17581 e o primeiro filme Shippuden movie/20982. A ordem de temporada do TMDB precisa ser validada antes de converter numeração linear.

## Verificação de episódios

As páginas HTML de episódios das edições principais de One Piece e Naruto Shippuden foram percorridas nas três fontes externas. Os JSONs registram a fila, falhas, rótulos e IDs internos deduplicados. A identificação de áudio veio da classificação do catálogo. No Bakashi, a verificação usou a listagem JSON anunciada nas páginas das obras, no escopo de temporada registrado em cada entrada.

| Fonte e edição | Páginas percorridas | Episódios únicos | Estado |
|---|---:|---:|---|
| Bakashi · [Naruto Shippuden](https://bakashi.top/anime/naruto-shippuden-1a-temporada) | 10 | 500 | concluída nas páginas anunciadas · temporada 1 da fonte |
| Bakashi · [One Piece](https://bakashi.top/anime/one-piece-1a-temporada) | 24 | 1180 | concluída nas páginas anunciadas · temporada 1 da fonte |
| Bakashi · [One Piece Dublado](https://bakashi.top/anime/one-piece-dublado-1a-temporada) | 18 | 891 | concluída nas páginas anunciadas · temporada 1 da fonte |
| HinataSoul · [One Piece - Dublado](https://www.hinatasoul.com/anime-dublado/7804b6bdda34932920657ba29e64025244f485c7) | 36 | 842 | concluída nas páginas anunciadas |
| HinataSoul · [Naruto Shippuden - Dublado](https://www.hinatasoul.com/anime-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) | 13 | 309 | concluída nas páginas anunciadas |
| HinataSoul · [One Piece](https://www.hinatasoul.com/animes/e1eaa4181415abd4e16cce073629ee329ebd3200) | 50 | 1185 | concluída nas páginas anunciadas |
| HinataSoul · [Naruto Shippuden](https://www.hinatasoul.com/animes/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) | 20 | 476 | concluída nas páginas anunciadas |
| AniTube22 · [One Piece - Dublado](https://www.anitube22.vip/animes-dublado/7804b6bdda34932920657ba29e64025244f485c7) | 36 | 842 | concluída nas páginas anunciadas |
| AniTube22 · [Naruto Shippuden - Dublado](https://www.anitube22.vip/animes-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) | 13 | 309 | concluída nas páginas anunciadas |
| AniTube22 · [One Piece](https://www.anitube22.vip/anime/e1eaa4181415abd4e16cce073629ee329ebd3200) | 50 | 1185 | concluída nas páginas anunciadas |
| AniTube22 · [Naruto Shippuden](https://www.anitube22.vip/anime/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) | 20 | 476 | concluída nas páginas anunciadas |
| AniTube · [One Piece - Dublado](https://www.anitube.vip/animes-dublado/7804b6bdda34932920657ba29e64025244f485c7) | 36 | 842 | concluída nas páginas anunciadas |
| AniTube · [Naruto Shippuden - Dublado](https://www.anitube.vip/animes-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) | 13 | 309 | concluída nas páginas anunciadas |
| AniTube · [One Piece](https://www.anitube.vip/anime/e1eaa4181415abd4e16cce073629ee329ebd3200) | 50 | 1185 | concluída nas páginas anunciadas |
| AniTube · [Naruto Shippuden](https://www.anitube.vip/anime/ce2d64638ce1a0d3928d04cd395e462c1c834b1a) | 20 | 476 | concluída nas páginas anunciadas |

No Naruto Shippuden dublado, o card do HinataSoul registrava 112/500. A paginação feita na manhã de 24 de novembro expôs 309 IDs e rótulos até o episódio 316, com lacunas na sequência. No One Piece dublado, o card mostrava 849/?? e as páginas anunciaram 842 IDs distintos. Os registros foram obtidos em momentos diferentes. [Naruto Shippuden dublado](https://www.hinatasoul.com/anime-dublado/75b296267e8ab2135b2dee3a771a2ad2c5dbb1fc) · [One Piece dublado](https://www.hinatasoul.com/anime-dublado/7804b6bdda34932920657ba29e64025244f485c7).

Reapliquei o extrator de numeração e flat_season_ranges do ZIP aos rótulos obtidos. Nas três fontes externas, One Piece contém números repetidos em IDs diferentes, inclusive 611, 612 e 613 na edição dublada. A função rejeitou a divisão automática por temporadas em ambas as edições. Para Naruto Shippuden dublado, a regra aceitou os intervalos mesmo com lacunas. Na edição sem áudio indicado, a travessia encontrou 476 IDs em cada fonte externa, e o endpoint do Bakashi retornou 500. As contagens são de registros anunciados. [One Piece no AniTube](https://www.anitube.vip/anime/e1eaa4181415abd4e16cce073629ee329ebd3200) · [Naruto Shippuden no Bakashi](https://bakashi.top/anime/naruto-shippuden-1a-temporada).

## TMDB

O addon integra a API por ajuste de usuário com valor padrão vazio no ZIP. O teste sem credencial recebeu 401. A verificação usou as páginas públicas e o índice da distribuição. A consulta autenticada pelo addon ficou pendente.

| Registro público | Título original ou alternativo exibido | Temporadas |
|---|---|---|
| [tv/37854 · One Piece (TV Series 1999)](https://www.themoviedb.org/tv/37854) | ワンピース | [0–23 (24 registros)](https://www.themoviedb.org/tv/37854/seasons) |
| [tv/137390 · Birdie Wing -Golf Girls' Story- (TV Series 2022)](https://www.themoviedb.org/tv/137390) | BIRDIE WING -Golf Girls' Story- | [1 (25 ep.)](https://www.themoviedb.org/tv/137390/seasons) |
| [tv/82684 · That Time I Got Reincarnated as a Slime (TV Series 2018)](https://www.themoviedb.org/tv/82684) | 転生したらスライムだった件 | [0 (16 ep.), 1 (24 ep.), 2 (24 ep.), 3 (24 ep.), 4 (24 ep.)](https://www.themoviedb.org/tv/82684/seasons) |
| [tv/99073 · I've Been Killing Slimes For 300 Years And Maxed Out My Level (TV Series 2021)](https://www.themoviedb.org/tv/99073) | スライム倒して300年、知らないうちにレベルMAXになってました | [1 (12 ep.), 2 (12 ep.)](https://www.themoviedb.org/tv/99073/seasons) |
| [tv/3570 · Sailor Moon (TV Series 1992)](https://www.themoviedb.org/tv/3570) | 美少女戦士セーラームーン | [0 (3 ep.), 1 (46 ep.), 2 (43 ep.), 3 (38 ep.), 4 (39 ep.), 5 (34 ep.)](https://www.themoviedb.org/tv/3570/seasons) |
| [tv/61339 · Sailor Moon Crystal (TV Series 2014)](https://www.themoviedb.org/tv/61339) | 美少女戦士セーラームーンCrystal | [1 (14 ep.), 2 (12 ep.), 3 (13 ep.)](https://www.themoviedb.org/tv/61339/seasons) |
| [tv/31910 · Naruto Shippuden (TV Series 2007)](https://www.themoviedb.org/tv/31910) | ナルト 疾風伝 | [0–20 (21 registros)](https://www.themoviedb.org/tv/31910/seasons) |
| [tv/46260 · Naruto (TV Series 2002)](https://www.themoviedb.org/tv/46260) | ナルト | [0 (2 ep.), 1 (52 ep.), 2 (52 ep.), 3 (54 ep.), 4 (62 ep.)](https://www.themoviedb.org/tv/46260/seasons) |
| [tv/100049 · TONIKAWA: Over The Moon For You (TV Series 2020)](https://www.themoviedb.org/tv/100049) | トニカクカワイイ | [0 (19 ep.), 1 (12 ep.), 2 (12 ep.)](https://www.themoviedb.org/tv/100049/seasons) |
| [movie/900667 · One Piece Film: Red (2022)](https://www.themoviedb.org/movie/900667) | ONE PIECE FILM RED | — |
| [movie/618851 · Pretty Guardian Sailor Moon Eternal: O Filme - Parte 1 (2021)](https://www.themoviedb.org/movie/618851) | 劇場版 美少女戦士セーラームーンEternal 前編 | — |
| [movie/784500 · Pretty Guardian Sailor Moon Eternal: O Filme - Parte 2 (2021)](https://www.themoviedb.org/movie/784500) | 劇場版 美少女戦士セーラームーンEternal 後編 | — |
| [movie/968868 · Pretty Guardian Sailor Moon Cosmos: O Filme – Parte 1 (2023)](https://www.themoviedb.org/movie/968868) | 劇場版 美少女戦士セーラームーンCosmos 前編 | — |
| [movie/968870 · Pretty Guardian Sailor Moon Cosmos: O Filme – Parte 2 (2023)](https://www.themoviedb.org/movie/968870) | 劇場版 美少女戦士セーラームーンCosmos 後編 | — |
| [movie/876792 · That Time I Got Reincarnated as a Slime - Laços Escarlates (2022)](https://www.themoviedb.org/movie/876792) | 劇場版 転生したらスライムだった件 紅蓮の絆編 | — |
| [movie/20982 · Naruto Shippuden: O Filme (2007)](https://www.themoviedb.org/movie/20982) | 劇場版 NARUTO -ナルト- 疾風伝 | — |
| [movie/17581 · Naruto Shippuden O Filme: Laços (2008)](https://www.themoviedb.org/movie/17581) | 劇場版 NARUTO -ナルト- 疾風伝 絆 | — |
| [tv/98034 · Digimon Adventure: (TV Series 2020)](https://www.themoviedb.org/tv/98034) | デジモンアドベンチャー： | — |
| [tv/31654 · Digimon (TV Series 1999)](https://www.themoviedb.org/tv/31654) | デジモンアドベンチャー | — |
| [tv/9410 · Basilisk (TV Series 2005)](https://www.themoviedb.org/tv/9410) | バジリスク甲賀忍法帖 | — |
| [tv/111110 · ONE PIECE: A Série (TV Series 2023)](https://www.themoviedb.org/tv/111110) | ONE PIECE | — |

## Sugestões de correção

1. Abrir os catálogos nas rotas próprias, visitar páginas e letras e registrar a seção de origem. Detectar repetições por conteúdo e validar mudanças de domínio.
2. Preservar título visível, título e texto alternativo da imagem. Resolver áudio com precedência explícita entre rótulo de item, seção, slug e servidor, guardando a evidência e o estado desconhecido.
3. Dar à obra uma identidade por tipo e ID. Guardar edição de áudio, temporada, parte e intervalo de episódios como atributos separados. Cadastrar aliases com escopo, inclusive em filmes com Part 1 e Part 2.
4. Exigir compatibilidade de tipo e ano antes de propagar um ID TMDB por título normalizado. Validar nomes alternativos e posições de especiais. Detectar números reaproveitados, separar especiais e preservar o número publicado antes de calcular intervalos do TMDB. Testar cortes de temporadas, filmes homônimos e endereço canônico.
5. Adicionar testes de regressão com os cards e URLs deste relatório e comparar as chaves do agrupador antes e depois de qualquer ajuste.
