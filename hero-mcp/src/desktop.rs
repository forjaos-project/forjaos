use crate::common;
use rmcp::{
    handler::server::router::tool::ToolRouter, handler::server::wrapper::Parameters, tool,
    tool_router,
};
use schemars::JsonSchema;
use serde::Deserialize;
use std::path::PathBuf;

pub struct DesktopServer {
    #[allow(dead_code)]
    tool_router: ToolRouter<Self>,
    dnd_state: tokio::sync::Mutex<DndState>,
}

#[derive(Default)]
struct DndState {
    connection: Option<zbus::Connection>,
    cookie: Option<u32>,
}

impl Default for DesktopServer {
    fn default() -> Self {
        Self {
            tool_router: Self::tool_router(),
            dnd_state: tokio::sync::Mutex::new(DndState::default()),
        }
    }
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct WindowArgs {
    #[schemars(length(max = 16))]
    window_id: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct NotifyArgs {
    #[schemars(length(max = 120))]
    title: String,
    #[schemars(length(max = 1000))]
    body: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ToggleArgs {
    enabled: bool,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ClipboardArgs {
    #[schemars(length(max = 16000))]
    text: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ScreenshotArgs {
    #[schemars(regex(pattern = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.png$"))]
    filename: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct AppArgs {
    #[schemars(length(max = 128))]
    desktop_id: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct UrlArgs {
    #[schemars(length(max = 2048))]
    #[schemars(regex(pattern = r"^https?://\S+$"))]
    url: String,
}

#[tool_router(server_handler)]
impl DesktopServer {
    #[tool(
        name = "windows.list",
        description = "Tier: livre. Lista janelas gráficas disponíveis.",
        annotations(read_only_hint = true)
    )]
    async fn windows_list(&self) -> String {
        common::run("wmctrl", &["-lp"])
            .await
            .unwrap_or_else(|_| "wmctrl indisponível nesta sessão".to_string())
    }

    #[tool(
        name = "windows.focus",
        description = "Tier: alterar. Foca uma janela pelo identificador retornado em windows.list.",
        annotations(destructive_hint = true)
    )]
    async fn windows_focus(&self, Parameters(args): Parameters<WindowArgs>) -> String {
        let id = args.window_id.strip_prefix("0x").unwrap_or(&args.window_id);
        if id.is_empty()
            || id.len() > 16
            || !id.chars().all(|character| character.is_ascii_hexdigit())
        {
            return "identificador de janela inválido".to_string();
        }
        common::run("wmctrl", &["-ia", &format!("0x{id}")])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "notify.send",
        description = "Tier: alterar. Exibe uma notificação local.",
        annotations(destructive_hint = true)
    )]
    async fn notify_send(&self, Parameters(args): Parameters<NotifyArgs>) -> String {
        if args.title.len() > 120
            || args.body.len() > 1000
            || args
                .title
                .chars()
                .chain(args.body.chars())
                .any(char::is_control)
        {
            return "texto da notificação inválido".to_string();
        }
        common::run("notify-send", &["--", &args.title, &args.body])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "dnd.toggle",
        description = "Tier: alterar. Ativa ou desativa Não Perturbe; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn dnd_toggle(&self, Parameters(args): Parameters<ToggleArgs>) -> String {
        let mut state = self.dnd_state.lock().await;
        if state.connection.is_none() {
            match zbus::Connection::session().await {
                Ok(connection) => state.connection = Some(connection),
                Err(_) => return "barramento D-Bus da sessão indisponível".to_string(),
            }
        }
        let Some(connection) = state.connection.as_ref() else {
            return "barramento D-Bus da sessão indisponível".to_string();
        };
        let Ok(proxy) = zbus::Proxy::new(
            connection,
            "org.freedesktop.Notifications",
            "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications",
        )
        .await
        else {
            return "serviço de notificações indisponível".to_string();
        };
        if args.enabled {
            if state.cookie.is_some() {
                return "Não Perturbe já está ativo nesta conexão".to_string();
            }
            let hints = std::collections::HashMap::<String, zbus::zvariant::OwnedValue>::new();
            match proxy
                .call::<_, _, u32>("Inhibit", &("forjaos", "HERO", hints))
                .await
            {
                Ok(cookie) => {
                    state.cookie = Some(cookie);
                    "Não Perturbe ativo".to_string()
                }
                Err(_) => "Não Perturbe indisponível nesta sessão".to_string(),
            }
        } else if let Some(cookie) = state.cookie {
            match proxy.call::<_, _, ()>("UnInhibit", &(cookie,)).await {
                Ok(()) => {
                    state.cookie = None;
                    "Não Perturbe desativado".to_string()
                }
                Err(_) => "não foi possível desativar Não Perturbe".to_string(),
            }
        } else {
            "Não Perturbe não foi ativado por esta conexão".to_string()
        }
    }

    #[tool(
        name = "media.play",
        description = "Tier: alterar. Retoma mídia no player ativo.",
        annotations(destructive_hint = true)
    )]
    async fn media_play(&self) -> String {
        common::run("playerctl", &["play"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "media.pause",
        description = "Tier: alterar. Pausa mídia no player ativo.",
        annotations(destructive_hint = true)
    )]
    async fn media_pause(&self) -> String {
        common::run("playerctl", &["pause"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "media.next",
        description = "Tier: alterar. Avança para a próxima mídia.",
        annotations(destructive_hint = true)
    )]
    async fn media_next(&self) -> String {
        common::run("playerctl", &["next"])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "clipboard.read",
        description = "Tier: alterar. Lê o conteúdo sensível da área de transferência; requer aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn clipboard_read(&self) -> String {
        common::run("wl-paste", &["--no-newline", "--type", "text/plain"])
            .await
            .unwrap_or_else(|_| "área de transferência indisponível".to_string())
    }

    #[tool(
        name = "clipboard.write",
        description = "Tier: alterar. Escreve texto na área de transferência local.",
        annotations(destructive_hint = true)
    )]
    async fn clipboard_write(&self, Parameters(args): Parameters<ClipboardArgs>) -> String {
        if args.text.len() > 16_000 {
            return "texto excede o limite".to_string();
        }
        common::run_input("wl-copy", &["--type", "text/plain"], &args.text)
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "screenshot.take",
        description = "Tier: alterar. Salva uma captura em ~/Pictures e avisa antes; requer aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn screenshot_take(&self, Parameters(args): Parameters<ScreenshotArgs>) -> String {
        if !common::valid_atom(args.filename.trim_end_matches(".png"), 80)
            || !args.filename.ends_with(".png")
        {
            return "use um nome simples terminado em .png".to_string();
        }
        let Some(home) = common::home() else {
            return "diretório pessoal indisponível".to_string();
        };
        let directory = home.join("Pictures");
        if !directory.is_dir() {
            return "~/Pictures não existe".to_string();
        }
        let path: PathBuf = directory.join(&args.filename);
        if path.exists() {
            return "o arquivo já existe; escolha outro nome".to_string();
        }
        let path = path.to_string_lossy().to_string();
        if let Err(error) = common::run(
            "notify-send",
            &["ForjaOS", "Captura de tela iniciada pelo HERO"],
        )
        .await
        {
            return format!("não foi possível avisar antes da captura: {error}");
        }
        common::run("spectacle", &["-b", "-n", "-o", &path])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "apps.launch",
        description = "Tier: alterar. Abre aplicativo instalado pelo desktop ID.",
        annotations(destructive_hint = true)
    )]
    async fn apps_launch(&self, Parameters(args): Parameters<AppArgs>) -> String {
        if !common::valid_atom(&args.desktop_id, 128) {
            return "desktop ID inválido".to_string();
        }
        common::run("gtk-launch", &[&args.desktop_id])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "url.open",
        description = "Tier: alterar. Abre uma URL HTTP/HTTPS no navegador padrão.",
        annotations(destructive_hint = true)
    )]
    async fn url_open(&self, Parameters(args): Parameters<UrlArgs>) -> String {
        let valid = (args.url.starts_with("https://") || args.url.starts_with("http://"))
            && args.url.len() <= 2048
            && !args
                .url
                .chars()
                .any(|character| character.is_whitespace() || character.is_control());
        if !valid {
            return "URL HTTP/HTTPS inválida".to_string();
        }
        common::run("xdg-open", &[&args.url])
            .await
            .unwrap_or_else(|error| error)
    }
}
