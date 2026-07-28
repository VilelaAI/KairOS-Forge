# ADR-0017 — Sete perfis novos: Mobile, Modernização, Evals de IA, Analytics, Eventos/Streaming e Localização

**Status:** Aceito
**Data:** 2026-07-28

## Contexto

Consultoria de gaps pedida pelo usuário sobre o catálogo de 64 agentes, com aprovação explícita para implementar as sugestões dos dois primeiros tiers. Os critérios de corte: lacuna real (nenhuma persona é dona do tema), demanda plausível no portfólio, e a regra do ADR-0012 aplicada à própria fábrica — persona nova só contra modo de falha compreendido. O Tier 3 da consultoria (SEO técnico, UX research dedicada, desktop, base de suporte) fica **registrado como candidato para o `/evoluir`**, não implementado.

## Decisão

A partir da **v0.13.0**, a fábrica passa de 64 para **71 agentes** — **40 core em 11 times + 31 apoio em 10 squads** (21 times).

### Tier 1 — lacunas de demanda ampla

**Time core novo: Mobile (2 agentes).** Maior ausência do catálogo — Marina é frontend *web*:

| Agente | Papel | Especialidade |
|---|---|---|
| 📱 **Yasmin** (`yasmin-mobile`) | Engenheira Mobile | React Native/Flutter, navegação e estado mobile, offline-first, push, deep links, performance de app |
| 🏪 **Théo** (`theo-distribuicao`) | Especialista em Distribuição Mobile | Lojas (App Store/Play), assinatura de builds, review guidelines, release trains, rollout gradual, crash reporting |

Fronteiras: Marina (web) × Yasmin (app); Marcos (CI da aplicação) × Théo (pipeline de app tem ciclo próprio: build assinado, faixas de rollout, review externo).

**🧱 Ivan (`ivan-modernizacao`) — Engenheiro de Modernização (core, Arquitetura).** Dono da *execução* de modernização de legado: strangler fig, migração de framework/versão, decomposição incremental com rollback, dívida estrutural como programa. Consome o mapa do `/mapear-arquitetura` e será o dono natural da futura skill `/migrar` (roadmap). Fronteiras: Rafael decide *se* migra (ADR); Diego desenha o alvo; Ivan conduz o *como* incremental.

**🎯 Alice (`alice-evals`) — Especialista em Evals de IA (core, Qualidade).** Fecha o anti-padrão de gerador avaliando a si mesmo: Gabriel/Milena constroem IA, Alice quebra — eval harness com gold sets, red team de prompts (injeção, jailbreak), testes de alucinação e fundamentação, regressão de prompt como gate de CI. Fronteiras: Helena (segurança clássica) × Alice (segurança/confiabilidade de IA); Ricardo (testes de código) × Alice (evals de modelo); ela avalia inclusive o grafo da Olívia (loop de F1 do playbook ADR-0009).

### Tier 2 — fortes no perfil do portfólio

**📈 Bento (`bento-analytics`) — Analytics Engineer (core, Dados).** O meio do ciclo de dados que faltava: modelagem dimensional, marts, camada semântica (estilo dbt), métricas com definição única. Juliana move o dado bruto; Bento o modela para análise; Davi analisa em cima; Fernanda segue dona do modelo do produto.

**📨 Murilo (`murilo-eventos`) — Arquiteto de Eventos/Streaming (core, Arquitetura).** Dono da infraestrutura semântica de eventos: mensageria (filas, Kafka), event-driven, outbox, idempotência e replay em escala, contratos de evento. Diego desenha fluxos entre componentes; Murilo é dono do *transporte e das garantias* (entrega, ordem, deduplicação). Thiago segue com APIs síncronas.

**🌍 Ingrid (`apoio-ingrid-localizacao`) — Analista de Localização (apoio, squad Microcopy).** i18n/l10n: glossário multi-idioma, políticas de data/moeda/fuso/plural, processo de tradução com contexto, pseudo-localização como teste. O squad apoio-microcopy passa a ter **4 agentes** — decisão deliberada: inventar mais 2 personas para "fechar um squad de 3" seria enchimento, exatamente o que este ADR evita. Celina escreve o texto; Ingrid o faz viajar entre línguas; Ada segue com acessibilidade.

### Colisões de nome

Nenhuma nova: Yasmin, Théo, Ivan, Alice, Bento, Murilo e Ingrid são inéditos. Os pares existentes (Marcos, Helena, Elisa) seguem únicos.

## Versão

Agentes novos → bump **minor**: 0.12.0 → **0.13.0**. O roadmap aspiracional (`/migrar`, RFC, Mermaid, debate) desloca para o minor seguinte — o Ivan inclusive prepara o terreno do `/migrar`.

## Consequências

Boas: a fábrica cobre app mobile de ponta a ponta (dev + distribuição), ganha dono para os dois temas que mais geram retrabalho silencioso (legado sem estratégia e IA sem avaliador independente), completa o ciclo de dados (bruto → marts → ciência) e o de eventos, e destrava produto multi-idioma. Custos: 7 personas a mais no roteamento da Laura (mitigado: níveis de acionamento próprios e sinais no yaml); primeiro squad com 4 agentes quebra a simetria de 3 (mitigado: registrado aqui como decisão, não acidente).

## Alternativas consideradas

1. **Esticar Marina para mobile.** Rejeitado: stack, ciclo de release e modos de falha completamente distintos — o racional anti-acúmulo de sempre.
2. **Alice como apoio.** Rejeitado: evals exigem implementar harness, gold sets e gates de CI — código; apoio não codifica (ADR-0003).
3. **Squad novo de localização com 3 personas.** Rejeitado: 2 personas de enchimento só para fechar simetria.
4. **Implementar também o Tier 3.** Rejeitado (nesta rodada): sem modo de falha compreendido ainda — candidatos registrados para o `/evoluir`.
