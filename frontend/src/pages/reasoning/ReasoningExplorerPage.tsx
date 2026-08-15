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

import {
  getBusinessDomains,
} from "../../services/businessEntities";

import {
  analyzeReasoning,
} from "../../services/reasoning";

import type {
  BusinessDomain,
} from "../../types/businessEntity";

import type {
  ReasoningCapability,
  ReasoningColumn,
  ReasoningEntity,
  ReasoningPath,
  ReasoningPlan,
  ReasoningTable,
} from "../../types/reasoning";


function ReasoningExplorerPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [prompt, setPrompt] = useState(
    "Show vehicles whose insurance expires this month"
  );

  const [maximumEntities, setMaximumEntities] =
    useState(6);

  const [maximumPathDepth, setMaximumPathDepth] =
    useState(4);

  const [result, setResult] =
    useState<ReasoningPlan | null>(null);

  const [loadingDomains, setLoadingDomains] =
    useState(true);

  const [analyzing, setAnalyzing] =
    useState(false);

  const [errorMessage, setErrorMessage] =
    useState("");


  useEffect(() => {
    const loadDomains = async () => {
      try {
        const response =
          await getBusinessDomains();

        setDomains(
          response.filter(
            (domain) => domain.is_active
          )
        );
      } catch (error: any) {
        setErrorMessage(
          error?.response?.data?.detail ??
            "Unable to load business domains."
        );
      } finally {
        setLoadingDomains(false);
      }
    };

    loadDomains();
  }, []);


  const handleAnalyze = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const cleanedPrompt =
      prompt.trim();

    if (!cleanedPrompt || analyzing) {
      return;
    }

    try {
      setAnalyzing(true);
      setErrorMessage("");
      setResult(null);

      const response =
        await analyzeReasoning({
          prompt: cleanedPrompt,
          domain_id:
            selectedDomainId === ""
              ? null
              : selectedDomainId,
          maximum_entities:
            maximumEntities,
          maximum_path_depth:
            maximumPathDepth,
        });

      setResult(response);
    } catch (error: any) {
      setErrorMessage(
        error?.response?.data?.detail ??
          "NIBGPT could not complete the reasoning analysis."
      );
    } finally {
      setAnalyzing(false);
    }
  };


  const examples = [
    "Show vehicles whose insurance expires this month",
    "Show customers with active accounts",
    "Show total foreign currency requests by branch",
    "Show drivers associated with pending trips",
    "Show customers with overdue loans",
  ];


  return (
    <Box>
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent:
            "space-between",
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
            Reasoning Explorer
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Inspect how NIBGPT moves from a business
            question to governed semantic knowledge.
          </Typography>
        </Box>

        <Chip
          label="No SQL execution"
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
              lg: "300px minmax(0, 1fr)",
            },
            gap: 2,
          }}
        >
          <Box
            sx={{
              display: "grid",
              gap: 2,
            }}
          >
            <FormControl
              fullWidth
              disabled={
                loadingDomains ||
                analyzing
              }
            >
              <InputLabel>
                Business domain
              </InputLabel>

              <Select
                label="Business domain"
                value={selectedDomainId}
                onChange={(event) =>
                  setSelectedDomainId(
                    event.target.value === ""
                      ? ""
                      : Number(
                          event.target.value
                        )
                  )
                }
              >
                <MenuItem value="">
                  Let NIBGPT determine the domain
                </MenuItem>

                {domains.map(
                  (domain) => (
                    <MenuItem
                      key={domain.id}
                      value={domain.id}
                    >
                      {domain.name}
                    </MenuItem>
                  )
                )}
              </Select>
            </FormControl>

            <TextField
              label="Maximum entities"
              type="number"
              value={maximumEntities}
              disabled={analyzing}
              onChange={(event) =>
                setMaximumEntities(
                  Math.max(
                    1,
                    Math.min(
                      15,
                      Number(
                        event.target.value
                      )
                    )
                  )
                )
              }
            />

            <TextField
              label="Maximum relationship depth"
              type="number"
              value={maximumPathDepth}
              disabled={analyzing}
              onChange={(event) =>
                setMaximumPathDepth(
                  Math.max(
                    1,
                    Math.min(
                      8,
                      Number(
                        event.target.value
                      )
                    )
                  )
                )
              }
            />
          </Box>

          <TextField
            fullWidth
            multiline
            minRows={7}
            maxRows={12}
            label="Ask a business question"
            value={prompt}
            disabled={analyzing}
            onChange={(event) =>
              setPrompt(
                event.target.value
              )
            }
            placeholder="Example: Show customers with active accounts"
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
            justifyContent:
              "flex-end",
          }}
        >
          <Button
            type="submit"
            variant="contained"
            disabled={
              analyzing ||
              !prompt.trim()
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
                NIBGPT is reasoning...
              </>
            ) : (
              "Analyze Reasoning"
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
        <ReasoningLoading />
      )}

      {result && (
        <ReasoningResult
          result={result}
        />
      )}
    </Box>
  );
}


function ReasoningLoading() {
  return (
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
          width: 84,
          height: 84,
          mx: "auto",
          mb: 2,
          borderRadius: 4,
          display: "grid",
          placeItems: "center",
          color: "#ffffff",
          fontWeight: 900,
          fontSize: "1.1rem",
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
          fontWeight: 900,
        }}
      >
        Building the reasoning plan
      </Typography>

      <Typography
        sx={{
          mt: 1,
          color: "#777777",
        }}
      >
        Resolving the domain, capabilities,
        entities, relationships and physical data.
      </Typography>

      <LinearProgress
        sx={{
          mt: 3,
          mx: "auto",
          maxWidth: 520,
          height: 8,
          borderRadius: 5,
        }}
      />
    </Paper>
  );
}


function ReasoningResult({
  result,
}: {
  result: ReasoningPlan;
}) {
  return (
    <Box sx={{ mt: 3 }}>
      {result.warnings.map(
        (warning) => (
          <Alert
            key={warning}
            severity="warning"
            sx={{ mb: 2 }}
          >
            {warning}
          </Alert>
        )
      )}

      {result.requires_clarification && (
        <Paper
          elevation={0}
          sx={{
            mb: 2.5,
            p: 2.5,
            borderRadius: 3,
            bgcolor: "#fff8e9",
            border:
              "1px solid #edcf92",
          }}
        >
          <Typography
            sx={{
              color: "#7b5114",
              fontWeight: 900,
            }}
          >
            Clarification required
          </Typography>

          {result.clarification_questions.map(
            (question) => (
              <Typography
                key={question}
                variant="body2"
                sx={{
                  mt: 1,
                  color: "#6d562e",
                }}
              >
                • {question}
              </Typography>
            )
          )}
        </Paper>
      )}

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
          value={formatLabel(
            result.intent
          )}
          confidence={
            result.intent_confidence
          }
        />

        <MetricCard
          label="Business Domain"
          value={
            result.selected_domain
              ?.name ?? "Not resolved"
          }
          confidence={
            result.selected_domain
              ?.confidence ?? 0
          }
        />

        <MetricCard
          label="Matched Entities"
          value={String(
            result.matched_entities.length
          )}
          confidence={
            averageConfidence(
              result.matched_entities.map(
                (entity) =>
                  entity.confidence
              )
            )
          }
        />

        <MetricCard
          label="Overall Confidence"
          value={`${result.overall_confidence}%`}
          confidence={
            result.overall_confidence
          }
        />
      </Box>

      <ReasoningFlow
        result={result}
      />

      <Box
        sx={{
          mt: 2.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "0.9fr 1.5fr",
          },
          gap: 2.5,
        }}
      >
        <Box
          sx={{
            display: "grid",
            gap: 2.5,
            alignContent: "start",
          }}
        >
          <ReasoningSection
            title="Selected Domain"
            subtitle="The broad business area identified for the question."
          >
            {result.selected_domain ? (
              <DomainCard
                domain={
                  result.selected_domain
                }
              />
            ) : (
              <EmptyMessage text="No business domain was resolved." />
            )}
          </ReasoningSection>

          <ReasoningSection
            title="Business Capabilities"
            subtitle="The functions or processes related to the question."
          >
            {result.matched_capabilities.length ? (
              <Box
                sx={{
                  display: "grid",
                  gap: 1.3,
                }}
              >
                {result.matched_capabilities.map(
                  (capability) => (
                    <CapabilityCard
                      key={capability.id}
                      capability={
                        capability
                      }
                    />
                  )
                )}
              </Box>
            ) : (
              <EmptyMessage text="No approved capability matched." />
            )}
          </ReasoningSection>

          <ReasoningSection
            title="Reasoning Explanation"
            subtitle="A plain-language explanation of the selected semantic knowledge."
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
                    }}
                  >
                    <Typography
                      component="span"
                      sx={{
                        color: "#28774b",
                        fontWeight: 900,
                      }}
                    >
                      ✓
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        color: "#555555",
                        lineHeight: 1.65,
                      }}
                    >
                      {item}
                    </Typography>
                  </Box>
                )
              )
            ) : (
              <EmptyMessage text="No reasoning explanation is available." />
            )}
          </ReasoningSection>
        </Box>

        <Box
          sx={{
            display: "grid",
            gap: 2.5,
            alignContent: "start",
          }}
        >
          <ReasoningSection
            title="Matched Business Entities"
            subtitle="The business objects required to answer the question."
          >
            {result.matched_entities.length ? (
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
                {result.matched_entities.map(
                  (entity) => (
                    <EntityCard
                      key={entity.id}
                      entity={entity}
                    />
                  )
                )}
              </Box>
            ) : (
              <EmptyMessage text="No approved business entity matched." />
            )}
          </ReasoningSection>

          <ReasoningSection
            title="Relationship Paths"
            subtitle="Approved knowledge-graph paths connecting the matched entities."
          >
            {result.relationship_paths.length ? (
              <Box
                sx={{
                  display: "grid",
                  gap: 1.5,
                }}
              >
                {result.relationship_paths.map(
                  (path, index) => (
                    <RelationshipPathCard
                      key={`${path.start_entity_id}-${path.end_entity_id}-${index}`}
                      path={path}
                      position={
                        index + 1
                      }
                    />
                  )
                )}
              </Box>
            ) : (
              <EmptyMessage text="No approved relationship path was required or found." />
            )}
          </ReasoningSection>

          <ReasoningSection
            title="Resolved Physical Data"
            subtitle="Approved database tables and columns linked to the business entities."
          >
            {result.physical_tables.length ? (
              <Box
                sx={{
                  display: "grid",
                  gap: 1.5,
                }}
              >
                {result.physical_tables.map(
                  (table) => (
                    <PhysicalTableCard
                      key={`${table.entity_id}-${table.id}`}
                      table={table}
                    />
                  )
                )}
              </Box>
            ) : (
              <EmptyMessage text="No usable physical table mappings were resolved." />
            )}
          </ReasoningSection>
        </Box>
      </Box>
    </Box>
  );
}


function ReasoningFlow({
  result,
}: {
  result: ReasoningPlan;
}) {
  const stages = [
    {
      label: "Question",
      value: result.prompt,
      confidence: 100,
    },
    {
      label: "Intent",
      value: formatLabel(
        result.intent
      ),
      confidence:
        result.intent_confidence,
    },
    {
      label: "Domain",
      value:
        result.selected_domain
          ?.name ?? "Not resolved",
      confidence:
        result.selected_domain
          ?.confidence ?? 0,
    },
    {
      label: "Capability",
      value:
        result.matched_capabilities[0]
          ?.name ?? "Not resolved",
      confidence:
        result.matched_capabilities[0]
          ?.confidence ?? 0,
    },
    {
      label: "Entities",
      value:
        result.matched_entities
          .map(
            (entity) =>
              entity.name
          )
          .join(", ") ||
        "Not resolved",
      confidence:
        averageConfidence(
          result.matched_entities.map(
            (entity) =>
              entity.confidence
          )
        ),
    },
    {
      label: "Physical Data",
      value: result.physical_tables.length
        ? `${result.physical_tables.length} table mapping(s)`
        : "Not resolved",
      confidence:
        averageConfidence(
          result.physical_tables.map(
            (table) =>
              table.mapping_confidence
          )
        ),
    },
  ];

  return (
    <Paper
      elevation={0}
      sx={{
        mt: 2.5,
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
        Reasoning Journey
      </Typography>

      <Typography
        variant="body2"
        sx={{
          mt: 0.5,
          mb: 2.5,
          color: "#888888",
        }}
      >
        The semantic stages NIBGPT followed
        before SQL planning.
      </Typography>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md:
              "repeat(6, minmax(0, 1fr))",
          },
          gap: 1.3,
        }}
      >
        {stages.map(
          (stage, index) => (
            <Box
              key={stage.label}
              sx={{
                position: "relative",
              }}
            >
              <Paper
                elevation={0}
                sx={{
                  height: "100%",
                  p: 1.8,
                  borderRadius: 2.5,
                  bgcolor: "#faf8f5",
                  border:
                    "1px solid #ece5dd",
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    color: "#9a672c",
                    fontWeight: 900,
                  }}
                >
                  {index + 1}.{" "}
                  {stage.label}
                </Typography>

                <Typography
                  variant="body2"
                  sx={{
                    mt: 0.8,
                    color: "#4f2c1a",
                    fontWeight: 800,
                    lineHeight: 1.5,
                    wordBreak:
                      "break-word",
                  }}
                >
                  {stage.value}
                </Typography>

                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    mt: 1,
                    color:
                      confidenceTone(
                        stage.confidence
                      ),
                    fontWeight: 800,
                  }}
                >
                  {stage.confidence}%
                </Typography>
              </Paper>
            </Box>
          )
        )}
      </Box>
    </Paper>
  );
}


function MetricCard({
  label,
  value,
  confidence,
}: {
  label: string;
  value: string;
  confidence: number;
}) {
  const tone =
    confidenceTone(confidence);

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
          textTransform:
            label === "Intent"
              ? "capitalize"
              : "none",
        }}
      >
        {value}
      </Typography>

      <LinearProgress
        variant="determinate"
        value={Math.max(
          0,
          Math.min(
            confidence,
            100
          )
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


function ReasoningSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
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
        {title}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          mt: 0.5,
          mb: 2,
          color: "#888888",
        }}
      >
        {subtitle}
      </Typography>

      {children}
    </Paper>
  );
}


function DomainCard({
  domain,
}: {
  domain: NonNullable<
    ReasoningPlan["selected_domain"]
  >;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.2,
        borderRadius: 2.5,
        bgcolor: "#faf8f5",
        border: "1px solid #ece5dd",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: 2,
        }}
      >
        <Typography
          sx={{
            color: "#4f2c1a",
            fontWeight: 900,
          }}
        >
          {domain.name}
        </Typography>

        <ConfidenceChip
          value={domain.confidence}
        />
      </Box>

      {domain.description && (
        <Typography
          variant="body2"
          sx={{
            mt: 1,
            color: "#666666",
            lineHeight: 1.65,
          }}
        >
          {domain.description}
        </Typography>
      )}

      <ReasonList
        reasons={domain.reasons}
      />
    </Paper>
  );
}


function CapabilityCard({
  capability,
}: {
  capability: ReasoningCapability;
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
          justifyContent:
            "space-between",
          gap: 2,
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {capability.name}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: "#888888",
              textTransform:
                "capitalize",
            }}
          >
            {capability.capability_type}
            {" · "}
            {capability.maturity_level}
          </Typography>
        </Box>

        <ConfidenceChip
          value={
            capability.confidence
          }
        />
      </Box>

      {capability.description && (
        <Typography
          variant="body2"
          sx={{
            mt: 1,
            color: "#666666",
          }}
        >
          {capability.description}
        </Typography>
      )}

      <ReasonList
        reasons={
          capability.reasons
        }
      />
    </Paper>
  );
}


function EntityCard({
  entity,
}: {
  entity: ReasoningEntity;
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
          justifyContent:
            "space-between",
          alignItems: "flex-start",
          gap: 1,
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {entity.name}
          </Typography>

          <Typography
            variant="caption"
            sx={{
              color: "#888888",
              textTransform:
                "capitalize",
            }}
          >
            {entity.classification}
          </Typography>
        </Box>

        <ConfidenceChip
          value={
            entity.confidence
          }
        />
      </Box>

      {entity.description && (
        <Typography
          variant="body2"
          sx={{
            mt: 1,
            color: "#666666",
            lineHeight: 1.6,
          }}
        >
          {entity.description}
        </Typography>
      )}

      {entity.matched_terms.length > 0 && (
        <Box
          sx={{
            mt: 1.3,
            display: "flex",
            flexWrap: "wrap",
            gap: 0.7,
          }}
        >
          {entity.matched_terms.map(
            (term) => (
              <Chip
                key={term}
                label={term}
                size="small"
                sx={{
                  bgcolor: "#fff3dc",
                  color: "#765019",
                }}
              />
            )
          )}
        </Box>
      )}

      <ReasonList
        reasons={entity.reasons}
      />
    </Paper>
  );
}


function RelationshipPathCard({
  path,
  position,
}: {
  path: ReasoningPath;
  position: number;
}) {
  const [expanded, setExpanded] =
    useState(position === 1);

  return (
    <Paper
      elevation={0}
      sx={{
        overflow: "hidden",
        borderRadius: 2.5,
        border:
          position === 1
            ? "1px solid #d2a244"
            : "1px solid #ece5dd",
      }}
    >
      <Box
        sx={{
          p: 2,
          bgcolor:
            position === 1
              ? "#fff8e9"
              : "#faf8f5",
          display: "flex",
          justifyContent:
            "space-between",
          alignItems: "flex-start",
          gap: 2,
        }}
      >
        <Box>
          <Typography
            variant="caption"
            sx={{
              color: "#9a672c",
              fontWeight: 900,
            }}
          >
            PATH #{position}
          </Typography>

          <Typography
            sx={{
              mt: 0.4,
              color: "#4f2c1a",
              fontWeight: 900,
              lineHeight: 1.6,
            }}
          >
            {path.explanation}
          </Typography>
        </Box>

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 1,
          }}
        >
          <ConfidenceChip
            value={path.confidence}
          />

          <Button
            size="small"
            onClick={() =>
              setExpanded(
                (current) =>
                  !current
              )
            }
            sx={{
              textTransform: "none",
              color: "#6b3b21",
            }}
          >
            {expanded
              ? "Hide steps"
              : "Show steps"}
          </Button>
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box
          sx={{
            p: 2,
            display: "grid",
            gap: 1,
          }}
        >
          {path.steps.map(
            (step, index) => (
              <Box
                key={`${step.relationship_id}-${index}`}
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    md:
                      "1fr auto 1fr",
                  },
                  alignItems: "center",
                  gap: 1,
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: "#faf8f5",
                }}
              >
                <Typography
                  sx={{
                    color: "#4f2c1a",
                    fontWeight: 800,
                  }}
                >
                  {step.source_entity_name}
                </Typography>

                <Chip
                  label={
                    step.relationship_name
                  }
                  size="small"
                  sx={{
                    bgcolor: "#fff3dc",
                    color: "#765019",
                    fontWeight: 800,
                  }}
                />

                <Box
                  sx={{
                    display: "flex",
                    justifyContent: {
                      xs: "flex-start",
                      md: "space-between",
                    },
                    gap: 1,
                  }}
                >
                  <Typography
                    sx={{
                      color: "#4f2c1a",
                      fontWeight: 800,
                    }}
                  >
                    {step.target_entity_name}
                  </Typography>

                  <Typography
                    variant="caption"
                    sx={{
                      color:
                        confidenceTone(
                          step.confidence
                        ),
                      fontWeight: 800,
                    }}
                  >
                    {step.confidence}%
                  </Typography>
                </Box>
              </Box>
            )
          )}
        </Box>
      </Collapse>
    </Paper>
  );
}


function PhysicalTableCard({
  table,
}: {
  table: ReasoningTable;
}) {
  const [expanded, setExpanded] =
    useState(true);

  return (
    <Paper
      elevation={0}
      sx={{
        overflow: "hidden",
        borderRadius: 2.5,
        border: "1px solid #ece5dd",
      }}
    >
      <Box
        sx={{
          p: 2,
          bgcolor: "#faf8f5",
          display: "flex",
          justifyContent:
            "space-between",
          gap: 2,
        }}
      >
        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {table.business_name ||
              table.table_name}
          </Typography>

          <Typography
            variant="caption"
            sx={{ color: "#888888" }}
          >
            Entity: {table.entity_name}
            {" · "}
            {table.schema_name
              ? `${table.schema_name}.${table.table_name}`
              : table.table_name}
          </Typography>
        </Box>

        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 1,
          }}
        >
          <ConfidenceChip
            value={
              table.mapping_confidence
            }
          />

          <Button
            size="small"
            onClick={() =>
              setExpanded(
                (current) =>
                  !current
              )
            }
            sx={{
              textTransform: "none",
              color: "#6b3b21",
            }}
          >
            {expanded
              ? "Hide columns"
              : "Show columns"}
          </Button>
        </Box>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ p: 2 }}>
          {table.description && (
            <Typography
              variant="body2"
              sx={{
                mb: 2,
                color: "#666666",
                lineHeight: 1.6,
              }}
            >
              {table.description}
            </Typography>
          )}

          {table.columns.length === 0 ? (
            <Alert severity="info">
              The table was resolved, but no
              individual column matched strongly.
            </Alert>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "repeat(2, 1fr)",
                },
                gap: 1.2,
              }}
            >
              {table.columns.map(
                (column) => (
                  <ColumnCard
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


function ColumnCard({
  column,
}: {
  column: ReasoningColumn;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 1.7,
        borderRadius: 2,
        bgcolor: "#faf8f5",
        border: "1px solid #ece5dd",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent:
            "space-between",
          gap: 1,
        }}
      >
        <Box>
          <Typography
            variant="body2"
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {column.business_name ||
              column.column_name}
          </Typography>

          <Typography
            variant="caption"
            sx={{ color: "#888888" }}
          >
            {column.column_name}
            {" · "}
            {column.data_type}
          </Typography>
        </Box>

        <ConfidenceChip
          value={
            column.confidence
          }
        />
      </Box>

      {column.description && (
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 1,
            color: "#666666",
          }}
        >
          {column.description}
        </Typography>
      )}

      <Box
        sx={{
          mt: 1,
          display: "flex",
          flexWrap: "wrap",
          gap: 0.6,
        }}
      >
        <Chip
          label={column.classification}
          size="small"
          sx={{
            textTransform: "capitalize",
          }}
        />

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

        {column.matched_terms.map(
          (term) => (
            <Chip
              key={term}
              label={term}
              size="small"
              sx={{
                bgcolor: "#fff3dc",
                color: "#765019",
              }}
            />
          )
        )}
      </Box>
    </Paper>
  );
}


function ReasonList({
  reasons,
}: {
  reasons: string[];
}) {
  if (!reasons.length) {
    return null;
  }

  return (
    <Box sx={{ mt: 1.5 }}>
      {reasons.map((reason) => (
        <Typography
          key={reason}
          variant="caption"
          sx={{
            display: "block",
            mb: 0.5,
            color: "#666666",
          }}
        >
          ✓ {reason}
        </Typography>
      ))}
    </Box>
  );
}


function ConfidenceChip({
  value,
}: {
  value: number;
}) {
  const tone =
    confidenceTone(value);

  return (
    <Chip
      label={`${value}%`}
      size="small"
      sx={{
        bgcolor: `${tone}18`,
        color: tone,
        fontWeight: 900,
      }}
    />
  );
}


function EmptyMessage({
  text,
}: {
  text: string;
}) {
  return (
    <Typography
      variant="body2"
      sx={{
        py: 2,
        color: "#888888",
        textAlign: "center",
      }}
    >
      {text}
    </Typography>
  );
}


function confidenceTone(
  value: number
): string {
  if (value >= 85) {
    return "#28774b";
  }

  if (value >= 65) {
    return "#a56b18";
  }

  return "#b3261e";
}


function averageConfidence(
  values: number[]
): number {
  if (!values.length) {
    return 0;
  }

  return Math.round(
    values.reduce(
      (total, value) =>
        total + value,
      0
    ) / values.length
  );
}


function formatLabel(
  value: string
): string {
  return value.replaceAll(
    "_",
    " "
  );
}


export default ReasoningExplorerPage;
