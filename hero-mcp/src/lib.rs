mod common;
mod desktop;
mod dev;
mod system;

use rmcp::service::serve_server;
use rmcp::transport::io::stdio_pipes;

pub async fn run_system() -> Result<(), Box<dyn std::error::Error>> {
    let service = serve_server(system::SystemServer::default(), stdio_pipes()).await?;
    service.waiting().await?;
    Ok(())
}

pub async fn run_desktop() -> Result<(), Box<dyn std::error::Error>> {
    let service = serve_server(desktop::DesktopServer::default(), stdio_pipes()).await?;
    service.waiting().await?;
    Ok(())
}

pub async fn run_dev() -> Result<(), Box<dyn std::error::Error>> {
    let service = serve_server(dev::DevServer::default(), stdio_pipes()).await?;
    service.waiting().await?;
    Ok(())
}
