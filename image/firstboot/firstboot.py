#!/usr/bin/env python3
"""First login wizard host. Only non-secret choices are written to disk."""

from pathlib import Path
import json
import subprocess
import sys

from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


NAMES = {"Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara"}
PROFILES = {"web", "backend", "gamedev", "devops", "ai", "minimal"}
CONFIG = Path.home() / ".config" / "forjaos"


class Bridge(QObject):
    @Slot(result=str)
    def setupStatus(self):
        try:
            state = json.loads((CONFIG / "firstboot-state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "Preparando configuração..."
        if state.get("status") == "complete":
            return "Configuração concluída."
        if state.get("status") == "failed":
            return "Configuração pendente em " + state.get("step", "perfil") + ". Rode forja setup novamente."
        return "Configurando " + state.get("step", "perfil") + " em segundo plano..."

    @Slot(str, str, result=str)
    def storeKey(self, provider, key):
        if provider not in {"anthropic", "openai", "openrouter", "nous"} or not key:
            return "Informe um provedor e uma chave."
        try:
            result = subprocess.run(
                ["secret-tool", "store", "--label", f"ForjaOS {provider}",
                 "application", "forjaos", "provider", provider],
                input=key, text=True, capture_output=True, check=False,
            )
        except OSError:
            return "KWallet indisponível; a chave não foi salva."
        return "Chave salva no KWallet." if result.returncode == 0 else "KWallet recusou a chave."

    @Slot(str, str, str, str, bool, result=str)
    def finish(self, name, profile, language, keyboard, install_unity):
        if (name not in NAMES or profile not in PROFILES or language not in {"pt-BR", "en-US"}
                or keyboard not in {"br", "us"}):
            return "Escolhas inválidas; nenhuma configuração foi gravada."
        command = ["forja", "setup", "--profile", profile, "--mascot", name,
                   "--language", language, "--keyboard", keyboard]
        if install_unity:
            command.append("--unity")
        try:
            subprocess.Popen(command, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        except OSError:
            return "Não foi possível iniciar forja setup."
        return "Configuração iniciada em segundo plano."

    @Slot(result=str)
    def githubLogin(self):
        try:
            subprocess.Popen(["konsole", "-e", "gh", "auth", "login"], start_new_session=True)
        except OSError:
            return "GitHub CLI indisponível. Configure depois com gh auth login."
        return "Autenticação aberta no terminal."


def main():
    if (CONFIG / "firstboot-complete").exists():
        return 0
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    bridge = Bridge(engine)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile("/usr/share/forjaos/firstboot/Wizard.qml"))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
