# AnimesPlay 1.5.0

## Alterações

- HLS usa o VideoPlayer/FFmpeg nativo por padrão. InputStream Adaptive pode ser escolhido nos ajustes; DASH continua usando Adaptive. Configurações globais do Kodi não são alteradas.
- O validador confere a playlist de mídia, o áudio anunciado e uma amostra de segmento antes de entregar HLS ao Kodi. Detecta HTML no lugar de mídia, playlists circulares e formatos não suportados, com limites de tamanho e consultas. Preserva assinaturas e não encaminha manualmente cookies/autorização a hosts diferentes.
- Retomada aguarda duração estável e verifica se o player permite saltos. Não substitui um salto manual nem restaura automaticamente uma transmissão ao vivo. O contexto inclui Reproduzir do início.
- Paginação de episódios mantém a mesma lista localmente por até 15 minutos, evitando repetir a consulta completa em cada página. Falhas opcionais de metadados não devem impedir a listagem.
- Fontes já agrupadas na obra/edição selecionada ficam vinculadas aos episódios. A recuperação confere identidade ou título canônico, ano quando informado, temporada, número e áudio, rejeitando conflitos e entradas ambíguas. Esses vínculos permitem recuperação sem credencial TMDB; novos enriquecimentos e consultas TMDB continuam exigindo uma chave/token própria nos ajustes.
- Diagnóstico recente identifica versão do código, ação, título, numeração e motivo, sem URLs de mídia, cookies ou tokens. Também registra erros anteriores à inicialização da rota. Esses registros ficam no perfil local e não são enviados automaticamente.
- As imagens locais usam versões oficiais menores dos mesmos arquivos públicos para reduzir memória e tamanho do pacote.

## Verificação e limites

119 testes automatizados passaram no ZIP extraído, incluindo HLS com áudio separado, segmentos com nomes opacos, rejeição de HTML, modo nativo/Adaptive, três páginas consecutivas, retomada adiada e recuperação por fontes vinculadas sem API.

Houve validação HTTP/HLS e decodificação externa de vídeo e áudio, inclusive após seek. O FFmpeg externo tem regras de extensões diferentes das do FFmpeg 6: o teste foi configurado para aceitar segmentos HTTP como nessa versão do Kodi. Kodi/MediaCodec Android não foi executado neste ambiente; a reprodução no aparelho precisa ser confirmada.

A disponibilidade de todos os arquivos de terceiros não é garantida. Serviços podem bloquear consultas ou remover arquivos. A recuperação depende de uma alternativa correspondente e válida. Skin, APK e preferências globais não são modificados.

## Instalação

Atualize pelo ZIP 1.5.0, reinicie Kodi/Flixbox e abra novamente a obra/lista para gerar os novos vínculos. HLS fica em Kodi nativo por padrão. Configure sua chave/token TMDB para novos metadados. Não há credencial embutida no pacote.

Os registros privados de diagnóstico, perfil, histórico, configurações e bancos locais não fazem parte desta distribuição.

Referências: [Kodi Omega / demuxer FFmpeg](https://github.com/xbmc/xbmc/blob/Omega/xbmc/cores/VideoPlayer/DVDDemuxers/DVDDemuxFFmpeg.cpp), [FFmpeg 6 / HLS](https://github.com/FFmpeg/FFmpeg/blob/n6.0/libavformat/hls.c), [routing](https://mirrors.kodi.tv/addons/omega/script.module.routing/).
