import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  FormControl,
  InputLabel,
  LinearProgress,
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
import { analyzePromptPipeline } from "../../services/promptPipeline";

import type {
  DataSource,
} from "../../types/dataSource";

import type {
  PromptPipelineResponse,
  ResolvedColumn,
  ResolvedTable,
} from "../../types/promptPipeline";


function AiPlaygroundPage() {
  const [dataSources, setDataSources] =
    useState<DataSource[]>([]);

  const [selectedSourceId, setSelectedSourceId] =
    useState<number | "">("");

  const [prompt, setPrompt] = useState(
    "Show active records created this month"
  );

  const [result, setResult] =
    useState<PromptPipelineResponse | null>(
      null
    );

  const [loadingSources, setLoadingSources] =
    useState(true);

  const [analyzing, setAnalyzing] =
    useState(false);

  const [errorMessage, setErrorMessage] =
    useState("");

  useEffect(() => {
    const loadSources = async () => {
      try {
        const sources = await getDataSources();

        setDataSources(
          sources.filter(
            (source) =>
              source.is_active &&
              source.status === "connected"
          )
        );
      } catch {
        setErrorMessage(
          "Unable to load connected data sources."
        );
      } finally {
        setLoadingSources(false);
      }
    };

    loadSources();
  }, []);

  const handleAnalyze = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const cleanedPrompt = prompt.trim();

    if (!cleanedPrompt || analyzing) {
      return;
    }

    try {
      setAnalyzing(true);
      setErrorMessage("");
      setResult(null);

      const response =
        await analyzePromptPipeline(
          cleanedPrompt,
          selectedSourceId === ""
            ? null
            : selectedSourceId
        );

      setResult(response);
    } catch (error: any) {
      setErrorMessage(
        error?.response?.data?.detail ??
          "NIBGPT could not analyze the prompt."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const examples = [
    "Show active records created this month",
    "How many approved requests were created today?",
    "Show the total transaction amount by branch",
    "Compare monthly requests by department",
    "Show expired records",
  ];

  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent: "space-between",
          alignItems: {
            xs: "flex-start",
            md: "center",
          },
          flexDirection: {
            xs: "column",
            md: "row",
          },
          gap: 2,
        }}
      >
        <Box>
          <Typography
            variant="h4"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            AI Playground
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Inspect how NIBGPT interprets business
            questions before generating SQL.
          </Typography>
        </Box>

        <Chip
          label="Read-only analysis"
          sx={{
            bgcolor: "#e7f6ed",
            color: "#207744",
            fontWeight: 800,
          }}
        />
      </Box>

      <Paper
        component="form"
        onSubmit={handleAnalyze}
        elevation={0}
        sx={{
          p: 3,
          borderRadius: 3,
          border: "1px solid #e9e2da",
          background:
            "linear-gradient(145deg, #ffffff, #fcfaf7)",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "280px minmax(0, 1fr)",
            },
            gap: 2,
          }}
        >
          <FormControl
            fullWidth
            disabled={loadingSources}
          >
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
                Search all connected sources
              </MenuItem>

              {dataSources.map((source) => (
                <MenuItem
                  key={source.id}
                  value={source.id}
                >
                  {source.name} ·{" "}
                  {source.database_type.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            multiline
            minRows={3}
            maxRows={7}
            label="Ask a business question"
            value={prompt}
            disabled={analyzing}
            onChange={(event) =>
              setPrompt(event.target.value)
            }
            placeholder="Example: Show approved requests created this month"
          />
        </Box>

        <Box
          sx={{
            mt: 2,
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
          }}
        >
          {examples.map((example) => (
            <Chip
              key={example}
              label={example}
              onClick={() =>
                setPrompt(example)
              }
              sx={{
                cursor: "pointer",
                bgcolor: "#fff3dc",
                color: "#765019",
                "&:hover": {
                  bgcolor: "#f7dfad",
                },
              }}
            />
          ))}
        </Box>

        <Box
          sx={{
            mt: 3,
            display: "flex",
            justifyContent: "flex-end",
          }}
        >
          <Button
            type="submit"
            variant="contained"
            disabled={
              analyzing || !prompt.trim()
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
            {analyzing ? (
              <>
                <CircularProgress
                  size={18}
                  color="inherit"
                  sx={{ mr: 1 }}
                />
                NIBGPT is analyzing...
              </>
            ) : (
              "Analyze with NIBGPT"
            )}
          </Button>
        </Box>
      </Paper>

      {errorMessage && (
        <Alert
          severity="error"
          sx={{ mt: 2 }}
          onClose={() =>
            setErrorMessage("")
          }
        >
          {errorMessage}
        </Alert>
      )}

      {analyzing && (
        <Paper
          elevation={0}
          sx={{
            mt: 3,
            p: 4,
            borderRadius: 3,
            border: "1px solid #e9e2da",
            textAlign: "center",
          }}
        >
          <Box
            sx={{
              width: 72,
              height: 72,
              mx: "auto",
              mb: 2,
              borderRadius: 4,
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

          <Typography
            variant="h6"
            sx={{
              color: "#4f2c1a",
              fontWeight: 800,
            }}
          >
            Understanding your question
          </Typography>

          <Typography
            sx={{
              mt: 1,
              color: "#777777",
            }}
          >
            Detecting intent, extracting business
            terms and ranking approved metadata.
          </Typography>

          <LinearProgress
            sx={{
              mt: 3,
              maxWidth: 480,
              mx: "auto",
              height: 8,
              borderRadius: 5,
            }}
          />
        </Paper>
      )}

      {result && (
        <AnalysisResult result={result} />
      )}
    </Box>
  );
}


function AnalysisResult({
  result,
}: {
  result: PromptPipelineResponse;
}) {
  return (
    <Box sx={{ mt: 3 }}>
      {!result.is_safe && (
        <Alert
          severity="error"
          sx={{ mb: 2.5 }}
        >
          <Typography
            sx={{ fontWeight: 800 }}
          >
            Request blocked
          </Typography>

          {result.blocked_reason}
        </Alert>
      )}

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
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            xl: "repeat(4, 1fr)",
          },
          gap: 2,
        }}
      >
        <MetricCard
          label="Intent"
          value={result.intent.replaceAll(
            "_",
            " "
          )}
          confidence={
            result.intent_confidence
          }
        />

        <MetricCard
          label="Metadata Match"
          value={
            result.matched_tables.length
              ? `${
                  result.matched_tables.length
                } table${
                  result.matched_tables.length === 1
                    ? ""
                    : "s"
                }`
              : "No match"
          }
          confidence={
            result.metadata_confidence
          }
        />

        <MetricCard
          label="Overall Confidence"
          value={`${result.overall_confidence}%`}
          confidence={
            result.overall_confidence
          }
        />

        <MetricCard
          label="Safety"
          value={
            result.is_safe
              ? "Read only"
              : "Blocked"
          }
          confidence={
            result.is_safe ? 100 : 0
          }
        />
      </Box>

      <Box
        sx={{
          mt: 2.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "0.85fr 1.65fr",
          },
          gap: 2.5,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          <Typography
            variant="h6"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Prompt Understanding
          </Typography>

          <InfoSection
            title="Extracted entities"
          >
            <ChipGroup
              values={result.entities.map(
                (entity) =>
                  `${entity.value} · ${entity.entity_type}`
              )}
              emptyText="No entities detected"
            />
          </InfoSection>

          <InfoSection title="Keywords">
            <ChipGroup
              values={result.keywords}
              emptyText="No keywords detected"
            />
          </InfoSection>

          <InfoSection
            title="Time expressions"
          >
            <ChipGroup
              values={
                result.time_expressions
              }
              emptyText="No time filter detected"
            />
          </InfoSection>

          <InfoSection
            title="Status terms"
          >
            <ChipGroup
              values={result.status_terms}
              emptyText="No status filter detected"
            />
          </InfoSection>

          <InfoSection
            title="How NIBGPT interpreted it"
          >
            {result.explanation.length ? (
              result.explanation.map(
                (item) => (
                  <Box
                    key={item}
                    sx={{
                      display: "flex",
                      gap: 1,
                      mb: 1.1,
                      color: "#555555",
                    }}
                  >
                    <Box
                      component="span"
                      sx={{
                        color: "#2e8b57",
                        fontWeight: 900,
                      }}
                    >
                      ✓
                    </Box>

                    <Typography variant="body2">
                      {item}
                    </Typography>
                  </Box>
                )
              )
            ) : (
              <Typography
                variant="body2"
                sx={{ color: "#888888" }}
              >
                No explanation is available.
              </Typography>
            )}
          </InfoSection>
        </Paper>

        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: 3,
            border: "1px solid #e9e2da",
          }}
        >
          <Typography
            variant="h6"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
              mb: 2,
            }}
          >
            Ranked Metadata Matches
          </Typography>

          {result.matched_tables.length === 0 ? (
            <Box
              sx={{
                minHeight: 300,
                display: "grid",
                placeItems: "center",
                textAlign: "center",
              }}
            >
              <Box>
                <Typography
                  variant="h6"
                  sx={{
                    color: "#4f2c1a",
                    fontWeight: 800,
                  }}
                >
                  No matching metadata
                </Typography>

                <Typography
                  sx={{
                    mt: 1,
                    color: "#777777",
                  }}
                >
                  Add or approve Business Dictionary
                  definitions and synonyms for this
                  dataset.
                </Typography>
              </Box>
            </Box>
          ) : (
            <Box
              sx={{
                display: "grid",
                gap: 2,
              }}
            >
              {result.matched_tables.map(
                (table, index) => (
                  <TableMatchCard
                    key={table.id}
                    table={table}
                    position={index + 1}
                  />
                )
              )}
            </Box>
          )}
        </Paper>
      </Box>
    </Box>
  );
}


interface MetricCardProps {
  label: string;
  value: string;
  confidence: number;
}

function MetricCard({
  label,
  value,
  confidence,
}: MetricCardProps) {
  const tone =
    confidence >= 85
      ? "#2e8b57"
      : confidence >= 65
        ? "#b17a1e"
        : "#b3261e";

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
        variant="h5"
        sx={{
          mt: 0.8,
          color: "#4f2c1a",
          fontWeight: 900,
          textTransform: "capitalize",
        }}
      >
        {value}
      </Typography>

      <LinearProgress
        variant="determinate"
        value={Math.max(
          0,
          Math.min(confidence, 100)
        )}
        sx={{
          mt: 1.8,
          height: 7,
          borderRadius: 5,
          "& .MuiLinearProgress-bar": {
            bgcolor: tone,
          },
        }}
      />

      <Typography
        variant="caption"
        sx={{
          display: "block",
          mt: 0.6,
          color: tone,
          fontWeight: 800,
        }}
      >
        {confidence}% confidence
      </Typography>
    </Paper>
  );
}


function TableMatchCard({
  table,
  position,
}: {
  table: ResolvedTable;
  position: number;
}) {
  const [expanded, setExpanded] =
    useState(position === 1);

  return (
    <Paper
      elevation={0}
      sx={{
        overflow: "hidden",
        borderRadius: 3,
        border:
          position === 1
            ? "1px solid #cf9b39"
            : "1px solid #e9e2da",
      }}
    >
      <Box
        sx={{
          p: 2.5,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 2,
          bgcolor:
            position === 1
              ? "#fff8e9"
              : "#faf8f5",
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 1,
            }}
          >
            <Chip
              label={`#${position}`}
              size="small"
              sx={{
                bgcolor:
                  position === 1
                    ? "#d19a2b"
                    : "#eeeeee",
                color:
                  position === 1
                    ? "#ffffff"
                    : "#555555",
                fontWeight: 900,
              }}
            />

            <Typography
              variant="h6"
              sx={{
                color: "#4f2c1a",
                fontWeight: 900,
              }}
            >
              {table.business_name ||
                table.table_name}
            </Typography>

            <Chip
              label={`${table.confidence}%`}
              size="small"
              sx={{
                bgcolor:
                  table.confidence >= 85
                    ? "#e7f6ed"
                    : "#fff3dc",
                color:
                  table.confidence >= 85
                    ? "#207744"
                    : "#8b5d12",
                fontWeight: 800,
              }}
            />
          </Box>

          <Typography
            variant="body2"
            sx={{
              mt: 0.6,
              color: "#888888",
            }}
          >
            {table.schema_name
              ? `${table.schema_name}.${table.table_name}`
              : table.table_name}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              mt: 1,
              color: "#666666",
              lineHeight: 1.7,
            }}
          >
            {table.description ||
              "No approved business description is available."}
          </Typography>
        </Box>

        <Button
          size="small"
          variant="outlined"
          onClick={() =>
            setExpanded((current) => !current)
          }
          sx={{
            flexShrink: 0,
            textTransform: "none",
            color: "#6b3b21",
            borderColor: "#9f795d",
          }}
        >
          {expanded
            ? "Hide details"
            : "Why this match?"}
        </Button>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ p: 2.5 }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(2, 1fr)",
              },
              gap: 2,
            }}
          >
            <InfoCard
              title="Governance"
              values={[
                `Classification: ${table.classification}`,
                `Definition: ${table.definition_status}`,
                `AI access: ${
                  table.ai_access_allowed
                    ? "Allowed"
                    : "Blocked"
                }`,
                `Department: ${
                  table.department ||
                  "Not assigned"
                }`,
                `Owner: ${
                  table.data_owner ||
                  "Not assigned"
                }`,
              ]}
            />

            <InfoCard
              title="Matching reasons"
              values={
                table.reasons.length
                  ? table.reasons
                  : [
                      "No detailed reasons were returned.",
                    ]
              }
            />
          </Box>

          <Typography
            sx={{
              mt: 2.5,
              mb: 1.5,
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            Relevant Columns
          </Typography>

          {table.columns.length === 0 ? (
            <Alert severity="info">
              The table matched, but no individual
              column received a strong match.
            </Alert>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "repeat(2, 1fr)",
                },
                gap: 1.5,
              }}
            >
              {table.columns.map(
                (column) => (
                  <ColumnMatchCard
                    key={column.id}
                    column={column}
                  />
                )
              )}
            </Box>
          )}
        </Box>
      </Collapse>
    </Paper>
  );
}


function ColumnMatchCard({
  column,
}: {
  column: ResolvedColumn;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2.5,
        bgcolor: "#faf8f5",
        border: "1px solid #ece5dd",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 800,
            }}
          >
            {column.business_name ||
              column.column_name}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: "#888888",
            }}
          >
            {column.column_name} ·{" "}
            {column.data_type}
          </Typography>
        </Box>

        <Chip
          label={`${column.confidence}%`}
          size="small"
          sx={{
            fontWeight: 800,
          }}
        />
      </Box>

      {column.description && (
        <Typography
          variant="body2"
          sx={{
            mt: 1,
            color: "#666666",
          }}
        >
          {column.description}
        </Typography>
      )}

      <Box
        sx={{
          mt: 1.3,
          display: "flex",
          flexWrap: "wrap",
          gap: 0.7,
        }}
      >
        {column.is_sensitive && (
          <Chip
            label="Sensitive"
            size="small"
            sx={{
              bgcolor: "#fdecec",
              color: "#b3261e",
            }}
          />
        )}

        <Chip
          label={column.classification}
          size="small"
          sx={{
            textTransform: "capitalize",
          }}
        />
      </Box>
    </Paper>
  );
}


function InfoSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Box sx={{ mt: 2.5 }}>
      <Typography
        variant="body2"
        sx={{
          mb: 1,
          color: "#4f2c1a",
          fontWeight: 800,
        }}
      >
        {title}
      </Typography>

      {children}
    </Box>
  );
}


function ChipGroup({
  values,
  emptyText,
}: {
  values: string[];
  emptyText: string;
}) {
  if (!values.length) {
    return (
      <Typography
        variant="body2"
        sx={{ color: "#888888" }}
      >
        {emptyText}
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: 0.8,
      }}
    >
      {values.map((value) => (
        <Chip
          key={value}
          label={value}
          size="small"
          sx={{
            bgcolor: "#fff3dc",
            color: "#775019",
          }}
        />
      ))}
    </Box>
  );
}


function InfoCard({
  title,
  values,
}: {
  title: string;
  values: string[];
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2.5,
        bgcolor: "#faf8f5",
        border: "1px solid #ece5dd",
      }}
    >
      <Typography
        sx={{
          mb: 1.2,
          color: "#4f2c1a",
          fontWeight: 800,
        }}
      >
        {title}
      </Typography>

      {values.map((value) => (
        <Box
          key={value}
          sx={{
            display: "flex",
            gap: 1,
            mb: 0.8,
          }}
        >
          <Box
            component="span"
            sx={{
              color: "#2e8b57",
              fontWeight: 900,
            }}
          >
            ✓
          </Box>

          <Typography
            variant="body2"
            sx={{ color: "#555555" }}
          >
            {value}
          </Typography>
        </Box>
      ))}
    </Paper>
  );
}

export default AiPlaygroundPage;
