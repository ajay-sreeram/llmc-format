import * as vscode from 'vscode';
import { marked } from 'marked';

// --- Parser (mirrors Python parser logic) ---

interface Block {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result';
  text: string;
}

interface Message {
  role: 'system' | 'user' | 'assistant';
  blocks: Block[];
}

interface Chat {
  metadata: Record<string, unknown>;
  messages: Message[];
}

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
  const headerRe = /^## (system|user|assistant)\s*$/;
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
    const hm = lines[idx].match(headerRe);
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
  const fenceOpenRe = /^```(thinking|tool_use|tool_result)\s*$/;
  const fenceCloseRe = /^```\s*$/;
  let textAcc: string[] = [];
  let fenceType: string | null = null;
  let fenceAcc: string[] = [];

  function flushText() {
    const t = textAcc.join('\n').trim();
    if (t) {
      blocks.push({ type: 'text', text: t });
    }
    textAcc = [];
  }

  for (const line of lines) {
    if (fenceType) {
      if (fenceCloseRe.test(line)) {
        blocks.push({ type: fenceType as Block['type'], text: fenceAcc.join('\n') });
        fenceType = null;
        fenceAcc = [];
      } else {
        fenceAcc.push(line);
      }
    } else {
      const fm = line.match(fenceOpenRe);
      if (fm) {
        flushText();
        fenceType = fm[1];
        fenceAcc = [];
      } else {
        textAcc.push(line);
      }
    }
  }
  flushText();
  return blocks;
}

// --- Webview ---

function getWebviewContent(chat: Chat, cssUri: vscode.Uri): string {
  let html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<link rel="stylesheet" href="${cssUri}">
</head><body>`;

  // Metadata
  if (Object.keys(chat.metadata).length > 0) {
    html += `<div class="metadata">`;
    for (const [k, v] of Object.entries(chat.metadata)) {
      html += `<div><strong>${esc(k)}:</strong> ${esc(String(v))}</div>`;
    }
    html += `</div>`;
  }

  // Messages
  for (const msg of chat.messages) {
    html += `<div class="message-card role-${msg.role}">`;
    html += `<div class="role-header">${esc(msg.role)}</div>`;
    html += `<div class="body">`;
    for (const block of msg.blocks) {
      if (block.type === 'thinking') {
        html += `<details class="thinking-block"><summary>Thinking...</summary>
          <div class="thinking-content">${esc(block.text)}</div></details>`;
      } else if (block.type === 'tool_use') {
        html += `<div class="tool-block"><div class="tool-label">Tool Use</div>${esc(block.text)}</div>`;
      } else if (block.type === 'tool_result') {
        html += `<div class="tool-block"><div class="tool-label">Tool Result</div>${esc(block.text)}</div>`;
      } else {
        html += marked.parse(block.text) as string;
      }
    }
    html += `</div></div>`;
  }

  html += `</body></html>`;
  return html;
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
