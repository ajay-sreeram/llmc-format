import * as vscode from 'vscode';
import { marked } from 'marked';

// --- Parser (mirrors Python parser logic) ---

interface Block {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result';
  text: string;
  id?: string;
  name?: string;
  isError?: boolean;
}

interface Message {
  role: 'system' | 'user' | 'assistant';
  blocks: Block[];
}

interface Chat {
  metadata: Record<string, unknown>;
  messages: Message[];
}

// Regex patterns for parsing
const HEADER_RE = /^## (system|user|assistant)\s*$/;

// Legacy fence patterns (backward compatibility)
const FENCE_OPEN_RE = /^```(thinking|tool_use|tool_result)\s*$/;
const FENCE_CLOSE_RE = /^```\s*$/;

// XML-style tag patterns (primary format)
const THINK_OPEN_RE = /^<(think|thinking)>\s*$/;
const THINK_CLOSE_RE = /^<\/(think|thinking)>\s*$/;

// Tool use: <tool_use id="..." name="...">
const TOOL_USE_OPEN_RE = /^<tool_use(?:\s+id=["']([^"']*)["'])?(?:\s+name=["']([^"']*)["'])?\s*>\s*$/;
const TOOL_USE_CLOSE_RE = /^<\/tool_use>\s*$/;

// Tool result: <tool_result id="..." is_error="true">
const TOOL_RESULT_OPEN_RE = /^<tool_result(?:\s+id=["']([^"']*)["'])?(?:\s+is_error=["']([^"']*)["'])?\s*>\s*$/;
const TOOL_RESULT_CLOSE_RE = /^<\/tool_result>\s*$/;

function parseLlmc(text: string): Chat {
  const lines = text.split('\n');
  let idx = 0;
  let metadata: Record<string, unknown> = {};

  // Parse YAML frontmatter
  if (lines[0]?.trim() === '---') {
    idx = 1;
    const yamlLines: string[] = [];
    while (idx < lines.length && lines[idx].trim() !== '---') {
      yamlLines.push(lines[idx]);
      idx++;
    }
    idx++; // skip closing ---
    // Simple YAML key:value parser (no nested structures needed)
    for (const line of yamlLines) {
      const m = line.match(/^(\w[\w.-]*)\s*:\s*(.*)$/);
      if (m) {
        metadata[m[1]] = m[2];
      }
    }
  }

  // Split into messages by ## role headers
  const messages: Message[] = [];
  let currentRole: string | null = null;
  let bodyLines: string[] = [];

  function flushMessage() {
    if (currentRole) {
      messages.push({
        role: currentRole as Message['role'],
        blocks: parseBlocks(bodyLines),
      });
    }
  }

  while (idx < lines.length) {
    const hm = lines[idx].match(HEADER_RE);
    if (hm) {
      flushMessage();
      currentRole = hm[1];
      bodyLines = [];
    } else {
      bodyLines.push(lines[idx]);
    }
    idx++;
  }
  flushMessage();

  return { metadata, messages };
}

function parseBlocks(lines: string[]): Block[] {
  const blocks: Block[] = [];
  let textAcc: string[] = [];

  // State for block parsing
  let blockType: string | null = null;
  let blockStyle: string | null = null; // 'xml' or 'fence'
  let blockLines: string[] = [];
  let blockAttrs: Record<string, string | undefined> = {};

  function flushText() {
    const t = textAcc.join('\n').trim();
    if (t) {
      blocks.push({ type: 'text', text: t });
    }
    textAcc = [];
  }

  function createBlock(btype: string, content: string, attrs: Record<string, string | undefined>): Block {
    if (btype === 'thinking') {
      return { type: 'thinking', text: content };
    } else if (btype === 'tool_use') {
      return {
        type: 'tool_use',
        text: content,
        id: attrs.id,
        name: attrs.name,
      };
    } else if (btype === 'tool_result') {
      return {
        type: 'tool_result',
        text: content,
        id: attrs.id,
        isError: attrs.isError?.toLowerCase() === 'true',
      };
    }
    return { type: 'text', text: content };
  }

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (blockType === null) {
      // Not inside a block - check for opening tags/fences

      // Check XML-style thinking tag
      let m = line.match(THINK_OPEN_RE);
      if (m) {
        flushText();
        blockType = 'thinking';
        blockStyle = 'xml';
        blockLines = [];
        blockAttrs = {};
        i++;
        continue;
      }

      // Check XML-style tool_use tag
      m = line.match(TOOL_USE_OPEN_RE);
      if (m) {
        flushText();
        blockType = 'tool_use';
        blockStyle = 'xml';
        blockLines = [];
        blockAttrs = { id: m[1], name: m[2] };
        i++;
        continue;
      }

      // Check XML-style tool_result tag
      m = line.match(TOOL_RESULT_OPEN_RE);
      if (m) {
        flushText();
        blockType = 'tool_result';
        blockStyle = 'xml';
        blockLines = [];
        blockAttrs = { id: m[1], isError: m[2] };
        i++;
        continue;
      }

      // Check legacy fence opening
      m = line.match(FENCE_OPEN_RE);
      if (m) {
        flushText();
        blockType = m[1];
        blockStyle = 'fence';
        blockLines = [];
        blockAttrs = {};
        i++;
        continue;
      }

      // Regular text line
      textAcc.push(line);
      i++;
    } else {
      // Inside a block - look for closing tag/fence
      let closed = false;

      if (blockStyle === 'xml') {
        if (blockType === 'thinking' && THINK_CLOSE_RE.test(line)) {
          closed = true;
        } else if (blockType === 'tool_use' && TOOL_USE_CLOSE_RE.test(line)) {
          closed = true;
        } else if (blockType === 'tool_result' && TOOL_RESULT_CLOSE_RE.test(line)) {
          closed = true;
        }
      } else if (blockStyle === 'fence') {
        if (FENCE_CLOSE_RE.test(line)) {
          closed = true;
        }
      }

      if (closed) {
        const content = blockLines.join('\n');
        blocks.push(createBlock(blockType, content, blockAttrs));
        blockType = null;
        blockStyle = null;
        blockLines = [];
        blockAttrs = {};
      } else {
        blockLines.push(line);
      }

      i++;
    }
  }

  // Remaining text
  flushText();
  return blocks;
}

// --- Webview ---

function getWebviewContent(chat: Chat, cssUri: vscode.Uri): string {
  let html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link rel="stylesheet" href="${cssUri}">
</head><body>`;

  // Metadata bar
  if (Object.keys(chat.metadata).length > 0) {
    html += `<div class="metadata">`;
    for (const [k, v] of Object.entries(chat.metadata)) {
      html += `<span><span class="label">${esc(k)}:</span> ${esc(String(v))}</span>`;
    }
    html += `</div>`;
  }

  // Messages
  html += `<div class="messages">`;
  for (const msg of chat.messages) {
    html += `<div class="message role-${msg.role}">`;
    html += `<div class="role">${getRoleIcon(msg.role)} ${esc(msg.role)}</div>`;
    html += `<div class="content">`;

    for (const block of msg.blocks) {
      if (block.type === 'thinking') {
        const renderedThinking = marked.parse(block.text) as string;
        html += `<details class="thinking">
          <summary>Thinking</summary>
          <div class="thinking-body">${renderedThinking}</div>
        </details>`;
      } else if (block.type === 'tool_use') {
        const name = block.name || 'tool';
        const id = block.id ? esc(block.id) : '';
        html += `<div class="tool tool-use">
          <div class="tool-header">
            <span class="tool-icon">→</span>
            <span class="tool-name">${esc(name)}</span>
            ${id ? `<span class="tool-id">${id}</span>` : ''}
          </div>
          <div class="tool-body">${formatJson(block.text)}</div>
        </div>`;
      } else if (block.type === 'tool_result') {
        const errorClass = block.isError ? ' tool-error' : '';
        const icon = block.isError ? '✗' : '←';
        const label = block.isError ? 'error' : 'result';
        const id = block.id ? esc(block.id) : '';
        html += `<div class="tool tool-result${errorClass}">
          <div class="tool-header">
            <span class="tool-icon">${icon}</span>
            <span class="tool-name">${label}</span>
            ${id ? `<span class="tool-id">${id}</span>` : ''}
          </div>
          <div class="tool-body">${formatJson(block.text)}</div>
        </div>`;
      } else {
        html += `<div class="text">${marked.parse(block.text) as string}</div>`;
      }
    }

    html += `</div></div>`;
  }
  html += `</div>`;

  html += `</body></html>`;
  return html;
}

function getRoleIcon(role: string): string {
  switch (role) {
    case 'system': return '⚙';
    case 'user': return '●';
    case 'assistant': return '◆';
    default: return '○';
  }
}

function formatJson(text: string): string {
  try {
    const parsed = JSON.parse(text.trim());
    return esc(JSON.stringify(parsed, null, 2));
  } catch {
    return esc(text);
  }
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// --- Extension activation ---

export function activate(context: vscode.ExtensionContext) {
  const cssPath = vscode.Uri.joinPath(context.extensionUri, 'media', 'preview.css');

  let currentPanel: vscode.WebviewPanel | undefined;

  function updatePreview(document: vscode.TextDocument) {
    if (!currentPanel) { return; }
    const chat = parseLlmc(document.getText());
    const cssUri = currentPanel.webview.asWebviewUri(cssPath);
    currentPanel.webview.html = getWebviewContent(chat, cssUri);
  }

  const cmd = vscode.commands.registerCommand('llmc.openPreview', () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'llmc') {
      vscode.window.showWarningMessage('Open an .llmc file first.');
      return;
    }

    if (currentPanel) {
      currentPanel.reveal(vscode.ViewColumn.Beside);
    } else {
      currentPanel = vscode.window.createWebviewPanel(
        'llmcPreview',
        'LLMC Preview',
        vscode.ViewColumn.Beside,
        { enableScripts: false, localResourceRoots: [vscode.Uri.joinPath(context.extensionUri, 'media')] }
      );
      currentPanel.onDidDispose(() => { currentPanel = undefined; }, null, context.subscriptions);
    }

    updatePreview(editor.document);
  });

  const onSave = vscode.workspace.onDidSaveTextDocument((doc) => {
    if (doc.languageId === 'llmc' && currentPanel) {
      updatePreview(doc);
    }
  });

  context.subscriptions.push(cmd, onSave);
}

export function deactivate() {}
