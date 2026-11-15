pub async fn classify(query: &str) -> &'static str {
    if let Some(route) = rule_route(query) {
        return route;
    }
    super::ai::classify_with_local_model(query).await
}

fn rule_route(query: &str) -> Option<&'static str> {
    let text = query.trim().to_lowercase();
    if contains_any(
        &text,
        &[
            "memória",
            "memoria",
            "lembra",
            "histórico do que fiz",
            "o que fiz ontem",
            "o que eu fiz ontem",
        ],
    ) {
        return Some("memória");
    }
    if contains_any(
        &text,
        &[
            "cpu",
            "gpu",
            "temperatura",
            "desempenho do sistema",
            "saúde do sistema",
            "saude do sistema",
            "uso de memória ram",
            "uso de memoria ram",
            "conexão de rede",
            "conexao de rede",
        ],
    ) {
        return Some("saúde-do-sistema");
    }
    if contains_any(
        &text,
        &[
            "wifi",
            "wi-fi",
            "bluetooth",
            "vpn",
            "configuração do sistema",
            "configuracao do sistema",
            "problema no sistema",
            "atualização do sistema",
            "atualizacao do sistema",
        ],
    ) {
        return Some("sistema");
    }
    if contains_any(
        &text,
        &[
            "código",
            "codigo",
            "programa",
            "programação",
            "programacao",
            "compilar",
            "compilação",
            "compilacao",
            "bug",
            "git",
            "rust",
            "python",
            "typescript",
            "javascript",
            "api",
            "dockerfile",
            "compose",
            "pull request",
        ],
    ) {
        return Some("código");
    }
    if contains_any(
        &text,
        &[
            "pesquise",
            "pesquisa",
            "pesquisar",
            "fontes sobre",
            "referências sobre",
            "referencias sobre",
            "compare",
            "investigue",
            "investigação",
            "investigacao",
        ],
    ) {
        return Some("pesquisa");
    }
    if contains_any(
        &text,
        &[
            "escreva",
            "redija",
            "crie um texto",
            "crie uma história",
            "crie uma historia",
            "gere uma ideia",
            "roteiro",
            "poema",
            "resuma este texto",
            "traduza",
        ],
    ) {
        return Some("criação");
    }
    None
}

fn contains_any(text: &str, phrases: &[&str]) -> bool {
    phrases.iter().any(|phrase| text.contains(phrase))
}
