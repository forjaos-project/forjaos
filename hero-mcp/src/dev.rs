use crate::common;
use rmcp::{
    handler::server::router::tool::ToolRouter, handler::server::wrapper::Parameters, tool,
    tool_router,
};
use schemars::JsonSchema;
use serde::Deserialize;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

pub struct DevServer {
    #[allow(dead_code)]
    tool_router: ToolRouter<Self>,
}

impl Default for DevServer {
    fn default() -> Self {
        Self {
            tool_router: Self::tool_router(),
        }
    }
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ProjectArgs {
    #[schemars(length(max = 64))]
    project: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ComposeArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(extend("enum" = ["podman", "docker"]))]
    backend: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct BackendArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(extend("enum" = ["podman", "docker"]))]
    backend: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct ContainerArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(length(max = 128))]
    container: String,
    #[schemars(extend("enum" = ["podman", "docker"]))]
    backend: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct BranchArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(length(max = 128))]
    branch: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
struct CommitArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(length(max = 500))]
    message: String,
}

#[derive(Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
#[allow(dead_code)]
struct AgentArgs {
    #[schemars(length(max = 64))]
    project: String,
    #[schemars(extend("enum" = ["claude-code", "codex", "hermes"]))]
    agent: String,
    #[schemars(length(max = 4000))]
    task: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProjectConfig {
    #[serde(default)]
    projects: Vec<ProjectEntry>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ProjectEntry {
    name: String,
    path: PathBuf,
}

fn project_roots() -> Vec<PathBuf> {
    let Some(home) = common::home() else {
        return Vec::new();
    };
    ["proj", "dev", "code"]
        .map(|name| home.join(name))
        .into_iter()
        .collect()
}

fn known_projects() -> BTreeMap<String, PathBuf> {
    let Some(home) = common::home() else {
        return BTreeMap::new();
    };
    let mut projects = BTreeMap::new();
    let config_path = home.join(".config/hero/projects.toml");
    if let Ok(source) = fs::read_to_string(config_path) {
        if let Ok(config) = toml::from_str::<ProjectConfig>(&source) {
            for project in config.projects {
                if common::valid_atom(&project.name, 64) {
                    let path = if project.path.is_absolute() {
                        project.path
                    } else {
                        home.join(project.path)
                    };
                    if let Ok(path) = canonical_project(&path) {
                        projects.insert(project.name, path);
                    }
                }
            }
        }
    }
    for root in project_roots() {
        let Ok(root) = root.canonicalize() else {
            continue;
        };
        let Ok(entries) = fs::read_dir(&root) else {
            continue;
        };
        for entry in entries.flatten() {
            let candidate = entry.path();
            add_detected_project(&mut projects, &candidate, &root);
            if let Ok(children) = fs::read_dir(&candidate) {
                for child in children.flatten() {
                    add_detected_project(&mut projects, &child.path(), &root);
                }
            }
        }
    }
    projects
}

fn canonical_project(path: &Path) -> Result<PathBuf, ()> {
    let canonical = path.canonicalize().map_err(|_| ())?;
    if !canonical.is_dir() {
        return Err(());
    }
    Ok(canonical)
}

fn is_git_project(path: &Path) -> bool {
    path.join(".git").exists()
}

fn add_detected_project(projects: &mut BTreeMap<String, PathBuf>, path: &Path, root: &Path) {
    let Ok(canonical) = canonical_project(path) else {
        return;
    };
    if !canonical.starts_with(root) || !is_git_project(&canonical) {
        return;
    }
    let Some(name) = canonical.file_name().and_then(|name| name.to_str()) else {
        return;
    };
    projects.entry(name.to_string()).or_insert(canonical);
}

fn project_path(name: &str) -> Result<PathBuf, String> {
    known_projects().remove(name).ok_or_else(|| {
        "projeto não cadastrado em projects.toml nem detectado em ~/proj, ~/dev ou ~/code"
            .to_string()
    })
}

fn backend_program(backend: &str) -> Option<&'static str> {
    match backend {
        "podman" => Some("podman"),
        "docker" => Some("docker"),
        _ => None,
    }
}

fn compose_file(path: &Path) -> Option<PathBuf> {
    [
        "compose.yaml",
        "compose.yml",
        "docker-compose.yaml",
        "docker-compose.yml",
    ]
    .iter()
    .map(|file| path.join(file))
    .find(|file| file.is_file())
}

fn branch_valid(branch: &str) -> bool {
    branch.len() <= 128
        && branch
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphanumeric)
        && !branch.starts_with('-')
        && !branch.contains("..")
        && !branch.contains("//")
        && !branch.ends_with('/')
        && !branch.ends_with(".lock")
        && branch
            .chars()
            .all(|character| character.is_ascii_alphanumeric() || "._/-".contains(character))
}

#[tool_router(server_handler)]
impl DevServer {
    #[tool(
        name = "projects.list",
        description = "Tier: livre. Lista apenas projetos cadastrados ou detectados nas raízes permitidas.",
        annotations(read_only_hint = true)
    )]
    async fn projects_list(&self) -> String {
        let projects = known_projects();
        if projects.is_empty() {
            return "nenhum projeto cadastrado".to_string();
        }
        projects
            .into_iter()
            .map(|(name, path)| format!("{name}\t{}", path.display()))
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[tool(
        name = "project.open",
        description = "Tier: alterar. Abre um projeto conhecido no gerenciador de arquivos.",
        annotations(destructive_hint = false)
    )]
    async fn project_open(&self, Parameters(args): Parameters<ProjectArgs>) -> String {
        let Ok(path) = project_path(&args.project) else {
            return "projeto não cadastrado".to_string();
        };
        common::run("xdg-open", &[path.to_string_lossy().as_ref()])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "compose.up",
        description = "Tier: alterar. Sobe Compose no projeto conhecido; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn compose_up(&self, Parameters(args): Parameters<ComposeArgs>) -> String {
        self.compose(&args.project, &args.backend, "up").await
    }

    #[tool(
        name = "compose.down",
        description = "Tier: alterar. Derruba Compose no projeto conhecido; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn compose_down(&self, Parameters(args): Parameters<ComposeArgs>) -> String {
        self.compose(&args.project, &args.backend, "down").await
    }

    #[tool(
        name = "compose.logs",
        description = "Tier: livre. Mostra logs do Compose no projeto conhecido.",
        annotations(read_only_hint = true)
    )]
    async fn compose_logs(&self, Parameters(args): Parameters<ComposeArgs>) -> String {
        let Ok(path) = project_path(&args.project) else {
            return "projeto não cadastrado".to_string();
        };
        let Some(program) = backend_program(&args.backend) else {
            return "backend inválido".to_string();
        };
        let Some(file) = compose_file(&path) else {
            return "arquivo Compose não encontrado".to_string();
        };
        let file = file.to_string_lossy().to_string();
        common::run(
            program,
            &[
                "compose",
                "-p",
                &args.project,
                "-f",
                &file,
                "logs",
                "--tail",
                "100",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "containers.list",
        description = "Tier: livre. Lista containers do backend selecionado.",
        annotations(read_only_hint = true)
    )]
    async fn containers_list(&self, Parameters(args): Parameters<BackendArgs>) -> String {
        let Some(program) = backend_program(&args.backend) else {
            return "backend inválido".to_string();
        };
        if !common::valid_atom(&args.project, 64) || project_path(&args.project).is_err() {
            return "projeto não cadastrado".to_string();
        }
        let label = format!("label=com.docker.compose.project={}", args.project);
        common::run(
            program,
            &[
                "ps",
                "--all",
                "--filter",
                &label,
                "--format",
                "{{.ID}}\t{{.Names}}",
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "containers.logs",
        description = "Tier: livre. Lê logs recentes de um container pelo ID/nome.",
        annotations(read_only_hint = true)
    )]
    async fn containers_logs(&self, Parameters(args): Parameters<ContainerArgs>) -> String {
        let Some(program) = backend_program(&args.backend) else {
            return "backend inválido".to_string();
        };
        if !common::valid_atom(&args.project, 64) || project_path(&args.project).is_err() {
            return "projeto não cadastrado".to_string();
        }
        if !common::valid_atom(&args.container, 128) {
            return "identificador de container inválido".to_string();
        }
        let label = format!("label=com.docker.compose.project={}", args.project);
        let members = common::run(
            program,
            &[
                "ps",
                "--all",
                "--filter",
                &label,
                "--format",
                "{{.ID}}\t{{.Names}}",
            ],
        )
        .await
        .unwrap_or_else(|error| return error);
        let member = members.lines().any(|line| {
            line.split_once('\t')
                .is_some_and(|(id, name)| args.container == id || args.container == name)
        });
        if !member {
            return "container não pertence ao projeto cadastrado".to_string();
        }
        common::run(program, &["logs", "--tail", "100", &args.container])
            .await
            .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "git.status",
        description = "Tier: livre. Consulta status Git do projeto cadastrado.",
        annotations(read_only_hint = true)
    )]
    async fn git_status(&self, Parameters(args): Parameters<ProjectArgs>) -> String {
        self.git_read(&args.project, "status", &[]).await
    }

    #[tool(
        name = "git.log",
        description = "Tier: livre. Consulta os últimos commits do projeto cadastrado.",
        annotations(read_only_hint = true)
    )]
    async fn git_log(&self, Parameters(args): Parameters<ProjectArgs>) -> String {
        self.git_read(
            &args.project,
            "log",
            &["-n", "20", "--oneline", "--decorate"],
        )
        .await
    }

    #[tool(
        name = "git.diff",
        description = "Tier: livre. Consulta resumo das diferenças Git do projeto cadastrado.",
        annotations(read_only_hint = true)
    )]
    async fn git_diff(&self, Parameters(args): Parameters<ProjectArgs>) -> String {
        self.git_read(&args.project, "diff", &["--stat"]).await
    }

    #[tool(
        name = "git.branch.create",
        description = "Tier: alterar. Cria branch no projeto conhecido; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn git_branch_create(&self, Parameters(args): Parameters<BranchArgs>) -> String {
        if !branch_valid(&args.branch) {
            return "nome de branch inválido".to_string();
        }
        let Ok(path) = project_path(&args.project) else {
            return "projeto não cadastrado".to_string();
        };
        common::run(
            "git",
            &[
                "-C",
                path.to_string_lossy().as_ref(),
                "switch",
                "-c",
                &args.branch,
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "git.commit",
        description = "Tier: alterar. Cria commit somente com o índice já staged; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn git_commit(&self, Parameters(args): Parameters<CommitArgs>) -> String {
        if args.message.trim().is_empty()
            || args.message.len() > 500
            || args.message.chars().any(char::is_control)
        {
            return "mensagem de commit inválida".to_string();
        }
        let Ok(path) = project_path(&args.project) else {
            return "projeto não cadastrado".to_string();
        };
        common::run(
            "git",
            &[
                "-C",
                path.to_string_lossy().as_ref(),
                "commit",
                "-m",
                &args.message,
            ],
        )
        .await
        .unwrap_or_else(|error| error)
    }

    #[tool(
        name = "tests.run",
        description = "Tier: alterar. Executa a suíte padrão detectada no projeto; o cliente MCP deve solicitar aprovação.",
        annotations(destructive_hint = true)
    )]
    async fn tests_run(&self, Parameters(args): Parameters<ProjectArgs>) -> String {
        let Ok(path) = project_path(&args.project) else {
            return "projeto não cadastrado".to_string();
        };
        let cwd = path.to_string_lossy().to_string();
        let (program, args): (&str, &[&str]) = if path.join("Cargo.toml").is_file() {
            ("cargo", &["test"])
        } else if path.join("pnpm-lock.yaml").is_file() {
            ("pnpm", &["test"])
        } else if path.join("package-lock.json").is_file() {
            ("npm", &["test"])
        } else if path.join("go.mod").is_file() {
            ("go", &["test", "./..."])
        } else if path.join("pyproject.toml").is_file() {
            ("python", &["-m", "pytest"])
        } else {
            return "manifesto de testes não reconhecido".to_string();
        };
        let mut command = tokio::process::Command::new(program);
        command.args(args).current_dir(cwd).kill_on_drop(true);
        match tokio::time::timeout(std::time::Duration::from_secs(300), command.output()).await {
            Ok(Ok(output)) if output.status.success() => "suíte concluída com sucesso".to_string(),
            Ok(Ok(_)) => "a suíte falhou; saída detalhada foi omitida".to_string(),
            _ => "não foi possível concluir a suíte de testes".to_string(),
        }
    }

    #[tool(
        name = "terminal.spawn_agent",
        description = "Tier: bloqueado. Agentes autônomos não são iniciados pelo servidor MCP.",
        annotations(destructive_hint = true)
    )]
    async fn terminal_spawn_agent(&self, Parameters(_args): Parameters<AgentArgs>) -> String {
        "bloqueado por segurança: o servidor MCP não executa agentes autônomos; abra o agente escolhido manualmente no projeto cadastrado".to_string()
    }
}

impl DevServer {
    async fn compose(&self, project: &str, backend: &str, action: &str) -> String {
        let Some(program) = backend_program(backend) else {
            return "backend inválido".to_string();
        };
        let Ok(path) = project_path(project) else {
            return "projeto não cadastrado".to_string();
        };
        let Some(file) = compose_file(&path) else {
            return "arquivo Compose não encontrado".to_string();
        };
        let file = file.to_string_lossy().to_string();
        if action == "up" {
            common::run(
                program,
                &["compose", "-p", project, "-f", &file, "up", "-d"],
            )
            .await
            .unwrap_or_else(|error| error)
        } else {
            common::run(program, &["compose", "-p", project, "-f", &file, "down"])
                .await
                .unwrap_or_else(|error| error)
        }
    }

    async fn git_read(&self, project: &str, subcommand: &str, rest: &[&str]) -> String {
        let Ok(path) = project_path(project) else {
            return "projeto não cadastrado".to_string();
        };
        let path = path.to_string_lossy().to_string();
        let mut args = vec!["-C", path.as_str(), subcommand];
        args.extend_from_slice(rest);
        common::run("git", &args)
            .await
            .unwrap_or_else(|error| error)
    }
}
