function statusLabel(state, yesLabel, noLabel, unknownLabel) {
    if (state === "yes") {
        return yesLabel;
    }
    if (state === "no") {
        return noLabel;
    }
    return unknownLabel;
}

function stateNote(hasUnavailableStatus, portuguese) {
    if (portuguese) {
        return hasUnavailableStatus
            ? "A detecção de sistema ainda não está conectada para todos os estados. Estados sem leitura aparecem como indisponíveis. Nenhuma alteração de disco ou de firmware será feita nesta tela."
            : "Os estados acima foram lidos deste sistema. Nenhuma alteração de disco ou de firmware será feita nesta tela.";
    }
    return hasUnavailableStatus
        ? "System detection is not connected for every status yet. Unreadable states remain marked as unavailable. This screen will not change disks or firmware."
        : "The statuses above were read from this system. This screen will not change disks or firmware.";
}
