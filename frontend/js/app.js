let currentSessionId = localStorage.getItem("trudpravo_session_id") || null;

const messagesArea = document.getElementById("messages-area");
const welcomeScreen = document.getElementById("welcome-screen");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const historyList = document.getElementById("history-list");
const newChatBtn = document.getElementById("new-chat-btn");

document.addEventListener("DOMContentLoaded", () => {
  loadSessions();
  if (currentSessionId) {
    loadSessionMessages(currentSessionId);
  }

  // Быстрые темы (chips)
  document.querySelectorAll(".topic-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const query = chip.getAttribute("data-query");
      if (query) {
        sendMessage(query);
      }
    });
  });

  // Отправка по Enter (без Shift)
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  sendBtn.addEventListener("click", handleSend);

  newChatBtn.addEventListener("click", () => {
    currentSessionId = null;
    localStorage.removeItem("trudpravo_session_id");
    messagesArea.innerHTML = "";
    if (welcomeScreen) {
      messagesArea.appendChild(welcomeScreen);
      welcomeScreen.style.display = "block";
    }
    loadSessions();
  });
});

function handleSend() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  sendMessage(text);
}

async function sendMessage(query) {
  if (welcomeScreen) {
    welcomeScreen.style.display = "none";
  }

  // 1. Рендерим сообщение пользователя
  appendMessage("user", query);

  // 2. Рендерим индикатор загрузки
  const loaderId = appendLoader();

  // Блокируем кнопку отправки
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: query,
        session_id: currentSessionId,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Ошибка сервера");
    }

    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("trudpravo_session_id", currentSessionId);

    // Удаляем лоадер и рендерим ответ
    removeLoader(loaderId);
    appendMessage("bot", data.answer, data.citations);

    loadSessions();
  } catch (error) {
    removeLoader(loaderId);
    appendMessage("bot", `⚠️ Произошла ошибка: ${error.message}`);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

function appendMessage(role, content, citations = []) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "👤" : "⚖️";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatMessageContent(content);

  // Добавляем бейджи статей, если есть
  if (citations && citations.length > 0) {
    const sourcesBox = document.createElement("div");
    sourcesBox.className = "sources-container";

    citations.forEach(c => {
      const badge = document.createElement("span");
      badge.className = "citation-badge";
      let label = c.source_id ? `[${c.source_id}] ` : "";
      if (c.article_number) {
        label += `Статья ${c.article_number}`;
        if (c.point_number) label += `, п. ${c.point_number}`;
      } else {
        label += "ТК РК";
      }
      badge.textContent = `📜 ${label}`;
      badge.title = c.breadcrumb || c.article_name || "";
      sourcesBox.appendChild(badge);
    });

    bubble.appendChild(sourcesBox);
  }

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  messagesArea.appendChild(msgDiv);
  scrollToBottom();
}

function appendLoader() {
  const id = "loader-" + Date.now();
  const msgDiv = document.createElement("div");
  msgDiv.className = "message bot";
  msgDiv.id = id;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "⚖️";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `
    <div class="loading-box">
      <div class="spinner"></div>
      <span>Ищу статью в Трудовом кодексе РК...</span>
    </div>
  `;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  messagesArea.appendChild(msgDiv);
  scrollToBottom();
  return id;
}

function removeLoader(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatMessageContent(text) {
  // Экранирование HTML и замена переносов строк
  let clean = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Подсветка цитат [S1], [**S1**], [S2]
  clean = clean.replace(/\[(?:\*\*|\*)?(S\d+)(?:\*\*|\*)?\]/g, '<strong style="color:var(--primary); background: #EFF6FF; padding: 2px 6px; border-radius: 4px; border: 1px solid #BFDBFE;">[$1]</strong>');
  clean = clean.replace(/\n/g, "<br>");
  return clean;
}

function scrollToBottom() {
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

async function loadSessions() {
  if (!historyList) return;
  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) return;
    const sessions = await res.json();
    historyList.innerHTML = "";

    sessions.forEach(s => {
      const btn = document.createElement("button");
      btn.className = `chat-history-item ${s.id === currentSessionId ? "active" : ""}`;
      btn.textContent = `💬 ${s.title || "Диалог"}`;
      btn.title = s.title;
      btn.addEventListener("click", () => {
        currentSessionId = s.id;
        localStorage.setItem("trudpravo_session_id", currentSessionId);
        loadSessionMessages(s.id);
        loadSessions();
      });
      historyList.appendChild(btn);
    });
  } catch (e) {
    console.warn("Не удалось загрузить историю сессий", e);
  }
}

async function loadSessionMessages(sessionId) {
  try {
    const res = await fetch(`/api/chat/${sessionId}/messages`);
    if (!res.ok) return;
    const messages = await res.json();

    messagesArea.innerHTML = "";
    if (messages.length === 0 && welcomeScreen) {
      messagesArea.appendChild(welcomeScreen);
      welcomeScreen.style.display = "block";
      return;
    }

    if (welcomeScreen) welcomeScreen.style.display = "none";

    messages.forEach(m => {
      appendMessage(m.from_ai ? "bot" : "user", m.content, m.citations);
    });
  } catch (e) {
    console.error("Ошибка загрузки сообщений", e);
  }
}
