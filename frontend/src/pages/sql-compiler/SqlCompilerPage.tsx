import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  TextField,
  Typography,
} from "@mui/material";

import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import CodeRoundedIcon from "@mui/icons-material/CodeRounded";
import StorageRoundedIcon from "@mui/icons-material/StorageRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";

import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getBusinessDomains,
} from "../../services/businessEntities";

import {
  compileSemanticSql,
} from "../../services/sqlCompiler";

import type {
  BusinessDomain,
} from "../../types/businessEntity";

import type {
  CompiledJoin,
  CompiledParameter,
  CompiledTable,
  SqlCompilerResult,
} from "../../types/sqlCompiler";


function SqlCompilerPage() {
  const [domains, setDomains] =
    useState<BusinessDomain[]>([]);

  const [selectedDomainId, setSelectedDomainId] =
    useState<number | "">("");

  const [prompt, setPrompt] =
    useState("Show active vehicles");

  const [requestedLimit, setRequestedLimit] =
    useState(100);

  const [maximumEntities, setMaximumEntities] =
    useState(6);

  const [maximumPathDepth, setMaximumPathDepth] =
    useState(4);

  const [userRole, setUserRole] =
    useState("standard_user");

  const [result, setResult] =
    useState<SqlCompilerResult | null>(null);

  const [loadingDomains, setLoadingDomains] =
    useState(true);

  const [compiling, setCompiling] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [messageType, setMessageType] =
    useState<"success" | "error">("success");


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
        showMessage(
          error?.response?.data?.detail ??
            "Unable to load business domains.",
          "error"
        );
      } finally {
        setLoadingDomains(false);
      }
    };

    loadDomains();
  }, []);


  const showMessage = (
    text: string,
    type: "success" | "error"
  ) => {
    setMessage(text);
    setMessageType(type);
  };


  const handleCompile = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    const cleanedPrompt =
      prompt.trim();

    if (!cleanedPrompt || compiling) {
      return;
    }

    try {
      setCompiling(true);
      setResult(null);

      const response =
        await compileSemanticSql({
          prompt: cleanedPrompt,
          domain_id:
            selectedDomainId === ""
              ? null
              : selectedDomainId,
          requested_limit:
            requestedLimit,
          maximum_entities:
            maximumEntities,
          maximum_path_depth:
            maximumPathDepth,
          user_role:
            userRole,
        });

      setResult(response);

      if (response.is_compiled) {
        showMessage(
          "SQL compiled successfully.",
          "success"
        );
      } else {
        showMessage(
          "The governed plan could not be compiled.",
          "error"
        );
      }
    } catch (error: any) {
      showMessage(
        error?.response?.data?.detail ??
          "Unable to compile the governed SQL plan.",
        "error"
      );
    } finally {
      setCompiling(false);
    }
  };


  const examples = [
    "Show active vehicles",
    "Show customers with active accounts",
    "Show total foreign currency amount by branch this month",
    "Show drivers associated with pending trips",
    "Show top 10 customers by account balance",
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
            Semantic SQL Compiler
          </Typography>

          <Typography
            sx={{
              mt: 0.7,
              color: "#777777",
            }}
          >
            Translate approved governed query plans
            into parameterized, read-only SQL.
          </Typography>
        </Box>

        <Chip
          icon={<CodeRoundedIcon />}
          label="Compilation only — no execution"
          sx={{
            bgcolor: "#e7f6ed",
            color: "#207744",
            fontWeight: 800,
          }}
        />
      </Box>

      <Paper
        component="form"
        onSubmit={handleCompile}
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
              lg: "320px minmax(0, 1fr)",
            },
            gap: 2.5,
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
                compiling
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

            <FormControl fullWidth>
              <InputLabel>
                Temporary user role
              </InputLabel>

              <Select
                label="Temporary user role"
                value={userRole}
                disabled={compiling}
                onChange={(event) =>
                  setUserRole(
                    event.target.value
                  )
                }
              >
                <MenuItem value="standard_user">
                  Standard User
                </MenuItem>

                <MenuItem value="manager">
                  Manager
                </MenuItem>

                <MenuItem value="executive">
                  Executive
                </MenuItem>

                <MenuItem value="analyst">
                  Analyst
                </MenuItem>

                <MenuItem value="knowledge_steward">
                  Knowledge Steward
                </MenuItem>

                <MenuItem value="data_steward">
                  Data Steward
                </MenuItem>

                <MenuItem value="administrator">
                  Administrator
                </MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Requested result limit"
              type="number"
              value={requestedLimit}
              disabled={compiling}
              onChange={(event) =>
                setRequestedLimit(
                  Math.max(
                    1,
                    Math.min(
                      1000,
                      Number(
                        event.target.value
                      )
                    )
                  )
                )
              }
            />

            <TextField
              label="Maximum entities"
              type="number"
              value={maximumEntities}
              disabled={compiling}
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
              disabled={compiling}
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
            minRows={10}
            maxRows={15}
            label="Business question"
            value={prompt}
            disabled={compiling}
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
            justifyContent: "flex-end",
          }}
        >
          <Button
            type="submit"
            variant="contained"
            disabled={
              compiling ||
              !prompt.trim()
            }
            startIcon={
              compiling
                ? (
                    <CircularProgress
                      size={18}
                      color="inherit"
                    />
                  )
                : (
                    <CodeRoundedIcon />
                  )
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
            {compiling
              ? "Compiling SQL..."
              : "Compile Governed SQL"}
          </Button>
        </Box>
      </Paper>

      {compiling && (
        <CompilerLoading />
      )}

      {result && (
        <CompilerResult
          result={result}
          onCopySql={() =>
            copyText(
              result.sql ?? "",
              "SQL copied to clipboard.",
              showMessage
            )
          }
        />
      )}

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={6000}
        onClose={() =>
          setMessage("")
        }
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
      >
        <Alert
          severity={messageType}
          variant="filled"
          onClose={() =>
            setMessage("")
          }
        >
          {message}
        </Alert>
      </Snackbar>
    </Box>
  );
}


function CompilerLoading() {
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
          width: 88,
          height: 88,
          mx: "auto",
          mb: 2,
          borderRadius: 4,
          display: "grid",
          placeItems: "center",
          color: "#ffffff",
          background:
            "linear-gradient(145deg, #60351f, #d3a034)",
        }}
      >
        <CodeRoundedIcon
          sx={{ fontSize: 42 }}
        />
      </Box>

      <Typography
        variant="h6"
        sx={{
          color: "#4f2c1a",
          fontWeight: 900,
        }}
      >
        Compiling the governed query plan
      </Typography>

      <Typography
        sx={{
          mt: 1,
          color: "#777777",
        }}
      >
        Validating tables, joins, columns, filters,
        parameters, dialect and row limits.
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


function CompilerResult({
  result,
  onCopySql,
}: {
  result: SqlCompilerResult;
  onCopySql: () => void;
}) {
  const decisionColor =
    result.is_compiled
      ? "#28774b"
      : "#b3261e";

  return (
    <Box sx={{ mt: 3 }}>
      {result.errors.map(
        (error) => (
          <Alert
            key={error}
            severity="error"
            sx={{ mb: 1.5 }}
          >
            {error}
          </Alert>
        )
      )}

      {result.warnings.map(
        (warning) => (
          <Alert
            key={warning}
            severity="warning"
            sx={{ mb: 1.5 }}
          >
            {warning}
          </Alert>
        )
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
        <SummaryCard
          label="Compilation Decision"
          value={formatLabel(
            result.decision
          )}
          color={decisionColor}
        />

        <SummaryCard
          label="Database Dialect"
          value={
            result.dialect
              ? formatLabel(
                  result.dialect
                )
              : "Not resolved"
          }
          color="#6b3b21"
        />

        <SummaryCard
          label="Approved Row Limit"
          value={String(
            result.approved_limit
          )}
          color="#9a672c"
        />

        <SummaryCard
          label="Overall Confidence"
          value={`${result.overall_confidence}%`}
          color={confidenceColor(
            result.overall_confidence
          )}
        />
      </Box>

      <Paper
        elevation={0}
        sx={{
          mt: 2.5,
          overflow: "hidden",
          borderRadius: 3,
          border: "1px solid #e9e2da",
        }}
      >
        <Box
          sx={{
            px: 2.5,
            py: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 2,
            bgcolor: result.is_compiled
              ? "#f0f8f3"
              : "#fff3f2",
            borderBottom:
              "1px solid #e9e2da",
          }}
        >
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.3,
            }}
          >
            {result.is_compiled ? (
              <CheckCircleRoundedIcon
                sx={{ color: "#28774b" }}
              />
            ) : (
              <ErrorRoundedIcon
                sx={{ color: "#b3261e" }}
              />
            )}

            <Box>
              <Typography
                sx={{
                  color: "#4f2c1a",
                  fontWeight: 900,
                }}
              >
                {result.is_compiled
                  ? "SQL compiled successfully"
                  : "SQL was not compiled"}
              </Typography>

              <Typography
                variant="body2"
                sx={{ color: "#777777" }}
              >
                {result.is_compiled
                  ? "This statement is parameterized and ready for read-only validation."
                  : "Review the governance decision and compiler errors."}
              </Typography>
            </Box>
          </Box>

          {result.sql && (
            <Button
              variant="outlined"
              startIcon={
                <ContentCopyRoundedIcon />
              }
              onClick={onCopySql}
              sx={{
                textTransform: "none",
                fontWeight: 800,
                color: "#6b3b21",
                borderColor: "#9f795d",
              }}
            >
              Copy SQL
            </Button>
          )}
        </Box>

        <Box
          sx={{
            p: {
              xs: 1.5,
              md: 2.5,
            },
            bgcolor: "#1f1b18",
            minHeight: 260,
            overflowX: "auto",
          }}
        >
          {result.sql ? (
            <Box
              component="pre"
              sx={{
                m: 0,
                color: "#f9e7c5",
                fontFamily:
                  "'Consolas', 'Courier New', monospace",
                fontSize: "0.9rem",
                lineHeight: 1.75,
                whiteSpace: "pre",
              }}
            >
              {result.sql}
            </Box>
          ) : (
            <Box
              sx={{
                minHeight: 230,
                display: "grid",
                placeItems: "center",
                textAlign: "center",
              }}
            >
              <Box>
                <CodeRoundedIcon
                  sx={{
                    fontSize: 48,
                    color: "#8c7b6f",
                  }}
                />

                <Typography
                  sx={{
                    mt: 1,
                    color: "#c8b9ae",
                  }}
                >
                  No SQL statement is available.
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      </Paper>

      <Box
        sx={{
          mt: 2.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "1fr 1fr",
          },
          gap: 2.5,
        }}
      >
        <CompilerSection
          title="Bound Parameters"
          subtitle="Runtime values are separated from SQL to prevent injection."
        >
          {result.parameters.length ? (
            <ParameterTable
              parameters={
                result.parameters
              }
            />
          ) : (
            <EmptyState
              text="This statement does not use bound parameters."
            />
          )}
        </CompilerSection>

        <CompilerSection
          title="Physical Tables"
          subtitle="Approved database objects selected by the governed plan."
        >
          {result.tables.length ? (
            <Box
              sx={{
                display: "grid",
                gap: 1.2,
              }}
            >
              {result.tables.map(
                (table) => (
                  <TableCard
                    key={
                      table.metadata_table_id
                    }
                    table={table}
                  />
                )
              )}
            </Box>
          ) : (
            <EmptyState
              text="No physical tables were compiled."
            />
          )}
        </CompilerSection>

        <CompilerSection
          title="Compiled Joins"
          subtitle="Approved physical join mappings used in the SQL statement."
        >
          {result.joins.length ? (
            <Box
              sx={{
                display: "grid",
                gap: 1.2,
              }}
            >
              {result.joins.map(
                (join) => (
                  <JoinCard
                    key={
                      join.join_mapping_id
                    }
                    join={join}
                  />
                )
              )}
            </Box>
          ) : (
            <EmptyState
              text="This statement does not require a physical join."
            />
          )}
        </CompilerSection>

        <CompilerSection
          title="Compiler Explanation"
          subtitle="A readable summary of what the compiler produced."
        >
          {result.explanation.length ? (
            <Box
              sx={{
                display: "grid",
                gap: 1,
              }}
            >
              {result.explanation.map(
                (item) => (
                  <Box
                    key={item}
                    sx={{
                      display: "flex",
                      gap: 1,
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
              )}
            </Box>
          ) : (
            <EmptyState
              text="No compiler explanation is available."
            />
          )}
        </CompilerSection>
      </Box>
    </Box>
  );
}


function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
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
          mt: 1,
          color,
          fontWeight: 900,
          textTransform: "capitalize",
        }}
      >
        {value}
      </Typography>
    </Paper>
  );
}


function CompilerSection({
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


function ParameterTable({
  parameters,
}: {
  parameters: CompiledParameter[];
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gap: 1,
      }}
    >
      {parameters.map(
        (parameter) => (
          <Paper
            key={parameter.name}
            elevation={0}
            sx={{
              p: 1.7,
              borderRadius: 2.2,
              bgcolor: "#faf8f5",
              border:
                "1px solid #ece5dd",
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "100px 1fr 110px",
              },
              gap: 1.3,
              alignItems: "center",
            }}
          >
            <Chip
              label={`:${parameter.name}`}
              size="small"
              sx={{
                justifySelf: "start",
                bgcolor: "#fff3dc",
                color: "#765019",
                fontWeight: 900,
              }}
            />

            <Typography
              variant="body2"
              sx={{
                color: "#4f2c1a",
                fontFamily:
                  "'Consolas', monospace",
                wordBreak: "break-all",
              }}
            >
              {formatParameterValue(
                parameter.value
              )}
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color: "#888888",
                textTransform: "capitalize",
              }}
            >
              {parameter.data_type}
            </Typography>
          </Paper>
        )
      )}
    </Box>
  );
}


function TableCard({
  table,
}: {
  table: CompiledTable;
}) {
  const fullName =
    table.schema_name
      ? `${table.schema_name}.${table.table_name}`
      : table.table_name;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2.5,
        bgcolor: "#faf8f5",
        border: "1px solid #ece5dd",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 1.5,
      }}
    >
      <Box
        sx={{
          display: "flex",
          gap: 1.3,
          alignItems: "center",
        }}
      >
        <Box
          sx={{
            width: 42,
            height: 42,
            borderRadius: 2,
            display: "grid",
            placeItems: "center",
            bgcolor: "#fff3dc",
            color: "#765019",
          }}
        >
          <StorageRoundedIcon />
        </Box>

        <Box>
          <Typography
            sx={{
              color: "#4f2c1a",
              fontWeight: 900,
            }}
          >
            {fullName}
          </Typography>

          <Typography
            variant="caption"
            sx={{ color: "#888888" }}
          >
            Metadata table #{table.metadata_table_id}
            {" · "}
            Data source #{table.data_source_id}
          </Typography>
        </Box>
      </Box>

      <Chip
        label={`Alias: ${table.alias}`}
        sx={{
          bgcolor: "#e7f6ed",
          color: "#207744",
          fontWeight: 800,
        }}
      />
    </Paper>
  );
}


function JoinCard({
  join,
}: {
  join: CompiledJoin;
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
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Box>
          <Typography
            variant="caption"
            sx={{
              color: "#9a672c",
              fontWeight: 900,
              textTransform: "uppercase",
            }}
          >
            {formatLabel(
              join.join_type
            )} join
          </Typography>

          <Typography
            sx={{
              mt: 0.6,
              color: "#4f2c1a",
              fontWeight: 900,
              fontFamily:
                "'Consolas', monospace",
            }}
          >
            {join.expression}
          </Typography>
        </Box>

        <Chip
          label={`Mapping #${join.join_mapping_id}`}
          size="small"
        />
      </Box>

      <Box
        sx={{
          mt: 1.5,
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "1fr auto 1fr",
          },
          gap: 1,
          alignItems: "center",
        }}
      >
        <Typography
          variant="body2"
          sx={{
            color: "#555555",
            fontWeight: 800,
          }}
        >
          {join.source_table_alias}.
          {join.source_column_name}
        </Typography>

        <Chip
          label="="
          size="small"
          sx={{
            bgcolor: "#fff3dc",
            color: "#765019",
            fontWeight: 900,
          }}
        />

        <Typography
          variant="body2"
          sx={{
            color: "#555555",
            fontWeight: 800,
          }}
        >
          {join.target_table_alias}.
          {join.target_column_name}
        </Typography>
      </Box>
    </Paper>
  );
}


function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <Box
      sx={{
        py: 4,
        textAlign: "center",
      }}
    >
      <Typography
        variant="body2"
        sx={{ color: "#888888" }}
      >
        {text}
      </Typography>
    </Box>
  );
}


async function copyText(
  text: string,
  successMessage: string,
  showMessage: (
    text: string,
    type: "success" | "error"
  ) => void
) {
  if (!text) {
    showMessage(
      "There is no SQL to copy.",
      "error"
    );
    return;
  }

  try {
    await navigator.clipboard.writeText(
      text
    );

    showMessage(
      successMessage,
      "success"
    );
  } catch {
    showMessage(
      "Unable to copy the SQL statement.",
      "error"
    );
  }
}


function formatParameterValue(
  value: unknown
): string {
  if (value === null) {
    return "NULL";
  }

  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value);
}


function formatLabel(
  value: string
): string {
  return value.replaceAll(
    "_",
    " "
  );
}


function confidenceColor(
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


export default SqlCompilerPage;
