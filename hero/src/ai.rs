use crate::persona::{self, Persona};
use crate::routes::{self, Provider, RouteProvider};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::path::PathBuf;
use std::process::Output;
use std::time::Duration;
use tokio::process::Command;
use tokio::time::{sleep, timeout};

const OLLAMA_CHAT_URL: &str = "http://127.0.0.1:11434/api/chat";
const MAX_QUERY_CHARS: usize = 4000;
const TURN_TIMEOUT: Duration = Duration::from_secs(58);
const PROCESS_TIMEOUT: Duration = Duration::from_secs(3);
const FIXED_PERSONA: &str = "Responda em português brasileiro com frases curtas e claras. Quando perguntarem, diga a rota atual. Nunca afirme que executou uma ação. Ações do sistema só podem ser executadas pelo catálogo local e pela Policy Engine; confirme antes de qualquer ação que altere o sistema.";

#[derive(Clone, Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SnapshotDoApp {
    #[serde(default)]
    pub application: Option<String>,
    #[serde(default)]
    pub window_title: Option<String>,
}

#[derive(Clone, Debug)]
pub struct Turn {
    pub user: String,
    pub assistant: String,
}

#[derive(Serialize)]
struct AskReply {
    status: &'static str,
    route: String,
    context: String,
    tier: &'static str,
    requires_confirmation: bool,
    answer: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    model: Option<String>,
}

#[derive(Clone, Serialize)]
struct Message {
    role: &'static str,
    content: String,
}

#[derive(Deserialize)]
struct OllamaResponse {
    message: OllamaMessage,
}

#[derive(Deserialize)]
struct OllamaMessage {
    content: String,
}

#[derive(Deserialize)]
struct TagsResponse {
    models: Vec<TaggedModel>,
}

#[derive(Deserialize)]
struct TaggedModel {
    name: String,
}

#[derive(Deserialize)]
struct OpenAiResponse {
    choices: Vec<OpenAiChoice>,
}

#[derive(Deserialize)]
struct OpenAiChoice {
    message: OpenAiMessage,
}

#[derive(Deserialize)]
struct OpenAiMessage {
    content: Option<String>,
}

#[derive(Deserialize)]
struct AnthropicResponse {
    content: Vec<AnthropicBlock>,
}

#[derive(Deserialize)]
struct AnthropicBlock {
    #[serde(rename = "type")]
    block_type: String,
    text: Option<String>,
}

async fn run_output(command: &mut Command) -> Option<Output> {
    command.kill_on_drop(true);
    timeout(PROCESS_TIMEOUT, command.output()).await.ok()?.ok()
}

fn json_reply(
    status: &'static str,
    route: &str,
    context: &str,
    answer: impl Into<String>,
    model: Option<String>,
) -> String {
    serde_json::to_string(&AskReply {
        status,
        route: route.to_string(),
        context: context.to_string(),
        tier: "livre",
        requires_confirmation: false,
        answer: answer.into(),
        model,
    })
    .expect("serialize HERO reply")
}

pub fn busy() -> String {
    json_reply(
        "busy",
        "conversa-de-voz",
        "nenhum",
        "O HERO já está ocupado com outro turno.",
        None,
    )
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

fn persona_prompt(persona: &Persona, route: &str, snapshot: &SnapshotDoApp) -> String {
    let mut prompt = format!(
        "Você é {} do ForjaOS.",
        persona.name.as_deref().unwrap_or("Guará")
    );
    if let Some(instructions) = persona.instructions.as_deref() {
        if !instructions.trim().is_empty() {
            prompt.push_str("\nPreferências editáveis da persona: ");
            prompt.push_str(instructions.trim());
        }
    }
    prompt.push_str("\nRota atual: ");
    prompt.push_str(route);
    if let Some(application) = snapshot.application.as_deref() {
        prompt.push_str("\nAplicativo ativo: ");
        prompt.push_str(&safe_snapshot_value(application));
    }
    if let Some(title) = snapshot.window_title.as_deref() {
        prompt.push_str("\nTítulo da janela ativa: ");
        prompt.push_str(&safe_snapshot_value(title));
    }
    prompt.push_str("\nRegras fixas de segurança e formato: ");
    prompt.push_str(FIXED_PERSONA);
    prompt
}

fn safe_snapshot_value(value: &str) -> String {
    value
        .chars()
        .filter(|character| !character.is_control())
        .take(240)
        .collect()
}

async fn local_answer(
    client: &reqwest::Client,
    query: &str,
    model: &str,
    system_prompt: &str,
    history: &[Turn],
) -> Result<String, &'static str> {
    let mut messages = vec![Message {
        role: "system",
        content: system_prompt.to_string(),
    }];
    append_history(&mut messages, history);
    messages.push(Message {
        role: "user",
        content: query.to_string(),
    });
    let response = client
        .post(OLLAMA_CHAT_URL)
        .json(&json!({
            "model": model,
            "messages": messages,
            "stream": false,
            "keep_alive": "5m",
            "options": {"num_predict": 512}
        }))
        .send()
        .await
        .map_err(|_| "provider_request_failed")?
        .error_for_status()
        .map_err(|_| "provider_request_failed")?
        .json::<OllamaResponse>()
        .await
        .map_err(|_| "provider_response_invalid")?;
    nonempty_response(response.message.content)
}

async fn cloud_answer(
    client: &reqwest::Client,
    provider: Provider,
    model: &str,
    system_prompt: &str,
    query: &str,
    history: &[Turn],
) -> Result<String, &'static str> {
    let key = read_secret(provider).await?;
    let mut messages = vec![Message {
        role: "system",
        content: system_prompt.to_string(),
    }];
    append_history(&mut messages, history);
    messages.push(Message {
        role: "user",
        content: query.to_string(),
    });

    let response = match provider {
        Provider::Anthropic => {
            let mut claude_messages = messages
                .into_iter()
                .filter(|message| message.role != "system")
                .map(|message| json!({"role":message.role,"content":message.content}))
                .collect::<Vec<_>>();
            if claude_messages.is_empty() {
                claude_messages.push(json!({"role":"user","content":query}));
            }
            client
                .post("https://api.anthropic.com/v1/messages")
                .header("x-api-key", &key)
                .header("anthropic-version", "2023-06-01")
                .json(&json!({
                    "model": model,
                    "max_tokens": 512,
                    "system": system_prompt,
                    "messages": claude_messages,
                    "stream": false
                }))
                .send()
                .await
                .map_err(|_| "provider_request_failed")?
                .error_for_status()
                .map_err(|_| "provider_request_failed")?
                .json::<AnthropicResponse>()
                .await
                .map_err(|_| "provider_response_invalid")?
                .content
                .into_iter()
                .filter(|block| block.block_type == "text")
                .filter_map(|block| block.text)
                .collect::<Vec<_>>()
                .join("\n")
        }
        Provider::OpenAi | Provider::OpenRouter | Provider::Nous => {
            let endpoint = match provider {
                Provider::OpenAi => "https://api.openai.com/v1/chat/completions",
                Provider::OpenRouter => "https://openrouter.ai/api/v1/chat/completions",
                Provider::Nous => "https://inference-api.nousresearch.com/v1/chat/completions",
                _ => unreachable!(),
            };
            client
                .post(endpoint)
                .bearer_auth(&key)
                .json(&json!({
                    "model": model,
                    "messages": messages,
                    "max_tokens": 512,
                    "stream": false,
                    "store": false
                }))
                .send()
                .await
                .map_err(|_| "provider_request_failed")?
                .error_for_status()
                .map_err(|_| "provider_request_failed")?
                .json::<OpenAiResponse>()
                .await
                .map_err(|_| "provider_response_invalid")?
                .choices
                .into_iter()
                .next()
                .and_then(|choice| choice.message.content)
                .ok_or("provider_response_invalid")?
        }
        Provider::Ollama => return Err("provider_not_supported"),
    };
    nonempty_response(response)
}

fn append_history(messages: &mut Vec<Message>, history: &[Turn]) {
    for turn in history.iter().rev().take(10).rev() {
        messages.push(Message {
            role: "user",
            content: turn.user.clone(),
        });
        messages.push(Message {
            role: "assistant",
            content: turn.assistant.clone(),
        });
    }
}

fn nonempty_response(answer: String) -> Result<String, &'static str> {
    let answer = answer.trim();
    if answer.is_empty() {
        Err("provider_response_invalid")
    } else {
        Ok(answer.to_string())
    }
}

async fn read_secret(provider: Provider) -> Result<String, &'static str> {
    if provider == Provider::Ollama {
        return Err("provider_not_supported");
    }
    let mut command = Command::new("secret-tool");
    command.args([
        "lookup",
        "application",
        "forjaos",
        "provider",
        provider.as_str(),
    ]);
    let output = run_output(&mut command)
        .await
        .ok_or("secret_service_unavailable")?;
    if !output.status.success() {
        return Err(
            if output.status.code() == Some(1) && output.stderr.is_empty() {
                "provider_key_missing"
            } else {
                "secret_service_unavailable"
            },
        );
    }
    let mut secret = String::from_utf8(output.stdout).map_err(|_| "secret_service_unavailable")?;
    if secret.ends_with('\n') {
        secret.pop();
    }
    if secret.is_empty() || secret.len() > 4096 || secret.chars().any(char::is_control) {
        return Err("secret_service_unavailable");
    }
    Ok(secret)
}

pub async fn classify_with_local_model(query: &str) -> &'static str {
    if !ollama_installed() {
        return "conversa-de-voz";
    }
    let Ok(client) = client() else {
        return "conversa-de-voz";
    };
    if !ensure_server(&client).await {
        return "conversa-de-voz";
    }
    let model = "qwen3:4b";
    if !model_available(&client, model).await {
        return "conversa-de-voz";
    }
    let response = client
        .post(OLLAMA_CHAT_URL)
        .json(&json!({
            "model": model,
            "messages": [
                {"role":"system","content":"Classifique a intenção do usuário em exatamente uma rota. Rotas válidas: conversa-de-voz, sistema, pesquisa, criação, código, saúde-do-sistema, memória. A rota sistema inclui pedidos sobre configuração/controle do sistema. Responda apenas JSON no formato {\"route\":\"...\"}. Não execute nem sugira ações."},
                {"role":"user","content":query}
            ],
            "format": {"type":"object","properties":{"route":{"type":"string","enum":["conversa-de-voz","sistema","pesquisa","criação","código","saúde-do-sistema","memória"]}},"required":["route"]},
            "stream":false,
            "keep_alive":"5m",
            "options":{"temperature":0,"num_predict":32}
        }))
        .send()
        .await;
    let Ok(response) = response else {
        return "conversa-de-voz";
    };
    let Ok(response) = response.error_for_status() else {
        return "conversa-de-voz";
    };
    let Ok(response) = response.json::<OllamaResponse>().await else {
        return "conversa-de-voz";
    };
    let Ok(value) = serde_json::from_str::<serde_json::Value>(&response.message.content) else {
        return "conversa-de-voz";
    };
    match value["route"].as_str() {
        Some("sistema") => "sistema",
        Some("pesquisa") => "pesquisa",
        Some("criação") => "criação",
        Some("código") => "código",
        Some("saúde-do-sistema") => "saúde-do-sistema",
        Some("memória") => "memória",
        _ => "conversa-de-voz",
    }
}

pub async fn ask(
    query: &str,
    route: &str,
    context: &str,
    snapshot: &SnapshotDoApp,
    history: &[Turn],
) -> String {
    match timeout(
        TURN_TIMEOUT,
        ask_inner(query, route, context, snapshot, history),
    )
    .await
    {
        Ok(reply) => reply,
        Err(_) => json_reply(
            "timeout",
            route,
            context,
            "O turno excedeu o limite local de 58 segundos. Tente novamente.",
            None,
        ),
    }
}

async fn ask_inner(
    query: &str,
    route: &str,
    context: &str,
    snapshot: &SnapshotDoApp,
    history: &[Turn],
) -> String {
    let query = query.trim();
    if query.is_empty() || query.chars().count() > MAX_QUERY_CHARS {
        return json_reply(
            "invalid_query",
            route,
            context,
            "A pergunta deve ter entre 1 e 4000 caracteres.",
            None,
        );
    }
    let choice = match routes::provider_for(route) {
        Ok(choice) => choice,
        Err(error) => {
            return json_reply(
                error,
                route,
                context,
                "A configuração da rota é inválida; nenhuma solicitação foi enviada.",
                None,
            )
        }
    };
    let system_prompt = persona_prompt(&persona::load(), route, snapshot);
    let Ok(client) = client() else {
        return json_reply(
            "backend_unavailable",
            route,
            context,
            "Assistente indisponível.",
            None,
        );
    };

    match answer_with_provider(&client, &choice, query, &system_prompt, history).await {
        Ok((answer, model)) => json_reply("ok", route, context, answer, Some(model)),
        Err(error) => json_reply(
            error,
            route,
            context,
            provider_error_message(error),
            choice.model,
        ),
    }
}

async fn answer_with_provider(
    client: &reqwest::Client,
    choice: &RouteProvider,
    query: &str,
    system_prompt: &str,
    history: &[Turn],
) -> Result<(String, String), &'static str> {
    match choice.provider {
        Provider::Ollama => {
            if !ollama_installed() || !ensure_server(client).await {
                return Err("ollama_unavailable");
            }
            let model = match choice.model.as_deref() {
                Some(model) => model.to_string(),
                None => selected_model().await.to_string(),
            };
            if !model_available(client, &model).await {
                return Err("model_not_installed");
            }
            let answer = local_answer(client, query, &model, system_prompt, history).await?;
            Ok((answer, model))
        }
        provider => {
            let model = choice.model.as_deref().ok_or("provider_model_required")?;
            let answer =
                cloud_answer(client, provider, model, system_prompt, query, history).await?;
            Ok((answer, model.to_string()))
        }
    }
}

fn provider_error_message(code: &str) -> &'static str {
    match code {
        "provider_key_missing" => {
            "A chave desta rota não está no KWallet. Configure-a com `forja keys set <provedor>`."
        }
        "secret_service_unavailable" => {
            "KWallet/Secret Service indisponível; nenhuma chave foi carregada."
        }
        "provider_model_required" => "Defina um modelo para este provedor em routes.toml.",
        "cloud_provider_forbidden_on_local_route" => {
            "Esta rota aceita somente o provedor local; nenhuma solicitação foi enviada à nuvem."
        }
        "model_not_installed" => "O modelo local configurado não está instalado no Ollama.",
        "ollama_unavailable" => "O serviço Ollama local não está disponível.",
        "provider_response_invalid" => "O provedor retornou uma resposta inválida.",
        _ => "O provedor configurado não respondeu. Nenhum provedor alternativo foi usado.",
    }
}
