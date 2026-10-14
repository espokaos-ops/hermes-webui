import pathlib
import re

REPO = pathlib.Path(__file__).parent.parent
INDEX = (REPO / "static" / "index.html").read_text(encoding="utf-8")
PANELS = (REPO / "static" / "panels.js").read_text(encoding="utf-8")
CSS = (REPO / "static" / "style.css").read_text(encoding="utf-8")
I18N = (REPO / "static" / "i18n.js").read_text(encoding="utf-8")


def _function_body(src: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", src)
    assert match, f"{name}() not found"
    brace = src.find("{", match.end())
    assert brace != -1, f"{name}() has no body"
    depth = 1
    i = brace + 1
    in_string = None
    escaped = False
    in_line_comment = False
    in_block_comment = False
    while i < len(src) and depth:
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == in_string:
                in_string = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in "'\"`":
            in_string = ch
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    assert depth == 0, f"{name}() body did not close"
    return src[brace + 1:i - 1]


def _code_only(src: str) -> str:
    """Return JS source with comments removed (full-line `//` and `/* */`).

    Token-presence checks must prove real code, not comments: the poll
    comments literally mention `redirect401:false`, so a naive `in` check
    passes even if the option is never passed.
    """
    lines = [ln for ln in src.splitlines() if not ln.strip().startswith("//")]
    text = "\n".join(lines)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def test_logs_tab_is_wired_between_insights_and_settings_in_rail_and_mobile_nav():
    rail = INDEX[INDEX.index('data-panel="insights"'):INDEX.index('<div class="rail-spacer"')]
    assert 'data-panel="logs"' in rail
    assert rail.index('data-panel="insights"') < rail.index('data-panel="logs"')

    mobile_start = INDEX.index('class="sidebar-nav"')
    mobile_end = INDEX.index('<!-- Settings button mirrored here for mobile')
    mobile_nav = INDEX[mobile_start:mobile_end]
    assert 'data-panel="logs"' in mobile_nav
    assert mobile_nav.index('data-panel="insights"') < mobile_nav.index('data-panel="logs"')

    assert 'id="panelLogs"' in INDEX
    assert 'id="mainLogs"' in INDEX
    assert "tab_logs" in I18N


def test_logs_panel_fetches_allowlisted_api_and_exposes_controls():
    load_fn = _function_body(PANELS, "loadLogs")
    render_fn = _function_body(PANELS, "_renderLogs")
    selected_file_fn = _function_body(PANELS, "_selectedLogsFile")
    selected_tail_fn = _function_body(PANELS, "_selectedLogsTail")
    assert "api('/api/logs" in load_fn or 'api("/api/logs' in load_fn
    assert "logsFile" in selected_file_fn and "logsTail" in selected_tail_fn
    assert "agent" in INDEX and "errors" in INDEX and "gateway" in INDEX
    assert 'value="200" selected' in INDEX
    assert 'value="100"' in INDEX and 'value="500"' in INDEX and 'value="1000"' in INDEX
    assert "logsWrap" in INDEX
    assert "logsCopyAll" in INDEX
    assert "logsAutoRefresh" in INDEX
    assert "logsSeverityFilter" in INDEX
    copy_fn = _function_body(PANELS, "copyLogsAll")
    assert "_copyText" in copy_fn
    assert "logs-copy" in INDEX


def test_logs_autorefresh_runs_only_while_logs_tab_is_visible_and_enabled():
    start_fn = _function_body(PANELS, "_startLogsAutoRefresh")
    stop_fn = _function_body(PANELS, "_stopLogsAutoRefresh")
    assert "if (nextPanel === 'logs') await loadLogs();" in PANELS
    assert "_syncLogsAutoRefresh();" in PANELS
    assert "_logsAutoRefreshTimer" in PANELS
    assert "setInterval" in start_fn and "5000" in start_fn
    assert "_currentPanel !== 'logs'" in start_fn
    assert "clearInterval" in stop_fn


def test_logs_severity_coloring_prioritizes_explicit_log_level_before_message_text():
    severity_fn = _function_body(PANELS, "_logLineSeverityClass")
    # A WARNING message can legitimately contain words like "provider error";
    # color by the explicit level token, not by incidental message text.
    assert severity_fn.index("log-line-warning") < severity_fn.index("log-line-error")


def test_logs_filter_severity_priority_matches_coloring():
    sev_fn = _code_only(_function_body(PANELS, "_severityForLine"))
    cls_fn = _code_only(_function_body(PANELS, "_logLineSeverityClass"))
    canon_fn = _code_only(_function_body(PANELS, "_logLineSeverity"))
    # Filter and color must derive from one canonical classifier, whose order
    # is WARNING → DEBUG → INFO → ERROR (explicit level token wins over
    # incidental message text, per the pre-existing coloring contract).
    assert "_logLineSeverity" in sev_fn
    assert "_logLineSeverity" in cls_fn
    order = ["WARNING", "DEBUG", "INFO", "ERROR"]
    idx = [canon_fn.index(tok) for tok in order]
    assert idx == sorted(idx), "canonical severity order changed"


def test_logs_poll_is_resilient_to_unauthenticated_and_stale_responses():
    load_fn = _code_only(_function_body(PANELS, "loadLogs"))
    render_fn = _code_only(_function_body(PANELS, "_renderLogs"))
    settle_fn = _code_only(_function_body(PANELS, "_settleLogsFailure"))
    # Background poll must not navigate to login nor bust caches (real code,
    # not comments: the comment above the call mentions redirect401:false).
    assert "redirect401" in load_fn and "false" in load_fn
    assert "no-store" in load_fn
    # Automatic polls stay silent on timeout; manual refresh keeps the toast.
    assert "timeoutToast" in load_fn
    # 401 resolves to undefined: keep last good lines instead of wiping.
    assert "data === undefined" in load_fn
    # Freshness on both paths: successes paint only when newer than the last
    # painted result; failures settle only when no newer request was issued.
    assert "_logsPaintedSeq" in load_fn
    assert "mySeq <= _logsPaintedSeq" in load_fn
    assert "mySeq !== _logsLoadSeq" in load_fn
    # Failure settlement is identity-scoped (never another file's snapshot).
    assert "_lastLogsFile" in settle_fn and "_lastLogsTail" in settle_fn
    # Render must tolerate undefined without throwing (data.tail crash).
    assert "data === undefined" in render_fn


def test_logs_filter_preserves_truncation_metadata():
    apply_fn = _function_body(PANELS, "_applyLogsSeverityFilter")
    # Re-render from cache must carry the last fresh truncated/hint metadata.
    assert "_lastLogsTruncated" in apply_fn
    assert "_lastLogsHint" in apply_fn
    assert "_fromFilter" in apply_fn


def test_logs_client_sse_reporter_does_not_redirect_to_login():
    workspace = (REPO / "static" / "workspace.js").read_text(encoding="utf-8")
    idx = workspace.find("recordClientSSEError")
    assert idx != -1, "recordClientSSEError() not found"
    # Slice a window covering the reporter (its default param contains braces
    # that defeat the naive _function_body brace matcher).
    reporter = workspace[idx:idx + 1200]
    # A background SSE error report with an expired session must not navigate
    # the page to login (which would kill all live streams); it already opts
    # out of toasts, it must also opt out of the 401 redirect.
    assert "redirect401" in reporter and "false" in reporter


def test_logs_severity_functions_agree_on_result():
    """Result-check (via node when available) that filter and color agree on
    every mixed-token line, following the canonical WARNING → DEBUG → INFO →
    ERROR order: an explicit level token wins over incidental message text."""
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        import pytest as _pytest

        _pytest.skip("node binary not available for JS result check")
    panels = REPO / "static" / "panels.js"
    script = (
        "const fs=require('fs');"
        f"const src=fs.readFileSync({str(panels)!r},'utf8');"
        "function extract(name){"
        "const m=src.match(new RegExp('function '+name+'\\\\s*\\\\('));"
        "if(!m) throw new Error(name+' missing');"
        "let i=src.indexOf('{',m.index),d=1;i++;"
        "while(i<src.length&&d){if(src[i]==='{')d++;else if(src[i]==='}')d--;i++;}"
        "return src.slice(m.index,i);}"
        "const sevSrc=extract('_severityForLine'),clsSrc=extract('_logLineSeverityClass'),canonSrc=extract('_logLineSeverity');"
        "eval(canonSrc+';'+sevSrc+';'+clsSrc+';');"
        "const cases=["
        "['2026-05-04 WARNING provider error while fetching', 'warning', 'log-line-warning'],"
        "['2026-05-04 ERROR synthetic-log-marker failed safely', 'error', 'log-line-error'],"
        "['2026-05-04 INFO synthetic-log-marker all good', 'info', 'log-line-info'],"
        "['2026-05-04 INFO provider error while fetching', 'info', 'log-line-info'],"
        "['2026-05-04 DEBUG provider error while fetching', 'debug', 'log-line-debug'],"
        "];"
        "for(const [line,wantSev,wantCls] of cases){"
        "if(_severityForLine(line)!==wantSev) throw new Error('severity: '+line);"
        "if(_logLineSeverityClass(line)!==wantCls) throw new Error('class: '+line);}"
        "console.log('SEVERITY-RESULT-OK');"
    )
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "SEVERITY-RESULT-OK" in proc.stdout


def test_logs_poll_ordering_with_deferred_promises():
    """Execute the real loadLogs() against controllable deferred promises.

    Covers the maintainer's schedules: overlapping slow successes all paint
    (no freeze), a late failure never clobbers a newer empty success, a
    failed file switch shows no foreign lines, a same-scope failure keeps its
    own lines, and 401/undefined keeps them too. Request options (silent
    background polls, toast on manual refresh) are asserted on the real call.
    """
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        import pytest as _pytest

        _pytest.skip("node binary not available for JS result check")
    panels = REPO / "static" / "panels.js"
    src = panels.read_text(encoding="utf-8")
    start = src.index("function _selectedLogsFile")
    end = src.index("async function copyLogsAll")
    block = src[start:end]
    prelude = (
        "let _logsAutoRefreshTimer=null,_lastLogsLines=[],_logsSeverityFilter='all',"
        "_lastLogsHint='',_lastLogsTruncated=false,_lastLogsTotalBytes=0,_lastLogsMtime=null,"
        "_logsLoadSeq=0,_logsVisibilityHookInstalled=false,_logsPaintedSeq=0,"
        "_lastLogsFile=null,_lastLogsTail=null,_currentPanel='logs';"
        "const __els={};"
        "function __mkEl(v){return{value:v,textContent:'',innerHTML:'',checked:true,"
        "disabled:false,style:{},classList:{toggle(){}}}};"
        "__els.logsOutput=__mkEl('');__els.logsStatus=__mkEl('');"
        "__els.logsRefreshBtn=__mkEl('');__els.logsFile=__mkEl('agent');"
        "__els.logsTail=__mkEl('200');__els.logsSeverityFilter=__mkEl('all');"
        "__els.logsAutoRefresh=__mkEl('');__els.logsWrap=__mkEl('');"
        "function $(id){return __els[id]||null;}"
        "function t(k){return k;}"
        "function esc(s){return String(s);}"
        "const __toasts=[];"
        "function showToast(m){__toasts.push(m);}"
        "const __pending=[];"
        "function api(url,opts){return new Promise((res,rej)=>"
        "{__pending.push({url:url,opts:Object.assign({},opts),resolve:res,reject:rej});});}"
        "const __intervals=[];"
        "function setInterval(fn,ms){__intervals.push({fn:fn,ms:ms});return __intervals.length;}"
        "function clearInterval(){}"
        "const __visHandlers=[];"
        "const document={hidden:false,"
        "addEventListener(ev,fn){if(ev==='visibilitychange')__visHandlers.push(fn);}};"
    )
    driver = (
        "(async()=>{"
        "const box=$('logsOutput'),status=$('logsStatus'),fileSel=$('logsFile');"
        "const tick=(ms)=>new Promise((r)=>setTimeout(r,ms===undefined?5:ms));"
        "function okResp(lines){return{file:'agent',tail:200,lines:lines,"
        "truncated:false,total_bytes:0,hint:'',mtime:null};}"
        # Overlapping slow successes: three polls issued before any settles.
        "const a1=loadLogs(false),a2=loadLogs(false),a3=loadLogs(false);"
        "if(__pending.length!==3)throw new Error('expected 3 in flight');"
        "for(const q of __pending){"
        "if(q.opts.redirect401!==false)throw new Error('redirect401 must be false');"
        "if(q.opts.cache!=='no-store')throw new Error('cache must be no-store');"
        "if(q.opts.timeoutMs!==15000)throw new Error('timeoutMs must be 15000');"
        "if(q.opts.timeoutToast!==false)throw new Error('auto poll must stay silent');}"
        "__pending[0].resolve(okResp(['a1']));await tick();"
        "if(!box.innerHTML.includes('a1'))throw new Error('slow success 1 must paint');"
        "__pending[1].resolve(okResp(['a1','a2']));await tick();"
        "if(!box.innerHTML.includes('a2'))throw new Error('slow success 2 must paint, no freeze');"
        "__pending[2].resolve(okResp(['a1','a2','a3']));await tick();"
        "if(!box.innerHTML.includes('a3'))throw new Error('slow success 3 must paint');"
        "await Promise.all([a1,a2,a3]);"
        # Newer empty success paints; older failure arrives late.
        "let base=__pending.length;"
        "const b1=loadLogs(false),b2=loadLogs(false);"
        "__pending[base+1].resolve(okResp([]));await tick();await b2;"
        "if(!box.innerHTML.includes('logs_empty')||box.innerHTML.includes('error_prefix'))"
        "throw new Error('genuine empty success must paint empty view');"
        "if(!status.textContent.includes('0 / 200'))throw new Error('empty status must report 0 lines');"
        "const freshStatus=status.textContent;"
        "__pending[base].reject(new Error('late boom'));await tick();await b1;"
        "if(!box.innerHTML.includes('logs_empty')||box.innerHTML.includes('late boom'))"
        "throw new Error('late failure must not clobber fresh empty view');"
        "if(status.textContent!==freshStatus)throw new Error('late failure must not clobber status');"
        # File switch with a failed new-scope request shows no foreign lines.
        "fileSel.value='errors';"
        "const c1=loadLogs(true);await tick();"
        "if(box.innerHTML.includes('a3'))throw new Error('scope change must drop old lines at once');"
        "if(__pending[__pending.length-1].opts.timeoutToast!==true)"
        "throw new Error('manual refresh keeps the timeout toast');"
        "__pending[__pending.length-1].reject(new Error('errors unreachable'));"
        "await tick();await c1;"
        "if(box.innerHTML.includes('a3'))throw new Error('failed switch must not show agent lines');"
        "if(!box.innerHTML.includes('error_prefix'))throw new Error('failed scope needs failed state');"
        # Same-scope failure keeps its own lines; 401/undefined keeps them too.
        "fileSel.value='agent';"
        "const d1=loadLogs(false);await tick();"
        "__pending[__pending.length-1].resolve({file:'agent',tail:200,lines:['b1','b2'],"
        "truncated:false,total_bytes:0,hint:'',mtime:null});await tick();await d1;"
        "if(!box.innerHTML.includes('b2'))throw new Error('agent reload must paint');"
        "const d2=loadLogs(false);"
        "__pending[__pending.length-1].reject(new Error('timeout'));await tick();await d2;"
        "if(!box.innerHTML.includes('b2'))throw new Error('same-scope failure keeps own lines');"
        "if(status.textContent!=='logs_load_failed')throw new Error('failure status must report');"
        "const d3=loadLogs(false);"
        "__pending[__pending.length-1].resolve(undefined);await tick();await d3;"
        "if(!box.innerHTML.includes('b2'))throw new Error('401/undefined keeps own lines');"
        # Visibility catch-up and 5s cadence wiring stay intact.
        "if(!__intervals.some((e)=>e.ms===5000))throw new Error('5s poll cadence must stay');"
        "if(__visHandlers.length!==1)throw new Error('visibility hook must install once');"
        "const before=__pending.length;"
        "__visHandlers[0]();await tick();"
        "if(__pending.length!==before+1)throw new Error('visible tab must trigger catch-up poll');"
        "console.log('POLL-ORDER-OK');"
        "})().catch((e)=>{console.error('POLL-ORDER-FAIL: '+(e&&e.stack||e));process.exit(1);});"
    )
    script = prelude + block + driver
    proc = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (proc.stderr + proc.stdout)[-3000:]
    assert "POLL-ORDER-OK" in proc.stdout


def test_logs_severity_coloring_and_monospace_wrap_css_are_present():
    css_min = re.sub(r"\s+", "", CSS)
    assert ".logs-output{" in css_min
    assert "font-family" in css_min and "monospace" in css_min
    assert ".logs-output.wrap" in css_min and "white-space:pre-wrap" in css_min
    for cls in ("log-line-error", "log-line-warning", "log-line-info", "log-line-debug"):
        assert f".{cls}" in css_min


def test_logs_source_fixtures_do_not_bake_private_log_content():
    combined = "\n".join(
        (REPO / path).read_text(encoding="utf-8")
        for path in (
            "tests/test_logs_endpoint.py",
            "tests/test_logs_ui_static.py",
            "static/index.html",
            "static/panels.js",
        )
    )
    assert "/home/" + "michael/.hermes/logs" not in combined
    for name in ("agent", "gateway", "errors"):
        assert name + ".log:" not in combined
