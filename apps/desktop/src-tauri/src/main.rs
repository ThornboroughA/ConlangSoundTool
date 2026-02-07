use std::net::TcpListener;

use tauri::{api::process::Command, State};

struct ApiState {
    port: u16,
}

#[tauri::command]
fn api_port(state: State<ApiState>) -> u16 {
    state.port
}

fn pick_port() -> Result<u16, String> {
    TcpListener::bind("127.0.0.1:0")
        .map_err(|err| err.to_string())
        .and_then(|listener| listener.local_addr().map_err(|err| err.to_string()))
        .map(|addr| addr.port())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let port = pick_port()?;
            let mut command = Command::new_sidecar("core_api").map_err(|err| err.to_string())?;
            command = command.env("CONLANG_API_PORT", port.to_string());
            let _child = command.spawn().map_err(|err| err.to_string())?;
            app.manage(ApiState { port });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![api_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
