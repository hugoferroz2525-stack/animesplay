# AnimesPlay 1.4.0

## Resultado

Corrigido um player real ignorado no Sushi. Black Clover dublado, temporada 1, episódio 1, passou pela validação MP4, pela leitura dos codecs (H.264 1920×1080 e AAC) e pela decodificação de dois segundos de vídeo e áudio com FFmpeg. Esses testes ocorreram fora do Kodi; não há Kodi/Flixbox instalado neste ambiente.

A troca automática foi verificada ao vivo em Goyabu → Sushi (Black Clover dublado 1x01) e AniTure → Sushi (Black Clover dublado 1x44, episódio citado no log). A indisponibilidade do servidor inicial deixa de encerrar a tentativa quando uma cópia correspondente está disponível em outra fonte. Isso não significa que os bloqueios do servidor inicial tenham sido removidos.

## Alterações

- Sushi: leitura do `iframe srcdoc` e da variável pública `playerEmbed` declarada no documento interno. Extração limitada, sem executar JavaScript. O arquivo assinado é preservado e os cabeçalhos Referer, Origin e User-Agent seguem o player/site. O resolvedor anterior reconhecia apenas iframes com `src` e ignorava o player nativo.
- Reprodução automática: após falha da fonte escolhida, procura alternativas nas fontes integradas. Exige a mesma identidade TMDB, temporada, episódio e áudio. Entradas ambíguas não são escolhidas; áudio desconhecido não é adivinhado. Para Meti, o áudio solicitado é conferido pela API do player. Máximo de quatro alternativas de mídia; pesquisas podem consultar as fontes para encontrá-las. Cancelamento é respeitado.
- Uma qualidade/player escolhido manualmente permanece nessa escolha; não muda de fonte nesse modo. O ajuste **Tentar outro servidor quando o episódio falhar** permite desligar a alternância automática.
- Histórico/retomada permanecem associados ao episódio original. URLs temporárias e cookies não são gravados em relatórios. As opções continuam com nomes Servidor 1, Servidor 2 etc.
- Goyabu: número do episódio nos lançamentos é extraído do marcador de episódio, permitindo metadados e associação precisa. Falhas HTTP ao consultar opções agora aparecem como etapa específica no diagnóstico.

## Evidências

105 testes automatizados passaram no ZIP extraído. Incluem separação de temporada/áudio/identidade, rejeição de episódios ambíguos, cancelamento, opção manual e player srcdoc, além das regressões anteriores. A API Kodi é simulada nos testes.

Arquivos sem credenciais, cookies nem endereços de mídia assinados: `sushi14-live.json`, `sushi14-codecs.json`, `sushi14-decode.json`, `failover14-live.json`, `more14-live.json`, `onlines14-live.json` e `investigation14.json` nesta pasta.

| Caso real | Resultado |
| --- | --- |
| Sushi / Black Clover dublado 1x01 | MP4 válido; H.264 1080p + AAC; dois segundos decodificados com sucesso. |
| Goyabu / Black Clover dublado 1x01 | Fonte inicial não entregou mídia; alternativa Sushi validada para o mesmo episódio. |
| AniTure / Black Clover dublado 1x44 | Google Video inacessível nesta rede; alternativa Sushi validada para o mesmo episódio. |
| AniTure / Black Clover dublado 1x01 | Consulta inicial sem mídia utilizável; alternativa Sushi validada. |
| AnimesOnlines / Psyren dublado 1x04 | AniDrive retornou HTTP 403; alternativa encontrada também não pôde ser lida nesta rede. Não confirmado. |
| AnimesOnlines / Black Clover 2 | AniDrive retornou HTTP 403; alternativa encontrada também falhou na leitura de mídia. Não confirmado. |

## Bloqueios restantes

Google Video: em parte das amostras a recusa ocorre no estabelecimento do túnel de rede deste ambiente, antes da resposta do servidor de vídeo. Trocar Referer/Origin não remove essa restrição. O log Android enviado também contém HTTP 403, mas esse log não demonstra que a causa seja idêntica à da rede de testes.

AniDrive: a resposta 403 tem sinais Cloudflare. As consultas com sessão e cabeçalhos de iframe não liberaram os vídeos testados. Alguns players AniTure apontam para arquivo ausente (404). Conteúdo que exige confirmação de idade continua exigindo a verificação no serviço. Não foram fabricados cookies de liberação ou tokens, nem declarada a idade do usuário automaticamente.

Portanto, não estão confirmados todos os episódios das seis fontes. O ganho concreto é o novo player funcional do Sushi e a recuperação automática de falhas quando há uma cópia correspondente validada. Os resultados são amostrais; disponibilidade remota muda.

## Configuração TMDB e credenciais

A chave embutida herdada da versão antiga foi retirada do pacote público. Configure sua própria chave de API ou token de leitura TMDB nos ajustes. Se já existe uma chave configurada no perfil Kodi, ela é mantida. Sem credencial, os players continuam disponíveis, mas novos enriquecimentos e alternativas que precisam de identificação TMDB podem não ser encontrados. O menu inicial mostra Configurar metadados TMDB enquanto o campo estiver vazio. Uma API sem token não faz consultas anônimas repetidas.

## Instalação

Instale o ZIP 1.4.0 como atualização e reinicie Kodi/Flixbox. Abra novamente o addon e reproduza o episódio em modo automático. Quando a fonte falhar, a janela informa a tentativa de uma alternativa. Não é necessário FFmpeg, navegador ou servidor auxiliar instalado no aparelho; FFmpeg foi usado somente para o teste externo.
