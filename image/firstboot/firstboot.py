#!/usr/bin/env python3
"""First login wizard host. Only non-secret choices are written to disk."""

from pathlib import Path
import json
import subprocess
import sys

from PySide6.QtCore import QObject, Property, QProcess, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


NAMES = {"Guará", "Tupã", "Jaci", "Iara", "Ipê", "Boto", "Curió", "Arara"}
PROFILES = {"web", "backend", "gamedev", "devops", "ai", "minimal"}
CONFIG = Path.home() / ".config" / "forjaos"
PIPER_VOICES = {"pt_BR-cadu-medium", "pt_BR-jeff-medium"}


class Bridge(QObject):
    voiceStatusChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._voice_status = "Escolha uma voz para baixar e usar, se quiser."
        self._voice_process = None

    @Property(str, notify=voiceStatusChanged)
    def voiceStatus(self):
        return self._voice_status

    def _set_voice_status(self, status):
        self._voice_status = status
        self.voiceStatusChanged.emit()

    @Slot(str, result=str)
    def downloadVoice(self, voice):
        if voice not in PIPER_VOICES:
            return "Voz indisponível no catálogo."
        if self._voice_process is not None and self._voice_process.state() != QProcess.ProcessState.NotRunning:
            return "Um download de voz já está em andamento."
        process = QProcess(self)
        process.setProgram("forja")
        process.setArguments(["mascot", "voices", "download", voice])
        process.finished.connect(lambda code, _status: self._finish_voice_download(voice, code))
        process.errorOccurred.connect(lambda _error: self._set_voice_status("Não foi possível iniciar o download da voz."))
        self._voice_process = process
        self._set_voice_status(f"Baixando {voice}; aguarde a verificação do arquivo.")
        process.start()
        if not process.waitForStarted(2000):
            self._set_voice_status("CLI forja indisponível; a voz não foi instalada.")
        return self._voice_status

    def _finish_voice_download(self, voice, exit_code):
        process = self._voice_process
        self._voice_process = None
        if process is not None:
            process.deleteLater()
        if exit_code != 0:
            self._set_voice_status("Download ou verificação da voz falhou; nenhuma voz foi selecionada.")
            return
        try:
            selected = subprocess.run(
                ["forja", "mascot", "voice", voice],
                capture_output=True, text=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            selected = None
        if selected is None or selected.returncode != 0:
            self._set_voice_status("Voz baixada, mas não foi possível selecioná-la no perfil.")
            return
        self._set_voice_status(f"Voz {voice} baixada, verificada e selecionada.")

    @Slot(result=str)
    def setupLog(self):
        try:
            state = json.loads((CONFIG / "firstboot-state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ""
        marks = {"running": "[RUNNING]", "done": "[✓]", "failed": "[FAILED]"}
        return "\n".join(f"{marks.get(item.get('status'), '[?]')} {item.get('step', '')}"
                         for item in state.get("events", []))

    @Slot(result=float)
    def setupProgress(self):
        try:
            state = json.loads((CONFIG / "firstboot-state.json").read_text(encoding="utf-8"))
            return float(state.get("done", 0)) / max(1, int(state.get("total", 0)))
        except (OSError, ValueError, TypeError, ZeroDivisionError):
            return 0.0

    @Slot(str)
    def copyText(self, value):
        QGuiApplication.clipboard().setText(value)

    @Slot(result=str)
    def setupStatus(self):
        try:
            state = json.loads((CONFIG / "firstboot-state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "Preparando configuração..."
        if state.get("status") == "complete":
            if state.get("wakeword") == "training_pending":
                return "Configuração concluída. Treino do nome personalizado pendente."
            if state.get("wakeword") == "model_pending":
                return "Configuração concluída. Modelo de wake word pendente."
            return "Configuração concluída."
        if state.get("status") == "failed":
            return "Configuração pendente em " + state.get("step", "perfil") + ". Rode forja setup novamente."
        if state.get("status") == "partial":
            return "Perfil parcial. Pendências: " + ", ".join(state.get("pending", []))
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

    @Slot(str, str, str, str, bool, bool, bool, bool, bool, result=str)
    def finish(self, name, profile, language, keyboard, install_github, install_unity,
               install_claude, install_devcontainers, install_vscode_devcontainers):
        valid_name = 2 <= len(name) <= 24 and all(ch.isalpha() or ch in " -'" for ch in name)
        if (not valid_name or profile not in PROFILES or language not in {"pt-BR", "en-US"}
                or keyboard not in {"br", "us"}):
            return "Escolhas inválidas; nenhuma configuração foi gravada."
        command = ["forja", "setup", "--profile", profile, "--mascot", name,
                   "--language", language, "--keyboard", keyboard]
        if install_github:
            command.append("--github")
        if install_unity:
            command.append("--unity")
        if install_claude:
            command.append("--claude-code")
        if install_devcontainers:
            command.append("--devcontainers")
        if install_vscode_devcontainers:
            command.append("--vscode-devcontainers")
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

    @Slot(result=str)
    def sshAdd(self):
        try:
            subprocess.Popen(["konsole", "-e", "forja", "keys", "ssh-add"], start_new_session=True)
        except OSError:
            return "Abra um terminal e execute forja keys ssh-add."
        return "Chaves SSH serão solicitadas pelo KWallet."

    @Slot(result=str)
    def dockerSetup(self):
        try:
            subprocess.Popen(["konsole", "-e", "forja", "docker", "install"],
                             start_new_session=True)
        except OSError:
            return "Abra um terminal e execute forja docker install."
        return "Instalador Docker aberto no terminal; ele solicita confirmação e senha de administrador."


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
