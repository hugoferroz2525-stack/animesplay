# AnimesPlay 1.2.0

Atualização baseada nas seis fontes indicadas e no log do Flixbox/Kodi 21.3 com Python 3.11 enviado pelo usuário. O log completo não foi incluído no ZIP nem no GitHub.

## Causa da falha relatada

Pokémon 1 e 22 usam, via MyEmbed/PlayerFlix, o serviço VIP Embedplayer. A versão 1.1.0 não consultava a API desse player. Foi implementada a chamada oficial de leitura com sessão e o uso de `securedLink`, preservando a assinatura. O caso Pokémon 1 passou de ponta a ponta pelo motor e pelo validador. Além do manifesto HLS, a playlist de mídia e 1024 bytes do primeiro segmento MPEG-TS foram lidos com sucesso.

O log de Black Clover também indicava que só a qualidade escolhida estava sendo testada. Agora, se ela falhar, as outras qualidades reconhecidas são tentadas. O Kodi recebe os cookies aplicáveis ao endereço da mídia; para InputStream Adaptive são informados tanto cabeçalhos de manifesto quanto de segmentos. O timeout de consulta Meti foi ampliado de 15 para 25 segundos; isso reduz falhas transitórias, mas não garante disponibilidade de uma página lenta.

## Navegação e metadados

- Catálogo e busca reúnem as seis fontes; sem seletor público por nome de site. As variantes carregadas são agrupadas por título normalizado ou identidade TMDB reconhecida. Ao abrir uma obra, a busca consulta as fontes novamente para encontrar variantes além daquela página. Isso não é uma sincronização integral de todos os catálogos em segundo plano.
- Fluxo: anime → Dublado/Legendado → Servidor 1, Servidor 2… → episódios. Quando a fonte não declara áudio, a disponibilidade é confirmada ao abrir/resolver a edição; MyEmbed filtra o idioma anunciado pela API.
- Clicar no episódio reproduz automaticamente. “Escolher player ou qualidade” fica no menu de contexto. A janela de contexto somente inicia uma nova rota PlayMedia; a resolução usa o handle de reprodução apropriado.
- Rótulo: `[B] EPISÓDIO 03:[/B] [COLOR yellow]Nome do episódio[/COLOR]`. Apenas o prefixo fica em negrito. A skin pode definir sua própria apresentação de rótulos.
- Identificação automática conservadora no TMDB: somente correspondência exata de título/original, gênero animação e ano compatível quando declarado. Associações manuais existentes têm prioridade. Traduções sem correspondência exata podem continuar separadas e precisam de associação manual; não são agrupadas por mera semelhança.
- Para os episódios reconhecidos, consulta temporada e detalhes individuais: título, sinopse, data, duração quando fornecida, elenco/participações, equipe, IDs externos, imagens e vídeos. São aplicados os campos aceitos pelo InfoTagVideo; pôster/thumb/fanart vêm do TMDB quando existem. Nenhum dado é inventado quando o TMDB não fornece o campo. Numeração que não corresponde à temporada mantém os dados da fonte.

## Resultado dos testes reais das seis fontes

| Fonte | Resultado nesta revisão |
| --- | --- |
| Goyabu | Catálogo/players reconhecidos. URLs Google Video identificadas; a rede deste ambiente recusa o túnel HTTP com 403. Não foi confirmada reprodução audiovisual no Kodi. |
| MetiAnimes | Caso Pokémon 1 do log: motor, manifesto HLS e primeiro segmento MPEG-TS validados. |
| AnimesDigital | Catálogo AJAX corrigido (60 edições entre dubladas/legendadas na página testada), player Anivideo, manifesto HLS e primeiro segmento MPEG-TS validados. |
| SushiAnimes | Catálogo e opções reconhecidos. A API retorna `age_verification_required` com HTTP 403, exigindo confirmação de idade no próprio serviço. O addon informa a restrição; não declara a reprodução como aprovada. |
| AniTure | Catálogo/episódios/players reconhecidos. Google Video bloqueado pela rede do ambiente; o outro embed não forneceu fonte reconhecida. Reprodução não confirmada. |
| AnimesOnlines | Catálogo/episódios reconhecidos. O iframe AniDrive retornou HTTP 403 neste ambiente. Reprodução não confirmada. |

O episódio 1 de Pokémon foi identificado automaticamente como TMDB 60572, com título “Pokémon, Eu Escolho Você!” e imagem própria do episódio. Evidências sem credenciais ou links assinados estão em `six-live.json`, `tmdb12-live.json` e `hls-segments12.json`. A listagem Digital foi corrigida após o primeiro registro de `six-live.json`; o teste posterior retornou 60 itens.

## Verificação e limites

84 testes locais passaram antes de empacotar. Cobrem o fluxo VIP, assinaturas, catálogo AJAX, agrupamento de variantes, escolha/fallback de qualidade, metadados individuais e formato/ação dos episódios, além das regressões anteriores. O ZIP é extraído e testado novamente.

Este ambiente não tem o aplicativo Kodi/Flixbox instalado. O motor HTTP foi testado realmente; a API Kodi é simulada nos testes. Não foi possível validar áudio/vídeo e skin no aparelho do usuário. O log mostra que a falha relatada ocorre antes de abrir o player de vídeo; avisos da skin do Flixbox também existem, mas não foram tratados como causa sem evidência.

Referências oficiais consultadas: [ListItem e contexto](https://xbmc.github.io/docs.kodi.tv/master/kodi-dev-kit/group__python__xbmcgui__listitem.html), [InfoTagVideo](https://xbmc.github.io/docs.kodi.tv/master/kodi-dev-kit/group__python___info_tag_video.html), [setResolvedUrl](https://xbmc.github.io/docs.kodi.tv/master/kodi-dev-kit/group__python__xbmcplugin.html), [InputStream Adaptive](https://github.com/xbmc/inputstream.adaptive).

## Instalação

Instale o ZIP 1.2.0 como atualização do mesmo ID, reinicie o Kodi/Flixbox e abra o addon novamente. Favoritos, histórico e associações manuais TMDB permanecem no perfil. Teste Pokémon 1 na edição dublada e escolha outro servidor quando um serviço remoto recusar o acesso. Não é necessário Chromium ou um servidor auxiliar.
