import { create } from "zustand";
import { api } from "../lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ title: string; content: string; score?: number }>;
}

interface SessionData {
  messages: ChatMessage[];
  sessionId?: string;
}

interface ChatState {
  sessions: Record<string, SessionData>;
  addMessage: (sessionKey: string, msg: ChatMessage) => void;
  setSessionId: (sessionKey: string, id: string) => void;
  clearSession: (sessionKey: string) => void;
  sendMessage: (
    sessionKey: string,
    question: string,
    searchMode?: string,
    topK?: number
  ) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: {},

  addMessage: (sessionKey: string, msg: ChatMessage) => {
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionKey]: {
          ...state.sessions[sessionKey],
          messages: [...(state.sessions[sessionKey]?.messages || []), msg],
        },
      },
    }));
  },

  setSessionId: (sessionKey: string, id: string) => {
    set((state) => ({
      sessions: {
        ...state.sessions,
        [sessionKey]: {
          ...state.sessions[sessionKey],
          sessionId: id,
          messages: state.sessions[sessionKey]?.messages || [],
        },
      },
    }));
  },

  clearSession: (sessionKey: string) => {
    set((state) => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [sessionKey]: _, ...rest } = state.sessions;
      return { sessions: rest };
    });
  },

  sendMessage: async (
    sessionKey: string,
    question: string,
    searchMode?: string,
    topK?: number
  ) => {
    const { addMessage, sessions } = get();

    addMessage(sessionKey, { role: "user", content: question });

    try {
      const payload: Record<string, unknown> = {
        question,
        search_mode: searchMode || "hybrid",
        top_k: topK || 5,
      };

      const sessionId = sessions[sessionKey]?.sessionId;
      if (sessionId) {
        payload.session_id = sessionId;
      }

      const response = await api.post("/chat/send", payload);

      const { answer, sources, session_id } = response.data;

      addMessage(sessionKey, {
        role: "assistant",
        content: answer,
        sources,
      });

      if (session_id) {
        get().setSessionId(sessionKey, session_id);
      }
    } catch (error) {
      addMessage(sessionKey, {
        role: "assistant",
        content: "抱歉，请求处理失败，请稍后重试。",
      });
      throw error;
    }
  },
}));
