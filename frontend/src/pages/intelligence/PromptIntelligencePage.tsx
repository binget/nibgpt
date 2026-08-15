import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import { getDataSources } from "../../services/dataSources";
import { analyzePrompt } from "../../services/intelligence";

import type {
  DataSource,
} from "../../types/dataSource";
import type {
  IntelligenceTableMatch,
  PromptAnalysisResponse,
} from "../../types/intelligence";


function PromptIntelligencePage() {
  const [dataSources, setDataSources] =
    useState<DataSource[]>([]);

  const [selectedSourceId, setSelectedSourceId] =
    useState<number | "">("");

  const [prompt, setPrompt] = useState(
    "Show available vehicles and their assignment status"
  );

  const [result, setResult] =
    useState<PromptAnalysisResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] =
    useState("");

  useEffect(() => {
    getDataSources()
      .then((sources) => {
        setDataSources(
          sources.filter(
            (source) =>
              source.is_active &&
              source.status === "connected"
          )
        );
      })
      .catch(() => {
        setErrorMessage(
          "Unable to load data sources."
        );
      });
  }, []);

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    if (!prompt.trim()) {
      return;
    }

    try {
      setLoading(true);
      setErrorMessage("");

      const response = await analyzePrompt(
        prompt.trim(),
        selectedSourceId === ""
          ? null
          : selectedSourceId
      );

      setResult(response);
    } catch (error: any) {
      setErrorMessage(
        error?.response?.data?.detail ??
          "Unable to analyze the prompt."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography
        variant="h4"
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        Prompt Intelligence
      </Typography>

      <Typography
        sx={{
          mt: 0.7,
          mb: 3,
          color: "#777777",
        }}
      >
        Test how NIBGPT understands business questions
        before generating or executing SQL.
      </Typography>

      <Paper
        component="form"
        onSubmit={handleSubmit}
        elevation={0}
        sx={{
          p: 3,
          borderRadius: 3,
          border: "1px solid #e9e2da",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "260px minmax(0, 1fr)",
            },
            gap: 2,
          }}
        >
          <FormControl fullWidth>
            <InputLabel>
              Data source
            </InputLabel>

            <Select
              label="Data source"
              value={selectedSourceId}
              onChange={(event) =>
                setSelectedSourceId(
                  event.target.value === ""
                    ? ""
                    : Number(
                        event.target.value
                      )
                )
              }
            >
              <MenuItem value="">
                Search all sources
              </MenuItem>

              {dataSources.map((source) => (
                <MenuItem
                  key={source.id}
                  value={source.id}
                >
                  {source.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            multiline
            minRows={3}
            label="Business question"
            value={prompt}
            onChange={(event) =>
              setPrompt(event.target.value)
            }
          />
        </Box>

        <Box
          sx={{
            mt: 2,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Button
            type="submit"
            variant="contained"
            disabled={
              loading || !prompt.trim()
            }
            sx={{
              px: 4,
              py: 1.2,
              borderRadius: 2.5,
              textTransform: "none",
              fontWeight: 800,
              background:
                "linear-gradient(90deg, #61351f, #c78f2b)",
            }}
          >
            {loading ? (
              <>
                <CircularProgress
                  size={18}
                  color="inherit"
                  sx={{ mr: 1 }}
                />
                Analyzing...
              </>
            ) : (
              "Analyze Prompt"
            )}
          </Button>
        </Box>
      </Paper>

      {errorMessage && (
        <Alert
          severity="error"
          sx={{ mt: 2 }}
        >
          {errorMessage}
        </Alert>
      )}

      {result && (
        <Box sx={{ mt: 3 }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(3, 1fr)",
              },
              gap: 2,
              mb: 2.5,
            }}
          >
            <ResultSummary
              label="Intent"
              value={result.intent}
            />

            <ResultSummary
              label="Confidence"
              value={`${result.confidence}%`}
            />

            <ResultSummary
              label="Matches"
              value={String(
                result.result_count
              )}
            />
          </Box>

          {result.warnings.map((warning) => (
            <Alert
              key={warning}
              severity="warning"
              sx={{ mb: 2 }}
            >
              {warning}
            </Alert>
          ))}

          <Box
            sx={{
              display: "grid",
              gap: 2.5,
            }}
          >
            {result.matches.map((match) => (
              <KnowledgeMatchCard
                key={match.id}
                match={match}
                onSuggestion={(question) =>
                  setPrompt(question)
                }
              />
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}


interface ResultSummaryProps {
  label: string;
  value: string;
}

function ResultSummary({
  label,
  value,
}: ResultSummaryProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: "1px solid #e9e2da",
      }}
    >
      <Typography
        variant="body2"
        sx={{
          color: "#888888",
          fontWeight: 700,
        }}
      >
        {label}
      </Typography>

      <Typography
        variant="h4"
        sx={{
          mt: 0.7,
          color: "#4f2c1a",
          fontWeight: 900,
          textTransform: "capitalize",
        }}
      >
        {value.replaceAll("_", " ")}
      </Typography>
    </Paper>
  );
}


interface KnowledgeMatchCardProps {
  match: IntelligenceTableMatch;
  onSuggestion: (value: string) => void;
}

function KnowledgeMatchCard({
  match,
  onSuggestion,
}: KnowledgeMatchCardProps) {
  return (
    <Paper
      elevation={0}
      sx={{
        overflow: "hidden",
        borderRadius: 3,
        border: "1px solid #e9e2da",
      }}
    >
      <Box
        sx={{
          p: 3,
          color: "#ffffff",
          background:
            "linear-gradient(135deg, #5b311b, #9b672b)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h5"
              sx={{ fontWeight: 900 }}
            >
              {match.business_name ||
                match.table_name}
            </Typography>

            <Typography
              variant="body2"
              sx={{
                color:
                  "rgba(255,255,255,0.72)",
              }}
            >
              {match.schema_name
                ? `${match.schema_name}.${match.table_name}`
                : match.table_name}
            </Typography>
          </Box>

          <Chip
            label={`${match.confidence}% confidence`}
            sx={{
              bgcolor:
                "rgba(255,255,255,0.16)",
              color: "#ffffff",
              fontWeight: 800,
            }}
          />
        </Box>

        <Typography
          sx={{
            mt: 2,
            color: "rgba(255,255,255,0.82)",
          }}
        >
          {match.description ||
            "No business description is available."}
        </Typography>
      </Box>

      <Box sx={{ p: 3 }}>
        <Typography
          sx={{
            color: "#4f2c1a",
            fontWeight: 800,
          }}
        >
          Why NIBGPT selected this table
        </Typography>

        <Box
          sx={{
            mt: 1,
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          {match.reasons.map((reason) => (
            <Chip
              key={reason}
              label={reason}
              size="small"
            />
          ))}
        </Box>

        <Typography
          sx={{
            mt: 3,
            color: "#4f2c1a",
            fontWeight: 800,
          }}
        >
          Relevant columns
        </Typography>

        <Box
          sx={{
            mt: 1.5,
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(2, 1fr)",
            },
            gap: 1.5,
          }}
        >
          {match.columns.map((column) => (
            <Paper
              key={column.id}
              elevation={0}
              sx={{
                p: 1.7,
                bgcolor: "#faf8f5",
                border:
                  "1px solid #ece5dd",
              }}
            >
              <Typography
                sx={{
                  fontWeight: 800,
                  color: "#4f2c1a",
                }}
              >
                {column.business_name ||
                  column.column_name}
              </Typography>

              <Typography
                variant="caption"
                sx={{ color: "#888888" }}
              >
                {column.column_name} ·{" "}
                {column.data_type}
              </Typography>

              {column.is_sensitive && (
                <Chip
                  label="Sensitive"
                  size="small"
                  sx={{
                    mt: 1,
                    bgcolor: "#fdecec",
                    color: "#b3261e",
                  }}
                />
              )}
            </Paper>
          ))}
        </Box>

        <Typography
          sx={{
            mt: 3,
            color: "#4f2c1a",
            fontWeight: 800,
          }}
        >
          Suggested questions
        </Typography>

        <Box
          sx={{
            mt: 1.5,
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          {match.suggested_questions.map(
            (question) => (
              <Button
                key={question}
                variant="outlined"
                onClick={() =>
                  onSuggestion(question)
                }
                sx={{
                  textTransform: "none",
                  color: "#6b3b21",
                  borderColor: "#b49379",
                }}
              >
                {question}
              </Button>
            )
          )}
        </Box>
      </Box>
    </Paper>
  );
}

export default PromptIntelligencePage;
