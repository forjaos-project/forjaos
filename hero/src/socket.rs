use std::io;
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::path::PathBuf;
use std::time::Duration;
use tokio::io::AsyncWriteExt;
use tokio::net::UnixListener;
use tokio::sync::watch;

pub fn bind() -> io::Result<UnixListener> {
    let runtime = std::env::var_os("XDG_RUNTIME_DIR")
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "XDG_RUNTIME_DIR ausente"))?;
    let runtime = PathBuf::from(runtime);
    if !runtime.is_absolute() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "XDG_RUNTIME_DIR deve ser absoluto",
        ));
    }
    let dir = runtime.join("forjaos");
    if !dir.exists() {
        std::fs::create_dir_all(&dir)?;
        std::fs::set_permissions(&dir, std::fs::Permissions::from_mode(0o700))?;
    }
    let metadata = std::fs::symlink_metadata(&dir)?;
    if !metadata.file_type().is_dir() || metadata.permissions().mode() & 0o077 != 0 {
        return Err(io::Error::new(
            io::ErrorKind::PermissionDenied,
            "diretório de runtime do HERO não é privado",
        ));
    }

    let path = dir.join("herod.sock");
    match std::fs::symlink_metadata(&path) {
        Err(error) if error.kind() == io::ErrorKind::NotFound => {}
        Err(error) => return Err(error),
        Ok(metadata) => {
            if !metadata.file_type().is_socket() {
                return Err(io::Error::new(
                    io::ErrorKind::AlreadyExists,
                    "caminho do socket do HERO ocupado",
                ));
            }
            if std::os::unix::net::UnixStream::connect(&path).is_ok() {
                return Err(io::Error::new(
                    io::ErrorKind::AddrInUse,
                    "socket do HERO já está ativo",
                ));
            }
            std::fs::remove_file(&path)?;
        }
    }
    let listener = UnixListener::bind(&path)?;
    std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600))?;
    Ok(listener)
}

pub async fn serve(
    listener: UnixListener,
    state_rx: watch::Receiver<&'static str>,
) -> io::Result<()> {
    loop {
        let (mut stream, _) = listener.accept().await?;
        let reply = serde_json::json!({"state": *state_rx.borrow()}).to_string() + "\n";
        let _ =
            tokio::time::timeout(Duration::from_secs(1), stream.write_all(reply.as_bytes())).await;
    }
}
