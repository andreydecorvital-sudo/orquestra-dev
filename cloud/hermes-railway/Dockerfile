# Isolated Railway OAuth host for Hermes only.
#
# The official Hermes image starts an interactive TUI as PID 1. In Railway,
# stdin is not a terminal, so the TUI exits and shuts down the entire
# container even though the deployment can show SUCCESS. We override the
# interactive ENTRYPOINT with a non-interactive, long-lived idle process.
#
# Operators use "railway ssh ... -- hermes auth ..." to run the official
# Hermes CLI with a separate SSH session. No login or AI calls run at boot.
# Keep the same private /opt/data volume; never bake credentials into layers.
FROM nousresearch/hermes-agent:v2026.9.14

# Prevent the inherited TUI/s6 startup from making the service exit.
# Railway's historical startCommand becomes CMD arguments and is ignored
# by the shell -c script; the process always remains idle until SIGTERM.
ENTRYPOINT ["/bin/sh", "-c", "exec sleep infinity"]
HEALTHCHECK NONE
