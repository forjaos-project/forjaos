use chrono::{Local, Utc};
mod mcp;
use regex::Regex;
use rusqlite::{ffi::sqlite3_auto_extension, params, Connection};
use serde::Serialize;
use serde_json::json;
use sqlite_vec::sqlite3_vec_init;
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::Once;
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
}

#[derive(Serialize)]
struct SearchHit {
    id: String,
    path: String,
    title: String,
    excerpt: String,
    modified_at: i64,
}

#[derive(Serialize)]
struct GraphDocument {
    graph: GraphMetadata,
    nodes: Vec<GraphNode>,
    links: Vec<GraphLink>,
    hyperedges: Vec<serde_json::Value>,
}

#[derive(Serialize)]
struct GraphMetadata {
    schema_version: u32,
    graphify_version: &'static str,
}

#[derive(Clone, Serialize)]
struct GraphNode {
    id: String,
    label: String,
    source_file: String,
    node_type: &'static str,
}

#[derive(Clone, Serialize)]
struct GraphLink {
    source: String,
    target: String,
    relation: &'static str,
    confidence: &'static str,
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
        })
    }

    fn initialize(&self) -> Result<(), String> {
        for directory in [
            self.vault.clone(),
            self.vault.join("daily"),
            self.vault.join("projects"),
            self.vault.join("hero"),
            self.vault.join("graph"),
            self.index
                .parent()
                .ok_or_else(|| "caminho do índice inválido".to_string())?
                .to_path_buf(),
        ] {
            fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
            restrict_directory(&directory)?;
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
                 );",
            )
            .map_err(|error| error.to_string())?;
        Ok(())
    }

    fn open(&self) -> Result<Connection, String> {
        SQLITE_VEC.call_once(|| unsafe {
            sqlite3_auto_extension(Some(std::mem::transmute(sqlite3_vec_init as *const ())));
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
        collect_markdown(&self.vault, &mut documents)?;
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
        for (index, (path, _text, modified_at)) in documents.iter().enumerate() {
            let relative = path
                .strip_prefix(&self.vault)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let id = relative.clone();
            let safe_text = &safe_documents[index];
            let title = markdown_title(&safe_text, path);
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
                node_type: "note",
            });
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
                let target_name = target
                    .split(|character| matches!(character, '|' | '#'))
                    .next()
                    .unwrap_or(&target);
                let key = alias_key(target_name);
                if let Some(matches) = aliases.get(&key).filter(|matches| matches.len() == 1) {
                    graph_links.push(GraphLink {
                        source: source.clone(),
                        target: matches[0].clone(),
                        relation: "references",
                        confidence: "EXTRACTED",
                        confidence_score: 1.0,
                    });
                }
            }
        }
        transaction.commit().map_err(|error| error.to_string())?;
        self.write_graph(&graph_nodes, &graph_links)?;
        Ok((documents.len(), has_embeddings))
    }

    fn write_graph(&self, nodes: &[GraphNode], links: &[GraphLink]) -> Result<(), String> {
        let graph = GraphDocument {
            graph: GraphMetadata {
                schema_version: 1,
                graphify_version: "forjaos-graphify-compatible",
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
                    let hits = rows
                        .collect::<Result<Vec<_>, _>>()
                        .map_err(|error| error.to_string())?;
                    if !hits.is_empty() {
                        return Ok(hits);
                    }
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
        rows.collect::<Result<Vec<_>, _>>()
            .map_err(|error| error.to_string())
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
    output: &mut Vec<(PathBuf, String, i64)>,
) -> Result<(), String> {
    let entries = fs::read_dir(current).map_err(|error| error.to_string())?;
    for entry in entries {
        let entry = entry.map_err(|error| error.to_string())?;
        let path = entry.path();
        let metadata = entry.metadata().map_err(|error| error.to_string())?;
        if metadata.file_type().is_symlink() {
            continue;
        }
        if metadata.is_dir() {
            if entry.file_name().to_string_lossy().starts_with('.') {
                continue;
            }
            collect_markdown(&path, output)?;
        } else if metadata.is_file()
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

fn redact_secrets(text: &str) -> String {
    let assignment = Regex::new(
        r"(?i)^\s*[A-Z0-9_]*(API[_-]?KEY|ACCESS[_-]?TOKEN|TOKEN|SECRET|PASSWORD|PASSWD|AUTHORIZATION)\s*[:=].*$",
    )
    .expect("valid secret pattern");
    let bearer = Regex::new(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*").expect("valid bearer pattern");
    let token = Regex::new(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})\b")
        .expect("valid token pattern");
    text.lines()
        .map(|line| {
            if assignment.is_match(line) {
                return "[SEGREDO REDIGIDO]".to_string();
            }
            token
                .replace_all(&bearer.replace_all(line, "$1[REDACTED]"), "[REDACTED]")
                .to_string()
        })
        .collect::<Vec<_>>()
        .join("\n")
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
