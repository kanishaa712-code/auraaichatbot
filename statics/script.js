/* Aura AI - front-end logic
   HTML ids used: chatForm, userInput, sendBtn, messages, chatWindow,
   welcome, chatPanel, newChatBtn, clearBtn  |  class: .suggestion[data-question]
   API: POST /api/chat  { "message": "..." }  ->  { "answer": "...", "score": 0.82 } */

(() => {
  "use strict";

  // ---------- 1. Select elements ----------
  const form = document.getElementById("chatForm");
  const input = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const messages = document.getElementById("messages");
  const chatWindow = document.getElementById("chatWindow");
  const welcome = document.getElementById("welcome");
  const chatPanel = document.getElementById("chatPanel");
  const newChatBtn = document.getElementById("newChatBtn");
  const clearBtn = document.getElementById("clearBtn");
  const suggestions = document.querySelectorAll(".suggestion");

  const API_URL = "/api/chat";
  const AVATAR_SRC = document.querySelector(".hero-bot img")?.getAttribute("src") || "/statics/ai.png";
  const REQUEST_TIMEOUT_MS = 15000;
  const MAX_INPUT_HEIGHT = 140;

  let isLoading = false;

  // ---------- helpers ----------
  const scrollToBottom = () => {
    chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: "smooth" });
  };

  const autoResize = () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, MAX_INPUT_HEIGHT) + "px";
  };

  const updateSendState = () => {
    sendBtn.disabled = isLoading || input.value.trim() === "";
  };

  const setLoading = (value) => {
    isLoading = value;
    chatPanel.classList.toggle("is-loading", value);
    updateSendState();
  };

  const showConversation = () => {
    welcome.hidden = true;
    chatPanel.classList.add("is-active");
  };

  // Bot avatar; hides the broken-image icon if ai.png is missing.
  const createBotAvatar = () => {
    const avatar = document.createElement("span");
    avatar.className = "avatar avatar--sm";
    const img = document.createElement("img");
    img.src = AVATAR_SRC;
    img.alt = "Aura AI";
    img.addEventListener("error", () => {
      img.remove();
      avatar.textContent = "A";
    });
    avatar.appendChild(img);
    return avatar;
  };

  const createUserAvatar = () => {
    const avatar = document.createElement("span");
    avatar.className = "avatar avatar--user";
    avatar.textContent = "You";
    avatar.setAttribute("aria-hidden", "true");
    return avatar;
  };

  // ---------- message rendering ----------
  const addMessage = (text, role, extraClass = "") => {
    const row = document.createElement("div");
    row.className = `message message--${role} ${extraClass}`.trim();

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text; // textContent = no HTML injection

    if (role === "bot") {
      row.append(createBotAvatar(), bubble);
    } else {
      row.append(bubble, createUserAvatar());
    }

    messages.appendChild(row);
    scrollToBottom();
    return row;
  };

  const showTyping = () => {
    const row = document.createElement("div");
    row.id = "typingIndicator";
    row.className = "message message--bot";

    const bubble = document.createElement("div");
    bubble.className = "bubble bubble--typing";
    bubble.setAttribute("aria-label", "Aura is typing");
    bubble.innerHTML = "<span></span><span></span><span></span>";

    row.append(createBotAvatar(), bubble);
    messages.appendChild(row);
    scrollToBottom();
  };

  const removeTyping = () => {
    document.getElementById("typingIndicator")?.remove();
  };

  // ---------- API call ----------
  const requestAnswer = async (text) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
        signal: controller.signal,
      });

      let data = {};
      try {
        data = await response.json();
      } catch (_) { /* non-JSON error body */ }

      if (!response.ok) {
        throw new Error(data.error || "Something went wrong. Please try again.");
      }
      return data.answer;
    } finally {
      clearTimeout(timer);
    }
  };

  // ---------- main send flow ----------
  const sendMessage = async (rawText) => {
    const text = rawText.trim();
    if (!text || isLoading) return;

    showConversation();
    addMessage(text, "user");

    input.value = "";
    autoResize();
    setLoading(true);
    showTyping();

    try {
      const answer = await requestAnswer(text);
      removeTyping();
      addMessage(answer, "bot");
    } catch (error) {
      removeTyping();
      const message =
        error.name === "AbortError"
          ? "That took too long. Please try again."
          : error instanceof TypeError
            ? "I can't reach the server right now. Check your connection and try again."
            : error.message;
      addMessage(message, "bot", "message--error");
    } finally {
      setLoading(false);
      input.focus();
    }
  };

  // ---------- new / clear conversation ----------
  const resetConversation = () => {
    messages.innerHTML = "";
    welcome.hidden = false;
    chatPanel.classList.remove("is-active");
    input.value = "";
    autoResize();
    setLoading(false);
    chatWindow.scrollTo({ top: 0 });
    input.focus();
  };

  // ---------- events ----------
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  input.addEventListener("input", () => {
    autoResize();
    updateSendState();
  });

  suggestions.forEach((card) => {
    card.addEventListener("click", () => sendMessage(card.dataset.question));
  });

  newChatBtn.addEventListener("click", resetConversation);
  clearBtn.addEventListener("click", resetConversation);

  // initial state
  updateSendState();
  input.focus();
})();
