use std::ffi::OsString;
use std::fs;
use std::path::PathBuf;
use std::sync::{Mutex, MutexGuard};
use std::time::{SystemTime, UNIX_EPOCH};

static HOME_LOCK: Mutex<()> = Mutex::new(());

pub struct TestHome {
    root: PathBuf,
    previous: Option<OsString>,
    _lock: MutexGuard<'static, ()>,
}

impl TestHome {
    pub fn new() -> Self {
        let lock = HOME_LOCK
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock after epoch")
            .as_nanos();
        let root =
            std::env::temp_dir().join(format!("hero-test-home-{}-{stamp}", std::process::id()));
        fs::create_dir_all(&root).expect("create temporary HOME");
        let previous = std::env::var_os("HOME");
        std::env::set_var("HOME", &root);
        Self {
            root,
            previous,
            _lock: lock,
        }
    }

    pub fn root(&self) -> &std::path::Path {
        &self.root
    }

    pub fn register_project(&self, name: &str) -> PathBuf {
        let project = self.root.join("dev").join(name);
        fs::create_dir_all(project.join(".git")).expect("create test git project");
        let config_dir = self.root.join(".config/hero");
        fs::create_dir_all(&config_dir).expect("create HERO config directory");
        let config = format!(
            "[[projects]]\nname = '{name}'\npath = '{}'\n",
            project.display()
        );
        fs::write(config_dir.join("projects.toml"), config).expect("register test project");
        project
    }
}

impl Drop for TestHome {
    fn drop(&mut self) {
        if let Some(previous) = self.previous.take() {
            std::env::set_var("HOME", previous);
        } else {
            std::env::remove_var("HOME");
        }
        let _ = fs::remove_dir_all(&self.root);
    }
}
