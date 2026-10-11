# Eleições 2026 — São Paulo: resultado por distrito municipal

Análise e visualização do 1º turno das eleições de 2026 (04/10/2026) na cidade de São Paulo, com a votação das **seções eleitorais** (TSE) agregada aos **96 distritos municipais** (`CD_MUNICIPIO = 71072`) via geocodificação de endereços + point-in-polygon.

São **duas disputas** sobre a mesma malha de distritos e a mesma tabela de locais de votação geocodificados:

| Disputa | Votos válidos | Resultado (96 distritos) |
|---|---|---|
| **Governador de SP** | 6.136.450 | Tarcísio (REPUBLICANOS) **70** · Haddad (PT) **26** |
| **Presidente** | 6.553.181 | Lula (PT) **52** · Bolsonaro (PL) **43** · **1 empate** |

## Aplicativo web

O entregável principal é um **site estático** (sem backend, sem build), servido a partir da própria pasta. Abra com servidor HTTP — abrir `index.html` direto do disco quebra os `iframe`:

```bash
python -m http.server   # depois acesse http://localhost:8000/index.html
```

- **`index.html`** — página de entrada (`lang="pt-BR"`). Não é um mapa: traz uma seção para cada disputa, cada uma embutindo o respectivo mapa num `iframe` (Governador imediato, Presidente sob demanda), com link para tela cheia.
- **`index_gov.html`** — choropleth dos 96 distritos para **Governador**, colorido pela **margem assinada em pontos percentuais** (Haddad +pp ⇄ Tarcísio +pp), com faixa de empate (`|margem| < 0,05 pp`).
- **`index_pres.html`** — choropleth dos 96 distritos para **Presidente**, na mesma convenção (Lula +pp ⇄ Bolsonaro +pp), incluindo o distrito de empate.
- **`index_disputa.html`** — os **26 distritos de voto dividido**: onde **Lula venceu para Presidente e Tarcísio venceu para Governador**.

Características comuns dos mapas: GeoJSON embutido no próprio HTML (96 features com `CD_DIST`, `NM_DIST`, vencedor, partido, votos e % de cada candidato, margem em pp e em votos, votos válidos); imagens de satélite **Esri World Imagery** como basemap; **Leaflet 1.9.4** via unpkg (`preferCanvas: true`); fonte dos dados: **TSE**.

Hooks de QA expostos pelos três mapas, úteis para verificação automatizada em browser: `window.__feats` (96), `window.__mapLayer`, `window.__corMargem`, `window.__MAX_PP`.

## Pipeline R de agregação

As seções eleitorais são agregadas aos distritos em etapas; cada script resolve o próprio diretório de trabalho e pode ser chamado de qualquer lugar, **na ordem**. Os passos 1–6 produzem a trilha do **Governador**; o passo 7 é a trilha do **Presidente**, independente das saídas dos passos 2–5 (consome `cache/locales_distrito.csv`):

```bash
Rscript scripts/step1_load_data.R            # Extrai locais de votação + dissolve setores censitários 2022 -> cache/districts_dissolved.gpkg (96 distritos)
Rscript scripts/step2_normalize_places.R     # Normaliza strings (seguro p/ Latin-1) + filtra votos de GOVERNADOR -> cache/votes_clean.csv, cache/voting_places_unique.csv (2.057 locais)
Rscript scripts/step3_geocode.R              # Geocodifica locais únicos com OSM Photon -> cache/geocode_result.csv (retomável via cache/geocode_cache.rds)
Rscript scripts/step4_join_aggregate.R       # Join espacial (pontos -> distritos; fallback vizinho mais próximo <= 500 m) -> cache/locales_distrito.csv
Rscript scripts/step5_results_qc.R           # Vencedores por distrito (GOVERNADOR) + gates de QC Q1-Q4 -> output/distritos_vencedor_2026.csv, output/votos_distritos_2026.csv
Rscript scripts/step6_maps.R                 # 4 mapas coropléticos do GOVERNADOR (300 DPI) -> output/mapa_sp_2026_governador_{vencedor,tarcisio_share,haddad_share,margem}.png
Rscript scripts/step7_presidente_distritos.R # Trilha do PRESIDENTE -> output/distritos_vencedor_presidente_2026.csv, output/votos_distritos_presidente_2026.csv
```

O passo 7 mapeia seção → local por `(NR_ZONA, NR_SECAO)` e local → distrito por `(NR_ZONA, NM_CLEAN, ADDR_CLEAN)`. O empate é declarado quando `|margem_pp| < 0,05` (`LIMIAR_EMPATE`), com `margem_pp = pct_lula - pct_bolsonaro`.

**Voto dividido**: `output/distritos_lula_pres_tarcio_gov_2026.csv` lista os 26 distritos em que Lula venceu para Presidente **e** Tarcísio venceu para Governador (colunas `CD_DIST`, `NM_DIST`, vencedores, `pct_lula`, `pct_bolsonaro`, `margem_pp_pres`, `pct_haddad`, `pct_tarcisio`, `margem_pp_gov`) — base da página `index_disputa.html`.

Fluxos de base (standalone):
- `Rscript run_analysis.R` — vencedor por seção (Presidente) (`output/section_winners_2026.csv`, 26.683 seções).
- `Rscript map_zonas.R` — choropleth por zona eleitoral (`output/choropleth_zonas_2026.png`).

### Armadilhas críticas de dados & encoding

1. **Formato do CSV-fonte**: `data/votacao_secao_2026_BR_71072.csv` é **delimitado por `;`** e **ISO-8859-1 / Latin-1**. Sempre ler com `data.table::fread(..., sep = ";", encoding = "Latin-1")`.
2. **Normalização de texto**: nunca passar strings Latin-1 cruas a `stringr::str_to_upper()`. Usar `iconv(x, "latin1", "UTF-8", sub = "")`, `toupper()` e `trimws()` da base R.
3. **Unicidade do local de votação**: `NR_LOCAL_VOTACAO` **não é único entre zonas eleitorais**. A chave do local é sempre `(NR_ZONA, NM_CLEAN, ADDR_CLEAN)`.
4. **Cargo, turno e votos válidos**: excluir `NR_VOTAVEL %in% c(95L, 96L)` (brancos e nulos) e filtrar `ANO_ELEICAO == 2026 & CD_MUNICIPIO == 71072 & NR_TURNO == 1`. O cargo depende da trilha: `DS_CARGO == "Governador"` (ou `CD_CARGO == 3`) no passo 2; `DS_CARGO == "Presidente"` (ou `CD_CARGO == 1`) no passo 7.
5. **Chave do distrito**: normalizar `CD_DIST` como string de 2 dígitos com zero à esquerda (`sprintf("%02d", as.numeric(CD_DIST))`) ao unir com `districts_dissolved.gpkg`.
6. **Candidatos**: para Presidente, casar totais com `grepl("LULA", toupper(NM_VOTAVEL))` e `grepl("BOLSONARO", toupper(NM_VOTAVEL))`; para Governador, usar `NM_URNA_CANDIDATO`. Metadados em `data/consulta_cand_2026.zip` (chave `SQ_CANDIDATO`).
7. **Saída em Latin-1**: `output/distritos_vencedor_presidente_2026.csv` é gravado em **Latin-1**, não UTF-8 — `read.csv()` da base R falha nele; use `data.table::fread(..., encoding = "Latin-1")`. Os CSVs do Governador são UTF-8.

### Geocodificação & invariantes espaciais

- **Endpoint Photon**: `https://photon.komoot.io/api/?q=<urlenc>&limit=1&lang=default&bbox=-46.92,-24.05,-46.28,-23.30`. Não usar `lang=pt` (não suportado). Resultados fora do bbox são descartados (motivo `fora_bbox`).
- **Rate limit & resiliência**: máx. 1,5 req/s (sleep mínimo 0,70 s; backoff de retry `1,5 * k` s). Cache escrito a cada 25 registros em `cache/geocode_cache.rds` para retomar execuções.
- **Honestidade estrita**: *nunca fabricar coordenadas/votos*. Locais não geocodificados permanecem `NA` (`metodo_geo = NA, metodo_distrito = "sem_geocode"`) e são reportados; pontos fora dos polígonos usam `sf::st_nearest_feature` apenas até 500 m com flag `metodo_distrito = "nearest"`, e um fallback final por maioria de zona eleitoral usa `metodo_distrito = "fallback_zona"`.
- **Validade topológica**: dissolução de setores com `sf_use_s2(FALSE)` → `st_make_valid()` → `st_union()` → `st_make_valid()` → `sf_use_s2(TRUE)`.

### Gates de controle de qualidade (QC)

`scripts/step5_results_qc.R` (Governador) e `scripts/step7_presidente_distritos.R` (Presidente) aplicam assertivas duras (`stopifnot`):

- **Q1 (conservação de votos)**: soma de votos válidos por distrito = referência municipal dentro de `TOL = 0.0001` (0,01%). A referência é `GATE_VALIDOS = 6136450L` no passo 5 (**Governador**) e `6553181L` no passo 7 (**Presidente**) — são números distintos, um por trilha.
- **Q2 (vencedor inequívoco)**: exatamente um vencedor por distrito; zero `NA`.
- **Q3 (faixa de %)** : share dos candidatos ∈ [0, 1] para todos os distritos.
- **Q4 (completude)**: nº de distritos cobertos = nº de distritos dissolvidos (96).
- **Q5 (só Presidente, no passo 7)**: o GeoJSON de 96 distritos (`data/tmp/distritos_sp.geojson`) deve casar com as 96 linhas agregadas.

## Restrições de ambiente

- **Sem instalação de pacotes**: `install.packages()` é proibido; usar apenas pacotes pré-instalados (`data.table`, `sf`, `ggplot2`, `jsonlite`, `dplyr`).
- **Device de mapa**: `ragg` está quebrado neste runtime; mapas e `ggsave` devem usar Cairo explicitamente (`grDevices::png(..., type = "cairo")`).
- **Baseline somente-leitura**: não modificar/remover `data/`, `run_analysis.R`, `map_zonas.R` nem `output/section_winners_2026.csv`.
- **Publicado no GitHub Pages**: apenas `.gitignore`, `.nojekyll`, `README.md`, `index.html`, `index_gov.html`, `index_pres.html`, `index_disputa.html`. `data/`, `cache/`, `output/`, `scripts/` e todos os `*.R/*.csv/*.gpkg/*.rds` ficam locais.
