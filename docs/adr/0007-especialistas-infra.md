# ADR-0007 — Especialistas de infraestrutura no squad Plataforma (IaC, Kubernetes, GitOps, Redes)

**Status:** Aceito
**Data:** 2026-07-03

## Contexto

O squad **Plataforma** cobria, até a v0.6.x, quatro papéis: Marcos (DevOps/SRE — Docker, CI/CD, secrets, rollback, SLOs), Elisa (Cloud Architect — provedor, FinOps, serverless), Helena (Security) e Renata (Observability). Isso dá conta do build/deploy e da decisão de nuvem, mas deixa três lacunas técnicas que aparecem em qualquer projeto que sobe além de um PaaS simples:

1. **Infra as Code.** Ninguém era dono de Terraform/OpenTofu — módulos reutilizáveis, state remoto, `plan`/`apply` revisado, detecção de drift. Elisa *decide* provedor e custo; Marcos faz CI/CD; mas a infra em si não era versionada por um especialista.
2. **Orquestração de containers.** Marcos builda a imagem, mas Kubernetes/EKS, Helm, autoscaling (HPA/Karpenter), Ingress/Load Balancer e limites de recurso não tinham dono.
3. **Entrega contínua declarativa (GitOps).** O CI/CD do Marcos entrega, mas de forma imperativa. ArgoCD/Kustomize, sync Git→cluster e progressive delivery (canary/blue-green) não eram cobertos.
4. **Rede e borda.** VPC, subnets, DNS, Application Load Balancer, CDN, WAF e TLS caíam parcialmente na Elisa, sem foco em superfície de exposição e topologia.

A referência foi o workshop **DevOps na Nuvem** (AWS + Terraform + Kubernetes, da arquitetura ao deploy contínuo — EKS do zero, Load Balancing, GitHub Actions, GitOps com ArgoCD e Kustomize, Karpenter). O usuário pediu explicitamente para inspirar o squad de infra nesse conteúdo.

## Decisão

A partir da v0.7.0, o squad Plataforma ganha **quatro agentes core** (a fábrica passa de 45 para 49 agentes; core de 24 para 28):

- **🏗️ Igor — Infra as Code** (`igor-iac`): Terraform, módulos, state/backend remoto, `plan`/`apply` revisado, drift, workspaces. Nunca aplica em produção sem plan revisado + aprovação humana.
- **☸️ Kaique — Kubernetes / Platform Engineer** (`kaique-kubernetes`): Kubernetes/EKS, Helm, autoscaling (HPA/Karpenter), Ingress/Load Balancer, health checks, requests/limits. Não faz `kubectl apply` manual em produção.
- **🔁 Gael — GitOps / Continuous Delivery** (`gael-gitops`): ArgoCD, Kustomize, sync Git→cluster, progressive delivery. Complementa (não substitui) o CI/CD do Marcos — ele builda/testa, Gael entrega declarativamente.
- **🌐 Nina — Networking / Edge** (`nina-redes`): VPC, subnets, DNS, Application Load Balancer, CDN (CloudFront), WAF, TLS, security groups. Desenha a rede; o provisionamento vira código com o Igor.

Todos são **core** (allow-list `Read, Write, Edit, Grep, Glob, Bash`), porque produzem artefatos reais (`.tf`, manifests YAML, charts) — diferente dos squads de apoio, que só geram texto. Seguem o formato lean dos demais agentes core (Marcos/Elisa/Renata) e o padrão de fronteiras: cada um aponta o colega certo fora do seu escopo.

O `templates/squad-fabrica.yaml` ganha quatro níveis de acionamento novos (`infra_como_codigo`, `orquestracao_containers`, `entrega_continua`, `rede_e_borda`), além do `deploy_infra` já existente.

### Versão

Adicionar agente exige bump **minor** (convenção obrigatória do CLAUDE.md), logo v0.6.2 → **v0.7.0**. O roadmap do ADR-0006 havia esboçado `/migrar`, modo RFC e `/revisar web` para o slot 0.7.0; essas skills passam para um minor subsequente. Bump de agentes tem precedência de numeração sobre o roadmap de skills, que é aspiracional.

## Consequências

Boas:

- Projetos que usam IaC, Kubernetes e GitOps passam a ter donos explícitos, com fronteiras claras entre si e com Marcos/Elisa/Helena/Renata.
- A fábrica cobre o ciclo completo de cloud-native (provisionar → orquestrar → entregar → expor) sem misturar responsabilidades num único "DevOps faz-tudo".
- Segue a linha lite/MIT: são papéis técnicos genéricos, sem nada regulatório — não colidem com o kairos-ai.

Custos:

- Mais quatro personas para o usuário conhecer. Mitigação: os `sinais_ativacao` e a coordenação da Laura já roteiam por contexto; as descrições deixam claro quem faz o quê.
- Sobreposição de fronteira entre Marcos (CI/CD) e Gael (CD/GitOps), e entre Elisa (decisão de rede/custo) e Nina/Igor (execução). Mitigada nos próprios prompts, que declaram a divisão.

## Alternativas consideradas

1. **Criar um squad de apoio de infra (só texto).** Rejeitado: IaC/K8s/GitOps geram arquivos reais (`.tf`, YAML). Apoio nunca codifica — não caberia.
2. **Empilhar tudo no Marcos (um DevOps faz-tudo).** Rejeitado: viola a granularidade dos demais times e torna o agente genérico demais para ser útil.
3. **Adicionar só o Igor (Terraform), que é o núcleo do workshop.** Rejeitado a pedido do usuário, que optou pelos quatro para cobertura completa cloud-native.
