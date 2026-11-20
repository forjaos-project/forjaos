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
    pub language: Option<String>,
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

struct CloudTarget<'a> {
    key: &'a str,
    endpoint: &'a str,
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
    if free_vram_mb().await.is_none_or(|free| free < 6_144) {
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
    server_ready_at(client, "http://127.0.0.1:11434/api/tags").await
}

async fn server_ready_at(client: &reqwest::Client, endpoint: &str) -> bool {
    client
        .get(endpoint)
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
    model_available_at(client, "http://127.0.0.1:11434/api/tags", model).await
}

async fn model_available_at(client: &reqwest::Client, endpoint: &str, model: &str) -> bool {
    let Ok(response) = client
        .get(endpoint)
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
    let fixed_persona = match snapshot.language.as_deref() {
        Some("en-US") => concat!(
            "Reply in US English using short, clear sentences. ",
            "State the current route when asked. Never claim an action was executed unless the local catalog reports success. ",
            "System actions may only run through the local catalog and Policy Engine; confirm before any action that changes the system."
        ),
        _ => FIXED_PERSONA,
    };
    prompt.push_str(fixed_persona);
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
    unload_after_response: bool,
) -> Result<String, &'static str> {
    local_answer_at(
        client,
        OLLAMA_CHAT_URL,
        query,
        model,
        system_prompt,
        history,
        unload_after_response,
    )
    .await
}

fn model_keep_alive(game_mode: bool) -> serde_json::Value {
    if game_mode {
        json!(0)
    } else {
        json!("5m")
    }
}

async fn local_answer_at(
    client: &reqwest::Client,
    endpoint: &str,
    query: &str,
    model: &str,
    system_prompt: &str,
    history: &[Turn],
    unload_after_response: bool,
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
    let keep_alive = model_keep_alive(unload_after_response);
    let response = client
        .post(endpoint)
        .json(&json!({
            "model": model,
            "messages": messages,
            "stream": false,
            "keep_alive": keep_alive,
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
    let endpoint = cloud_endpoint(provider)?;
    cloud_answer_at(
        client,
        provider,
        model,
        system_prompt,
        query,
        history,
        CloudTarget {
            key: &key,
            endpoint,
        },
    )
    .await
}

fn cloud_endpoint(provider: Provider) -> Result<&'static str, &'static str> {
    match provider {
        Provider::Anthropic => Ok("https://api.anthropic.com/v1/messages"),
        Provider::OpenAi => Ok("https://api.openai.com/v1/chat/completions"),
        Provider::OpenRouter => Ok("https://openrouter.ai/api/v1/chat/completions"),
        Provider::Nous => Ok("https://inference-api.nousresearch.com/v1/chat/completions"),
        Provider::Ollama => Err("provider_not_supported"),
    }
}

async fn cloud_answer_at(
    client: &reqwest::Client,
    provider: Provider,
    model: &str,
    system_prompt: &str,
    query: &str,
    history: &[Turn],
    target: CloudTarget<'_>,
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
                .post(target.endpoint)
                .header("x-api-key", target.key)
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
        Provider::OpenAi | Provider::OpenRouter | Provider::Nous => client
            .post(target.endpoint)
            .bearer_auth(target.key)
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
            .ok_or("provider_response_invalid")?,
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
    classify_with_model_endpoint(&client, OLLAMA_CHAT_URL, model, query).await
}

async fn classify_with_model_endpoint(
    client: &reqwest::Client,
    endpoint: &str,
    model: &str,
    query: &str,
) -> &'static str {
    let response = client
        .post(endpoint)
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
    route_from_model_output(&response.message.content)
}

fn route_from_model_output(content: &str) -> &'static str {
    let Ok(value) = serde_json::from_str::<serde_json::Value>(content) else {
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
    let game_mode = game_mode_active().await;
    match choice.provider {
        Provider::Ollama => {
            if !ollama_installed() || !ensure_server(client).await {
                return Err("ollama_unavailable");
            }
            let model = match (game_mode, choice.model.as_deref()) {
                (true, _) => "qwen3:4b".to_string(),
                (false, Some(model)) => model.to_string(),
                (false, None) => selected_model().await.to_string(),
            };
            if !model_available(client, &model).await {
                return Err("model_not_installed");
            }
            let answer =
                local_answer(client, query, &model, system_prompt, history, game_mode).await?;
            Ok((answer, model))
        }
        provider => {
            if game_mode {
                return Err("game_mode_local_only");
            }
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
        "game_mode_local_only" => {
            "No Modo Jogo, o HERO responde apenas com o modelo local Qwen3 4B."
        }
        "provider_response_invalid" => "O provedor retornou uma resposta inválida.",
        _ => "O provedor configurado não respondeu. Nenhum provedor alternativo foi usado.",
    }
}

#[cfg(test)]
mod tests {
    use super::{
        answer_with_provider, append_history, busy, classify_with_model_endpoint, cloud_answer_at,
        cloud_endpoint, json_reply, local_answer_at, model_available_at, model_keep_alive,
        nonempty_response, persona_prompt, provider_error_message, route_from_model_output,
        safe_snapshot_value, server_ready_at, CloudTarget, Message, SnapshotDoApp, Turn,
    };
    use crate::persona::Persona;
    use crate::routes::{Provider, RouteProvider};
    use crate::test_support::TestHome;
    use serde_json::{json, Value};
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;
    use tokio::task::JoinHandle;

    async fn mock_endpoint(body: &'static str, status: u16) -> (String, JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0")
            .await
            .expect("bind local HTTP mock");
        let address = listener.local_addr().expect("mock address");
        let task = tokio::spawn(async move {
            let Ok((mut stream, _)) = listener.accept().await else {
                return;
            };
            let mut request = [0u8; 4096];
            let _ = stream.read(&mut request).await;
            let reason = if (200..300).contains(&status) {
                "OK"
            } else {
                "Internal Server Error"
            };
            let response = format!(
                "HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
                body.len()
            );
            let _ = stream.write_all(response.as_bytes()).await;
        });
        (format!("http://{address}/test"), task)
    }

    #[test]
    fn replies_are_valid_json_and_busy_state_is_explicit() {
        let value: Value = serde_json::from_str(&busy()).expect("busy reply JSON");
        assert_eq!(value["status"], "busy");
        assert_eq!(value["route"], "conversa-de-voz");
        assert_eq!(value["requires_confirmation"], false);

        let reply = json_reply(
            "ok",
            "código",
            "projeto: demo",
            "pronto",
            Some("local".into()),
        );
        let value: Value = serde_json::from_str(&reply).expect("serialized reply JSON");
        assert_eq!(value["answer"], "pronto");
        assert_eq!(value["model"], "local");
        assert!(value.get("unused").is_none());
    }

    #[test]
    fn prompts_sanitize_window_metadata_and_follow_selected_language() {
        let persona = Persona {
            name: Some("Guará Dev".into()),
            voice: None,
            instructions: Some("  Seja conciso.  ".into()),
        };
        let snapshot = SnapshotDoApp {
            language: Some("en-US".into()),
            application: Some("Konsole\nsegundo campo".into()),
            window_title: Some("Projeto\u{7} ForjaOS".into()),
        };
        let prompt = persona_prompt(&persona, "código", &snapshot);
        assert!(prompt.contains("Você é Guará Dev"));
        assert!(prompt.contains("Preferências editáveis da persona: Seja conciso."));
        assert!(prompt.contains("Aplicativo ativo: Konsolesegundo campo"));
        assert!(prompt.contains("Título da janela ativa: Projeto ForjaOS"));
        assert!(prompt.contains("Reply in US English"));
        assert!(!prompt.contains("\u{7}"));
    }

    #[test]
    fn snapshot_values_are_control_free_and_bounded() {
        assert_eq!(safe_snapshot_value("A\nB\u{7}C"), "ABC");
        assert_eq!(safe_snapshot_value(&"x".repeat(300)).len(), 240);
    }

    #[test]
    fn history_keeps_only_the_latest_ten_turns_in_order() {
        let history = (0..12)
            .map(|index| Turn {
                user: format!("pergunta-{index}"),
                assistant: format!("resposta-{index}"),
            })
            .collect::<Vec<_>>();
        let mut messages = Vec::<Message>::new();
        append_history(&mut messages, &history);
        assert_eq!(messages.len(), 20);
        assert_eq!(
            messages.first().map(|message| message.content.as_str()),
            Some("pergunta-2")
        );
        assert_eq!(
            messages.last().map(|message| message.content.as_str()),
            Some("resposta-11")
        );
    }

    #[test]
    fn provider_responses_are_trimmed_and_empty_values_are_rejected() {
        assert_eq!(
            nonempty_response("  resposta local \n".into()),
            Ok("resposta local".into())
        );
        assert_eq!(
            nonempty_response(" \n ".into()),
            Err("provider_response_invalid")
        );
    }

    #[test]
    fn game_mode_models_unload_after_each_response() {
        assert_eq!(model_keep_alive(true), json!(0));
        assert_eq!(model_keep_alive(false), json!("5m"));
    }

    #[test]
    fn model_route_parser_allows_only_known_routes() {
        for (content, expected) in [
            (r#"{"route":"sistema"}"#, "sistema"),
            (r#"{"route":"pesquisa"}"#, "pesquisa"),
            (r#"{"route":"criação"}"#, "criação"),
            (r#"{"route":"código"}"#, "código"),
            (r#"{"route":"saúde-do-sistema"}"#, "saúde-do-sistema"),
            (r#"{"route":"memória"}"#, "memória"),
            (r#"{"route":"shell"}"#, "conversa-de-voz"),
            ("not json", "conversa-de-voz"),
        ] {
            assert_eq!(route_from_model_output(content), expected);
        }
    }

    #[test]
    fn provider_errors_never_suggest_an_implicit_fallback() {
        for error in [
            "provider_key_missing",
            "secret_service_unavailable",
            "provider_model_required",
            "cloud_provider_forbidden_on_local_route",
            "model_not_installed",
            "ollama_unavailable",
            "provider_response_invalid",
            "unknown",
        ] {
            let message = provider_error_message(error);
            assert!(!message.is_empty());
            if error == "unknown" {
                assert!(message.contains("Nenhum provedor alternativo"));
            }
        }
    }

    #[tokio::test]
    async fn provider_dispatch_rejects_missing_cloud_model_without_network() {
        let client = reqwest::Client::builder()
            .no_proxy()
            .build()
            .expect("HTTP client");
        let result = answer_with_provider(
            &client,
            &RouteProvider {
                provider: Provider::OpenAi,
                model: None,
            },
            "consulta",
            "persona",
            &[],
        )
        .await;
        assert_eq!(result, Err("provider_model_required"));
    }

    #[tokio::test]
    async fn ask_rejects_invalid_queries_before_provider_access() {
        let snapshot = SnapshotDoApp::default();
        let empty: Value =
            serde_json::from_str(&super::ask("  ", "pesquisa", "", &snapshot, &[]).await)
                .expect("empty query response");
        assert_eq!(empty["status"], "invalid_query");

        let long_query = "x".repeat(4001);
        let long: Value =
            serde_json::from_str(&super::ask(&long_query, "pesquisa", "", &snapshot, &[]).await)
                .expect("long query response");
        assert_eq!(long["status"], "invalid_query");

        let invalid_route: Value = serde_json::from_str(
            &super::ask("pergunta", "rota-inexistente", "", &snapshot, &[]).await,
        )
        .expect("invalid route response");
        assert_eq!(invalid_route["status"], "route_not_supported");
    }

    #[tokio::test]
    async fn ask_uses_the_selected_route_and_reports_local_backend_unavailable() {
        let _home = TestHome::new();
        let reply: Value = serde_json::from_str(
            &super::ask(
                "pergunta válida",
                "pesquisa",
                "sem contexto",
                &SnapshotDoApp::default(),
                &[],
            )
            .await,
        )
        .expect("ask reply JSON");
        assert_eq!(reply["status"], "ollama_unavailable");
        assert_eq!(reply["route"], "pesquisa");
        assert!(reply["answer"].as_str().unwrap().contains("Ollama"));
    }

    #[tokio::test]
    async fn local_answer_handles_success_http_failure_and_invalid_json() {
        let client = reqwest::Client::builder()
            .no_proxy()
            .build()
            .expect("HTTP client");
        let (url, server) =
            mock_endpoint(r#"{"message":{"content":" resposta local "}}"#, 200).await;
        assert_eq!(
            local_answer_at(&client, &url, "pergunta", "qwen3:4b", "persona", &[], false).await,
            Ok("resposta local".into())
        );
        server.await.expect("success mock task");

        let (url, server) = mock_endpoint(r#"{"message":{"content":"falha"}}"#, 500).await;
        assert_eq!(
            local_answer_at(&client, &url, "pergunta", "qwen3:4b", "persona", &[], false).await,
            Err("provider_request_failed")
        );
        server.await.expect("HTTP error mock task");

        let (url, server) = mock_endpoint(r#"{"wrong":true}"#, 200).await;
        assert_eq!(
            local_answer_at(&client, &url, "pergunta", "qwen3:4b", "persona", &[], false).await,
            Err("provider_response_invalid")
        );
        server.await.expect("invalid JSON mock task");

        assert_eq!(
            local_answer_at(
                &client,
                "invalid-url",
                "pergunta",
                "qwen3:4b",
                "persona",
                &[],
                false
            )
            .await,
            Err("provider_request_failed")
        );
    }

    #[tokio::test]
    async fn local_model_readiness_and_classifier_use_only_valid_responses() {
        let client = reqwest::Client::builder()
            .no_proxy()
            .build()
            .expect("HTTP client");
        let tags = r#"{"models":[{"name":"qwen3:4b"}]}"#;
        let (url, server) = mock_endpoint(tags, 200).await;
        assert!(server_ready_at(&client, &url).await);
        server.await.expect("ready mock task");

        let (url, server) = mock_endpoint(tags, 200).await;
        assert!(model_available_at(&client, &url, "qwen3:4b").await);
        server.await.expect("available model mock task");

        let (url, server) = mock_endpoint(tags, 200).await;
        assert!(!model_available_at(&client, &url, "missing").await);
        server.await.expect("missing model mock task");

        let (url, server) = mock_endpoint(tags, 503).await;
        assert!(!server_ready_at(&client, &url).await);
        server.await.expect("unavailable mock task");

        let (url, server) = mock_endpoint(
            r#"{"message":{"content":"{\"route\":\"saúde-do-sistema\"}"}}"#,
            200,
        )
        .await;
        assert_eq!(
            classify_with_model_endpoint(&client, &url, "qwen3:4b", "temperatura da CPU").await,
            "saúde-do-sistema"
        );
        server.await.expect("classifier mock task");

        assert!(!server_ready_at(&client, "invalid-url").await);
        assert!(!model_available_at(&client, "invalid-url", "qwen3:4b").await);
        assert_eq!(
            classify_with_model_endpoint(&client, "invalid-url", "qwen3:4b", "pergunta").await,
            "conversa-de-voz"
        );
    }

    #[tokio::test]
    async fn cloud_providers_parse_only_text_and_report_invalid_responses() {
        let client = reqwest::Client::builder()
            .no_proxy()
            .build()
            .expect("HTTP client");
        for provider in [Provider::OpenAi, Provider::OpenRouter, Provider::Nous] {
            assert!(cloud_endpoint(provider)
                .expect("cloud endpoint")
                .starts_with("https://"));
            let (url, server) = mock_endpoint(
                r#"{"choices":[{"message":{"content":" cloud reply "}}]}"#,
                200,
            )
            .await;
            assert_eq!(
                cloud_answer_at(
                    &client,
                    provider,
                    "model-x",
                    "persona",
                    "query",
                    &[],
                    CloudTarget {
                        key: "test-key",
                        endpoint: &url
                    }
                )
                .await,
                Ok("cloud reply".into())
            );
            server.await.expect("OpenAI-compatible mock task");
        }

        assert!(cloud_endpoint(Provider::Anthropic)
            .expect("Anthropic endpoint")
            .contains("anthropic.com"));
        let (url, server) = mock_endpoint(
            r#"{"content":[{"type":"text","text":"one"},{"type":"thinking","text":"hidden"},{"type":"text","text":"two"}]}"#,
            200,
        )
        .await;
        assert_eq!(
            cloud_answer_at(
                &client,
                Provider::Anthropic,
                "claude-test",
                "persona",
                "query",
                &[],
                CloudTarget {
                    key: "test-key",
                    endpoint: &url
                }
            )
            .await,
            Ok("one\ntwo".into())
        );
        server.await.expect("Anthropic mock task");

        let (url, server) = mock_endpoint(r#"{"choices":[]}"#, 200).await;
        assert_eq!(
            cloud_answer_at(
                &client,
                Provider::OpenAi,
                "model-x",
                "persona",
                "query",
                &[],
                CloudTarget {
                    key: "test-key",
                    endpoint: &url
                }
            )
            .await,
            Err("provider_response_invalid")
        );
        server.await.expect("invalid cloud response mock task");

        let (url, server) = mock_endpoint("not json", 200).await;
        assert_eq!(
            cloud_answer_at(
                &client,
                Provider::OpenAi,
                "model-x",
                "persona",
                "query",
                &[],
                CloudTarget {
                    key: "test-key",
                    endpoint: &url
                }
            )
            .await,
            Err("provider_response_invalid")
        );
        server.await.expect("malformed cloud response mock task");

        let (url, server) = mock_endpoint(r#"{"error":"unavailable"}"#, 503).await;
        assert_eq!(
            cloud_answer_at(
                &client,
                Provider::OpenAi,
                "model-x",
                "persona",
                "query",
                &[],
                CloudTarget {
                    key: "test-key",
                    endpoint: &url
                }
            )
            .await,
            Err("provider_request_failed")
        );
        server.await.expect("cloud HTTP failure mock task");
        assert_eq!(
            cloud_endpoint(Provider::Ollama),
            Err("provider_not_supported")
        );
    }
}
