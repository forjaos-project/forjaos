use std::time::Duration;

use zbus::Connection;

const SCREEN_SAVER: &str = "org.freedesktop.ScreenSaver";
const SCREEN_SAVER_PATH: &str = "/ScreenSaver";

/// A missing or unresponsive screen locker cannot authorize a state change.
pub async fn locked(connection: &Connection) -> bool {
    let destination = connection.is_bus().then_some(SCREEN_SAVER);
    let reply = tokio::time::timeout(
        Duration::from_millis(500),
        connection.call_method(
            destination,
            SCREEN_SAVER_PATH,
            Some(SCREEN_SAVER),
            "GetActive",
            &(),
        ),
    )
    .await;
    match reply {
        Ok(Ok(message)) => message.body().deserialize::<bool>().unwrap_or(true),
        _ => true,
    }
}

#[cfg(test)]
mod tests {
    use super::locked;
    use zbus::connection;

    struct ScreenSaver {
        active: bool,
    }

    #[zbus::interface(name = "org.freedesktop.ScreenSaver")]
    impl ScreenSaver {
        fn get_active(&self) -> bool {
            self.active
        }
    }

    async fn peer(active: Option<bool>) -> (zbus::Connection, zbus::Connection) {
        let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
            .await
            .expect("private D-Bus listener");
        let peer = tokio::net::TcpStream::connect(listener.local_addr().expect("address"))
            .await
            .expect("private peer");
        let server_stream = listener.accept().await.expect("accept peer").0;
        let server = connection::Builder::tcp_stream(server_stream)
            .server(zbus::Guid::generate())
            .expect("server GUID")
            .p2p();
        let client = connection::Builder::tcp_stream(peer).p2p();
        let client = if let Some(active) = active {
            client
                .serve_at("/ScreenSaver", ScreenSaver { active })
                .expect("serve screen locker")
        } else {
            client
        };
        tokio::try_join!(server.build(), client.build()).expect("connect private peer")
    }

    #[tokio::test]
    async fn lock_state_blocks_mutations_when_locked_or_unavailable() {
        let (server, _client) = peer(Some(true)).await;
        assert!(locked(&server).await);
        let (server, _client) = peer(Some(false)).await;
        assert!(!locked(&server).await);
        let (server, _client) = peer(None).await;
        assert!(locked(&server).await);
    }
}
