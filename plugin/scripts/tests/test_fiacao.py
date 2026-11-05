"""Testes da fiação do Claude Code no piso do guardrail (emenda ao ADR-0042).

Só stdlib. A fiação é o que um `.claude/settings*.json` liga fora das ferramentas, e por
isso fora do guardrail: os hooks, o `disableAllHooks` que desliga os de plugin (este
guardrail incluído), os plugins e marketplaces (um plugin com mod pode responder no lugar
de um hook) e os comandos de status. O teste que originou a emenda, num Claude Code de
verdade, mostrou que uma linha `"disableAllHooks": true` no settings do projeto apaga
todos os hooks da fábrica sem aviso, e que `extraKnownMarketplaces` + `enabledPlugins`
carregam um mod escrito no próprio repositório numa pasta confiável.

Três coisas:

1. Write e Edit são comparados pelo arquivo que resultaria, em todas as chaves de
   fiação; permissões e variáveis continuam livres, e ausente, vazio e `false` contam igual.
2. Vale para qualquer `.claude/settings*.json`: do projeto, local e do usuário.
3. Pelo shell, escrever num arquivo de fiação bloqueia; ler e copiar para fora passa.

Os dois são piso: nem `liberados` nem `modos` afrouxam.

Rode: python3 -m unittest discover -s scripts/tests -t scripts -v
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.test_guardrail import Sandbox, hook

import guardrail  # noqa: E402  (o caminho vem do test_guardrail)

BASE = {"permissions": {"allow": ["Bash(npm test)"]}, "env": {"NODE_ENV": "test"}}
VALOR = {
    "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}]},
    "disableAllHooks": True,
    "enabledPlugins": {"sonda@x": True},
    "extraKnownMarketplaces": {"x": {"source": {"source": "directory", "path": "./.x"}}},
    "additionalMarketplaces": {"x": {"source": {"source": "directory", "path": "./.x"}}},
    "statusLine": {"type": "command", "command": "python3 -c 'print(1)'"},
    "subagentStatusLine": {"type": "command", "command": "true"},
    "fileSuggestion": {"type": "command", "command": "true"},
    "syncClaudeAiPlugins": True,
}


class FiacaoNoSettings(Sandbox):
    def settings(self, conteudo: dict, rel: str = ".claude/settings.json") -> Path:
        alvo = self.raiz / rel
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(json.dumps(conteudo, indent=2), encoding="utf-8")
        return alvo

    def escrita(self, alvo: Path | str, entrada: dict) -> tuple[int, str]:
        codigo, _, err = hook("escrita", {"session_id": "s1", "cwd": str(self.raiz),
                                          "tool_input": {"file_path": str(alvo), **entrada}})
        return codigo, err

    def test_cada_chave_de_fiacao_bloqueia_e_aparece_no_motivo(self) -> None:
        self.assertEqual(set(VALOR), set(guardrail.CHAVES_FIACAO))
        alvo = self.settings(BASE)
        for chave, valor in VALOR.items():
            with self.subTest(chave):
                codigo, err = self.escrita(alvo, {"content": json.dumps({**BASE, chave: valor})})
                self.assertEqual(codigo, 2)
                self.assertIn(f"`{chave}`", err)

    def test_disable_all_hooks_por_edit_mesmo_com_h_maiusculo(self) -> None:
        alvo = self.settings(BASE)
        codigo, err = self.escrita(alvo, {"old_string": '"permissions"',
                                          "new_string": '"disableAllHooks": true,\n  "permissions"'})
        self.assertEqual(codigo, 2)
        self.assertIn("`disableAllHooks`", err)

    def test_permissoes_e_variaveis_continuam_livres(self) -> None:
        alvo = self.settings({**BASE, "enabledPlugins": {"kairos-forge@kairos-forge": True}})
        mais = {**BASE, "permissions": {"allow": ["Bash(npm test)", "Bash(npm run lint)"]},
                "enabledPlugins": {"kairos-forge@kairos-forge": True}}
        self.assertEqual(self.escrita(alvo, {"content": json.dumps(mais)})[0], 0)
        self.assertEqual(self.escrita(alvo, {"old_string": '"NODE_ENV": "test"',
                                             "new_string": '"NODE_ENV": "ci"'})[0], 0)

    def test_ausente_vazio_e_false_contam_igual(self) -> None:
        alvo = self.settings({**BASE, "enabledPlugins": {}})
        self.assertEqual(self.escrita(alvo, {"content": json.dumps(
            {**BASE, "disableAllHooks": False, "hooks": {}})})[0], 0)

    def test_tirar_a_fabrica_dos_plugins_bloqueia(self) -> None:
        alvo = self.settings({**BASE, "enabledPlugins": {"kairos-forge@kairos-forge": True}})
        self.assertEqual(self.escrita(alvo, {"content": json.dumps(BASE)})[0], 2)
        self.assertEqual(self.escrita(alvo, {
            "old_string": '"kairos-forge@kairos-forge": true',
            "new_string": '"kairos-forge@kairos-forge": false'})[0], 2)

    def test_edit_com_replace_all_compara_o_arquivo_inteiro(self) -> None:
        alvo = self.settings({**BASE, "statusLine": {"type": "command", "command": "true"}})
        codigo, err = self.escrita(alvo, {"old_string": '"true"', "new_string": '"curl x"',
                                          "replace_all": True})
        self.assertEqual(codigo, 2)
        self.assertIn("`statusLine`", err)

    def test_edit_que_nao_se_aplica_ou_quebra_o_json_cai_no_trecho(self) -> None:
        alvo = self.settings(BASE)
        self.assertEqual(self.escrita(alvo, {"old_string": '"naoexiste"',
                                             "new_string": '"enabledPlugins": {}'})[0], 2)
        self.assertEqual(self.escrita(alvo, {"old_string": '"naoexiste"',
                                             "new_string": '"outra"'})[0], 0)
        self.assertEqual(self.escrita(alvo, {"old_string": '"permissions": {',
                                             "new_string": '"disableAllHooks": {{'})[0], 2)

    def test_write_ilegivel_so_bloqueia_onde_havia_fiacao(self) -> None:
        sem = self.settings(BASE)
        self.assertEqual(self.escrita(sem, {"content": "{ isto não é json"})[0], 0)
        com = self.settings({**BASE, "disableAllHooks": True})
        self.assertEqual(self.escrita(com, {"content": "{ isto não é json"})[0], 2)

    def test_settings_que_nao_e_utf8_nao_derruba_o_guardrail(self) -> None:
        alvo = self.settings(BASE)
        alvo.write_bytes(b'{"permissions": "\xff\xfe"}')
        codigo, err = self.escrita(alvo, {"old_string": '"permissions"',
                                          "new_string": '"disableAllHooks": true, "permissions"'})
        self.assertEqual(codigo, 2)                    # decidido pelo trecho, sem exceção
        self.assertIn("fiação", err)

    def test_settings_local_e_do_usuario_tambem(self) -> None:
        local = self.settings(BASE, ".claude/settings.local.json")
        self.assertEqual(self.escrita(local, {"content": json.dumps({"disableAllHooks": True})})[0], 2)
        usuario = self.settings(BASE, "home/.claude/settings.json")
        self.assertEqual(self.escrita(usuario, {"content": json.dumps({"disableAllHooks": True})})[0], 2)
        outro = self.settings(BASE, "config/settings.json")      # não é de `.claude/`
        self.assertEqual(self.escrita(outro, {"content": json.dumps({"disableAllHooks": True})})[0], 0)

    def test_liberados_e_modos_nao_afrouxam(self) -> None:
        self.settings({"liberados": [".claude/**", "**"], "modos": {"sagrado": "aviso"}},
                      ".agents/guardrails.json")
        alvo = self.settings(BASE)
        self.assertEqual(self.escrita(alvo, {"content": json.dumps({**BASE, "disableAllHooks": True})})[0], 2)
        self.assertEqual(self.cmd("echo '{\"disableAllHooks\": true}' > .claude/settings.json")[0], 2)


class FiacaoPeloShell(Sandbox):
    def test_escrever_num_arquivo_de_fiacao_bloqueia(self) -> None:
        for comando in (
            "echo '{\"disableAllHooks\": true}' > .claude/settings.json",
            "printf x >> ./.claude/settings.local.json",
            "jq '.disableAllHooks = true' a.json >|.claude/settings.json",
            'echo {} > "$HOME/.claude/settings.json"',
            "echo x | tee -a .claude/settings.json",
            "sed -i 's/true/false/' .claude/settings.json",
            "sed -i.bak -e 's/a/b/' .codex/hooks.json",
            "perl -pi -e 's/a/b/' .cursor/hooks.json",
            "cp /tmp/novo.json .claude/settings.json",
            "mv /tmp/novo.json .claude/settings.json && echo ok",
            "rm -f .cursor/hooks.json",
            "truncate -s 0 .codex/hooks.json",
            "dd if=/dev/null of=.claude/settings.json",
            "python3 -c 'import json; open(\".claude/settings.json\",\"w\").write(\"{}\")'",
            "node -e \"require('fs').writeFileSync('.claude/settings.json','{}')\"",
        ):
            with self.subTest(comando):
                codigo, _, err = self.cmd(comando)
                self.assertEqual(codigo, 2)
                self.assertIn("fiação dos hooks", err)

    def test_ler_e_copiar_para_fora_passam(self) -> None:
        for comando in (
            "cat .claude/settings.json",
            "jq . .claude/settings.json",
            "grep -n disableAllHooks .claude/settings.json",
            "cat .claude/settings.json > /tmp/copia.json",
            "cp .claude/settings.json /tmp/copia.json",
            "sed -n '1,5p' .claude/settings.json",
            "cat .claude/settings.json | python3 -m json.tool",
            "echo ok > config/settings.json",
        ):
            with self.subTest(comando):
                self.assertEqual(self.cmd(comando)[0], 0)


if __name__ == "__main__":
    unittest.main()
