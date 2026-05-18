import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const CHAT_ENDPOINT = `${API_URL}/chat/`;
const CHAT_SESSION_STORAGE_KEY = 'tech-webbed-chat-session-id';
const INACTIVITY_TIMEOUT_MS = 3 * 60 * 1000;
console.log("API URL:", import.meta.env.VITE_API_URL);

function createMessage(role, text) {
  return {
    id: crypto.randomUUID(),
    role,
    text,
  };
}

function getChatSessionId() {
  try {
    const existingSessionId = window.sessionStorage.getItem(CHAT_SESSION_STORAGE_KEY);

    if (existingSessionId) {
      return existingSessionId;
    }

    const newSessionId = crypto.randomUUID();
    window.sessionStorage.setItem(CHAT_SESSION_STORAGE_KEY, newSessionId);
    return newSessionId;
  } catch (error) {
    return crypto.randomUUID();
  }
}

function extractName(value) {
  const cleaned = value
    .trim()
    .replace(/^(hi|hello|hey)[,\s]+/i, '')
    .replace(/^(my name is|name is|i am|i'm|this is)\s+/i, '')
    .replace(/\s+/g, ' ')
    .trim();
  const blockedWords = [
    'website',
    'marketing',
    'service',
    'price',
    'pricing',
    'package',
    'logo',
    'video',
    'automation',
    'help',
    'need',
    'want',
    'phone',
    'number',
    'contact',
    'mobile',
    'whatsapp',
  ];
  const words = cleaned.split(' ').filter(Boolean);
  const letterCount = (cleaned.match(/[a-zA-Z]/g) || []).length;
  const hasBlockedWord = blockedWords.some((word) => new RegExp(`\\b${word}\\b`, 'i').test(cleaned));
  const hasOnlyNameCharacters = /^[a-zA-Z .'-]+$/.test(cleaned);
  const hasValidNameWords = words.every((word) => /^[a-zA-Z][a-zA-Z.'-]*$/.test(word));

  if (
    letterCount < 2 ||
    cleaned.length > 80 ||
    words.length > 4 ||
    hasBlockedWord ||
    !hasOnlyNameCharacters ||
    !hasValidNameWords
  ) {
    return '';
  }

  return cleaned;
}

function normalizePhoneNumber(value) {
  const trimmed = value.trim();
  const digits = trimmed.replace(/\D/g, '');

  if (!/^\+?[\d\s().-]+$/.test(trimmed) || digits.length < 10 || digits.length > 15) {
    return '';
  }

  return trimmed.startsWith('+') ? `+${digits}` : digits;
}

function ChatbotWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [hasOpened, setHasOpened] = useState(false);
  const [leadId, setLeadId] = useState(null);
  const [leadDetails, setLeadDetails] = useState({ name: '', phone: '' });
  const [onboardingStep, setOnboardingStep] = useState('greeting');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isEnded, setIsEnded] = useState(false);
  const sessionIdRef = useRef(getChatSessionId());
  const requestCounterRef = useRef(0);
  const activeRequestRef = useRef(null);
  const leadCaptureRequestRef = useRef(null);
  const inactivityTimerRef = useRef(null);
  const endChatInProgressRef = useRef(false);
  const exitEndAttemptedRef = useRef(false);
  const latestChatStateRef = useRef({
    leadId: null,
    leadDetails: { name: '', phone: '' },
    messages: [],
    isSending: false,
    isEnded: false,
  });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    latestChatStateRef.current = {
      leadId,
      leadDetails,
      messages,
      isSending,
      isEnded,
    };
  }, [leadId, leadDetails, messages, isSending, isEnded]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  useEffect(() => {
    function handleBeforeUnload() {
      sendExitEndChat('beforeunload');
    }

    function handlePageHide() {
      sendExitEndChat('pagehide');
    }

    function handleVisibilityChange() {
      if (document.visibilityState === 'hidden') {
        sendExitEndChat('visibilitychange');
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('pagehide', handlePageHide);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('pagehide', handlePageHide);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    clearInactivityTimer();

    const lastMessage = messages[messages.length - 1];
    const canAutoEnd =
      !isSending &&
      !isEnded &&
      onboardingStep === 'ready' &&
      leadDetails.name &&
      leadDetails.phone &&
      lastMessage?.role === 'bot';

    if (!canAutoEnd) {
      return undefined;
    }

    console.log('[Tech Webbed Chat] inactivity timer started');
    inactivityTimerRef.current = window.setTimeout(() => {
      console.log('[Tech Webbed Chat] inactivity trigger fired');
      endChat({ automatic: true });
    }, INACTIVITY_TIMEOUT_MS);

    return clearInactivityTimer;
  }, [messages, isSending, isEnded, onboardingStep, leadDetails.name, leadDetails.phone]);

  useEffect(() => clearInactivityTimer, []);

  function clearInactivityTimer() {
    if (inactivityTimerRef.current) {
      window.clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }
  }

  function openChat() {
    setIsOpen(true);

    if (!hasOpened) {
      setHasOpened(true);
      setMessages([
        createMessage('bot', 'Hi, I am the Tech Webbed AI Assistant.'),
      ]);
    }
  }

  function addMessage(role, text) {
    const message = createMessage(role, text);

    setMessages((currentMessages) => {
      const nextMessages = [...currentMessages, message];
      latestChatStateRef.current = {
        ...latestChatStateRef.current,
        messages: nextMessages,
      };
      return nextMessages;
    });
  }

  function buildEndChatPayload(currentChatState) {
    return {
      action: 'end_chat',
      session_id: sessionIdRef.current,
      lead_id: currentChatState.leadId,
      name: currentChatState.leadDetails.name,
      phone: currentChatState.leadDetails.phone,
      conversation: currentChatState.messages,
    };
  }

  function shouldSendExitEndChat(currentChatState) {
    const hasLeadContact = currentChatState.leadDetails.name && currentChatState.leadDetails.phone;
    const hasConversation = currentChatState.messages.some(
      (message) => message.role !== 'status' && message.text?.trim()
    );

    return (
      hasLeadContact &&
      hasConversation &&
      !currentChatState.isEnded &&
      !endChatInProgressRef.current &&
      !exitEndAttemptedRef.current
    );
  }

  function sendExitEndChat(trigger) {
    const currentChatState = latestChatStateRef.current;

    if (!shouldSendExitEndChat(currentChatState)) {
      return;
    }

    console.log('[Tech Webbed Chat] unload trigger fired', trigger);
    exitEndAttemptedRef.current = true;
    latestChatStateRef.current = {
      ...currentChatState,
      isEnded: true,
    };
    setIsEnded(true);
    clearInactivityTimer();

    const body = JSON.stringify({
      ...buildEndChatPayload(currentChatState),
      trigger,
    });
    const beaconBody = new Blob([body], { type: 'text/plain;charset=UTF-8' });

    if (navigator.sendBeacon?.(CHAT_ENDPOINT, beaconBody)) {
      console.log('[Tech Webbed Chat] unload beacon queued', trigger);
      return;
    }

    console.log('[Tech Webbed Chat] unload keepalive fetch queued', trigger);
    fetch(CHAT_ENDPOINT, {
      method: 'POST',
      body,
      headers: {
        'Content-Type': 'text/plain;charset=UTF-8',
      },
      keepalive: true,
    }).catch(() => {});
  }

  async function postChat(payload) {
    requestCounterRef.current += 1;
    const requestId = requestCounterRef.current;
    console.log('[Tech Webbed Chat] fetch starts', requestId, payload.action || 'message');

    const response = await fetch(CHAT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    console.log('[Tech Webbed Chat] fetch completes', requestId, response.status);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Unable to connect right now.');
    }

    return response.json();
  }

  async function captureLead(details) {
    if (!details.name || !details.phone || leadCaptureRequestRef.current) {
      return;
    }

    console.log('[Tech Webbed Chat] lead capture request starts');

    try {
      const request = postChat({
        action: 'capture_lead',
        session_id: sessionIdRef.current,
        lead_id: leadId,
        name: details.name,
        phone: details.phone,
      });
      leadCaptureRequestRef.current = request;

      const data = await request;
      setLeadId(data.lead_id);
      latestChatStateRef.current = {
        ...latestChatStateRef.current,
        leadId: data.lead_id,
      };
      console.log('[Tech Webbed Chat] lead capture saved');
    } catch (error) {
      console.warn('[Tech Webbed Chat] lead capture failed', error.message || error);
    } finally {
      leadCaptureRequestRef.current = null;
    }
  }

  async function sendMessage() {
    const text = inputValue.trim();

    if (!text || isSending || isEnded || activeRequestRef.current) {
      console.log('[Tech Webbed Chat] duplicate or empty send blocked', {
        hasText: Boolean(text),
        isSending,
        isEnded,
        hasActiveRequest: Boolean(activeRequestRef.current),
      });
      return;
    }

    clearInactivityTimer();
    addMessage('user', text);
    setInputValue('');

    if (onboardingStep === 'greeting') {
      setOnboardingStep('name');
      addMessage('bot', 'May I know your name?');
      return;
    }

    if (onboardingStep === 'name') {
      const name = extractName(text);

      if (!name) {
        addMessage('bot', 'Please enter your name only to continue.');
        return;
      }

      const nextLeadDetails = { ...leadDetails, name };
      setLeadDetails(nextLeadDetails);
      latestChatStateRef.current = {
        ...latestChatStateRef.current,
        leadDetails: nextLeadDetails,
      };
      setOnboardingStep('phone');
      addMessage('bot', `Thanks, ${name}. May I know your WhatsApp number for better assistance?`);
      return;
    }

    if (onboardingStep === 'phone') {
      const phone = normalizePhoneNumber(text);

      if (!phone) {
        addMessage('bot', 'Please enter a valid WhatsApp number only to continue.');
        return;
      }

      const nextLeadDetails = { ...leadDetails, phone };
      setLeadDetails(nextLeadDetails);
      latestChatStateRef.current = {
        ...latestChatStateRef.current,
        leadDetails: nextLeadDetails,
      };
      setOnboardingStep('ready');
      addMessage('bot', 'Thanks. How can I help you today?');
      captureLead(nextLeadDetails);
      return;
    }

    setIsSending(true);

    const statusId = crypto.randomUUID();
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: statusId,
        role: 'status',
        text: 'Tech Webbed is typing...',
      },
    ]);

    try {
      activeRequestRef.current = postChat({
        action: 'message',
        session_id: sessionIdRef.current,
        lead_id: leadId,
        name: leadDetails.name,
        phone: leadDetails.phone,
        message: text,
      });

      const data = await activeRequestRef.current;
      setLeadId(data.lead_id);
      setMessages((currentMessages) =>
        currentMessages
          .filter((message) => message.id !== statusId)
          .concat({
            id: crypto.randomUUID(),
            role: 'bot',
            text: data.response,
          })
      );
    } catch (error) {
      setMessages((currentMessages) =>
        currentMessages
          .filter((message) => message.id !== statusId)
          .concat({
            id: crypto.randomUUID(),
            role: 'bot',
            text:
              error.message === 'Failed to fetch'
                ? 'Unable to reach Tech Webbed chat. Please make sure the backend server is running.'
                : error.message || 'Sorry, something went wrong. Please try again.',
          })
      );
    } finally {
      activeRequestRef.current = null;
      setIsSending(false);
    }
  }

  function handleInputKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      console.log('[Tech Webbed Chat] Enter pressed');
      sendMessage();
    }
  }

  function handleSendClick(event) {
    event.preventDefault();
    console.log('[Tech Webbed Chat] Send button clicked');
    sendMessage();
  }

  async function endChat(options = {}) {
    const automatic = options?.automatic === true;
    const trigger = automatic ? 'inactivity' : 'button';
    const currentChatState = latestChatStateRef.current;

    if (
      currentChatState.isSending ||
      currentChatState.isEnded ||
      activeRequestRef.current ||
      endChatInProgressRef.current
    ) {
      return;
    }

    clearInactivityTimer();
    console.log('[Tech Webbed Chat] end chat trigger fired', trigger);
    endChatInProgressRef.current = true;
    setIsSending(true);
    const statusId = crypto.randomUUID();
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: statusId,
        role: 'status',
        text: automatic ? 'Ending inactive chat...' : 'Ending chat...',
      },
    ]);

    try {
      const data = await postChat({
        ...buildEndChatPayload(currentChatState),
        trigger,
      });
      console.log('[Tech Webbed Chat] end chat result', data);

      setIsEnded(true);
      setMessages((currentMessages) =>
        currentMessages
          .filter((message) => message.id !== statusId)
          .concat({
            id: crypto.randomUUID(),
            role: 'bot',
            text: data.response || 'Thank you. Our Tech Webbed team will connect with you shortly for detailed discussion.',
          })
      );
    } catch (error) {
      setMessages((currentMessages) =>
        currentMessages
          .filter((message) => message.id !== statusId)
          .concat({
            id: crypto.randomUUID(),
            role: 'bot',
            text: error.message || 'Unable to end the chat right now. Please try again.',
          })
      );
    } finally {
      endChatInProgressRef.current = false;
      setIsSending(false);
    }
  }

  return (
    <div className="tw-chatbot" aria-live="polite">
      {!isOpen && (
        <button className="tw-chatbot__launcher" type="button" aria-label="Open Tech Webbed chat" onClick={openChat}>
          <span className="tw-chatbot__launcher-icon" aria-hidden="true">
            TW
          </span>
        </button>
      )}

      {isOpen && (
        <section className="tw-chatbot__panel" aria-label="Tech Webbed chatbot">
          <header className="tw-chatbot__header">
            <div>
              <p className="tw-chatbot__eyebrow">AI Chatbot</p>
              <h1>Tech Webbed AI Assistant</h1>
            </div>
            <button className="tw-chatbot__close" type="button" aria-label="Close chat" onClick={() => setIsOpen(false)}>
              x
            </button>
          </header>

          <main className="tw-chatbot__messages" aria-label="Chat messages">
            {messages.map((message) => (
              <div key={message.id} className={`tw-chatbot__message tw-chatbot__message--${message.role}`}>
                {message.text}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </main>

          <div className="tw-chatbot__composer">
            <input
              className="tw-chatbot__input"
              type="text"
              value={inputValue}
              disabled={isSending || isEnded}
              autoComplete="off"
              placeholder="Type your message..."
              aria-label="Message"
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleInputKeyDown}
            />
            <button
              className="tw-chatbot__send"
              type="button"
              disabled={isSending || isEnded}
              onClick={handleSendClick}
            >
              Send
            </button>
          </div>

          <button
            className="tw-chatbot__end"
            type="button"
            disabled={isSending || isEnded || messages.length === 0}
            onClick={endChat}
          >
            End chat
          </button>
        </section>
      )}
    </div>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ChatbotWidget />
  </React.StrictMode>
);
