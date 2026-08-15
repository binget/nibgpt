import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  deleteConversation,
  getConversation,
  getConversations,
  sendChatMessage,
} from "../../services/chat";

import type {
  ChatMessage,
  ConversationSummary,
} from "../../types/chat";


function ChatPage() {
  const [conversations, setConversations] = useState<
    ConversationSummary[]
  >([]);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeConversationId, setActiveConversationId] =
    useState<number | null>(null);

  const [prompt, setPrompt] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [sending, setSending] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const loadConversations = async () => {
    try {
      const result = await getConversations();
      setConversations(result);
    } catch {
      setErrorMessage(
        "Unable to load conversation history."
      );
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, sending]);

  const openConversation = async (
    conversationId: number
  ) => {
    try {
      setErrorMessage("");
      setActiveConversationId(conversationId);

      const conversation = await getConversation(
        conversationId
      );

      setMessages(conversation.messages);
    } catch {
      setErrorMessage(
        "Unable to open the selected conversation."
      );
    }
  };

  const startNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setPrompt("");
    setErrorMessage("");
  };

  const submitPrompt = async () => {
    const cleanedPrompt = prompt.trim();

    if (!cleanedPrompt || sending) {
      return;
    }

    setErrorMessage("");
    setPrompt("");

    const temporaryUserMessage: ChatMessage = {
      id: Date.now(),
      conversation_id:
        activeConversationId ?? 0,
      role: "user",
      content: cleanedPrompt,
      source_type: "user",
      created_at: new Date().toISOString(),
    };

    setMessages((current) => [
      ...current,
      temporaryUserMessage,
    ]);

    try {
      setSending(true);

      const result = await sendChatMessage(
        cleanedPrompt,
        activeConversationId
      );

      setActiveConversationId(
        result.conversation_id
      );

      setMessages((current) => [
        ...current,
        result.message,
      ]);

      await loadConversations();
    } catch (error: any) {
      setErrorMessage(
        error?.response?.data?.detail ??
          "NIBGPT could not process the prompt."
      );
    } finally {
      setSending(false);
    }
  };

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    await submitPrompt();
  };

  const handlePromptKeyDown = async (
    event: KeyboardEvent<HTMLDivElement>
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      await submitPrompt();
    }
  };

  const handleDeleteConversation = async (
    conversationId: number
  ) => {
    try {
      await deleteConversation(conversationId);

      if (
        activeConversationId === conversationId
      ) {
        startNewConversation();
      }

      await loadConversations();
    } catch {
      setErrorMessage(
        "Unable to delete the conversation."
      );
    }
  };

  return (
    <Box
      sx={{
        height: "calc(100vh - 145px)",
        minHeight: 600,
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          lg: "290px minmax(0, 1fr)",
        },
        gap: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          display: {
            xs: "none",
            lg: "flex",
          },
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 3,
          border: "1px solid #e9e2da",
        }}
      >
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            variant="contained"
            onClick={startNewConversation}
            sx={{
              py: 1.2,
              borderRadius: 2,
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            + New conversation
          </Button>
        </Box>

        <Divider />

        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            p: 1.2,
          }}
        >
          {loadingHistory ? (
            <Box
              sx={{
                py: 4,
                textAlign: "center",
              }}
            >
              <CircularProgress
                size={24}
                sx={{ color: "#a97826" }}
              />
            </Box>
          ) : conversations.length === 0 ? (
            <Typography
              variant="body2"
              sx={{
                p: 2,
                color: "#888888",
                textAlign: "center",
              }}
            >
              No previous conversations.
            </Typography>
          ) : (
            conversations.map((conversation) => {
              const selected =
                activeConversationId ===
                conversation.id;

              return (
                <Box
                  key={conversation.id}
                  sx={{
                    mb: 0.7,
                    p: 1.4,
                    borderRadius: 2,
                    cursor: "pointer",
                    bgcolor: selected
                      ? "#fff2d8"
                      : "transparent",
                    border: selected
                      ? "1px solid #e6c680"
                      : "1px solid transparent",
                    "&:hover": {
                      bgcolor: selected
                        ? "#fff2d8"
                        : "#f7f4ef",
                    },
                  }}
                >
                  <Box
                    onClick={() =>
                      openConversation(
                        conversation.id
                      )
                    }
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        color: "#4f2c1a",
                        fontWeight: 700,
                        overflow: "hidden",
                        whiteSpace: "nowrap",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {conversation.title}
                    </Typography>

                    <Typography
                      variant="caption"
                      sx={{ color: "#999999" }}
                    >
                      {new Date(
                        conversation.updated_at
                      ).toLocaleString()}
                    </Typography>
                  </Box>

                  {selected && (
                    <Button
                      size="small"
                      color="error"
                      onClick={() =>
                        handleDeleteConversation(
                          conversation.id
                        )
                      }
                      sx={{
                        mt: 0.7,
                        p: 0,
                        minWidth: 0,
                        textTransform: "none",
                        fontSize: "0.72rem",
                      }}
                    >
                      Delete
                    </Button>
                  )}
                </Box>
              );
            })
          )}
        </Box>
      </Paper>

      <Paper
        elevation={0}
        sx={{
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          borderRadius: 3,
          border: "1px solid #e9e2da",
          bgcolor: "#ffffff",
        }}
      >
        <Box
          sx={{
            px: 3,
            py: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #eee7df",
          }}
        >
          <Box>
            <Typography
              variant="h5"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              NibGPT AI Workspace
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: "#777777" }}
            >
              Secure prompt-driven intelligence
            </Typography>
          </Box>

          <Box
            sx={{
              px: 1.5,
              py: 0.7,
              borderRadius: 5,
              bgcolor: "#e7f6ed",
              color: "#207744",
              fontSize: "0.78rem",
              fontWeight: 800,
            }}
          >
            ● Platform online
          </Box>
        </Box>

        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            px: {
              xs: 2,
              md: 4,
            },
            py: 3,
            bgcolor: "#fcfbf9",
          }}
        >
          {errorMessage && (
            <Alert
              severity="error"
              sx={{ mb: 2 }}
              onClose={() =>
                setErrorMessage("")
              }
            >
              {errorMessage}
            </Alert>
          )}

          {messages.length === 0 ? (
            <WelcomePanel
              onPromptSelect={(value) =>
                setPrompt(value)
              }
            />
          ) : (
            messages.map((message) => (
              <MessageBubble
                key={`${message.role}-${message.id}`}
                message={message}
              />
            ))
          )}

          {sending && (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                mb: 2,
              }}
            >
              <Box
                sx={{
                  width: 38,
                  height: 38,
                  borderRadius: 2,
                  display: "grid",
                  placeItems: "center",
                  color: "#ffffff",
                  fontWeight: 900,
                  background:
                    "linear-gradient(145deg, #60351f, #d3a034)",
                }}
              >
                AI
              </Box>

              <Paper
                elevation={0}
                sx={{
                  px: 2,
                  py: 1.5,
                  borderRadius: 3,
                  border: "1px solid #e9e2da",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    gap: 1,
                    alignItems: "center",
                  }}
                >
                  <CircularProgress
                    size={16}
                    sx={{ color: "#a97826" }}
                  />

                  <Typography
                    variant="body2"
                    sx={{ color: "#777777" }}
                  >
                    NIBGPT is processing...
                  </Typography>
                </Box>
              </Paper>
            </Box>
          )}

          <div ref={messagesEndRef} />
        </Box>

        <Box
          component="form"
          onSubmit={handleSubmit}
          sx={{
            p: 2.5,
            borderTop: "1px solid #eee7df",
            bgcolor: "#ffffff",
          }}
        >
          <Box
            sx={{
              display: "flex",
              gap: 1.5,
              alignItems: "flex-end",
            }}
          >
            <TextField
              fullWidth
              multiline
              maxRows={6}
              value={prompt}
              disabled={sending}
              onChange={(event) =>
                setPrompt(event.target.value)
              }
              onKeyDown={handlePromptKeyDown}
              placeholder="Ask NIBGPT about data sources, reports, policies or banking information..."
              slotProps={{
                input: {
                  sx: {
                    borderRadius: 3,
                    bgcolor: "#faf8f5",
                  },
                },
              }}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={
                sending || !prompt.trim()
              }
              sx={{
                minWidth: 110,
                height: 56,
                borderRadius: 2.5,
                textTransform: "none",
                fontWeight: 800,
                background:
                  "linear-gradient(90deg, #61351f, #c78f2b)",
              }}
            >
              {sending ? "Wait..." : "Send"}
            </Button>
          </Box>

          <Typography
            variant="caption"
            sx={{
              display: "block",
              mt: 1,
              color: "#999999",
              textAlign: "center",
            }}
          >
            NIBGPT can make mistakes. Validate
            critical financial and regulatory outputs.
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}


interface WelcomePanelProps {
  onPromptSelect: (prompt: string) => void;
}

function WelcomePanel({
  onPromptSelect,
}: WelcomePanelProps) {
  const prompts = [
    "Show me the available data sources",
    "What can NIBGPT currently do?",
    "Generate a monthly deposit report",
    "How will NIBGPT connect to Oracle?",
  ];

  return (
    <Box
      sx={{
        maxWidth: 760,
        mx: "auto",
        pt: {
          xs: 2,
          md: 7,
        },
        textAlign: "center",
      }}
    >
      <Box
        sx={{
          width: 86,
          height: 86,
          mx: "auto",
          mb: 2.5,
          borderRadius: 4,
          display: "grid",
          placeItems: "center",
          color: "#ffffff",
          fontSize: "1.5rem",
          fontWeight: 900,
          background:
            "linear-gradient(145deg, #60351f, #d3a034)",
          boxShadow:
            "0 16px 40px rgba(104, 61, 29, 0.22)",
        }}
      >
        AI
      </Box>

      <Typography
        variant="h3"
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
          letterSpacing: "-1px",
        }}
      >
        How can NibGPT help?
      </Typography>

      <Typography
        sx={{
          mt: 1.5,
          color: "#777777",
          lineHeight: 1.8,
        }}
      >
        Ask about connected systems, institutional
        knowledge, reports and the NIBGPT platform.
      </Typography>

      <Box
        sx={{
          mt: 4,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(2, 1fr)",
          },
          gap: 1.5,
        }}
      >
        {prompts.map((suggestedPrompt) => (
          <Paper
            key={suggestedPrompt}
            elevation={0}
            onClick={() =>
              onPromptSelect(suggestedPrompt)
            }
            sx={{
              p: 2,
              textAlign: "left",
              borderRadius: 2.5,
              border: "1px solid #e8dfd5",
              cursor: "pointer",
              transition: "all 0.2s ease",
              "&:hover": {
                transform: "translateY(-2px)",
                borderColor: "#c99945",
                boxShadow:
                  "0 10px 24px rgba(83, 48, 26, 0.08)",
              },
            }}
          >
            <Typography
              variant="body2"
              sx={{
                color: "#5b311b",
                fontWeight: 700,
              }}
            >
              {suggestedPrompt}
            </Typography>
          </Paper>
        ))}
      </Box>
    </Box>
  );
}


interface MessageBubbleProps {
  message: ChatMessage;
}

function MessageBubble({
  message,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: isUser
          ? "row-reverse"
          : "row",
        gap: 1.5,
        alignItems: "flex-start",
        mb: 2.5,
      }}
    >
      <Box
        sx={{
          width: 38,
          height: 38,
          flexShrink: 0,
          borderRadius: 2,
          display: "grid",
          placeItems: "center",
          fontWeight: 900,
          color: "#ffffff",
          bgcolor: isUser
            ? "#805232"
            : undefined,
          background: isUser
            ? undefined
            : "linear-gradient(145deg, #60351f, #d3a034)",
        }}
      >
        {isUser ? "U" : "AI"}
      </Box>

      <Box
        sx={{
          maxWidth: {
            xs: "82%",
            md: "72%",
          },
        }}
      >
        <Paper
          elevation={0}
          sx={{
            px: 2.2,
            py: 1.7,
            borderRadius: 3,
            bgcolor: isUser
              ? "#5b311b"
              : "#ffffff",
            color: isUser
              ? "#ffffff"
              : "#333333",
            border: isUser
              ? "none"
              : "1px solid #e9e2da",
          }}
        >
          <Typography
            component="div"
            variant="body1"
            sx={{
              lineHeight: 1.75,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {message.content}
          </Typography>
        </Paper>

        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 0.5,
            px: 0.5,
            color: "#999999",
            textAlign: isUser
              ? "right"
              : "left",
          }}
        >
          {new Date(
            message.created_at
          ).toLocaleTimeString()}
        </Typography>
      </Box>
    </Box>
  );
}

export default ChatPage;
