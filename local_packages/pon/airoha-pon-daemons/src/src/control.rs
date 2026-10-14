// SPDX-License-Identifier: GPL-2.0-only

use std::fs;
use std::io::{self, BufRead, BufReader, Read};
use std::os::unix::fs::PermissionsExt;
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::{Path, PathBuf};
use std::thread;

pub struct ControlServer {
    socket_path: PathBuf,
}

impl ControlServer {
    pub fn start<F>(socket_path: &Path, handler: F) -> io::Result<Self>
    where
        F: Fn(UnixStream) -> io::Result<()> + Send + Sync + 'static,
    {
        prepare_socket_path(socket_path)?;
        let listener = UnixListener::bind(socket_path)?;
        fs::set_permissions(socket_path, fs::Permissions::from_mode(0o600))?;

        thread::Builder::new()
            .name("pon-control".to_owned())
            .spawn(move || {
                for stream in listener.incoming().flatten() {
                    let _ = handler(stream);
                }
            })
            .map_err(io::Error::other)?;

        Ok(Self {
            socket_path: socket_path.to_owned(),
        })
    }
}

impl Drop for ControlServer {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.socket_path);
    }
}

fn prepare_socket_path(socket_path: &Path) -> io::Result<()> {
    if socket_path.exists() {
        fs::remove_file(socket_path)?;
    }
    Ok(())
}

// Commands are short ASCII lines; bound both buffering and request growth.
const REQUEST_LIMIT: usize = 1024;
const REQUEST_BUFFER: usize = 256;

pub(crate) fn read_request(reader: impl Read) -> io::Result<String> {
    let mut request = String::new();
    BufReader::with_capacity(REQUEST_BUFFER, reader.take((REQUEST_LIMIT + 1) as u64))
        .read_line(&mut request)?;
    if request.len() > REQUEST_LIMIT {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "control request too long"));
    }
    Ok(request)
}

#[cfg(test)]
mod request_tests {
    use super::*;

    #[test]
    fn accepts_commands_and_stops_at_first_line() {
        for command in ["STATUS 1\n", "DATAPATH 1\n", "EVENTS 1 18446744073709551615\n", "STATUS 1"] {
            assert_eq!(read_request(command.as_bytes()).unwrap(), command);
        }
        assert_eq!(read_request(&b"STATUS 1\nignored\n"[..]).unwrap(), "STATUS 1\n");
    }

    #[test]
    fn bounds_unterminated_requests_and_checks_boundary() {
        assert_eq!(read_request(&vec![b'x'; REQUEST_LIMIT][..]).unwrap().len(), REQUEST_LIMIT);
        for size in [REQUEST_LIMIT + 1, 1024 * 1024] {
            assert_eq!(read_request(&vec![b'x'; size][..]).unwrap_err().kind(), io::ErrorKind::InvalidInput);
        }
    }
}
