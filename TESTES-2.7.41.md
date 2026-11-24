# AniPlay Experimental 2.7.41

Base testada: os 98 arquivos do ZIP distribuído 2.7.40 no commit `3f8a264122fdf9215e466c3d2d50704feff004b4`, com SHA-256 `979c96261a7cc1d41b5e6d732856a55226fa56809890dfe10a9a627b62533e10`. O checkout desse commit guardava o código do addon dentro do ZIP. Os arquivos extraídos conferiram byte por byte com o pacote. Os ajustes locais citados não estavam nesse checkout. Os casos de teste vieram dos ZIPs da revisão e do catálogo, ambos verificados por CRC.

## Correções

- **Bakashi.** Quando o usuário escolhe Dublado ou Legendado, o servidor preserva a edição na rota de temporada. Se o áudio faltar ou o player falhar, só se tenta outra edição depois de uma confirmação. Cancelar encerra a resolução. Sem alternativas, há aviso de áudio indisponível.
- **AniTube22.** Foram reabertas as páginas públicas 492294, 557129, 509115 e 580081 e as 12 opções de player da revisão. Cada opção carregou HTML em outro host. O HTML recebido não apresentou mídia direta, vídeo, iframe utilizável, fonte reconhecida ou a declaração de mídia e autorização esperada pelo extrator. A falha ocorreu na descoberta da mídia, antes de validar MP4/HLS. O 2.7.41 informa que o player abriu sem enviar uma fonte de vídeo reconhecível. A amostra não comprova que todos os episódios da fonte apresentem esse problema.
- **Digimon.** O original de 1999 usa TV 31654 e o remake de 2020 usa TV 98034. O título externo confirmado do original também recebe a identidade 31654.
- **Birdie Wing.** O Worker confirmou 25 episódios na temporada 1. A lista local 13+12 preserva os URLs originais e mapeia o segundo bloco aos episódios 14–25 do TMDB.
- **One Piece.** A reaplicação sobre os checkpoints manteve 842 e 1.185 IDs nas duas edições, em cada uma das três fontes externas. Registros ambíguos foram encaminhados a Outros episódios sem deduzir uma associação pelo número. Naruto Shippuden preservou os 309 e 476 IDs das duas edições na mesma verificação.
- **Slime.** O Worker confirmou 24 episódios na temporada 2. Os segmentos regulares verificados usam 1–12 e 13–24, com a indicação local preservada. O episódio 00 de cada segmento continua acessível fora do mapeamento regular.
- **Sailor Moon Cosmos.** A lista de dois itens passa os IDs de filme 968868 e 968870 à navegação, ficha, reprodução e exportação. Os dois registros foram confirmados no Worker.
- **Áudio por URL.** O rótulo explícito do título tem prioridade. O slug e a seção de dublados acrescentam evidência. Sem indicação, permanece desconhecido.

## Verificação no Termux

| Fonte | Páginas de episódios abertas no 2.7.40 / 2.7.41 | Com mídia validada no 2.7.40 / 2.7.41 |
|---|---:|---:|
| Bakashi | 6 / 6 | 6 / 6 |
| HinataSoul | 4 / 4 | 4 / 4 |
| AniTube22 | 4 / 4 | 0 / 0 |
| AniTube | 4 / 4 | 4 / 4 |

As duas passagens usaram a rede do aparelho e o resolvedor de cada versão. Validação de mídia significa assinatura MP4 ou manifesto HLS aceito. Os testes do resolvedor não confirmam início do vídeo nem idioma ouvido. O worker público confirmou as identidades; a API autenticada do TMDB não foi exercitada.

Passaram 16 testes de regressão com dublê de Kodi. Incluem cancelamento após escolha de áudio, seleção explícita de Legendado, propagação de Dublado, aviso de player vazio, leitura de áudio pelo slug e pela seção, mapeamento de temporadas e filmes e preservação das duas URLs em uma colisão de número. O ZIP 2.7.41 passou no CRC e os 99 arquivos empacotados conferiram byte por byte com o código testado.

## Kodi Android

Nenhum fluxo foi confirmado no Kodi Android. O aparelho tinha Kodi 21.2 com Estuary e AniPlay 2.7.37. O Termux não dispõe de ADB conectado, e o Android negou acesso ao controle do estado gráfico. A instalação existente foi preservada.

Ficaram pendentes a instalação e abertura do 2.7.41, a navegação completa Anime → Áudio → Servidor → Temporada → Episódio → Qualidade, o início do vídeo, a confirmação da faixa ouvida e da resolução decodificada, a retomada pelo player, a ficha nativa e a busca e metadados com cache frio, quente e limpo no Kodi. O ensaio anterior com perfil SQLite temporário demonstrou proteção de favoritos e progresso, mas esse resultado não foi confirmado no perfil real do Kodi.

[Revisão anterior](https://github.com/hugoferroz2525-stack/animesplay/blob/b5b577f056e85a889e55c8c57980b3760f3e8cc5/auditoria/revisao-aniplay-2.7.40/relatorio.md) · [Auditoria dos catálogos](https://github.com/hugoferroz2525-stack/animesplay/blob/3d9b14ffea0662617ad28bfd35f23d3830268e65/auditoria/aniplay-2.7.40/relatorio.md)
