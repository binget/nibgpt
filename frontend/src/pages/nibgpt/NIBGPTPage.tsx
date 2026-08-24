import {
  AutoAwesomeOutlined,
  DeleteOutlined,
  EditOutlined,
  MoreVert,
  SendOutlined,
  SmartToyOutlined,
} from "@mui/icons-material";

import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

import {
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  askNIBGPT,
  streamNIBGPT,
  streamReportExplanation,
} from "../../services/orchestrator";

import {
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
  renameConversation,
  saveConversationMessage,
} from "../../services/chat";

import type {
  ConversationSummary,
} from "../../types/chat";

import type {
  OrchestratorReport,
  ReportingContext,
} from "../../services/orchestrator";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ReportTable from "../../components/ReportTable";


type MessageRoute =
  | "reporting"
  | "knowledge"
  | "general";


type NIBGPTMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: MessageRoute;
  report?: OrchestratorReport;
  createdAt: string;
  isStreaming?: boolean;
};


function createMessageId(
  prefix: string
): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return (
    `${prefix}-${Date.now()}-` +
    `${Math.random()
      .toString(36)
      .slice(2)}`
  );
}


function formatCellValue(
  value: unknown
): string {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (typeof value === "number") {
    return value.toLocaleString(
      "en-US",
      {
        maximumFractionDigits: 2,
      }
    );
  }

  return String(value);
}


export default function NIBGPTPage() {
  const [prompt, setPrompt] =
    useState("");

  const [messages, setMessages] =
    useState<NIBGPTMessage[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [
    reportingContext,
    setReportingContext,
  ] = useState<ReportingContext | null>(
    null
  );

  const [
    activeConversationId,
    setActiveConversationId,
  ] = useState<number | null>(
    null
  );

  const [
    conversations,
    setConversations,
  ] = useState<ConversationSummary[]>(
    []
  );

  const [
    conversationsLoading,
    setConversationsLoading,
  ] = useState(false);


  const [
    conversationMenuAnchor,
    setConversationMenuAnchor,
  ] = useState<HTMLElement | null>(null);

  const [
    menuConversation,
    setMenuConversation,
  ] = useState<ConversationSummary | null>(null);

  const [
    renameDialogOpen,
    setRenameDialogOpen,
  ] = useState(false);

  const [
    renameTitle,
    setRenameTitle,
  ] = useState("");

  const [
    deleteDialogOpen,
    setDeleteDialogOpen,
  ] = useState(false);

  const conversationEndRef =
    useRef<HTMLDivElement | null>(
      null
    );

 


  
  const conversationScrollRef =
    useRef<HTMLDivElement | null>(
      null
    );

  const shouldAutoScrollRef =
    useRef(true);


  const handleConversationScroll = () => {
    const container =
      conversationScrollRef.current;

    if (!container) {
      return;
    }

    const distanceFromBottom =
      container.scrollHeight -
      container.scrollTop -
      container.clientHeight;

    shouldAutoScrollRef.current =
      distanceFromBottom < 120;
  };


  const scrollToConversationEnd = (
    behavior: ScrollBehavior = "smooth"
  ) => {
    if (!shouldAutoScrollRef.current) {
      return;
    }

    conversationEndRef.current
      ?.scrollIntoView({
        behavior,
        block: "end",
      });
  };

  const refreshConversations =
    async () => {
      try {
        setConversationsLoading(
          true
        );

        const items =
          await getConversations();

        setConversations(items);
      } catch (refreshError) {
        console.error(
          "Unable to load conversations:",
          refreshError
        );
      } finally {
        setConversationsLoading(
          false
        );
      }
    };


  useEffect(() => {
    void refreshConversations();
  }, []);


  const resolveStoredRoute = (
    sourceType: string | null
  ): MessageRoute | undefined => {
    if (
      sourceType === "reporting" ||
      sourceType === "knowledge" ||
      sourceType === "general"
    ) {
      return sourceType;
    }

    return undefined;
  };


  const openConversation =
    async (
      conversationId: number
    ) => {
      if (loading) {
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const conversation =
          await getConversation(
            conversationId
          );

        const restoredMessages: NIBGPTMessage[] =
          conversation.messages.map(
            (message): NIBGPTMessage => ({
              id: `saved-${message.id}`,
              role: message.role,
              content: message.content,
              route: resolveStoredRoute(message.source_type),
              report: message.report_payload
                ? (message.report_payload as unknown as OrchestratorReport)
                : undefined,
              createdAt: message.created_at,
              isStreaming: false,
            })
          );

        setActiveConversationId(
          conversation.id
        );

        setMessages(
          restoredMessages
        );

        /*
         * ReportingContext is not yet
         * persisted in chat_messages.
         * Reset it when reopening an
         * older conversation.
         */
        setReportingContext(
          null
        );

        shouldAutoScrollRef.current =
          true;

        setTimeout(() => {
          scrollToConversationEnd(
            "auto"
          );
        }, 50);
      } catch (openError) {
        const message =
          openError instanceof Error
            ? openError.message
            : (
                "Unable to open " +
                "conversation."
              );

        setError(message);
      } finally {
        setLoading(false);
      }
    };


  const ensureConversation =
    async (
      firstPrompt: string
    ): Promise<number> => {
      if (
        activeConversationId !==
        null
      ) {
        return activeConversationId;
      }

      const created =
        await createConversation(
          firstPrompt
        );

      setActiveConversationId(
        created.id
      );

      setConversations(
        (current) => [
          created,
          ...current.filter(
            (item) =>
              item.id !== created.id
          ),
        ]
      );

      return created.id;
    };


  const getConversationGroup = (
    dateValue: string
  ): "Today" | "Yesterday" | "Previous 7 Days" | "Older" => {
    const now = new Date();
    const date = new Date(dateValue);

    const today = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    );

    const itemDay = new Date(
      date.getFullYear(),
      date.getMonth(),
      date.getDate()
    );

    const diffDays = Math.floor(
      (today.getTime() - itemDay.getTime()) /
        86400000
    );

    if (diffDays <= 0) {
      return "Today";
    }

    if (diffDays === 1) {
      return "Yesterday";
    }

    if (diffDays <= 7) {
      return "Previous 7 Days";
    }

    return "Older";
  };


  const groupedConversations = [
    "Today",
    "Yesterday",
    "Previous 7 Days",
    "Older",
  ].map((label) => ({
    label,
    items: conversations.filter(
      (conversation) =>
        getConversationGroup(
          conversation.updated_at
        ) === label
    ),
  })).filter(
    (group) => group.items.length > 0
  );


  const openConversationMenu = (
    event: React.MouseEvent<HTMLElement>,
    conversation: ConversationSummary
  ) => {
    event.stopPropagation();
    setConversationMenuAnchor(
      event.currentTarget
    );
    setMenuConversation(
      conversation
    );
  };


  const closeConversationMenu = () => {
    setConversationMenuAnchor(null);
  };


  const beginRenameConversation = () => {
    if (!menuConversation) {
      return;
    }

    setRenameTitle(
      menuConversation.title
    );
    setRenameDialogOpen(true);
    closeConversationMenu();
  };


  const handleRenameConversation =
    async () => {
      if (
        !menuConversation ||
        !renameTitle.trim()
      ) {
        return;
      }

      try {
        setError(null);

        const updated =
          await renameConversation(
            menuConversation.id,
            renameTitle.trim()
          );

        setConversations(
          (current) =>
            current.map(
              (conversation) =>
                conversation.id ===
                updated.id
                  ? updated
                  : conversation
            )
        );

        setRenameDialogOpen(false);
        setMenuConversation(null);
      } catch (renameError) {
        setError(
          renameError instanceof Error
            ? renameError.message
            : "Unable to rename conversation."
        );
      }
    };


  const beginDeleteConversation = () => {
    if (!menuConversation) {
      return;
    }

    setDeleteDialogOpen(true);
    closeConversationMenu();
  };


  const handleDeleteConversation =
    async () => {
      if (!menuConversation) {
        return;
      }

      try {
        setError(null);

        await deleteConversation(
          menuConversation.id
        );

        setConversations(
          (current) =>
            current.filter(
              (conversation) =>
                conversation.id !==
                menuConversation.id
            )
        );

        if (
          activeConversationId ===
          menuConversation.id
        ) {
          resetConversation();
        }

        setDeleteDialogOpen(false);
        setMenuConversation(null);
      } catch (deleteError) {
        setError(
          deleteError instanceof Error
            ? deleteError.message
            : "Unable to delete conversation."
        );
      }
    };


const resetConversation = () => {
    shouldAutoScrollRef.current = true;

    setPrompt("");
    setMessages([]);
    setReportingContext(null);
    setActiveConversationId(
      null
    );
    setError(null);
    setLoading(false);
  };


  const addAssistantMessage = (
    message: NIBGPTMessage
  ) => {
    setMessages(
      (current) => [
        ...current,
        message,
      ]
    );
  };


  const streamGeneralResponse =
    async (
      cleanPrompt: string,
      conversationId: number
    ) => {
      const assistantId =
        createMessageId(
          "assistant"
        );

      let streamedContent = "";

      addAssistantMessage({
        id: assistantId,
        role: "assistant",
        content: "",
        route: "general",
        createdAt:
          new Date().toISOString(),
        isStreaming: true,
      });

      try {
        await streamNIBGPT(
  cleanPrompt,
  conversationId,
  {
    onToken: (token) => {
              if (!token) {
                return;
              }

              streamedContent +=
                token;

              setMessages(
                (current) =>
                  current.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            content:
                              message.content +
                              token,
                          }
                        : message
                  )
              );

              if (
                shouldAutoScrollRef.current
              ) {
                requestAnimationFrame(() => {
                  scrollToConversationEnd(
                    "auto"
                  );
                });
              }
            },

            onDone: () => {
              setMessages(
                (current) =>
                  current.map(
                    (message) =>
                      message.id ===
                      assistantId
                        ? {
                            ...message,
                            isStreaming:
                              false,
                          }
                        : message
                  )
              );
            },

            onError: (
              message
            ) => {
              setMessages(
                (current) =>
                  current.map(
                    (item) =>
                      item.id ===
                      assistantId
                        ? {
                            ...item,
                            content:
                              item.content ||
                              message,
                            isStreaming:
                              false,
                          }
                        : item
                  )
              );

              setError(message);
            },
          }
        );

        if (
          streamedContent.trim()
        ) {
          await saveConversationMessage(
            conversationId,
            "assistant",
            streamedContent,
            "general",
            null
          );

          await refreshConversations();
        }
      } catch (streamError) {
        const message =
          streamError instanceof Error
            ? streamError.message
            : (
                "Unable to stream " +
                "the NIBGPT response."
              );

        setError(message);

        setMessages(
          (current) =>
            current.map(
              (item) =>
                item.id ===
                assistantId
                  ? {
                      ...item,
                      content:
                        item.content ||
                        (
                          "I couldn't " +
                          "complete that " +
                          "request. Please " +
                          "try again."
                        ),
                      isStreaming:
                        false,
                    }
                  : item
            )
        );
      }
    };

  const streamReportingExplanation =
  async (
    conversationId: number,
    report: OrchestratorReport
  ) => {
    const assistantId =
      createMessageId(
        "assistant-report"
      );

    let explanation = "";

    /*
     * Display the report immediately.
     *
     * The explanation then streams above it.
     */
    addAssistantMessage({
      id: assistantId,
      role: "assistant",
      content: "",
      route: "reporting",
      report,
      createdAt:
        new Date().toISOString(),
      isStreaming: true,
    });

    try {
      await streamReportExplanation(
        report,
        {
          onToken: (token) => {
            if (!token) {
              return;
            }

            explanation +=
              token;

            setMessages(
              (current) =>
                current.map(
                  (message) =>
                    message.id ===
                    assistantId
                      ? {
                          ...message,
                          content:
                            message.content +
                            token,
                        }
                      : message
                )
            );

            if (
              shouldAutoScrollRef.current
            ) {
              requestAnimationFrame(
                () => {
                  scrollToConversationEnd(
                    "auto"
                  );
                }
              );
            }
          },

          onDone: () => {
            setMessages(
              (current) =>
                current.map(
                  (message) =>
                    message.id ===
                    assistantId
                      ? {
                          ...message,
                          isStreaming:
                            false,
                        }
                      : message
                )
            );
          },

          onError: () => {
            setMessages(
              (current) =>
                current.map(
                  (message) =>
                    message.id ===
                    assistantId
                      ? {
                          ...message,
                          content:
                            message.content ||
                            (
                              report.answer ||
                              "Report completed."
                            ),
                          isStreaming:
                            false,
                        }
                      : message
                )
            );
          },
        }
      );

      const finalContent =
        explanation.trim() ||
        report.answer ||
        "Report completed.";

      await saveConversationMessage(
        conversationId,
        "assistant",
        finalContent,
        "reporting",
        report
      );

      await refreshConversations();
    } catch (
      explanationError
    ) {
      console.error(
        "Report explanation error:",
        explanationError
      );

      const fallback =
        report.answer ||
        "Report completed.";

      setMessages(
        (current) =>
          current.map(
            (message) =>
              message.id ===
              assistantId
                ? {
                    ...message,
                    content:
                      message.content ||
                      fallback,
                    isStreaming:
                      false,
                  }
                : message
          )
      );

      await saveConversationMessage(
        conversationId,
        "assistant",
        fallback,
        "reporting",
        report
      );
    }
  };


  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const cleanPrompt =
      prompt.trim();

    if (
      !cleanPrompt ||
      loading
    ) {
      return;
    }

    

    const previousUserPrompt =
      [...messages]
        .reverse()
        .find(
          (message) =>
            message.role ===
            "user"
        )
        ?.content ?? null;

    const userMessage:
      NIBGPTMessage = {
        id: createMessageId(
          "user"
        ),
        role: "user",
        content: cleanPrompt,
        createdAt:
          new Date().toISOString(),
      };

    setMessages(
      (current) => [
        ...current,
        userMessage,
      ]
    );

    shouldAutoScrollRef.current = true;

    setTimeout(() => {
      scrollToConversationEnd(
        "smooth"
      );
    }, 50);

    setPrompt("");
    setError(null);
    setLoading(true);

    try {
      const conversationId =
        await ensureConversation(
          cleanPrompt
        );

      await saveConversationMessage(
        conversationId,
        "user",
        cleanPrompt,
        "user"
      );

      /*
       * /ask remains the routing endpoint.
       *
       * Reporting:
       *   receives the governed report.
       *
       * Knowledge:
       *   receives the current knowledge-agent
       *   response.
       *
       * General:
       *   switches to /stream so the answer
       *   appears progressively.
       */
      const response =
        await askNIBGPT({
          prompt: cleanPrompt,
          previous_prompt:
            previousUserPrompt,
          context:
            reportingContext,
          requested_limit: 100,
          maximum_entities: 6,
          maximum_path_depth: 4,
          user_role: "analyst",
        });

      if (
          response.route ===
            "reporting" &&
          response.report
        ) {
          await streamReportingExplanation(
            conversationId,
            response.report
          );

          return;
        }

      if (
        response.route ===
          "reporting" &&
        response.context
      ) {
        setReportingContext(
          response.context
        );
      }

      if (
        response.route ===
        "general"
      ) {
        /*
         * Do not add response.answer here,
         * otherwise the general answer appears
         * twice. The streaming endpoint owns
         * the displayed general-AI response.
         */
        await streamGeneralResponse(
          cleanPrompt,
          conversationId
        );

        return;
      }

      const assistantContent =
        response.answer ||
        (
          response.route ===
          "reporting"
            ? "NIBGPT completed your report."
            : "NIBGPT completed your request."
        );

      addAssistantMessage({
        id: createMessageId(
          "assistant"
        ),
        role: "assistant",
        content:
          assistantContent,
        route:
          response.route,
        report:
          response.report ||
          undefined,
        createdAt:
          new Date().toISOString(),
      });

      await saveConversationMessage(
        conversationId,
        "assistant",
        assistantContent,
        response.route,
        response.report ?? null
      );

      await refreshConversations();
    } catch (requestError) {
      const maybeAxiosError =
        requestError as {
          response?: {
            data?: {
              detail?: string;
            };
          };
          message?: string;
        };

      const message =
        maybeAxiosError
          ?.response
          ?.data
          ?.detail ||
        maybeAxiosError
          ?.message ||
        (
          "Unable to communicate " +
          "with NIBGPT."
        );

      setError(message);

      addAssistantMessage({
        id: createMessageId(
          "assistant-error"
        ),
        role: "assistant",
        content:
          (
            "I couldn't complete " +
            "that request. Please " +
            "try again."
          ),
        createdAt:
          new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };


  const hasMessages =
    messages.length > 0;


  return (
    <Box
      sx={{
        height:
          "calc(100vh - 110px)",
        minHeight: 650,
        display: "flex",
        overflow: "hidden",
        bgcolor: "#ffffff",
        borderRadius: 3,
        border:
          "1px solid #eadfd6",
      }}
    >
      {/* LEFT CHAT SIDEBAR */}

      <Box
        sx={{
          width: 275,
          minWidth: 275,
          display: {
            xs: "none",
            lg: "flex",
          },
          flexDirection:
            "column",
          bgcolor: "#fbf8f5",
          borderRight:
            "1px solid #eadfd6",
        }}
      >
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            variant="contained"
            startIcon={
              <AutoAwesomeOutlined />
            }
            onClick={
              resetConversation
            }
            disabled={loading}
            sx={{
              py: 1.2,
              borderRadius: 2,
              textTransform:
                "none",
              fontWeight: 800,
              bgcolor: "#5b311b",
              "&:hover": {
                bgcolor:
                  "#472515",
              },
            }}
          >
            New Chat
          </Button>
        </Box>

        <Divider />

        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            p: 1.5,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              display: "block",
              px: 1,
              py: 1,
              fontWeight: 800,
              textTransform:
                "uppercase",
              letterSpacing: 0.6,
              color: "#9a7b67",
            }}
          >
            Recent
          </Typography>

          {conversationsLoading &&
          conversations.length === 0 ? (
            <Typography
              variant="body2"
              sx={{
                px: 1.25,
                py: 1,
                color: "#9a7b67",
                fontSize: "0.78rem",
              }}
            >
              Loading conversations...
            </Typography>
          ) : conversations.length === 0 ? (
            <Typography
              variant="body2"
              sx={{
                px: 1.25,
                py: 1,
                color: "#9a7b67",
                fontSize: "0.78rem",
              }}
            >
              No saved conversations yet.
            </Typography>
          ) : (
            groupedConversations.map(
              (group) => (
                <Box
                  key={group.label}
                  sx={{ mb: 1.25 }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      display: "block",
                      px: 1,
                      pt: 0.8,
                      pb: 0.45,
                      color: "#a18d80",
                      fontSize: "0.68rem",
                      fontWeight: 800,
                    }}
                  >
                    {group.label}
                  </Typography>

                  {group.items.map(
                    (conversation) => (
                      <Box
                        key={conversation.id}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          borderRadius: 2,
                          mb: 0.35,
                          bgcolor:
                            activeConversationId ===
                            conversation.id
                              ? "#efe3d8"
                              : "transparent",
                          "&:hover": {
                            bgcolor: "#f1e8df",
                          },
                          "&:hover .chat-menu-button": {
                            opacity: 1,
                          },
                        }}
                      >
                        <Button
                          fullWidth
                          onClick={() => {
                            void openConversation(
                              conversation.id
                            );
                          }}
                          disabled={loading}
                          sx={{
                            minWidth: 0,
                            flex: 1,
                            justifyContent:
                              "flex-start",
                            textAlign: "left",
                            textTransform: "none",
                            color:
                              activeConversationId ===
                              conversation.id
                                ? "#3c2619"
                                : "#5f493c",
                            borderRadius: 2,
                            px: 1.25,
                            py: 0.9,
                          }}
                        >
                          <Typography
                            variant="body2"
                            noWrap
                            sx={{
                              width: "100%",
                              fontWeight:
                                activeConversationId ===
                                conversation.id
                                  ? 800
                                  : 600,
                              color: "inherit",
                            }}
                          >
                            {conversation.title}
                          </Typography>
                        </Button>

                        <IconButton
                          className="chat-menu-button"
                          size="small"
                          disabled={loading}
                          onClick={(event) =>
                            openConversationMenu(
                              event,
                              conversation
                            )
                          }
                          sx={{
                            mr: 0.5,
                            opacity: {
                              xs: 1,
                              lg: 0,
                            },
                            color: "#7f6859",
                            transition:
                              "opacity 0.15s ease",
                          }}
                        >
                          <MoreVert
                            fontSize="small"
                          />
                        </IconButton>
                      </Box>
                    )
                  )}
                </Box>
              )
            )
          )}
        </Box>

        <Divider />

        <Box sx={{ p: 2 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.3,
            }}
          >
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                display: "grid",
                placeItems: "center",
                bgcolor: "#5b311b",
                color: "#fff",
                fontWeight: 900,
              }}
            >
              N
            </Box>

            <Box>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: 800,
                  color: "#4b3021",
                }}
              >
                NIBGPT
              </Typography>

              <Typography
                variant="caption"
                sx={{
                  color: "#9a7b67",
                }}
              >
                Enterprise AI
              </Typography>
            </Box>
          </Box>
        </Box>
      </Box>

      <Menu
        anchorEl={conversationMenuAnchor}
        open={Boolean(conversationMenuAnchor)}
        onClose={closeConversationMenu}
        onClick={(event) =>
          event.stopPropagation()
        }
      >
        <MenuItem
          onClick={beginRenameConversation}
        >
          <EditOutlined
            fontSize="small"
            sx={{ mr: 1 }}
          />
          Rename
        </MenuItem>

        <MenuItem
          onClick={beginDeleteConversation}
          sx={{ color: "#b91c1c" }}
        >
          <DeleteOutlined
            fontSize="small"
            sx={{ mr: 1 }}
          />
          Delete
        </MenuItem>
      </Menu>

      <Dialog
        open={renameDialogOpen}
        onClose={() =>
          setRenameDialogOpen(false)
        }
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>
          Rename conversation
        </DialogTitle>

        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            value={renameTitle}
            onChange={(event) =>
              setRenameTitle(
                event.target.value
              )
            }
            onKeyDown={(event) => {
              if (
                event.key === "Enter" &&
                renameTitle.trim()
              ) {
                event.preventDefault();
                void handleRenameConversation();
              }
            }}
            label="Conversation title"
            sx={{ mt: 1 }}
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() =>
              setRenameDialogOpen(false)
            }
            sx={{
              textTransform: "none",
              color: "#6f5b4e",
            }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={!renameTitle.trim()}
            onClick={() => {
              void handleRenameConversation();
            }}
            sx={{
              textTransform: "none",
              bgcolor: "#5b311b",
              "&:hover": {
                bgcolor: "#472515",
              },
            }}
          >
            Rename
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={() =>
          setDeleteDialogOpen(false)
        }
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>
          Delete conversation?
        </DialogTitle>

        <DialogContent>
          <Typography
            variant="body2"
            sx={{ color: "#6f5b4e" }}
          >
            This will permanently delete
            "{menuConversation?.title}" and
            all of its saved messages.
          </Typography>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() =>
              setDeleteDialogOpen(false)
            }
            sx={{
              textTransform: "none",
              color: "#6f5b4e",
            }}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            onClick={() => {
              void handleDeleteConversation();
            }}
            sx={{
              textTransform: "none",
              bgcolor: "#b91c1c",
              "&:hover": {
                bgcolor: "#991b1b",
              },
            }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* MAIN CHAT AREA */}

      <Box
        sx={{
          flexGrow: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* HEADER */}

        <Box
          sx={{
            height: 64,
            px: {
              xs: 2,
              md: 3,
            },
            display: "flex",
            alignItems: "center",
            justifyContent:
              "space-between",
            borderBottom:
              "1px solid #eadfd6",
            flexShrink: 0,
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.2,
            }}
          >
            <Box
              sx={{
                width: 38,
                height: 38,
                borderRadius: 2,
                display: "grid",
                placeItems: "center",
                background:
                  (
                    "linear-gradient(" +
                    "135deg, #5b311b, " +
                    "#d4a441)"
                  ),
                color: "#fff",
              }}
            >
              <SmartToyOutlined />
            </Box>

            <Box>
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 900,
                  color: "#3c2619",
                }}
              >
                NIBGPT
              </Typography>

              <Typography
                variant="caption"
                noWrap
                sx={{
                  display: "block",
                  maxWidth: {
                    xs: 180,
                    md: 420,
                  },
                  color: "#8c6d5a",
                }}
              >
                {activeConversationId
                  ? (
                      conversations.find(
                        (item) =>
                          item.id ===
                          activeConversationId
                      )?.title ||
                      "Enterprise AI Assistant"
                    )
                  : "Enterprise AI Assistant"}
              </Typography>
            </Box>
          </Box>

          <Chip
            size="small"
            label={
              loading
                ? "Working"
                : "AI Ready"
            }
            sx={{
              bgcolor:
                loading
                  ? "#fff7ed"
                  : "#ecfdf5",
              color:
                loading
                  ? "#c2410c"
                  : "#047857",
              fontWeight: 700,
            }}
          />
        </Box>

        {/* CONVERSATION */}

        <Box
          ref={conversationScrollRef}
          onScroll={
            handleConversationScroll
          }
          sx={{
            flexGrow: 1,
            minHeight: 0,
            overflowY: "auto",
            px: {
              xs: 2,
              md: 4,
            },
          }}
        >
          {!hasMessages ? (
            <Box
              sx={{
                maxWidth: 900,
                minHeight: "100%",
                mx: "auto",
                display: "flex",
                flexDirection:
                  "column",
                alignItems: "center",
                justifyContent:
                  "center",
                py: 5,
              }}
            >
              <Box
                sx={{
                  width: 72,
                  height: 72,
                  mb: 2.5,
                  borderRadius: 3,
                  display: "grid",
                  placeItems: "center",
                  background:
                    (
                      "linear-gradient(" +
                      "135deg, #5b311b, " +
                      "#d4a441)"
                    ),
                  color: "#fff",
                  boxShadow:
                    (
                      "0 14px 35px " +
                      "rgba(91,49,27,0.22)"
                    ),
                }}
              >
                <SmartToyOutlined
                  sx={{
                    fontSize: 34,
                  }}
                />
              </Box>

              <Typography
                variant="h4"
                sx={{
                  fontWeight: 900,
                  color: "#342116",
                  textAlign: "center",
                  letterSpacing:
                    "-0.5px",
                }}
              >
                How can NIBGPT help
                you today?
              </Typography>

              <Typography
                variant="body2"
                sx={{
                  mt: 1.3,
                  color: "#7f6859",
                  maxWidth: 620,
                  mx: "auto",
                  textAlign: "center",
                  lineHeight: 1.7,
                }}
              >
                Ask questions about
                bank data, reports,
                policies, procedures
                and enterprise
                knowledge using natural
                language.
              </Typography>
            </Box>
          ) : (
            <Box
              sx={{
                maxWidth: 900,
                width: "100%",
                mx: "auto",
                py: 4,
              }}
            >
              {messages.map(
                (message) => (
                  <Box
                    key={message.id}
                    sx={{
                      display: "flex",
                      justifyContent:
                        message.role ===
                        "user"
                          ? "flex-end"
                          : "flex-start",
                      mb: 3,
                    }}
                  >
                    <Box
                      sx={{
                        maxWidth:
                          message.role ===
                          "user"
                            ? "75%"
                            : "100%",
                        width:
                          message.role ===
                          "assistant"
                            ? "100%"
                            : "auto",
                      }}
                    >
                      {message.role ===
                        "assistant" && (
                        <Box
                          sx={{
                            display:
                              "flex",
                            alignItems:
                              "center",
                            gap: 1,
                            mb: 1,
                          }}
                        >
                          <Box
                            sx={{
                              width: 30,
                              height: 30,
                              borderRadius:
                                1.5,
                              display:
                                "grid",
                              placeItems:
                                "center",
                              background:
                                (
                                  "linear-gradient(" +
                                  "135deg, " +
                                  "#5b311b, " +
                                  "#d4a441)"
                                ),
                              color:
                                "#fff",
                            }}
                          >
                            <SmartToyOutlined
                              sx={{
                                fontSize:
                                  18,
                              }}
                            />
                          </Box>

                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight:
                                800,
                              color:
                                "#4b3021",
                            }}
                          >
                            NIBGPT
                          </Typography>

                          {message.route && (
                            <Chip
                              size="small"
                              label={
                                message.route
                              }
                              sx={{
                                height: 22,
                                fontSize:
                                  "0.65rem",
                                textTransform:
                                  "capitalize",
                              }}
                            />
                          )}
                        </Box>
                      )}

                      <Box
                        sx={{
                          px:
                            message.role ===
                            "user"
                              ? 2
                              : 0,
                          py:
                            message.role ===
                            "user"
                              ? 1.4
                              : 0,
                          borderRadius:
                            message.role ===
                            "user"
                              ? 3
                              : 0,
                          bgcolor:
                            message.role ===
                            "user"
                              ? "#f1e8df"
                              : "transparent",
                          color:
                            "#3f3027",
                          whiteSpace:
                            message.role ===
                            "user"
                              ? "pre-wrap"
                              : "normal",
                          lineHeight: 1.55,
                          overflowWrap:
                            "anywhere",
                        }}
                      >
                        {message.role === "assistant" &&
!message.content &&
message.isStreaming ? (
  <Typography
    component="span"
    variant="body2"
    sx={{
      color: "#8b7669",
      fontStyle: "italic",
    }}
  >
    NIBGPT is thinking...
  </Typography>
) : message.role === "assistant" ? (
  <Box
    sx={{
      fontSize: "0.95rem",
      lineHeight: 1.55,

      "& p": {
        mt: 0,
        mb: 0.5,
        lineHeight: 1.55,
      },

      "& p:last-child": {
        mb: 0,
      },

      "& h1, & h2, & h3": {
        color: "#3f3027",
        fontWeight: 800,
        mt: 1.25,
        mb: 0.5,
        lineHeight: 1.35,
      },

      "& h1:first-of-type, & h2:first-of-type, & h3:first-of-type":
        {
          mt: 0,
        },

      "& h1": {
        fontSize: "1.35rem",
      },

      "& h2": {
        fontSize: "1.15rem",
      },

      "& h3": {
        fontSize: "1.05rem",
      },

      "& ol, & ul": {
        mt: 0.35,
        mb: 0.5,
        pl: 3,
      },

      "& li": {
        mb: 0.3,
        pl: 0.25,
        lineHeight: 1.55,
      },

      "& li > p": {
        display: "inline",
        margin: 0,
      },

      "& li > p + p": {
        display: "block",
        mt: 0.3,
      },

      "& li > ul, & li > ol": {
        mt: 0.3,
        mb: 0.3,
        pl: 3,
      },

      "& li > ul > li, & li > ol > li": {
        mt: 0.15,
        mb: 0.2,
      },

      "& ol > li": {
        mt: 0,
        mb: 0.6,
      },

      "& ol > li + li": {
        mt: 0.6,
      },

      "& li > br": {
        display: "none",
      },

      "& strong": {
        fontWeight: 800,
        color: "#342116",
      },

      "& code": {
        bgcolor: "#f4eee9",
        borderRadius: 1,
        px: 0.6,
        py: 0.2,
        fontFamily: "monospace",
        fontSize: "0.88em",
      },

      "& pre": {
        bgcolor: "#211a16",
        color: "#f8f5f2",
        p: 2,
        borderRadius: 2,
        overflowX: "auto",
      },

      "& pre code": {
        bgcolor: "transparent",
        color: "inherit",
        p: 0,
      },

      "& table": {
        width: "100%",
        borderCollapse: "collapse",
        my: 1.25,
      },

      "& th, & td": {
        border: "1px solid #e2d8d0",
        px: 1.5,
        py: 1,
        textAlign: "left",
      },

      "& th": {
        bgcolor: "#f8f3ef",
        fontWeight: 800,
      },

      "& blockquote": {
        borderLeft: "4px solid #d4a441",
        ml: 0,
        pl: 2,
        color: "#6f5b4e",
      },
    }}
  >
    <ReactMarkdown
      remarkPlugins={[
        remarkGfm,
      ]}
    >
      {message.content}
    </ReactMarkdown>
  </Box>
) : (
  message.content
)}

                        {message.isStreaming &&
                          message.content && (
                          <Box
                            component="span"
                            sx={{
                              display:
                                "inline-block",
                              width: 7,
                              height: 16,
                              ml: 0.5,
                              verticalAlign:
                                "text-bottom",
                              bgcolor:
                                "#7a4828",
                              animation:
                                (
                                  "nibgptBlink " +
                                  "1s step-end " +
                                  "infinite"
                                ),
                              "@keyframes nibgptBlink":
                                {
                                  "0%, 50%": {
                                    opacity:
                                      1,
                                  },
                                  "51%, 100%":
                                    {
                                      opacity:
                                        0,
                                    },
                                },
                            }}
                          />
                        )}
                      </Box>

                      {/* REPORT */}

                      {message.report &&
                      message.report.success &&
                      message.report.rows?.length >
                        0 && (
                        <ReportTable
                          report={
                            message.report
                          }
                        />
                    )}
                    </Box>
                  </Box>
                )
              )}

              {loading &&
                !messages.some(
                  (message) =>
                    message.isStreaming
                ) && (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.5,
                    mb: 3,
                  }}
                >
                  <Box
                    sx={{
                      width: 30,
                      height: 30,
                      borderRadius: 1.5,
                      display: "grid",
                      placeItems: "center",
                      bgcolor: "#5b311b",
                      color: "#fff",
                    }}
                  >
                    <SmartToyOutlined
                      sx={{
                        fontSize: 18,
                      }}
                    />
                  </Box>

                  <Typography
                    variant="body2"
                    sx={{
                      color: "#8b7669",
                    }}
                  >
                    NIBGPT is thinking...
                  </Typography>
                </Box>
              )}

              {error && (
                <Typography
                  variant="body2"
                  sx={{
                    color: "#b91c1c",
                    mt: 1,
                  }}
                >
                  {error}
                </Typography>
              )}

              <div
                ref={
                  conversationEndRef
                }
              />
            </Box>
          )}
        </Box>

        {/* BOTTOM COMPOSER */}

        <Box
          sx={{
            px: {
              xs: 2,
              md: 4,
            },
            pb: 2,
            pt: 1,
            bgcolor: "#fff",
            flexShrink: 0,
          }}
        >
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{
              maxWidth: 900,
              mx: "auto",
            }}
          >
            <Paper
              elevation={0}
              sx={{
                display: "flex",
                alignItems:
                  "flex-end",
                gap: 1,
                p: 1,
                borderRadius: 3,
                border:
                  "1px solid #d8c9be",
                boxShadow:
                  (
                    "0 6px 20px " +
                    "rgba(45,24,12,0.07)"
                  ),
              }}
            >
              <TextField
                multiline
                maxRows={5}
                fullWidth
                value={prompt}
                disabled={loading}
                onChange={(event) =>
                  setPrompt(
                    event.target.value
                  )
                }
                onKeyDown={(event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey
  ) {
    event.preventDefault();

    if (
      !prompt.trim() ||
      loading
    ) {
      return;
    }

    const form =
      event.currentTarget.closest(
        "form"
      );

    if (form) {
      form.requestSubmit();
    }
  }
}}
                placeholder=
                  "Ask NibGPT..."
                variant="standard"
                slotProps={{
                  input: {
                    disableUnderline:
                      true,
                  },
                }}
                sx={{
                  px: 1.5,
                  py: 0.6,
                  "& textarea": {
                    fontSize:
                      "0.95rem",
                    lineHeight: 1.6,
                  },
                }}
              />

              <IconButton
                type="submit"
                disabled={
                  !prompt.trim() ||
                  loading
                }
                sx={{
                  width: 42,
                  height: 42,
                  bgcolor:
                    prompt.trim() &&
                    !loading
                      ? "#5b311b"
                      : "#ddd2ca",
                  color: "#fff",
                  "&:hover": {
                    bgcolor:
                      "#472515",
                  },
                  "&.Mui-disabled":
                    {
                      color:
                        "#ffffff",
                    },
                }}
              >
                {loading
                  ? (
                    <Typography
                      component="span"
                      sx={{
                        fontSize:
                          "0.8rem",
                        color: "#fff",
                      }}
                    >
                      •••
                    </Typography>
                  )
                  : (
                    <SendOutlined />
                  )}
              </IconButton>
            </Paper>

            <Typography
              variant="caption"
              sx={{
                display: "block",
                mt: 1,
                textAlign: "center",
                color: "#a18d80",
              }}
            >
              Enter to send ·
              Shift + Enter for a new
              line · NIBGPT uses
              governed data and
              approved enterprise
              knowledge.
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}