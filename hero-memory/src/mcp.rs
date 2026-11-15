use crate::StorePaths;
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

const PROTOCOL_VERSION: &str = "2025-06-18";

pub fn run(paths: StorePaths) -> Result<(), String> {
    let stdin = io::stdin();
    let mut stdout = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line.map_err(|error| error.to_string())?;
        if line.trim().is_empty() {
            continue;
        }
        let request: Value = match serde_json::from_str(&line) {
            Ok(request) => request,
            Err(error) => {
                write_message(
                    &mut stdout,
                    &json!({"jsonrpc":"2.0", "id":null, "error":{"code":-32700, "message":error.to_string()}}),
                )?;
                continue;
            }
        };
        let Some(method) = request.get("method").and_then(Value::as_str) else {
            continue;
        };
        let id = request.get("id").cloned();
        let params = request.get("params").cloned().unwrap_or(Value::Null);
        let result = match method {
            "initialize" => Some(json!({
                "protocolVersion":PROTOCOL_VERSION,
                "capabilities":{"tools":{}},
                "serverInfo":{"name":"hero-memory", "version":env!("CARGO_PKG_VERSION")},
                "instructions":"Memória local ForjaOS. O tool forget remove permanentemente uma nota do vault."
            })),
            "ping" => Some(json!({})),
            "tools/list" => Some(tools()),
            "tools/call" => Some(call_tool(&paths, &params)),
            "notifications/initialized" | "notifications/cancelled" => None,
            _ => id.as_ref().map(|_| {
                json!({
                    "jsonrpc":"2.0",
                    "id":id,
                    "error":{"code":-32601, "message":"method not found"}
                })
            }),
        };
        if let (Some(id), Some(result)) = (id, result) {
            if result.get("jsonrpc").is_some() {
                write_message(&mut stdout, &result)?;
            } else {
                write_message(
                    &mut stdout,
                    &json!({"jsonrpc":"2.0", "id":id, "result":result}),
                )?;
            }
        }
    }
    Ok(())
}

fn write_message(output: &mut impl Write, message: &Value) -> Result<(), String> {
    serde_json::to_writer(&mut *output, message).map_err(|error| error.to_string())?;
    output.write_all(b"\n").map_err(|error| error.to_string())?;
    output.flush().map_err(|error| error.to_string())
}

fn tools() -> Value {
    json!({"tools":[
        {"name":"memory_search", "description":"Busca notas do vault local com FTS e embeddings disponíveis.", "inputSchema":{"type":"object", "properties":{"query":{"type":"string"}, "limit":{"type":"integer", "minimum":1, "maximum":100}}, "required":["query"]}},
        {"name":"memory_timeline", "description":"Lista notas locais recentes.", "inputSchema":{"type":"object", "properties":{"days":{"type":"integer", "minimum":1, "maximum":3650}, "limit":{"type":"integer", "minimum":1, "maximum":500}}}},
        {"name":"memory_related", "description":"Encontra notas ligadas a uma entidade pelo grafo local.", "inputSchema":{"type":"object", "properties":{"entity":{"type":"string"}}, "required":["entity"]}},
        {"name":"memory_remember", "description":"Salva uma nota local após redigir padrões conhecidos de segredos.", "inputSchema":{"type":"object", "properties":{"note":{"type":"string", "maxLength":65536}}, "required":["note"]}},
        {"name":"memory_forget", "description":"Remove permanentemente uma nota Markdown do vault pelo ID relativo.", "inputSchema":{"type":"object", "properties":{"id":{"type":"string"}}, "required":["id"]}}
    ]})
}

fn call_tool(paths: &StorePaths, params: &Value) -> Value {
    let Some(name) = params.get("name").and_then(Value::as_str) else {
        return tool_error("Nome da ferramenta ausente.");
    };
    let arguments = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));
    let response = match name {
        "memory_search" => {
            let Some(query) = arguments.get("query").and_then(Value::as_str) else {
                return tool_error("O argumento query é obrigatório.");
            };
            let limit = arguments.get("limit").and_then(Value::as_u64).unwrap_or(20) as u32;
            paths
                .initialize()
                .and_then(|()| paths.search(query, limit))
                .and_then(|items| serde_json::to_string(&items).map_err(|error| error.to_string()))
        }
        "memory_timeline" => {
            let days = arguments.get("days").and_then(Value::as_u64).unwrap_or(1) as u32;
            let limit = arguments
                .get("limit")
                .and_then(Value::as_u64)
                .unwrap_or(100) as u32;
            paths
                .initialize()
                .and_then(|()| paths.timeline(days, limit))
                .and_then(|items| serde_json::to_string(&items).map_err(|error| error.to_string()))
        }
        "memory_related" => {
            let Some(entity) = arguments.get("entity").and_then(Value::as_str) else {
                return tool_error("O argumento entity é obrigatório.");
            };
            related(paths, entity)
                .and_then(|items| serde_json::to_string(&items).map_err(|error| error.to_string()))
        }
        "memory_remember" => {
            let Some(note) = arguments.get("note").and_then(Value::as_str) else {
                return tool_error("O argumento note é obrigatório.");
            };
            paths.remember(note).and_then(|path| {
                serde_json::to_string(&json!({"path":path})).map_err(|error| error.to_string())
            })
        }
        "memory_forget" => {
            let Some(id) = arguments.get("id").and_then(Value::as_str) else {
                return tool_error("O argumento id é obrigatório.");
            };
            paths
                .forget(id)
                .map(|()| json!({"forgotten":id}).to_string())
        }
        _ => return tool_error("Ferramenta desconhecida."),
    };
    match response {
        Ok(text) => json!({"content":[{"type":"text", "text":text}], "isError":false}),
        Err(error) => tool_error(&error),
    }
}

fn related(paths: &StorePaths, entity: &str) -> Result<Vec<Value>, String> {
    let graph_path = paths.vault.join("graph/graph.json");
    let graph: Value =
        serde_json::from_slice(&std::fs::read(graph_path).map_err(|error| error.to_string())?)
            .map_err(|error| error.to_string())?;
    let nodes = graph["nodes"]
        .as_array()
        .ok_or_else(|| "grafo inválido".to_string())?;
    let links = graph["links"]
        .as_array()
        .ok_or_else(|| "grafo inválido".to_string())?;
    let matches = nodes
        .iter()
        .filter(|node| {
            node["id"]
                .as_str()
                .is_some_and(|value| value.eq_ignore_ascii_case(entity))
                || node["label"]
                    .as_str()
                    .is_some_and(|value| value.eq_ignore_ascii_case(entity))
        })
        .collect::<Vec<_>>();
    let ids = matches
        .iter()
        .filter_map(|node| node["id"].as_str())
        .collect::<Vec<_>>();
    Ok(links
        .iter()
        .filter(|link| {
            ids.contains(&link["source"].as_str().unwrap_or(""))
                || ids.contains(&link["target"].as_str().unwrap_or(""))
        })
        .cloned()
        .collect())
}

fn tool_error(message: &str) -> Value {
    json!({"content":[{"type":"text", "text":message}], "isError":true})
}
