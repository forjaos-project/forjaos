use chrono::{Local, Utc};
mod mcp;
use regex::Regex;
use rusqlite::{ffi::sqlite3_auto_extension, params, Connection, OptionalExtension};
use serde::Serialize;
use serde_json::json;
use sqlite_vec::sqlite3_vec_init;
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::{Mutex, Once};
use std::time::Duration;
use zbus::{connection, fdo, interface};

const BUS_NAME: &str = "org.forjaos.Memory";
const OBJECT_PATH: &str = "/org/forjaos/Memory";
const MAX_NOTE_BYTES: usize = 64 * 1024;
const EMBEDDING_MODEL: &str = "nomic-embed-text:latest";
const EMBEDDING_DIMENSIONS: usize = 768;
const OLLAMA_TAGS_URL: &str = "http://127.0.0.1:11434/api/tags";
const OLLAMA_EMBED_URL: &str = "http://127.0.0.1:11434/api/embed";
static SQLITE_VEC: Once = Once::new();
static CONFIG_LOCK: Mutex<()> = Mutex::new(());
const COLLECTORS: &[&str] = &["shell", "git", "hero", "windows", "code", "notes"];
const AUTOMATIC_COLLECTORS: &[&str] = &["shell", "git", "hero"];
const AVAILABLE_COLLECTORS: &[&str] = &["shell", "git", "hero", "windows", "code", "notes"];

#[derive(serde::Deserialize)]
struct EmbeddingReply {
    embeddings: Vec<Vec<f32>>,
}

#[derive(serde::Deserialize)]
struct OllamaTags {
    models: Vec<OllamaTag>,
}

#[derive(serde::Deserialize)]
struct OllamaTag {
    name: String,
}

#[derive(Clone)]
struct StorePaths {
    vault: PathBuf,
    index: PathBuf,
    config: PathBuf,
}

#[derive(Serialize)]
struct SearchHit {
    id: String,
    path: String,
    title: String,
    excerpt: String,
    modified_at: i64,
}

#[derive(Serialize, serde::Deserialize)]
struct GraphDocument {
    graph: GraphMetadata,
    nodes: Vec<GraphNode>,
    links: Vec<GraphLink>,
    hyperedges: Vec<serde_json::Value>,
}

#[derive(Serialize, serde::Deserialize)]
struct GraphMetadata {
    schema_version: u32,
    graphify_version: String,
}

#[derive(Clone, Serialize, serde::Deserialize)]
struct GraphNode {
    id: String,
    label: String,
    source_file: String,
    node_type: String,
    modified_at: i64,
}

#[derive(Clone, Serialize, serde::Deserialize)]
struct GraphLink {
    source: String,
    target: String,
    relation: String,
    confidence: String,
    confidence_score: f32,
}

impl StorePaths {
    fn from_environment() -> Result<Self, String> {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .ok_or_else(|| "HOME não está definido".to_string())?;
        let data = std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.join(".local/share"));
        Ok(Self {
            vault: home.join("ForjaOS/vault"),
            index: data.join("hero/memory.db"),
            config: std::env::var_os("XDG_CONFIG_HOME")
                .map(PathBuf::from)
                .unwrap_or_else(|| home.join(".config"))
                .join("hero/memory.toml"),
        })
    }

    fn initialize(&self) -> Result<(), String> {
        for directory in [
            self.vault.clone(),
            self.vault.join("daily"),
            self.vault.join("projects"),
            self.vault.join("hero"),
            self.vault.join("graph"),
            self.vault.join("notes"),
            self.config
                .parent()
                .ok_or_else(|| "caminho da configuração inválido".to_string())?
                .to_path_buf(),
            self.index
                .parent()
                .ok_or_else(|| "caminho do índice inválido".to_string())?
                .to_path_buf(),
        ] {
            fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
            restrict_directory(&directory)?;
        }
        if !self.config.exists() {
            self.write_default_config()?;
        }
        let connection = self.open()?;
        restrict_file(&self.index)?;
        connection
            .execute_batch(
                "PRAGMA journal_mode=WAL;
                 PRAGMA synchronous=NORMAL;
                 CREATE TABLE IF NOT EXISTS notes (
                     rowid INTEGER PRIMARY KEY,
                     id TEXT NOT NULL UNIQUE,
                     path TEXT NOT NULL,
                     modified_at INTEGER NOT NULL
                 );
                 CREATE VIRTUAL TABLE IF NOT EXISTS note_search USING fts5(
                     id UNINDEXED, path UNINDEXED, title, content,
                     tokenize='unicode61 remove_diacritics 2'
                 );
                 CREATE VIRTUAL TABLE IF NOT EXISTS note_vectors USING vec0(
                     note_rowid INTEGER PRIMARY KEY,
                     embedding float[768] distance_metric=cosine
                 );
                 CREATE TABLE IF NOT EXISTS git_repositories (
                     path TEXT PRIMARY KEY,
                     last_seen_commit TEXT NOT NULL
                 );",
            )
            .map_err(|error| error.to_string())?;
        Ok(())
    }

    fn write_default_config(&self) -> Result<(), String> {
        let _guard = CONFIG_LOCK.lock().map_err(|error| error.to_string())?;
        if self.config.exists() {
            return Ok(());
        }
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&self.config)
            .map_err(|error| error.to_string())?;
        restrict_file(&self.config)?;
        file.write_all(
            b"[collectors]\nshell = true\ngit = true\nhero = true\nwindows = false\ncode = false\nnotes = false\n\n[retention_days]\nshell = 365\ngit = 0\nhero = 0\nwindows = 90\ncode = 0\nnotes = 0\n",
        )
        .map_err(|error| error.to_string())?;
        file.sync_all().map_err(|error| error.to_string())
    }

    fn config_values(&self) -> Result<HashMap<String, String>, String> {
        let contents = fs::read_to_string(&self.config).map_err(|error| error.to_string())?;
        let mut section = String::new();
        let mut values = HashMap::new();
        for raw_line in contents.lines() {
            let line = raw_line.split('#').next().unwrap_or("").trim();
            if line.is_empty() {
                continue;
            }
            if line.starts_with('[') && line.ends_with(']') {
                section = line[1..line.len() - 1].trim().to_string();
                continue;
            }
            if let Some((key, value)) = line.split_once('=') {
                values.insert(
                    format!("{section}.{}", key.trim()),
                    value.trim().to_string(),
                );
            }
        }
        Ok(values)
    }

    fn save_config_values(&self, values: &HashMap<String, String>) -> Result<(), String> {
        let mut contents = String::from("[collectors]\n");
        for source in COLLECTORS {
            let value = values
                .get(&format!("collectors.{source}"))
                .map(String::as_str)
                .unwrap_or(if AUTOMATIC_COLLECTORS.contains(source) {
                    "true"
                } else {
                    "false"
                });
            if !matches!(value, "true" | "false") {
                return Err(format!("valor inválido para collector {source}"));
            }
            contents.push_str(&format!("{source} = {value}\n"));
        }
        contents.push_str("\n[retention_days]\n");
        for source in COLLECTORS {
            let default = if *source == "shell" {
                "365"
            } else if *source == "windows" {
                "90"
            } else {
                "0"
            };
            let value = values
                .get(&format!("retention_days.{source}"))
                .map(String::as_str)
                .unwrap_or(default);
            if value.parse::<u32>().map_or(true, |days| days > 36_500) {
                return Err(format!("retenção inválida para {source}"));
            }
            contents.push_str(&format!("{source} = {value}\n"));
        }
        let temporary = self.config.with_extension("toml.tmp");
        let mut file = OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .open(&temporary)
            .map_err(|error| error.to_string())?;
        file.write_all(contents.as_bytes())
            .map_err(|error| error.to_string())?;
        file.sync_all().map_err(|error| error.to_string())?;
        restrict_file(&temporary)?;
        fs::rename(temporary, &self.config).map_err(|error| error.to_string())
    }

    fn collectors(&self) -> Result<Vec<serde_json::Value>, String> {
        self.initialize()?;
        let values = self.config_values()?;
        Ok(COLLECTORS
            .iter()
            .map(|source| {
                let enabled = values
                    .get(&format!("collectors.{source}"))
                    .is_some_and(|value| value == "true");
                let retention_days = values
                    .get(&format!("retention_days.{source}"))
                    .and_then(|value| value.parse::<u32>().ok())
                    .unwrap_or(0);
                json!({
                    "source":source,
                    "enabled":enabled,
                    "available":collector_available(source),
                    "retention_days":retention_days
                })
            })
            .collect())
    }

    fn set_collector(&self, source: &str, enabled: bool) -> Result<(), String> {
        if !AVAILABLE_COLLECTORS.contains(&source) {
            return Err("coletor não disponível nesta versão".into());
        }
        if source == "code" && enabled && !command_available("graphify") {
            return Err(
                "Graphify não está instalado; instale o pacote oficial `graphifyy` com uv".into(),
            );
        }
        self.initialize()?;
        {
            let _guard = CONFIG_LOCK.lock().map_err(|error| error.to_string())?;
            let mut values = self.config_values()?;
            values.insert(format!("collectors.{source}"), enabled.to_string());
            self.save_config_values(&values)?;
        }
        if source == "git" {
            self.refresh_git_cursors()?;
        }
        if source == "notes" {
            self.rebuild()?;
        }
        if source == "code" {
            self.rebuild()?;
        }
        Ok(())
    }

    fn graph_repository(&self, path: &str) -> Result<serde_json::Value, String> {
        self.initialize()?;
        let values = self.config_values()?;
        if !values
            .get("collectors.code")
            .is_some_and(|value| value == "true")
        {
            return Err(
                "coletor code desativado; habilite com `forja memory collectors enable code`"
                    .into(),
            );
        }
        if !command_available("graphify") {
            return Err(
                "Graphify não está instalado; instale o pacote oficial `graphifyy` com uv".into(),
            );
        }

        let root = Path::new(path)
            .canonicalize()
            .map_err(|error| format!("repositório inválido: {error}"))?;
        if !root.is_dir() {
            return Err("o caminho informado não é um diretório".into());
        }
        let root_text = root.to_string_lossy().into_owned();
        let git_root = git_output(&root_text, &["rev-parse", "--show-toplevel"])?;
        let git_root = Path::new(&git_root)
            .canonicalize()
            .map_err(|error| format!("raiz Git inválida: {error}"))?;
        if git_root != root {
            return Err(format!(
                "informe a raiz do repositório Git: {}",
                git_root.display()
            ));
        }

        let output_root = self.vault.join("graph/code").join(repository_key(&root)?);
        fs::create_dir_all(&output_root).map_err(|error| error.to_string())?;
        restrict_directory(&self.vault.join("graph/code"))?;
        restrict_directory(&output_root)?;
        let graphify = command_path("graphify").ok_or_else(|| {
            "Graphify não está instalado; use `uv tool install graphifyy`".to_string()
        })?;
        let output = Command::new("timeout")
            .args(["--signal=TERM", "--kill-after=15s", "1800s"])
            .arg(graphify)
            .env("GRAPHIFY_BACKEND", "none")
            .arg("extract")
            .arg(&root)
            .args(["--code-only", "--no-viz", "--out"])
            .arg(&output_root)
            .output()
            .map_err(|error| format!("graphify indisponível ou falhou ao iniciar: {error}"))?;
        if !output.status.success() {
            if output.status.code() == Some(124) || output.status.code() == Some(137) {
                return Err("Graphify excedeu o limite de 30 minutos".into());
            }
            let detail = String::from_utf8_lossy(&output.stderr).trim().to_string();
            return Err(if detail.is_empty() {
                format!("graphify terminou com {}", output.status)
            } else {
                format!("graphify falhou: {detail}")
            });
        }
        restrict_tree(&output_root)?;
        let graph_path = output_root.join("graphify-out/graph.json");
        let graph_metadata = fs::symlink_metadata(&graph_path)
            .map_err(|_| "graphify terminou sem produzir graphify-out/graph.json".to_string())?;
        if !graph_metadata.is_file() || graph_metadata.file_type().is_symlink() {
            return Err("a saída graphify/graph.json não é um arquivo regular".into());
        }
        if graph_metadata.len() > 100 * 1024 * 1024 {
            return Err("o grafo excede o limite de 100 MiB".into());
        }
        let graph: serde_json::Value =
            serde_json::from_slice(&fs::read(&graph_path).map_err(|error| error.to_string())?)
                .map_err(|error| format!("graphify gerou JSON inválido: {error}"))?;
        let nodes = graph["nodes"].as_array().map_or(0, Vec::len);
        let links = graph["links"].as_array().map_or(0, Vec::len);
        if !graph["nodes"].is_array() || !graph["links"].is_array() {
            return Err("graphify gerou um grafo sem arrays nodes e links".into());
        }
        restrict_file(&graph_path)?;
        self.rebuild()?;
        Ok(json!({
            "status":"ok",
            "repository":root.to_string_lossy(),
            "path":graph_path.strip_prefix(&self.vault).unwrap_or(&graph_path).to_string_lossy().replace('\\', "/"),
            "nodes":nodes,
            "links":links,
            "local_only":true
        }))
    }

    fn set_retention(&self, source: &str, days: u32) -> Result<(), String> {
        if !COLLECTORS.contains(&source) || days > 36_500 {
            return Err("coletor inválido ou retenção superior a 100 anos".into());
        }
        self.initialize()?;
        let _guard = CONFIG_LOCK.lock().map_err(|error| error.to_string())?;
        let mut values = self.config_values()?;
        values.insert(format!("retention_days.{source}"), days.to_string());
        self.save_config_values(&values)
    }

    fn collect_event(
        &self,
        source: &str,
        detail: &str,
        cwd: &str,
        exit_code: i32,
        duration_ms: u64,
    ) -> Result<String, String> {
        if !AVAILABLE_COLLECTORS.contains(&source) {
            return Err("coletor não disponível nesta versão".into());
        }
        if detail.trim().is_empty() || detail.len() > MAX_NOTE_BYTES || cwd.len() > 4096 {
            return Err("evento vazio ou maior que o limite permitido".into());
        }
        self.initialize()?;
        let values = self.config_values()?;
        if !values
            .get(&format!("collectors.{source}"))
            .is_some_and(|value| value == "true")
        {
            return Err("coletor desativado".into());
        }
        let safe_detail = markdown_inline(&redact_secrets(detail));
        let safe_cwd = markdown_inline(&redact_secrets(cwd));
        let now = Local::now();
        let date = now.format("%Y-%m-%d").to_string();
        let directory = self.vault.join("daily/collectors").join(source).join(&date);
        fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
        restrict_directory(&directory)?;
        let stamp = now.format("%H%M%S").to_string();
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|error| error.to_string())?
            .as_nanos();
        let path = directory.join(format!("{stamp}-{nonce}.md"));
        let title = format!("{} · {stamp}", source.to_uppercase());
        let body = format!(
            "---\ntitle: {}\nsource: collector-{source}\ncreated_at: \"{}\"\n---\n\n- cwd: `{safe_cwd}`\n- exit: {exit_code}\n- duration_ms: {duration_ms}\n- detail: `{safe_detail}`\n",
            markdown_inline(&title),
            now.to_rfc3339()
        );
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&path)
            .map_err(|error| error.to_string())?;
        restrict_file(&path)?;
        file.write_all(body.as_bytes())
            .map_err(|error| error.to_string())?;
        file.sync_all().map_err(|error| error.to_string())?;
        self.index_markdown(&path)?;
        self.update_event_graph(&path)?;
        if source == "git" {
            self.advance_git_cursor_from_event(cwd, detail)?;
        }
        path.strip_prefix(&self.vault)
            .map(|path| path.to_string_lossy().replace('\\', "/"))
            .map_err(|error| error.to_string())
    }

    fn advance_git_cursor_from_event(&self, cwd: &str, detail: &str) -> Result<(), String> {
        let Some((commit, _)) = detail.split_once('\t') else {
            return Ok(());
        };
        if !matches!(commit.len(), 40 | 64) || !commit.bytes().all(|byte| byte.is_ascii_hexdigit())
        {
            return Ok(());
        }
        let root_output = Command::new("git")
            .args(["-C", cwd, "rev-parse", "--show-toplevel"])
            .output()
            .map_err(|error| error.to_string())?;
        if !root_output.status.success() {
            return Ok(());
        }
        let root = PathBuf::from(String::from_utf8_lossy(&root_output.stdout).trim())
            .canonicalize()
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .to_string();
        let reference = format!("{commit}^{{commit}}");
        if git_output(&root, &["cat-file", "-e", &reference]).is_err() {
            return Ok(());
        }
        self.open()?
            .execute(
                "UPDATE git_repositories SET last_seen_commit = ?1 WHERE path = ?2",
                params![commit, root],
            )
            .map_err(|error| error.to_string())?;
        Ok(())
    }

    fn register_git_repository(&self, path: &str) -> Result<String, String> {
        if path.trim().is_empty() || path.len() > 4096 {
            return Err("caminho de repositório vazio ou acima de 4096 bytes".into());
        }
        self.initialize()?;
        let root_output = Command::new("git")
            .args(["-C", path, "rev-parse", "--show-toplevel"])
            .output()
            .map_err(|error| error.to_string())?;
        if !root_output.status.success() {
            return Err("o caminho informado não pertence a um repositório Git".into());
        }
        let root = PathBuf::from(String::from_utf8_lossy(&root_output.stdout).trim())
            .canonicalize()
            .map_err(|error| error.to_string())?;
        let root = root.to_string_lossy().to_string();
        let head = match git_output(&root, &["rev-parse", "--verify", "HEAD"]) {
            Ok(head) => head,
            Err(_)
                if git_output(&root, &["rev-parse", "--is-inside-work-tree"])
                    .is_ok_and(|value| value == "true") =>
            {
                String::new()
            }
            Err(error) => return Err(error),
        };
        let connection = self.open()?;
        let inserted = connection
            .execute(
                "INSERT OR IGNORE INTO git_repositories(path, last_seen_commit) VALUES (?1, ?2)",
                params![root, head],
            )
            .map_err(|error| error.to_string())?
            > 0;
        Ok(json!({"status":"ok", "repository":root, "registered":inserted}).to_string())
    }

    fn unregister_git_repository(&self, path: &str) -> Result<String, String> {
        if path.trim().is_empty() || path.len() > 4096 {
            return Err("caminho de repositório vazio ou acima de 4096 bytes".into());
        }
        self.initialize()?;
        let requested = PathBuf::from(path);
        let resolved = if let Ok(canonical) = requested.canonicalize() {
            canonical
        } else if requested.is_absolute() {
            requested
        } else {
            return Err("para remover um repositório ausente, informe o caminho absoluto".into());
        };
        let resolved = resolved.to_string_lossy().to_string();
        let root_output = Command::new("git")
            .args(["-C", &resolved, "rev-parse", "--show-toplevel"])
            .output();
        let root = match root_output {
            Ok(output) if output.status.success() => {
                PathBuf::from(String::from_utf8_lossy(&output.stdout).trim())
                    .canonicalize()
                    .unwrap_or_else(|_| PathBuf::from(&resolved))
                    .to_string_lossy()
                    .to_string()
            }
            _ => resolved,
        };
        let connection = self.open()?;
        let removed = connection
            .execute("DELETE FROM git_repositories WHERE path = ?1", [&root])
            .map_err(|error| error.to_string())?
            > 0;
        Ok(json!({"status":"ok", "repository":root, "unregistered":removed}).to_string())
    }

    fn scan_git_repositories(&self) -> Result<String, String> {
        self.initialize()?;
        let values = self.config_values()?;
        if !values
            .get("collectors.git")
            .is_some_and(|value| value == "true")
        {
            return Ok(json!({
                "status":"disabled",
                "repositories":0,
                "commits_recorded":0,
                "errors":[]
            })
            .to_string());
        }
        let repositories = {
            let connection = self.open()?;
            let mut statement = connection
                .prepare("SELECT path, last_seen_commit FROM git_repositories ORDER BY path")
                .map_err(|error| error.to_string())?;
            let repositories = statement
                .query_map([], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
                })
                .map_err(|error| error.to_string())?
                .collect::<Result<Vec<_>, _>>()
                .map_err(|error| error.to_string())?;
            repositories
        };
        let mut scanned = 0usize;
        let mut errors = Vec::new();
        for (root, last_seen) in &repositories {
            let result = self.scan_git_repository(root, last_seen);
            match result {
                Ok(count) => scanned += count,
                Err(error) => errors.push(json!({"repository":root, "error":error})),
            }
        }
        Ok(json!({
            "status": if errors.is_empty() { "ok" } else { "partial" },
            "repositories": repositories.len(),
            "commits_recorded": scanned,
            "errors": errors
        })
        .to_string())
    }

    fn refresh_git_cursors(&self) -> Result<(), String> {
        let repositories = {
            let connection = self.open()?;
            let mut statement = connection
                .prepare("SELECT path FROM git_repositories ORDER BY path")
                .map_err(|error| error.to_string())?;
            let repositories = statement
                .query_map([], |row| row.get::<_, String>(0))
                .map_err(|error| error.to_string())?
                .collect::<Result<Vec<_>, _>>()
                .map_err(|error| error.to_string())?;
            repositories
        };
        for root in repositories {
            let head = match git_output(&root, &["rev-parse", "--verify", "HEAD"]) {
                Ok(head) => head,
                Err(_) => {
                    self.open()?
                        .execute("DELETE FROM git_repositories WHERE path = ?1", [&root])
                        .map_err(|error| error.to_string())?;
                    continue;
                }
            };
            self.open()?
                .execute(
                    "UPDATE git_repositories SET last_seen_commit = ?1 WHERE path = ?2",
                    params![head, root],
                )
                .map_err(|error| error.to_string())?;
        }
        Ok(())
    }

    fn scan_git_repository(&self, root: &str, last_seen: &str) -> Result<usize, String> {
        let head = match git_output(root, &["rev-parse", "--verify", "HEAD"]) {
            Ok(head) => head,
            Err(_)
                if git_output(root, &["rev-parse", "--is-inside-work-tree"])
                    .is_ok_and(|value| value == "true") =>
            {
                return Ok(0);
            }
            Err(error) => return Err(error),
        };
        if head == *last_seen {
            return Ok(0);
        }
        let merge_base = if last_seen.is_empty() {
            None
        } else {
            Command::new("git")
                .args(["-C", root, "merge-base", last_seen, "HEAD"])
                .output()
                .ok()
                .filter(|output| output.status.success())
                .map(|output| String::from_utf8_lossy(&output.stdout).trim().to_string())
        };
        if merge_base.as_deref() == Some(head.as_str()) {
            self.open()?
                .execute(
                    "UPDATE git_repositories SET last_seen_commit = ?1 WHERE path = ?2",
                    params![head, root],
                )
                .map_err(|error| error.to_string())?;
            return Ok(0);
        }
        let output = if let Some(base) = merge_base {
            let range = format!("{base}..HEAD");
            Command::new("git")
                .args([
                    "-C",
                    root,
                    "log",
                    "--reverse",
                    "--format=%H%x09%ct%x09%s",
                    &range,
                ])
                .output()
        } else if last_seen.is_empty() {
            Command::new("git")
                .args(["-C", root, "log", "--reverse", "--format=%H%x09%ct%x09%s"])
                .output()
        } else {
            Command::new("git")
                .args(["-C", root, "log", "-1", "--format=%H%x09%ct%x09%s", "HEAD"])
                .output()
        }
        .map_err(|error| error.to_string())?;
        if !output.status.success() {
            return Err("não foi possível ler commits posteriores ao último cursor".into());
        }
        if output.stdout.len() > 16 * 1024 * 1024 {
            return Err(
                "intervalo Git excede o limite de 16 MiB; nenhum cursor foi alterado".into(),
            );
        }
        let commits = String::from_utf8_lossy(&output.stdout);
        let mut recorded = 0usize;
        for line in commits.lines() {
            let mut fields = line.splitn(3, '\t');
            let Some(commit) = fields.next() else {
                continue;
            };
            let Some(timestamp) = fields.next() else {
                continue;
            };
            let Some(subject) = fields.next() else {
                continue;
            };
            let detail = format!("commit={commit}; timestamp={timestamp}; subject={subject}");
            self.collect_event("git", &detail, root, 0, 0)?;
            self.open()?
                .execute(
                    "UPDATE git_repositories SET last_seen_commit = ?1 WHERE path = ?2",
                    params![commit, root],
                )
                .map_err(|error| error.to_string())?;
            recorded += 1;
        }
        if recorded == 0 && head != *last_seen {
            self.open()?
                .execute(
                    "UPDATE git_repositories SET last_seen_commit = ?1 WHERE path = ?2",
                    params![head, root],
                )
                .map_err(|error| error.to_string())?;
        }
        Ok(recorded)
    }

    fn index_markdown(&self, path: &Path) -> Result<(), String> {
        let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
        let safe_text = redact_secrets(&text);
        let relative = path
            .strip_prefix(&self.vault)
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        let modified_at = path
            .metadata()
            .ok()
            .and_then(|metadata| metadata.modified().ok())
            .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |duration| duration.as_secs() as i64);
        let title = markdown_title(&safe_text, path);
        let connection = self.open()?;
        let transaction = connection
            .unchecked_transaction()
            .map_err(|error| error.to_string())?;
        let existing: Option<i64> = transaction
            .query_row(
                "SELECT rowid FROM notes WHERE id = ?1",
                [&relative],
                |row| row.get(0),
            )
            .optional()
            .map_err(|error| error.to_string())?;
        if let Some(rowid) = existing {
            transaction
                .execute("DELETE FROM note_search WHERE id = ?1", [&relative])
                .and_then(|_| {
                    transaction.execute("DELETE FROM note_vectors WHERE note_rowid = ?1", [rowid])
                })
                .and_then(|_| {
                    transaction.execute(
                        "UPDATE notes SET path = ?1, modified_at = ?2 WHERE rowid = ?3",
                        params![relative, modified_at, rowid],
                    )
                })
                .map_err(|error| error.to_string())?;
        } else {
            transaction
                .execute(
                    "INSERT INTO notes(id, path, modified_at) VALUES (?1, ?1, ?2)",
                    params![relative, modified_at],
                )
                .map_err(|error| error.to_string())?;
        }
        transaction
            .execute(
                "INSERT INTO note_search(id, path, title, content) VALUES (?1, ?2, ?3, ?4)",
                params![relative, relative, title, safe_text],
            )
            .map_err(|error| error.to_string())?;
        transaction.commit().map_err(|error| error.to_string())
    }

    fn update_event_graph(&self, path: &Path) -> Result<(), String> {
        let graph_path = self.vault.join("graph/graph.json");
        let metadata = match fs::symlink_metadata(&graph_path) {
            Ok(metadata) => metadata,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                self.rebuild()?;
                return Ok(());
            }
            Err(error) => return Err(error.to_string()),
        };
        if !metadata.is_file()
            || metadata.file_type().is_symlink()
            || metadata.len() > 100 * 1024 * 1024
        {
            return Err("grafo local ausente, inválido ou acima de 100 MiB".into());
        }
        let graph_bytes = fs::read(&graph_path).map_err(|error| error.to_string())?;
        let mut graph: GraphDocument = match serde_json::from_slice(&graph_bytes) {
            Ok(graph) => graph,
            Err(_) => {
                self.rebuild()?;
                return Ok(());
            }
        };
        let text = fs::read_to_string(path).map_err(|error| error.to_string())?;
        let id = path
            .strip_prefix(&self.vault)
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .replace('\\', "/");
        let modified_at = path
            .metadata()
            .ok()
            .and_then(|metadata| metadata.modified().ok())
            .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |duration| duration.as_secs() as i64);
        let title = markdown_title(&redact_secrets(&text), path);
        graph.nodes.retain(|node| node.id != id);
        graph
            .links
            .retain(|link| link.source != id && link.target != id);
        for other in graph.nodes.iter().filter(|node| {
            matches!(
                node.node_type.as_str(),
                "command" | "commit" | "conversation" | "window"
            ) && node.modified_at.div_euclid(900) == modified_at.div_euclid(900)
        }) {
            graph.links.push(GraphLink {
                source: id.clone(),
                target: other.id.clone(),
                relation: "co_occurs".into(),
                confidence: "EXTRACTED".into(),
                confidence_score: 1.0,
            });
        }
        graph.nodes.push(GraphNode {
            id,
            label: title,
            source_file: path
                .strip_prefix(&self.vault)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/"),
            node_type: memory_node_type(
                &path
                    .strip_prefix(&self.vault)
                    .map_err(|error| error.to_string())?
                    .to_string_lossy(),
            )
            .to_string(),
            modified_at,
        });
        self.write_graph(&graph.nodes, &graph.links)
    }

    fn purge(&self) -> Result<usize, String> {
        self.initialize()?;
        let values = self.config_values()?;
        let now = std::time::SystemTime::now();
        let mut removed = 0;
        for source in COLLECTORS {
            let days = values
                .get(&format!("retention_days.{source}"))
                .and_then(|value| value.parse::<u64>().ok())
                .unwrap_or(0);
            if days == 0 {
                continue;
            }
            let (directory, markdown_only) = match *source {
                "notes" => (self.vault.join("notes"), true),
                "code" => (self.vault.join("graph/code"), false),
                _ => (self.vault.join("daily/collectors").join(source), false),
            };
            let retention = Duration::from_secs(days * 86_400);
            if directory.exists() {
                removed += purge_directory(&directory, now, retention, markdown_only)?;
            }
            if *source == "hero" {
                removed += purge_hero_notes(&self.vault.join("daily"), now, retention)?;
            }
        }
        if removed > 0 {
            let _ = self.rebuild()?;
        }
        Ok(removed)
    }

    fn open(&self) -> Result<Connection, String> {
        SQLITE_VEC.call_once(|| unsafe {
            sqlite3_auto_extension(Some(std::mem::transmute::<
                *const (),
                unsafe extern "C" fn(
                    *mut rusqlite::ffi::sqlite3,
                    *mut *mut i8,
                    *const rusqlite::ffi::sqlite3_api_routines,
                ) -> i32,
            >(sqlite3_vec_init as *const ())));
        });
        let connection = Connection::open(&self.index).map_err(|error| error.to_string())?;
        connection
            .busy_timeout(Duration::from_secs(3))
            .map_err(|error| error.to_string())?;
        Ok(connection)
    }

    fn rebuild(&self) -> Result<(usize, bool), String> {
        self.initialize()?;
        let mut documents = Vec::new();
        let values = self.config_values()?;
        let notes_enabled = values
            .get("collectors.notes")
            .is_some_and(|value| value == "true");
        collect_markdown(&self.vault, &self.vault, notes_enabled, &mut documents)?;
        documents.sort_by(|left, right| left.0.cmp(&right.0));
        let safe_documents = documents
            .iter()
            .map(|(_, text, _)| redact_secrets(text))
            .collect::<Vec<_>>();
        let embeddings = embed_texts(&safe_documents).unwrap_or_default();
        let has_embeddings = embeddings.len() == documents.len() && !documents.is_empty();
        let connection = self.open()?;
        let transaction = connection
            .unchecked_transaction()
            .map_err(|error| error.to_string())?;
        transaction
            .execute("DELETE FROM note_search", [])
            .and_then(|_| transaction.execute("DELETE FROM note_vectors", []))
            .and_then(|_| transaction.execute("DELETE FROM notes", []))
            .map_err(|error| error.to_string())?;
        let mut graph_nodes = Vec::new();
        let mut graph_links = Vec::new();
        let mut aliases: HashMap<String, Vec<String>> = HashMap::new();
        let mut event_windows: BTreeMap<i64, Vec<String>> = BTreeMap::new();
        for (index, (path, _text, modified_at)) in documents.iter().enumerate() {
            let relative = path
                .strip_prefix(&self.vault)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let id = relative.clone();
            let safe_text = &safe_documents[index];
            let title = markdown_title(safe_text, path);
            transaction
                .execute(
                    "INSERT INTO notes(id, path, modified_at) VALUES (?1, ?2, ?3)",
                    params![id, relative, modified_at],
                )
                .map_err(|error| error.to_string())?;
            let note_rowid = transaction.last_insert_rowid();
            transaction
                .execute(
                    "INSERT INTO note_search(id, path, title, content) VALUES (?1, ?2, ?3, ?4)",
                    params![id, relative, title, safe_text],
                )
                .map_err(|error| error.to_string())?;
            if has_embeddings {
                let serialized =
                    serde_json::to_string(&embeddings[index]).map_err(|error| error.to_string())?;
                transaction
                    .execute(
                        "INSERT INTO note_vectors(note_rowid, embedding) VALUES (?1, ?2)",
                        params![note_rowid, serialized],
                    )
                    .map_err(|error| error.to_string())?;
            }
            graph_nodes.push(GraphNode {
                id: id.clone(),
                label: title.clone(),
                source_file: relative.clone(),
                node_type: memory_node_type(&relative).to_string(),
                modified_at: *modified_at,
            });
            if relative.starts_with("daily/collectors/") {
                event_windows
                    .entry(modified_at.div_euclid(900))
                    .or_default()
                    .push(id.clone());
            }
            for alias in [
                title.clone(),
                path.file_stem()
                    .map(|stem| stem.to_string_lossy().to_string())
                    .unwrap_or_default(),
                relative.clone(),
            ] {
                let candidates = aliases.entry(alias_key(&alias)).or_default();
                if !candidates.contains(&id) {
                    candidates.push(id.clone());
                }
            }
        }
        for (index, (path, _text, _)) in documents.iter().enumerate() {
            let source = path
                .strip_prefix(&self.vault)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            for target in wikilinks(&safe_documents[index]) {
                let target_name = target.split(['|', '#']).next().unwrap_or(&target);
                let key = alias_key(target_name);
                if let Some(matches) = aliases.get(&key).filter(|matches| matches.len() == 1) {
                    graph_links.push(GraphLink {
                        source: source.clone(),
                        target: matches[0].clone(),
                        relation: "references".into(),
                        confidence: "EXTRACTED".into(),
                        confidence_score: 1.0,
                    });
                }
            }
        }
        for ids in event_windows.values() {
            if let Some((anchor, related)) = ids.split_first() {
                graph_links.extend(related.iter().map(|target| GraphLink {
                    source: anchor.clone(),
                    target: target.clone(),
                    relation: "co_occurs".into(),
                    confidence: "EXTRACTED".into(),
                    confidence_score: 1.0,
                }));
            }
        }
        let code_enabled = values
            .get("collectors.code")
            .is_some_and(|value| value == "true");
        if code_enabled {
            append_code_graphs(&self.vault, &mut graph_nodes, &mut graph_links)?;
        }
        transaction.commit().map_err(|error| error.to_string())?;
        self.write_graph(&graph_nodes, &graph_links)?;
        Ok((documents.len(), has_embeddings))
    }

    fn write_graph(&self, nodes: &[GraphNode], links: &[GraphLink]) -> Result<(), String> {
        let graph = GraphDocument {
            graph: GraphMetadata {
                schema_version: 1,
                graphify_version: "forjaos-graphify-compatible".into(),
            },
            nodes: nodes.to_vec(),
            links: links.to_vec(),
            hyperedges: Vec::new(),
        };
        let output = self.vault.join("graph/graph.json");
        let temporary = output.with_extension("json.tmp");
        let bytes = serde_json::to_vec_pretty(&graph).map_err(|error| error.to_string())?;
        fs::write(&temporary, bytes).map_err(|error| error.to_string())?;
        restrict_file(&temporary)?;
        fs::rename(&temporary, &output).map_err(|error| error.to_string())?;
        Ok(())
    }

    fn search(&self, query: &str, limit: u32) -> Result<Vec<SearchHit>, String> {
        if query.trim().is_empty() {
            return Err("A busca não pode estar vazia".into());
        }
        let fts_query = query
            .split(|character: char| !character.is_alphanumeric())
            .filter(|term| !term.is_empty())
            .map(|term| format!("\"{}\"", term.replace('"', "\"\"")))
            .collect::<Vec<_>>()
            .join(" AND ");
        if fts_query.is_empty() {
            return Ok(Vec::new());
        }
        let limit = limit.clamp(1, 100);
        let connection = self.open()?;
        let has_vectors: bool = connection
            .query_row(
                "SELECT EXISTS(SELECT 1 FROM note_vectors LIMIT 1)",
                [],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        let mut hits = Vec::new();
        if has_vectors {
            if let Some(mut embeddings) = embed_texts(&[query.to_string()]) {
                if let Some(embedding) = embeddings.pop() {
                    let vector =
                        serde_json::to_string(&embedding).map_err(|error| error.to_string())?;
                    let mut statement = connection
                        .prepare(
                            "SELECT n.id, note_search.path, note_search.title,
                                snippet(note_search, 3, '', '', '…', 18), n.modified_at
                         FROM note_vectors
                         JOIN notes n ON n.rowid = note_vectors.note_rowid
                         JOIN note_search ON note_search.id = n.id
                         WHERE embedding MATCH ?1 AND k = ?2
                         ORDER BY distance",
                        )
                        .map_err(|error| error.to_string())?;
                    let rows = statement
                        .query_map(params![vector, i64::from(limit)], |row| {
                            Ok(SearchHit {
                                id: row.get(0)?,
                                path: row.get(1)?,
                                title: row.get(2)?,
                                excerpt: row.get(3)?,
                                modified_at: row.get(4)?,
                            })
                        })
                        .map_err(|error| error.to_string())?;
                    hits = rows
                        .collect::<Result<Vec<_>, _>>()
                        .map_err(|error| error.to_string())?;
                }
            }
        }
        let mut statement = connection
            .prepare(
                "SELECT n.id, note_search.path, note_search.title, snippet(note_search, 3, '', '', '…', 18), n.modified_at
                 FROM note_search JOIN notes n ON n.id = note_search.id
                 WHERE note_search MATCH ?1 ORDER BY rank LIMIT ?2",
            )
            .map_err(|error| error.to_string())?;
        let rows = statement
            .query_map(params![fts_query, limit], |row| {
                Ok(SearchHit {
                    id: row.get(0)?,
                    path: row.get(1)?,
                    title: row.get(2)?,
                    excerpt: row.get(3)?,
                    modified_at: row.get(4)?,
                })
            })
            .map_err(|error| error.to_string())?;
        for hit in rows
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| error.to_string())?
        {
            if !hits
                .iter()
                .any(|existing: &SearchHit| existing.id == hit.id)
            {
                hits.push(hit);
            }
            if hits.len() >= limit as usize {
                break;
            }
        }
        Ok(hits)
    }

    fn timeline(&self, days: u32, limit: u32) -> Result<Vec<SearchHit>, String> {
        let days = i64::from(days.clamp(1, 3650));
        let since = Utc::now().timestamp() - days * 86_400;
        let connection = self.open()?;
        let mut statement = connection
            .prepare(
                "SELECT n.id, note_search.path, note_search.title, snippet(note_search, 3, '', '', '…', 18), n.modified_at
                 FROM notes n JOIN note_search ON n.id = note_search.id
                 WHERE n.modified_at >= ?1 ORDER BY n.modified_at DESC LIMIT ?2",
            )
            .map_err(|error| error.to_string())?;
        let rows = statement
            .query_map(params![since, i64::from(limit.clamp(1, 500))], |row| {
                Ok(SearchHit {
                    id: row.get(0)?,
                    path: row.get(1)?,
                    title: row.get(2)?,
                    excerpt: row.get(3)?,
                    modified_at: row.get(4)?,
                })
            })
            .map_err(|error| error.to_string())?;
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| error.to_string())
    }

    fn remember(&self, note: &str) -> Result<String, String> {
        let note = note.trim();
        if note.is_empty() || note.len() > MAX_NOTE_BYTES {
            return Err("A nota deve ter entre 1 byte e 64 KiB".into());
        }
        self.initialize()?;
        let date = Local::now().format("%Y-%m-%d").to_string();
        let path = self.vault.join("daily").join(format!("{date}.md"));
        let safe_note = redact_secrets(note);
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)
            .map_err(|error| error.to_string())?;
        if file.metadata().map_err(|error| error.to_string())?.len() == 0 {
            writeln!(file, "---\ntitle: Atividade de {date}\nsource: hero\n---\n")
                .map_err(|error| error.to_string())?;
        }
        writeln!(file, "- {}", safe_note).map_err(|error| error.to_string())?;
        restrict_file(&path)?;
        let _ = self.rebuild()?;
        Ok(path
            .strip_prefix(&self.vault)
            .map_err(|error| error.to_string())?
            .to_string_lossy()
            .replace('\\', "/"))
    }

    fn forget(&self, id: &str) -> Result<(), String> {
        use std::path::Component;

        self.initialize()?;
        let relative = Path::new(id);
        if relative.as_os_str().is_empty()
            || relative.is_absolute()
            || relative
                .extension()
                .is_none_or(|extension| extension != "md")
            || relative
                .components()
                .any(|component| !matches!(component, Component::Normal(_)))
        {
            return Err("ID inválido; informe o caminho relativo de uma nota .md".into());
        }
        let candidate = self.vault.join(relative);
        let metadata = fs::symlink_metadata(&candidate).map_err(|error| error.to_string())?;
        if !metadata.is_file() || metadata.file_type().is_symlink() {
            return Err("o ID não aponta para uma nota regular do vault".into());
        }
        let vault = self
            .vault
            .canonicalize()
            .map_err(|error| error.to_string())?;
        let resolved = candidate
            .canonicalize()
            .map_err(|error| error.to_string())?;
        if !resolved.starts_with(vault) {
            return Err("o ID escapa do vault".into());
        }
        fs::remove_file(resolved).map_err(|error| error.to_string())?;
        self.rebuild().map(|_| ())
    }
}

fn append_code_graphs(
    vault: &Path,
    nodes: &mut Vec<GraphNode>,
    links: &mut Vec<GraphLink>,
) -> Result<(), String> {
    let root = vault.join("graph/code");
    let entries = match fs::read_dir(&root) {
        Ok(entries) => entries,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(error.to_string()),
    };
    let mut repositories = entries
        .map(|entry| entry.map_err(|error| error.to_string()))
        .collect::<Result<Vec<_>, _>>()?;
    repositories.sort_by_key(|entry| entry.file_name());

    for repository in repositories {
        let file_type = repository.file_type().map_err(|error| error.to_string())?;
        if !file_type.is_dir() || file_type.is_symlink() {
            continue;
        }
        let repository_id = repository.file_name().to_string_lossy().into_owned();
        let graph_path = repository.path().join("graphify-out/graph.json");
        let metadata = match fs::symlink_metadata(&graph_path) {
            Ok(metadata) => metadata,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
            Err(error) => return Err(error.to_string()),
        };
        if !metadata.is_file()
            || metadata.file_type().is_symlink()
            || metadata.len() > 100 * 1024 * 1024
        {
            continue;
        }
        let modified_at = metadata
            .modified()
            .ok()
            .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
            .map_or(0, |duration| duration.as_secs() as i64);
        let graph: serde_json::Value =
            serde_json::from_slice(&fs::read(&graph_path).map_err(|error| error.to_string())?)
                .map_err(|error| format!("grafo de código inválido: {error}"))?;
        let Some(source_nodes) = graph.get("nodes").and_then(serde_json::Value::as_array) else {
            continue;
        };
        let Some(source_links) = graph.get("links").and_then(serde_json::Value::as_array) else {
            continue;
        };
        let mut remapped = HashMap::new();
        for node in source_nodes {
            let Some(source_id) = ["id", "name"]
                .iter()
                .find_map(|key| node.get(*key).and_then(serde_json::Value::as_str))
            else {
                continue;
            };
            if source_id.is_empty() || source_id.len() > 4096 {
                continue;
            }
            let id = format!("code:{repository_id}:{source_id}");
            let label = ["label", "name", "id"]
                .iter()
                .find_map(|key| node.get(*key).and_then(serde_json::Value::as_str))
                .unwrap_or(source_id)
                .chars()
                .filter(|character| !character.is_control())
                .take(512)
                .collect::<String>();
            let source_file = ["source_file", "file_path", "filePath", "file"]
                .iter()
                .find_map(|key| node.get(*key).and_then(serde_json::Value::as_str))
                .map(|path| {
                    path.chars()
                        .filter(|character| !character.is_control())
                        .take(2048)
                        .collect()
                })
                .unwrap_or_else(|| repository_id.clone());
            remapped.insert(source_id.to_string(), id.clone());
            nodes.push(GraphNode {
                id,
                label,
                source_file,
                node_type: "code".to_string(),
                modified_at,
            });
        }
        for link in source_links {
            let Some(source_id) = link.get("source").and_then(serde_json::Value::as_str) else {
                continue;
            };
            let Some(target_id) = link.get("target").and_then(serde_json::Value::as_str) else {
                continue;
            };
            let (Some(source), Some(target)) = (remapped.get(source_id), remapped.get(target_id))
            else {
                continue;
            };
            let relation = ["relation", "type", "label"]
                .iter()
                .find_map(|key| link.get(*key).and_then(serde_json::Value::as_str))
                .unwrap_or("code_reference")
                .chars()
                .filter(|character| !character.is_control())
                .take(64)
                .collect::<String>();
            links.push(GraphLink {
                source: source.clone(),
                target: target.clone(),
                relation,
                confidence: "EXTRACTED".into(),
                confidence_score: 1.0,
            });
        }
    }
    Ok(())
}

fn repository_key(root: &Path) -> Result<String, String> {
    let mut child = Command::new("sha256sum")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .map_err(|error| format!("sha256sum: {error}"))?;
    child
        .stdin
        .take()
        .ok_or_else(|| "stdin do sha256sum indisponível".to_string())?
        .write_all(root.as_os_str().as_encoded_bytes())
        .map_err(|error| error.to_string())?;
    let output = child
        .wait_with_output()
        .map_err(|error| error.to_string())?;
    if !output.status.success() {
        return Err("não foi possível gerar o identificador do repositório".into());
    }
    let digest = String::from_utf8_lossy(&output.stdout);
    let digest = digest
        .split_whitespace()
        .next()
        .ok_or_else(|| "sha256sum não retornou um digest".to_string())?;
    let label = root
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("repository")
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || character == '-' || character == '_' {
                character.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .take(40)
        .collect::<String>()
        .trim_matches('-')
        .to_string();
    Ok(format!(
        "{}-{}",
        if label.is_empty() {
            "repository"
        } else {
            &label
        },
        &digest[..12]
    ))
}

fn restrict_tree(path: &Path) -> Result<(), String> {
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() {
        return Err("a saída do Graphify contém um link simbólico".into());
    }
    if metadata.is_dir() {
        restrict_directory(path)?;
        for entry in fs::read_dir(path).map_err(|error| error.to_string())? {
            restrict_tree(&entry.map_err(|error| error.to_string())?.path())?;
        }
    } else if metadata.is_file() {
        restrict_file(path)?;
    } else {
        return Err("a saída do Graphify contém um tipo de arquivo não suportado".into());
    }
    Ok(())
}

fn collector_available(source: &str) -> bool {
    AVAILABLE_COLLECTORS.contains(&source)
        && (source != "code" || command_path("graphify").is_some())
}

fn command_available(command: &str) -> bool {
    command_path(command).is_some()
}

fn command_path(command: &str) -> Option<PathBuf> {
    let mut directories = Vec::new();
    if let Some(path) = std::env::var_os("PATH") {
        directories.extend(std::env::split_paths(&path));
    }
    if let Some(path) = std::env::var_os("UV_TOOL_BIN_DIR") {
        directories.push(PathBuf::from(path));
    }
    if let Some(home) = std::env::var_os("HOME") {
        directories.push(PathBuf::from(home).join(".local/bin"));
    }
    directories
        .into_iter()
        .map(|directory| directory.join(command))
        .find(|candidate| {
            let Ok(metadata) = fs::metadata(candidate) else {
                return false;
            };
            if !metadata.is_file() {
                return false;
            }
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                metadata.permissions().mode() & 0o111 != 0
            }
            #[cfg(not(unix))]
            {
                true
            }
        })
}

fn ollama_tags(client: &reqwest::blocking::Client) -> Option<OllamaTags> {
    client
        .get(OLLAMA_TAGS_URL)
        .send()
        .and_then(reqwest::blocking::Response::error_for_status)
        .and_then(|response| response.json::<OllamaTags>())
        .ok()
}

fn ollama_client() -> Option<reqwest::blocking::Client> {
    let home = std::env::var_os("HOME").map(PathBuf::from)?;
    if !home.join(".brew/bin/ollama").is_file() {
        return None;
    }
    let client = reqwest::blocking::Client::builder()
        .no_proxy()
        .timeout(Duration::from_secs(90))
        .build()
        .ok()?;
    let mut tags = ollama_tags(&client);
    if tags.is_none() {
        let started = std::process::Command::new("systemctl")
            .args(["--user", "start", "--no-block", "ollama.service"])
            .output()
            .is_ok_and(|output| output.status.success());
        if !started {
            return None;
        }
        for _ in 0..40 {
            std::thread::sleep(Duration::from_millis(250));
            tags = ollama_tags(&client);
            if tags.is_some() {
                break;
            }
        }
    }
    tags?
        .models
        .iter()
        .any(|model| model.name == EMBEDDING_MODEL)
        .then_some(client)
}

fn embed_texts(texts: &[String]) -> Option<Vec<Vec<f32>>> {
    if texts.is_empty() {
        return Some(Vec::new());
    }
    let client = ollama_client()?;
    let mut embeddings = Vec::with_capacity(texts.len());
    for batch in texts.chunks(32) {
        let input = batch
            .iter()
            .map(|text| text.chars().take(6000).collect::<String>())
            .collect::<Vec<_>>();
        let response = client
            .post(OLLAMA_EMBED_URL)
            .json(&json!({
                "model": EMBEDDING_MODEL,
                "input": input,
                "truncate": true,
                "keep_alive": "5m"
            }))
            .send()
            .ok()?
            .error_for_status()
            .ok()?
            .json::<EmbeddingReply>()
            .ok()?;
        if response.embeddings.len() != batch.len()
            || response
                .embeddings
                .iter()
                .any(|embedding| embedding.len() != EMBEDDING_DIMENSIONS)
        {
            return None;
        }
        embeddings.extend(response.embeddings);
    }
    Some(embeddings)
}

fn collect_markdown(
    current: &Path,
    vault: &Path,
    notes_enabled: bool,
    output: &mut Vec<(PathBuf, String, i64)>,
) -> Result<(), String> {
    let entries = fs::read_dir(current).map_err(|error| error.to_string())?;
    for entry in entries {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        let file_type = entry.file_type().map_err(|error| error.to_string())?;
        if file_type.is_symlink() {
            continue;
        }
        let metadata = entry.metadata().map_err(|error| error.to_string())?;
        if file_type.is_dir() {
            if entry.file_name().to_string_lossy().starts_with('.') {
                continue;
            }
            if path == vault.join("notes") && !notes_enabled {
                continue;
            }
            collect_markdown(&path, vault, notes_enabled, output)?;
        } else if file_type.is_file()
            && path.extension().is_some_and(|extension| extension == "md")
            && !path
                .file_name()
                .is_some_and(|name| name.to_string_lossy().to_lowercase().contains(".env"))
            && metadata.len() <= 2 * 1024 * 1024
        {
            let text = fs::read_to_string(&path).map_err(|error| error.to_string())?;
            let modified_at = metadata
                .modified()
                .ok()
                .and_then(|time| time.duration_since(std::time::UNIX_EPOCH).ok())
                .map_or(0, |duration| duration.as_secs() as i64);
            output.push((path, text, modified_at));
        }
    }
    Ok(())
}

fn memory_node_type(path: &str) -> &'static str {
    if path.starts_with("daily/collectors/shell/") {
        "command"
    } else if path.starts_with("daily/collectors/git/") {
        "commit"
    } else if path.starts_with("daily/collectors/hero/") {
        "conversation"
    } else if path.starts_with("daily/collectors/windows/") {
        "window"
    } else if path.starts_with("projects/") {
        "repository"
    } else {
        "note"
    }
}

fn redact_secrets(text: &str) -> String {
    let assignment = Regex::new(
        r"(?i)^\s*[A-Z0-9_]*(API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|PASSWD|AUTHORIZATION)\s*[:=].*$",
    )
    .expect("valid secret pattern");
    let bearer = Regex::new(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*").expect("valid bearer pattern");
    let token = Regex::new(
        r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})\b",
    )
    .expect("valid token pattern");
    let url_credentials =
        Regex::new(r"(?i)\b(https?://)[^/@\s]+:[^/@\s]+@").expect("valid URL credential pattern");
    let private_header = Regex::new(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")
        .expect("valid private key header pattern");
    let private_footer = Regex::new(r"-----END [A-Z0-9 ]*PRIVATE KEY-----")
        .expect("valid private key footer pattern");
    let inline_secret = Regex::new(
        r"(?i)((?:--?(?:api[_-]?key|access[_-]?token|token|secret|password|passwd|authorization)|(?:api[_-]?key|access[_-]?token|token|secret|password|passwd|authorization))\s*(?:=|\s+)\s*)[^\s]+",
    )
    .expect("valid inline secret pattern");
    let mut in_private_key = false;
    text.lines()
        .filter_map(|line| {
            if in_private_key {
                if private_footer.is_match(line) {
                    in_private_key = false;
                }
                return None;
            }
            if private_header.is_match(line) {
                in_private_key = !private_footer.is_match(line);
                return Some("[CHAVE PRIVADA REDIGIDA]".to_string());
            }
            if assignment.is_match(line) {
                return Some("[SEGREDO REDIGIDO]".to_string());
            }
            let safe = inline_secret.replace_all(line, "$1[REDACTED]");
            let safe = url_credentials.replace_all(&safe, "$1[REDACTED]@");
            Some(
                token
                    .replace_all(&bearer.replace_all(&safe, "$1[REDACTED]"), "[REDACTED]")
                    .to_string(),
            )
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn markdown_inline(value: &str) -> String {
    value
        .chars()
        .filter(|character| !character.is_control())
        .collect::<String>()
        .replace('\n', " ")
        .replace('`', "\\`")
}

fn purge_directory(
    directory: &Path,
    now: std::time::SystemTime,
    retention: Duration,
    markdown_only: bool,
) -> Result<usize, String> {
    let mut removed = 0;
    for entry in fs::read_dir(directory).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
        if metadata.file_type().is_symlink() {
            continue;
        }
        if metadata.is_dir() {
            removed += purge_directory(&path, now, retention, markdown_only)?;
        } else if metadata.is_file()
            && (!markdown_only
                || path
                    .extension()
                    .is_some_and(|extension| extension.eq_ignore_ascii_case("md")))
            && metadata
                .modified()
                .is_ok_and(|modified| now.duration_since(modified).unwrap_or_default() > retention)
        {
            fs::remove_file(path).map_err(|error| error.to_string())?;
            removed += 1;
        }
    }
    Ok(removed)
}

fn purge_hero_notes(
    directory: &Path,
    now: std::time::SystemTime,
    retention: Duration,
) -> Result<usize, String> {
    let mut removed = 0;
    for entry in fs::read_dir(directory).map_err(|error| error.to_string())? {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        let metadata = fs::symlink_metadata(&path).map_err(|error| error.to_string())?;
        if metadata.file_type().is_symlink()
            || !metadata.is_file()
            || !path
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("md"))
            || metadata.len() > 2 * 1024 * 1024
            || !metadata
                .modified()
                .is_ok_and(|modified| now.duration_since(modified).unwrap_or_default() > retention)
        {
            continue;
        }
        let contents = fs::read_to_string(&path).map_err(|error| error.to_string())?;
        if contents
            .lines()
            .take(6)
            .any(|line| line.trim() == "source: hero")
        {
            fs::remove_file(path).map_err(|error| error.to_string())?;
            removed += 1;
        }
    }
    Ok(removed)
}

fn markdown_title(content: &str, path: &Path) -> String {
    content
        .lines()
        .find_map(|line| {
            line.strip_prefix("# ")
                .map(str::trim)
                .filter(|title| !title.is_empty())
        })
        .map(str::to_string)
        .or_else(|| {
            path.file_stem()
                .map(|stem| stem.to_string_lossy().to_string())
        })
        .unwrap_or_else(|| "Nota".into())
}

fn wikilinks(content: &str) -> Vec<String> {
    let mut links = Vec::new();
    let mut remaining = content;
    while let Some(start) = remaining.find("[[") {
        remaining = &remaining[start + 2..];
        let Some(end) = remaining.find("]]") else {
            break;
        };
        let target = remaining[..end].trim();
        if !target.is_empty() {
            links.push(target.to_string());
        }
        remaining = &remaining[end + 2..];
    }
    links
}

fn alias_key(value: &str) -> String {
    value
        .trim()
        .replace('\\', "/")
        .trim_end_matches(".md")
        .to_lowercase()
}

#[cfg(unix)]
fn restrict_directory(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o700)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_directory(_path: &Path) -> Result<(), String> {
    Ok(())
}

#[cfg(unix)]
fn restrict_file(path: &Path) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_file(_path: &Path) -> Result<(), String> {
    Ok(())
}

struct MemoryService {
    paths: StorePaths,
}

#[interface(name = "org.forjaos.Memory")]
impl MemoryService {
    async fn search(&self, query: &str, limit: u32) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let query = query.to_string();
        tokio::task::spawn_blocking(move || {
            let store = paths;
            store.initialize().map_err(fdo::Error::Failed)?;
            store.search(&query, limit).map_err(fdo::Error::Failed)
        })
        .await
        .map_err(|error| fdo::Error::Failed(error.to_string()))?
        .map(|result| serde_json::to_string(&result).unwrap_or_else(|_| "[]".into()))
    }

    async fn timeline(&self, days: u32, limit: u32) -> fdo::Result<String> {
        let paths = self.paths.clone();
        tokio::task::spawn_blocking(move || {
            paths.initialize().map_err(fdo::Error::Failed)?;
            paths.timeline(days, limit).map_err(fdo::Error::Failed)
        })
        .await
        .map_err(|error| fdo::Error::Failed(error.to_string()))?
        .map(|result| serde_json::to_string(&result).unwrap_or_else(|_| "[]".into()))
    }

    async fn rebuild(&self) -> fdo::Result<String> {
        let paths = self.paths.clone();
        tokio::task::spawn_blocking(move || paths.rebuild())
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map(|(count, semantic)| {
                json!({"status":"ok", "indexed":count, "semantic_search":semantic}).to_string()
            })
            .map_err(fdo::Error::Failed)
    }

    async fn remember(&self, note: &str) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let note = note.to_string();
        tokio::task::spawn_blocking(move || paths.remember(&note))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map(|path| json!({"status":"ok", "path":path}).to_string())
            .map_err(fdo::Error::Failed)
    }

    async fn collectors(&self) -> fdo::Result<String> {
        let paths = self.paths.clone();
        tokio::task::spawn_blocking(move || paths.collectors())
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .and_then(|result| serde_json::to_string(&result).map_err(|error| error.to_string()))
            .map_err(fdo::Error::Failed)
    }

    async fn set_collector(&self, source: &str, enabled: bool) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let source = source.to_string();
        let reply_source = source.clone();
        tokio::task::spawn_blocking(move || paths.set_collector(&source, enabled))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map(|()| json!({"status":"ok", "source":reply_source, "enabled":enabled}).to_string())
            .map_err(fdo::Error::Failed)
    }

    async fn graph_repository(&self, path: &str) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let path = path.to_string();
        tokio::task::spawn_blocking(move || paths.graph_repository(&path))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .and_then(|result| serde_json::to_string(&result).map_err(|error| error.to_string()))
            .map_err(fdo::Error::Failed)
    }

    async fn set_retention(&self, source: &str, days: u32) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let source = source.to_string();
        let reply_source = source.clone();
        tokio::task::spawn_blocking(move || paths.set_retention(&source, days))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map(|()| {
                json!({"status":"ok", "source":reply_source, "retention_days":days}).to_string()
            })
            .map_err(fdo::Error::Failed)
    }

    async fn collect_event(
        &self,
        source: &str,
        detail: &str,
        cwd: &str,
        exit_code: i32,
        duration_ms: u64,
    ) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let (source, detail, cwd) = (source.to_string(), detail.to_string(), cwd.to_string());
        tokio::task::spawn_blocking(move || {
            paths.collect_event(&source, &detail, &cwd, exit_code, duration_ms)
        })
        .await
        .map_err(|error| fdo::Error::Failed(error.to_string()))?
        .map(|path| json!({"status":"ok", "path":path}).to_string())
        .map_err(fdo::Error::Failed)
    }

    async fn collect_window(&self, app: &str, title: &str) -> fdo::Result<String> {
        if app.trim().is_empty() || app.len() > 256 || title.trim().is_empty() || title.len() > 4096
        {
            return Err(fdo::Error::InvalidArgs(
                "metadados de janela vazios ou acima do limite permitido".into(),
            ));
        }
        let paths = self.paths.clone();
        let (app, title) = (app.to_string(), title.to_string());
        tokio::task::spawn_blocking(move || {
            let detail = format!("app={app}; title={title}");
            paths.collect_event("windows", &detail, "", 0, 30_000)
        })
        .await
        .map_err(|error| fdo::Error::Failed(error.to_string()))?
        .map(|path| json!({"status":"ok", "path":path}).to_string())
        .map_err(fdo::Error::Failed)
    }

    async fn register_git_repository(&self, path: &str) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let path = path.to_string();
        tokio::task::spawn_blocking(move || paths.register_git_repository(&path))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map_err(fdo::Error::Failed)
    }

    async fn unregister_git_repository(&self, path: &str) -> fdo::Result<String> {
        let paths = self.paths.clone();
        let path = path.to_string();
        tokio::task::spawn_blocking(move || paths.unregister_git_repository(&path))
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map_err(fdo::Error::Failed)
    }

    async fn scan_git_repositories(&self) -> fdo::Result<String> {
        let paths = self.paths.clone();
        tokio::task::spawn_blocking(move || paths.scan_git_repositories())
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map_err(fdo::Error::Failed)
    }

    async fn purge(&self) -> fdo::Result<String> {
        let paths = self.paths.clone();
        tokio::task::spawn_blocking(move || paths.purge())
            .await
            .map_err(|error| fdo::Error::Failed(error.to_string()))?
            .map(|removed| json!({"status":"ok", "removed":removed}).to_string())
            .map_err(fdo::Error::Failed)
    }
}

fn git_output(root: &str, args: &[&str]) -> Result<String, String> {
    let output = Command::new("git")
        .args(["-C", root])
        .args(args)
        .output()
        .map_err(|error| error.to_string())?;
    if !output.status.success() {
        return Err("comando Git falhou para o repositório registrado".into());
    }
    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

#[tokio::main]
async fn main() -> zbus::Result<()> {
    let paths = StorePaths::from_environment().map_err(std::io::Error::other)?;
    paths.initialize().map_err(std::io::Error::other)?;
    if std::env::args().nth(1).as_deref() == Some("--mcp") {
        if let Err(error) = mcp::run(paths) {
            eprintln!("hero-memory MCP: {error}");
        }
        return Ok(());
    }
    let service = MemoryService { paths };
    let _connection = connection::Builder::session()?
        .name(BUS_NAME)?
        .serve_at(OBJECT_PATH, service)?
        .build()
        .await?;
    std::future::pending::<()>().await;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::MutexGuard;

    static NEXT_TEMP: AtomicUsize = AtomicUsize::new(0);
    static TEST_LOCK: Mutex<()> = Mutex::new(());

    struct TestDirectory {
        path: PathBuf,
        previous_home: Option<std::ffi::OsString>,
        _guard: MutexGuard<'static, ()>,
    }

    impl TestDirectory {
        fn new() -> Self {
            let guard = TEST_LOCK
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner);
            let id = NEXT_TEMP.fetch_add(1, Ordering::Relaxed);
            let path =
                std::env::temp_dir().join(format!("forja-memory-test-{}-{id}", std::process::id()));
            fs::create_dir_all(&path).expect("create temporary test directory");
            let previous_home = std::env::var_os("HOME");
            std::env::set_var("HOME", &path);
            Self {
                path,
                previous_home,
                _guard: guard,
            }
        }

        fn store(&self) -> StorePaths {
            StorePaths {
                vault: self.path.join("vault"),
                index: self.path.join("data/hero/memory.db"),
                config: self.path.join("config/hero/memory.toml"),
            }
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.path);
            if let Some(home) = self.previous_home.take() {
                std::env::set_var("HOME", home);
            } else {
                std::env::remove_var("HOME");
            }
        }
    }

    #[cfg(unix)]
    #[test]
    fn collect_markdown_skips_symlinks() {
        use std::os::unix::fs::symlink;

        let temp = TestDirectory::new();
        let vault = temp.path.join("vault");
        let outside = temp.path.join("outside.md");
        fs::create_dir_all(&vault).unwrap();
        fs::write(&outside, "# Conteúdo externo").unwrap();
        symlink(&outside, vault.join("linked.md")).unwrap();

        let mut notes = Vec::new();
        collect_markdown(&vault, &vault, true, &mut notes).unwrap();

        assert!(notes.is_empty());
    }

    #[test]
    fn note_retention_preserves_non_markdown_attachments() {
        let temp = TestDirectory::new();
        let notes = temp.path.join("notes");
        fs::create_dir_all(&notes).unwrap();
        let markdown = notes.join("old.md");
        let attachment = notes.join("attachment.pdf");
        fs::write(&markdown, "# Nota antiga").unwrap();
        fs::write(&attachment, b"attachment").unwrap();
        let future = std::time::SystemTime::now() + Duration::from_secs(86_400);

        let removed = purge_directory(&notes, future, Duration::ZERO, true).unwrap();

        assert_eq!(removed, 1);
        assert!(!markdown.exists());
        assert!(attachment.exists());
    }

    #[test]
    fn hero_retention_removes_only_hero_authored_markdown() {
        let temp = TestDirectory::new();
        let daily = temp.path.join("daily");
        fs::create_dir_all(&daily).unwrap();
        let hero_note = daily.join("hero.md");
        let user_note = daily.join("user.md");
        fs::write(&hero_note, "---\nsource: hero\n---\n# Lembrança").unwrap();
        fs::write(&user_note, "---\nsource: user\n---\n# Nota").unwrap();
        let future = std::time::SystemTime::now() + Duration::from_secs(86_400);

        let removed = purge_hero_notes(&daily, future, Duration::ZERO).unwrap();

        assert_eq!(removed, 1);
        assert!(!hero_note.exists());
        assert!(user_note.exists());
    }

    #[test]
    fn event_graph_cooccurrence_does_not_cross_a_fifteen_minute_bucket() {
        let temp = TestDirectory::new();
        let vault = temp.path.join("vault");
        let index = temp.path.join("memory.db");
        let config = temp.path.join("memory.toml");
        fs::create_dir_all(vault.join("graph")).unwrap();
        let note = vault.join("notes/current.md");
        fs::create_dir_all(note.parent().unwrap()).unwrap();
        fs::write(&note, "# Nota").unwrap();
        let event_time = note
            .metadata()
            .unwrap()
            .modified()
            .unwrap()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;
        let prior_bucket_time = event_time.div_euclid(900) * 900 - 1;
        let graph = GraphDocument {
            graph: GraphMetadata {
                schema_version: 1,
                graphify_version: "test".into(),
            },
            nodes: vec![GraphNode {
                id: "daily/collectors/shell/event.md".into(),
                label: "Evento anterior".into(),
                source_file: "daily/collectors/shell/event.md".into(),
                node_type: "command".into(),
                modified_at: prior_bucket_time,
            }],
            links: Vec::new(),
            hyperedges: Vec::new(),
        };
        fs::write(
            vault.join("graph/graph.json"),
            serde_json::to_vec(&graph).unwrap(),
        )
        .unwrap();
        let paths = StorePaths {
            vault,
            index,
            config,
        };

        paths.update_event_graph(&note).unwrap();

        let updated: GraphDocument =
            serde_json::from_slice(&fs::read(paths.vault.join("graph/graph.json")).unwrap())
                .unwrap();
        assert!(updated.links.is_empty());
    }

    #[test]
    fn initialize_rebuild_search_and_timeline_use_the_local_index() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        paths.initialize().unwrap();
        let projects = paths.vault.join("projects");
        fs::create_dir_all(&projects).unwrap();
        fs::write(
            projects.join("alpha.md"),
            "---\ntitle: Projeto Alpha\n---\nO vulcão guarda magma. [[Beta]].",
        )
        .unwrap();
        fs::write(
            projects.join("beta.md"),
            "---\ntitle: Beta\n---\nA resposta está no mapa.",
        )
        .unwrap();
        fs::write(
            paths.vault.join("notes/pessoal.md"),
            "# Nota privada\nconteúdo local",
        )
        .unwrap();

        let (indexed, semantic) = paths.rebuild().unwrap();
        let hits = paths.search("vulcão", 10).unwrap();
        let timeline = paths.timeline(30, 20).unwrap();
        let graph: GraphDocument =
            serde_json::from_slice(&fs::read(paths.vault.join("graph/graph.json")).unwrap())
                .unwrap();

        assert_eq!(indexed, 2);
        assert!(!semantic);
        assert_eq!(hits.len(), 1);
        assert!(hits[0].id.ends_with("alpha.md"));
        assert_eq!(timeline.len(), 2);
        assert!(graph.links.iter().any(|link| link.relation == "references"));
        assert!(paths.search("   ", 10).is_err());

        paths.set_collector("notes", true).unwrap();
        let (with_notes, _) = paths.rebuild().unwrap();
        assert_eq!(with_notes, 3);
        assert_eq!(paths.search("privada", 10).unwrap().len(), 1);
    }

    #[test]
    fn collectors_and_retention_configuration_validate_and_persist() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        let collectors = paths.collectors().unwrap();
        assert_eq!(collectors.len(), COLLECTORS.len());
        for (source, expected) in [
            ("shell", true),
            ("git", true),
            ("hero", true),
            ("windows", false),
            ("code", false),
            ("notes", false),
        ] {
            assert_eq!(
                collectors
                    .iter()
                    .find(|collector| collector["source"] == source)
                    .unwrap()["enabled"],
                expected
            );
        }
        assert!(paths.set_collector("unknown", true).is_err());
        paths.set_collector("shell", false).unwrap();
        assert!(paths
            .collect_event("shell", "echo segredo", "", 0, 0)
            .is_err());
        paths.set_collector("shell", true).unwrap();
        assert!(paths.set_retention("unknown", 1).is_err());
        assert!(paths.set_retention("shell", 36_501).is_err());
        paths.set_retention("notes", 12).unwrap();
        assert_eq!(paths.config_values().unwrap()["retention_days.notes"], "12");
    }

    #[test]
    fn remembered_notes_are_redacted_searchable_and_removable() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        let id = paths
            .remember("API_KEY=abc123\nLembrar do farol azul")
            .unwrap();
        let note_path = paths.vault.join(&id);
        let saved = fs::read_to_string(&note_path).unwrap();

        assert!(saved.contains("[SEGREDO REDIGIDO]"));
        assert_eq!(paths.search("farol", 10).unwrap().len(), 1);
        assert!(paths.forget("../secret.md").is_err());
        paths.forget(&id).unwrap();
        assert!(!note_path.exists());
        assert!(paths.search("farol", 10).unwrap().is_empty());
    }

    #[test]
    fn collector_events_redact_content_and_update_searchable_graph() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        let id = paths
            .collect_event(
                "shell",
                "TOKEN=supersecret echo deploy",
                "/tmp/projeto",
                0,
                42,
            )
            .unwrap();
        let event_path = paths.vault.join(&id);
        let event = fs::read_to_string(&event_path).unwrap();
        let _ = paths.rebuild().unwrap();
        let hits = paths.search("SHELL", 10).unwrap();
        let graph: GraphDocument =
            serde_json::from_slice(&fs::read(paths.vault.join("graph/graph.json")).unwrap())
                .unwrap();

        assert!(event.contains("[SEGREDO REDIGIDO]"));
        assert!(!event.contains("supersecret"));
        assert_eq!(hits.len(), 1);
        assert!(graph
            .nodes
            .iter()
            .any(|node| node.id == id && node.node_type == "command"));
        assert!(paths.collect_event("shell", "  ", "", 0, 0).is_err());
        assert!(paths.collect_event("invalid", "evento", "", 0, 0).is_err());
    }

    #[test]
    fn local_git_repository_registration_scan_and_removal_work() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        paths.initialize().unwrap();
        let repository = temp.path.join("repo");
        fs::create_dir_all(&repository).unwrap();
        let git = |args: &[&str]| {
            let output = Command::new("git")
                .arg("-C")
                .arg(&repository)
                .args(args)
                .output()
                .unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
        };
        git(&["init", "--quiet"]);
        git(&["config", "user.name", "Forja Test"]);
        git(&["config", "user.email", "forja-test@example.invalid"]);
        fs::write(repository.join("README.md"), "primeiro commit").unwrap();
        git(&["add", "README.md"]);
        git(&["commit", "--quiet", "-m", "primeiro"]);

        let first = paths
            .register_git_repository(repository.to_str().unwrap())
            .unwrap();
        let first: serde_json::Value = serde_json::from_str(&first).unwrap();
        assert_eq!(first["registered"], true);
        assert!(paths
            .register_git_repository(repository.to_str().unwrap())
            .unwrap()
            .contains("false"));
        fs::write(repository.join("README.md"), "segundo commit").unwrap();
        git(&["add", "README.md"]);
        git(&["commit", "--quiet", "-m", "segundo"]);
        let scan: serde_json::Value =
            serde_json::from_str(&paths.scan_git_repositories().unwrap()).unwrap();
        assert_eq!(scan["status"], "ok");
        assert_eq!(scan["commits_recorded"], 1);
        let removed: serde_json::Value = serde_json::from_str(
            &paths
                .unregister_git_repository(repository.to_str().unwrap())
                .unwrap(),
        )
        .unwrap();
        assert_eq!(removed["unregistered"], true);
    }

    #[test]
    fn graphify_output_is_safely_merged_into_the_shared_graph() {
        let temp = TestDirectory::new();
        let vault = temp.path.join("vault");
        let output = vault.join("graph/code/demo/graphify-out");
        fs::create_dir_all(&output).unwrap();
        fs::write(
            output.join("graph.json"),
            r#"{"nodes":[{"id":"a","label":"A"},{"name":"b","file":"src/b.rs"}],"links":[{"source":"a","target":"b","type":"calls"},{"source":"missing","target":"b"}]}"#,
        )
        .unwrap();
        let mut nodes = Vec::new();
        let mut links = Vec::new();

        append_code_graphs(&vault, &mut nodes, &mut links).unwrap();

        assert_eq!(nodes.len(), 2);
        assert!(nodes.iter().all(|node| node.id.starts_with("code:demo:")));
        assert_eq!(nodes[1].source_file, "src/b.rs");
        assert_eq!(links.len(), 1);
        assert_eq!(links[0].relation, "calls");
        assert!(append_code_graphs(
            &temp.path.join("empty-vault"),
            &mut Vec::new(),
            &mut Vec::new()
        )
        .is_ok());
    }

    #[test]
    fn markdown_graph_and_redaction_helpers_handle_supported_shapes() {
        assert_eq!(memory_node_type("daily/collectors/git/sha.md"), "commit");
        assert_eq!(
            memory_node_type("daily/collectors/windows/app.md"),
            "window"
        );
        assert_eq!(
            memory_node_type("daily/collectors/hero/chat.md"),
            "conversation"
        );
        assert_eq!(memory_node_type("daily/collectors/shell/cmd.md"), "command");
        assert_eq!(memory_node_type("projects/repo.md"), "repository");
        assert_eq!(memory_node_type("notes/x.md"), "note");
        assert_eq!(
            markdown_title(
                "---\ntitle: \"Minha nota\"\n---\n# Outro",
                Path::new("fallback.md")
            ),
            "Outro"
        );
        assert_eq!(
            markdown_title("# Cabeçalho\ntexto", Path::new("fallback.md")),
            "Cabeçalho"
        );
        assert_eq!(
            markdown_title("sem título", Path::new("fallback.md")),
            "fallback"
        );
        assert_eq!(
            wikilinks("[[Alvo]] [[Alvo|apelido]] [[Alvo#parte]]"),
            vec!["Alvo", "Alvo|apelido", "Alvo#parte"]
        );
        assert_eq!(alias_key("  Olá, MUNDO!  "), "olá, mundo!");
        assert_eq!(markdown_inline("linha\n`código`"), "linha\\`código\\`");
        let redacted =
            redact_secrets("PASSWORD=hunter2\nAuthorization: Bearer abc.def\nhttps://u:p@host");
        assert!(!redacted.contains("hunter2"));
        assert!(!redacted.contains("abc.def"));
        assert!(!redacted.contains("u:p"));
    }

    #[test]
    fn purge_applies_collector_retention_to_hero_and_notes_only() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        paths.initialize().unwrap();
        paths.set_retention("hero", 1).unwrap();
        paths.set_retention("notes", 1).unwrap();
        let hero = paths.vault.join("daily/old.md");
        let notes = paths.vault.join("notes/old.md");
        let attachment = paths.vault.join("notes/keep.pdf");
        fs::write(&hero, "---\nsource: hero\n---\nnota antiga").unwrap();
        fs::write(&notes, "# Nota antiga").unwrap();
        fs::write(&attachment, b"preservar").unwrap();
        let old = std::time::SystemTime::now() - Duration::from_secs(2 * 86_400);
        for path in [&hero, &notes, &attachment] {
            fs::File::open(path)
                .unwrap()
                .set_times(std::fs::FileTimes::new().set_modified(old))
                .unwrap();
        }

        assert_eq!(paths.purge().unwrap(), 2);
        assert!(!hero.exists());
        assert!(!notes.exists());
        assert!(attachment.exists());
    }

    #[tokio::test]
    async fn dbus_service_methods_route_to_the_store_and_validate_inputs() {
        let temp = TestDirectory::new();
        let service = MemoryService {
            paths: temp.store(),
        };

        assert!(service.search(" ", 10).await.is_err());
        assert!(service.timeline(1, 10).await.is_ok());
        assert!(service.rebuild().await.is_ok());
        assert!(service.remember("nota do serviço").await.is_ok());
        assert!(service.collectors().await.is_ok());
        assert!(service.set_collector("windows", true).await.is_ok());
        assert!(service.collect_window("", "título").await.is_err());
        assert!(service
            .collect_window("Editor", "arquivo aberto")
            .await
            .is_ok());
        assert!(service.set_retention("notes", 30).await.is_ok());
        assert!(service.set_retention("notes", 36_501).await.is_err());
        assert!(service
            .graph_repository("/missing/repository")
            .await
            .is_err());
        assert!(service.register_git_repository("").await.is_err());
        assert!(service
            .unregister_git_repository("relative-missing")
            .await
            .is_err());
        assert!(service.scan_git_repositories().await.is_ok());
        assert!(service.purge().await.is_ok());
    }

    #[test]
    fn rebuild_10k_notes_finishes_with_a_consistent_sqlite_index() {
        let temp = TestDirectory::new();
        let paths = temp.store();
        let projects = paths.vault.join("projects");
        fs::create_dir_all(&projects).unwrap();
        for index in 0..10_000 {
            fs::write(
                projects.join(format!("note-{index:05}.md")),
                format!("# Nota {index}\nDocumento sintético para medir a reconstrução do índice."),
            )
            .unwrap();
        }

        let started = std::time::Instant::now();
        let (indexed, semantic) = paths.rebuild().unwrap();
        let elapsed = started.elapsed();
        let connection = paths.open().unwrap();
        let integrity: String = connection
            .query_row("PRAGMA integrity_check", [], |row| row.get(0))
            .unwrap();

        assert_eq!(indexed, 10_000);
        assert!(!semantic);
        assert!(
            elapsed < Duration::from_secs(300),
            "rebuild took {elapsed:?}"
        );
        assert_eq!(integrity, "ok");
    }
}
