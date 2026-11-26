#!/bin/bash
J=$1; shift
SCR="C:/NX_MCP_WORKSPACE/mouse_pcb_nx/nx/$J.py"
powershell -NoProfile -Command "& 'C:/Users/USER/.claude/skills/nx-journal-core/scripts/run_journal.ps1' -Script '$SCR' -WorkDir 'C:/NX_MCP_WORKSPACE/mouse_pcb_nx/out' -TimeoutSec 1200 $*" > /c/NX_MCP_WORKSPACE/mouse_pcb_nx/out/$J.log 2>&1
cd /c/NX_MCP_WORKSPACE/mouse_pcb_nx/out && echo "== $J" && (python ../nx/show.py ${J}_result.json 2>/dev/null || tail -25 $J.log)
