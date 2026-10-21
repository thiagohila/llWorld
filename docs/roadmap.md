# Roadmap — estado atual e próximas etapas

Atualizado em 2026-10-21. O *quê* está em `../llWorld-visao-produto.md`; ideias de design (não aprovadas) em `rascunhos/worldbox-ai-design.md`; decisões pendentes em `pendencias/projeto.md`.

## Estado atual

### O jogo — fork `worldbox/` em `6dc41f1` (funcionando)

Roda como veio do `ryfcx/worldbox`, com melhorias pontuais — nenhuma regra de simulação mudou (md5 de regressão idêntico desde o início):

| Área | Situação | Commit |
|---|---|---|
| Interface | HUD de jogo, abas, log com filtros, minimapa, atalhos; poderes com efeito, aviso e log | `b10f9fb` |
| Arte | spritesheets do Claude Design (pessoas, overlays, prédios, terreno, props) com troca de cor por tribo; fallback gerado | `6804118` |
| Performance | −27–33% de custo por dia; velocidades viraram taxas reais | `bfe84cd` |
| IA das tribos | fontes grátis por `.env` (Gemini testado), mente offline `mock`, controle de custo, backoff, contadores no HUD | `d6472e1` |
| Correções | Smite matava 0 de 14 (agora mata), narrador só com DeepSeek, política `{}` | `d6472e1` |

Ainda em aberto no jogo: segurança do servidor local (CSRF, DNS rebinding), determinismo com duas chaves, sem suíte de testes — ver `pendencias/jogo.md`.

### O projeto — repo `llWorld`

- Docs de referência do fork (`docs/worldbox/01..08`), ambiente e versões (`ambiente.md`), checklists, agentes `worldbox-guide` e `sim-runner`.
- `.venv` com Python 3.14; remotes: `thiagohila/llWorld` e `thiagohila/worldbox` (push para o upstream bloqueado).
- `worldbox-ai/` **ainda não existe** — é a próxima fase.

## Camadas e interfaces

```
llWorld/
  worldbox/      fork — regras do mundo, simulação, mapa ao vivo, mentes das tribos
  worldbox-ai/   nosso — Arthur, conselheiro, chat, memória, decisões de alto nível
```

**Regra:** `worldbox-ai` usa o jogo só pelas interfaces abaixo; `worldbox` nunca importa `worldbox-ai`. Mudança no fork só quando não houver interface — e então mínima, genérica e commitada no submódulo (decisão a fechar em `pendencias/projeto.md`).

### Contrato: o que o `worldbox-ai` usa do jogo

| Para quê | Interface no fork | Status |
|---|---|---|
| Criar e rodar o mundo | `SimulationEngine(config, seed)`, `step()`; `SimulationRunner` (`lock`, `start`, `pause`, `set_delay`) | **pronto** [código] |
| Mapa ao vivo junto | `cli.webview.LiveServer(engine, runner)` no mesmo processo | **pronto** [código] |
| Ler o estado | `engine.groups` / `settlements` / `diplomacy` / `agents` / `chronicle`, sempre sob `runner.lock`; ou `GET /state` | **pronto** [código] |
| Observar acontecimentos | `engine.events.subscribe(fn)` — recebe todos os tipos, inclusive os poderes (`SYSTEM`) que o feed HTTP omite | **pronto** [código] |
| Decidir pela tribo do Arthur | subclasse de `ai.minds.MindDirector` atribuída a `engine.minds`; validar com `parse_policy` / `TribePolicy` | **pronto** [código] |
| Chamar a LLM | `ai.client.chat()` com as fontes do `.env` (DeepSeek, OpenAI, compatível com OpenAI, `mock`); `ChatResult` traz `status`, `fatal`, tokens | **pronto** [código] |
| Controlar custo | `MindDirector` já limita as tribos; o loop do Arthur precisa do mesmo cuidado (teto por minuto compartilhado) | **a fazer** no `worldbox-ai` |
| Fundar o reino | mesmo caminho do `/found` (`groups.create` + agentes) — hoje dentro de `LiveState.found_civ` | **a extrair** (função reutilizável) ou duplicar no `worldbox-ai` |
| Arthur fixo como chefe | `society.culture.choose_chieftain` chamado via módulo → patch por fora; ou gancho no fork | **decisão** |
| Arthur não morrer / sucessão | `Agent.lifespan_days` e mortes em `engine._process_deaths` | **decisão** |
| Reino não se dividir/dissolver | `GroupRegistry.try_split` / `find_unviable` → patch ou gancho | **decisão** |
| Chat (HTTP) | servidor próprio do `worldbox-ai`, outra porta, mesmo processo, com `Host` validado, token e POST | **a fazer** |
| UI do chat | página própria do `worldbox-ai` ou painel no `live.html` | **decisão** |
| Importar o fork | `sys.path` num único ponto do entrypoint (fork não é instalável) | **decisão** (proposta v1) |

## Próximas etapas (proposta)

Cada etapa é pequena, testável offline com a mente `mock` e não muda a regressão do fork. Começa só quando o Thiago aprovar.

| # | Etapa | Pronto quando |
|---|---|---|
| 0 | **Decisões de produto** — origem do reino, morte/sucessão, divisão, ritmo do mundo na conversa, idioma, modelo (`pendencias/projeto.md`) | decisões registradas |
| 1 | **Esqueleto do `worldbox-ai/`** — entrypoint que monta engine + runner + mapa do fork; ponte de import; config; pasta de testes com o harness offline (API simulada) | `worldbox-ai` abre o mapa como hoje; testes offline passam; md5 do fork intacto |
| 2 | **Reino do Arthur** — fundar o reino no início, Arthur chefe fixo, persona aplicada aos traços dele | Arthur aparece como chefe e continua chefe por N anos de jogo |
| 3 | **Mente do Arthur** — a tribo dele decidida por um loop próprio (persona + contexto), demais tribos como hoje | políticas com justificativa, com `mock` e com Gemini |
| 4 | **Chat do conselheiro** — rota + UI; conselho vira item de agenda do próximo conselho | Arthur responde em personagem; pode recusar; o chat não muda o mundo diretamente |
| 5 | **Memória, confiança, conhecimento limitado** | conselhos e consequências lembrados; Arthur não sabe o que não viu |
| 6 | **Avaliação** pelos critérios da visão §11 | cenários roteirizados passam |

Design detalhado das etapas 3–5 (camadas de contexto, contratos de saída, confiança): `rascunhos/worldbox-ai-design.md` — revisar antes da etapa 3.

## Cuidados

- **Orçamento de LLM:** o plano grátis tem limite por minuto e por dia, e o Gemini oscila (503). Desenvolver com `mock`; com IA real, Arthur e tribos dividem o mesmo teto — talvez reduzir `max_minds` quando Arthur estiver ativo.
- **Segurança:** o chat não pode herdar os problemas do servidor do fork (CSRF, DNS rebinding).
- **Testes:** cenários por seed com `mock` são reprodutíveis; com LLM real, não.
