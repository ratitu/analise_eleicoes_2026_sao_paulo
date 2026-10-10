# Eleições 2026 — São Paulo: resultado por distrito municipal

Análise e visualização do 1º turno da eleição para **Governador de SP (04/10/2026)**, com votação agregada por **seção eleitoral** (TSE) aos **96 distritos municipais de São Paulo** (`CD_MUNICIPIO = 71072`), via geocodificação de endereços + point-in-polygon.

## Mapa interativo — `index.html`

`index.html` é o entregável principal: um **HTML estático e autocontido** (sem backend, sem build) com um choropleth dos 96 distritos por **margem assinada em pontos percentuais** (pp) — convenção herdada de `output/mapa_distritos_margem_2026.png`.

- **Dados**: GeoJSON embutido no HTML (96 features com `CD_DIST`, `NM_DIST`, vencedor, partido, votos e % de cada candidato, margem em pp e em votos, votos válidos). Fonte: **TSE**.
- **Basemap**: imagens de satélite **Esri World Imagery** (`server.arcgisonline.com`…`World_Imagery/MapServer`, `maxZoom: 19`, atribuição Esri/Maxar/Earthstar).
- **Biblioteca**: Leaflet 1.9.4 via unpkg (`preferCanvas: true`).
- **Interação**: zoom/pan; clicar num distrito dá `fitBounds` no polígono; legenda colapsável com barra de gradiente (`Haddad +pp` ⇄ `Tarcísio +pp`) e faixa de empate (`|margem| < 0,05 pp`); rodapé com totais (6.136.450 votos válidos · Tarcísio 52,70% · Haddad 46,04%).
- **Hooks de QA**: `window.__feats` (96), `window.__mapLayer`, `window.__corMargem`, `window.__MAX_PP = 37.86` — úteis para verificação automatizada em browser.

## Pipeline R de agregação

As seções eleitorais são agregadas aos distritos em 6 etapas; cada script resolve o próprio diretório de trabalho e pode ser chamado de qualquer lugar, **na ordem**:

```bash
Rscript scripts/step1_load_data.R          # Extrai locais de votação + dissolve setores censitários 2022 -> cache/districts_dissolved.gpkg (96 distritos)
Rscript scripts/step2_normalize_places.R   # Normaliza strings (seguro p/ Latin-1) -> cache/votes_clean.csv, cache/voting_places_unique.csv
Rscript scripts/step3_geocode.R            # Geocodifica locais únicos com OSM Photon -> cache/geocode_result.csv (retomável via cache/geocode_cache.rds)
Rscript scripts/step4_join_aggregate.R     # Join espacial (pontos -> distritos; fallback vizinho mais próximo <= 500 m) -> cache/votes_with_distrito.csv
Rscript scripts/step5_results_qc.R         # Vencedores por distrito + gates de QC Q1-Q4 -> output/distritos_vencedor_2026.csv, output/votos_distritos_2026.csv
Rscript scripts/step6_maps.R               # 4 mapas coropléticos (300 DPI) -> output/mapa_distritos_*.png
```

Fluxos de base (standalone):
- `Rscript run_analysis.R` — vencedor por seção (`output/section_winners_2026.csv`, 26.683 seções).
- `Rscript map_zonas.R` — choropleth por zona eleitoral (`output/choropleth_zonas_2026.png`).

### Armadilhas críticas de dados & encoding

1. **Formato do CSV-fonte**: `data/votacao_secao_2026_BR_71072.csv` é **delimitado por `;`** e **ISO-8859-1 / Latin-1**. Sempre ler com `data.table::fread(..., sep = ";", encoding = "Latin-1")`.
2. **Normalização de texto**: nunca passar strings Latin-1 cruas a `stringr::str_to_upper()`. Usar `iconv(x, "latin1", "UTF-8", sub = "")`, `toupper()` e `trimws()` da base R.
3. **Unicidade do local de votação**: `NR_LOCAL_VOTACAO` **não é único entre zonas eleitorais**. A chave do local é sempre `(NR_ZONA, NM_CLEAN, ADDR_CLEAN)`.
4. **Definição de votos válidos**: excluir `NR_VOTAVEL %in% c(95L, 96L)` (brancos e nulos). Filtro: `ANO_ELEICAO == 2026 & CD_MUNICIPIO == 71072 & DS_CARGO == "Presidente" & NR_TURNO == 1`.
5. **Chave do distrito**: normalizar `CD_DIST` como string de 2 dígitos com zero à esquerda (`sprintf("%02d", as.numeric(CD_DIST))`) ao unir com `districts_dissolved.gpkg`.
6. **Candidatos**: casar totais com `grepl("LULA", toupper(NM_VOTAVEL))` e `grepl("BOLSONARO", toupper(NM_VOTAVEL))`. Metadados em `data/consulta_cand_2026.zip` (chave `SQ_CANDIDATO`).

### Geocodificação & invariantes espaciais

- **Endpoint Photon**: `https://photon.komoot.io/api/?q=<urlenc>&limit=1&lang=default&bbox=-46.92,-24.05,-46.28,-23.30`. Não usar `lang=pt` (não suportado).
- **Rate limit & resiliência**: máx. 1,5 req/s (sleep mínimo 0,70 s). Cache escrito a cada 25 registros em `cache/geocode_cache.rds` para retomar execuções.
- **Honestidade estrita**: *nunca fabricar coordenadas/votos*. Locais não geocodificados permanecem `NA` e são reportados; pontos fora dos polígonos usam `sf::st_nearest_feature` apenas até 500 m com flag `metodo_distrito = "nearest"`.
- **Validade topológica**: dissolução de setores com `sf_use_s2(FALSE)` → `st_make_valid()` → `st_union()` → `st_make_valid()` → `sf_use_s2(TRUE)`.

### Gates de controle de qualidade (QC)

`scripts/step5_results_qc.R` aplica assertivas duras (`stopifnot`):

- **Q1 (conservação de votos)**: soma de votos válidos por distrito = referência municipal (`GATE_VALIDOS = 6553181L`) dentro de `TOL = 0.0001` (0,01%).
- **Q2 (vencedor inequívoco)**: exatamente um vencedor por distrito; zero `NA`.
- **Q3 (faixa de %)** : share dos candidatos ∈ [0, 1] para todos os distritos.
- **Q4 (completude)**: nº de distritos cobertos = nº de distritos dissolvidos (96).

## Restrições de ambiente

- **Sem instalação de pacotes**: `install.packages()` é proibido; usar apenas pacotes pré-instalados (`data.table`, `sf`, `ggplot2`, `jsonlite`, `dplyr`).
- **Device de mapa**: `ragg` está quebrado neste runtime; mapas e `ggsave` devem usar Cairo explicitamente (`grDevices::png(..., type = "cairo")`).
- **Baseline somente-leitura**: não modificar/remover `data/`, `run_analysis.R`, `map_zonas.R` nem `output/section_winners_2026.csv`.

