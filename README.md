# Brasileirão: título e rebaixamento

Página estática com a classificação da Série A e as chances de título, vaga direta na
Libertadores e rebaixamento, recalculadas automaticamente por simulação Monte Carlo.

Mesma arquitetura do SportGuia: **GitHub Actions (cron) → Python/httpx → JSON → Astro 5 → Cloudflare Pages**.

```
football-data.org ──► ingest/ (Python) ──► src/data/*.json ──► Astro build ──► Cloudflare Pages
                       partidas, modelo       snapshot +           HTML estático     /version.json
                       e 20 mil simulações    histórico por rodada                   avisa build novo
```

## Estrutura

```
ingest/
  config.py      regulamento (vagas, rebaixados) e parâmetros do modelo
  client.py      chamada única à API (com retry e respeito ao limite de 10 req/min)
  models.py      tipos de domínio e parsing do payload
  table.py       classificação calculada a partir das partidas
  model.py       forças de ataque/defesa (Poisson ponderado por recência + encolhimento)
  simulate.py    Monte Carlo vetorizado em NumPy
  run.py         orquestra e grava src/data/brasileirao.json e history.json
  sample.py      campeonato fictício para desenvolver sem token
src/
  components/    Hero, TitleRace, ProbBars, StandingsTable, PositionHeatmap, NextMatches, Methodology
  pages/         index.astro e version.json.ts
  data/          JSON gerado (versionado pelo workflow)
tests/           pytest do pipeline
.github/workflows/update.yml
```

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
npm ci

# dados fictícios (sem token)
npm run data:sample

# ou dados reais
export FOOTBALL_DATA_TOKEN=seu_token
npm run data

npm run dev        # http://localhost:4321
pytest -q          # testes do modelo
npm run check      # tipos do Astro
```

## Publicar

1. Crie um token gratuito em <https://www.football-data.org/client/register> (o plano free inclui a competição `BSA`).
2. Crie o projeto no Cloudflare Pages (Direct Upload) com o nome `brasileirao-probabilidades`.
3. No GitHub, em **Settings → Secrets and variables → Actions**:
   - Secrets: `FOOTBALL_DATA_TOKEN`, `CLOUDFLARE_API_TOKEN` (permissão *Cloudflare Pages: Edit*), `CLOUDFLARE_ACCOUNT_ID`
   - Variables (opcionais): `SEASON` (padrão 2026), `CF_PAGES_PROJECT`
4. Rode o workflow **Atualizar dados e publicar** manualmente uma vez. Depois ele roda a cada 2 horas.

O primeiro run real substitui os dados de exemplo e zera o histórico fictício.
O histórico guarda um ponto por rodada (o run mais recente da rodada prevalece), e é daí que sai o gráfico da corrida pelo título.

A página consulta `/version.json` a cada 5 minutos e quando a aba volta ao foco. Se houver build novo, mostra “Há dados novos · Recarregar”.

## Modelo

- λ do mandante = μ_casa · ataque[mandante] · defesa[visitante] (análogo para o visitante).
- Forças estimadas por ajuste iterativo da verossimilhança de Poisson. O peso de cada jogo cai pela metade a cada 12 rodadas, e há encolhimento equivalente a 6 jogos na média da liga.
- Desempate: pontos, vitórias, saldo, gols pró e sorteio. Confronto direto e cartões ficam de fora.
- Ajustes de regulamento (vagas diretas, número de rebaixados) ficam em `ingest/config.py`.

Limitações: o modelo não vê desfalques, troca de técnico nem a motivação de times sem objetivo. Jogos adiados entram como pendentes e são simulados normalmente.
