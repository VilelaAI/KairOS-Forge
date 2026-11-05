"""Testes da pausa da faixa 3 na execução (ADR-0052).

Só stdlib. O `guardrail.py faixa3` diz, para uma chamada de ferramenta, se o efeito dela
sai do repositório de um jeito que um revert não desfaz e se a autonomia do arco está
ligada. Quem pergunta à pessoa é o mod (`hooks/pausa.ts`, testado pelo kit do Claude
Code); aqui fica a regra:

1. Precisão: o que um revert não desfaz para; ensaio, leitura e banco local passam.
2. Contexto: só com ciclo ou quadro aberto, ou com `"faixa_3": "sempre"` no projeto.
3. Saída: JSON com o cartão que a pessoa lê, evento na trajetória, sempre exit 0.
4. No Cursor (ADR-0055): a resposta no esquema dele, recusa com o cartão por padrão.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from tests.test_guardrail import Sandbox, hook

import guardrail  # noqa: E402  (o caminho vem do test_guardrail)
import telemetria  # noqa: E402

PARAM = (
    "terraform apply -auto-approve", "cd infra && terraform destroy", "tofu apply", "pulumi up --yes",
    "npx cdk deploy MyStack", "kubectl apply -f k8s/", "kubectl delete pod x",
    "kubectl rollout restart deploy/api", "helm upgrade --install api ./chart", "ansible-playbook site.yml",
    "flyctl deploy", "vercel --prod", "netlify deploy --prod --dir dist", "git push heroku main",
    "docker push ghcr.io/x/y:1", "docker compose push", "npm publish", "pnpm publish --access public",
    "cargo publish", "twine upload dist/*", "uv publish", "gh release create v1.2.0",
    "git push origin --tags", "git push origin main", "git push origin HEAD:main",
    "gh secret set API_KEY < k.txt", "vault kv put secret/app x=1", "aws s3 rm s3://b/k --recursive",
    "aws ec2 terminate-instances --instance-ids i-1", "aws s3 sync dist s3://site --delete",
    "aws s3 cp f.txt s3://b/f.txt", "gcloud run deploy api --image x", "gsutil rm gs://b/x",
    "az group delete -n rg", "doctl apps create --spec x",
    "curl https://api.stripe.com/v1/refunds -u sk_live_abc123:", "stripe refunds create --charge ch_1",
    "npx prisma migrate deploy", "supabase db push", "make deploy", "npm run deploy",
    "./scripts/deploy.sh", "RAILS_ENV=production bin/rails db:migrate",
    "export RAILS_ENV=production && bin/rails db:migrate",
    "DATABASE_URL=postgres://u:p@prod-db.acme.com/app alembic upgrade head",
    "psql -h prod-db.acme.com -U app -c 'delete from x where id=1'",
    "redis-cli -h cache.prod.acme.com FLUSHALL",
    "npm publish --dry-run && npm publish",
)
PASSA = (
    "terraform plan", "terraform init", "kubectl get pods", "kubectl apply --dry-run=client -f x",
    "helm template ./chart", "helm upgrade api ./chart --dry-run", "ansible-playbook site.yml --check",
    "npm publish --dry-run", "cargo publish --dry-run", "git push -u origin claude/feature",
    "git push origin feature/main-fix", "git -C repo status", "git push --dry-run origin main",
    "docker build -t x .", "docker compose up -d", "npm test", "npm run build", "pnpm run lint",
    "make test", "make", "ls deploy", "cat deploy/README.md", "alembic upgrade head",
    "DATABASE_URL=postgres://u:p@localhost:5432/app alembic upgrade head", "bin/rails db:migrate",
    "npx prisma migrate dev", "supabase db push --local", "psql -h localhost -c 'select 1'",
    "psql postgres://u@db:5432/app -c 'select 1'", "aws s3 ls s3://b",
    "aws configure set region us-east-1", "aws sts get-caller-identity", "gcloud components update",
    "gcloud config set project x", "az account set -s x", "gh pr create --fill", "gh release view v1",
    "echo release", "python3 scripts/ciclo.py registrar pronto SPEC-007",
    "stripe listen --forward-to localhost:3000", "git commit -m 'deploy docs'", "vercel", "vercel dev",
)


class Precisao(unittest.TestCase):
    def test_o_que_um_revert_nao_desfaz_para(self) -> None:
        for comando in PARAM:
            with self.subTest(comando):
                self.assertTrue(guardrail.efeito_irreversivel(comando))

    def test_ensaio_leitura_e_banco_local_passam(self) -> None:
        for comando in PASSA:
            with self.subTest(comando):
                self.assertIsNone(guardrail.efeito_irreversivel(comando))

    def test_o_efeito_diz_o_que_acontece(self) -> None:
        self.assertEqual(guardrail.efeito_irreversivel("terraform apply"), "aplica ou destrói infraestrutura")
        self.assertEqual(guardrail.efeito_irreversivel("psql -h prod-db.acme.com -c 'select 1'"),
                         "conecta a um banco fora da máquina (prod-db.acme.com)")
        self.assertEqual(guardrail.efeito_irreversivel("RAILS_ENV=production rake db:migrate"),
                         "aplica migration num banco de produção ou remoto")

    def test_mcp_pelo_nome_e_as_outras_ferramentas_nao(self) -> None:
        self.assertEqual(guardrail.efeito_da_ferramenta("mcp__supabase__apply_migration", {}),
                         "chama `apply_migration` num serviço de fora")
        for nome in ("mcp__github__merge_pull_request", "mcp__vercel__deploy_project",
                     "mcp__stripe__create_refund", "mcp__slack__send_message"):
            with self.subTest(nome):
                self.assertTrue(guardrail.efeito_da_ferramenta(nome, {}))
        for nome, entrada in (("mcp__github__list_pull_requests", {}), ("mcp__supabase__list_tables", {}),
                              ("Write", {"file_path": "deploy.sh"}), ("Read", {"file_path": ".env"})):
            with self.subTest(nome):
                self.assertIsNone(guardrail.efeito_da_ferramenta(nome, entrada))


class ComEstado(Sandbox):
    """Ciclo, quadro e trajetória num projeto de verdade; sem testes próprios."""

    def estado(self, pasta: str, nome: str, dados: dict) -> None:
        alvo = self.raiz / ".agents" / pasta / f"{nome}.json"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(dados), encoding="utf-8")

    def eventos(self) -> list[dict]:
        pasta = self.raiz / ".agents" / "execucoes"
        return [json.loads(l) for p in sorted(pasta.glob("*.jsonl"))
                for l in p.read_text(encoding="utf-8").splitlines()] if pasta.is_dir() else []


class Contexto(ComEstado):
    def faixa3(self, comando: str = "terraform apply", ferramenta: str = "Bash") -> tuple[int, dict]:
        entrada = {"command": comando} if ferramenta == "Bash" else {"pull_number": 51}
        codigo, out, _ = hook("faixa3", {"cwd": str(self.raiz), "tool_name": ferramenta,
                                         "tool_input": entrada})
        return codigo, json.loads(out)

    def test_sem_arco_nao_pausa(self) -> None:
        self.assertEqual(self.faixa3(), (0, {"pausa": False}))
        self.assertEqual(self.eventos(), [])

    def test_ciclo_aberto_pausa_com_o_cartao_e_o_evento(self) -> None:
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "construindo"})
        codigo, r = self.faixa3("terraform apply -auto-approve")
        self.assertEqual(codigo, 0)
        self.assertTrue(r["pausa"])
        self.assertEqual(r["spec"], "SPEC-007")
        self.assertIn("aplica ou destrói infraestrutura", r["razao"])
        self.assertIn("o ciclo SPEC-007 está em `construindo`", r["razao"])
        self.assertIn('ciclo.py escalar SPEC-007 --motivo "faixa 3: aplica ou destrói infraestrutura"',
                      r["razao"])
        [evento] = self.eventos()
        self.assertEqual((evento["tipo"], evento["classe"], evento["spec"]), ("pausa", "faixa3", "SPEC-007"))
        self.assertEqual(evento["alvo"], "terraform apply -auto-approve")

    def test_no_arco_o_que_nao_e_irreversivel_passa_sem_evento(self) -> None:
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "validando"})
        self.assertEqual(self.faixa3("npm test"), (0, {"pausa": False}))
        self.assertEqual(self.eventos(), [])

    def test_ciclo_encerrado_ou_escalado_nao_pausa(self) -> None:
        for estado in ("encerrado", "escalado"):
            with self.subTest(estado):
                self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": estado})
                self.assertFalse(self.faixa3()[1]["pausa"])

    def test_quadro_em_andamento_pausa_e_encerrado_nao(self) -> None:
        self.estado("quadro", "forge-007", {"slug": "forge-007", "encerrado_em": None})
        _, r = self.faixa3("npm publish")
        self.assertTrue(r["pausa"])
        self.assertIn("a mobilização `forge-007` está em andamento", r["razao"])
        self.assertIn("o quadro bloqueado com o motivo", r["razao"])
        self.estado("quadro", "forge-007", {"slug": "forge-007", "encerrado_em": "2026-11-05T10:00:00Z"})
        self.assertFalse(self.faixa3("npm publish")[1]["pausa"])

    def test_quadro_sem_slug_usa_o_nome_do_arquivo(self) -> None:
        self.estado("quadro", "forge-sem-slug", {"encerrado_em": None})
        self.assertIn("a mobilização `forge-sem-slug`", self.faixa3("npm publish")[1]["razao"])

    def test_vale_o_cwd_do_payload_nao_o_do_processo(self) -> None:
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "construindo"})
        with tempfile.TemporaryDirectory() as outro:
            os.chdir(outro)
            try:
                self.assertTrue(self.faixa3()[1]["pausa"])
            finally:
                os.chdir(self.raiz)

    def test_sempre_no_guardrails_json_estende_para_fora_do_arco(self) -> None:
        (self.raiz / ".agents").mkdir(exist_ok=True)
        (self.raiz / ".agents" / "guardrails.json").write_text('{"faixa_3": "sempre"}', encoding="utf-8")
        _, r = self.faixa3("kubectl apply -f k8s/")
        self.assertTrue(r["pausa"])
        self.assertIsNone(r["spec"])
        self.assertIn("sempre (`.agents/guardrails.json`)", r["razao"])

    def test_mcp_no_arco_pausa(self) -> None:
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "construindo"})
        _, r = self.faixa3(ferramenta="mcp__github__merge_pull_request")
        self.assertTrue(r["pausa"])
        self.assertEqual(self.eventos()[0]["alvo"], "mcp__github__merge_pull_request")

    def test_payload_ilegivel_falha_aberto_sem_saida(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["guardrail.py", "faixa3"]), \
                mock.patch.object(sys, "stdin", io.StringIO("{ isto não é json")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(guardrail.main(), 0)
        self.assertEqual(out.getvalue(), "")              # sem JSON, o mod segue sem pausa
        self.assertIn("falhou e deixou passar", err.getvalue())


    def test_numa_subpasta_do_projeto_tambem_pausa(self) -> None:
        # `cd infra && terraform apply` deixa o `cwd` na subpasta; o ciclo mora na raiz.
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "construindo"})
        (self.raiz / "infra").mkdir()
        codigo, out, _ = hook("faixa3", {"cwd": str(self.raiz / "infra"), "tool_name": "Bash",
                                         "tool_input": {"command": "terraform apply"}})
        self.assertTrue(json.loads(out)["pausa"])
        self.assertEqual(self.eventos()[0]["spec"], "SPEC-007")


    def test_sem_o_execucao_ao_lado_a_raiz_e_o_proprio_cwd(self) -> None:
        # Cópia avulsa do guardrail, sem o `execucao.py`: o `cwd` vale como está.
        with mock.patch.dict(sys.modules, {"execucao": None}):
            self.assertEqual(guardrail.raiz_da_chamada({"cwd": str(self.raiz / "infra")}),
                             self.raiz / "infra")
            self.assertEqual(guardrail.raiz_da_chamada({}), guardrail.Path("."))


class NoCursor(ComEstado):
    """No Cursor (ADR-0055), o `ask` de um hook não chega a uma pessoa no Auto-review: a
    pausa nasce como recusa com o cartão, e a resposta sai sempre no esquema dele."""

    def cursor(self, evento: str = "beforeShellExecution", **campos) -> tuple[int, dict]:
        payload = {"conversation_id": "c1", "generation_id": "g1", "hook_event_name": evento,
                   "workspace_roots": [str(self.raiz)], **campos}
        codigo, out, _ = hook("faixa3", payload)
        return codigo, json.loads(out)

    def mcp(self, servidor: str, ferramenta: str, entrada: str = '{"pull_number": 51}',
            **extra) -> tuple[int, dict]:
        return self.cursor("beforeMCPExecution", tool_name=ferramenta, tool_input=entrada,
                           mcp_server_name=servidor, **extra)

    def no_arco(self) -> None:
        self.estado("ciclo", "SPEC-007", {"spec": "SPEC-007", "estado": "construindo"})

    def test_fora_do_arco_responde_allow_no_esquema_do_cursor(self) -> None:
        # Resposta fora do esquema bloqueia a ação no Cursor: `{"pausa": false}` travaria tudo.
        self.assertEqual(self.cursor(command="terraform apply", cwd=str(self.raiz)),
                         (0, {"permission": "allow"}))
        self.assertEqual(self.eventos(), [])

    def test_no_arco_o_irreversivel_e_recusado_com_o_cartao(self) -> None:
        self.no_arco()
        codigo, r = self.cursor(command="npm publish", cwd=str(self.raiz))
        self.assertEqual((codigo, r["permission"]), (0, "deny"))
        self.assertEqual(r["user_message"], "kairos-forge recusou (faixa 3): publica um pacote")
        for trecho in ("publica um pacote", "o ciclo SPEC-007 está em `construindo`", "ADR-0055",
                       "no Auto-review, o classificador a libera", "Não contorne",
                       'ciclo.py escalar SPEC-007 --motivo "faixa 3: publica um pacote"',
                       '"faixa_3_cursor": "perguntar"'):
            self.assertIn(trecho, r["agent_message"])
        self.assertNotIn("Permita só se", r["agent_message"])
        [evento] = self.eventos()
        self.assertEqual((evento["decisao"], evento["cli"], evento["alvo"]),
                         ("deny", "cursor", "npm publish"))

    def test_perguntar_no_guardrails_json_vira_ask_para_a_pessoa(self) -> None:
        self.no_arco()
        (self.raiz / ".agents" / "guardrails.json").write_text('{"faixa_3_cursor": "perguntar"}',
                                                               encoding="utf-8")
        _, r = self.cursor(command="terraform apply", cwd=str(self.raiz))
        self.assertEqual(r["permission"], "ask")
        self.assertIn("Permita só se você conferiu o alvo", r["user_message"])
        self.assertEqual(r["user_message"], r["agent_message"])
        self.assertEqual(self.eventos()[0]["decisao"], "ask")

    def test_o_que_passa_no_arco_responde_allow(self) -> None:
        self.no_arco()
        self.assertEqual(self.cursor(command="terraform plan", cwd=str(self.raiz))[1],
                         {"permission": "allow"})

    def test_mcp_pelo_nome_com_tool_input_em_texto(self) -> None:
        self.no_arco()
        _, r = self.mcp("github", "merge_pull_request")
        self.assertEqual(r["permission"], "deny")
        self.assertIn("chama `merge_pull_request` num serviço de fora", r["agent_message"])
        self.assertEqual(self.eventos()[0]["alvo"], "mcp__github__merge_pull_request")
        self.assertEqual(self.mcp("github", "get_pull_request")[1], {"permission": "allow"})

    def test_a_linha_que_lanca_o_servidor_mcp_nao_e_o_comando(self) -> None:
        # Servidor stdio manda `command` com a linha que o lança: não é shell do agente.
        self.no_arco()
        _, r = self.mcp("deploys", "list_items", command="npx -y deploy-mcp --prod")
        self.assertEqual(r, {"permission": "allow"})

    def test_tool_input_ilegivel_ou_que_nao_e_objeto_vira_vazio(self) -> None:
        for entrada in ("{ não é json", "[1, 2]", "null"):
            with self.subTest(entrada):
                p = guardrail.normalizar_payload({"conversation_id": "c1", "tool_input": entrada,
                                                  "tool_name": "execute_sql",
                                                  "mcp_server_name": "supabase"})
                self.assertEqual((p["tool_input"], p["tool_name"]),
                                 ({}, "mcp__supabase__execute_sql"))

    def test_mcp_sem_servidor_ainda_e_julgado_pelo_nome(self) -> None:
        p = guardrail.normalizar_payload({"conversation_id": "c1", "tool_input": "{}",
                                          "tool_name": "deploy"})
        self.assertEqual(p["tool_name"], "mcp__desconhecido__deploy")

    def test_payload_do_claude_code_nao_e_tocado(self) -> None:
        payload = {"session_id": "s1", "cwd": "/x", "tool_name": "Bash",
                   "tool_input": {"command": "ls"}}
        self.assertIs(guardrail.normalizar_payload(payload), payload)
        com_conversa = {"conversation_id": "c1", "tool_input": {"command": "ls"}}
        self.assertIs(guardrail.normalizar_payload(com_conversa), com_conversa)

    def test_shell_do_cursor_vira_bash(self) -> None:
        p = guardrail.normalizar_payload({"conversation_id": "c1", "command": "ls",
                                          "workspace_roots": ["/w"]})
        self.assertEqual((p["tool_name"], p["tool_input"], p["cwd"]),
                         ("Bash", {"command": "ls"}, "/w"))
        leitura = guardrail.normalizar_payload({"conversation_id": "c1", "file_path": "/w/a"})
        self.assertEqual(leitura["tool_name"], "")

    def test_numa_subpasta_o_cwd_do_cursor_acha_o_ciclo(self) -> None:
        self.no_arco()
        (self.raiz / "infra").mkdir()
        _, r = self.cursor(command="terraform apply", cwd=str(self.raiz / "infra"))
        self.assertEqual(r["permission"], "deny")

    def test_o_sync_liga_a_pausa_no_shell_e_no_mcp(self) -> None:
        from tests.test_sync import carregar_sync
        hooks = carregar_sync().montar_hooks_cursor()["hooks"]
        faixa3 = {"command": "python3 .cursor/scripts/guardrail.py faixa3"}
        self.assertEqual(hooks["beforeShellExecution"][0],
                         {"command": "python3 .cursor/scripts/guardrail.py comando"})
        self.assertIn(faixa3, hooks["beforeShellExecution"])
        self.assertEqual(hooks["beforeMCPExecution"], [faixa3])


class NaTrajetoria(unittest.TestCase):
    def test_o_resumo_conta_as_pausas_por_efeito(self) -> None:
        eventos = [{"sessao": "s1", "tipo": "pausa", "regra": "publica um pacote"},
                   {"sessao": "s1", "tipo": "pausa", "regra": "aplica ou destrói infraestrutura"},
                   {"sessao": "s2", "tipo": "pausa", "regra": "publica um pacote"},
                   {"sessao": "s2", "tipo": "recusa", "classe": "comando", "modo": "bloqueio"}]
        m = telemetria.metricas(telemetria.por_sessao(eventos))
        self.assertEqual(m["pausas_faixa3"], 3)
        self.assertEqual(m["pausas_por_efeito"], {"publica um pacote": 2,
                                                  "aplica ou destrói infraestrutura": 1})
        self.assertEqual(m["recusas_total"], 1)            # pausa não é recusa
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            telemetria.imprimir_resumo(m, 7)
        self.assertIn("Pausas da faixa 3:    3 — publica um pacote (2), aplica ou destrói "
                      "infraestrutura (1)", out.getvalue())

    def test_sem_pausa_a_linha_nao_aparece(self) -> None:
        m = telemetria.metricas(telemetria.por_sessao([{"sessao": "s1", "tipo": "prompt"}]))
        self.assertEqual((m["pausas_faixa3"], m["pausas_por_efeito"]), (0, {}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            telemetria.imprimir_resumo(m, 7)
        self.assertNotIn("Pausas", out.getvalue())
        self.assertIn("Rodadas de correção:  0\n  Tokens:", out.getvalue())   # nada entre as duas

    def test_skills_contadas_pela_mesma_conta(self) -> None:
        eventos = [{"sessao": "s1", "tipo": "prompt", "skill": "entregar"},
                   {"sessao": "s1", "tipo": "prompt", "skill": "validar"},
                   {"sessao": "s2", "tipo": "prompt", "skill": "entregar"}]
        m = telemetria.metricas(telemetria.por_sessao(eventos))
        self.assertEqual(m["skills_usadas"], {"entregar": 2, "validar": 1})


if __name__ == "__main__":
    unittest.main()
