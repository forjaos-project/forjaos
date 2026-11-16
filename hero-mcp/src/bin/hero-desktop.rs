#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    hero_mcp::run_desktop().await
}
