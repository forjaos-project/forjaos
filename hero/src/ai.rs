use serde::Serialize;
use std::path::PathBuf;
use std::process::Output;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::{sleep, timeout};

const OLLAMA_CHAT_URL: &str = "http://127.0.0.1:11434/api/chat";
const MAX_QUERY_CHARS: usize = 4000;
const TURN_TIMEOUT: Duration = Duration::from_secs(58);
const PROCESS_TIMEOUT: Duration = Duration::from_secs(3);

async fn run_output(command: &mut Command) -> Option<Output> {
    command.kill_on_drop(true);
    timeout(PROCESS_TIMEOUT, command.output()).await.ok()?.ok()
}

#[derive(Serialize)]
struct AskReply<'a> {
    status: &'a str,
    route: &'a str,
    context: &'a str,
    tier: &'a str,
    requires_confirmation: bool,
    answer: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    model: Option<&'a str>,
}

#[derive(serde::Deserialize)]
struct ChatResponse {
    message: ChatMessage,
}

#[derive(serde::Deserialize)]
struct ChatMessage {
    content: String,
}

#[derive(serde::Deserialize)]
struct TagsResponse {
    models: Vec<TaggedModel>,
}

#[derive(serde::Deserialize)]
struct TaggedModel {
    name: String,
}

fn json_reply(reply: AskReply<'_>) -> String {
    serde_json::to_string(&reply).expect("serialize HERO reply")
}

pub fn busy() -> String {
    json_reply(AskReply {
        status: "busy",
        route: "conversa-de-voz",
        context: "nenhum",
        tier: "livre",
        requires_confirmation: false,
        answer: "O HERO já está ocupado com outro turno.".into(),
        model: None,
    })
}

fn system_request(query: &str) -> bool {
    let normalized = query.trim().to_lowercase();
    [
        "instale ",
        "execute ",
        "rode ",
        "apague ",
        "remova ",
        "atualize ",
        "reinicie ",
        "ligue ",
        "desligue ",
        "abra ",
        "crie ",
        "suba ",
        "derrube ",
    ]
    .iter()
    .any(|prefix| normalized.starts_with(prefix))
}

async fn game_mode_active() -> bool {
    run_output(Command::new("systemctl").args([
        "--user",
        "is-active",
        "--quiet",
        "hero-game.target",
    ]))
    .await
    .is_some_and(|output| output.status.success())
}

async fn free_vram_mb() -> Option<u64> {
    let output = run_output(
        Command::new("nvidia-smi")
            .args(["--query-gpu=memory.free", "--format=csv,noheader,nounits"]),
    )
    .await?;
    if !output.status.success() {
        return None;
    }
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.trim().parse::<u64>().ok())
        .min()
}

async fn selected_model() -> &'static str {
    if game_mode_active().await || free_vram_mb().await.is_none_or(|free| free < 6_144) {
        "qwen3:4b"
    } else {
        "qwen3:8b"
    }
}

fn client() -> Result<reqwest::Client, ()> {
    reqwest::Client::builder()
        .no_proxy()
        .timeout(Duration::from_secs(60))
        .build()
        .map_err(|_| ())
}

async fn server_ready(client: &reqwest::Client) -> bool {
    client
        .get("http://127.0.0.1:11434/api/tags")
        .timeout(Duration::from_secs(1))
        .send()
        .await
        .is_ok_and(|response| response.status().is_success())
}

async fn start_ollama_service() -> bool {
    run_output(Command::new("systemctl").args(["--user", "start", "--no-block", "ollama.service"]))
        .await
        .is_some_and(|output| output.status.success())
}

fn ollama_installed() -> bool {
    std::env::var_os("HOME")
        .map(PathBuf::from)
        .is_some_and(|home| home.join(".brew/bin/ollama").is_file())
}

async fn ensure_server(client: &reqwest::Client) -> bool {
    if server_ready(client).await {
        return true;
    }
    if !start_ollama_service().await {
        return false;
    }

    timeout(Duration::from_secs(10), async {
        loop {
            if server_ready(client).await {
                return true;
            }
            sleep(Duration::from_millis(250)).await;
        }
    })
    .await
    .unwrap_or(false)
}

async fn model_available(client: &reqwest::Client, model: &str) -> bool {
    let Ok(response) = client
        .get("http://127.0.0.1:11434/api/tags")
        .timeout(Duration::from_secs(1))
        .send()
        .await
    else {
        return false;
    };
    let Ok(response) = response.error_for_status() else {
        return false;
    };
    response
        .json::<TagsResponse>()
        .await
        .is_ok_and(|tags| tags.models.iter().any(|item| item.name == model))
}

async fn local_answer(client: &reqwest::Client, query: &str, model: &str) -> Result<String, ()> {
    let response = client
        .post(OLLAMA_CHAT_URL)
        .json(&serde_json::json!({
            "model": model,
            "messages": [
                {"role":"system", "content":"Você é o HERO do ForjaOS. Responda em português brasileiro, com clareza e concisão. Você não tem ferramentas para alterar o sistema; nunca diga que executou uma ação."},
                {"role":"user", "content": query}
            ],
            "stream": false,
            "keep_alive": "5m",
            "options": {"num_predict": 512}
        }))
        .send()
        .await
        .map_err(|_| ())?
        .error_for_status()
        .map_err(|_| ())?
        .json::<ChatResponse>()
        .await
        .map_err(|_| ())?;
    Ok(response.message.content)
}

pub async fn ask(query: &str) -> String {
    match timeout(TURN_TIMEOUT, ask_inner(query)).await {
        Ok(reply) => reply,
        Err(_) => json_reply(AskReply {
            status: "timeout",
            route: "conversa-de-voz",
            context: "nenhum",
            tier: "livre",
            requires_confirmation: false,
            answer: "O turno excedeu o limite local de 58 segundos. Tente novamente.".into(),
            model: None,
        }),
    }
}

async fn ask_inner(query: &str) -> String {
    let query = query.trim();
    if query.is_empty() || query.chars().count() > MAX_QUERY_CHARS {
        return json_reply(AskReply {
            status: "invalid_query",
            route: "conversa-de-voz",
            context: "nenhum",
            tier: "livre",
            requires_confirmation: false,
            answer: "A pergunta deve ter entre 1 e 4000 caracteres.".into(),
            model: None,
        });
    }

    if system_request(query) {
        return json_reply(AskReply {
            status: "blocked",
            route: "sistema",
            context: "nenhum; o catálogo de ações ainda não está disponível",
            tier: "bloqueado",
            requires_confirmation: false,
            answer: "Nenhuma ação foi executada. A solicitação não corresponde a uma ferramenta permitida do catálogo.".into(),
            model: None,
        });
    }

    let Ok(client) = client() else {
        return backend_unavailable("Assistente local indisponível.", None);
    };
    if !ollama_installed() {
        return backend_unavailable(
            "Ollama não está instalado. Selecione o perfil de IA no primeiro boot e tente novamente.",
            None,
        );
    }
    if !ensure_server(&client).await {
        return backend_unavailable("O serviço Ollama local não pôde ser iniciado.", None);
    }

    let model = selected_model().await;
    if !model_available(&client, model).await {
        return json_reply(AskReply {
            status: "model_not_installed",
            route: "conversa-de-voz",
            context: "nenhum",
            tier: "livre",
            requires_confirmation: false,
            answer: format!("O modelo {model} não está instalado. Para instalá-lo, execute `ollama pull {model}` e tente novamente."),
            model: Some(model),
        });
    }

    match local_answer(&client, query, model).await {
        Ok(answer) => json_reply(AskReply {
            status: "ok",
            route: "conversa-de-voz",
            context: "nenhum",
            tier: "livre",
            requires_confirmation: false,
            answer,
            model: Some(model),
        }),
        Err(()) => json_reply(AskReply {
            status: "backend_unavailable",
            route: "conversa-de-voz",
            context: "nenhum",
            tier: "livre",
            requires_confirmation: false,
            answer: "Assistente local indisponível. Verifique o Ollama local.".into(),
            model: Some(model),
        }),
    }
}

fn backend_unavailable(answer: &str, model: Option<&str>) -> String {
    json_reply(AskReply {
        status: "backend_unavailable",
        route: "conversa-de-voz",
        context: "nenhum",
        tier: "livre",
        requires_confirmation: false,
        answer: answer.into(),
        model,
    })
}
