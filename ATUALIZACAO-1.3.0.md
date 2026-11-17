# AnimesPlay 1.3.0

Revisão do log Kodi 21.3/Android e das três imagens enviadas. O log pessoal não está incluído no pacote.

## Correções

- URLs de navegação e reprodução usam referências locais persistentes de 24 caracteres. Sinopses, imagens e o JSON do item não são mais transportados nas novas URLs. Atalhos antigos por query continuam aceitos. O avanço automático usa a mesma referência local.
- Prefixo dos episódios centralizado: `[B] EPISÓDIO 07:[/B] [COLOR yellow]Nome[/COLOR]`, incluindo lançamentos, favoritos e retomada. Limpeza de duração/data dos títulos de origem. Lançamentos agora procuram o anime pai e os metadados do episódio específico, quando a associação é segura.
- O reagrupamento preserva pôster, fanart, sinopse e ano enriquecidos. Antes, parte desses campos se perdia ao reconstruir as variantes, deixando a imagem padrão.
- Black Clover e Black Clover 2 foram consultados nas seis fontes e no TMDB. Ambos corresponderam ao ID 73223; a temporada 2 foi confirmada na lista de temporadas do TMDB. As edições são agrupadas sem perder a temporada de origem. Uma continuação com título e ID próprios mantém sua identidade. Não se removem todos os números indiscriminadamente. A busca agrupa a página retornada antes de paginar localmente; ao abrir a obra, consulta variantes nas outras fontes. Não existe sincronização integral de todos os títulos/páginas das seis fontes.
- Nomes japoneses nos créditos não indicam, por si, corrupção UTF-8: a skin das imagens não exibe esses glifos. Para créditos enriquecidos, o addon busca nomes/aliases latinos oficiais de cada pessoa no TMDB, com cache. Se não houver alternativa legível, evita exibir o nome com glifos incompatíveis; não inventa transliteração. O addon não altera a fonte da skin.
- Busca Sushi combina o cartão de imagem com o link do título, deixando de usar HD/FULLHD como nome. Preserva a capa do cartão original.
- Paginação AniTure usa `/page/N/`; lançamentos AnimesOnlines usam `?ep_pg=N`. A segunda página desses sites e do Sushi foi conferida: nenhuma URL de episódio em comum com a primeira nas amostras.
- Próxima página aparece em amarelo com número e descrição de continuação. Menus principais usam imagens reais de animes obtidas no TMDB, empacotadas localmente. Créditos abaixo.
- Validador tenta uma consulta sem Range quando o mesmo endereço rejeita Range com 403/405/416, mantendo leitura limitada a 2048 bytes. Não considera HTML um vídeo válido. Player AniTure alternativo agora consulta sua API pública de resolução quando o endereço contém o identificador no fragmento; o arquivo testado retornou 404.
- Log normal da reprodução tem um resumo; o detalhamento das etapas permanece no diagnóstico local. Diagnóstico de catálogo agregado não atribui o último HTTP 403 do Goyabu ao resultado combinado de todas as fontes. O objeto Addon da navegação é liberado ao terminar, e o backend cached é inicializado apenas quando necessário. Isso não permite garantir a eliminação de todos os avisos CPythonInvoker de módulos externos.

## Testes reais e limites

94 testes automatizados passaram no pacote extraído. Cobrem rotas antigas/novas, retomada, agrupamento/temporadas, preservação de arte, nomes oficiais, seletores e validação de mídia. Testes Kodi usam módulos simulados: não há Kodi/Flixbox instalado neste ambiente, portanto não houve validação audiovisual nem visual da skin no Samsung.

| Fonte | Resultado da amostra nesta revisão |
| --- | --- |
| MetiAnimes | Pokémon 1: motor e manifesto HLS validados novamente. Black Clover 1: player resolve, mas a mídia não pôde ser lida nesta rede. |
| AnimesDigital | 60 edições no catálogo; episódio Dragon Ball Super: Beerus testado com manifesto HLS válido. |
| Goyabu | Catálogo, busca Black Clover/2 e players reconhecidos; Google Video não pôde ser lido nesta rede. |
| AniTure | Catálogo/episódios e paginação reconhecidos. Black Clover 2x01: Google Video sem acesso nesta rede; Byse respondeu arquivo inexistente e o player alternativo retornou 404. Não confirmado. |
| SushiAnimes | Catálogo, títulos da busca e paginação corrigidos. A API de vídeo da amostra exige confirmação de idade (`age_verification_required`, HTTP 403). Não confirmado. |
| AnimesOnlines | Catálogo, busca e paginação reconhecidos; iframe AniDrive recusou consulta com HTTP 403. Não confirmado. |

O log enviado mostra Devils’ Crest chegando a abrir H.264 1080p e AAC no Kodi. Mostra também falhas reais 403 de outros vídeos no aparelho; corrigir menus não garante a disponibilidade desses servidores. Não se afirma que todos os sites/episódios estejam reproduzindo. Os erros `PCRE '*.mp4'`, includes ausentes da skin e plugins externos inexistentes não aparecem no código deste addon e não foram corrigidos alterando a instalação do usuário.

Evidências sem credenciais e sem URLs assinadas: `six-live13.json`, `black13-live.json` e `live-final13.json` nesta pasta. Os testes são amostrais, não uma verificação de todos os episódios dos seis catálogos.

## Instalação

Atualize pelo ZIP 1.3.0 e reinicie Kodi/Flixbox. Abra o addon novamente para gerar as novas URLs compactas; atalhos antigos guardados fora dele podem continuar aparecendo extensos no log. Favoritos, histórico e associações manuais permanecem no perfil. Os nomes/aliases oficiais só são exibidos quando disponíveis no TMDB.

## Artes

Imagens de menu sem alteração obtidas via TMDB: One Piece (37854), Pokémon (31911), Naruto (46260), Demon Slayer (85937), Attack on Titan (1429), Bleach (30984). Arquivos correspondentes: explore, latest_sources, search, favorites, continue, next. O fundo do menu usa a mesma imagem de One Piece; o ícone do addon usa a imagem de Demon Slayer. As artes repetidas são referenciadas pelo mesmo arquivo para reduzir o ZIP. Imagens e marcas pertencem aos respectivos titulares. This product uses the TMDB API but is not endorsed or certified by TMDB.
