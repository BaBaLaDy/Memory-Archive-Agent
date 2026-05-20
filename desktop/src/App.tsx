import { useState, useRef, useCallback, useEffect } from "react";

const API = "http://127.0.0.1:8899";
const COLLAPSED_W = 600, COLLAPSED_H = 68;
const EXPANDED_W = 600, EXPANDED_H = 600;

// 右键菜单项（hover 高亮）
function CtxItem({ children, onClick, border }: { children: React.ReactNode; onClick: () => void; border?: boolean }) {
  const [hov, setHov] = useState(false);
  return (
    <div
      style={{ ...ctxSt.item, ...(border ? { borderBottom: '1px solid #eee' } : {}), background: hov ? '#f5f5f5' : 'transparent' }}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      onClick={onClick}>{children}
    </div>
  );
}

const TOOL_LABELS: Record<string, string> = {
  search_index: "搜索中", archive_file: "归档中", parse_file: "解析文件",
  classify_content: "分类中", extract_content: "抓取网页", update_index: "更新索引",
  git_sync: "同步中", git_status: "检查状态", list_tree: "扫描目录",
  pull_to_local: "拉取文件", git_remote_info: "检查远程",
};

const ANIMALS = ['🐒', '🐶', '🐱', '🐹', '🐰', '🦊', '🐻', '🐼', '🐧', '🐥', '🐸', '🦖', '🐙', '🐌', '🦞'];

export default function App() {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [toolStatus, setToolStatus] = useState("");
  const [lang, setLang] = useState("zh");
  const [animalIdx, setAnimalIdx] = useState(0);

  const [toolsList, setToolsList] = useState<{name: string, description: string}[]>([]);
  const [showTools, setShowTools] = useState(false);
  const [toolFilter, setToolFilter] = useState("");
  const [toolSelIdx, setToolSelIdx] = useState(0);

  const [text, setText] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<{ name: string; path: string }[]>([]);
  const [batchIndex, setBatchIndex] = useState(-1);
  const batchTotalRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const storageRootRef = useRef("");
  const answerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; path: string; name: string } | null>(null);

  const hasContent = !!answer;

  // 动物自动切换
  useEffect(() => {
    const timer = setInterval(() => {
      setAnimalIdx((i) => (i + 1) % ANIMALS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  // 获取 storage_root 用于解析 [file:] 链接
  useEffect(() => {
    fetch(`${API}/config`)
      .then(r => r.json())
      .then(d => { storageRootRef.current = d.storage_root; })
      .catch(() => {});

    fetch(`${API}/tools`)
      .then(r => r.json())
      .then(d => setToolsList(d))
      .catch(() => {});
  }, []);

  // 代理 [file:] 链接：左键=打开文件，右键=操作菜单
  useEffect(() => {
    const getAbsPath = (link: HTMLElement) => {
      const relPath = link.getAttribute('data-path');
      if (!relPath || !storageRootRef.current) return null;
      
      const normalized = relPath.replace(/\\/g, '/');
      // 如果已经是绝对路径（Windows 的 C:/... 或者 Linux/Mac 的 /...）
      if (/^[a-zA-Z]:\//.test(normalized) || normalized.startsWith('/')) {
        return normalized;
      }
      
      const parts = [storageRootRef.current.replace(/\\/g, '/')];
      for (const seg of normalized.split('/')) {
        if (seg && seg !== '.') parts.push(seg);
      }
      return parts.join('/');
    };

    const clickHandler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest('.maa-file-link') as HTMLElement | null;
      if (!link) return;
      e.preventDefault();
      e.stopPropagation();
      const absPath = getAbsPath(link);
      if (!absPath) return;
      // 左键：调后端 open-file（os.startfile，Windows 最可靠）
      fetch(`${API}/open-file?path=${encodeURIComponent(absPath)}`).catch(() => {});
    };

    const contextHandler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const link = target.closest('.maa-file-link') as HTMLElement | null;
      if (!link) return;
      e.preventDefault();
      e.stopPropagation();
      const absPath = getAbsPath(link);
      if (!absPath) return;
      const name = link.textContent || link.getAttribute('data-path') || '';
      setContextMenu({ x: e.clientX, y: e.clientY, path: absPath, name });
    };

    // 点击其他地方关闭菜单
    const closeMenu = () => setContextMenu(null);

    // 绑定到 document 上，利用事件委托，避免 conditional render 导致 ref.current 为 null 时绑定失败
    document.addEventListener('click', clickHandler);
    document.addEventListener('contextmenu', contextHandler);
    document.addEventListener('click', closeMenu);
    return () => {
      document.removeEventListener('click', clickHandler);
      document.removeEventListener('contextmenu', contextHandler);
      document.removeEventListener('click', closeMenu);
    };
  }, []);

  // 菜单操作
  const handleMenuAction = useCallback((action: 'open' | 'reveal' | 'copy') => {
    if (!contextMenu) return;
    const { path } = contextMenu;
    setContextMenu(null);
    if (action === 'open') {
      fetch(`${API}/open-file?path=${encodeURIComponent(path)}`).catch(() => {});
    } else if (action === 'reveal') {
      fetch(`${API}/reveal-file?path=${encodeURIComponent(path)}`).catch(() => {});
    } else if (action === 'copy') {
      navigator.clipboard?.writeText(path).catch(() => {});
    }
  }, [contextMenu]);

  // Esc 隐藏到托盘
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") (window as any).electronAPI?.hideWindow();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // 窗口呼出时自动聚焦输入框
  useEffect(() => {
    const onFocus = () => inputRef.current?.focus();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  // 窗口自适应：根据内容动态调整高度
  const measureRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const api = (window as any).electronAPI;
    if (!api?.resizeWindow) return;

    // We expand if there's content, loading state, attached files, OR tools dropdown showing
    const ex = hasContent || loading || attachedFiles.length > 0 || showTools;
    if (!ex) {
      api.resizeWindow({ width: COLLAPSED_W, height: COLLAPSED_H });
      return;
    }

    const observer = new ResizeObserver((entries) => {
      for (let entry of entries) {
        let h = entry.target.offsetHeight + 16; // padding top 12 + margin buffer
        h = Math.min(Math.max(h, COLLAPSED_H), EXPANDED_H);
        api.resizeWindow({ width: EXPANDED_W, height: h });
      }
    });

    if (measureRef.current) {
      observer.observe(measureRef.current);
    }

    return () => observer.disconnect();
  }, [hasContent, loading, attachedFiles.length, toolStatus, showTools]);

  // ---- SSE（关键修复：token中 \\n 还原为真实换行）----
  const handleSSE = useCallback((type: string, data: string) => {
    switch (type) {
      case "token":
        // SSE层把 \n 换成了字面量 \\n，这里还原
        setAnswer((prev) => prev + data.replace(/\\n/g, "\n"));
        break;
      case "tool_start":
        try { setToolStatus(TOOL_LABELS[JSON.parse(data).name] ?? "处理中..."); }
        catch { setToolStatus("处理中..."); }
        break;
      case "tool_end":
        try {
          const d = JSON.parse(data);
          const raw = d.output || "";
          let tr: { success: boolean; error?: string } | null = null;
          if (typeof raw === "string") {
            try { tr = JSON.parse(raw); } catch {}
          }
          if (tr && !tr.success) {
            setAnswer((prev) => prev + `\n\n⚠️ ${d.name}: ${tr.error || '未知错误'}`);
          }
        } catch {}
        setToolStatus("");
        break;
      case "done":
        setToolStatus("");
        break;
      case "error":
        setAnswer((prev) => prev + `\n\n❌ ${data}`);
        setToolStatus("");
        break;
    }
  }, []);

  // ---- send one message via SSE, returns when stream ends ----
  const sendOneFile = useCallback(async (message: string, currentLang: string, signal: AbortSignal): Promise<void> => {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, language: currentLang === "zh" ? "中文" : "English" }),
      signal,
    });
    const reader = res.body?.getReader();
    if (!reader) throw new Error("No reader");
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop() || "";
      let et = "";
      for (const l of lines) {
        if (l.startsWith("event: ")) et = l.slice(7).trim();
        else if (l.startsWith("data: ")) handleSSE(et, l.slice(6));
      }
    }
  }, [handleSSE]);

  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setText(val);
    
    // Check if the current word being typed starts with '/'
    // We want to match things like "/ar", " /ar", but not "foo/bar"
    const match = val.match(/(?:^|\s)\/([a-zA-Z0-9_-]*)$/);
    if (match) {
      setShowTools(true);
      setToolFilter(match[1] || "");
      setToolSelIdx(0);
    } else {
      setShowTools(false);
    }
  }, []);

  // ---- send (batch) ----
  const handleSend = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed && attachedFiles.length === 0) return;
    if (loading) return;

    // 构建消息队列：有文件时每个文件一条归档指令，无文件时发送纯文本
    type QueueItem = { label: string; message: string };
    const queue: QueueItem[] = [];

    if (attachedFiles.length > 0) {
      for (const f of attachedFiles) {
        queue.push({
          label: f.name,
          message: trimmed
            ? `请归档文件 ${f.path}\n${trimmed}`
            : `请归档文件 ${f.path}`,
        });
      }
    } else {
      queue.push({ label: "", message: trimmed });
    }

    const totalCount = queue.length;
    setAttachedFiles([]); setText("");
    setLoading(true);
    batchTotalRef.current = totalCount;

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      for (let i = 0; i < queue.length; i++) {
        if (abort.signal.aborted) break;
        const item = queue[i];

        setBatchIndex(i);
        setAnswer(""); setToolStatus("");

        const prefix = totalCount > 1 ? `[${i + 1}/${totalCount}] ` : "";

        try {
          await sendOneFile(prefix + item.message, lang, abort.signal);
        } catch (e: any) {
          if (e.name === "AbortError") break;
          setAnswer((prev) => prev + `\n\n❌ 失败: ${e}`);
        }
      }
    } finally {
      setBatchIndex(-1);
      setLoading(false);
      setToolStatus("");
    }
  }, [text, attachedFiles, loading, lang, sendOneFile]);

  const filteredTools = toolsList.filter(t => t.name.toLowerCase().includes(toolFilter.toLowerCase()));

  const onKey = useCallback((e: React.KeyboardEvent) => {
    if (showTools && filteredTools.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setToolSelIdx(prev => (prev + 1) % filteredTools.length);
        return;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setToolSelIdx(prev => (prev - 1 + filteredTools.length) % filteredTools.length);
        return;
      } else if (e.key === "Enter") {
        e.preventDefault();
        const selTool = filteredTools[toolSelIdx];
        if (selTool) {
          const match = text.match(/(.*)(?:^|\s)\/([a-zA-Z0-9_-]*)$/);
          if (match) {
            setText(match[1] + (match[1] ? " " : "") + "/" + selTool.name + " ");
          }
          setShowTools(false);
        }
        return;
      } else if (e.key === "Escape") {
        setShowTools(false);
      }
    }

    if (e.key === "Enter" && !e.shiftKey) { 
      if (!showTools) {
        e.preventDefault(); 
        handleSend(); 
      }
    }
  }, [handleSend, showTools, filteredTools, toolSelIdx, text]);

  return (
    <div style={st.root}>
      <div ref={measureRef} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {/* ====== 输入条（顶部锚点，位置始终不变） ====== */}
        <div style={st.input}>
          {attachedFiles.length > 0 && (
          <div style={st.chips}>
            {attachedFiles.map((f, i) => (
              <div key={i} style={st.chip}>
                <span style={st.chipName}>{f.name}</span>
                <span style={st.chipX} onClick={() => !loading && setAttachedFiles(prev => prev.filter((_, j) => j !== i))}>✕</span>
              </div>
            ))}
          </div>
        )}
        <div style={st.row}>
          <div 
            style={{
              ...st.iconWrapper,
              fontSize: "18px",
              cursor: "pointer",
              userSelect: "none",
              animation: loading ? "maa-animal-run 0.4s infinite" : "maa-animal-idle 2.5s infinite ease-in-out",
              transformOrigin: "center bottom",
              display: "inline-block",
            }}
            onClick={() => setAnimalIdx((i) => (i + 1) % ANIMALS.length)}
            title={lang === "zh" ? "点我换个小动物！" : "Click to change animal!"}
          >
            {ANIMALS[animalIdx]}
          </div>
          <input
            ref={inputRef}
            style={st.field}
            placeholder={lang === "zh" ? "输入问题，或拖拽文件..." : "Ask a question, or drag and drop files..."}
            value={text}
            onChange={handleTextChange}
            onKeyDown={onKey}
            disabled={loading}
            onDrop={(e) => {
              e.preventDefault();
              const fs = e.dataTransfer.files;
              if (!fs || fs.length === 0) return;
              const incoming: { name: string; path: string }[] = [];
              for (let i = 0; i < fs.length; i++) {
                try {
                  const fp = (window as any).electronAPI?.getFilePath?.(fs[i]);
                  incoming.push({ name: fs[i].name, path: fp || fs[i].name });
                } catch { incoming.push({ name: fs[i].name, path: fs[i].name }); }
              }
              setAttachedFiles(prev => [...prev, ...incoming]);
            }}
          />
          <button
            style={{ ...st.btn, opacity: loading || (!text.trim() && attachedFiles.length === 0) ? 0.4 : 1 }}
            onClick={handleSend} disabled={loading}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={loading || (!text.trim() && attachedFiles.length === 0) ? "#999" : "#0d47a1"} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
          <button
            style={{ ...st.langBtn }}
            onClick={() => setLang(l => l === "zh" ? "en" : "zh")}
            title="切换语言 / Switch Language"
          >
            {lang === "zh" ? "中" : "EN"}
          </button>
          <div style={st.dragHandle} title="拖拽移动窗口">
            <svg width="10" height="16" viewBox="0 0 10 16" fill="none">
              <circle cx="3" cy="3" r="1.2" fill="#999" />
              <circle cx="7" cy="3" r="1.2" fill="#999" />
              <circle cx="3" cy="8" r="1.2" fill="#999" />
              <circle cx="7" cy="8" r="1.2" fill="#999" />
              <circle cx="3" cy="13" r="1.2" fill="#999" />
              <circle cx="7" cy="13" r="1.2" fill="#999" />
            </svg>
          </div>
        </div>
      </div>

        {/* ====== 内容区：输入框下方 ====== */}
        <div style={st.content}>
          {/* Tool Popup (in normal document flow so it expands the window) */}
          {showTools && filteredTools.length > 0 && (
            <div style={st.toolPopup}>
              {filteredTools.map((t, idx) => (
                <div 
                  key={t.name}
                  onClick={() => {
                    const match = text.match(/(.*)(?:^|\s)\/([a-zA-Z0-9_-]*)$/);
                    if (match) {
                      setText(match[1] + (match[1] ? " " : "") + "/" + t.name + " ");
                    }
                    setShowTools(false);
                    inputRef.current?.focus();
                  }}
                  onMouseEnter={() => setToolSelIdx(idx)}
                  style={{
                    ...st.toolItem,
                    background: idx === toolSelIdx ? "#f0f4f8" : "transparent",
                  }}
                >
                  <div style={st.toolItemName}>/{t.name}</div>
                  <div style={st.toolItemDesc}>{t.description}</div>
                </div>
              ))}
            </div>
          )}

        {/* 工具状态 */}
        {toolStatus && (
          <div style={st.status}>
            {batchTotalRef.current > 1 && batchIndex >= 0
              ? `(${batchIndex + 1}/${batchTotalRef.current}) `
              : ""}
            {toolStatus}
          </div>
        )}

        {/* AI 回答 */}
        {(answer || loading) && (
          <div style={st.answer} ref={answerRef}>
            {answer
              ? <div style={st.answerText} dangerouslySetInnerHTML={{ __html: md(answer) }} />
              : <div style={st.thinking}>
                  <i style={st.dot} />
                  <i style={{ ...st.dot, animationDelay: "0.2s" }} />
                  <i style={{ ...st.dot, animationDelay: "0.4s" }} />
                </div>}
          </div>
        )}
</div>
      </div>
      
      {contextMenu && (
        <div style={ctxSt.overlay} onClick={() => setContextMenu(null)}>
          <div style={{ ...ctxSt.menu, left: contextMenu.x, top: contextMenu.y }} onClick={e => e.stopPropagation()}>
            <div style={ctxSt.menuTitle}>{contextMenu.name}</div>
            <CtxItem onClick={() => handleMenuAction('open')}>📄 打开文件</CtxItem>
            <CtxItem onClick={() => handleMenuAction('reveal')}>📁 定位文件</CtxItem>
            <CtxItem onClick={() => handleMenuAction('copy')} border>📋 复制路径</CtxItem>
            <div style={ctxSt.pathText}>{contextMenu.path}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ======== Markdown 渲染（修复：HTML 转义在 code 转换之前） ======== */
function md(raw: string): string {
  if (!raw) return "";

  // 1. 提取围栏代码块（```），用占位符保护
  const codeBlocks: string[] = [];
  let text = raw.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const i = codeBlocks.length;
    codeBlocks.push(`<pre style="background:#f5f5f5;border:1px solid rgba(0,0,0,0.08);border-radius:6px;padding:10px 12px;overflow:auto;font-size:12px;line-height:1.5;margin:6px 0;"><code>${esc(code.trim())}</code></pre>`);
    return `\x00CODE${i}\x00`;
  });

  // 2. 把 LLM 输出的 <code>...</code> HTML 标签转为反引号格式（避免后续被转义）
  text = text.replace(/<code\b[^>]*>([\s\S]*?)<\/code>/g, "`$1`");

  // 3. HTML 转义正文（必须先做，防止 XSS）
  text = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // 3.5 [file:路径] → 可点击链接（在 HTML 转义之后，因为路径字符无需转义）
  text = text.replace(/\[file:([^\]]+)\]/g, (_: string, p: string) => {
    const name = p.split("/").pop() || p;
    return `<a class="maa-file-link" data-path="${esc(p)}" href="#" style="color:#1a6dd4;text-decoration:underline;cursor:pointer;">${esc(name)}</a>`;
  });

  // 4. 反引号行内代码 → 带样式的 <code> HTML
  text = text.replace(/`([^`]+)`/g,
    '<code style="background:#f0f0f0;color:#333;padding:1px 5px;border-radius:3px;font-size:13px;">$1</code>');

  // 5. 粗体 / 斜体
  text = text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>");

  // 6. 链接
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" style="color:#333;text-decoration:underline;">$1</a>');

  // 7. 标题
  text = text
    .replace(/^### (.+)$/gm, "<h3 style='font-size:14px;margin:10px 0 4px;color:#222;'>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2 style='font-size:16px;margin:12px 0 6px;color:#222;'>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1 style='font-size:18px;margin:14px 0 6px;color:#222;'>$1</h1>");

  // 8. 无序列表 / 有序列表
  text = text.replace(/^- (.+)$/gm, "<li style='margin-left:14px;color:#555;'>$1</li>");
  text = text.replace(/^\d+\. (.+)$/gm, "<li style='margin-left:14px;color:#555;'>$1</li>");

  // 9. 段落（双换行）/ 单换行
  text = text.replace(/\n\n/g, "</p><p style='margin:4px 0;'>");
  text = text.replace(/\n/g, "<br/>");

  // 10. 还原代码块占位符
  text = text.replace(/\x00CODE(\d+)\x00/g, (_, i) => codeBlocks[+i]);

  return `<p style='margin:2px 0;'>${text}</p>`;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* ======== 样式 ======== */
const BORDER = "1px solid rgba(0,0,0,0.15)";
const st: Record<string, React.CSSProperties> = {
  root: {
    height: "100%", display: "flex", flexDirection: "column",
    padding: "12px 12px 0", overflow: "hidden",
    background: "transparent",
  },
  content: {
    display: "flex", flexDirection: "column", gap: "10px",
    paddingTop: "6px",
    paddingBottom: "12px",
  },
  // input（中间锚点）
  input: {
    borderRadius: "16px", flexShrink: 0,
    background: "rgba(255,255,255,0.9)",
    border: "1px solid rgba(0,0,0,0.12)",
    backdropFilter: "blur(24px) saturate(150%)",
    WebkitBackdropFilter: "blur(24px) saturate(150%)",
    padding: "8px 6px 8px 12px",
    boxShadow: "0 8px 24px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)",
    transition: "box-shadow 0.2s ease",
  },
  chips: {
    display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "4px",
  },
  chip: {
    display: "flex", alignItems: "center", gap: "6px",
    padding: "3px 10px",
    borderRadius: "6px", background: "#f5f5f5",
    border: "1px solid rgba(0,0,0,0.08)",
    fontSize: "11px", color: "#555",
  },
  chipName: { flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  chipX: { cursor: "pointer", color: "#999", fontSize: "11px", background: "none", border: "none" },
  row: { display: "flex", alignItems: "center", gap: "6px" },
  iconWrapper: {
    display: "flex", alignItems: "center", justifyContent: "center",
    padding: "0 4px", color: "#888",
  },
  field: {
    flex: 1, padding: "6px 0", border: "none", background: "transparent",
    color: "#222", fontSize: "14px", outline: "none",
    fontFamily: "inherit",
    letterSpacing: "0.2px",
  },
  btn: {
    flexShrink: 0, width: "32px", height: "32px", borderRadius: "10px",
    border: "1px solid rgba(0,0,0,0.06)", background: "#f8f9fa", cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
    transition: "all 0.2s cubic-bezier(0.2, 0, 0, 1)",
    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
  },
  langBtn: {
    flexShrink: 0, width: "32px", height: "32px", borderRadius: "10px",
    border: "1px solid rgba(0,0,0,0.06)", background: "#ffffff", cursor: "pointer",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: "12px", color: "#555", fontWeight: "600",
    transition: "all 0.2s cubic-bezier(0.2, 0, 0, 1)",
    boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
  },
  dragHandle: {
    flexShrink: 0, width: "18px", height: "28px",
    display: "flex", alignItems: "center", justifyContent: "center",
    cursor: "grab", WebkitAppRegion: "drag" as any,
    borderRadius: "4px", opacity: 0.3,
    transition: "opacity 0.2s",
  },
  // status
  status: { fontSize: "11px", color: "#888", padding: "0 2px", flexShrink: 0 },
  // answer（下方）
  answer: {
    padding: "14px 18px", borderRadius: "16px", flexShrink: 0,
    background: "rgba(255,255,255,0.95)", 
    border: "1px solid rgba(0,0,0,0.08)",
    backdropFilter: "blur(24px) saturate(150%)",
    WebkitBackdropFilter: "blur(24px) saturate(150%)",
    fontSize: "14px", lineHeight: 1.6, color: "#2c2c2e",
    maxHeight: "500px", overflow: "auto",
    boxShadow: "0 8px 32px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06)",
    animation: "maa-slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards",
  },
  answerText: { whiteSpace: "pre-wrap" as any, wordBreak: "break-word", userSelect: "text", cursor: "text", letterSpacing: "0.1px" },
  thinking: { display: "flex", gap: "4px", padding: "2px 0" },
  dot: {
    display: "inline-block", width: "5px", height: "5px", borderRadius: "50%",
    background: "#0d47a1", opacity: 0.6, fontStyle: "normal",
    animation: "maa-p 1.2s ease-in-out infinite",
  },
  toolPopup: {
    background: "rgba(255,255,255,0.98)",
    backdropFilter: "blur(12px)",
    border: "1px solid rgba(0,0,0,0.1)",
    borderRadius: "12px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
    maxHeight: "240px",
    overflowY: "auto",
    padding: "6px",
    flexShrink: 0,
    animation: "maa-slide-up 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards",
  },
  toolItem: {
    padding: "8px 12px",
    cursor: "pointer",
    borderRadius: "8px",
    marginBottom: "2px",
    transition: "background 0.1s",
  },
  toolItemName: { fontSize: "13px", fontWeight: "bold", color: "#333", marginBottom: "2px" },
  toolItemDesc: { fontSize: "11px", color: "#777", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
};

const ctxSt: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 9999, background: 'transparent',
  },
  menu: {
    position: 'fixed', minWidth: 220,
    background: '#fff', borderRadius: 8,
    boxShadow: '0 4px 20px rgba(0,0,0,0.18)',
    border: '1px solid rgba(0,0,0,0.12)',
    padding: '4px 0', overflow: 'hidden',
  },
  menuTitle: {
    padding: '6px 14px 4px', fontSize: 11, color: '#888',
    borderBottom: '1px solid #f0f0f0',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  item: {
    padding: '8px 14px', fontSize: 13, color: '#333',
    cursor: 'pointer', transition: 'background 0.1s',
  },
  pathText: {
    padding: '4px 14px 6px', fontSize: 10, color: '#aaa',
    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
};

// 注入基础样式
(function () {
  if (typeof document === "undefined") return;
  if (document.getElementById("maa-base")) return;
  const s = document.createElement("style");
  s.id = "maa-base";
  s.textContent = `
    *{margin:0;padding:0;box-sizing:border-box}
    html,body,#root{height:100%;background:transparent;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;overflow:hidden}
    @keyframes maa-p{0%,100%{opacity:.4;transform:translateY(0) scale(.8)}50%{opacity:1;transform:translateY(-2px) scale(1.1)}}
    @keyframes maa-slide-up{0%{opacity:0;transform:translateY(10px) scale(0.98)}100%{opacity:1;transform:translateY(0) scale(1)}}
    @keyframes maa-animal-idle{0%,100%{transform:scale(1) rotate(0deg)}50%{transform:scale(1.15) rotate(8deg)}}
    @keyframes maa-animal-run{0%{transform:translateY(0) rotate(0deg) scale(1.2)}25%{transform:translateY(-5px) rotate(20deg) scale(1.2)}50%{transform:translateY(0) rotate(0deg) scale(1.2)}75%{transform:translateY(-5px) rotate(-20deg) scale(1.2)}100%{transform:translateY(0) rotate(0deg) scale(1.2)}}
    input::placeholder{color:#a0a0a5}
    .maa-file-link:hover{color:#0d47a1!important}
    button:hover{background:#ececec!important}
  `;
  document.head.appendChild(s);
})();
